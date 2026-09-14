import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from fluxmed.domain.enums import (
    AggregatedPricingModel,
    CompensationModel,
    FuelType,
    HelperPolicy,
    OperationStatus,
    VehicleOwnershipType,
    VehicleStatus,
    VehicleType,
    WorkerEngagementType,
    WorkerRole,
)
from fluxmed.domain.resources import (
    MaintenanceItemInput,
    OwnedVehicleCostInput,
    ResourceValidationError,
    VehicleCostCalculator,
)
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.resource import (
    AggregatedVehicleContractModel,
    OwnedVehicleCostProfileModel,
    VehicleMaintenanceItemModel,
    VehicleModel,
    WorkerAvailabilityModel,
    WorkerModel,
)
from fluxmed.infrastructure.repositories.resource_repository import ResourceRepository


class VehicleNotFoundError(LookupError):
    pass


class WorkerNotFoundError(LookupError):
    pass


class ResourceConflictError(RuntimeError):
    pass


class ResourceSelectionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MaintenanceInput:
    name: str
    cost_brl: Decimal
    interval_km: Decimal
    active: bool = True


@dataclass(frozen=True, slots=True)
class OwnedCostInput:
    acquisition_value_brl: Decimal
    residual_value_brl: Decimal
    useful_life_km: Decimal
    annual_ipva_brl: Decimal
    annual_insurance_brl: Decimal
    annual_fixed_costs_brl: Decimal
    expected_productive_hours_per_year: Decimal
    maintenance_items: list[MaintenanceInput]


@dataclass(frozen=True, slots=True)
class AggregatedContractInput:
    price_brl: Decimal
    pricing_model: AggregatedPricingModel = AggregatedPricingModel.PER_ROUTE
    fuel_included: bool = False
    driver_included: bool = False
    helper_included: bool = False


@dataclass(frozen=True, slots=True)
class VehicleInput:
    plate: str
    type: VehicleType
    ownership_type: VehicleOwnershipType
    max_payload_kg: Decimal
    max_volume_m3: Decimal
    max_range_km: Decimal
    refrigerated: bool = False
    status: VehicleStatus = VehicleStatus.AVAILABLE
    helper_policy: HelperPolicy = HelperPolicy.OPTIONAL
    fuel_type: FuelType | None = None
    fuel_efficiency_km_per_l: Decimal | None = None
    owned_cost: OwnedCostInput | None = None
    aggregated_contract: AggregatedContractInput | None = None


@dataclass(frozen=True, slots=True)
class MaintenanceView:
    id: uuid.UUID
    name: str
    cost_brl: Decimal
    interval_km: Decimal
    active: bool
    cost_per_km: Decimal


@dataclass(frozen=True, slots=True)
class VehicleCostView:
    ownership_type: VehicleOwnershipType
    depreciation_per_km: Decimal | None
    maintenance_per_km: Decimal | None
    fixed_cost_per_hour: Decimal | None
    contract_price_brl: Decimal | None
    pricing_model: AggregatedPricingModel | None
    fuel_included: bool
    driver_included: bool
    helper_included: bool
    maintenance_items: list[MaintenanceView]


@dataclass(frozen=True, slots=True)
class VehicleView:
    id: uuid.UUID
    plate: str
    type: VehicleType
    ownership_type: VehicleOwnershipType
    max_payload_kg: Decimal
    max_volume_m3: Decimal
    max_range_km: Decimal
    refrigerated: bool
    status: VehicleStatus
    helper_policy: HelperPolicy
    fuel_type: FuelType | None
    fuel_efficiency_km_per_l: Decimal | None
    active: bool
    cost: VehicleCostView
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkerInput:
    name: str
    role: WorkerRole
    engagement_type: WorkerEngagementType
    compensation_model: CompensationModel
    compensation_value_brl: Decimal


@dataclass(frozen=True, slots=True)
class WorkerView:
    id: uuid.UUID
    name: str
    role: WorkerRole
    engagement_type: WorkerEngagementType
    compensation_model: CompensationModel
    compensation_value_brl: Decimal
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkerAvailabilityView:
    worker_id: uuid.UUID
    date: date
    available: bool
    notes: str | None


