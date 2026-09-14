import random
import uuid

from fluxmed.optimization.models import DecodedSolution

Chromosome = tuple[uuid.UUID, ...]


def repair_chromosome(
    chromosome: Chromosome,
    solution: DecodedSolution,
    rng: random.Random,
) -> Chromosome:
    """Move currently unassigned deliveries earlier without inventing or deleting genes."""
    if not solution.unassigned_delivery_ids:
        return chromosome

    blocked = set(solution.unassigned_delivery_ids)
    prioritized = [gene for gene in chromosome if gene in blocked]
    retained = [gene for gene in chromosome if gene not in blocked]
    rng.shuffle(prioritized)

    repaired: list[uuid.UUID] = []
    while prioritized or retained:
        if prioritized:
            repaired.append(prioritized.pop())
        if retained:
            repaired.append(retained.pop(0))
    return tuple(repaired)
