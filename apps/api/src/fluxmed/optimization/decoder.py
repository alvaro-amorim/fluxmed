import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from fluxmed.domain.enums import (
    DeliveryPriority,
    HandlingRequirement,
    HelperPolicy,
    TemperatureClass,
)
from fluxmed.optimization.models import (
    PRIORITY_WEIGHTS,
    ZERO,
    DecodedRoute,
    DecodedSolution,
    DecodedStop,
    OptimizationDelivery,
    OptimizationVehicle,
    TravelMatrix,
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
        operation_start_at: datetime | None = None,
        operation_end_at: datetime | None = None,
        advanced_pruning_enabled: bool = True,
    ) -> None:
        self._deliveries = {delivery.id: delivery for delivery in deliveries}
        self._vehicles = tuple(vehicles)
        self._travel_matrix = travel_matrix
        self._operation_start_at = operation_start_at
        self._operation_end_at = operation_end_at
        self._advanced_pruning_enabled = advanced_pruning_enabled

    def decode(self, chromosome: tuple[uuid.UUID, ...]) -> DecodedSolution:
        states = [_RouteState(vehicle=vehicle, delivery_ids=[]) for vehicle in self._vehicles]
        unassigned: list[uuid.UUID] = []
        pruning_counts: dict[str, int] = {}

        for delivery_id in chromosome:
            delivery = self._deliveries[delivery_id]
            candidate = self._best_vehicle(states, delivery, pruning_counts)
            if candidate is None:
                unassigned.append(delivery_id)
                continue
            candidate.delivery_ids.append(delivery_id)
            candidate.weight_kg += delivery.weight_kg
            candidate.volume_m3 += delivery.volume_m3

        routes = tuple(self._finalize_route(state) for state in states if state.delivery_ids)
        return DecodedSolution(
            routes=routes,
            unassigned_delivery_ids=tuple(unassigned),
            pruning_counts=pruning_counts,
        )

    def _best_vehicle(
        self,
        states: list[_RouteState],
        delivery: OptimizationDelivery,
        pruning_counts: dict[str, int],
    ) -> _RouteState | None:
        feasible: list[tuple[tuple[object, ...], _RouteState]] = []
        for state in states:
            vehicle = state.vehicle
            reason = self._basic_eligibility_failure(state, delivery)
            if reason is not None:
                pruning_counts[reason] = pruning_counts.get(reason, 0) + 1
                continue

            if self._advanced_pruning_enabled:
                reason = self._advanced_eligibility_failure(state, delivery)
                if reason is not None:
                    pruning_counts[reason] = pruning_counts.get(reason, 0) + 1
                    continue

            prospective = self._prospective_route(state, delivery)
            if self._advanced_pruning_enabled:
                if prospective.distance_km > vehicle.max_range_km:
                    pruning_counts["RANGE_IMPOSSIBLE"] = (
                        pruning_counts.get("RANGE_IMPOSSIBLE", 0) + 1
                    )
                    continue
                if prospective.hard_violations:
                    for violation in prospective.hard_violations:
                        pruning_counts[violation] = pruning_counts.get(violation, 0) + 1
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
            remaining_weight = vehicle.max_payload_kg - (state.weight_kg + delivery.weight_kg)
            remaining_volume = vehicle.max_volume_m3 - (state.volume_m3 + delivery.volume_m3)
            rank = (
                prospective.weighted_lateness_minutes,
                prospective.critical_risk,
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

    @staticmethod
    def _basic_eligibility_failure(
        state: _RouteState,
        delivery: OptimizationDelivery,
    ) -> str | None:
        vehicle = state.vehicle
        next_weight = state.weight_kg + delivery.weight_kg
        next_volume = state.volume_m3 + delivery.volume_m3
        if next_weight > vehicle.max_payload_kg:
            return "CAPACITY_EXCEEDED"
        if next_volume > vehicle.max_volume_m3:
            return "VOLUME_EXCEEDED"
        return None

    @staticmethod
    def _advanced_eligibility_failure(
        state: _RouteState,
        delivery: OptimizationDelivery,
    ) -> str | None:
        vehicle = state.vehicle
        if delivery.temperature_class is TemperatureClass.REFRIGERATED and not vehicle.refrigerated:
            return "REFRIGERATION_INCOMPATIBLE"
        helper_required = (
            delivery.handling_requirement is HandlingRequirement.TWO_PERSON
            or vehicle.helper_policy is HelperPolicy.REQUIRED
        )
        if helper_required and not vehicle.helper_available:
            return "TEAM_INFEASIBLE"
        if (
            delivery.handling_requirement is HandlingRequirement.TWO_PERSON
            and vehicle.helper_policy is HelperPolicy.FORBIDDEN
        ):
            return "TEAM_INFEASIBLE"
        return None

    def _prospective_route(
        self,
        state: _RouteState,
        delivery: OptimizationDelivery,
    ) -> DecodedRoute:
        candidate = _RouteState(
            vehicle=state.vehicle,
            delivery_ids=[*state.delivery_ids, delivery.id],
            weight_kg=state.weight_kg + delivery.weight_kg,
            volume_m3=state.volume_m3 + delivery.volume_m3,
        )
        return self._finalize_route(candidate)

    @staticmethod
    def _align(reference: datetime, value: datetime) -> datetime:
        if reference.tzinfo is None:
            if value.tzinfo is not None:
                raise ValueError(
                    "Cannot align a timezone-aware value to a naive operation schedule."
                )
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=reference.tzinfo)
        return value.astimezone(reference.tzinfo)

    def _finalize_route(self, state: _RouteState) -> DecodedRoute:
        distance_km = ZERO
        travel_minutes = ZERO
        service_minutes = 0
        current: uuid.UUID | None = None
        current_at = self._operation_start_at
        stops: list[DecodedStop] = []
        hard_violations: list[str] = []
        soft_lateness = ZERO
        weighted_lateness = ZERO
        waiting_minutes = ZERO
        critical_risk = ZERO

        for delivery_id in state.delivery_ids:
            delivery = self._deliveries[delivery_id]
            if (
                delivery.temperature_class is TemperatureClass.REFRIGERATED
                and not state.vehicle.refrigerated
            ):
                hard_violations.append("REFRIGERATION_INCOMPATIBLE")
            helper_required = (
                delivery.handling_requirement is HandlingRequirement.TWO_PERSON
                or state.vehicle.helper_policy is HelperPolicy.REQUIRED
            )
            if helper_required and not state.vehicle.helper_available:
                hard_violations.append("TEAM_INFEASIBLE")
            if (
                delivery.handling_requirement is HandlingRequirement.TWO_PERSON
                and state.vehicle.helper_policy is HelperPolicy.FORBIDDEN
            ):
                hard_violations.append("TEAM_INFEASIBLE")

            metric = self._travel_matrix.metric(current, delivery_id)
            distance_km += metric.distance_km
            travel_minutes += metric.travel_minutes
            service_minutes += delivery.service_minutes

            if current_at is not None:
                arrival_at = current_at + timedelta(minutes=float(metric.travel_minutes))
                service_start_at = arrival_at
                window_start = (
                    self._align(service_start_at, delivery.time_window_start)
                    if delivery.time_window_start is not None
                    else None
                )
                window_end = (
                    self._align(service_start_at, delivery.time_window_end)
                    if delivery.time_window_end is not None
                    else None
                )
                if window_start is not None and service_start_at < window_start:
                    waiting_minutes += Decimal(
                        str((window_start - service_start_at).total_seconds())
                    ) / Decimal("60")
                    service_start_at = window_start
                lateness = ZERO
                if window_end is not None and service_start_at > window_end:
                    lateness = Decimal(str((service_start_at - window_end).total_seconds())) / 60
                    if delivery.time_window_policy.value == "HARD":
                        hard_violations.append("HARD_TIME_WINDOW_IMPOSSIBLE")
                    else:
                        soft_lateness += lateness
                        weighted_lateness += lateness * PRIORITY_WEIGHTS[delivery.priority]
                if delivery.priority is DeliveryPriority.CRITICAL:
                    if window_end is not None:
                        slack_minutes = Decimal(
                            str((window_end - service_start_at).total_seconds() / 60)
                        )
                        if slack_minutes < Decimal("30"):
                            critical_risk += max(ZERO, Decimal("30") - slack_minutes)
                    critical_risk += lateness * Decimal("3")
                departure_at = service_start_at + timedelta(minutes=delivery.service_minutes)
                stops.append(
                    DecodedStop(
                        delivery_id=delivery.id,
                        arrival_at=arrival_at,
                        service_start_at=service_start_at,
                        departure_at=departure_at,
                        lateness_minutes=lateness,
                        priority=delivery.priority,
                    )
                )
                current_at = departure_at
            current = delivery_id

        return_metric = self._travel_matrix.metric(current, None)
        distance_km += return_metric.distance_km
        travel_minutes += return_metric.travel_minutes
        if current_at is not None:
            current_at = current_at + timedelta(minutes=float(return_metric.travel_minutes))
            if self._operation_end_at is not None:
                operation_end = self._align(current_at, self._operation_end_at)
                if current_at > operation_end:
                    hard_violations.append("END_OF_SHIFT_IMPOSSIBLE")

        total_duration = travel_minutes + Decimal(service_minutes) + waiting_minutes
        vehicle = state.vehicle
        total_cost = (
            vehicle.fixed_route_cost_brl
            + distance_km * vehicle.cost_per_km_brl
            + (total_duration / Decimal("60")) * vehicle.cost_per_hour_brl
        )
        if distance_km > vehicle.max_range_km:
            hard_violations.append("RANGE_IMPOSSIBLE")

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
            stops=tuple(stops),
            hard_violations=tuple(dict.fromkeys(hard_violations)),
            soft_lateness_minutes=soft_lateness,
            critical_risk=critical_risk,
            waiting_minutes=waiting_minutes,
            weighted_lateness_minutes=weighted_lateness,
        )
