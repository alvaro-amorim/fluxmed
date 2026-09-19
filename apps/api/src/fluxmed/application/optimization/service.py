import uuid
from collections.abc import Callable
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.application.optimization.problem_inputs import (
    build_delivery_inputs,
    build_vehicle_input,
    operation_window,
    resolve_operation_timezone,
)
from fluxmed.application.optimization.results import (
    OptimizationResultService,
    OptimizationResultView,
)
from fluxmed.application.optimization.routing_matrix import RoutingMatrixBuilder
from fluxmed.application.optimization.team_assignment import TeamAssignmentError
from fluxmed.application.preflight import PreflightService
from fluxmed.application.resources import ResourceService
from fluxmed.domain.enums import OperationStatus, WorkerRole
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.optimization_result import OptimizationRunModel
from fluxmed.optimization import (
    GeneticOptimizer,
    GeneticOptimizerConfig,
    OptimizationProgress,
    OptimizationResult,
    SolutionValidator,
    ValidationResult,
)


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
    run_id: uuid.UUID
    result: OptimizationResult
    validation: ValidationResult
    persisted_result: OptimizationResultView


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

    @property
    def config(self) -> GeneticOptimizerConfig:
        return self._optimizer.config

    def optimize_operation(
        self,
        operation_id: uuid.UUID,
        *,
        random_seed: int | None = None,
        actor_user_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        on_progress: Callable[[OptimizationProgress], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> OperationOptimizationView:
        operation = self._session.get(OperationModel, operation_id)
        if operation is None:
            raise OptimizationOperationNotFoundError(operation_id)
        if operation.status is OperationStatus.DISPATCHED:
            raise OptimizationInputError("Operação despachada não pode ser reotimizada.")
        if operation.status is OperationStatus.OPTIMIZING and run_id is None:
            raise OptimizationInputError("Já existe uma otimização em andamento.")
        if run_id is not None:
            queued_run = self._session.get(OptimizationRunModel, run_id)
            if queued_run is None or queued_run.operation_id != operation.id:
                raise OptimizationInputError(
                    "Execução de otimização não pertence à operação informada."
                )

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
        deliveries = build_delivery_inputs(delivery_models)

        resource_view = ResourceService(self._session).get_operation_resources(operation_id)
        selected_ids = set(resource_view.selected_vehicle_ids)
        selected_worker_ids = set(resource_view.selected_worker_ids)
        selected_workers = [
            worker for worker in resource_view.workers if worker.id in selected_worker_ids
        ]
        helper_available = any(worker.role is WorkerRole.HELPER for worker in selected_workers)
        selected_vehicle_views = [
            vehicle for vehicle in resource_view.vehicles if vehicle.id in selected_ids
        ]
        vehicles = [
            build_vehicle_input(vehicle, helper_available=helper_available)
            for vehicle in selected_vehicle_views
        ]
        if not deliveries or not vehicles:
            raise OptimizationInputError("Otimização exige entregas e veículos selecionados.")

        matrix_builder = RoutingMatrixBuilder(self._session)
        matrix = matrix_builder.build(
            operation=operation,
            delivery_addresses={
                delivery.id: delivery.destination_address_id for delivery in delivery_models
            },
        )
        try:
            operation_timezone = resolve_operation_timezone(self._session, delivery_models)
        except ValueError as exc:
            raise OptimizationInputError(str(exc)) from exc
        operation_start_at, operation_end_at = operation_window(
            operation_date=operation.operation_date,
            operation_start_time=operation.operation_start_time,
            operation_end_time=operation.operation_end_time,
            timezone=operation_timezone,
        )
        seed = random_seed if random_seed is not None else operation.id.int % 2_147_483_647
        result = self._optimizer.optimize(
            deliveries=deliveries,
            vehicles=vehicles,
            travel_matrix=matrix,
            random_seed=seed,
            operation_start_at=operation_start_at,
            operation_end_at=operation_end_at,
            on_progress=on_progress,
            should_cancel=should_cancel,
        )
        validation = self._validator.validate(
            solution=result.best.solution,
            deliveries=deliveries,
            vehicles=vehicles,
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

        try:
            persisted = OptimizationResultService(self._session).persist(
                operation=operation,
                algorithm_result=result,
                validation=validation,
                deliveries=deliveries,
                delivery_models=delivery_models,
                vehicles=selected_vehicle_views,
                workers=selected_workers,
                actor_user_id=actor_user_id or operation.created_by_user_id,
                run_id=run_id,
            )
        except TeamAssignmentError as exc:
            raise OptimizationInputError(f"TEAM_INFEASIBLE: {exc}") from exc

        return OperationOptimizationView(
            operation_id=operation.id,
            random_seed=seed,
            run_id=persisted.run_id,
            result=result,
            validation=validation,
            persisted_result=persisted,
        )

