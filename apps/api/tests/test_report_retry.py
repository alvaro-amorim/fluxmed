import uuid
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from fluxmed.application.reports.retry import ReportRetryService
from fluxmed.application.reports.service import ReportInputError, ReportService
from fluxmed.infrastructure.models.report import ReportModel


def _failed_report() -> ReportModel:
    return ReportModel(
        id=uuid.uuid4(),
        operation_id=uuid.uuid4(),
        optimization_run_id=uuid.uuid4(),
        created_by_user_id=uuid.uuid4(),
        report_type="DAILY_OPERATION",
        format="PDF",
        status="FAILED",
        snapshot={
            "snapshot_version": "report-v1",
            "operation": {"operation_code": "OP-20260915-001", "revision_number": 2},
            "optimization": {"run_id": "original-run"},
        },
        error_message="falha simulada",
        created_at=datetime(2026, 9, 15, 14, 0, tzinfo=UTC),
    )


def test_retry_reuses_exact_persisted_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    report = _failed_report()
    original_snapshot = deepcopy(report.snapshot)
    session = MagicMock(spec=Session)
    session.get.return_value = report
    received: list[dict[str, object]] = []

    def fake_generate(
        report_format: str,
        snapshot: dict[str, object],
    ) -> tuple[bytes, str, str]:
        assert report_format == "PDF"
        received.append(deepcopy(snapshot))
        return b"%PDF-retried", "application/pdf", "pdf"

    monkeypatch.setattr(ReportService, "_generate", staticmethod(fake_generate))

    retried = ReportRetryService(session).retry(report.id)

    assert received == [original_snapshot]
    assert report.snapshot == original_snapshot
    assert report.optimization_run_id == retried.optimization_run_id
    assert report.status == "COMPLETED"
    assert report.error_message is None
    assert report.artifact == b"%PDF-retried"
    assert report.filename == f"fluxmed_retry_{report.id}.pdf"
    assert session.flush.call_count == 2


def test_retry_rejects_report_that_did_not_fail() -> None:
    report = _failed_report()
    report.status = "COMPLETED"
    session = MagicMock(spec=Session)
    session.get.return_value = report

    with pytest.raises(ReportInputError, match="Apenas relatórios com falha"):
        ReportRetryService(session).retry(report.id)
