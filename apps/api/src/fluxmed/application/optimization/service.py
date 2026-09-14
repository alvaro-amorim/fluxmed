import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.application.optimization.routing_matrix import RoutingMatrixBuilder
from fluxmed.application.preflight import PreflightService
from fluxmed.application.resources import ResourceService, VehicleView
from fluxmed.domain.enums import OperationStatus, VehicleOwnershipType
from fluxmed.infrastructure.models.city import AddressModel, CityModel
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.optimization import (
    GeneticOptimizer,
    GeneticOptimizerConfig,
    OptimizationContext,
    OptimizationDelivery,
    OptimizationResult,
    OptimizationVehicle,
    SolutionValidator,
    ValidationResult,
)

ZERO = Decimal("0")


class OptimizationOperationNotFoundError(LookupError):
    pass


class OptimizationInputError(ValueError):
    pass


class OptimizationValidationMismatchError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OperationOptimizationView:
    operation_id: uuid.UUID
    random_seed: int
    result: OptimizationResult
    validation: ValidationResult


class OptimizationService:
    def __init__(
        self,
        session: Session,
        *,
        config: GeneticOptimizerConfig | None = None,
    ) -> None:
        self._session = session
        self._optimizer = GeneticOptimizer(config)
        self._validator = SolutionValidator()

    def optimize_operation(
        self,
        operation_id: uuid.UUID,
        *,
        random_seed: int | None = None,
    ) -> OperationOptimizationView:
        operation = self._session.get(OperationModel, operation_id)
        if operation is None:
            raise OptimizationOperationNotFoundError(operation_id)
        if operation.status is OperationStatus.DISPATCHED:
            raise OptimizationInputError("Operação despachada não pode ser reotimizada.")
        if operation.status is OperationStatus.OPTIMIZING:
            raise OptimizationInputError("Já existe uma otimização em andamento.")

        preflight = PreflightService(self._session).validate_operation(operation_id)
        if not preflight.is_valid:
            codes = ", ".join(issue.code for issue in preflight.blocking_errors)
            raise OptimizationInputError(f"Preflight inválido: {codes}.")

        delivery_models = list(
            self._session.scalars(
                select(DeliveryModel)
                .where(DeliveryModel.operation_id == operation_id)
                .order_by(DeliveryModel.delivery_code)
            )
        )
        deliveries = [
            OptimizationDelivery(
                id=delivery.id,
                weight_kg=delivery.total_weight_kg,
                volume_m3=delivery.total_volume_m3,
                service_minutes=delivery.service_time_minutes,
                priority=delivery.priority,
                temperature_class=delivery.temperature_class,
                time_window_policy=delivery.time_window_policy,
                time_window_start=delivery.time_window_start,
                time_window_end=delivery.time_window_end,
            )
            for delivery in delivery_models
        ]

        resource_view = ResourceService(self._session).get_operation_resources(operation_id)
        selected_ids = set(resource_view.selected_vehicle_ids)
        selected_vehicle_views = [
            vehicle for vehicle in resource_view.vehicles if vehicle.id in selected_ids
        ]
        vehicles = [self._vehicle_input(vehicle) for vehicle in selected_vehicle_views]
        if not deliveries or not vehicles:
            raise OptimizationInputError("Otimização exige entregas e veículos selecionados.")

        context = self._optimization_context(operation, delivery_models)
        matrix = RoutingMatrixBuilder(self._session).build(
            operation=operation,
            delivery_addresses={
                delivery.id: delivery.destination_address_id for delivery in delivery_models
            },
        )
        seed = random_seed if random_seed is not None else operation.id.int % 2_147_483_647
        result = self._optimizer.optimize(
            deliveries=deliveries,
            vehicles=vehicles,
            travel_matrix=matrix,
            random_seed=seed,
            context=context,
        )
        validation = self._validator.validate(
            solution=result.best.solution,
            deliveries=deliveries,
            vehicles=vehicles,
            context=context,
        )
        if result.best.fitness.feasible != validation.valid:
            raise OptimizationValidationMismatchError(
                "OPTIMIZER_VALIDATION_MISMATCH: fitness e validator divergiram."
            )
        if not validation.valid:
            issue_codes = ", ".join(issue.code for issue in validation.issues)
            raise OptimizationInputError(
                f"NO_FEASIBLE_SOLUTION_FOUND: {issue_codes or 'sem solução válida'}."
            )

        return OperationOptimizationView(
            operation_id=operation.id,
            random_seed=seed,
            result=result,
            validation=validation,
        )

    def _optimization_context(
        self,
        operation: OperationModel,
        deliveries: list[DeliveryModel],
    ) -> OptimizationContext:
        first_address = self._session.get(AddressModel, deliveries[0].destination_address_id)
        if first_address is None:
            raise OptimizationInputError("Não foi possível determinar a cidade da operação.")
        city = self._session.get(CityModel, first_address.city_id)
        if city is None:
            raise OptimizationInputError("Não foi possível determinar o timezone da operação.")
        timezone = ZoneInfo(city.timezone)
        return OptimizationContext(
            operation_start_at=datetime.combine(
                operation.operation_date,
                operation.operation_start_time,
                tzinfo=timezone,
            ),
            operation_end_at=datetime.combine(
                operation.operation_date,
                operation.operation_end_time,
                tzinfo=timezone,
            ),
        )

    @staticmethod
    def _vehicle_input(vehicle: VehicleView) -> OptimizationVehicle:
        if vehicle.ownership_type is VehicleOwnershipType.OWNED:
            cost_per_km = (vehicle.cost.depreciation_per_km or ZERO) + (
                vehicle.cost.maintenance_per_km or ZERO
            )
            cost_per_hour = vehicle.cost.fixed_cost_per_hour or ZERO
            fixed_route_cost = ZERO
        else:
            cost_per_km = ZERO
            cost_per_hour = ZERO
            fixed_route_cost = vehicle.cost.contract_price_brl or ZERO
        return OptimizationVehicle(
            id=vehicle.id,
            max_payload_kg=vehicle.max_payload_kg,
            max_volume_m3=vehicle.max_volume_m3,
            max_range_km=vehicle.max_range_km,
            refrigerated=vehicle.refrigerated,
            fixed_route_cost_brl=fixed_route_cost,
            cost_per_km_brl=cost_per_km,
            cost_per_hour_brl=cost_per_hour,
        )
