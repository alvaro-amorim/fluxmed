import random
from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class GeneticOptimizerConfig:
    population_size: int = 48
    max_generations: int = 120
    tournament_size: int = 3
    crossover_rate: float = 0.9
    mutation_rate: float = 0.22
    elitism_fraction: float = 0.05
    stagnation_generations: int = 25

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
        if not 0 < self.elitism_fraction < 1:
            raise ValueError("elitism_fraction must be between zero and one.")
        if self.stagnation_generations < 1:
            raise ValueError("stagnation_generations must be positive.")


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
    ) -> OptimizationResult:
        if not deliveries:
            raise ValueError("Genetic optimizer requires at least one delivery.")
        if not vehicles:
            raise ValueError("Genetic optimizer requires at least one vehicle.")

        rng = random.Random(random_seed)
        decoder = RouteDecoder(
            deliveries=deliveries,
            vehicles=vehicles,
            travel_matrix=travel_matrix,
        )
        baselines = self._baselines(deliveries, travel_matrix, decoder)
        population = self._initial_population(deliveries, baselines, rng)
        evaluated = [self._evaluate(chromosome, decoder) for chromosome in population]
        best = min(evaluated, key=lambda item: item.fitness.sort_key())
        stagnant = 0
        generations_completed = 0
        stop_reason = "MAX_GENERATIONS"

        for generation in range(1, self.config.max_generations + 1):
            generations_completed = generation
            evaluated.sort(key=lambda item: item.fitness.sort_key())
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
                if rng.random() < self.config.mutation_rate:
                    child = mutate(child, rng)
                next_population.append(child)

            evaluated = [self._evaluate(chromosome, decoder) for chromosome in next_population]
            generation_best = min(evaluated, key=lambda item: item.fitness.sort_key())
            if generation_best.fitness.sort_key() < best.fitness.sort_key():
                best = generation_best
                stagnant = 0
            else:
                stagnant += 1

            if stagnant >= self.config.stagnation_generations:
                stop_reason = "EARLY_STOPPING"
                break

        return OptimizationResult(
            random_seed=random_seed,
            generations_completed=generations_completed,
            stop_reason=stop_reason,
            best=best,
            baselines=baselines,
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
            evaluated = self._evaluate(chromosome, decoder)
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

    def _evaluate(self, chromosome: Chromosome, decoder: RouteDecoder) -> EvaluatedIndividual:
        solution = decoder.decode(chromosome)
        return EvaluatedIndividual(
            chromosome=chromosome,
            solution=solution,
            fitness=self._fitness.evaluate(solution),
        )
