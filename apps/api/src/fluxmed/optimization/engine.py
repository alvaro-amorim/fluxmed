import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from fluxmed.optimization.baselines import (
    best_insertion_chromosome,
    nearest_neighbor_chromosome,
)
from fluxmed.optimization.decoder import RouteDecoder
from fluxmed.optimization.fitness import FitnessEvaluator
from fluxmed.optimization.models import (
    BaselineResult,
    EvaluatedIndividual,
    OptimizationDelivery,
    OptimizationProgress,
    OptimizationResult,
    OptimizationVehicle,
    TravelMatrix,
)
from fluxmed.optimization.operators import (
    Chromosome,
    mutate,
    order_crossover,
    tournament_select,
)
from fluxmed.optimization.repair import repair_chromosome

ProgressCallback = Callable[[OptimizationProgress], None]
CancelCheck = Callable[[], bool]


class OptimizationCancelled(RuntimeError):
    """Raised when a caller requests cooperative GA cancellation."""


@dataclass(frozen=True, slots=True)
class GeneticOptimizerConfig:
    population_size: int = 48
    max_generations: int = 120
    tournament_size: int = 3
    crossover_rate: float = 0.9
    mutation_rate: float = 0.22
    max_mutation_rate: float = 0.55
    elitism_fraction: float = 0.05
    stagnation_generations: int = 25
    low_diversity_threshold: float = 0.35
    immigrant_fraction: float = 0.10
    advanced_pruning_enabled: bool = True
    repair_enabled: bool = True

    def validate(self) -> None:
        if self.population_size < 4:
            raise ValueError("population_size must be at least 4.")
        if self.max_generations < 1:
            raise ValueError("max_generations must be positive.")
        if self.tournament_size < 1:
            raise ValueError("tournament_size must be positive.")
        if not 0 <= self.crossover_rate <= 1:
            raise ValueError("crossover_rate must be between zero and one.")
        if not 0 <= self.mutation_rate <= 1:
            raise ValueError("mutation_rate must be between zero and one.")
        if not self.mutation_rate <= self.max_mutation_rate <= 1:
            raise ValueError("max_mutation_rate must be >= mutation_rate and <= 1.")
        if not 0 < self.elitism_fraction < 1:
            raise ValueError("elitism_fraction must be between zero and one.")
        if self.stagnation_generations < 1:
            raise ValueError("stagnation_generations must be positive.")
        if not 0 < self.low_diversity_threshold <= 1:
            raise ValueError("low_diversity_threshold must be in (0, 1].")
        if not 0 <= self.immigrant_fraction < 1:
            raise ValueError("immigrant_fraction must be in [0, 1).")


