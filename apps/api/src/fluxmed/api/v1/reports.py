import uuid
from datetime import datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.application.reports import (
    ReportInputError,
    ReportNotFoundError,
    ReportService,
    ReportView,
)
from fluxmed.application.reports.retry import ReportRetryService

router = APIRouter(tags=["reports"])


class ReportCreateRequest(BaseModel):
    report_type: str = "DAILY_OPERATION"
    format: str


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    operation_id: uuid.UUID
    optimization_run_id: uuid.UUID
    report_type: str
    format: str
    status: str
    filename: str | None
    content_type: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    download_url: str | None = None


class ReportListResponse(BaseModel):
    items: list[ReportResponse]


def _response(view: ReportView) -> ReportResponse:
    return ReportResponse(
        id=view.id,
        operation_id=view.operation_id,
        optimization_run_id=view.optimization_run_id,
        report_type=view.report_type,
        format=view.format,
        status=view.status,
        filename=view.filename,
        content_type=view.content_type,
        error_message=view.error_message,
        created_at=view.created_at,
        completed_at=view.completed_at,
        download_url=(
            f"/api/v1/reports/{view.id}/download" if view.status == "COMPLETED" else None
        ),
    )


def _raise_report_error(exc: Exception) -> None:
    if isinstance(exc, ReportNotFoundError):
        raise ApiError(status.HTTP_404_NOT_FOUND, "REPORT_NOT_FOUND", "Relatório não encontrado.")
    if isinstance(exc, ReportInputError):
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "REPORT_INVALID", str(exc))
    raise exc


@router.get("/reports", response_model=ReportListResponse)
def list_reports(
    session: DbSession,
    _current_user: CurrentUser,
    operation_id: uuid.UUID | None = None,
) -> ReportListResponse:
    items = [_response(item) for item in ReportService(session).list(operation_id)]
    return ReportListResponse(items=items)


@router.post(
    "/operations/{operation_id}/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_report(
    operation_id: uuid.UUID,
    payload: ReportCreateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ReportResponse:
    try:
        report = ReportService(session).create(
            operation_id,
            report_type=payload.report_type,
            report_format=payload.format,
            actor_user_id=current_user.id,
        )
    except Exception as exc:
        _raise_report_error(exc)
        raise
    return _response(report)


@router.post(
    "/reports/{report_id}/retry",
    response_model=ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_report(
    report_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> ReportResponse:
    try:
        report = ReportRetryService(session).retry(report_id, actor_user_id=current_user.id)
    except Exception as exc:
        _raise_report_error(exc)
        raise
    return _response(report)


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: uuid.UUID,
    session: DbSession,
    _current_user: CurrentUser,
) -> ReportResponse:
    try:
        return _response(ReportService(session).get(report_id))
    except Exception as exc:
        _raise_report_error(exc)
        raise


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    session: DbSession,
    _current_user: CurrentUser,
) -> Response:
    try:
        report, artifact = ReportService(session).download(report_id)
    except Exception as exc:
        _raise_report_error(exc)
        raise
    filename = report.filename or f"fluxmed_report_{report.id}.{report.format.lower()}"
    return Response(
        content=artifact,
        media_type=report.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
