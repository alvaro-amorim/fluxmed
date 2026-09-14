import uuid
from dataclasses import dataclass
from datetime import time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fluxmed.domain.enums import (
    DeliveryPriority,
    HandlingRequirement,
    HelperPolicy,
    OperationStatus,
    TemperatureClass,
    TimeWindowPolicy,
    VehicleStatus,
    VehicleType,
    WorkerRole,
)
from fluxmed.infrastructure.models.city import AddressModel, CityModel, RoadSegmentModel
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.resource import (
    AggregatedVehicleContractModel,
    VehicleModel,
    WorkerModel,
)
from fluxmed.infrastructure.repositories.resource_repository import ResourceRepository

ZERO = Decimal("0")


class PreflightOperationNotFoundError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class PreflightOperation:
    start_time: time
    end_time: time


@dataclass(frozen=True, slots=True)
class PreflightDelivery:
    id: uuid.UUID
    delivery_code: str
    weight_kg: Decimal
    volume_m3: Decimal
    priority: DeliveryPriority
    temperature_class: TemperatureClass
    handling_requirement: HandlingRequirement
    time_window_policy: TimeWindowPolicy
    address_valid: bool = True
    minimum_roundtrip_km: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PreflightVehicle:
    id: uuid.UUID
    plate: str
    type: VehicleType
    max_payload_kg: Decimal
    max_volume_m3: Decimal
    max_range_km: Decimal
    refrigerated: bool
    helper_policy: HelperPolicy
    driver_included: bool = False
    helper_included: bool = False


@dataclass(frozen=True, slots=True)
class PreflightWorker:
    id: uuid.UUID
    role: WorkerRole


