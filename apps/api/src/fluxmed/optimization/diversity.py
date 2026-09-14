from itertools import combinations

from fluxmed.optimization.operators import Chromosome


def population_diversity(population: list[Chromosome]) -> float:
    """Return average normalized positional Hamming distance in [0, 1]."""
    if len(population) < 2:
        return 0.0
    gene_count = len(population[0])
    if gene_count == 0:
        return 0.0

    distances: list[float] = []
    for left, right in combinations(population, 2):
        if len(left) != gene_count or len(right) != gene_count:
            raise ValueError("All chromosomes must have the same length.")
        differences = sum(a != b for a, b in zip(left, right, strict=True))
        distances.append(differences / gene_count)
    return sum(distances) / len(distances)
