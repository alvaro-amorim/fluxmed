import uuid
from decimal import Decimal

from fastapi import APIRouter, status
from pydantic import BaseModel

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.application.preflight import (
    PreflightIssue,
    PreflightOperationNotFoundError,
    PreflightResult,
    PreflightService,
)

router = APIRouter(prefix="/operations", tags=["operations"])


class PreflightIssueResponse(BaseModel):
    code: str
    message: str
    related_delivery_ids: list[uuid.UUID]


class PreflightSummaryResponse(BaseModel):
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


class PreflightResponse(BaseModel):
    status: str
    blocking_errors: list[PreflightIssueResponse]
    warnings: list[PreflightIssueResponse]
    summary: PreflightSummaryResponse


def _issue_response(issue: PreflightIssue) -> PreflightIssueResponse:
    return PreflightIssueResponse(
        code=issue.code,
        message=issue.message,
        related_delivery_ids=list(issue.related_delivery_ids),
    )


def _response(result: PreflightResult) -> PreflightResponse:
    return PreflightResponse(
        status=result.status,
        blocking_errors=[_issue_response(issue) for issue in result.blocking_errors],
        warnings=[_issue_response(issue) for issue in result.warnings],
        summary=PreflightSummaryResponse(
            delivery_count=result.summary.delivery_count,
            vehicle_count=result.summary.vehicle_count,
            worker_count=result.summary.worker_count,
            critical_count=result.summary.critical_count,
            refrigerated_count=result.summary.refrigerated_count,
            hard_window_count=result.summary.hard_window_count,
            two_person_count=result.summary.two_person_count,
            total_weight_kg=result.summary.total_weight_kg,
            total_volume_m3=result.summary.total_volume_m3,
            operation_window_minutes=result.summary.operation_window_minutes,
        ),
    )


@router.post("/{operation_id}/validate", response_model=PreflightResponse)
def validate_operation(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> PreflightResponse:
    del current_user
    try:
        result = PreflightService(session).validate_operation(operation_id)
    except PreflightOperationNotFoundError as exc:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "OPERATION_NOT_FOUND",
            "Operação não encontrada.",
        ) from exc
    return _response(result)
