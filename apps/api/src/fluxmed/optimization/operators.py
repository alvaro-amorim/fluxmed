import random
import uuid

from fluxmed.optimization.models import EvaluatedIndividual

Chromosome = tuple[uuid.UUID, ...]


def order_crossover(parent_a: Chromosome, parent_b: Chromosome, rng: random.Random) -> Chromosome:
    if len(parent_a) != len(parent_b) or set(parent_a) != set(parent_b):
        raise ValueError("OX parents must contain the same unique genes.")
    size = len(parent_a)
    if size < 2:
        return parent_a

    start, end = sorted(rng.sample(range(size), 2))
    end += 1
    child: list[uuid.UUID | None] = [None] * size
    child[start:end] = parent_a[start:end]
    inherited = set(parent_a[start:end])
    fill = [gene for gene in parent_b if gene not in inherited]
    positions = list(range(end, size)) + list(range(0, start))
    for position, gene in zip(positions, fill, strict=True):
        child[position] = gene

    if any(gene is None for gene in child):
        raise RuntimeError("OX produced an incomplete chromosome.")
    result = tuple(gene for gene in child if gene is not None)
    if len(result) != size or set(result) != set(parent_a):
        raise RuntimeError("OX violated permutation invariants.")
    return result


def swap_mutation(chromosome: Chromosome, rng: random.Random) -> Chromosome:
    if len(chromosome) < 2:
        return chromosome
    left, right = rng.sample(range(len(chromosome)), 2)
    genes = list(chromosome)
    genes[left], genes[right] = genes[right], genes[left]
    return tuple(genes)


def insertion_mutation(chromosome: Chromosome, rng: random.Random) -> Chromosome:
    if len(chromosome) < 2:
        return chromosome
    source, target = rng.sample(range(len(chromosome)), 2)
    genes = list(chromosome)
    gene = genes.pop(source)
    genes.insert(target, gene)
    return tuple(genes)


def inversion_mutation(chromosome: Chromosome, rng: random.Random) -> Chromosome:
    if len(chromosome) < 2:
        return chromosome
    left, right = sorted(rng.sample(range(len(chromosome)), 2))
    genes = list(chromosome)
    genes[left : right + 1] = reversed(genes[left : right + 1])
    return tuple(genes)


def mutate(chromosome: Chromosome, rng: random.Random) -> Chromosome:
    operator = rng.choice((swap_mutation, insertion_mutation, inversion_mutation))
    return operator(chromosome, rng)


def tournament_select(
    population: list[EvaluatedIndividual],
    *,
    tournament_size: int,
    rng: random.Random,
) -> EvaluatedIndividual:
    if not population:
        raise ValueError("Tournament selection requires a non-empty population.")
    sample_size = min(max(1, tournament_size), len(population))
    candidates = rng.sample(population, sample_size)
    return min(candidates, key=lambda item: item.fitness.sort_key())
