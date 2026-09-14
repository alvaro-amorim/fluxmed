import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal

from fluxmed.domain.enums import DeliveryPriority, TemperatureClass, TimeWindowPolicy
from fluxmed.optimization.models import (
    ZERO,
    DecodedRoute,
    DecodedSolution,
    DecodedStop,
    FitnessVector,
    OptimizationContext,
    OptimizationDelivery,
    OptimizationVehicle,
    PruningReason,
    PruningSummary,
    TravelMatrix,
    TravelMetric,
)
from fluxmed.optimization.pruning import PruningTracker

_PRIORITY_WEIGHT: dict[DeliveryPriority, Decimal] = {
    DeliveryPriority.CRITICAL: Decimal("4"),
    DeliveryPriority.HIGH: Decimal("2"),
    DeliveryPriority.NORMAL: Decimal("1"),
    DeliveryPriority.LOW: Decimal("0.5"),
}
_CRITICAL_BUFFER_MINUTES: dict[DeliveryPriority, Decimal] = {
    DeliveryPriority.CRITICAL: Decimal("30"),
    DeliveryPriority.HIGH: Decimal("15"),
    DeliveryPriority.NORMAL: ZERO,
    DeliveryPriority.LOW: ZERO,
}


@dataclass(slots=True)
class _RouteState:
    vehicle: OptimizationVehicle
    delivery_ids: list[uuid.UUID] = field(default_factory=list)
    stops: list[DecodedStop] = field(default_factory=list)
    weight_kg: Decimal = ZERO
    volume_m3: Decimal = ZERO
    distance_km: Decimal = ZERO
    travel_minutes: Decimal = ZERO
    service_minutes: int = 0
    current_at: datetime | None = None

    @property
    def current_location(self) -> uuid.UUID | None:
        if not self.delivery_ids:
            return None
        return self.delivery_ids[-1]


@dataclass(frozen=True, slots=True)
class _Candidate:
    state_index: int
    stop: DecodedStop
    leg: TravelMetric
    return_leg: TravelMetric
    projected_weight_kg: Decimal
    projected_volume_m3: Decimal
    projected_distance_with_return_km: Decimal
    projected_return_at: datetime | None
    projected_cost_brl: Decimal
    rank: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class DecodeOutcome:
    solution: DecodedSolution
    pruning: PruningSummary


