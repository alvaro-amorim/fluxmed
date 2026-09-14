import uuid

from fluxmed.domain.enums import DeliveryPriority, TemperatureClass, TimeWindowPolicy
from fluxmed.optimization.models import DecodedSolution, OptimizationDelivery
from fluxmed.optimization.operators import Chromosome

_PRIORITY_RANK = {
    DeliveryPriority.CRITICAL: 0,
    DeliveryPriority.HIGH: 1,
    DeliveryPriority.NORMAL: 2,
    DeliveryPriority.LOW: 3,
}


def repair_candidates(
    chromosome: Chromosome,
    solution: DecodedSolution,
    deliveries: list[OptimizationDelivery],
) -> tuple[Chromosome, ...]:
    """Return deterministic permutation repairs without inventing or dropping genes."""
    if not solution.unassigned_delivery_ids:
        return ()

    delivery_by_id = {delivery.id: delivery for delivery in deliveries}
    unassigned = set(solution.unassigned_delivery_ids)
    constrained = sorted(
        unassigned,
        key=lambda delivery_id: _constraint_rank(delivery_by_id[delivery_id]),
    )
    assigned = [gene for gene in chromosome if gene not in unassigned]

    front_loaded = tuple([*constrained, *assigned])
    interleaved = _interleave_constrained(constrained, assigned)
    candidates = []
    for candidate in (front_loaded, interleaved):
        if candidate != chromosome and candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)


def _constraint_rank(delivery: OptimizationDelivery) -> tuple[object, ...]:
    return (
        0 if delivery.temperature_class is TemperatureClass.REFRIGERATED else 1,
        0 if delivery.time_window_policy is TimeWindowPolicy.HARD else 1,
        _PRIORITY_RANK[delivery.priority],
        delivery.time_window_end.isoformat() if delivery.time_window_end is not None else "9999",
        str(delivery.id),
    )


def _interleave_constrained(
    constrained: list[uuid.UUID],
    assigned: list[uuid.UUID],
) -> Chromosome:
    if not constrained:
        return tuple(assigned)
    output = list(assigned)
    step = max(1, len(output) // (len(constrained) + 1))
    offset = 0
    for index, delivery_id in enumerate(constrained):
        position = min(len(output), (index + 1) * step + offset)
        output.insert(position, delivery_id)
        offset += 1
    return tuple(output)
