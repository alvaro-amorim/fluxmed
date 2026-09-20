import uuid
from decimal import Decimal

from fluxmed.benchmarks import OptimizerBenchmarkRunner, write_academic_artifacts
from fluxmed.benchmarks.charts import _x_tick_values
from fluxmed.benchmarks.models import BenchmarkProblem
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
