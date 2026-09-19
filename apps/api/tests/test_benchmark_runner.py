import uuid
from decimal import Decimal

from fluxmed.benchmarks import BenchmarkMethod, BenchmarkProblem, OptimizerBenchmarkRunner
from fluxmed.domain.enums import TemperatureClass
from fluxmed.optimization import (
    GeneticOptimizerConfig,
    OptimizationDelivery,
    OptimizationVehicle,
    RouteDecoder,
    TravelMatrix,
    TravelMetric,
)


def _problem() -> BenchmarkProblem:
    deliveries = [
        OptimizationDelivery(
            id=uuid.UUID(int=index),
            weight_kg=Decimal("20"),
            volume_m3=Decimal("0.10"),
            service_minutes=5,
        )
        for index in range(1, 5)
    ]
    vehicles = [
        OptimizationVehicle(
            id=uuid.UUID(int=100 + index),
            max_payload_kg=Decimal("60"),
            max_volume_m3=Decimal("0.50"),
            max_range_km=Decimal("200"),
            fixed_route_cost_brl=Decimal("5"),
            cost_per_km_brl=Decimal("0.50"),
            cost_per_hour_brl=Decimal("2"),
        )
        for index in range(1, 3)
    ]
    locations = [None, *(delivery.id for delivery in deliveries)]
    positions = {location: index for index, location in enumerate(locations)}
    metrics: dict[tuple[uuid.UUID | None, uuid.UUID | None], TravelMetric] = {}
    for origin in locations:
        for destination in locations:
            if origin == destination:
                continue
            distance = Decimal(abs(positions[origin] - positions[destination]) + 1)
            metrics[(origin, destination)] = TravelMetric(
                distance_km=distance,
                travel_minutes=distance * Decimal("3"),
            )
    return BenchmarkProblem(
        scenario_name="UNIT",
        deliveries=deliveries,
        vehicles=vehicles,
        travel_matrix=TravelMatrix(metrics),
    )


def test_benchmark_runner_compares_baselines_and_three_ga_variants() -> None:
    runner = OptimizerBenchmarkRunner(
        GeneticOptimizerConfig(
            population_size=8,
            max_generations=5,
            stagnation_generations=3,
        )
    )

    report = runner.run(_problem(), seeds=(11, 22))

    assert len(report.runs) == 8
    counts = {
        method: sum(run.method is method for run in report.runs) for method in BenchmarkMethod
    }
    assert counts[BenchmarkMethod.NEAREST_NEIGHBOR] == 1
    assert counts[BenchmarkMethod.BEST_INSERTION] == 1
    assert counts[BenchmarkMethod.GA_BASIC] == 2
    assert counts[BenchmarkMethod.GA_PRUNING] == 2
    assert counts[BenchmarkMethod.GA_PRUNING_REPAIR] == 2
    assert len(report.summaries) == 5
    assert all(summary.feasible_rate == 1.0 for summary in report.summaries)


def test_decoder_can_measure_advanced_pruning_without_hiding_infeasibility() -> None:
    delivery = OptimizationDelivery(
        id=uuid.UUID(int=1),
        weight_kg=Decimal("10"),
        volume_m3=Decimal("0.10"),
        service_minutes=5,
        temperature_class=TemperatureClass.REFRIGERATED,
    )
    vehicle = OptimizationVehicle(
        id=uuid.UUID(int=2),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("1"),
        max_range_km=Decimal("100"),
        refrigerated=False,
    )
    matrix = TravelMatrix(
        {
            (None, delivery.id): TravelMetric(Decimal("5"), Decimal("10")),
            (delivery.id, None): TravelMetric(Decimal("5"), Decimal("10")),
        }
    )

    pruned = RouteDecoder(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=matrix,
        advanced_pruning_enabled=True,
    ).decode((delivery.id,))
    unpruned = RouteDecoder(
        deliveries=[delivery],
        vehicles=[vehicle],
        travel_matrix=matrix,
        advanced_pruning_enabled=False,
    ).decode((delivery.id,))

    assert pruned.unassigned_delivery_ids == (delivery.id,)
    assert pruned.pruning_counts["REFRIGERATION_INCOMPATIBLE"] == 1
    assert unpruned.unassigned_delivery_ids == ()
    assert unpruned.routes[0].hard_violations == ("REFRIGERATION_INCOMPATIBLE",)
