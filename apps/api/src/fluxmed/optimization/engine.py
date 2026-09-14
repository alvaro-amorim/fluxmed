import random
import time
from collections.abc import Callable
from dataclasses import dataclass

from fluxmed.domain.enums import DeliveryPriority, TemperatureClass, TimeWindowPolicy
from fluxmed.optimization.baselines import (
    best_insertion_chromosome,
    nearest_neighbor_chromosome,
)
from fluxmed.optimization.decoder import RouteDecoder
from fluxmed.optimization.diversity import population_diversity
from fluxmed.optimization.fitness import FitnessEvaluator
from fluxmed.optimization.models import (
    BaselineResult,
    EvaluatedIndividual,
    FitnessVector,
    OptimizationContext,
    OptimizationDelivery,
    OptimizationResult,
    OptimizationVehicle,
    PruningSummary,
    TravelMatrix,
)
from fluxmed.optimization.operators import (
    Chromosome,
    mutate,
    order_crossover,
    tournament_select,
)
from fluxmed.optimization.pruning import PruningTracker
from fluxmed.optimization.repair import repair_candidates

Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class GeneticOptimizerConfig:
    population_size: int = 48
    max_generations: int = 120
    tournament_size: int = 3
    crossover_rate: float = 0.9
    mutation_rate: float = 0.22
    max_adaptive_mutation_rate: float = 0.55
    elitism_fraction: float = 0.05
    stagnation_generations: int = 25
    low_diversity_threshold: float = 0.35
    immigrant_fraction: float = 0.10
    immigrant_stagnation_generations: int = 5
    repair_enabled: bool = True
    time_budget_seconds: float = 30.0
    hard_time_limit_seconds: float = 60.0

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
        if not self.mutation_rate <= self.max_adaptive_mutation_rate <= 1:
            raise ValueError("max_adaptive_mutation_rate must be between mutation_rate and one.")
        if not 0 < self.elitism_fraction < 1:
            raise ValueError("elitism_fraction must be between zero and one.")
        if self.stagnation_generations < 1:
            raise ValueError("stagnation_generations must be positive.")
        if not 0 <= self.low_diversity_threshold <= 1:
            raise ValueError("low_diversity_threshold must be between zero and one.")
        if not 0 <= self.immigrant_fraction < 1:
            raise ValueError("immigrant_fraction must be between zero and one.")
        if self.immigrant_stagnation_generations < 1:
            raise ValueError("immigrant_stagnation_generations must be positive.")
        if self.time_budget_seconds <= 0:
            raise ValueError("time_budget_seconds must be positive.")
        if self.hard_time_limit_seconds < self.time_budget_seconds:
            raise ValueError("hard_time_limit_seconds must be >= time_budget_seconds.")


@dataclass(frozen=True, slots=True)
class _EvaluationOutcome:
    individual: EvaluatedIndividual
    pruning: PruningSummary
    repairs_applied: int = 0


