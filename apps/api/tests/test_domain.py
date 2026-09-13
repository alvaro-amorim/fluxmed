from decimal import Decimal

import pytest

from fluxmed.domain import Money, OperationStatus, TrafficMode, UserRole


def test_core_enums_use_stable_api_values() -> None:
    assert UserRole.ADMIN.value == "ADMIN"
    assert OperationStatus.DISPATCHED.value == "DISPATCHED"
    assert TrafficMode.AUTOMATIC.value == "AUTOMATIC"


def test_money_rounds_half_up_to_cents() -> None:
    value = Money(Decimal("10.005"))

    assert value.amount == Decimal("10.01")


def test_money_arithmetic_preserves_decimal_precision() -> None:
    result = Money(Decimal("10.10")) + Money(Decimal("0.20"))

    assert result.amount == Decimal("10.30")


def test_money_rejects_non_decimal_inputs() -> None:
    with pytest.raises(TypeError):
        Money(10.0)  # type: ignore[arg-type]


def test_money_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError):
        Money(Decimal("NaN"))
