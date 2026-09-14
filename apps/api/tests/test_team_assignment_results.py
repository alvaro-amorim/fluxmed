import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fluxmed.application.optimization.cost_engine import FinalCostEngine
from fluxmed.application.optimization.team_assignment import (
    TeamAssignmentError,
    TeamAssignmentSolver,
)
from fluxmed.application.resources.service import VehicleCostView, VehicleView, WorkerView
from fluxmed.domain.enums import (
    CompensationModel,
    FuelType,
    HandlingRequirement,
    HelperPolicy,
    VehicleOwnershipType,
    VehicleStatus,
    VehicleType,
    WorkerEngagementType,
    WorkerRole,
)
from fluxmed.optimization import DecodedRoute, OptimizationDelivery


def _id(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


def _vehicle(
    value: int,
    *,
    vehicle_type: VehicleType = VehicleType.CARGO_VAN,
    ownership: VehicleOwnershipType = VehicleOwnershipType.OWNED,
    helper_policy: HelperPolicy = HelperPolicy.OPTIONAL,
    driver_included: bool = False,
    helper_included: bool = False,
) -> VehicleView:
    owned = ownership is VehicleOwnershipType.OWNED
    return VehicleView(
        id=_id(value),
        plate=f"ABC{value}D{value}",
        type=vehicle_type,
        ownership_type=ownership,
        max_payload_kg=Decimal("1000"),
        max_volume_m3=Decimal("8"),
        max_range_km=Decimal("500"),
        refrigerated=True,
        status=VehicleStatus.AVAILABLE,
        helper_policy=helper_policy,
        fuel_type=FuelType.DIESEL,
        fuel_efficiency_km_per_l=Decimal("10"),
        active=True,
        cost=VehicleCostView(
            ownership_type=ownership,
            depreciation_per_km=Decimal("0.50") if owned else None,
            maintenance_per_km=Decimal("0.20") if owned else None,
            fixed_cost_per_hour=Decimal("10") if owned else None,
            contract_price_brl=None if owned else Decimal("180"),
            pricing_model=None,
            fuel_included=False,
            driver_included=driver_included,
            helper_included=helper_included,
            maintenance_items=[],
        ),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _worker(value: int, role: WorkerRole, hourly: str) -> WorkerView:
    return WorkerView(
        id=_id(value),
        name=f"Worker {value}",
        role=role,
        engagement_type=WorkerEngagementType.EMPLOYEE,
        compensation_model=CompensationModel.HOURLY,
        compensation_value_brl=Decimal(hourly),
        active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _route(vehicle_id: uuid.UUID, duration: str, delivery_ids: tuple[uuid.UUID, ...]) -> DecodedRoute:
    return DecodedRoute(
        vehicle_id=vehicle_id,
        delivery_ids=delivery_ids,
        total_weight_kg=Decimal("100"),
        total_volume_m3=Decimal("1"),
        distance_km=Decimal("20"),
        travel_minutes=Decimal(duration),
        service_minutes=0,
        total_duration_minutes=Decimal(duration),
        total_cost_brl=Decimal("0"),
    )


def test_team_solver_finds_global_minimum_cost_matching() -> None:
    vehicles = [_vehicle(101), _vehicle(102)]
    routes = (
        _route(vehicles[0].id, "60", (_id(1),)),
        _route(vehicles[1].id, "240", (_id(2),)),
    )
    deliveries = [
        OptimizationDelivery(_id(1), Decimal("10"), Decimal("0.1"), 5),
        OptimizationDelivery(_id(2), Decimal("10"), Decimal("0.1"), 5),
    ]
    cheap = _worker(201, WorkerRole.DRIVER, "10")
    expensive = _worker(202, WorkerRole.DRIVER, "20")

    plan = TeamAssignmentSolver().solve(
        routes=routes,
        deliveries=deliveries,
        vehicles=vehicles,
        workers=[cheap, expensive],
    )
    assignments = plan.by_vehicle()

    assert assignments[vehicles[1].id].primary_worker_id == cheap.id
    assert assignments[vehicles[0].id].primary_worker_id == expensive.id
    assert plan.total_team_cost_brl == Decimal("60")


def test_motorcycle_route_requires_motorcycle_courier() -> None:
    vehicle = _vehicle(101, vehicle_type=VehicleType.MOTO)
    delivery = OptimizationDelivery(_id(1), Decimal("1"), Decimal("0.01"), 3)
    courier = _worker(201, WorkerRole.MOTORCYCLE_COURIER, "15")

    plan = TeamAssignmentSolver().solve(
        routes=(_route(vehicle.id, "60", (delivery.id,)),),
        deliveries=[delivery],
        vehicles=[vehicle],
        workers=[courier],
    )

    assignment = plan.assignments[0]
    assert assignment.primary_role is WorkerRole.MOTORCYCLE_COURIER
    assert assignment.primary_worker_id == courier.id


def test_two_person_route_fails_without_helper() -> None:
    vehicle = _vehicle(101)
    delivery = OptimizationDelivery(
        _id(1),
        Decimal("10"),
        Decimal("0.1"),
        5,
        handling_requirement=HandlingRequirement.TWO_PERSON,
    )

    with pytest.raises(TeamAssignmentError, match="HELPER"):
        TeamAssignmentSolver().solve(
            routes=(_route(vehicle.id, "60", (delivery.id,)),),
            deliveries=[delivery],
            vehicles=[vehicle],
            workers=[_worker(201, WorkerRole.DRIVER, "10")],
        )


def test_contract_included_team_requires_no_worker_cost() -> None:
    vehicle = _vehicle(
        101,
        ownership=VehicleOwnershipType.AGGREGATED,
        helper_policy=HelperPolicy.REQUIRED,
        driver_included=True,
        helper_included=True,
    )
    delivery = OptimizationDelivery(_id(1), Decimal("10"), Decimal("0.1"), 5)

    plan = TeamAssignmentSolver().solve(
        routes=(_route(vehicle.id, "90", (delivery.id,)),),
        deliveries=[delivery],
        vehicles=[vehicle],
        workers=[],
    )

    assignment = plan.assignments[0]
    assert assignment.primary_included is True
    assert assignment.helper_included is True
    assert assignment.team_cost_brl == Decimal("0")


def test_final_cost_engine_consolidates_vehicle_fuel_and_team() -> None:
    vehicle = _vehicle(101)
    route = _route(vehicle.id, "120", (_id(1),))
    team_plan = TeamAssignmentSolver().solve(
        routes=(route,),
        deliveries=[OptimizationDelivery(_id(1), Decimal("10"), Decimal("0.1"), 5)],
        vehicles=[vehicle],
        workers=[_worker(201, WorkerRole.DRIVER, "10")],
    )

    breakdown = FinalCostEngine().calculate(
        route=route,
        vehicle=vehicle,
        team=team_plan.assignments[0],
    )

    assert breakdown.depreciation_brl == Decimal("10.00")
    assert breakdown.maintenance_brl == Decimal("4.00")
    assert breakdown.fixed_time_brl == Decimal("20")
    assert breakdown.fuel_brl == Decimal("12.00")
    assert breakdown.team_brl == Decimal("20")
    assert breakdown.total_brl == Decimal("66.00")
