import uuid
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
    """Retry a failed artifact using the exact persisted report snapshot."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def retry(self, report_id: uuid.UUID) -> ReportView:
        report = self._session.get(ReportModel, report_id)
        if report is None:
            raise ReportNotFoundError(report_id)
        if report.status != "FAILED":
            raise ReportInputError("Apenas relatórios com falha podem ser gerados novamente.")

        report.status = "QUEUED"
        report.error_message = None
        report.completed_at = None
        report.artifact = None
        report.filename = None
        report.content_type = None
        self._session.flush()

        try:
            artifact, content_type, extension = ReportService._generate(report.format, report.snapshot)
            report.artifact = artifact
            report.content_type = content_type
            report.filename = f"fluxmed_retry_{report.id}.{extension}"
            report.status = "COMPLETED"
            report.completed_at = datetime.now(UTC)
        except Exception as exc:  # pragma: no cover - defensive persistence boundary
            report.status = "FAILED"
            report.error_message = str(exc)[:2000]
            report.completed_at = datetime.now(UTC)

        self._session.flush()
        return ReportService(self._session).get(report.id)
