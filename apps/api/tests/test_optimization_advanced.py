import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fluxmed.domain.enums import (
    DeliveryPriority,
    HandlingRequirement,
    TemperatureClass,
    TimeWindowPolicy,
)
from fluxmed.optimization import (
    DecodedSolution,
    GeneticOptimizer,
    GeneticOptimizerConfig,
    OptimizationDelivery,
    OptimizationVehicle,
    RouteDecoder,
    SolutionValidator,
    TravelMatrix,
    TravelMetric,
    repair_chromosome,
)


def _id(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


def _matrix(delivery_ids: list[uuid.UUID], distance_km: Decimal = Decimal("5")) -> TravelMatrix:
    locations: list[uuid.UUID | None] = [None, *delivery_ids]
    metrics: dict[tuple[uuid.UUID | None, uuid.UUID | None], TravelMetric] = {}
    for origin in locations:
        for destination in locations:
            if origin == destination:
                continue
            metrics[(origin, destination)] = TravelMetric(
                distance_km=distance_km,
                travel_minutes=distance_km * Decimal("2"),
            )
    return TravelMatrix(metrics)


def test_refrigerated_delivery_prunes_non_refrigerated_vehicle() -> None:
    delivery = OptimizationDelivery(
        id=_id(1),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
        temperature_class=TemperatureClass.REFRIGERATED,
    )
    vehicles = [
        OptimizationVehicle(
            id=_id(101),
            max_payload_kg=Decimal("100"),
            max_volume_m3=Decimal("1"),
            refrigerated=False,
        ),
        OptimizationVehicle(
            id=_id(102),
            max_payload_kg=Decimal("100"),
            max_volume_m3=Decimal("1"),
            refrigerated=True,
        ),
    ]
    solution = RouteDecoder(
        deliveries=[delivery],
        vehicles=vehicles,
        travel_matrix=_matrix([delivery.id]),
    ).decode((delivery.id,))

    assert solution.unassigned_delivery_ids == ()
    assert solution.routes[0].vehicle_id == vehicles[1].id
    assert solution.pruning_counts["REFRIGERATION_INCOMPATIBLE"] == 1


def test_range_constraint_can_make_delivery_unassigned() -> None:
    delivery = OptimizationDelivery(
        id=_id(1),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
    )
    vehicle = OptimizationVehicle(
        id=_id(101),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("1"),
        max_range_km=Decimal("8"),
    )
    solution = RouteDecoder(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=_matrix([delivery.id], Decimal("5")),
    ).decode((delivery.id,))

    assert solution.unassigned_delivery_ids == (delivery.id,)
    assert solution.pruning_counts["RANGE_IMPOSSIBLE"] == 1


def test_hard_time_window_is_not_accepted() -> None:
    start = datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)
    delivery = OptimizationDelivery(
        id=_id(1),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
        time_window_end=start + timedelta(minutes=5),
        time_window_policy=TimeWindowPolicy.HARD,
    )
    vehicle = OptimizationVehicle(
        id=_id(101),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("1"),
    )
    solution = RouteDecoder(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=_matrix([delivery.id], Decimal("5")),
        operation_start_at=start,
        operation_end_at=start + timedelta(hours=4),
    ).decode((delivery.id,))

    assert solution.unassigned_delivery_ids == (delivery.id,)
    assert solution.pruning_counts["HARD_TIME_WINDOW_IMPOSSIBLE"] == 1


def test_soft_window_lateness_enters_service_penalty() -> None:
    start = datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)
    delivery = OptimizationDelivery(
        id=_id(1),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
        priority=DeliveryPriority.CRITICAL,
        time_window_end=start + timedelta(minutes=5),
        time_window_policy=TimeWindowPolicy.SOFT,
    )
    vehicle = OptimizationVehicle(
        id=_id(101),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("1"),
    )
    optimizer = GeneticOptimizer(
        GeneticOptimizerConfig(population_size=4, max_generations=2, stagnation_generations=1)
    )
    result = optimizer.optimize(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=_matrix([delivery.id], Decimal("5")),
        random_seed=12,
        operation_start_at=start,
        operation_end_at=start + timedelta(hours=4),
    )

    assert result.best.fitness.feasible is True
    assert result.best.fitness.service_penalty > Decimal("0")
    assert result.best.fitness.critical_risk > Decimal("0")


def test_two_person_delivery_requires_helper_capability() -> None:
    delivery = OptimizationDelivery(
        id=_id(1),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
        handling_requirement=HandlingRequirement.TWO_PERSON,
    )
    vehicle = OptimizationVehicle(
        id=_id(101),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("1"),
        helper_available=False,
    )
    solution = RouteDecoder(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=_matrix([delivery.id]),
    ).decode((delivery.id,))

    assert solution.unassigned_delivery_ids == (delivery.id,)
    assert solution.pruning_counts["TEAM_INFEASIBLE"] == 1


def test_repair_preserves_permutation() -> None:
    chromosome = (_id(1), _id(2), _id(3), _id(4))
    solution = DecodedSolution(routes=(), unassigned_delivery_ids=chromosome)
    repaired = repair_chromosome(chromosome, solution, random.Random(42))

    assert set(repaired) == set(chromosome)
    assert len(repaired) == len(chromosome)


def test_solution_validator_rechecks_range_and_refrigeration() -> None:
    delivery = OptimizationDelivery(
        id=_id(1),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
        temperature_class=TemperatureClass.REFRIGERATED,
    )
    vehicle = OptimizationVehicle(
        id=_id(101),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("1"),
        max_range_km=Decimal("5"),
        refrigerated=False,
    )
    route = RouteDecoder(
        deliveries=[delivery],
        vehicles=[
            OptimizationVehicle(
                id=vehicle.id,
                max_payload_kg=vehicle.max_payload_kg,
                max_volume_m3=vehicle.max_volume_m3,
                max_range_km=Decimal("100"),
                refrigerated=True,
            )
        ],
        travel_matrix=_matrix([delivery.id]),
    ).decode((delivery.id,)).routes[0]

    validation = SolutionValidator().validate(
        solution=DecodedSolution(routes=(route,)),
        deliveries=[delivery],
        vehicles=[vehicle],
    )
    codes = {issue.code for issue in validation.issues}
    assert "RANGE_IMPOSSIBLE" in codes
    assert "REFRIGERATION_INCOMPATIBLE" in codes
