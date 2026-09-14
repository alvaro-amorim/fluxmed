import uuid
from datetime import time
from decimal import Decimal

from fluxmed.application.preflight import (
    PreflightDelivery,
    PreflightOperation,
    PreflightValidator,
    PreflightVehicle,
    PreflightWorker,
)
from fluxmed.domain.enums import (
    DeliveryPriority,
    HandlingRequirement,
    HelperPolicy,
    TemperatureClass,
    TimeWindowPolicy,
    VehicleType,
    WorkerRole,
)


def delivery(
    *,
    temperature: TemperatureClass = TemperatureClass.AMBIENT,
    handling: HandlingRequirement = HandlingRequirement.STANDARD,
    weight: str = "10",
    volume: str = "0.1",
    range_km: str | None = "10",
    address_valid: bool = True,
) -> PreflightDelivery:
    return PreflightDelivery(
        id=uuid.uuid4(),
        delivery_code="DLV-TEST-001",
        weight_kg=Decimal(weight),
        volume_m3=Decimal(volume),
        priority=DeliveryPriority.NORMAL,
        temperature_class=temperature,
        handling_requirement=handling,
        time_window_policy=TimeWindowPolicy.SOFT,
        address_valid=address_valid,
        minimum_roundtrip_km=Decimal(range_km) if range_km is not None else None,
    )


def vehicle(
    *,
    refrigerated: bool = False,
    payload: str = "100",
    volume: str = "1",
    range_km: str = "100",
    helper_policy: HelperPolicy = HelperPolicy.OPTIONAL,
    vehicle_type: VehicleType = VehicleType.CARGO_VAN,
    driver_included: bool = False,
    helper_included: bool = False,
) -> PreflightVehicle:
    return PreflightVehicle(
        id=uuid.uuid4(),
        plate="ABC1D23",
        type=vehicle_type,
        max_payload_kg=Decimal(payload),
        max_volume_m3=Decimal(volume),
        max_range_km=Decimal(range_km),
        refrigerated=refrigerated,
        helper_policy=helper_policy,
        driver_included=driver_included,
        helper_included=helper_included,
    )


def worker(role: WorkerRole) -> PreflightWorker:
    return PreflightWorker(id=uuid.uuid4(), role=role)


def operation(start: time = time(7, 30), end: time = time(18, 0)) -> PreflightOperation:
    return PreflightOperation(start_time=start, end_time=end)


def error_codes(result: object) -> set[str]:
    return {issue.code for issue in result.blocking_errors}  # type: ignore[attr-defined]


def test_preflight_blocks_empty_operation_and_invalid_window() -> None:
    result = PreflightValidator().validate(
        operation=operation(time(18, 0), time(7, 30)),
        deliveries=[],
        vehicles=[],
        workers=[],
    )

    assert result.status == "INVALID"
    assert error_codes(result) == {
        "INVALID_OPERATION_SCHEDULE",
        "NO_DELIVERIES",
        "NO_VEHICLES",
    }


def test_preflight_blocks_missing_refrigerated_vehicle() -> None:
    result = PreflightValidator().validate(
        operation=operation(),
        deliveries=[delivery(temperature=TemperatureClass.REFRIGERATED)],
        vehicles=[vehicle()],
        workers=[worker(WorkerRole.DRIVER)],
    )

    assert "NO_FEASIBLE_VEHICLE" in error_codes(result)


def test_preflight_blocks_individual_capacity_and_range() -> None:
    capacity_result = PreflightValidator().validate(
        operation=operation(),
        deliveries=[delivery(weight="500")],
        vehicles=[vehicle(payload="100")],
        workers=[worker(WorkerRole.DRIVER)],
    )
    range_result = PreflightValidator().validate(
        operation=operation(),
        deliveries=[delivery(range_km="250")],
        vehicles=[vehicle(range_km="100")],
        workers=[worker(WorkerRole.DRIVER)],
    )

    assert "CAPACITY_INFEASIBLE" in error_codes(capacity_result)
    assert "RANGE_INFEASIBLE" in error_codes(range_result)


def test_preflight_blocks_invalid_address_and_impossible_team() -> None:
    invalid_address = PreflightValidator().validate(
        operation=operation(),
        deliveries=[delivery(address_valid=False)],
        vehicles=[vehicle()],
        workers=[worker(WorkerRole.DRIVER)],
    )
    missing_helper = PreflightValidator().validate(
        operation=operation(),
        deliveries=[delivery(handling=HandlingRequirement.TWO_PERSON)],
        vehicles=[vehicle()],
        workers=[worker(WorkerRole.DRIVER)],
    )

    assert "ADDRESS_NOT_FOUND" in error_codes(invalid_address)
    assert "TEAM_INFEASIBLE" in error_codes(missing_helper)


def test_preflight_accepts_valid_plan_and_warns_about_single_refrigerated_vehicle() -> None:
    result = PreflightValidator().validate(
        operation=operation(),
        deliveries=[delivery(temperature=TemperatureClass.REFRIGERATED)],
        vehicles=[vehicle(refrigerated=True)],
        workers=[worker(WorkerRole.DRIVER)],
    )

    assert result.status == "VALID"
    assert not result.blocking_errors
    assert [warning.code for warning in result.warnings] == ["LOW_REFRIGERATION_REDUNDANCY"]
    assert result.summary.delivery_count == 1
    assert result.summary.refrigerated_count == 1
    assert result.summary.operation_window_minutes == 630


def test_preflight_accepts_included_team_contract_and_motorcycle_courier() -> None:
    aggregated = PreflightValidator().validate(
        operation=operation(),
        deliveries=[delivery(handling=HandlingRequirement.TWO_PERSON)],
        vehicles=[vehicle(driver_included=True, helper_included=True)],
        workers=[],
    )
    moto = PreflightValidator().validate(
        operation=operation(),
        deliveries=[delivery()],
        vehicles=[vehicle(vehicle_type=VehicleType.MOTO, helper_policy=HelperPolicy.FORBIDDEN)],
        workers=[worker(WorkerRole.MOTORCYCLE_COURIER)],
    )

    assert aggregated.status == "VALID"
    assert moto.status == "VALID"
