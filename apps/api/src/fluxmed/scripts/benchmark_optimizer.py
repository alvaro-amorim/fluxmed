import argparse
import uuid
from decimal import Decimal
from pathlib import Path

from sqlalchemy.exc import OperationalError
from fluxmed.benchmarks import (
    BenchmarkProblem,
    OptimizerBenchmarkRunner,
    SantaAuroraBenchmarkLoader,
    write_benchmark_report,
)
from fluxmed.infrastructure.database import SessionFactory
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


def _config(*, quick: bool) -> GeneticOptimizerConfig:
    if not quick:
        return GeneticOptimizerConfig()
    return GeneticOptimizerConfig(
        population_size=16,
        max_generations=30,
        stagnation_generations=8,
    )


def _load_operation(operation_code: str) -> tuple[BenchmarkProblem, str]:
    session = SessionFactory()
    try:
        loaded = SantaAuroraBenchmarkLoader(session).load_by_code(operation_code)
        label = (
            f"{loaded.operation_code} · traffic={loaded.traffic_mode.value} · "
            f"deliveries={loaded.problem.delivery_count} · vehicles={len(loaded.problem.vehicles)}"
        )
        return loaded.problem, label
    except OperationalError as exc:
        raise RuntimeError(
            "Não foi possível conectar ao PostgreSQL do FluxMed em até 5 segundos. "
            "Verifique se o serviço 'db' está ativo e se DATABASE_URL aponta para o banco "
            "de desenvolvimento que contém a operação."
        ) from exc
    finally:
        session.rollback()
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FluxMed optimizer benchmark runner for smoke and Santa Aurora operations."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--smoke", action="store_true", help="Run the deterministic smoke dataset.")
    source.add_argument(
        "--operation-code",
        help="Load an existing Santa Aurora operation read-only by operation code.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use a reduced GA configuration for development validation.",
    )
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
        default=None,
        help="Directory for JSON and CSV outputs.",
    )
    args = parser.parse_args()

    if args.smoke:
        problem = _smoke_problem()
        label = "SMOKE_SYNTHETIC"
        output_dir = args.output or Path("benchmarks/results/smoke")
        config = _config(quick=True)
    else:
        operation_code = str(args.operation_code)
        try:
            problem, label = _load_operation(operation_code)
        except RuntimeError as exc:
            parser.error(str(exc))
        suffix = "-quick" if args.quick else ""
        output_dir = args.output or Path(f"benchmarks/results/operation-{operation_code}{suffix}")
        config = _config(quick=args.quick)

    print(f"Problem loaded: {label}")
    runner = OptimizerBenchmarkRunner(config)
    report = runner.run(problem, seeds=tuple(args.seeds))
    json_path, csv_path = write_benchmark_report(report, output_dir)
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