@dataclass(frozen=True, slots=True)
class PreflightIssue:
    code: str
    message: str
    related_delivery_ids: tuple[uuid.UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class PreflightSummary:
    delivery_count: int
    vehicle_count: int
    worker_count: int
    critical_count: int
    refrigerated_count: int
    hard_window_count: int
    two_person_count: int
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    operation_window_minutes: int


@dataclass(frozen=True, slots=True)
class PreflightResult:
    status: str
    blocking_errors: tuple[PreflightIssue, ...]
    warnings: tuple[PreflightIssue, ...]
    summary: PreflightSummary

    @property
    def is_valid(self) -> bool:
        return not self.blocking_errors


class PreflightValidator:
    def validate(
        self,
        *,
        operation: PreflightOperation,
        deliveries: list[PreflightDelivery],
        vehicles: list[PreflightVehicle],
        workers: list[PreflightWorker],
    ) -> PreflightResult:
        blocking: list[PreflightIssue] = []
        warnings: list[PreflightIssue] = []

        if operation.end_time <= operation.start_time:
            blocking.append(
                PreflightIssue(
                    code="INVALID_OPERATION_SCHEDULE",
                    message="A janela operacional deve terminar depois do horário de saída.",
                )
            )
        if not deliveries:
            blocking.append(
                PreflightIssue(
                    code="NO_DELIVERIES",
                    message="Adicione ao menos uma entrega antes de otimizar.",
                )
            )
        if not vehicles:
            blocking.append(
                PreflightIssue(
                    code="NO_VEHICLES",
                    message="Selecione ao menos um veículo disponível antes de otimizar.",
                )
            )

        worker_roles = {worker.role for worker in workers}
        for delivery in deliveries:
            related = (delivery.id,)
            if not delivery.address_valid:
                blocking.append(
                    PreflightIssue(
                        code="ADDRESS_NOT_FOUND",
                        message=(
                            f"O endereço da entrega {delivery.delivery_code} "
                            "não está roteável."
                        ),
                        related_delivery_ids=related,
                    )
                )
                continue
            if not vehicles:
                continue

            temperature_candidates = [
                vehicle
                for vehicle in vehicles
                if delivery.temperature_class is not TemperatureClass.REFRIGERATED
                or vehicle.refrigerated
            ]
            if not temperature_candidates:
                blocking.append(
                    PreflightIssue(
                        code="NO_FEASIBLE_VEHICLE",
                        message=(
                            f"A entrega {delivery.delivery_code} exige refrigeração, "
                            "mas não há veículo refrigerado selecionado."
                        ),
                        related_delivery_ids=related,
                    )
                )
                continue

            capacity_candidates = [
                vehicle
                for vehicle in temperature_candidates
                if vehicle.max_payload_kg >= delivery.weight_kg
                and vehicle.max_volume_m3 >= delivery.volume_m3
            ]
            if not capacity_candidates:
                blocking.append(
                    PreflightIssue(
                        code="CAPACITY_INFEASIBLE",
                        message=(
                            f"A entrega {delivery.delivery_code} excede a capacidade individual "
                            "de peso ou volume dos veículos elegíveis."
                        ),
                        related_delivery_ids=related,
                    )
                )
                continue

            range_candidates = [
                vehicle
                for vehicle in capacity_candidates
                if delivery.minimum_roundtrip_km is None
                or vehicle.max_range_km >= delivery.minimum_roundtrip_km
            ]
            if not range_candidates:
                blocking.append(
                    PreflightIssue(
                        code="RANGE_INFEASIBLE",
                        message=(
                            f"A entrega {delivery.delivery_code} ultrapassa até o limite inferior "
                            "seguro de autonomia dos veículos elegíveis."
                        ),
                        related_delivery_ids=related,
                    )
                )
                continue

            if not any(
                self._team_available(vehicle, delivery, worker_roles)
                for vehicle in range_candidates
            ):
                blocking.append(
                    PreflightIssue(
                        code="TEAM_INFEASIBLE",
                        message=(
                            "Não há equipe selecionada capaz de atender a entrega "
                            f"{delivery.delivery_code} com os veículos elegíveis."
                        ),
                        related_delivery_ids=related,
                    )
                )

        refrigerated_deliveries = [
            delivery
            for delivery in deliveries
            if delivery.temperature_class is TemperatureClass.REFRIGERATED
        ]
        refrigerated_vehicles = [vehicle for vehicle in vehicles if vehicle.refrigerated]
        if refrigerated_deliveries and len(refrigerated_vehicles) == 1:
            warnings.append(
                PreflightIssue(
                    code="LOW_REFRIGERATION_REDUNDANCY",
                    message=(
                        "Existe apenas um veículo refrigerado selecionado; "
                        "qualquer indisponibilidade pode inviabilizar entregas refrigeradas."
                    ),
                    related_delivery_ids=tuple(item.id for item in refrigerated_deliveries),
                )
            )

        summary = PreflightSummary(
            delivery_count=len(deliveries),
            vehicle_count=len(vehicles),
            worker_count=len(workers),
            critical_count=sum(
                delivery.priority is DeliveryPriority.CRITICAL for delivery in deliveries
            ),
            refrigerated_count=len(refrigerated_deliveries),
            hard_window_count=sum(
                delivery.time_window_policy is TimeWindowPolicy.HARD for delivery in deliveries
            ),
            two_person_count=sum(
                delivery.handling_requirement is HandlingRequirement.TWO_PERSON
                for delivery in deliveries
            ),
            total_weight_kg=sum((delivery.weight_kg for delivery in deliveries), ZERO),
            total_volume_m3=sum((delivery.volume_m3 for delivery in deliveries), ZERO),
            operation_window_minutes=self._window_minutes(operation),
        )
        return PreflightResult(
            status="VALID" if not blocking else "INVALID",
            blocking_errors=tuple(blocking),
            warnings=tuple(warnings),
            summary=summary,
        )

    @staticmethod
    def _team_available(
        vehicle: PreflightVehicle,
        delivery: PreflightDelivery,
        worker_roles: set[WorkerRole],
    ) -> bool:
        if (
            delivery.handling_requirement is HandlingRequirement.TWO_PERSON
            and vehicle.type is VehicleType.MOTO
        ):
            return False

        if vehicle.type is VehicleType.MOTO:
            driver_available = (
                vehicle.driver_included or WorkerRole.MOTORCYCLE_COURIER in worker_roles
            )
        else:
            driver_available = vehicle.driver_included or WorkerRole.DRIVER in worker_roles
        if not driver_available:
            return False

        helper_required = (
            delivery.handling_requirement is HandlingRequirement.TWO_PERSON
            or vehicle.helper_policy is HelperPolicy.REQUIRED
        )
        return (
            not helper_required
            or vehicle.helper_included
            or WorkerRole.HELPER in worker_roles
        )

    @staticmethod
    def _window_minutes(operation: PreflightOperation) -> int:
        start = operation.start_time.hour * 60 + operation.start_time.minute
        end = operation.end_time.hour * 60 + operation.end_time.minute
        return max(0, end - start)


class PreflightService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._resources = ResourceRepository(session)
        self._validator = PreflightValidator()

    def validate_operation(self, operation_id: uuid.UUID) -> PreflightResult:
        operation = self._session.get(OperationModel, operation_id)
        if operation is None:
            raise PreflightOperationNotFoundError(operation_id)

        deliveries = list(
            self._session.scalars(
                select(DeliveryModel)
                .where(DeliveryModel.operation_id == operation_id)
                .order_by(DeliveryModel.delivery_code)
            )
        )
        selected_vehicle_ids = self._resources.selected_vehicle_ids(operation_id)
        selected_worker_ids = self._resources.selected_worker_ids(operation_id)

        vehicles = self._load_vehicles(selected_vehicle_ids)
        workers = self._load_workers(selected_worker_ids, operation)
        preflight_deliveries = [self._delivery_input(delivery) for delivery in deliveries]

        result = self._validator.validate(
            operation=PreflightOperation(
                start_time=operation.operation_start_time,
                end_time=operation.operation_end_time,
            ),
            deliveries=preflight_deliveries,
            vehicles=vehicles,
            workers=workers,
        )

        if result.is_valid and operation.status is OperationStatus.DRAFT:
            operation.status = OperationStatus.READY
        elif not result.is_valid and operation.status is OperationStatus.READY:
            operation.status = OperationStatus.DRAFT
        self._session.flush()
        return result

    def _load_vehicles(self, vehicle_ids: list[uuid.UUID]) -> list[PreflightVehicle]:
        loaded: list[PreflightVehicle] = []
        for vehicle_id in vehicle_ids:
            vehicle = self._session.get(VehicleModel, vehicle_id)
            if (
                vehicle is None
                or not vehicle.active
                or vehicle.status is not VehicleStatus.AVAILABLE
            ):
                continue
            contract = self._session.scalar(
                select(AggregatedVehicleContractModel).where(
                    AggregatedVehicleContractModel.vehicle_id == vehicle.id,
                    AggregatedVehicleContractModel.active.is_(True),
                )
            )
            loaded.append(
                PreflightVehicle(
                    id=vehicle.id,
                    plate=vehicle.plate,
                    type=vehicle.type,
                    max_payload_kg=vehicle.max_payload_kg,
                    max_volume_m3=vehicle.max_volume_m3,
                    max_range_km=vehicle.max_range_km,
                    refrigerated=vehicle.refrigerated,
                    helper_policy=vehicle.helper_policy,
                    driver_included=contract.driver_included if contract is not None else False,
                    helper_included=contract.helper_included if contract is not None else False,
                )
            )
        return loaded

    def _load_workers(
        self,
        worker_ids: list[uuid.UUID],
        operation: OperationModel,
    ) -> list[PreflightWorker]:
        loaded: list[PreflightWorker] = []
        for worker_id in worker_ids:
            worker = self._session.get(WorkerModel, worker_id)
            if worker is None or not worker.active:
                continue
            availability = self._resources.get_availability(worker.id, operation.operation_date)
            if availability is not None and not availability.available:
                continue
            loaded.append(PreflightWorker(id=worker.id, role=worker.role))
        return loaded

    def _delivery_input(self, delivery: DeliveryModel) -> PreflightDelivery:
        address = self._session.get(AddressModel, delivery.destination_address_id)
        segment = (
            self._session.get(RoadSegmentModel, address.road_segment_id)
            if address is not None
            else None
        )
        address_valid = bool(
            address is not None
            and address.active
            and segment is not None
            and segment.active
        )
        minimum_roundtrip_km: Decimal | None = None
        if address_valid:
            distance_m = self._session.scalar(
                select(func.ST_DistanceSphere(AddressModel.location, CityModel.depot_geometry))
                .join(CityModel, CityModel.id == AddressModel.city_id)
                .where(AddressModel.id == delivery.destination_address_id)
            )
            if distance_m is not None:
                minimum_roundtrip_km = (Decimal(str(distance_m)) * Decimal("2")) / Decimal(
                    "1000"
                )

        return PreflightDelivery(
            id=delivery.id,
            delivery_code=delivery.delivery_code,
            weight_kg=delivery.total_weight_kg,
            volume_m3=delivery.total_volume_m3,
            priority=delivery.priority,
            temperature_class=delivery.temperature_class,
            handling_requirement=delivery.handling_requirement,
            time_window_policy=delivery.time_window_policy,
            address_valid=address_valid,
            minimum_roundtrip_km=minimum_roundtrip_km,
        )
