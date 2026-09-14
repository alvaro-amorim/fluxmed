import uuid
from dataclasses import asdict
from datetime import datetime, time
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.application.routing import (
    InvalidRoadOverrideError,
    RoadOverrideConflictError,
    RoadOverrideNotFoundError,
    RoadOverrideService,
    RoadOverrideView,
    RoutingAddressNotFoundError,
    RoutingOperationNotFoundError,
    RoutingService,
    RoutingUnavailableError,
)
from fluxmed.domain.enums import (
    RoadOverrideDirectionScope,
    RoadOverrideType,
    RoutingAlgorithm,
    TrafficLevel,
    TrafficMode,
)

router = APIRouter(prefix="/operations", tags=["routing"])


class RoadOverrideCreateRequest(BaseModel):
    road_segment_id: uuid.UUID
    override_type: RoadOverrideType
    direction_scope: RoadOverrideDirectionScope = RoadOverrideDirectionScope.SEGMENT_DIRECTION
    traffic_level: TrafficLevel | None = None
    reason: str = Field(min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=500)


class RoadOverrideUpdateRequest(BaseModel):
    traffic_level: TrafficLevel | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=500)


class RoadOverrideResponse(BaseModel):
    id: uuid.UUID
    operation_id: uuid.UUID
    road_segment_id: uuid.UUID
    street_name: str
    override_type: RoadOverrideType
    direction_scope: RoadOverrideDirectionScope
    traffic_level: TrafficLevel | None
    reason: str
    notes: str | None
    is_bridge: bool
    bridge_name: str | None


class RoutePreviewRequest(BaseModel):
    destination_address_id: uuid.UUID
    departure_time: time | None = None
    algorithm: RoutingAlgorithm = RoutingAlgorithm.ASTAR


class RoutePreviewResponse(BaseModel):
    operation_id: uuid.UUID
    destination_address_id: uuid.UUID
    algorithm: RoutingAlgorithm
    traffic_mode: TrafficMode
    departure_at: datetime
    arrival_at: datetime
    distance_m: float
    travel_time_seconds: float
    time_bucket: str
    edge_ids: list[uuid.UUID]
    geometry: dict[str, Any]
    cache_hit: bool


def _override_response(view: RoadOverrideView) -> RoadOverrideResponse:
    return RoadOverrideResponse(**asdict(view))


def _raise_routing_error(exc: Exception) -> None:
    if isinstance(exc, RoutingOperationNotFoundError):
        raise ApiError(status.HTTP_404_NOT_FOUND, "OPERATION_NOT_FOUND", "Operação não encontrada.")
    if isinstance(exc, RoutingAddressNotFoundError):
        raise ApiError(status.HTTP_404_NOT_FOUND, "ADDRESS_NOT_FOUND", "Endereço não encontrado.")
    if isinstance(exc, RoadOverrideNotFoundError):
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "ROAD_OVERRIDE_NOT_FOUND",
            "Override viário não encontrado.",
        )
    if isinstance(exc, RoadOverrideConflictError):
        raise ApiError(status.HTTP_409_CONFLICT, "ROAD_OVERRIDE_CONFLICT", str(exc))
    if isinstance(exc, InvalidRoadOverrideError):
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_ROAD_OVERRIDE", str(exc))
    if isinstance(exc, RoutingUnavailableError):
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "ROUTE_NOT_AVAILABLE", str(exc))
    raise exc


@router.get("/{operation_id}/road-overrides", response_model=list[RoadOverrideResponse])
def list_road_overrides(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> list[RoadOverrideResponse]:
    del current_user
    try:
        items = RoadOverrideService(session).list(operation_id)
    except Exception as exc:
        _raise_routing_error(exc)
        raise
    return [_override_response(item) for item in items]


@router.post(
    "/{operation_id}/road-overrides",
    response_model=RoadOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_road_override(
    operation_id: uuid.UUID,
    payload: RoadOverrideCreateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> RoadOverrideResponse:
    del current_user
    try:
        view = RoadOverrideService(session).create(
            operation_id=operation_id,
            road_segment_id=payload.road_segment_id,
            override_type=payload.override_type,
            direction_scope=payload.direction_scope,
            traffic_level=payload.traffic_level,
            reason=payload.reason,
            notes=payload.notes,
        )
    except Exception as exc:
        _raise_routing_error(exc)
        raise
    return _override_response(view)


@router.patch(
    "/{operation_id}/road-overrides/{override_id}",
    response_model=RoadOverrideResponse,
)
def update_road_override(
    operation_id: uuid.UUID,
    override_id: uuid.UUID,
    payload: RoadOverrideUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> RoadOverrideResponse:
    del current_user
    try:
        view = RoadOverrideService(session).update(
            operation_id=operation_id,
            override_id=override_id,
            traffic_level=payload.traffic_level,
            reason=payload.reason,
            notes=payload.notes,
        )
    except Exception as exc:
        _raise_routing_error(exc)
        raise
    return _override_response(view)


@router.delete(
    "/{operation_id}/road-overrides/{override_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_road_override(
    operation_id: uuid.UUID,
    override_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> Response:
    del current_user
    try:
        RoadOverrideService(session).delete(operation_id, override_id)
    except Exception as exc:
        _raise_routing_error(exc)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{operation_id}/route-preview", response_model=RoutePreviewResponse)
def preview_route(
    operation_id: uuid.UUID,
    payload: RoutePreviewRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> RoutePreviewResponse:
    del current_user
    try:
        route = RoutingService(session).preview_depot_to_address(
            operation_id=operation_id,
            destination_address_id=payload.destination_address_id,
            departure_time=payload.departure_time,
            algorithm=payload.algorithm,
        )
    except Exception as exc:
        _raise_routing_error(exc)
        raise
    return RoutePreviewResponse(
        operation_id=route.operation_id,
        destination_address_id=route.destination_address_id,
        algorithm=route.algorithm,
        traffic_mode=route.traffic_mode,
        departure_at=route.departure_at,
        arrival_at=route.arrival_at,
        distance_m=round(route.distance_m, 2),
        travel_time_seconds=round(route.travel_time_seconds, 2),
        time_bucket=route.time_bucket,
        edge_ids=list(route.edge_ids),
        geometry=route.geometry,
        cache_hit=route.cache_hit,
    )
