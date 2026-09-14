import uuid
from datetime import datetime
from decimal import Decimal

from fluxmed.domain.enums import DeliveryPriority, TemperatureClass, TimeWindowPolicy
from fluxmed.optimization import (
    DecodedRoute,
    DecodedSolution,
    DecodedStop,
    FitnessEvaluator,
    FitnessVector,
    GeneticOptimizer,
    GeneticOptimizerConfig,
    OptimizationContext,
    OptimizationDelivery,
    OptimizationVehicle,
    RouteDecoder,
    SolutionValidator,
    TravelMatrix,
    TravelMetric,
    population_diversity,
    repair_candidates,
)


def _id(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


def _context(*, end_hour: int = 12, end_minute: int = 0) -> OptimizationContext:
    return OptimizationContext(
        operation_start_at=datetime(2026, 9, 14, 8, 0),
        operation_end_at=datetime(2026, 9, 14, end_hour, end_minute),
        range_safety_factor=Decimal("1"),
    )


def _matrix(
    delivery_ids: list[uuid.UUID],
    *,
    travel_minutes: Decimal = Decimal("10"),
    distance_km: Decimal = Decimal("5"),
) -> TravelMatrix:
    locations: list[uuid.UUID | None] = [None, *delivery_ids]
    metrics: dict[tuple[uuid.UUID | None, uuid.UUID | None], TravelMetric] = {}
    for origin in locations:
        for destination in locations:
            if origin == destination:
                continue
            metrics[(origin, destination)] = TravelMetric(
                distance_km=distance_km,
                travel_minutes=travel_minutes,
            )
    return TravelMatrix(metrics)


def test_future_feasibility_preserves_only_refrigerated_vehicle() -> None:
    ambient = OptimizationDelivery(
        id=_id(1),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.2"),
        service_minutes=5,
    )
    refrigerated = OptimizationDelivery(
        id=_id(2),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.2"),
        service_minutes=5,
        temperature_class=TemperatureClass.REFRIGERATED,
    )
    refrigerated_vehicle = OptimizationVehicle(
        id=_id(100),
        max_payload_kg=Decimal("10"),
        max_volume_m3=Decimal("1"),
        max_range_km=Decimal("100"),
        refrigerated=True,
    )
    ambient_vehicle = OptimizationVehicle(
        id=_id(200),
        max_payload_kg=Decimal("10"),
        max_volume_m3=Decimal("1"),
        max_range_km=Decimal("100"),
    )
    outcome = RouteDecoder(
        deliveries=[ambient, refrigerated],
        vehicles=[refrigerated_vehicle, ambient_vehicle],
        travel_matrix=_matrix([ambient.id, refrigerated.id]),
        context=_context(),
    ).decode_with_pruning((ambient.id, refrigerated.id))

    assert not outcome.solution.unassigned_delivery_ids
    route_by_vehicle = {route.vehicle_id: route for route in outcome.solution.routes}
    assert route_by_vehicle[ambient_vehicle.id].delivery_ids == (ambient.id,)
    assert route_by_vehicle[refrigerated_vehicle.id].delivery_ids == (refrigerated.id,)
    assert outcome.pruning.pruned_by_reason["FUTURE_INFEASIBILITY"] >= 1


def test_hard_window_is_pruned_but_soft_window_becomes_service_penalty() -> None:
    hard = OptimizationDelivery(
        id=_id(10),
        weight_kg=Decimal("1"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
        time_window_policy=TimeWindowPolicy.HARD,
        time_window_start=datetime(2026, 9, 14, 8, 0),
        time_window_end=datetime(2026, 9, 14, 8, 10),
    )
    vehicle = OptimizationVehicle(
        id=_id(110),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("10"),
        max_range_km=Decimal("100"),
    )
    matrix = _matrix([hard.id], travel_minutes=Decimal("20"))
    hard_outcome = RouteDecoder(
        deliveries=[hard],
        vehicles=[vehicle],
        travel_matrix=matrix,
        context=_context(),
    ).decode_with_pruning((hard.id,))

    assert hard_outcome.solution.unassigned_delivery_ids == (hard.id,)
    assert hard_outcome.pruning.pruned_by_reason["HARD_TIME_WINDOW_IMPOSSIBLE"] == 1

    soft = OptimizationDelivery(
        id=hard.id,
        weight_kg=hard.weight_kg,
        volume_m3=hard.volume_m3,
        service_minutes=hard.service_minutes,
        priority=DeliveryPriority.NORMAL,
        time_window_policy=TimeWindowPolicy.SOFT,
        time_window_start=hard.time_window_start,
        time_window_end=hard.time_window_end,
    )
    soft_solution = RouteDecoder(
        deliveries=[soft],
        vehicles=[vehicle],
        travel_matrix=matrix,
        context=_context(),
    ).decode((soft.id,))
    fitness = FitnessEvaluator().evaluate(soft_solution)

    assert fitness.feasible is True
    assert fitness.service_penalty == Decimal("10")


def test_range_and_operation_end_are_hard_constraints() -> None:
    delivery = OptimizationDelivery(
        id=_id(20),
        weight_kg=Decimal("1"),
        volume_m3=Decimal("0.1"),
        service_minutes=15,
    )
    short_range_vehicle = OptimizationVehicle(
        id=_id(120),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("10"),
        max_range_km=Decimal("10"),
    )
    range_outcome = RouteDecoder(
        deliveries=[delivery],
        vehicles=[short_range_vehicle],
        travel_matrix=_matrix([delivery.id], distance_km=Decimal("6")),
        context=_context(),
    ).decode_with_pruning((delivery.id,))
    assert range_outcome.solution.unassigned_delivery_ids == (delivery.id,)
    assert range_outcome.pruning.pruned_by_reason["RANGE_IMPOSSIBLE"] == 1

    long_range_vehicle = OptimizationVehicle(
        id=_id(121),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("10"),
        max_range_km=Decimal("100"),
    )
    shift_outcome = RouteDecoder(
        deliveries=[delivery],
        vehicles=[long_range_vehicle],
        travel_matrix=_matrix([delivery.id], travel_minutes=Decimal("10")),
        context=_context(end_hour=8, end_minute=30),
    ).decode_with_pruning((delivery.id,))
    assert shift_outcome.solution.unassigned_delivery_ids == (delivery.id,)
    assert shift_outcome.pruning.pruned_by_reason["END_OF_SHIFT_IMPOSSIBLE"] == 1


def test_repair_can_defer_delivery_that_blocks_an_early_hard_window() -> None:
    flexible = OptimizationDelivery(
        id=_id(30),
        weight_kg=Decimal("1"),
        volume_m3=Decimal("0.1"),
        service_minutes=10,
    )
    urgent = OptimizationDelivery(
        id=_id(31),
        weight_kg=Decimal("1"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
        priority=DeliveryPriority.CRITICAL,
        time_window_policy=TimeWindowPolicy.HARD,
        time_window_start=datetime(2026, 9, 14, 8, 0),
        time_window_end=datetime(2026, 9, 14, 8, 15),
    )
    vehicle = OptimizationVehicle(
        id=_id(130),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("10"),
        max_range_km=Decimal("100"),
    )
    decoder = RouteDecoder(
        deliveries=[flexible, urgent],
        vehicles=[vehicle],
        travel_matrix=_matrix([flexible.id, urgent.id]),
        context=_context(),
    )
    chromosome = (flexible.id, urgent.id)
    initial = decoder.decode(chromosome)

    assert initial.unassigned_delivery_ids == (flexible.id,)
    candidates = repair_candidates(chromosome, initial, [flexible, urgent])
    repaired = [candidate for candidate in candidates if candidate == (urgent.id, flexible.id)]
    assert repaired
    repaired_solution = decoder.decode(repaired[0])
    assert not repaired_solution.unassigned_delivery_ids
    assert set(repaired[0]) == set(chromosome)


def test_safe_lower_bound_prunes_only_when_partial_solution_cannot_beat_best() -> None:
    delivery = OptimizationDelivery(
        id=_id(40),
        weight_kg=Decimal("1"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
    )
    vehicle = OptimizationVehicle(
        id=_id(140),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("10"),
        max_range_km=Decimal("100"),
        fixed_route_cost_brl=Decimal("100"),
    )
    best = FitnessVector(
        feasible=True,
        hard_violations=0,
        service_penalty=Decimal("0"),
        critical_risk=Decimal("0"),
        total_cost_brl=Decimal("50"),
        makespan_minutes=Decimal("30"),
        travel_minutes=Decimal("20"),
        distance_km=Decimal("10"),
        vehicles_used=1,
    )
    outcome = RouteDecoder(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=_matrix([delivery.id]),
        context=_context(),
    ).decode_with_pruning((delivery.id,), best_known_fitness=best)

    assert outcome.solution.unassigned_delivery_ids == (delivery.id,)
    assert outcome.pruning.pruned_by_reason["LOWER_BOUND"] == 1
    assert outcome.pruning.avoided_full_evaluations == 1


def test_validator_independently_rejects_advanced_constraint_violations() -> None:
    delivery = OptimizationDelivery(
        id=_id(50),
        weight_kg=Decimal("1"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
        temperature_class=TemperatureClass.REFRIGERATED,
        time_window_policy=TimeWindowPolicy.HARD,
        time_window_start=datetime(2026, 9, 14, 8, 0),
        time_window_end=datetime(2026, 9, 14, 8, 10),
    )
    vehicle = OptimizationVehicle(
        id=_id(150),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("10"),
        max_range_km=Decimal("10"),
        refrigerated=False,
    )
    route = DecodedRoute(
        vehicle_id=vehicle.id,
        delivery_ids=(delivery.id,),
        total_weight_kg=Decimal("1"),
        total_volume_m3=Decimal("0.1"),
        distance_km=Decimal("12"),
        travel_minutes=Decimal("30"),
        service_minutes=5,
        total_duration_minutes=Decimal("50"),
        total_cost_brl=Decimal("10"),
        stops=(
            DecodedStop(
                delivery_id=delivery.id,
                service_start_at=datetime(2026, 9, 14, 8, 20),
            ),
        ),
        return_at=datetime(2026, 9, 14, 12, 30),
    )
    result = SolutionValidator().validate(
        solution=DecodedSolution(routes=(route,)),
        deliveries=[delivery],
        vehicles=[vehicle],
        context=_context(),
    )

    codes = {issue.code for issue in result.issues}
    assert result.valid is False
    assert {
        "RANGE_EXCEEDED",
        "REFRIGERATION_INCOMPATIBLE",
        "HARD_TIME_WINDOW_MISSED",
        "END_OF_SHIFT_EXCEEDED",
    } <= codes


def test_diversity_drives_adaptive_mutation_and_time_budget_keeps_best_valid() -> None:
    delivery = OptimizationDelivery(
        id=_id(60),
        weight_kg=Decimal("1"),
        volume_m3=Decimal("0.1"),
        service_minutes=5,
    )
    vehicle = OptimizationVehicle(
        id=_id(160),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("10"),
    )
    matrix = _matrix([delivery.id])
    assert population_diversity([(delivery.id,), (delivery.id,)]) == 0.0

    adaptive = GeneticOptimizer(
        GeneticOptimizerConfig(
            population_size=4,
            max_generations=1,
            mutation_rate=0.10,
            max_adaptive_mutation_rate=0.60,
            stagnation_generations=5,
            time_budget_seconds=30,
            hard_time_limit_seconds=60,
        )
    ).optimize(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=matrix,
        random_seed=123,
    )
    assert adaptive.mutation_rate_history
    assert adaptive.mutation_rate_history[0] > 0.10

    class FakeClock:
        def __init__(self) -> None:
            self.value = -31.0

        def __call__(self) -> float:
            self.value += 31.0
            return self.value

    timed = GeneticOptimizer(
        GeneticOptimizerConfig(
            population_size=4,
            max_generations=10,
            stagnation_generations=5,
            time_budget_seconds=30,
            hard_time_limit_seconds=60,
        ),
        clock=FakeClock(),
    ).optimize(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=matrix,
        random_seed=123,
    )
    assert timed.stop_reason == "TIME_BUDGET"
    assert timed.best.fitness.feasible is True
    assert timed.generations_completed == 0
