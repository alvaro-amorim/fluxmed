import uuid
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from fluxmed.application.reports.retry import ReportRetryService
from fluxmed.application.reports.service import (
    REPORT_GENERATION_FAILED_MESSAGE,
    ReportInputError,
    ReportService,
)
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


def test_retry_reuses_snapshot_and_preserves_failed_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _failed_report()
    original_snapshot = deepcopy(source.snapshot)
    actor_user_id = uuid.uuid4()
    session = MagicMock(spec=Session)
    session.get.return_value = source
    received: list[dict[str, object]] = []

    def fake_generate(
        report_format: str,
        snapshot: dict[str, object],
    ) -> tuple[bytes, str, str]:
        assert report_format == "PDF"
        received.append(deepcopy(snapshot))
        return b"%PDF-retried", "application/pdf", "pdf"

    monkeypatch.setattr(ReportService, "_generate", staticmethod(fake_generate))

    retried = ReportRetryService(session).retry(source.id, actor_user_id=actor_user_id)
    retry_model = session.add.call_args.args[0]

    assert isinstance(retry_model, ReportModel)
    assert received == [original_snapshot]
    assert retry_model.snapshot == original_snapshot
    assert retry_model.snapshot is not source.snapshot
    assert retry_model.optimization_run_id == source.optimization_run_id
    assert retry_model.optimization_run_id == retried.optimization_run_id
    assert retry_model.created_by_user_id == actor_user_id
    assert retry_model.status == "COMPLETED"
    assert retry_model.artifact == b"%PDF-retried"
    assert retry_model.filename == f"fluxmed_retry_{retry_model.id}.pdf"
    assert source.status == "FAILED"
    assert source.error_message == "falha simulada"
    assert source.snapshot == original_snapshot
    assert session.flush.call_count == 2


def test_retry_rejects_report_that_did_not_fail() -> None:
    report = _failed_report()
    report.status = "COMPLETED"
    session = MagicMock(spec=Session)
    session.get.return_value = report

    with pytest.raises(ReportInputError, match="Apenas relatórios com falha"):
        ReportRetryService(session).retry(report.id, actor_user_id=uuid.uuid4())


def test_retry_generation_failure_is_sanitized_and_preserves_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _failed_report()
    original_snapshot = deepcopy(source.snapshot)
    session = MagicMock(spec=Session)
    session.get.return_value = source

    def failing_generate(
        _report_format: str,
        _snapshot: dict[str, object],
    ) -> tuple[bytes, str, str]:
        raise RuntimeError("secret=/tmp/private-report-path")

    monkeypatch.setattr(ReportService, "_generate", staticmethod(failing_generate))

    retried = ReportRetryService(session).retry(
        source.id,
        actor_user_id=uuid.uuid4(),
    )
    retry_model = session.add.call_args.args[0]

    assert isinstance(retry_model, ReportModel)
    assert retried.status == "FAILED"
    assert retry_model.status == "FAILED"
    assert retry_model.error_message == REPORT_GENERATION_FAILED_MESSAGE
    assert "secret" not in retry_model.error_message
    assert retry_model.artifact is None
    assert retry_model.filename is None
    assert source.status == "FAILED"
    assert source.error_message == "falha simulada"
    assert source.snapshot == original_snapshot
