import argparse
import uuid
from decimal import Decimal
from pathlib import Path

from fluxmed.benchmarks import BenchmarkProblem, OptimizerBenchmarkRunner, write_benchmark_report
from fluxmed.optimization import (
    GeneticOptimizerConfig,
    OptimizationDelivery,
    OptimizationVehicle,
    TravelMatrix,
    TravelMetric,
)


def _smoke_problem() -> BenchmarkProblem:
    deliveries = [
        OptimizationDelivery(
            id=uuid.UUID(int=index),
            weight_kg=Decimal("25"),
            volume_m3=Decimal("0.15"),
            service_minutes=8,
        )
        for index in range(1, 7)
    ]
    vehicles = [
        OptimizationVehicle(
            id=uuid.UUID(int=100 + index),
            max_payload_kg=Decimal("100"),
            max_volume_m3=Decimal("1.0"),
            max_range_km=Decimal("250"),
            fixed_route_cost_brl=Decimal("8"),
            cost_per_km_brl=Decimal("0.65"),
            cost_per_hour_brl=Decimal("3"),
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
                travel_minutes=distance * Decimal("4"),
            )
    return BenchmarkProblem(
        scenario_name="SMOKE_SYNTHETIC",
        deliveries=deliveries,
        vehicles=vehicles,
        travel_matrix=TravelMatrix(metrics),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FluxMed optimizer benchmark runner. The current CLI exposes a smoke dataset; "
        "Santa Aurora scenario-matrix loading is added in the next Phase 17 increment."
    )
    parser.add_argument("--smoke", action="store_true", help="Run the deterministic smoke dataset.")
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=[101, 202, 303],
        help="GA seeds used for each GA variant.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/results/smoke"),
        help="Directory for JSON and CSV outputs.",
    )
    args = parser.parse_args()
    if not args.smoke:
        parser.error("Use --smoke for the current first benchmark increment.")

    runner = OptimizerBenchmarkRunner(
        GeneticOptimizerConfig(
            population_size=16,
            max_generations=30,
            stagnation_generations=8,
        )
    )
    report = runner.run(_smoke_problem(), seeds=tuple(args.seeds))
    json_path, csv_path = write_benchmark_report(report, args.output)
    print(f"Benchmark complete: {len(report.runs)} runs")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    for summary in report.summaries:
        print(
            f"{summary.method.value}: feasible={summary.feasible_runs}/{summary.runs} "
            f"mean_cost={summary.mean_cost_brl} mean_runtime={summary.mean_runtime_seconds:.4f}s"
        )


if __name__ == "__main__":
    main()
