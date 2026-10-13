import uuid
from decimal import Decimal

from fluxmed.application.deliveries.scenario import ScenarioProfile
from fluxmed.benchmarks import (
    BenchmarkProblem,
    OptimizerBenchmarkRunner,
    ScenarioMatrixBenchmarkRunner,
)
from fluxmed.optimization import (
    GeneticOptimizerConfig,
    OptimizationDelivery,
    OptimizationVehicle,
    TravelMatrix,
    TravelMetric,
)


def _problem(profile: ScenarioProfile, delivery_count: int, scenario_seed: int) -> BenchmarkProblem:
    deliveries = [
        OptimizationDelivery(
            id=uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{profile.value}:{delivery_count}:{scenario_seed}:{index}",
            ),
            weight_kg=Decimal("10"),
            volume_m3=Decimal("0.05"),
            service_minutes=5,
        )
        for index in range(delivery_count)
    ]
    vehicle = OptimizationVehicle(
        id=uuid.UUID(int=500),
        max_payload_kg=Decimal("500"),
        max_volume_m3=Decimal("5"),
        max_range_km=Decimal("500"),
        fixed_route_cost_brl=Decimal("5"),
        cost_per_km_brl=Decimal("0.5"),
        cost_per_hour_brl=Decimal("2"),
    )
    locations = [None, *(delivery.id for delivery in deliveries)]
    metrics: dict[tuple[uuid.UUID | None, uuid.UUID | None], TravelMetric] = {}
    for origin in locations:
        for destination in locations:
            if origin == destination:
                continue
            metrics[(origin, destination)] = TravelMetric(
                distance_km=Decimal("1"),
                travel_minutes=Decimal("2"),
            )
    return BenchmarkProblem(
        scenario_name=f"{profile.value}-{delivery_count}-S{scenario_seed}",
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=TravelMatrix(metrics),
    )


def test_matrix_runner_combines_cells_without_mixing_inputs() -> None:
    benchmark_runner = OptimizerBenchmarkRunner(
        GeneticOptimizerConfig(
            population_size=8,
            max_generations=4,
            stagnation_generations=2,
        )
    )
    matrix = ScenarioMatrixBenchmarkRunner(
        problem_factory=lambda **kwargs: _problem(**kwargs),
        benchmark_runner=benchmark_runner,
    )

    result = matrix.run(
        template_operation_code="OP-TEMPLATE",
        profiles=(ScenarioProfile.NORMAL, ScenarioProfile.BUSY),
        sizes=(2, 3),
        scenario_seeds=(9001,),
        ga_seeds=(101,),
    )

    assert len(result.cells) == 4
    assert len(result.report.runs) == 20
    assert len(result.report.summaries) == 20
    assert {cell.scenario_name for cell in result.cells} == {
        "NORMAL-2-S9001",
        "NORMAL-3-S9001",
        "BUSY-2-S9001",
        "BUSY-3-S9001",
    }
    assert all(run.feasible for run in result.report.runs)
