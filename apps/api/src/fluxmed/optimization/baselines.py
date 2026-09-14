import uuid
from decimal import Decimal

from fluxmed.optimization.models import OptimizationDelivery, TravelMatrix


def nearest_neighbor_chromosome(
    deliveries: list[OptimizationDelivery],
    travel_matrix: TravelMatrix,
) -> tuple[uuid.UUID, ...]:
    remaining = {delivery.id for delivery in deliveries}
    chromosome: list[uuid.UUID] = []
    current: uuid.UUID | None = None

    while remaining:
        next_delivery = min(
            remaining,
            key=lambda delivery_id: (
                travel_matrix.metric(current, delivery_id).travel_minutes,
                travel_matrix.metric(current, delivery_id).distance_km,
                str(delivery_id),
            ),
        )
        chromosome.append(next_delivery)
        remaining.remove(next_delivery)
        current = next_delivery
    return tuple(chromosome)


def best_insertion_chromosome(
    deliveries: list[OptimizationDelivery],
    travel_matrix: TravelMatrix,
) -> tuple[uuid.UUID, ...]:
    if not deliveries:
        return ()

    remaining = {delivery.id for delivery in deliveries}
    first = min(
        remaining,
        key=lambda delivery_id: (
            travel_matrix.metric(None, delivery_id).travel_minutes,
            travel_matrix.metric(None, delivery_id).distance_km,
            str(delivery_id),
        ),
    )
    route = [first]
    remaining.remove(first)

    while remaining:
        best_choice: tuple[tuple[Decimal, Decimal, str, int], uuid.UUID, int] | None = None
        for delivery_id in sorted(remaining, key=str):
            for position in range(len(route) + 1):
                previous = None if position == 0 else route[position - 1]
                following = None if position == len(route) else route[position]
                added_time = (
                    travel_matrix.metric(previous, delivery_id).travel_minutes
                    + travel_matrix.metric(delivery_id, following).travel_minutes
                    - travel_matrix.metric(previous, following).travel_minutes
                )
                added_distance = (
                    travel_matrix.metric(previous, delivery_id).distance_km
                    + travel_matrix.metric(delivery_id, following).distance_km
                    - travel_matrix.metric(previous, following).distance_km
                )
                rank = (added_time, added_distance, str(delivery_id), position)
                candidate = (rank, delivery_id, position)
                if best_choice is None or candidate[0] < best_choice[0]:
                    best_choice = candidate
        if best_choice is None:
            raise RuntimeError("Best Insertion could not choose a remaining delivery.")
        _, delivery_id, position = best_choice
        route.insert(position, delivery_id)
        remaining.remove(delivery_id)

    return tuple(route)
