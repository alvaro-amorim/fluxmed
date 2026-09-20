import json
import time
import uuid
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.application.optimization.results import (
    OptimizationApprovalError,
    OptimizationResultNotFoundError,
    OptimizationResultService,
    TeamSimulationError,
)
from fluxmed.application.optimization.routing_matrix import OptimizationRoutingError
from fluxmed.application.optimization.runtime import optimization_run_coordinator
from fluxmed.application.optimization.service import (
    OptimizationInputError,
    OptimizationOperationNotFoundError,
    OptimizationValidationMismatchError,
)
from fluxmed.application.optimization.trace import (
    TERMINAL_RUN_STATUSES,
    OptimizationLifecycleError,
    OptimizationRunNotFoundError,
    OptimizationTraceEventView,
    OptimizationTraceService,
)
from fluxmed.infrastructure.database import SessionFactory

router = APIRouter(tags=["optimization"])


class OptimizeRequest(BaseModel):
    random_seed: int | None = None


class OptimizeAcceptedResponse(BaseModel):
    optimization_run_id: uuid.UUID
    status: str
    result_url: str
    status_url: str
    events_url: str


class OptimizationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class OptimizationTraceEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    sequence: int
    event_type: str
    generation: int | None
    elapsed_ms: int | None
    payload: dict[str, object]
    created_at: datetime


class WorkerResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    role: str


class VehicleResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plate: str
    type: str
    ownership_type: str


class RouteCostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    depreciation_brl: Decimal
    maintenance_brl: Decimal
    fixed_time_brl: Decimal
    fuel_brl: Decimal
    team_brl: Decimal
    contract_brl: Decimal
    total_brl: Decimal


class RouteTeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    primary_role: str | None
    primary_worker: WorkerResultResponse | None
    helper: WorkerResultResponse | None
    primary_included: bool
    helper_included: bool
    team_cost_brl: Decimal


class RouteStopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: int
    delivery_id: uuid.UUID
    delivery_code: str
    recipient_name: str
    address_label: str
    priority: str
    longitude: float
    latitude: float
    planned_arrival_at: datetime | None
    planned_departure_at: datetime | None
    time_window_start: datetime | None
    time_window_end: datetime | None
    time_window_policy: str
    service_time_minutes: int
    lateness_minutes: Decimal


class RouteResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    route_code: str
    vehicle: VehicleResultResponse
    team: RouteTeamResponse
    delivery_count: int
    distance_km: Decimal
    duration_minutes: Decimal
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    weight_utilization_pct: Decimal
    volume_utilization_pct: Decimal
    cost: RouteCostResponse
    geometry: dict[str, object]
    stops: tuple[RouteStopResponse, ...]


class OptimizationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: uuid.UUID
    operation_id: uuid.UUID
    revision_number: int
    status: str
    validated: bool
    random_seed: int
    generations_completed: int
    stop_reason: str
    delivery_count: int
    vehicles_used: int
    total_cost_brl: Decimal
    distance_km: Decimal
    makespan_minutes: Decimal
    critical_delays: int
    on_time_percentage: Decimal
    average_weight_utilization_pct: Decimal
    average_volume_utilization_pct: Decimal
    pruning_counts: dict[str, int]
    routes: tuple[RouteResultResponse, ...]


class TeamSimulationRequest(BaseModel):
    primary_worker_id: uuid.UUID | None = None
    helper_worker_id: uuid.UUID | None = None


class TeamSimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    valid: bool
    route_id: uuid.UUID
    team: RouteTeamResponse | None
    route_cost: RouteCostResponse | None
    issues: tuple[str, ...]


def _raise_optimization_error(exc: Exception) -> None:
    if isinstance(
        exc,
        (
            OptimizationOperationNotFoundError,
            OptimizationResultNotFoundError,
            OptimizationRunNotFoundError,
        ),
    ):
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "OPTIMIZATION_RESULT_NOT_FOUND",
            "Execução ou resultado de otimização não encontrado.",
        )
    if isinstance(exc, (OptimizationInputError, TeamSimulationError, OptimizationLifecycleError)):
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "OPTIMIZATION_INVALID", str(exc))
    if isinstance(exc, OptimizationApprovalError):
        raise ApiError(status.HTTP_409_CONFLICT, "OPTIMIZATION_APPROVAL_BLOCKED", str(exc))
    if isinstance(exc, OptimizationRoutingError):
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "ROUTING_UNAVAILABLE", str(exc))
    if isinstance(exc, OptimizationValidationMismatchError):
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "OPTIMIZER_VALIDATION_MISMATCH",
            "A validação independente divergiu do resultado do otimizador.",
        )
    raise exc


