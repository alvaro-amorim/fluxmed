import uuid
from dataclasses import dataclass
from functools import partial

from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.application.optimization.evaluation import OperationalFitnessEvaluator
from fluxmed.application.optimization.problem_inputs import (
    build_delivery_inputs,
    build_vehicle_input,
    operation_window,
    resolve_operation_timezone,
)
from fluxmed.application.optimization.routing_matrix import RoutingMatrixBuilder
from fluxmed.application.preflight import PreflightService
from fluxmed.application.resources import ResourceService
from fluxmed.benchmarks.models import BenchmarkProblem
from fluxmed.domain.enums import TrafficMode, WorkerRole
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel


class BenchmarkOperationNotFoundError(LookupError):
    pass


class BenchmarkProblemLoadError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LoadedBenchmarkOperation:
    operation_id: uuid.UUID
    operation_code: str
    traffic_mode: TrafficMode
    problem: BenchmarkProblem


class SantaAuroraBenchmarkLoader:
    """Build the exact optimizer input for an existing operation without persisting changes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_by_code(
        self,
        operation_code: str,
        *,
        require_valid_preflight: bool = True,
    ) -> LoadedBenchmarkOperation:
        normalized = operation_code.strip()
        operation = self._session.scalar(
            select(OperationModel).where(OperationModel.operation_code == normalized)
        )
        if operation is None:
            raise BenchmarkOperationNotFoundError(normalized)
        return self._load(operation, require_valid_preflight=require_valid_preflight)

    def _load(
        self,
        operation: OperationModel,
        *,
        require_valid_preflight: bool,
    ) -> LoadedBenchmarkOperation:
        if require_valid_preflight:
            preflight = PreflightService(self._session).validate_operation(operation.id)
            if not preflight.is_valid:
                codes = ", ".join(issue.code for issue in preflight.blocking_errors)
                raise BenchmarkProblemLoadError(f"Preflight inválido: {codes}.")

        delivery_models = list(
            self._session.scalars(
                select(DeliveryModel)
                .where(DeliveryModel.operation_id == operation.id)
                .order_by(DeliveryModel.delivery_code)
            )
        )
        deliveries = build_delivery_inputs(delivery_models)

        resource_view = ResourceService(self._session).get_operation_resources(operation.id)
        selected_vehicle_ids = set(resource_view.selected_vehicle_ids)
        selected_worker_ids = set(resource_view.selected_worker_ids)
        selected_workers = [
            worker
            for worker in resource_view.workers
            if worker.id in selected_worker_ids
            and worker.id not in resource_view.unavailable_worker_ids
        ]
        helper_available = any(worker.role is WorkerRole.HELPER for worker in selected_workers)
        selected_vehicles = [
            vehicle for vehicle in resource_view.vehicles if vehicle.id in selected_vehicle_ids
        ]
        vehicles = [
            build_vehicle_input(vehicle, helper_available=helper_available)
            for vehicle in selected_vehicles
        ]
        if not deliveries or not vehicles:
            raise BenchmarkProblemLoadError(
                "Benchmark exige entregas e veículos selecionados na operação."
            )

        travel_matrix = RoutingMatrixBuilder(self._session).build(
            operation=operation,
            delivery_addresses={
                delivery.id: delivery.destination_address_id for delivery in delivery_models
            },
        )
        try:
            timezone = resolve_operation_timezone(self._session, delivery_models)
        except ValueError as exc:
            raise BenchmarkProblemLoadError(str(exc)) from exc
        operation_start_at, operation_end_at = operation_window(
            operation_date=operation.operation_date,
            operation_start_time=operation.operation_start_time,
            operation_end_time=operation.operation_end_time,
            timezone=timezone,
        )
        problem = BenchmarkProblem(
            scenario_name=operation.operation_code,
            deliveries=deliveries,
            vehicles=vehicles,
            travel_matrix=travel_matrix,
            operation_start_at=operation_start_at,
            operation_end_at=operation_end_at,
            fitness_evaluator_factory=partial(
                OperationalFitnessEvaluator,
                deliveries=deliveries,
                vehicles=selected_vehicles,
                workers=selected_workers,
            ),
        )
        return LoadedBenchmarkOperation(
            operation_id=operation.id,
            operation_code=operation.operation_code,
            traffic_mode=operation.traffic_mode,
            problem=problem,
        )
