import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fluxmed.application.preflight import PreflightService
from fluxmed.domain.enums import OperationStatus, OptimizationRunStatus
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.optimization_result import (
    OptimizationRunModel,
    OptimizationTraceEventModel,
)

ZERO = Decimal("0")
TERMINAL_RUN_STATUSES = {
    OptimizationRunStatus.COMPLETED,
    OptimizationRunStatus.FAILED,
    OptimizationRunStatus.CANCELLED,
    OptimizationRunStatus.INTERRUPTED,
}


class OptimizationLifecycleError(ValueError):
    pass


class OptimizationRunNotFoundError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class OptimizationRunView:
    id: uuid.UUID
    operation_id: uuid.UUID
    status: str
    random_seed: int
    generations_completed: int
    stop_reason: str
    validated: bool
    error_code: str | None
    error_message: str | None
    latest_sequence: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    cancel_requested_at: datetime | None


@dataclass(frozen=True, slots=True)
class OptimizationTraceEventView:
    id: uuid.UUID
    run_id: uuid.UUID
    sequence: int
    event_type: str
    generation: int | None
    elapsed_ms: int | None
    payload: dict[str, object]
    created_at: datetime


class OptimizationTraceService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def queue_operation(
        self,
        operation_id: uuid.UUID,
        *,
        random_seed: int | None,
    ) -> OptimizationRunView:
        operation = self._session.get(OperationModel, operation_id)
        if operation is None:
            raise OptimizationRunNotFoundError(operation_id)
        if operation.status is OperationStatus.DISPATCHED:
            raise OptimizationLifecycleError("Operação despachada não pode ser reotimizada.")
        if operation.status is OperationStatus.OPTIMIZING:
            raise OptimizationLifecycleError("Já existe uma otimização em andamento.")

        active_run = self._session.scalar(
            select(OptimizationRunModel.id)
            .where(
                OptimizationRunModel.operation_id == operation_id,
                OptimizationRunModel.status.in_(
                    [OptimizationRunStatus.QUEUED.value, OptimizationRunStatus.RUNNING.value]
                ),
            )
            .limit(1)
        )
        if active_run is not None:
            raise OptimizationLifecycleError("Já existe uma otimização ativa para esta operação.")

        preflight = PreflightService(self._session).validate_operation(operation_id)
        if not preflight.is_valid:
            codes = ", ".join(issue.code for issue in preflight.blocking_errors)
            raise OptimizationLifecycleError(f"Preflight inválido: {codes}.")

        delivery_count = self._session.scalar(
            select(func.count())
            .select_from(DeliveryModel)
            .where(DeliveryModel.operation_id == operation_id)
        )
        seed = random_seed if random_seed is not None else operation.id.int % 2_147_483_647
        previous_status = operation.status.value
        run = OptimizationRunModel(
            operation_id=operation.id,
            operation_revision_id=None,
            status=OptimizationRunStatus.QUEUED.value,
            random_seed=seed,
            generations_completed=0,
            stop_reason="QUEUED",
            validated=False,
            delivery_count=int(delivery_count or 0),
            vehicles_used=0,
            total_cost_brl=ZERO,
            distance_km=ZERO,
            makespan_minutes=ZERO,
            critical_delays=0,
            on_time_percentage=ZERO,
            average_weight_utilization_pct=ZERO,
            average_volume_utilization_pct=ZERO,
            pruning_counts={},
            previous_operation_status=previous_status,
            completed_at=None,
        )
        operation.status = OperationStatus.OPTIMIZING
        self._session.add(run)
        self._session.flush()
        return self.get_run(run.id)

    def mark_running(self, run_id: uuid.UUID) -> OptimizationRunView:
        run = self._require_run(run_id)
        if OptimizationRunStatus(run.status) in TERMINAL_RUN_STATUSES:
            return self.get_run(run.id)
        run.status = OptimizationRunStatus.RUNNING.value
        run.stop_reason = "RUNNING"
        run.started_at = run.started_at or datetime.now(UTC)
        run.error_code = None
        run.error_message = None
        self._session.flush()
        return self.get_run(run.id)

    def append_event(
        self,
        run_id: uuid.UUID,
        event_type: str,
        *,
        payload: dict[str, object] | None = None,
        generation: int | None = None,
        elapsed_ms: int | None = None,
    ) -> OptimizationTraceEventView:
        self._require_run(run_id)
        current = self._session.scalar(
            select(func.coalesce(func.max(OptimizationTraceEventModel.sequence), 0)).where(
                OptimizationTraceEventModel.optimization_run_id == run_id
            )
        )
        row = OptimizationTraceEventModel(
            optimization_run_id=run_id,
            sequence=int(current or 0) + 1,
            event_type=event_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            payload=payload or {},
        )
        self._session.add(row)
        self._session.flush()
        return self._event_view(row)

    def get_run(self, run_id: uuid.UUID) -> OptimizationRunView:
        run = self._require_run(run_id)
        latest_sequence = self._session.scalar(
            select(func.coalesce(func.max(OptimizationTraceEventModel.sequence), 0)).where(
                OptimizationTraceEventModel.optimization_run_id == run.id
            )
        )
        return OptimizationRunView(
            id=run.id,
            operation_id=run.operation_id,
            status=run.status,
            random_seed=run.random_seed,
            generations_completed=run.generations_completed,
            stop_reason=run.stop_reason,
            validated=run.validated,
            error_code=run.error_code,
            error_message=run.error_message,
            latest_sequence=int(latest_sequence or 0),
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            cancel_requested_at=run.cancel_requested_at,
        )

    def latest_for_operation(self, operation_id: uuid.UUID) -> OptimizationRunView:
        run_id = self._session.scalar(
            select(OptimizationRunModel.id)
            .where(OptimizationRunModel.operation_id == operation_id)
            .order_by(OptimizationRunModel.created_at.desc())
            .limit(1)
        )
        if run_id is None:
            raise OptimizationRunNotFoundError(operation_id)
        return self.get_run(run_id)

    def events(
        self,
        run_id: uuid.UUID,
        *,
        after_sequence: int = 0,
    ) -> tuple[OptimizationTraceEventView, ...]:
        self._require_run(run_id)
        rows = list(
            self._session.scalars(
                select(OptimizationTraceEventModel)
                .where(
                    OptimizationTraceEventModel.optimization_run_id == run_id,
                    OptimizationTraceEventModel.sequence > after_sequence,
                )
                .order_by(OptimizationTraceEventModel.sequence)
            )
        )
        return tuple(self._event_view(row) for row in rows)

    def request_cancel(self, run_id: uuid.UUID) -> OptimizationRunView:
        run = self._require_run(run_id)
        if OptimizationRunStatus(run.status) in TERMINAL_RUN_STATUSES:
            return self.get_run(run.id)
        run.cancel_requested_at = run.cancel_requested_at or datetime.now(UTC)
        run.stop_reason = "CANCEL_REQUESTED"
        self._session.flush()
        return self.get_run(run.id)

    def mark_cancelled(self, run_id: uuid.UUID, *, elapsed_ms: int | None = None) -> None:
        run = self._require_run(run_id)
        if OptimizationRunStatus(run.status) in TERMINAL_RUN_STATUSES:
            return
        run.status = OptimizationRunStatus.CANCELLED.value
        run.stop_reason = "CANCELLED_BY_USER"
        run.completed_at = datetime.now(UTC)
        run.error_code = None
        run.error_message = None
        self._restore_operation(run)
        self.append_event(
            run.id,
            "optimization_cancelled",
            payload={"status": OptimizationRunStatus.CANCELLED.value},
            elapsed_ms=elapsed_ms,
        )

    def mark_failed(
        self,
        run_id: uuid.UUID,
        *,
        error_code: str,
        error_message: str,
        elapsed_ms: int | None = None,
    ) -> None:
        run = self._require_run(run_id)
        if OptimizationRunStatus(run.status) in TERMINAL_RUN_STATUSES:
            return
        run.status = OptimizationRunStatus.FAILED.value
        run.stop_reason = "FAILED"
        run.error_code = error_code
        run.error_message = error_message[:1000]
        run.completed_at = datetime.now(UTC)
        self._restore_operation(run)
        self.append_event(
            run.id,
            "optimization_failed",
            payload={
                "status": OptimizationRunStatus.FAILED.value,
                "error_code": error_code,
                "message": run.error_message,
            },
            elapsed_ms=elapsed_ms,
        )

    def recover_interrupted_runs(self) -> int:
        runs = list(
            self._session.scalars(
                select(OptimizationRunModel).where(
                    OptimizationRunModel.status.in_(
                        [OptimizationRunStatus.QUEUED.value, OptimizationRunStatus.RUNNING.value]
                    )
                )
            )
        )
        for run in runs:
            run.status = OptimizationRunStatus.INTERRUPTED.value
            run.stop_reason = "PROCESS_INTERRUPTED"
            run.error_code = "PROCESS_INTERRUPTED"
            run.error_message = "A execução foi interrompida pelo encerramento do processo da API."
            run.completed_at = datetime.now(UTC)
            self._restore_operation(run)
            self.append_event(
                run.id,
                "optimization_failed",
                payload={
                    "status": OptimizationRunStatus.INTERRUPTED.value,
                    "error_code": "PROCESS_INTERRUPTED",
                    "message": run.error_message,
                },
            )
        self._session.flush()
        return len(runs)

    def cancellation_requested(self, run_id: uuid.UUID) -> bool:
        run = self._require_run(run_id)
        return run.cancel_requested_at is not None

    def _restore_operation(self, run: OptimizationRunModel) -> None:
        operation = self._session.get(OperationModel, run.operation_id)
        if operation is None or operation.status is not OperationStatus.OPTIMIZING:
            return
        previous = run.previous_operation_status
        try:
            operation.status = OperationStatus(previous) if previous else OperationStatus.READY
        except ValueError:
            operation.status = OperationStatus.READY

    def _require_run(self, run_id: uuid.UUID) -> OptimizationRunModel:
        run = self._session.get(OptimizationRunModel, run_id)
        if run is None:
            raise OptimizationRunNotFoundError(run_id)
        return run

    @staticmethod
    def _event_view(row: OptimizationTraceEventModel) -> OptimizationTraceEventView:
        return OptimizationTraceEventView(
            id=row.id,
            run_id=row.optimization_run_id,
            sequence=row.sequence,
            event_type=row.event_type,
            generation=row.generation,
            elapsed_ms=row.elapsed_ms,
            payload=row.payload,
            created_at=row.created_at,
        )
