from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from fluxmed.domain.deliveries import (
    DeliveryValidationError,
    ServiceTimeEstimator,
    validate_delivery_values,
)
from fluxmed.domain.enums import BuildingType, HandlingRequirement


def test_delivery_invariants_reject_invalid_load_and_window() -> None:
    with pytest.raises(DeliveryValidationError):
        validate_delivery_values(
            package_count=0,
            total_weight_kg=Decimal("10"),
            total_volume_m3=Decimal("0.2"),
            time_window_start=None,
            time_window_end=None,
            service_time_minutes=10,
        )

    start = datetime.now(UTC)
    with pytest.raises(DeliveryValidationError):
        validate_delivery_values(
            package_count=1,
            total_weight_kg=Decimal("10"),
            total_volume_m3=Decimal("0.2"),
            time_window_start=start,
            time_window_end=start - timedelta(minutes=1),
            service_time_minutes=10,
        )


def test_service_time_estimator_is_deterministic_and_helper_reduces_time() -> None:
    estimator = ServiceTimeEstimator()
    kwargs = {
        "building_type": BuildingType.HOSPITAL,
        "package_count": 18,
        "total_weight_kg": Decimal("220"),
        "total_volume_m3": Decimal("1.8"),
        "handling_requirement": HandlingRequirement.TWO_PERSON,
    }

    first = estimator.estimate(**kwargs)
    second = estimator.estimate(**kwargs)

    assert first == second
    assert first.with_helper_minutes < first.solo_minutes
    assert first.selected_minutes == first.with_helper_minutes