class RouteDecoder:
    def __init__(
        self,
        *,
        deliveries: list[OptimizationDelivery],
        vehicles: list[OptimizationVehicle],
        travel_matrix: TravelMatrix,
        context: OptimizationContext | None = None,
    ) -> None:
        self._deliveries = {delivery.id: delivery for delivery in deliveries}
        self._vehicles = tuple(vehicles)
        self._travel_matrix = travel_matrix
        self._context = context
        if context is not None:
            context.validate()

    def decode(self, chromosome: tuple[uuid.UUID, ...]) -> DecodedSolution:
        return self.decode_with_pruning(chromosome).solution

    def decode_with_pruning(
        self,
        chromosome: tuple[uuid.UUID, ...],
        *,
        best_known_fitness: FitnessVector | None = None,
    ) -> DecodeOutcome:
        states = [
            _RouteState(
                vehicle=vehicle,
                current_at=(self._context.operation_start_at if self._context is not None else None),
            )
            for vehicle in self._vehicles
        ]
        unassigned: list[uuid.UUID] = []
        tracker = PruningTracker()

        for index, delivery_id in enumerate(chromosome):
            delivery = self._deliveries[delivery_id]
            remaining_ids = chromosome[index + 1 :]
            candidates: list[_Candidate] = []
            for state_index, state in enumerate(states):
                candidate, reason = self._project_candidate(
                    state_index=state_index,
                    state=state,
                    delivery=delivery,
                    remaining_ids=remaining_ids,
                )
                if candidate is None:
                    if reason is not None:
                        tracker.record(reason)
                    continue

                hypothetical = self._states_after_candidate(states, candidate, delivery)
                if remaining_ids and not self._future_feasible(hypothetical, remaining_ids):
                    tracker.record(PruningReason.FUTURE_INFEASIBILITY)
                    continue
                if self._cannot_beat_best(hypothetical, best_known_fitness):
                    tracker.record(
                        PruningReason.LOWER_BOUND,
                        avoided_full_evaluation=True,
                    )
                    continue
                candidates.append(candidate)

            candidates = self._remove_symmetric_dominated(states, candidates, tracker)
            if not candidates:
                unassigned.append(delivery_id)
                continue

            candidate = min(candidates, key=lambda item: item.rank)
            self._apply_candidate(states[candidate.state_index], candidate, delivery)

        routes = tuple(self._finalize_route(state) for state in states if state.delivery_ids)
        return DecodeOutcome(
            solution=DecodedSolution(
                routes=routes,
                unassigned_delivery_ids=tuple(unassigned),
            ),
            pruning=tracker.summary(),
        )

    def _project_candidate(
        self,
        *,
        state_index: int,
        state: _RouteState,
        delivery: OptimizationDelivery,
        remaining_ids: tuple[uuid.UUID, ...],
    ) -> tuple[_Candidate | None, PruningReason | None]:
        vehicle = state.vehicle
        if (
            delivery.temperature_class is TemperatureClass.REFRIGERATED
            and not vehicle.refrigerated
        ):
            return None, PruningReason.REFRIGERATION_INCOMPATIBLE

        projected_weight = state.weight_kg + delivery.weight_kg
        if projected_weight > vehicle.max_payload_kg:
            return None, PruningReason.CAPACITY_EXCEEDED
        projected_volume = state.volume_m3 + delivery.volume_m3
        if projected_volume > vehicle.max_volume_m3:
            return None, PruningReason.VOLUME_EXCEEDED

        try:
            leg = self._travel_matrix.metric(
                state.current_location,
                delivery.id,
                state.current_at,
            )
        except KeyError:
            return None, PruningReason.ROAD_ACCESS_IMPOSSIBLE

        arrival_at = self._plus_minutes(state.current_at, leg.travel_minutes)
        service_start_at = arrival_at
        if (
            service_start_at is not None
            and delivery.time_window_start is not None
            and service_start_at < delivery.time_window_start
        ):
            service_start_at = delivery.time_window_start

        if (
            delivery.time_window_policy is TimeWindowPolicy.HARD
            and delivery.time_window_end is not None
            and service_start_at is not None
            and service_start_at > delivery.time_window_end
        ):
            return None, PruningReason.HARD_TIME_WINDOW_IMPOSSIBLE

        departure_at = self._plus_minutes(
            service_start_at,
            Decimal(delivery.service_minutes),
        )
        try:
            return_leg = self._travel_matrix.metric(delivery.id, None, departure_at)
        except KeyError:
            return None, PruningReason.ROAD_ACCESS_IMPOSSIBLE

        projected_distance_with_return = state.distance_km + leg.distance_km + return_leg.distance_km
        if projected_distance_with_return > self._effective_range(vehicle):
            return None, PruningReason.RANGE_IMPOSSIBLE

        projected_return_at = self._plus_minutes(departure_at, return_leg.travel_minutes)
        if (
            self._context is not None
            and projected_return_at is not None
            and projected_return_at > self._context.operation_end_at
        ):
            return None, PruningReason.END_OF_SHIFT_IMPOSSIBLE

        lateness = self._lateness_minutes(delivery, service_start_at)
        slack = self._slack_minutes(delivery, service_start_at)
        service_penalty = (
            lateness * _PRIORITY_WEIGHT[delivery.priority]
            if delivery.time_window_policy is TimeWindowPolicy.SOFT
            else ZERO
        )
        critical_risk = self._critical_risk(delivery, slack)
        stop = DecodedStop(
            delivery_id=delivery.id,
            arrival_at=arrival_at,
            service_start_at=service_start_at,
            departure_at=departure_at,
            lateness_minutes=lateness,
            slack_minutes=slack,
            service_penalty=service_penalty,
            critical_risk=critical_risk,
        )
        projected_duration = self._projected_duration(
            state=state,
            leg=leg,
            delivery=delivery,
            projected_return_at=projected_return_at,
            return_leg=return_leg,
        )
        projected_cost = (
            vehicle.fixed_route_cost_brl
            + projected_distance_with_return * vehicle.cost_per_km_brl
            + (projected_duration / Decimal("60")) * vehicle.cost_per_hour_brl
        )
        scarce_penalty = self._scarce_resource_penalty(vehicle, delivery, remaining_ids)
        rank = (
            scarce_penalty,
            service_penalty,
            critical_risk,
            projected_cost,
            projected_duration,
            projected_distance_with_return,
            vehicle.max_payload_kg - projected_weight,
            vehicle.max_volume_m3 - projected_volume,
            str(vehicle.id),
        )
        return (
            _Candidate(
                state_index=state_index,
                stop=stop,
                leg=leg,
                return_leg=return_leg,
                projected_weight_kg=projected_weight,
                projected_volume_m3=projected_volume,
                projected_distance_with_return_km=projected_distance_with_return,
                projected_return_at=projected_return_at,
                projected_cost_brl=projected_cost,
                rank=rank,
            ),
            None,
        )

    def _future_feasible(
        self,
        states: list[_RouteState],
        remaining_ids: tuple[uuid.UUID, ...],
    ) -> bool:
        remaining = [self._deliveries[delivery_id] for delivery_id in remaining_ids]
        total_weight = sum((delivery.weight_kg for delivery in remaining), ZERO)
        total_volume = sum((delivery.volume_m3 for delivery in remaining), ZERO)
        available_weight = sum(
            (state.vehicle.max_payload_kg - state.weight_kg for state in states),
            ZERO,
        )
        available_volume = sum(
            (state.vehicle.max_volume_m3 - state.volume_m3 for state in states),
            ZERO,
        )
        if total_weight > available_weight or total_volume > available_volume:
            return False

        refrigerated = [
            delivery
            for delivery in remaining
            if delivery.temperature_class is TemperatureClass.REFRIGERATED
        ]
        if refrigerated:
            refrigerated_states = [state for state in states if state.vehicle.refrigerated]
            refrigerated_weight = sum((delivery.weight_kg for delivery in refrigerated), ZERO)
            refrigerated_volume = sum((delivery.volume_m3 for delivery in refrigerated), ZERO)
            available_refrigerated_weight = sum(
                (state.vehicle.max_payload_kg - state.weight_kg for state in refrigerated_states),
                ZERO,
            )
            available_refrigerated_volume = sum(
                (state.vehicle.max_volume_m3 - state.volume_m3 for state in refrigerated_states),
                ZERO,
            )
            if (
                refrigerated_weight > available_refrigerated_weight
                or refrigerated_volume > available_refrigerated_volume
            ):
                return False

        return all(
            any(self._can_serve_next(state, delivery) for state in states)
            for delivery in remaining
        )

    def _can_serve_next(self, state: _RouteState, delivery: OptimizationDelivery) -> bool:
        candidate, _reason = self._project_candidate(
            state_index=0,
            state=state,
            delivery=delivery,
            remaining_ids=(),
        )
        return candidate is not None

    def _states_after_candidate(
        self,
        states: list[_RouteState],
        candidate: _Candidate,
        delivery: OptimizationDelivery,
    ) -> list[_RouteState]:
        copied = [
            replace(
                state,
                delivery_ids=list(state.delivery_ids),
                stops=list(state.stops),
            )
            for state in states
        ]
        self._apply_candidate(copied[candidate.state_index], candidate, delivery)
        return copied

    @staticmethod
    def _apply_candidate(
        state: _RouteState,
        candidate: _Candidate,
        delivery: OptimizationDelivery,
    ) -> None:
        state.delivery_ids.append(delivery.id)
        state.stops.append(candidate.stop)
        state.weight_kg = candidate.projected_weight_kg
        state.volume_m3 = candidate.projected_volume_m3
        state.distance_km += candidate.leg.distance_km
        state.travel_minutes += candidate.leg.travel_minutes
        state.service_minutes += delivery.service_minutes
        state.current_at = candidate.stop.departure_at

    def _remove_symmetric_dominated(
        self,
        states: list[_RouteState],
        candidates: list[_Candidate],
        tracker: PruningTracker,
    ) -> list[_Candidate]:
        kept: dict[tuple[object, ...], _Candidate] = {}
        for candidate in sorted(candidates, key=lambda item: item.rank):
            state = states[candidate.state_index]
            vehicle = state.vehicle
            signature = (
                state.current_location,
                state.weight_kg,
                state.volume_m3,
                state.distance_km,
                state.travel_minutes,
                state.service_minutes,
                state.current_at,
                vehicle.max_payload_kg,
                vehicle.max_volume_m3,
                vehicle.max_range_km,
                vehicle.refrigerated,
                vehicle.fixed_route_cost_brl,
                vehicle.cost_per_km_brl,
                vehicle.cost_per_hour_brl,
            )
            if signature in kept:
                tracker.record(PruningReason.DOMINATED_STATE)
                continue
            kept[signature] = candidate
        return list(kept.values())

    def _cannot_beat_best(
        self,
        states: list[_RouteState],
        best_known_fitness: FitnessVector | None,
    ) -> bool:
        if best_known_fitness is None or not best_known_fitness.feasible:
            return False

        service_penalty = sum(
            (stop.service_penalty for state in states for stop in state.stops),
            ZERO,
        )
        critical_risk = sum(
            (stop.critical_risk for state in states for stop in state.stops),
            ZERO,
        )
        if service_penalty > best_known_fitness.service_penalty:
            return True
        if service_penalty < best_known_fitness.service_penalty:
            return False
        if critical_risk > best_known_fitness.critical_risk:
            return True
        if critical_risk < best_known_fitness.critical_risk:
            return False

        partial_cost = sum((self._partial_cost_lower_bound(state) for state in states), ZERO)
        return partial_cost > best_known_fitness.total_cost_brl

    def _partial_cost_lower_bound(self, state: _RouteState) -> Decimal:
        if not state.delivery_ids:
            return ZERO
        if self._context is not None and state.current_at is not None:
            duration = self._minutes_between(state.current_at, self._context.operation_start_at)
        else:
            duration = state.travel_minutes + Decimal(state.service_minutes)
        return (
            state.vehicle.fixed_route_cost_brl
            + state.distance_km * state.vehicle.cost_per_km_brl
            + (duration / Decimal("60")) * state.vehicle.cost_per_hour_brl
        )

    def _finalize_route(self, state: _RouteState) -> DecodedRoute:
        try:
            return_metric = self._travel_matrix.metric(
                state.current_location,
                None,
                state.current_at,
            )
        except KeyError:
            return_metric = TravelMetric(distance_km=ZERO, travel_minutes=ZERO)
        distance_km = state.distance_km + return_metric.distance_km
        travel_minutes = state.travel_minutes + return_metric.travel_minutes
        return_at = self._plus_minutes(state.current_at, return_metric.travel_minutes)
        if self._context is not None and return_at is not None:
            total_duration = self._minutes_between(return_at, self._context.operation_start_at)
        else:
            total_duration = travel_minutes + Decimal(state.service_minutes)
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
            service_minutes=state.service_minutes,
            total_duration_minutes=total_duration,
            total_cost_brl=total_cost,
            stops=tuple(state.stops),
            return_at=return_at,
        )

    def _projected_duration(
        self,
        *,
        state: _RouteState,
        leg: TravelMetric,
        delivery: OptimizationDelivery,
        projected_return_at: datetime | None,
        return_leg: TravelMetric,
    ) -> Decimal:
        if self._context is not None and projected_return_at is not None:
            return self._minutes_between(projected_return_at, self._context.operation_start_at)
        return (
            state.travel_minutes
            + leg.travel_minutes
            + return_leg.travel_minutes
            + Decimal(state.service_minutes + delivery.service_minutes)
        )

    def _effective_range(self, vehicle: OptimizationVehicle) -> Decimal:
        factor = self._context.range_safety_factor if self._context is not None else Decimal("1")
        return vehicle.max_range_km * factor

    def _scarce_resource_penalty(
        self,
        vehicle: OptimizationVehicle,
        delivery: OptimizationDelivery,
        remaining_ids: tuple[uuid.UUID, ...],
    ) -> int:
        if delivery.temperature_class is TemperatureClass.REFRIGERATED or not vehicle.refrigerated:
            return 0
        return int(
            any(
                self._deliveries[delivery_id].temperature_class
                is TemperatureClass.REFRIGERATED
                for delivery_id in remaining_ids
            )
        )

    @staticmethod
    def _lateness_minutes(
        delivery: OptimizationDelivery,
        service_start_at: datetime | None,
    ) -> Decimal:
        if service_start_at is None or delivery.time_window_end is None:
            return ZERO
        if service_start_at <= delivery.time_window_end:
            return ZERO
        return RouteDecoder._minutes_between(service_start_at, delivery.time_window_end)

    @staticmethod
    def _slack_minutes(
        delivery: OptimizationDelivery,
        service_start_at: datetime | None,
    ) -> Decimal | None:
        if service_start_at is None or delivery.time_window_end is None:
            return None
        return RouteDecoder._minutes_between(delivery.time_window_end, service_start_at)

    @staticmethod
    def _critical_risk(
        delivery: OptimizationDelivery,
        slack_minutes: Decimal | None,
    ) -> Decimal:
        buffer = _CRITICAL_BUFFER_MINUTES[delivery.priority]
        if buffer == ZERO or slack_minutes is None:
            return ZERO
        return max(ZERO, buffer - slack_minutes) * _PRIORITY_WEIGHT[delivery.priority]

    @staticmethod
    def _plus_minutes(value: datetime | None, minutes: Decimal) -> datetime | None:
        if value is None:
            return None
        return value + timedelta(seconds=float(minutes * Decimal("60")))

    @staticmethod
    def _minutes_between(later: datetime, earlier: datetime) -> Decimal:
        seconds = Decimal(str((later - earlier).total_seconds()))
        return seconds / Decimal("60")
