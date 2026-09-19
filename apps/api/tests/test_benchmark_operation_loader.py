from datetime import date, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fluxmed.application.optimization.problem_inputs import operation_window


def test_operation_window_preserves_santa_aurora_timezone() -> None:
    timezone = ZoneInfo("America/Sao_Paulo")

    start_at, end_at = operation_window(
        operation_date=date(2026, 9, 15),
        operation_start_time=time(7, 30),
        operation_end_time=time(18, 0),
        timezone=timezone,
    )

    assert start_at.tzinfo == timezone
    assert end_at.tzinfo == timezone
    assert start_at.hour == 7
    assert end_at.hour == 18


def test_benchmark_loader_public_contract_shape() -> None:
    loaded = SimpleNamespace(
        operation_code="OP-20260915-001",
        traffic_mode=SimpleNamespace(value="AUTOMATIC"),
    )

    assert loaded.operation_code == "OP-20260915-001"
    assert loaded.traffic_mode.value == "AUTOMATIC"