class GeneticOptimizer:
    def __init__(
        self,
        config: GeneticOptimizerConfig | None = None,
        *,
        clock: Clock = time.monotonic,
    ) -> None:
        self.config = config or GeneticOptimizerConfig()
        self.config.validate()
        self._fitness = FitnessEvaluator()
        self._clock = clock

    def optimize(
        self,
        *,
        deliveries: list[OptimizationDelivery],
        vehicles: list[OptimizationVehicle],
        travel_matrix: TravelMatrix,
        random_seed: int,
        context: OptimizationContext | None = None,
    ) -> OptimizationResult:
        if not deliveries:
            raise ValueError("Genetic optimizer requires at least one delivery.")
        if not vehicles:
            raise ValueError("Genetic optimizer requires at least one vehicle.")
        if context is not None:
            context.validate()

        started_at = self._clock()
        rng = random.Random(random_seed)
        decoder = RouteDecoder(
            deliveries=deliveries,
            vehicles=vehicles,
            travel_matrix=travel_matrix,
            context=context,
        )
        pruning_tracker = PruningTracker()
        baselines, baseline_pruning = self._baselines(deliveries, travel_matrix, decoder)
        pruning_tracker.merge(baseline_pruning)
        population = self._initial_population(deliveries, baselines, rng)

        evaluation_outcomes = [
            self._evaluate(
                chromosome,
                decoder,
                deliveries,
                best_known_fitness=None,
            )
            for chromosome in population
        ]
        for outcome in evaluation_outcomes:
            pruning_tracker.merge(outcome.pruning)
        repairs_applied = sum(outcome.repairs_applied for outcome in evaluation_outcomes)
        evaluated = [outcome.individual for outcome in evaluation_outcomes]
        best = min(evaluated, key=lambda item: item.fitness.sort_key())
        best_valid = self._best_valid(evaluated)
        if best_valid is not None:
            best = best_valid

        stagnant = 0
        generations_completed = 0
        stop_reason = "MAX_GENERATIONS"
        diversity_history: list[float] = [
            population_diversity([item.chromosome for item in evaluated])
        ]
        mutation_rate_history: list[float] = []

        for generation in range(1, self.config.max_generations + 1):
            elapsed = self._clock() - started_at
            if elapsed >= self.config.hard_time_limit_seconds:
                stop_reason = "HARD_TIME_LIMIT"
                break
            if elapsed >= self.config.time_budget_seconds and best_valid is not None:
                stop_reason = "TIME_BUDGET"
                break

            generations_completed = generation
            evaluated.sort(key=lambda item: item.fitness.sort_key())
            diversity = population_diversity([item.chromosome for item in evaluated])
            mutation_rate = self._adaptive_mutation_rate(diversity, stagnant)
            mutation_rate_history.append(mutation_rate)
            elite_count = max(1, round(self.config.population_size * self.config.elitism_fraction))
            next_population: list[Chromosome] = [
                item.chromosome for item in evaluated[:elite_count]
            ]

            while len(next_population) < self.config.population_size:
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
                if rng.random() < mutation_rate:
                    child = mutate(child, rng)
                next_population.append(child)

            if (
                diversity < self.config.low_diversity_threshold
                and stagnant >= self.config.immigrant_stagnation_generations
            ):
                self._inject_immigrants(
                    next_population,
                    deliveries=deliveries,
                    elite_count=elite_count,
                    rng=rng,
                )

            best_known_fitness = best_valid.fitness if best_valid is not None else None
            evaluation_outcomes = [
                self._evaluate(
                    chromosome,
                    decoder,
                    deliveries,
                    best_known_fitness=best_known_fitness,
                )
                for chromosome in next_population
            ]
            for outcome in evaluation_outcomes:
                pruning_tracker.merge(outcome.pruning)
            repairs_applied += sum(outcome.repairs_applied for outcome in evaluation_outcomes)
            evaluated = [outcome.individual for outcome in evaluation_outcomes]
            diversity_history.append(
                population_diversity([item.chromosome for item in evaluated])
            )

            generation_best = min(evaluated, key=lambda item: item.fitness.sort_key())
            generation_best_valid = self._best_valid(evaluated)
            candidate_best = generation_best_valid or generation_best
            if candidate_best.fitness.sort_key() < best.fitness.sort_key():
                best = candidate_best
                stagnant = 0
            else:
                stagnant += 1
            if generation_best_valid is not None and (
                best_valid is None
                or generation_best_valid.fitness.sort_key() < best_valid.fitness.sort_key()
            ):
                best_valid = generation_best_valid
                best = generation_best_valid
                stagnant = 0

            elapsed = self._clock() - started_at
            if elapsed >= self.config.hard_time_limit_seconds:
                stop_reason = "HARD_TIME_LIMIT"
                break
            if elapsed >= self.config.time_budget_seconds and best_valid is not None:
                stop_reason = "TIME_BUDGET"
                break
            if stagnant >= self.config.stagnation_generations:
                stop_reason = "EARLY_STOPPING"
                break

        if best_valid is not None:
            best = best_valid
        return OptimizationResult(
            random_seed=random_seed,
            generations_completed=generations_completed,
            stop_reason=stop_reason,
            best=best,
            baselines=baselines,
            pruning=pruning_tracker.summary(),
            repairs_applied=repairs_applied,
            diversity_history=tuple(diversity_history),
            mutation_rate_history=tuple(mutation_rate_history),
            elapsed_seconds=max(0.0, self._clock() - started_at),
        )

    def _baselines(
        self,
        deliveries: list[OptimizationDelivery],
        travel_matrix: TravelMatrix,
        decoder: RouteDecoder,
    ) -> tuple[tuple[BaselineResult, ...], PruningSummary]:
        baseline_specs = (
            ("NEAREST_NEIGHBOR", nearest_neighbor_chromosome(deliveries, travel_matrix)),
            ("BEST_INSERTION", best_insertion_chromosome(deliveries, travel_matrix)),
        )
        results: list[BaselineResult] = []
        pruning_tracker = PruningTracker()
        for name, chromosome in baseline_specs:
            decoded = decoder.decode_with_pruning(chromosome)
            pruning_tracker.merge(decoded.pruning)
            fitness = self._fitness.evaluate(decoded.solution)
            results.append(
                BaselineResult(
                    name=name,
                    chromosome=chromosome,
                    solution=decoded.solution,
                    fitness=fitness,
                )
            )
        return tuple(results), pruning_tracker.summary()

    def _initial_population(
        self,
        deliveries: list[OptimizationDelivery],
        baselines: tuple[BaselineResult, ...],
        rng: random.Random,
    ) -> list[Chromosome]:
        chromosomes: list[Chromosome] = [baseline.chromosome for baseline in baselines]
        constrained_seed = self._constrained_first_chromosome(deliveries)
        if constrained_seed not in chromosomes:
            chromosomes.append(constrained_seed)
        for seed in tuple(chromosomes):
            for _ in range(3):
                chromosomes.append(mutate(seed, rng))

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
        deliveries: list[OptimizationDelivery],
        *,
        best_known_fitness: FitnessVector | None,
    ) -> _EvaluationOutcome:
        pruning_tracker = PruningTracker()
        decoded = decoder.decode_with_pruning(
            chromosome,
            best_known_fitness=best_known_fitness,
        )
        pruning_tracker.merge(decoded.pruning)
        best_individual = EvaluatedIndividual(
            chromosome=chromosome,
            solution=decoded.solution,
            fitness=self._fitness.evaluate(decoded.solution),
        )
        repairs_applied = 0

        if self.config.repair_enabled and decoded.solution.unassigned_delivery_ids:
            for repaired_chromosome in repair_candidates(chromosome, decoded.solution, deliveries):
                repaired = decoder.decode_with_pruning(
                    repaired_chromosome,
                    best_known_fitness=best_known_fitness,
                )
                pruning_tracker.merge(repaired.pruning)
                repaired_individual = EvaluatedIndividual(
                    chromosome=repaired_chromosome,
                    solution=repaired.solution,
                    fitness=self._fitness.evaluate(repaired.solution),
                )
                if repaired_individual.fitness.sort_key() < best_individual.fitness.sort_key():
                    best_individual = repaired_individual
                    repairs_applied = 1

        return _EvaluationOutcome(
            individual=best_individual,
            pruning=pruning_tracker.summary(),
            repairs_applied=repairs_applied,
        )

    def _adaptive_mutation_rate(self, diversity: float, stagnant: int) -> float:
        rate = self.config.mutation_rate
        threshold = self.config.low_diversity_threshold
        if threshold > 0 and diversity < threshold:
            pressure = 1.0 - diversity / threshold
            rate += (self.config.max_adaptive_mutation_rate - rate) * pressure
        if stagnant >= max(1, self.config.stagnation_generations // 2):
            rate = max(
                rate,
                (self.config.mutation_rate + self.config.max_adaptive_mutation_rate) / 2,
            )
        return min(self.config.max_adaptive_mutation_rate, rate)

    def _inject_immigrants(
        self,
        population: list[Chromosome],
        *,
        deliveries: list[OptimizationDelivery],
        elite_count: int,
        rng: random.Random,
    ) -> None:
        replaceable = len(population) - elite_count
        immigrant_count = min(
            replaceable,
            max(1, round(self.config.population_size * self.config.immigrant_fraction)),
        )
        genes = [delivery.id for delivery in deliveries]
        for offset in range(immigrant_count):
            candidate = list(genes)
            rng.shuffle(candidate)
            population[len(population) - 1 - offset] = tuple(candidate)

    @staticmethod
    def _best_valid(evaluated: list[EvaluatedIndividual]) -> EvaluatedIndividual | None:
        feasible = [item for item in evaluated if item.fitness.feasible]
        if not feasible:
            return None
        return min(feasible, key=lambda item: item.fitness.sort_key())

    @staticmethod
    def _constrained_first_chromosome(
        deliveries: list[OptimizationDelivery],
    ) -> Chromosome:
        priority_rank = {
            DeliveryPriority.CRITICAL: 0,
            DeliveryPriority.HIGH: 1,
            DeliveryPriority.NORMAL: 2,
            DeliveryPriority.LOW: 3,
        }
        ordered = sorted(
            deliveries,
            key=lambda delivery: (
                0 if delivery.temperature_class is TemperatureClass.REFRIGERATED else 1,
                0 if delivery.time_window_policy is TimeWindowPolicy.HARD else 1,
                priority_rank[delivery.priority],
                (
                    delivery.time_window_end.isoformat()
                    if delivery.time_window_end is not None
                    else "9999"
                ),
                str(delivery.id),
            ),
        )
        return tuple(delivery.id for delivery in ordered)
