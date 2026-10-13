import uuid
from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.application.operations import (
    OperationDispatchError,
    OperationNotFoundError,
    OperationService,
    OperationUpdate,
    OperationView,
)
from fluxmed.domain.enums import OperationStatus, TrafficMode
from fluxmed.domain.operations import ImmutableOperationError, InvalidOperationSchedule

router = APIRouter(prefix="/operations", tags=["operations"])

CITY_PLACEHOLDER_NAME = "Santa Aurora"


class OperationCreateRequest(BaseModel):
    operation_date: date
    operation_start_time: time
    operation_end_time: time
    traffic_mode: TrafficMode = TrafficMode.AUTOMATIC


class OperationUpdateRequest(BaseModel):
    operation_date: date | None = None
    operation_start_time: time | None = None
    operation_end_time: time | None = None
    traffic_mode: TrafficMode | None = None


class OperationResponse(BaseModel):
    id: uuid.UUID
    operation_code: str
    operation_date: date
    operation_start_time: time
    operation_end_time: time
    traffic_mode: TrafficMode
    status: OperationStatus
    current_revision_number: int
    city_name: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class OperationListResponse(BaseModel):
    items: list[OperationResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


def _response(view: OperationView) -> OperationResponse:
    return OperationResponse(
        id=view.id,
        operation_code=view.operation_code,
        operation_date=view.operation_date,
        operation_start_time=view.operation_start_time,
        operation_end_time=view.operation_end_time,
        traffic_mode=view.traffic_mode,
        status=view.status,
        current_revision_number=view.current_revision_number,
        city_name=CITY_PLACEHOLDER_NAME,
        created_by_user_id=view.created_by_user_id,
        created_at=view.created_at,
        updated_at=view.updated_at,
    )


def _raise_operation_error(exc: Exception) -> None:
    if isinstance(exc, OperationNotFoundError):
        raise ApiError(status.HTTP_404_NOT_FOUND, "OPERATION_NOT_FOUND", "Operação não encontrada.")
    if isinstance(exc, InvalidOperationSchedule):
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_OPERATION_SCHEDULE",
            str(exc),
        )
    if isinstance(exc, ImmutableOperationError):
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "OPERATION_ALREADY_DISPATCHED",
            "Uma operação despachada não pode ser alterada.",
        )
    if isinstance(exc, OperationDispatchError):
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "OPERATION_DISPATCH_BLOCKED",
            str(exc),
        )
    raise exc


@router.get("", response_model=OperationListResponse)
def list_operations(
    session: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[OperationStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    sort: Annotated[
        str,
        Query(pattern="^(created_at|updated_at|operation_date|operation_code)$"),
    ] = "updated_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> OperationListResponse:
    del current_user
    result = OperationService(session).list(
        page=page,
        page_size=page_size,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        q=q,
        sort=sort,
        order=order,
    )
    return OperationListResponse(
        items=[_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )


@router.post("", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
def create_operation(
    payload: OperationCreateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> OperationResponse:
    try:
        view = OperationService(session).create(
            created_by_user_id=current_user.id,
            operation_date=payload.operation_date,
            operation_start_time=payload.operation_start_time,
            operation_end_time=payload.operation_end_time,
            traffic_mode=payload.traffic_mode,
        )
    except Exception as exc:
        _raise_operation_error(exc)
        raise
    return _response(view)


@router.get("/{operation_id}", response_model=OperationResponse)
def get_operation(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OperationResponse:
    del current_user
    try:
        view = OperationService(session).get(operation_id)
    except Exception as exc:
        _raise_operation_error(exc)
        raise
    return _response(view)


@router.patch("/{operation_id}", response_model=OperationResponse)
def update_operation(
    operation_id: uuid.UUID,
    payload: OperationUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> OperationResponse:
    del current_user
    try:
        view = OperationService(session).update(
            operation_id,
            OperationUpdate(
                operation_date=payload.operation_date,
                operation_start_time=payload.operation_start_time,
                operation_end_time=payload.operation_end_time,
                traffic_mode=payload.traffic_mode,
            ),
        )
    except Exception as exc:
        _raise_operation_error(exc)
        raise
    return _response(view)


@router.post("/{operation_id}/dispatch", response_model=OperationResponse)
def dispatch_operation(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OperationResponse:
    del current_user
    try:
        view = OperationService(session).dispatch(operation_id)
    except Exception as exc:
        _raise_operation_error(exc)
        raise
    return _response(view)
