import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from statistics import fmean, pstdev
from time import perf_counter

from fluxmed.benchmarks.models import (
    BenchmarkConvergencePoint,
    BenchmarkMethod,
    BenchmarkProblem,
    BenchmarkReport,
    BenchmarkRun,
    BenchmarkSummary,
)
from fluxmed.optimization.baselines import (
    best_insertion_chromosome,
    nearest_neighbor_chromosome,
)
from fluxmed.optimization.decoder import RouteDecoder
from fluxmed.optimization.engine import GeneticOptimizer, GeneticOptimizerConfig
from fluxmed.optimization.fitness import FitnessEvaluator
from fluxmed.optimization.models import (
    DecodedSolution,
    FitnessVector,
    OptimizationDelivery,
    OptimizationProgress,
    TravelMatrix,
)


class OptimizerBenchmarkRunner:
    def __init__(self, ga_config: GeneticOptimizerConfig | None = None) -> None:
        self._ga_config = ga_config or GeneticOptimizerConfig()
        self._fitness = FitnessEvaluator()

    def run(
        self,
        problem: BenchmarkProblem,
        *,
        seeds: tuple[int, ...],
    ) -> BenchmarkReport:
        if not problem.deliveries:
            raise ValueError("Benchmark problem requires deliveries.")
        if not problem.vehicles:
            raise ValueError("Benchmark problem requires vehicles.")
        if not seeds:
            raise ValueError("At least one GA seed is required.")

        runs: list[BenchmarkRun] = []
        convergence: list[BenchmarkConvergencePoint] = []
        runs.append(
            self._run_baseline(
                problem,
                BenchmarkMethod.NEAREST_NEIGHBOR,
                nearest_neighbor_chromosome,
            )
        )
        runs.append(
            self._run_baseline(
                problem,
                BenchmarkMethod.BEST_INSERTION,
                best_insertion_chromosome,
            )
        )

        variants = (
            (
                BenchmarkMethod.GA_BASIC,
                replace(
                    self._ga_config,
                    advanced_pruning_enabled=False,
                    repair_enabled=False,
                ),
            ),
            (
                BenchmarkMethod.GA_PRUNING,
                replace(
                    self._ga_config,
                    advanced_pruning_enabled=True,
                    repair_enabled=False,
                ),
            ),
            (
                BenchmarkMethod.GA_PRUNING_REPAIR,
                replace(
                    self._ga_config,
                    advanced_pruning_enabled=True,
                    repair_enabled=True,
                ),
            ),
        )
        for method, config in variants:
            for seed in seeds:
                run, points = self._run_ga(
                    problem,
                    method=method,
                    config=config,
                    seed=seed,
                )
                runs.append(run)
                convergence.extend(points)

        return BenchmarkReport(
            runs=tuple(runs),
            summaries=self._summaries(problem, runs),
            convergence=tuple(convergence),
        )

    def _run_baseline(
        self,
        problem: BenchmarkProblem,
        method: BenchmarkMethod,
        chromosome_factory: Callable[
            [list[OptimizationDelivery], TravelMatrix],
            tuple[uuid.UUID, ...],
        ],
    ) -> BenchmarkRun:
        decoder = RouteDecoder(
            deliveries=problem.deliveries,
            vehicles=problem.vehicles,
            travel_matrix=problem.travel_matrix,
            operation_start_at=problem.operation_start_at,
            operation_end_at=problem.operation_end_at,
            advanced_pruning_enabled=True,
        )
        started = perf_counter()
        chromosome = chromosome_factory(problem.deliveries, problem.travel_matrix)
        solution = decoder.decode(chromosome)
        fitness = self._fitness.evaluate(solution)
        runtime = perf_counter() - started
        return self._record(
            problem,
            method=method,
            seed=None,
            runtime_seconds=runtime,
            fitness=fitness,
            solution=solution,
            pruning_counts=solution.pruning_counts,
        )

    def _run_ga(
        self,
        problem: BenchmarkProblem,
        *,
        method: BenchmarkMethod,
        config: GeneticOptimizerConfig,
        seed: int,
    ) -> tuple[BenchmarkRun, tuple[BenchmarkConvergencePoint, ...]]:
        optimizer = GeneticOptimizer(config)
        started = perf_counter()
        points: list[BenchmarkConvergencePoint] = []
        best_generation = 0
        time_to_best_seconds = 0.0

        def on_progress(progress: OptimizationProgress) -> None:
            nonlocal best_generation, time_to_best_seconds
            elapsed = perf_counter() - started
            generation = progress.generation
            if progress.improved:
                best_generation = generation
                time_to_best_seconds = elapsed
            fitness = progress.best.fitness
            points.append(
                BenchmarkConvergencePoint(
                    scenario_name=problem.scenario_name,
                    delivery_count=problem.delivery_count,
                    method=method,
                    seed=seed,
                    generation=generation,
                    elapsed_seconds=elapsed,
                    improved=progress.improved,
                    feasible=fitness.feasible,
                    hard_violations=fitness.hard_violations,
                    service_penalty=float(fitness.service_penalty),
                    cost_brl=float(fitness.total_cost_brl),
                    makespan_minutes=float(fitness.makespan_minutes),
                    distance_km=float(fitness.distance_km),
                    vehicles_used=fitness.vehicles_used,
                    diversity_ratio=progress.diversity_ratio,
                    effective_mutation_rate=progress.effective_mutation_rate,
                    immigrants_added=progress.immigrants_added,
                    pruning_counts=dict(progress.pruning_counts),
                )
            )

        result = optimizer.optimize(
            deliveries=problem.deliveries,
            vehicles=problem.vehicles,
            travel_matrix=problem.travel_matrix,
            random_seed=seed,
            operation_start_at=problem.operation_start_at,
            operation_end_at=problem.operation_end_at,
            on_progress=on_progress,
        )
        runtime = perf_counter() - started
        candidate_evaluations = 2 + config.population_size * (result.generations_completed + 1)
        run = self._record(
            problem,
            method=method,
            seed=seed,
            runtime_seconds=runtime,
            fitness=result.best.fitness,
            solution=result.best.solution,
            pruning_counts=result.pruning_counts,
            candidate_evaluations=candidate_evaluations,
            best_generation=best_generation,
            time_to_best_seconds=time_to_best_seconds,
            generations_completed=result.generations_completed,
            stop_reason=result.stop_reason,
        )
        return run, tuple(points)

    @staticmethod
    def _record(
        problem: BenchmarkProblem,
        *,
        method: BenchmarkMethod,
        seed: int | None,
        runtime_seconds: float,
        fitness: FitnessVector,
        solution: DecodedSolution,
        pruning_counts: dict[str, int],
        candidate_evaluations: int | None = None,
        best_generation: int | None = None,
        time_to_best_seconds: float | None = None,
        generations_completed: int | None = None,
        stop_reason: str | None = None,
    ) -> BenchmarkRun:
        route_hard_violation_counts = Counter(
            code for route in solution.routes for code in route.hard_violations
        )
        return BenchmarkRun(
            scenario_name=problem.scenario_name,
            delivery_count=problem.delivery_count,
            method=method,
            seed=seed,
            runtime_seconds=runtime_seconds,
            feasible=fitness.feasible,
            hard_violations=fitness.hard_violations,
            unassigned_delivery_count=len(solution.unassigned_delivery_ids),
            route_hard_violation_counts=dict(route_hard_violation_counts),
            candidate_evaluations=candidate_evaluations,
            best_generation=best_generation,
            time_to_best_seconds=time_to_best_seconds,
            service_penalty=float(fitness.service_penalty),
            critical_risk=float(fitness.critical_risk),
            cost_brl=float(fitness.total_cost_brl),
            makespan_minutes=float(fitness.makespan_minutes),
            travel_minutes=float(fitness.travel_minutes),
            distance_km=float(fitness.distance_km),
            vehicles_used=fitness.vehicles_used,
            pruning_counts=dict(pruning_counts),
            generations_completed=generations_completed,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _summaries(
        problem: BenchmarkProblem,
        runs: list[BenchmarkRun],
    ) -> tuple[BenchmarkSummary, ...]:
        summaries: list[BenchmarkSummary] = []
        for method in BenchmarkMethod:
            method_runs = [run for run in runs if run.method is method]
            if not method_runs:
                continue
            feasible = [run for run in method_runs if run.feasible]
            costs = [run.cost_brl for run in feasible]
            makespans = [run.makespan_minutes for run in feasible]
            evaluations = [
                float(run.candidate_evaluations)
                for run in method_runs
                if run.candidate_evaluations is not None
            ]
            times_to_best = [
                run.time_to_best_seconds
                for run in method_runs
                if run.time_to_best_seconds is not None
            ]
            summaries.append(
                BenchmarkSummary(
                    scenario_name=problem.scenario_name,
                    delivery_count=problem.delivery_count,
                    method=method,
                    runs=len(method_runs),
                    feasible_runs=len(feasible),
                    feasible_rate=len(feasible) / len(method_runs),
                    best_cost_brl=min(costs) if costs else None,
                    mean_cost_brl=fmean(costs) if costs else None,
                    std_cost_brl=pstdev(costs) if len(costs) > 1 else (0.0 if costs else None),
                    worst_cost_brl=max(costs) if costs else None,
                    mean_runtime_seconds=fmean(run.runtime_seconds for run in method_runs),
                    mean_candidate_evaluations=(
                        fmean(evaluations) if evaluations else None
                    ),
                    mean_time_to_best_seconds=(
                        fmean(times_to_best) if times_to_best else None
                    ),
                    best_makespan_minutes=min(makespans) if makespans else None,
                    mean_makespan_minutes=fmean(makespans) if makespans else None,
                )
            )
        return tuple(summaries)
