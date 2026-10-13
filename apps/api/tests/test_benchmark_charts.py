import uuid
from decimal import Decimal

from fluxmed.benchmarks import OptimizerBenchmarkRunner, write_academic_artifacts
from fluxmed.benchmarks.charts import (
    _carry_forward_hard_violation_mean,
    _x_tick_values,
)
from fluxmed.benchmarks.models import (
    BenchmarkConvergencePoint,
    BenchmarkMethod,
    BenchmarkProblem,
)
from fluxmed.optimization import (
    GeneticOptimizerConfig,
    OptimizationDelivery,
    OptimizationVehicle,
    TravelMatrix,
    TravelMetric,
)


def test_academic_artifacts_generate_svg_and_markdown(tmp_path) -> None:
    deliveries = [
        OptimizationDelivery(
            id=uuid.UUID(int=index),
            weight_kg=Decimal("10"),
            volume_m3=Decimal("0.10"),
            service_minutes=5,
        )
        for index in range(1, 4)
    ]
    vehicle = OptimizationVehicle(
        id=uuid.UUID(int=50),
        max_payload_kg=Decimal("100"),
        max_volume_m3=Decimal("1"),
        max_range_km=Decimal("100"),
        fixed_route_cost_brl=Decimal("5"),
        cost_per_km_brl=Decimal("0.5"),
        cost_per_hour_brl=Decimal("2"),
    )
    locations = [None, *(delivery.id for delivery in deliveries)]
    metrics = {
        (origin, destination): TravelMetric(Decimal("1"), Decimal("2"))
        for origin in locations
        for destination in locations
        if origin != destination
    }
    problem = BenchmarkProblem(
        scenario_name="NORMAL-20-S20260917",
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=TravelMatrix(metrics),
    )
    report = OptimizerBenchmarkRunner(
        GeneticOptimizerConfig(
            population_size=8,
            max_generations=4,
            stagnation_generations=2,
        )
    ).run(problem, seeds=(101,))

    artifacts = write_academic_artifacts(report, tmp_path)

    assert artifacts
    assert (tmp_path / "academic-summary.md").exists()
    svg_paths = [path for path in artifacts if path.suffix == ".svg"]
    assert len(svg_paths) >= 4
    assert all("<svg" in path.read_text(encoding="utf-8") for path in svg_paths)


def test_dense_chart_axis_uses_readable_tick_count() -> None:
    ticks = _x_tick_values(list(range(121)))

    assert len(ticks) <= 8
    assert ticks[0] == 0
    assert ticks[-1] == 120


def test_convergence_carries_early_stopped_seed_forward() -> None:
    points = [
        BenchmarkConvergencePoint(
            scenario_name="EMERGENCY-80-S20260917",
            delivery_count=80,
            method=BenchmarkMethod.GA_PRUNING_REPAIR,
            seed=101,
            generation=0,
            elapsed_seconds=0.0,
            improved=True,
            feasible=False,
            hard_violations=5,
            service_penalty=0.0,
            cost_brl=0.0,
            makespan_minutes=0.0,
            distance_km=0.0,
            vehicles_used=0,
            diversity_ratio=1.0,
            effective_mutation_rate=0.22,
            immigrants_added=0,
            pruning_counts={},
        ),
        BenchmarkConvergencePoint(
            scenario_name="EMERGENCY-80-S20260917",
            delivery_count=80,
            method=BenchmarkMethod.GA_PRUNING_REPAIR,
            seed=101,
            generation=1,
            elapsed_seconds=1.0,
            improved=True,
            feasible=False,
            hard_violations=1,
            service_penalty=0.0,
            cost_brl=0.0,
            makespan_minutes=0.0,
            distance_km=0.0,
            vehicles_used=0,
            diversity_ratio=0.9,
            effective_mutation_rate=0.22,
            immigrants_added=0,
            pruning_counts={},
        ),
        BenchmarkConvergencePoint(
            scenario_name="EMERGENCY-80-S20260917",
            delivery_count=80,
            method=BenchmarkMethod.GA_PRUNING_REPAIR,
            seed=202,
            generation=0,
            elapsed_seconds=0.0,
            improved=True,
            feasible=False,
            hard_violations=7,
            service_penalty=0.0,
            cost_brl=0.0,
            makespan_minutes=0.0,
            distance_km=0.0,
            vehicles_used=0,
            diversity_ratio=1.0,
            effective_mutation_rate=0.22,
            immigrants_added=0,
            pruning_counts={},
        ),
        BenchmarkConvergencePoint(
            scenario_name="EMERGENCY-80-S20260917",
            delivery_count=80,
            method=BenchmarkMethod.GA_PRUNING_REPAIR,
            seed=202,
            generation=2,
            elapsed_seconds=2.0,
            improved=True,
            feasible=True,
            hard_violations=0,
            service_penalty=0.0,
            cost_brl=100.0,
            makespan_minutes=100.0,
            distance_km=100.0,
            vehicles_used=5,
            diversity_ratio=0.8,
            effective_mutation_rate=0.22,
            immigrants_added=0,
            pruning_counts={},
        ),
    ]

    result = _carry_forward_hard_violation_mean(points, max_generation=2)

    assert result == [(0, 6.0), (1, 4.0), (2, 0.5)]
