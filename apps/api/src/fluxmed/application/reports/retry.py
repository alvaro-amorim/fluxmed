import uuid
from copy import deepcopy
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from fluxmed.application.reports.service import (
    ReportInputError,
    ReportNotFoundError,
    ReportService,
    ReportView,
)
from fluxmed.infrastructure.models.report import ReportModel


class ReportRetryService:
    """Retry a failed artifact from its persisted snapshot without rewriting history."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def retry(self, report_id: uuid.UUID, *, actor_user_id: uuid.UUID) -> ReportView:
        source = self._session.get(ReportModel, report_id)
        if source is None:
            raise ReportNotFoundError(report_id)
        if source.status != "FAILED":
            raise ReportInputError("Apenas relatórios com falha podem ser gerados novamente.")

        retry = ReportModel(
            id=uuid.uuid4(),
            operation_id=source.operation_id,
            optimization_run_id=source.optimization_run_id,
            created_by_user_id=actor_user_id,
            report_type=source.report_type,
            format=source.format,
            status="QUEUED",
            snapshot=deepcopy(source.snapshot),
            created_at=datetime.now(UTC),
        )
        self._session.add(retry)
        self._session.flush()

        try:
            artifact, content_type, extension = ReportService._generate(
                retry.format,
                retry.snapshot,
            )
            retry.artifact = artifact
            retry.content_type = content_type
            retry.filename = f"fluxmed_retry_{retry.id}.{extension}"
            retry.status = "COMPLETED"
            retry.completed_at = datetime.now(UTC)
        except Exception as exc:  # pragma: no cover - defensive persistence boundary
            retry.status = "FAILED"
            retry.error_message = str(exc)[:2000]
            retry.completed_at = datetime.now(UTC)

        self._session.flush()
        return ReportView(
            id=retry.id,
            operation_id=retry.operation_id,
            optimization_run_id=retry.optimization_run_id,
            report_type=retry.report_type,
            format=retry.format,
            status=retry.status,
            filename=retry.filename,
            content_type=retry.content_type,
            error_message=retry.error_message,
            created_at=retry.created_at,
            completed_at=retry.completed_at,
        )