@dataclass(frozen=True, slots=True)
class OperationResourcesView:
    operation_id: uuid.UUID
    operation_date: date
    selected_vehicle_ids: list[uuid.UUID]
    selected_worker_ids: list[uuid.UUID]
    vehicles: list[VehicleView]
    workers: list[WorkerView]
    unavailable_worker_ids: list[uuid.UUID]


class ResourceService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._resources = ResourceRepository(session)

    def create_vehicle(self, payload: VehicleInput) -> VehicleView:
        plate = self._normalize_plate(payload.plate)
        if self._resources.get_vehicle_by_plate(plate) is not None:
            raise ResourceConflictError("Já existe um veículo com esta placa.")
        self._validate_vehicle_input(payload)
        vehicle = VehicleModel(
            plate=plate,
            type=payload.type,
            ownership_type=payload.ownership_type,
            max_payload_kg=payload.max_payload_kg,
            max_volume_m3=payload.max_volume_m3,
            max_range_km=payload.max_range_km,
            refrigerated=payload.refrigerated,
            status=payload.status,
            helper_policy=self._normalized_helper_policy(payload.type, payload.helper_policy),
            fuel_type=payload.fuel_type,
            fuel_efficiency_km_per_l=payload.fuel_efficiency_km_per_l,
            active=True,
        )
        self._resources.add_vehicle(vehicle)
        self._session.flush()
        self._replace_cost_data(vehicle, payload.owned_cost, payload.aggregated_contract)
        self._session.flush()
        return self._vehicle_view(vehicle)

    def list_vehicles(
        self,
        *,
        active: bool | None = None,
        status: VehicleStatus | None = None,
        refrigerated: bool | None = None,
        q: str | None = None,
    ) -> list[VehicleView]:
        return [
            self._vehicle_view(item)
            for item in self._resources.list_vehicles(
                active=active,
                status=status,
                refrigerated=refrigerated,
                q=q,
            )
        ]

    def get_vehicle(self, vehicle_id: uuid.UUID) -> VehicleView:
        return self._vehicle_view(self._require_vehicle(vehicle_id))

    def update_vehicle(self, vehicle_id: uuid.UUID, changes: dict[str, Any]) -> VehicleView:
        model = self._require_vehicle(vehicle_id)
        editable = {
            "plate",
            "type",
            "max_payload_kg",
            "max_volume_m3",
            "max_range_km",
            "refrigerated",
            "status",
            "helper_policy",
            "fuel_type",
            "fuel_efficiency_km_per_l",
        }
        unknown = set(changes) - editable
        if unknown:
            raise ResourceValidationError(
                f"Campos de veículo não editáveis: {', '.join(sorted(unknown))}."
            )
        if "plate" in changes:
            plate = self._normalize_plate(str(changes["plate"]))
            existing = self._resources.get_vehicle_by_plate(plate)
            if existing is not None and existing.id != model.id:
                raise ResourceConflictError("Já existe um veículo com esta placa.")
            changes["plate"] = plate
        for field, value in changes.items():
            setattr(model, field, value)
        model.helper_policy = self._normalized_helper_policy(model.type, model.helper_policy)
        self._validate_vehicle_model(model)
        self._session.flush()
        return self._vehicle_view(model)

    def update_vehicle_cost(
        self,
        vehicle_id: uuid.UUID,
        *,
        owned_cost: OwnedCostInput | None,
        aggregated_contract: AggregatedContractInput | None,
    ) -> VehicleView:
        model = self._require_vehicle(vehicle_id)
        self._validate_ownership_payload(model.ownership_type, owned_cost, aggregated_contract)
        self._replace_cost_data(model, owned_cost, aggregated_contract)
        self._session.flush()
        return self._vehicle_view(model)

    def deactivate_vehicle(self, vehicle_id: uuid.UUID) -> VehicleView:
        model = self._require_vehicle(vehicle_id)
        model.active = False
        model.status = VehicleStatus.INACTIVE
        self._session.flush()
        return self._vehicle_view(model)

    def create_worker(self, payload: WorkerInput) -> WorkerView:
        self._validate_worker_input(payload)
        worker = WorkerModel(
            name=payload.name.strip(),
            role=payload.role,
            engagement_type=payload.engagement_type,
            compensation_model=payload.compensation_model,
            compensation_value_brl=payload.compensation_value_brl,
            active=True,
        )
        self._resources.add_worker(worker)
        self._session.flush()
        return self._worker_view(worker)

    def list_workers(
        self,
        *,
        active: bool | None = None,
        role: WorkerRole | None = None,
        q: str | None = None,
    ) -> list[WorkerView]:
        return [
            self._worker_view(item)
            for item in self._resources.list_workers(active=active, role=role, q=q)
        ]

    def get_worker(self, worker_id: uuid.UUID) -> WorkerView:
        return self._worker_view(self._require_worker(worker_id))

    def update_worker(self, worker_id: uuid.UUID, changes: dict[str, Any]) -> WorkerView:
        model = self._require_worker(worker_id)
        editable = {
            "name",
            "role",
            "engagement_type",
            "compensation_model",
            "compensation_value_brl",
        }
        unknown = set(changes) - editable
        if unknown:
            raise ResourceValidationError(
                f"Campos de worker não editáveis: {', '.join(sorted(unknown))}."
            )
        for field, value in changes.items():
            setattr(model, field, value)
        self._validate_worker_model(model)
        self._session.flush()
        return self._worker_view(model)

    def deactivate_worker(self, worker_id: uuid.UUID) -> WorkerView:
        model = self._require_worker(worker_id)
        model.active = False
        self._session.flush()
        return self._worker_view(model)

    def get_worker_availability(
        self, worker_id: uuid.UUID, target_date: date
    ) -> WorkerAvailabilityView:
        self._require_worker(worker_id)
        model = self._resources.get_availability(worker_id, target_date)
        if model is None:
            return WorkerAvailabilityView(
                worker_id=worker_id,
                date=target_date,
                available=True,
                notes=None,
            )
        return self._availability_view(model)

    def set_worker_availability(
        self,
        worker_id: uuid.UUID,
        target_date: date,
        *,
        available: bool,
        notes: str | None,
    ) -> WorkerAvailabilityView:
        worker = self._require_worker(worker_id)
        if not worker.active and available:
            raise ResourceSelectionError("Worker inativo não pode ser marcado como disponível.")
        model = self._resources.set_availability(
            worker_id,
            target_date,
            available=available,
            notes=self._clean_optional(notes),
        )
        self._session.flush()
        return self._availability_view(model)

    def get_operation_resources(self, operation_id: uuid.UUID) -> OperationResourcesView:
        operation = self._require_operation(operation_id)
        vehicles = self._resources.list_vehicles(active=True)
        workers = self._resources.list_workers(active=True)
        unavailable_worker_ids = [
            worker.id
            for worker in workers
            if not self.get_worker_availability(worker.id, operation.operation_date).available
        ]
        return OperationResourcesView(
            operation_id=operation.id,
            operation_date=operation.operation_date,
            selected_vehicle_ids=self._resources.selected_vehicle_ids(operation.id),
            selected_worker_ids=self._resources.selected_worker_ids(operation.id),
            vehicles=[self._vehicle_view(vehicle) for vehicle in vehicles],
            workers=[self._worker_view(worker) for worker in workers],
            unavailable_worker_ids=unavailable_worker_ids,
        )

    def update_operation_resources(
        self,
        operation_id: uuid.UUID,
        *,
        vehicle_ids: list[uuid.UUID],
        worker_ids: list[uuid.UUID],
    ) -> OperationResourcesView:
        operation = self._require_mutable_operation(operation_id)
        unique_vehicle_ids = list(dict.fromkeys(vehicle_ids))
        unique_worker_ids = list(dict.fromkeys(worker_ids))
        for vehicle_id in unique_vehicle_ids:
            vehicle = self._require_vehicle(vehicle_id)
            if not vehicle.active or vehicle.status is not VehicleStatus.AVAILABLE:
                raise ResourceSelectionError(
                    f"Veículo {vehicle.plate} não está disponível para seleção."
                )
        for worker_id in unique_worker_ids:
            worker = self._require_worker(worker_id)
            if not worker.active:
                raise ResourceSelectionError(f"Worker {worker.name} está inativo.")
            availability = self.get_worker_availability(worker_id, operation.operation_date)
            if not availability.available:
                date_label = operation.operation_date.isoformat()
                raise ResourceSelectionError(
                    f"Worker {worker.name} está indisponível em {date_label}."
                )
        self._resources.replace_operation_selection(
            operation.id,
            vehicle_ids=unique_vehicle_ids,
            worker_ids=unique_worker_ids,
        )
        self._touch_operation(operation)
        self._session.flush()
        return self.get_operation_resources(operation.id)

    def _replace_cost_data(
        self,
        vehicle: VehicleModel,
        owned_cost: OwnedCostInput | None,
        aggregated_contract: AggregatedContractInput | None,
    ) -> None:
        self._validate_ownership_payload(vehicle.ownership_type, owned_cost, aggregated_contract)
        owned_model: OwnedVehicleCostProfileModel | None = None
        maintenance_models: list[VehicleMaintenanceItemModel] = []
        contract_model: AggregatedVehicleContractModel | None = None
        if owned_cost is not None:
            profile = self._owned_domain_input(owned_cost)
            profile.validate()
            owned_model = OwnedVehicleCostProfileModel(
                vehicle_id=vehicle.id,
                acquisition_value_brl=owned_cost.acquisition_value_brl,
                residual_value_brl=owned_cost.residual_value_brl,
                useful_life_km=owned_cost.useful_life_km,
                annual_ipva_brl=owned_cost.annual_ipva_brl,
                annual_insurance_brl=owned_cost.annual_insurance_brl,
                annual_fixed_costs_brl=owned_cost.annual_fixed_costs_brl,
                expected_productive_hours_per_year=owned_cost.expected_productive_hours_per_year,
            )
            for item in owned_cost.maintenance_items:
                if not item.name.strip():
                    raise ResourceValidationError("Item de manutenção deve possuir nome.")
                domain_item = MaintenanceItemInput(
                    cost_brl=item.cost_brl,
                    interval_km=item.interval_km,
                )
                domain_item.validate()
                maintenance_models.append(
                    VehicleMaintenanceItemModel(
                        vehicle_id=vehicle.id,
                        name=item.name.strip(),
                        cost_brl=item.cost_brl,
                        interval_km=item.interval_km,
                        active=item.active,
                    )
                )
        if aggregated_contract is not None:
            if aggregated_contract.price_brl < Decimal("0"):
                raise ResourceValidationError("Preço de contrato não pode ser negativo.")
            contract_model = AggregatedVehicleContractModel(
                vehicle_id=vehicle.id,
                pricing_model=aggregated_contract.pricing_model,
                price_brl=aggregated_contract.price_brl,
                fuel_included=aggregated_contract.fuel_included,
                driver_included=aggregated_contract.driver_included,
                helper_included=aggregated_contract.helper_included,
                active=True,
            )
        self._resources.replace_vehicle_cost_data(
            vehicle.id,
            owned_profile=owned_model,
            maintenance_items=maintenance_models,
            aggregated_contract=contract_model,
        )

    def _vehicle_view(self, vehicle: VehicleModel) -> VehicleView:
        owned = self._resources.get_owned_cost_profile(vehicle.id)
        contract = self._resources.get_aggregated_contract(vehicle.id)
        maintenance_models = self._resources.list_maintenance_items(vehicle.id)
        maintenance_views = [
            MaintenanceView(
                id=item.id,
                name=item.name,
                cost_brl=item.cost_brl,
                interval_km=item.interval_km,
                active=item.active,
                cost_per_km=(item.cost_brl / item.interval_km),
            )
            for item in maintenance_models
        ]
        if vehicle.ownership_type is VehicleOwnershipType.OWNED:
            if owned is None:
                raise ResourceConflictError(
                    f"Veículo próprio {vehicle.plate} está sem perfil de custo."
                )
            rates = VehicleCostCalculator.owned_rates(
                self._owned_domain_model(owned),
                [
                    MaintenanceItemInput(cost_brl=item.cost_brl, interval_km=item.interval_km)
                    for item in maintenance_models
                    if item.active
                ],
            )
            cost = VehicleCostView(
                ownership_type=vehicle.ownership_type,
                depreciation_per_km=rates.depreciation_per_km,
                maintenance_per_km=rates.maintenance_per_km,
                fixed_cost_per_hour=rates.fixed_cost_per_hour,
                contract_price_brl=None,
                pricing_model=None,
                fuel_included=False,
                driver_included=False,
                helper_included=False,
                maintenance_items=maintenance_views,
            )
        else:
            if contract is None:
                raise ResourceConflictError(
                    f"Veículo agregado {vehicle.plate} está sem contrato ativo."
                )
            cost = VehicleCostView(
                ownership_type=vehicle.ownership_type,
                depreciation_per_km=None,
                maintenance_per_km=None,
                fixed_cost_per_hour=None,
                contract_price_brl=contract.price_brl,
                pricing_model=contract.pricing_model,
                fuel_included=contract.fuel_included,
                driver_included=contract.driver_included,
                helper_included=contract.helper_included,
                maintenance_items=[],
            )
        return VehicleView(
            id=vehicle.id,
            plate=vehicle.plate,
            type=vehicle.type,
            ownership_type=vehicle.ownership_type,
            max_payload_kg=vehicle.max_payload_kg,
            max_volume_m3=vehicle.max_volume_m3,
            max_range_km=vehicle.max_range_km,
            refrigerated=vehicle.refrigerated,
            status=vehicle.status,
            helper_policy=vehicle.helper_policy,
            fuel_type=vehicle.fuel_type,
            fuel_efficiency_km_per_l=vehicle.fuel_efficiency_km_per_l,
            active=vehicle.active,
            cost=cost,
            created_at=vehicle.created_at,
            updated_at=vehicle.updated_at,
        )

    @staticmethod
    def _worker_view(worker: WorkerModel) -> WorkerView:
        return WorkerView(
            id=worker.id,
            name=worker.name,
            role=worker.role,
            engagement_type=worker.engagement_type,
            compensation_model=worker.compensation_model,
            compensation_value_brl=worker.compensation_value_brl,
            active=worker.active,
            created_at=worker.created_at,
            updated_at=worker.updated_at,
        )

    @staticmethod
    def _availability_view(model: WorkerAvailabilityModel) -> WorkerAvailabilityView:
        return WorkerAvailabilityView(
            worker_id=model.worker_id,
            date=model.date,
            available=model.available,
            notes=model.notes,
        )

    def _require_vehicle(self, vehicle_id: uuid.UUID) -> VehicleModel:
        model = self._resources.get_vehicle(vehicle_id)
        if model is None:
            raise VehicleNotFoundError(vehicle_id)
        return model

    def _require_worker(self, worker_id: uuid.UUID) -> WorkerModel:
        model = self._resources.get_worker(worker_id)
        if model is None:
            raise WorkerNotFoundError(worker_id)
        return model

    def _require_operation(self, operation_id: uuid.UUID) -> OperationModel:
        model = self._session.get(OperationModel, operation_id)
        if model is None:
            raise ResourceSelectionError("Operação não encontrada.")
        return model

    def _require_mutable_operation(self, operation_id: uuid.UUID) -> OperationModel:
        model = self._require_operation(operation_id)
        if model.status is OperationStatus.DISPATCHED:
            raise ResourceConflictError("Uma operação despachada é imutável.")
        if model.status is OperationStatus.OPTIMIZING:
            raise ResourceConflictError("Não altere recursos durante a otimização.")
        return model

    @staticmethod
    def _touch_operation(operation: OperationModel) -> None:
        if operation.status in {OperationStatus.OPTIMIZED, OperationStatus.APPROVED}:
            operation.status = OperationStatus.OUTDATED
        elif operation.status is OperationStatus.READY:
            operation.status = OperationStatus.DRAFT

    @staticmethod
    def _validate_vehicle_input(payload: VehicleInput) -> None:
        if payload.max_payload_kg <= Decimal("0"):
            raise ResourceValidationError("Capacidade de peso deve ser maior que zero.")
        if payload.max_volume_m3 <= Decimal("0"):
            raise ResourceValidationError("Capacidade de volume deve ser maior que zero.")
        if payload.max_range_km <= Decimal("0"):
            raise ResourceValidationError("Autonomia deve ser maior que zero.")
        if (
            payload.fuel_efficiency_km_per_l is not None
            and payload.fuel_efficiency_km_per_l <= Decimal("0")
        ):
            raise ResourceValidationError("Eficiência de combustível deve ser maior que zero.")
        ResourceService._validate_ownership_payload(
            payload.ownership_type,
            payload.owned_cost,
            payload.aggregated_contract,
        )

    @staticmethod
    def _validate_vehicle_model(model: VehicleModel) -> None:
        if not model.plate.strip():
            raise ResourceValidationError("Placa é obrigatória.")
        if model.max_payload_kg <= Decimal("0"):
            raise ResourceValidationError("Capacidade de peso deve ser maior que zero.")
        if model.max_volume_m3 <= Decimal("0"):
            raise ResourceValidationError("Capacidade de volume deve ser maior que zero.")
        if model.max_range_km <= Decimal("0"):
            raise ResourceValidationError("Autonomia deve ser maior que zero.")
        if (
            model.fuel_efficiency_km_per_l is not None
            and model.fuel_efficiency_km_per_l <= Decimal("0")
        ):
            raise ResourceValidationError("Eficiência de combustível deve ser maior que zero.")

    @staticmethod
    def _validate_ownership_payload(
        ownership_type: VehicleOwnershipType,
        owned_cost: OwnedCostInput | None,
        aggregated_contract: AggregatedContractInput | None,
    ) -> None:
        if ownership_type is VehicleOwnershipType.OWNED:
            if owned_cost is None:
                raise ResourceValidationError("Veículo próprio exige perfil de custo próprio.")
            if aggregated_contract is not None:
                raise ResourceValidationError("Veículo próprio não pode possuir contrato agregado.")
        else:
            if aggregated_contract is None:
                raise ResourceValidationError("Veículo agregado exige contrato por rota.")
            if owned_cost is not None:
                raise ResourceValidationError("Veículo agregado não usa perfil de custo próprio.")

    @staticmethod
    def _validate_worker_input(payload: WorkerInput) -> None:
        if not payload.name.strip():
            raise ResourceValidationError("Nome do worker é obrigatório.")
        if payload.compensation_value_brl < Decimal("0"):
            raise ResourceValidationError("Compensação não pode ser negativa.")

    @staticmethod
    def _validate_worker_model(model: WorkerModel) -> None:
        if not model.name.strip():
            raise ResourceValidationError("Nome do worker é obrigatório.")
        if model.compensation_value_brl < Decimal("0"):
            raise ResourceValidationError("Compensação não pode ser negativa.")

    @staticmethod
    def _normalize_plate(value: str) -> str:
        plate = "".join(char for char in value.upper().strip() if char.isalnum())
        if len(plate) < 7 or len(plate) > 8:
            raise ResourceValidationError("Placa deve possuir 7 ou 8 caracteres alfanuméricos.")
        return plate

    @staticmethod
    def _normalized_helper_policy(
        vehicle_type: VehicleType, helper_policy: HelperPolicy
    ) -> HelperPolicy:
        if vehicle_type is VehicleType.MOTO:
            return HelperPolicy.FORBIDDEN
        return helper_policy

    @staticmethod
    def _owned_domain_input(payload: OwnedCostInput) -> OwnedVehicleCostInput:
        return OwnedVehicleCostInput(
            acquisition_value_brl=payload.acquisition_value_brl,
            residual_value_brl=payload.residual_value_brl,
            useful_life_km=payload.useful_life_km,
            annual_ipva_brl=payload.annual_ipva_brl,
            annual_insurance_brl=payload.annual_insurance_brl,
            annual_fixed_costs_brl=payload.annual_fixed_costs_brl,
            expected_productive_hours_per_year=payload.expected_productive_hours_per_year,
        )

    @staticmethod
    def _owned_domain_model(model: OwnedVehicleCostProfileModel) -> OwnedVehicleCostInput:
        return OwnedVehicleCostInput(
            acquisition_value_brl=model.acquisition_value_brl,
            residual_value_brl=model.residual_value_brl,
            useful_life_km=model.useful_life_km,
            annual_ipva_brl=model.annual_ipva_brl,
            annual_insurance_brl=model.annual_insurance_brl,
            annual_fixed_costs_brl=model.annual_fixed_costs_brl,
            expected_productive_hours_per_year=model.expected_productive_hours_per_year,
        )

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
