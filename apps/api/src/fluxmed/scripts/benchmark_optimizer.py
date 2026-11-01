import argparse
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.exc import OperationalError

from fluxmed.application.deliveries.scenario import ScenarioProfile
from fluxmed.benchmarks import (
    BenchmarkProblem,
    BenchmarkRun,
    OptimizerBenchmarkRunner,
    SantaAuroraBenchmarkLoader,
    SantaAuroraScenarioProblemFactory,
    ScenarioMatrixBenchmarkRunner,
    ScenarioMatrixCell,
    write_academic_artifacts,
    write_benchmark_report,
    write_matrix_manifest,
)
from fluxmed.benchmarks.checkpoint import MatrixCheckpoint
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


FINAL_GA_SEEDS = (101, 202, 303, 404, 505)
FINAL_SCENARIO_SEEDS = (20260917,)
FINAL_SIZES = (20, 40, 60, 80)


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


def _show_run(run: BenchmarkRun) -> None:
    print(
        f"Run complete: {run.scenario_name} {run.method.value} seed={run.seed} "
        f"runtime={run.runtime_seconds:.3f}s feasible={run.feasible} "
        f"cost={run.cost_brl:.2f}",
        flush=True,
    )


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
    source.add_argument(
        "--matrix-template-code",
        help=(
            "Use an existing operation as the resource/time/traffic template for a scenario matrix."
        ),
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=[profile.value for profile in ScenarioProfile],
        default=[profile.value for profile in ScenarioProfile],
        help="Scenario profiles used by matrix mode.",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[20, 40, 60, 80],
        help="Delivery counts used by matrix mode.",
    )
    parser.add_argument(
        "--scenario-seeds",
        nargs="+",
        type=int,
        default=[20260917],
        help="Seeds used to generate each synthetic scenario cell.",
    )
    parser.add_argument(
        "--preset",
        choices=["final"],
        default=None,
        help="Apply a reproducible academic benchmark preset.",
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
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse completed matrix scenarios with identical code and inputs.",
    )
    args = parser.parse_args()
    if args.resume and (not args.matrix_template_code or args.output is None):
        parser.error("--resume requires --matrix-template-code and an explicit --output.")

    if args.preset == "final":
        if not args.matrix_template_code:
            parser.error("--preset final requires --matrix-template-code.")
        if args.quick:
            parser.error("--preset final cannot be combined with --quick.")
        args.profiles = [profile.value for profile in ScenarioProfile]
        args.sizes = list(FINAL_SIZES)
        args.scenario_seeds = list(FINAL_SCENARIO_SEEDS)
        args.seeds = list(FINAL_GA_SEEDS)
        if args.output is None:
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            args.output = Path(f"benchmarks/results/final-evidence-{stamp}")
        print(
            "Preset final: profiles=ALL sizes=20,40,60,80 "
            "scenario_seed=20260917 ga_seeds=101,202,303,404,505"
        )

    config = _config(quick=args.quick)
    if args.smoke:
        problem = _smoke_problem()
        label = "SMOKE_SYNTHETIC"
        output_dir = args.output or Path("benchmarks/results/smoke")
        print(f"Problem loaded: {label}")
        report = OptimizerBenchmarkRunner(_config(quick=True)).run(
            problem,
            seeds=tuple(args.seeds),
        )
    elif args.operation_code:
        operation_code = str(args.operation_code)
        try:
            problem, label = _load_operation(operation_code)
        except RuntimeError as exc:
            parser.error(str(exc))
        suffix = "-quick" if args.quick else ""
        output_dir = args.output or Path(f"benchmarks/results/operation-{operation_code}{suffix}")
        print(f"Problem loaded: {label}")
        report = OptimizerBenchmarkRunner(config).run(
            problem,
            seeds=tuple(args.seeds),
        )
    else:
        template_code = str(args.matrix_template_code)
        suffix = "-quick" if args.quick else ""
        output_dir = args.output or Path(f"benchmarks/results/matrix-{template_code}{suffix}")
        session = SessionFactory()
        try:
            factory = SantaAuroraScenarioProblemFactory(
                session,
                template_operation_code=template_code,
            )
            matrix_runner = ScenarioMatrixBenchmarkRunner(
                problem_factory=factory.build,
                benchmark_runner=OptimizerBenchmarkRunner(config, on_run_complete=_show_run),
            )

            def show_cell(cell: ScenarioMatrixCell) -> None:
                print(
                    "Matrix cell: "
                    f"{cell.profile.value} · deliveries={cell.delivery_count} · "
                    f"scenario_seed={cell.scenario_seed}"
                )

            recipe = {
                "template_operation_code": factory.template_operation_code,
                "profiles": args.profiles,
                "sizes": args.sizes,
                "scenario_seeds": args.scenario_seeds,
                "ga_seeds": args.seeds,
                "ga_config": asdict(config),
                "quick": args.quick,
                "cost_metric": "operational_vehicle_fuel_and_global_team",
            }
            with MatrixCheckpoint(
                output_dir,
                root=Path(__file__).resolve().parents[5],
                recipe=recipe,
                resume=args.resume,
            ) as checkpoint:
                matrix_result = matrix_runner.run(
                    template_operation_code=factory.template_operation_code,
                    profiles=tuple(ScenarioProfile(value) for value in args.profiles),
                    sizes=tuple(args.sizes),
                    scenario_seeds=tuple(args.scenario_seeds),
                    ga_seeds=tuple(args.seeds),
                    on_cell_start=show_cell,
                    checkpoint=checkpoint,
                )
            report = matrix_result.report
            manifest_path = write_matrix_manifest(
                matrix_result,
                output_dir,
                ga_seeds=tuple(args.seeds),
                quick=args.quick,
                ga_config=config,
            )
        finally:
            session.rollback()
            session.close()
        print(f"Matrix manifest: {manifest_path}")

    json_path, csv_path = write_benchmark_report(report, output_dir)
    academic_artifacts = write_academic_artifacts(report, output_dir)
    print(f"Benchmark complete: {len(report.runs)} runs")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    print(f"Summary CSV: {output_dir / 'benchmark-summaries.csv'}")
    print(f"Convergence CSV: {output_dir / 'benchmark-convergence.csv'}")
    print(f"Academic artifacts: {len(academic_artifacts)} files")
    for summary in report.summaries:
        print(
            f"{summary.scenario_name} · {summary.method.value}: "
            f"feasible={summary.feasible_runs}/{summary.runs} "
            f"mean_cost={summary.mean_cost_brl} "
            f"mean_runtime={summary.mean_runtime_seconds:.4f}s"
        )


if __name__ == "__main__":
    main()
