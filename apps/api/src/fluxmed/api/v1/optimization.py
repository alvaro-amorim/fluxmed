import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, status
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
from fluxmed.application.optimization.service import (
    OptimizationInputError,
    OptimizationOperationNotFoundError,
    OptimizationService,
    OptimizationValidationMismatchError,
)

router = APIRouter(tags=["optimization"])


class OptimizeRequest(BaseModel):
    random_seed: int | None = None


class OptimizeAcceptedResponse(BaseModel):
    optimization_run_id: uuid.UUID
    status: str
    result_url: str


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
    if isinstance(exc, (OptimizationOperationNotFoundError, OptimizationResultNotFoundError)):
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "OPTIMIZATION_RESULT_NOT_FOUND",
            "Resultado de otimização não encontrado.",
        )
    if isinstance(exc, (OptimizationInputError, TeamSimulationError)):
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
        view = OptimizationService(session).optimize_operation(
            operation_id,
            random_seed=payload.random_seed,
            actor_user_id=current_user.id,
        )
    except Exception as exc:
        _raise_optimization_error(exc)
        raise
    return OptimizeAcceptedResponse(
        optimization_run_id=view.run_id,
        status="COMPLETED",
        result_url=f"/api/v1/optimization-runs/{view.run_id}/result",
    )


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
