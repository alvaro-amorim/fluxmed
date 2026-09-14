import uuid
from dataclasses import dataclass
from decimal import Decimal

from fluxmed.optimization.models import (
    DecodedRoute,
    DecodedSolution,
    OptimizationDelivery,
    OptimizationVehicle,
    TravelMatrix,
    ZERO,
)


@dataclass(slots=True)
class _RouteState:
    vehicle: OptimizationVehicle
    delivery_ids: list[uuid.UUID]
    weight_kg: Decimal = ZERO
    volume_m3: Decimal = ZERO

    @property
    def current_location(self) -> uuid.UUID | None:
        if not self.delivery_ids:
            return None
        return self.delivery_ids[-1]


class RouteDecoder:
    def __init__(
        self,
        *,
        deliveries: list[OptimizationDelivery],
        vehicles: list[OptimizationVehicle],
        travel_matrix: TravelMatrix,
    ) -> None:
        self._deliveries = {delivery.id: delivery for delivery in deliveries}
        self._vehicles = tuple(vehicles)
        self._travel_matrix = travel_matrix

    def decode(self, chromosome: tuple[uuid.UUID, ...]) -> DecodedSolution:
        states = [_RouteState(vehicle=vehicle, delivery_ids=[]) for vehicle in self._vehicles]
        unassigned: list[uuid.UUID] = []

        for delivery_id in chromosome:
            delivery = self._deliveries[delivery_id]
            candidate = self._best_vehicle(states, delivery)
            if candidate is None:
                unassigned.append(delivery_id)
                continue
            candidate.delivery_ids.append(delivery_id)
            candidate.weight_kg += delivery.weight_kg
            candidate.volume_m3 += delivery.volume_m3

        routes = tuple(self._finalize_route(state) for state in states if state.delivery_ids)
        return DecodedSolution(routes=routes, unassigned_delivery_ids=tuple(unassigned))

    def _best_vehicle(
        self,
        states: list[_RouteState],
        delivery: OptimizationDelivery,
    ) -> _RouteState | None:
        feasible: list[tuple[tuple[object, ...], _RouteState]] = []
        for state in states:
            vehicle = state.vehicle
            next_weight = state.weight_kg + delivery.weight_kg
            next_volume = state.volume_m3 + delivery.volume_m3
            if next_weight > vehicle.max_payload_kg or next_volume > vehicle.max_volume_m3:
                continue

            current = state.current_location
            direct_return = self._travel_matrix.metric(current, None)
            to_delivery = self._travel_matrix.metric(current, delivery.id)
            delivery_return = self._travel_matrix.metric(delivery.id, None)
            marginal_minutes = (
                to_delivery.travel_minutes
                + delivery_return.travel_minutes
                - direct_return.travel_minutes
            )
            marginal_distance = (
                to_delivery.distance_km + delivery_return.distance_km - direct_return.distance_km
            )
            remaining_weight = vehicle.max_payload_kg - next_weight
            remaining_volume = vehicle.max_volume_m3 - next_volume
            rank = (
                marginal_minutes,
                marginal_distance,
                remaining_weight,
                remaining_volume,
                str(vehicle.id),
            )
            feasible.append((rank, state))

        if not feasible:
            return None
        feasible.sort(key=lambda item: item[0])
        return feasible[0][1]

    def _finalize_route(self, state: _RouteState) -> DecodedRoute:
        distance_km = ZERO
        travel_minutes = ZERO
        service_minutes = 0
        current: uuid.UUID | None = None

        for delivery_id in state.delivery_ids:
            metric = self._travel_matrix.metric(current, delivery_id)
            distance_km += metric.distance_km
            travel_minutes += metric.travel_minutes
            service_minutes += self._deliveries[delivery_id].service_minutes
            current = delivery_id

        return_metric = self._travel_matrix.metric(current, None)
        distance_km += return_metric.distance_km
        travel_minutes += return_metric.travel_minutes
        total_duration = travel_minutes + Decimal(service_minutes)
        vehicle = state.vehicle
        total_cost = (
            vehicle.fixed_route_cost_brl
            + distance_km * vehicle.cost_per_km_brl
            + (total_duration / Decimal("60")) * vehicle.cost_per_hour_brl
        )
        return DecodedRoute(
            vehicle_id=vehicle.id,
            delivery_ids=tuple(state.delivery_ids),
            total_weight_kg=state.weight_kg,
            total_volume_m3=state.volume_m3,
            distance_km=distance_km,
            travel_minutes=travel_minutes,
            service_minutes=service_minutes,
            total_duration_minutes=total_duration,
            total_cost_brl=total_cost,
        )