@router.post(
    "/operations/{operation_id}/optimize",
    response_model=OptimizeAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def optimize_operation(
    operation_id: uuid.UUID,
    payload: OptimizeRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> OptimizeAcceptedResponse:
    try:
        run = OptimizationTraceService(session).queue_operation(
            operation_id,
            random_seed=payload.random_seed,
        )
        # The background runner uses a separate SQLAlchemy session, so the queued
        # row and OPTIMIZING state must be visible before the thread starts.
        session.commit()
        optimization_run_coordinator.submit(run.id, current_user.id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return OptimizeAcceptedResponse(
        optimization_run_id=run.id,
        status=run.status,
        result_url=f"/api/v1/optimization-runs/{run.id}/result",
        status_url=f"/api/v1/optimization-runs/{run.id}",
        events_url=f"/api/v1/optimization-runs/{run.id}/events",
    )


@router.get(
    "/operations/{operation_id}/optimization-runs/latest-run",
    response_model=OptimizationRunResponse,
)
def latest_run(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OptimizationRunResponse:
    del current_user
    try:
        run = OptimizationTraceService(session).latest_for_operation(operation_id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return OptimizationRunResponse.model_validate(run)


@router.get("/optimization-runs/{run_id}", response_model=OptimizationRunResponse)
def get_run(
    run_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OptimizationRunResponse:
    del current_user
    try:
        run = OptimizationTraceService(session).get_run(run_id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return OptimizationRunResponse.model_validate(run)


@router.get(
    "/optimization-runs/{run_id}/trace",
    response_model=tuple[OptimizationTraceEventResponse, ...],
)
def get_trace(
    run_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> tuple[OptimizationTraceEventResponse, ...]:
    del current_user
    try:
        events = OptimizationTraceService(session).events(run_id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return tuple(OptimizationTraceEventResponse.model_validate(event) for event in events)


def _sse_event(event: OptimizationTraceEventView) -> str:
    data = OptimizationTraceEventResponse.model_validate(event).model_dump(mode="json")
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type}\n"
        f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )


@router.get("/optimization-runs/{run_id}/events")
def stream_events(
    run_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    after: int = 0,
) -> StreamingResponse:
    del current_user
    header_sequence = request.headers.get("last-event-id")
    try:
        cursor = max(after, int(header_sequence)) if header_sequence else max(0, after)
    except ValueError:
        cursor = max(0, after)

    # Fail before opening the stream when the run does not exist.
    probe = SessionFactory()
    try:
        OptimizationTraceService(probe).get_run(run_id)
    except Exception as exc:
        probe.close()
        _raise_optimization_error(exc)
        raise
    probe.close()

    def event_stream() -> Iterator[str]:
        nonlocal cursor
        idle_ticks = 0
        yield "retry: 1000\n\n"
        while True:
            poll = SessionFactory()
            try:
                service = OptimizationTraceService(poll)
                events = service.events(run_id, after_sequence=cursor)
                run = service.get_run(run_id)
            finally:
                poll.close()

            if events:
                idle_ticks = 0
                for event in events:
                    cursor = event.sequence
                    yield _sse_event(event)
            else:
                idle_ticks += 1
                if idle_ticks >= 40:
                    idle_ticks = 0
                    yield ": keep-alive\n\n"

            if run.status in {terminal.value for terminal in TERMINAL_RUN_STATUSES} and not events:
                return
            time.sleep(0.25)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/optimization-runs/{run_id}/cancel", response_model=OptimizationRunResponse)
def cancel_run(
    run_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OptimizationRunResponse:
    del current_user
    try:
        run = OptimizationTraceService(session).request_cancel(run_id)
        session.commit()
        optimization_run_coordinator.request_cancel(run_id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return OptimizationRunResponse.model_validate(run)


@router.get(
    "/operations/{operation_id}/optimization-runs/latest",
    response_model=OptimizationResultResponse,
)
def latest_result(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OptimizationResultResponse:
    del current_user
    try:
        result = OptimizationResultService(session).latest_for_operation(operation_id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return OptimizationResultResponse.model_validate(result)


@router.get(
    "/optimization-runs/{run_id}/result",
    response_model=OptimizationResultResponse,
)
def get_result(
    run_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OptimizationResultResponse:
    del current_user
    try:
        result = OptimizationResultService(session).get_result(run_id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return OptimizationResultResponse.model_validate(result)


@router.get("/routes/{route_id}", response_model=RouteResultResponse)
def get_route(
    route_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> RouteResultResponse:
    del current_user
    try:
        result = OptimizationResultService(session).get_route(route_id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return RouteResultResponse.model_validate(result)


@router.post(
    "/optimization-runs/{run_id}/approve",
    response_model=OptimizationResultResponse,
)
def approve_result(
    run_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OptimizationResultResponse:
    del current_user
    try:
        result = OptimizationResultService(session).approve(run_id)
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return OptimizationResultResponse.model_validate(result)


@router.post(
    "/routes/{route_id}/team-simulation",
    response_model=TeamSimulationResponse,
)
def simulate_team(
    route_id: uuid.UUID,
    payload: TeamSimulationRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> TeamSimulationResponse:
    del current_user
    try:
        result = OptimizationResultService(session).simulate_team(
            route_id,
            primary_worker_id=payload.primary_worker_id,
            helper_worker_id=payload.helper_worker_id,
        )
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return TeamSimulationResponse.model_validate(result)


@router.put("/routes/{route_id}/team", response_model=TeamSimulationResponse)
def apply_team(
    route_id: uuid.UUID,
    payload: TeamSimulationRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> TeamSimulationResponse:
    del current_user
    try:
        result = OptimizationResultService(session).simulate_team(
            route_id,
            primary_worker_id=payload.primary_worker_id,
            helper_worker_id=payload.helper_worker_id,
            apply=True,
        )
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return TeamSimulationResponse.model_validate(result)