class GeneticOptimizer:
    def __init__(self, config: GeneticOptimizerConfig | None = None) -> None:
        self.config = config or GeneticOptimizerConfig()
        self.config.validate()
        self._fitness = FitnessEvaluator()

    def optimize(
        self,
        *,
        deliveries: list[OptimizationDelivery],
        vehicles: list[OptimizationVehicle],
        travel_matrix: TravelMatrix,
        random_seed: int,
        operation_start_at: datetime | None = None,
        operation_end_at: datetime | None = None,
        on_progress: ProgressCallback | None = None,
        should_cancel: CancelCheck | None = None,
    ) -> OptimizationResult:
        if not deliveries:
            raise ValueError("Genetic optimizer requires at least one delivery.")
        if not vehicles:
            raise ValueError("Genetic optimizer requires at least one vehicle.")
        self._raise_if_cancelled(should_cancel)

        rng = random.Random(random_seed)
        decoder = RouteDecoder(
            deliveries=deliveries,
            vehicles=vehicles,
            travel_matrix=travel_matrix,
            operation_start_at=operation_start_at,
            operation_end_at=operation_end_at,
            advanced_pruning_enabled=self.config.advanced_pruning_enabled,
        )
        baselines = self._baselines(deliveries, travel_matrix, decoder)
        self._raise_if_cancelled(should_cancel)
        population = self._initial_population(deliveries, baselines, rng)
        evaluated = [self._evaluate(chromosome, decoder, rng) for chromosome in population]
        best = min(evaluated, key=lambda item: item.fitness.sort_key())
        stagnant = 0
        generations_completed = 0
        stop_reason = "MAX_GENERATIONS"
        effective_mutation_rate = self.config.mutation_rate
        immigrants_added = 0
        diversity_ratio = self._diversity_ratio(evaluated)
        self._emit_progress(
            on_progress,
            generation=0,
            best=best,
            improved=True,
            diversity_ratio=diversity_ratio,
            effective_mutation_rate=effective_mutation_rate,
            immigrants_added=immigrants_added,
        )

        for generation in range(1, self.config.max_generations + 1):
            self._raise_if_cancelled(should_cancel)
            generations_completed = generation
            evaluated.sort(key=lambda item: item.fitness.sort_key())
            diversity_ratio = self._diversity_ratio(evaluated)
            effective_mutation_rate = self._adaptive_mutation_rate(stagnant, diversity_ratio)
            elite_count = max(1, round(self.config.population_size * self.config.elitism_fraction))
            next_population: list[Chromosome] = [
                item.chromosome for item in evaluated[:elite_count]
            ]

            immigrant_target = 0
            if diversity_ratio < self.config.low_diversity_threshold:
                immigrant_target = max(
                    1,
                    round(self.config.population_size * self.config.immigrant_fraction),
                )

            breeding_target = self.config.population_size - immigrant_target
            while len(next_population) < breeding_target:
                parent_a = tournament_select(
                    evaluated,
                    tournament_size=self.config.tournament_size,
                    rng=rng,
                )
                parent_b = tournament_select(
                    evaluated,
                    tournament_size=self.config.tournament_size,
                    rng=rng,
                )
                if rng.random() < self.config.crossover_rate:
                    child = order_crossover(parent_a.chromosome, parent_b.chromosome, rng)
                else:
                    child = parent_a.chromosome
                if rng.random() < effective_mutation_rate:
                    child = mutate(child, rng)
                next_population.append(child)

            genes = [delivery.id for delivery in deliveries]
            for _ in range(immigrant_target):
                candidate = list(genes)
                rng.shuffle(candidate)
                next_population.append(tuple(candidate))
                immigrants_added += 1

            evaluated = [self._evaluate(chromosome, decoder, rng) for chromosome in next_population]
            generation_best = min(evaluated, key=lambda item: item.fitness.sort_key())
            improved = generation_best.fitness.sort_key() < best.fitness.sort_key()
            if improved:
                best = generation_best
                stagnant = 0
            else:
                stagnant += 1

            diversity_ratio = self._diversity_ratio(evaluated)
            self._emit_progress(
                on_progress,
                generation=generation,
                best=best,
                improved=improved,
                diversity_ratio=diversity_ratio,
                effective_mutation_rate=effective_mutation_rate,
                immigrants_added=immigrants_added,
            )
            self._raise_if_cancelled(should_cancel)

            if stagnant >= self.config.stagnation_generations:
                stop_reason = "EARLY_STOPPING"
                break

        return OptimizationResult(
            random_seed=random_seed,
            generations_completed=generations_completed,
            stop_reason=stop_reason,
            best=best,
            baselines=baselines,
            diversity_ratio=diversity_ratio,
            effective_mutation_rate=effective_mutation_rate,
            immigrants_added=immigrants_added,
            pruning_counts=dict(best.solution.pruning_counts),
        )

    def _baselines(
        self,
        deliveries: list[OptimizationDelivery],
        travel_matrix: TravelMatrix,
        decoder: RouteDecoder,
    ) -> tuple[BaselineResult, ...]:
        baseline_specs = (
            ("NEAREST_NEIGHBOR", nearest_neighbor_chromosome(deliveries, travel_matrix)),
            ("BEST_INSERTION", best_insertion_chromosome(deliveries, travel_matrix)),
        )
        results: list[BaselineResult] = []
        for name, chromosome in baseline_specs:
            evaluated = self._evaluate(chromosome, decoder, random.Random(0))
            results.append(
                BaselineResult(
                    name=name,
                    chromosome=chromosome,
                    solution=evaluated.solution,
                    fitness=evaluated.fitness,
                )
            )
        return tuple(results)

    def _initial_population(
        self,
        deliveries: list[OptimizationDelivery],
        baselines: tuple[BaselineResult, ...],
        rng: random.Random,
    ) -> list[Chromosome]:
        chromosomes: list[Chromosome] = [baseline.chromosome for baseline in baselines]
        for baseline in baselines:
            for _ in range(3):
                chromosomes.append(mutate(baseline.chromosome, rng))

        genes = [delivery.id for delivery in deliveries]
        while len(chromosomes) < self.config.population_size:
            candidate = list(genes)
            rng.shuffle(candidate)
            chromosomes.append(tuple(candidate))
        return chromosomes[: self.config.population_size]

    def _evaluate(
        self,
        chromosome: Chromosome,
        decoder: RouteDecoder,
        rng: random.Random,
    ) -> EvaluatedIndividual:
        solution = decoder.decode(chromosome)
        if self.config.repair_enabled and solution.unassigned_delivery_ids:
            repaired_chromosome = repair_chromosome(chromosome, solution, rng)
            repaired_solution = decoder.decode(repaired_chromosome)
            if (
                self._fitness.evaluate(repaired_solution).sort_key()
                < self._fitness.evaluate(solution).sort_key()
            ):
                chromosome = repaired_chromosome
                solution = repaired_solution
        return EvaluatedIndividual(
            chromosome=chromosome,
            solution=solution,
            fitness=self._fitness.evaluate(solution),
        )

    def _adaptive_mutation_rate(self, stagnant: int, diversity_ratio: float) -> float:
        pressure = stagnant / self.config.stagnation_generations
        if diversity_ratio < self.config.low_diversity_threshold:
            pressure = max(pressure, 0.75)
        return min(
            self.config.max_mutation_rate,
            self.config.mutation_rate
            + (self.config.max_mutation_rate - self.config.mutation_rate) * pressure,
        )

    @staticmethod
    def _diversity_ratio(evaluated: list[EvaluatedIndividual]) -> float:
        if not evaluated:
            return 0.0
        unique = len({item.chromosome for item in evaluated})
        return unique / len(evaluated)

    @staticmethod
    def _raise_if_cancelled(should_cancel: CancelCheck | None) -> None:
        if should_cancel is not None and should_cancel():
            raise OptimizationCancelled("Optimization cancelled by request.")

    @staticmethod
    def _emit_progress(
        callback: ProgressCallback | None,
        *,
        generation: int,
        best: EvaluatedIndividual,
        improved: bool,
        diversity_ratio: float,
        effective_mutation_rate: float,
        immigrants_added: int,
    ) -> None:
        if callback is None:
            return
        callback(
            OptimizationProgress(
                generation=generation,
                best=best,
                improved=improved,
                diversity_ratio=diversity_ratio,
                effective_mutation_rate=effective_mutation_rate,
                immigrants_added=immigrants_added,
                pruning_counts=dict(best.solution.pruning_counts),
            )
        )
