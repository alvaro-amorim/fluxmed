import uuid
from datetime import date, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from fluxmed.application.optimization.problem_inputs import (
    build_delivery_inputs,
    operation_window,
)
from fluxmed.domain.enums import (
    DeliveryPriority,
    HandlingRequirement,
    TemperatureClass,
    TimeWindowPolicy,
)
from fluxmed.infrastructure.models.delivery import DeliveryModel


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


def test_delivery_input_mapping_matches_production_fields() -> None:
    model = DeliveryModel(
        id=uuid.UUID(int=1),
        total_weight_kg=Decimal("42.500"),
        total_volume_m3=Decimal("0.7500"),
        service_time_minutes=12,
        priority=DeliveryPriority.HIGH,
        temperature_class=TemperatureClass.REFRIGERATED,
        handling_requirement=HandlingRequirement.TWO_PERSON,
        time_window_start=None,
        time_window_end=None,
        time_window_policy=TimeWindowPolicy.SOFT,
    )

    [delivery] = build_delivery_inputs([model])

    assert delivery.id == model.id
    assert delivery.weight_kg == Decimal("42.500")
    assert delivery.volume_m3 == Decimal("0.7500")
    assert delivery.service_minutes == 12
    assert delivery.priority is DeliveryPriority.HIGH
    assert delivery.temperature_class is TemperatureClass.REFRIGERATED
    assert delivery.handling_requirement is HandlingRequirement.TWO_PERSON
