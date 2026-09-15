import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fluxmed.application.optimization.routing_matrix import (
    OptimizationRoutingError,
    RoutingMatrixBuilder,
)
from fluxmed.application.optimization.service import OptimizationService
from fluxmed.application.optimization.trace import OptimizationTraceService
from fluxmed.domain.enums import OptimizationRunStatus
from fluxmed.infrastructure.database import SessionFactory
from fluxmed.infrastructure.models.city import AddressModel
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.optimization_result import OptimizationRunModel
from fluxmed.optimization import (
    FitnessVector,
    OptimizationCancelled,
    OptimizationProgress,
)


class OptimizationRunCoordinator:
    """Small in-process runner for V1.

    Runs are persisted before submission. If the API process dies, startup recovery
    marks QUEUED/RUNNING rows as INTERRUPTED instead of pretending they completed.
    """

    def __init__(self, *, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="fluxmed-optimization",
        )
        self._lock = threading.Lock()
        self._cancellations: dict[uuid.UUID, threading.Event] = {}
        self._futures: dict[uuid.UUID, Future[None]] = {}

    def submit(self, run_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        with self._lock:
            existing = self._futures.get(run_id)
            if existing is not None and not existing.done():
                return
            cancellation = threading.Event()
            self._cancellations[run_id] = cancellation
            future = self._executor.submit(self._execute, run_id, actor_user_id, cancellation)
            self._futures[run_id] = future
            future.add_done_callback(lambda _future: self._forget(run_id))

    def request_cancel(self, run_id: uuid.UUID) -> None:
        with self._lock:
            cancellation = self._cancellations.get(run_id)
            if cancellation is not None:
                cancellation.set()

    def _forget(self, run_id: uuid.UUID) -> None:
        with self._lock:
            self._cancellations.pop(run_id, None)
            self._futures.pop(run_id, None)

    def _execute(
        self,
        run_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        cancellation: threading.Event,
    ) -> None:
        session = SessionFactory()
        started_monotonic = time.monotonic()
        try:
            trace = OptimizationTraceService(session)
            run_view = trace.mark_running(run_id)
            session.commit()
            if run_view.status in {
                OptimizationRunStatus.CANCELLED.value,
                OptimizationRunStatus.FAILED.value,
                OptimizationRunStatus.INTERRUPTED.value,
                OptimizationRunStatus.COMPLETED.value,
            }:
                return
            if cancellation.is_set() or self._db_cancel_requested(session, run_id):
                trace.mark_cancelled(run_id, elapsed_ms=self._elapsed_ms(started_monotonic))
                session.commit()
                return

            run = session.get(OptimizationRunModel, run_id)
            if run is None:
                return
            operation = session.get(OperationModel, run.operation_id)
            if operation is None:
                trace.mark_failed(
                    run_id,
                    error_code="OPERATION_NOT_FOUND",
                    error_message="Operação da execução não foi encontrada.",
                    elapsed_ms=self._elapsed_ms(started_monotonic),
                )
                session.commit()
                return

            delivery_rows = session.execute(
                select(
                    DeliveryModel.id,
                    DeliveryModel.delivery_code,
                    DeliveryModel.destination_address_id,
                    func.ST_X(AddressModel.location),
                    func.ST_Y(AddressModel.location),
                )
                .join(AddressModel, AddressModel.id == DeliveryModel.destination_address_id)
                .where(DeliveryModel.operation_id == operation.id)
                .order_by(DeliveryModel.delivery_code)
            ).all()
            delivery_addresses = {
                delivery_id: address_id
                for delivery_id, _code, address_id, _longitude, _latitude in delivery_rows
            }
            delivery_points = {
                delivery_id: {
                    "delivery_id": str(delivery_id),
                    "delivery_code": code,
                    "longitude": float(longitude),
                    "latitude": float(latitude),
                }
                for delivery_id, code, _address_id, longitude, latitude in delivery_rows
            }
            optimizer = OptimizationService(session)
            config = optimizer.config
            trace.append_event(
                run_id,
                "optimization_started",
                payload={
                    "status": OptimizationRunStatus.RUNNING.value,
                    "random_seed": run.random_seed,
                    "delivery_count": len(delivery_rows),
                    "population_size": config.population_size,
                    "max_generations": config.max_generations,
                    "deliveries": list(delivery_points.values()),
                },
                elapsed_ms=self._elapsed_ms(started_monotonic),
            )
            session.commit()

            previous_best: FitnessVector | None = None
            previous_assignments: dict[uuid.UUID, tuple[uuid.UUID, int]] = {}
            geometry_builder = RoutingMatrixBuilder(session)

            def should_cancel() -> bool:
                return cancellation.is_set() or self._db_cancel_requested(session, run_id)

            def on_progress(progress: OptimizationProgress) -> None:
                nonlocal previous_assignments, previous_best
                elapsed_ms = self._elapsed_ms(started_monotonic)
                current_run = session.get(OptimizationRunModel, run_id)
                if current_run is not None:
                    current_run.generations_completed = progress.generation
                    current_run.pruning_counts = progress.pruning_counts
                trace.append_event(
                    run_id,
                    "generation_snapshot",
                    generation=progress.generation,
                    elapsed_ms=elapsed_ms,
                    payload=self._generation_payload(progress),
                )
                if progress.improved:
                    routes = self._routes_payload(
                        progress,
                        operation=operation,
                        delivery_addresses=delivery_addresses,
                        delivery_points=delivery_points,
                        geometry_builder=geometry_builder,
                    )
                    trace.append_event(
                        run_id,
                        "best_solution_updated",
                        generation=progress.generation,
                        elapsed_ms=elapsed_ms,
                        payload={
                            **self._generation_payload(progress),
                            "selection_reasons": self._selection_reasons(
                                previous_best,
                                progress.best.fitness,
                            ),
                            "routes": routes,
                        },
                    )
                    route_changes, current_assignments = self._route_assignment_changes(
                        previous_assignments,
                        progress,
                    )
                    if route_changes:
                        trace.append_event(
                            run_id,
                            "route_assignment_change",
                            generation=progress.generation,
                            elapsed_ms=elapsed_ms,
                            payload={"changes": route_changes},
                        )
                    previous_assignments = current_assignments
                    previous_best = progress.best.fitness
                if progress.generation == 0 or progress.generation % 10 == 0:
                    trace.append_event(
                        run_id,
                        "pruning_summary",
                        generation=progress.generation,
                        elapsed_ms=elapsed_ms,
                        payload={"counts": progress.pruning_counts},
                    )
                session.commit()

            result_view = optimizer.optimize_operation(
                operation.id,
                random_seed=run.random_seed,
                actor_user_id=actor_user_id,
                run_id=run_id,
                on_progress=on_progress,
                should_cancel=should_cancel,
            )

            elapsed_ms = self._elapsed_ms(started_monotonic)
            trace = OptimizationTraceService(session)
            trace.append_event(
                run_id,
                "pruning_summary",
                generation=result_view.result.generations_completed,
                elapsed_ms=elapsed_ms,
                payload={"counts": result_view.result.pruning_counts, "final": True},
            )
            final_comparison: dict[str, object] = {
                "final": self._fitness_payload(result_view.result.best.fitness),
                "baselines": [
                    {
                        "name": baseline.name,
                        **self._fitness_payload(baseline.fitness),
                    }
                    for baseline in result_view.result.baselines
                ],
            }
            trace.append_event(
                run_id,
                "final_comparison",
                generation=result_view.result.generations_completed,
                elapsed_ms=elapsed_ms,
                payload=final_comparison,
            )
            trace.append_event(
                run_id,
                "optimization_completed",
                generation=result_view.result.generations_completed,
                elapsed_ms=elapsed_ms,
                payload={
                    "status": OptimizationRunStatus.COMPLETED.value,
                    "validated": result_view.validation.valid,
                    "stop_reason": result_view.result.stop_reason,
                    **final_comparison,
                    "pruning_counts": result_view.result.pruning_counts,
                },
            )
            session.commit()
        except OptimizationCancelled:
            session.rollback()
            trace = OptimizationTraceService(session)
            trace.mark_cancelled(run_id, elapsed_ms=self._elapsed_ms(started_monotonic))
            session.commit()
        except Exception as exc:
            session.rollback()
            trace = OptimizationTraceService(session)
            try:
                trace.mark_failed(
                    run_id,
                    error_code=type(exc).__name__.upper(),
                    error_message=str(exc) or "Falha inesperada durante a otimização.",
                    elapsed_ms=self._elapsed_ms(started_monotonic),
                )
                session.commit()
            except Exception:
                session.rollback()
        finally:
            session.close()

    @staticmethod
    def _elapsed_ms(started_monotonic: float) -> int:
        return max(0, int((time.monotonic() - started_monotonic) * 1000))

    @staticmethod
    def _db_cancel_requested(session: Session, run_id: uuid.UUID) -> bool:
        value = session.scalar(
            select(OptimizationRunModel.cancel_requested_at).where(
                OptimizationRunModel.id == run_id
            )
        )
        return value is not None

    @staticmethod
    def _generation_payload(progress: OptimizationProgress) -> dict[str, object]:
        return {
            "generation": progress.generation,
            **OptimizationRunCoordinator._fitness_payload(progress.best.fitness),
            "diversity_ratio": progress.diversity_ratio,
            "mutation_rate": progress.effective_mutation_rate,
            "immigrants_added": progress.immigrants_added,
            "pruning_counts": progress.pruning_counts,
        }

    @staticmethod
    def _fitness_payload(fitness: FitnessVector) -> dict[str, object]:
        return {
            "feasible": fitness.feasible,
            "hard_violations": fitness.hard_violations,
            "service_penalty": str(fitness.service_penalty),
            "critical_risk": str(fitness.critical_risk),
            "cost_brl": str(fitness.total_cost_brl),
            "makespan_minutes": str(fitness.makespan_minutes),
            "travel_minutes": str(fitness.travel_minutes),
            "distance_km": str(fitness.distance_km),
            "vehicles_used": fitness.vehicles_used,
        }

    @staticmethod
    def _selection_reasons(
        previous: FitnessVector | None,
        current: FitnessVector,
    ) -> list[dict[str, object]]:
        if previous is None:
            return [{"code": "INITIAL_BEST", "metric": "fitness"}]
        reasons: list[dict[str, object]] = []
        OptimizationRunCoordinator._append_reason(
            reasons, "hard_violations", previous.hard_violations, current.hard_violations
        )
        OptimizationRunCoordinator._append_reason(
            reasons, "service_penalty", previous.service_penalty, current.service_penalty
        )
        OptimizationRunCoordinator._append_reason(
            reasons, "critical_risk", previous.critical_risk, current.critical_risk
        )
        OptimizationRunCoordinator._append_reason(
            reasons, "cost_brl", previous.total_cost_brl, current.total_cost_brl
        )
        OptimizationRunCoordinator._append_reason(
            reasons, "makespan_minutes", previous.makespan_minutes, current.makespan_minutes
        )
        OptimizationRunCoordinator._append_reason(
            reasons, "travel_minutes", previous.travel_minutes, current.travel_minutes
        )
        OptimizationRunCoordinator._append_reason(
            reasons, "distance_km", previous.distance_km, current.distance_km
        )
        OptimizationRunCoordinator._append_reason(
            reasons, "vehicles_used", previous.vehicles_used, current.vehicles_used
        )
        return reasons or [{"code": "LEXICOGRAPHIC_IMPROVEMENT", "metric": "fitness"}]

    @staticmethod
    def _append_reason(
        reasons: list[dict[str, object]],
        metric: str,
        before: int | Decimal,
        after: int | Decimal,
    ) -> None:
        if after >= before:
            return
        reasons.append(
            {
                "code": "METRIC_IMPROVED",
                "metric": metric,
                "before": str(before),
                "after": str(after),
            }
        )

    @staticmethod
    def _route_assignment_changes(
        previous: dict[uuid.UUID, tuple[uuid.UUID, int]],
        progress: OptimizationProgress,
    ) -> tuple[
        list[dict[str, object]],
        dict[uuid.UUID, tuple[uuid.UUID, int]],
    ]:
        current: dict[uuid.UUID, tuple[uuid.UUID, int]] = {}
        for route in progress.best.solution.routes:
            for position, delivery_id in enumerate(route.delivery_ids, start=1):
                current[delivery_id] = (route.vehicle_id, position)

        if not previous:
            return [], current

        changes: list[dict[str, object]] = []
        for delivery_id, (vehicle_id, position) in current.items():
            old = previous.get(delivery_id)
            if old is None or old == (vehicle_id, position):
                continue
            previous_vehicle_id, previous_position = old
            changes.append(
                {
                    "delivery_id": str(delivery_id),
                    "from_vehicle_id": str(previous_vehicle_id),
                    "to_vehicle_id": str(vehicle_id),
                    "from_position": previous_position,
                    "to_position": position,
                }
            )
        return changes, current

    @staticmethod
    def _routes_payload(
        progress: OptimizationProgress,
        *,
        operation: OperationModel,
        delivery_addresses: dict[uuid.UUID, uuid.UUID],
        delivery_points: dict[uuid.UUID, dict[str, object]],
        geometry_builder: RoutingMatrixBuilder,
    ) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for route_index, route in enumerate(progress.best.solution.routes, start=1):
            try:
                geometry: dict[str, object] | None = geometry_builder.build_route_geometry(
                    operation=operation,
                    delivery_addresses=delivery_addresses,
                    delivery_ids=route.delivery_ids,
                )
            except OptimizationRoutingError:
                geometry = None
            stops = []
            for sequence, delivery_id in enumerate(route.delivery_ids, start=1):
                point = delivery_points.get(delivery_id)
                if point is None:
                    continue
                stops.append({**point, "sequence": sequence})
            payload.append(
                {
                    "route_code": f"R-{route_index:02d}",
                    "vehicle_id": str(route.vehicle_id),
                    "delivery_ids": [str(delivery_id) for delivery_id in route.delivery_ids],
                    "distance_km": str(route.distance_km),
                    "duration_minutes": str(route.total_duration_minutes),
                    "geometry": geometry,
                    "stops": stops,
                }
            )
        return payload


optimization_run_coordinator = OptimizationRunCoordinator()
