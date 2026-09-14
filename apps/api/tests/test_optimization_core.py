import random
import uuid
from decimal import Decimal

from fluxmed.optimization import (
    DecodedRoute,
    DecodedSolution,
    FitnessEvaluator,
    GeneticOptimizer,
    GeneticOptimizerConfig,
    OptimizationDelivery,
    OptimizationVehicle,
    RouteDecoder,
    SolutionValidator,
    TravelMatrix,
    TravelMetric,
    insertion_mutation,
    inversion_mutation,
    order_crossover,
    swap_mutation,
)


def _id(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


def _problem(
    delivery_count: int = 20,
) -> tuple[list[OptimizationDelivery], list[OptimizationVehicle], TravelMatrix]:
    deliveries = [
        OptimizationDelivery(
            id=_id(index + 1),
            weight_kg=Decimal("12") + Decimal(index % 5),
            volume_m3=Decimal("0.08") + Decimal(index % 3) / Decimal("100"),
            service_minutes=6 + index % 4,
        )
        for index in range(delivery_count)
    ]
    vehicles = [
        OptimizationVehicle(
            id=_id(100 + index),
            max_payload_kg=Decimal("120"),
            max_volume_m3=Decimal("1.0"),
            cost_per_km_brl=Decimal("1.20") + Decimal(index) / Decimal("10"),
            cost_per_hour_brl=Decimal("18.00"),
        )
        for index in range(3)
    ]
    positions = {delivery.id: Decimal(index + 1) for index, delivery in enumerate(deliveries)}
    positions[None] = Decimal("0")
    metrics: dict[tuple[uuid.UUID | None, uuid.UUID | None], TravelMetric] = {}
    for origin, origin_position in positions.items():
        for destination, destination_position in positions.items():
            if origin == destination:
                continue
            distance = abs(destination_position - origin_position) + Decimal("0.5")
            metrics[(origin, destination)] = TravelMetric(
                distance_km=distance,
                travel_minutes=distance * Decimal("2.4"),
            )
    return deliveries, vehicles, TravelMatrix(metrics)


def test_order_crossover_preserves_permutation() -> None:
    genes = tuple(_id(index) for index in range(1, 21))
    parent_b = tuple(reversed(genes))
    rng = random.Random(9217)

    for _ in range(50):
        child = order_crossover(genes, parent_b, rng)
        assert len(child) == len(genes)
        assert set(child) == set(genes)
        assert len(set(child)) == len(child)


def test_mutations_preserve_all_genes() -> None:
    chromosome = tuple(_id(index) for index in range(1, 16))
    for operator in (swap_mutation, insertion_mutation, inversion_mutation):
        mutated = operator(chromosome, random.Random(77))
        assert len(mutated) == len(chromosome)
        assert set(mutated) == set(chromosome)


def test_lexicographic_fitness_prefers_feasible_solution() -> None:
    evaluator = FitnessEvaluator()
    feasible = DecodedSolution(
        routes=(
            DecodedRoute(
                vehicle_id=_id(100),
                delivery_ids=(_id(1),),
                total_weight_kg=Decimal("10"),
                total_volume_m3=Decimal("0.1"),
                distance_km=Decimal("40"),
                travel_minutes=Decimal("80"),
                service_minutes=10,
                total_duration_minutes=Decimal("90"),
                total_cost_brl=Decimal("500"),
            ),
        ),
    )
    infeasible = DecodedSolution(
        routes=(),
        unassigned_delivery_ids=(_id(1),),
    )

    assert evaluator.evaluate(feasible).sort_key() < evaluator.evaluate(infeasible).sort_key()


def test_decoder_splits_load_across_vehicles_and_returns_to_depot() -> None:
    deliveries, vehicles, matrix = _problem(delivery_count=8)
    limited = [
        OptimizationVehicle(
            id=vehicle.id,
            max_payload_kg=Decimal("60"),
            max_volume_m3=Decimal("0.5"),
        )
        for vehicle in vehicles[:2]
    ]
    chromosome = tuple(delivery.id for delivery in deliveries)
    solution = RouteDecoder(
        deliveries=deliveries,
        vehicles=limited,
        travel_matrix=matrix,
    ).decode(chromosome)

    assert not solution.unassigned_delivery_ids
    assert len(solution.routes) == 2
    assert all(route.starts_at_depot and route.returns_to_depot for route in solution.routes)
    assert all(route.total_weight_kg <= Decimal("60") for route in solution.routes)
    assert all(route.total_volume_m3 <= Decimal("0.5") for route in solution.routes)


def test_solution_validator_detects_duplicate_and_missing_delivery() -> None:
    deliveries, vehicles, _matrix = _problem(delivery_count=3)
    route = DecodedRoute(
        vehicle_id=vehicles[0].id,
        delivery_ids=(deliveries[0].id, deliveries[0].id, deliveries[1].id),
        total_weight_kg=Decimal("40"),
        total_volume_m3=Decimal("0.3"),
        distance_km=Decimal("10"),
        travel_minutes=Decimal("20"),
        service_minutes=18,
        total_duration_minutes=Decimal("38"),
        total_cost_brl=Decimal("20"),
    )
    result = SolutionValidator().validate(
        solution=DecodedSolution(routes=(route,)),
        deliveries=deliveries,
        vehicles=vehicles,
    )

    codes = {issue.code for issue in result.issues}
    assert result.valid is False
    assert "DELIVERY_DUPLICATED" in codes
    assert "DELIVERY_UNASSIGNED" in codes


def test_genetic_optimizer_is_deterministic_and_never_worse_than_seed_baselines() -> None:
    deliveries, vehicles, matrix = _problem()
    optimizer = GeneticOptimizer(
        GeneticOptimizerConfig(
            population_size=32,
            max_generations=45,
            stagnation_generations=12,
        )
    )

    first = optimizer.optimize(
        deliveries=deliveries,
        vehicles=vehicles,
        travel_matrix=matrix,
        random_seed=582914,
    )
    second = optimizer.optimize(
        deliveries=deliveries,
        vehicles=vehicles,
        travel_matrix=matrix,
        random_seed=582914,
    )

    assert first.best.chromosome == second.best.chromosome
    assert first.best.fitness.sort_key() == second.best.fitness.sort_key()
    assert first.best.fitness.feasible is True
    assert all(
        first.best.fitness.sort_key() <= baseline.fitness.sort_key()
        for baseline in first.baselines
    )
