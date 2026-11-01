import uuid
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal

from fluxmed.domain.enums import HandlingRequirement, HelperPolicy, TimeWindowPolicy
from fluxmed.optimization.models import (
    PRIORITY_WEIGHTS,
    ZERO,
    DecodedRoute,
    DecodedSolution,
    FitnessVector,
    OptimizationDelivery,
    OptimizationVehicle,
    TravelMatrix,
    ValidationIssue,
    ValidationResult,
)


class FitnessEvaluator:
    def evaluate(self, solution: DecodedSolution) -> FitnessVector:
        route_hard_violations = sum(len(route.hard_violations) for route in solution.routes)
        hard_violations = len(solution.unassigned_delivery_ids) + route_hard_violations
        distance_km = sum((route.distance_km for route in solution.routes), ZERO)
        travel_minutes = sum((route.travel_minutes for route in solution.routes), ZERO)
        total_cost = sum((route.total_cost_brl for route in solution.routes), ZERO)
        makespan = max(
            (route.total_duration_minutes for route in solution.routes),
            default=ZERO,
        )
        service_penalty = sum(
            (
                route.weighted_lateness_minutes
                if route.weighted_lateness_minutes is not None
                else route.soft_lateness_minutes
                for route in solution.routes
            ),
            ZERO,
        )
        critical_risk = sum((route.critical_risk for route in solution.routes), ZERO)
        return FitnessVector(
            feasible=hard_violations == 0,
            hard_violations=hard_violations,
            service_penalty=service_penalty,
            critical_risk=critical_risk,
            total_cost_brl=total_cost,
            makespan_minutes=makespan,
            travel_minutes=travel_minutes,
            distance_km=distance_km,
            vehicles_used=len(solution.routes),
            priority_inversion_minutes=self._priority_inversions(solution),
        )

    @staticmethod
    def _priority_inversions(solution: DecodedSolution) -> Decimal:
        """Penalize lower-priority service ahead of higher-priority service, across routes.

        Equal priorities and simultaneous service add no penalty. Accumulated times
        make this O(n log n), without comparing every pair of stops.
        """
        stops = sorted(
            (stop for route in solution.routes for stop in route.stops),
            key=lambda stop: stop.service_start_at,
        )
        if not stops:
            return ZERO
        reference = stops[0].service_start_at
        counts = [0] * 5
        totals = [ZERO] * 5
        penalty = ZERO
        for stop in stops:
            elapsed = Decimal(str((stop.service_start_at - reference).total_seconds())) / 60
            weight = PRIORITY_WEIGHTS[stop.priority]
            for lower in range(1, weight):
                penalty += (weight - lower) * (elapsed * counts[lower] - totals[lower])
            counts[weight] += 1
            totals[weight] += elapsed
        return penalty


class SolutionValidator:
    def validate(
        self,
        *,
        solution: DecodedSolution,
        deliveries: list[OptimizationDelivery],
        vehicles: list[OptimizationVehicle],
        travel_matrix: TravelMatrix,
        operation_start_at: datetime | None = None,
        operation_end_at: datetime | None = None,
    ) -> ValidationResult:
        expected_ids = {delivery.id for delivery in deliveries}
        assigned = [delivery_id for route in solution.routes for delivery_id in route.delivery_ids]
        counts = Counter(assigned)
        vehicle_by_id = {vehicle.id: vehicle for vehicle in vehicles}
        delivery_by_id = {delivery.id: delivery for delivery in deliveries}
        issues: list[ValidationIssue] = []
        vehicle_counts = Counter(route.vehicle_id for route in solution.routes)
        for vehicle_id, count in vehicle_counts.items():
            if count > 1:
                issues.append(
                    ValidationIssue(
                        "VEHICLE_REUSED",
                        "Vehicle occurs in multiple routes.",
                        vehicle_id=vehicle_id,
                    )
                )

        for delivery_id in sorted(expected_ids, key=str):
            count = counts.get(delivery_id, 0)
            if count == 0:
                issues.append(
                    ValidationIssue(
                        code="DELIVERY_UNASSIGNED",
                        message="Delivery is not assigned to any route.",
                        delivery_id=delivery_id,
                    )
                )
            elif count > 1:
                issues.append(
                    ValidationIssue(
                        code="DELIVERY_DUPLICATED",
                        message="Delivery appears more than once in the route plan.",
                        delivery_id=delivery_id,
                    )
                )

        unexpected = set(assigned) - expected_ids
        for delivery_id in sorted(unexpected, key=str):
            issues.append(
                ValidationIssue(
                    code="UNKNOWN_DELIVERY",
                    message="Route plan contains a delivery outside the optimization problem.",
                    delivery_id=delivery_id,
                )
            )

        if set(solution.unassigned_delivery_ids):
            for delivery_id in solution.unassigned_delivery_ids:
                if delivery_id in expected_ids and counts.get(delivery_id, 0) == 0:
                    continue
                issues.append(
                    ValidationIssue(
                        code="UNASSIGNED_STATE_MISMATCH",
                        message="Unassigned delivery state does not match route assignments.",
                        delivery_id=delivery_id,
                    )
                )

        for route in solution.routes:
            vehicle = vehicle_by_id.get(route.vehicle_id)
            if vehicle is None:
                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_VEHICLE",
                        message="Route references a vehicle outside the optimization problem.",
                        vehicle_id=route.vehicle_id,
                    )
                )
                continue
            issues.extend(
                self._recheck_route(
                    route=route,
                    deliveries=delivery_by_id,
                    vehicle=vehicle,
                    travel_matrix=travel_matrix,
                    operation_start_at=operation_start_at,
                    operation_end_at=operation_end_at,
                )
            )
            if route.total_weight_kg > vehicle.max_payload_kg:
                issues.append(
                    ValidationIssue(
                        code="CAPACITY_EXCEEDED",
                        message="Route exceeds vehicle payload capacity.",
                        vehicle_id=route.vehicle_id,
                    )
                )
            if route.total_volume_m3 > vehicle.max_volume_m3:
                issues.append(
                    ValidationIssue(
                        code="VOLUME_EXCEEDED",
                        message="Route exceeds vehicle volume capacity.",
                        vehicle_id=route.vehicle_id,
                    )
                )
            if route.distance_km > vehicle.max_range_km:
                issues.append(
                    ValidationIssue(
                        code="RANGE_IMPOSSIBLE",
                        message="Route exceeds vehicle autonomy.",
                        vehicle_id=route.vehicle_id,
                    )
                )
            if not route.starts_at_depot or not route.returns_to_depot:
                issues.append(
                    ValidationIssue(
                        code="DEPOT_RETURN_REQUIRED",
                        message="Every route must start and finish at the depot.",
                        vehicle_id=route.vehicle_id,
                    )
                )
            for code in route.hard_violations:
                issues.append(
                    ValidationIssue(
                        code=code,
                        message=f"Route violates hard optimization rule: {code}.",
                        vehicle_id=route.vehicle_id,
                    )
                )
            for delivery_id in route.delivery_ids:
                delivery = delivery_by_id.get(delivery_id)
                if delivery is None:
                    continue
                if delivery.temperature_class.value == "REFRIGERATED" and not vehicle.refrigerated:
                    issues.append(
                        ValidationIssue(
                            code="REFRIGERATION_INCOMPATIBLE",
                            message="Refrigerated delivery assigned to non-refrigerated vehicle.",
                            delivery_id=delivery_id,
                            vehicle_id=route.vehicle_id,
                        )
                    )
                if (
                    delivery.handling_requirement.value == "TWO_PERSON"
                    and not vehicle.helper_available
                ):
                    issues.append(
                        ValidationIssue(
                            code="TEAM_INFEASIBLE",
                            message="Two-person delivery assigned without helper capability.",
                            delivery_id=delivery_id,
                            vehicle_id=route.vehicle_id,
                        )
                    )

        return ValidationResult(valid=not issues, issues=tuple(issues))

    @staticmethod
    def _recheck_route(
        *,
        route: DecodedRoute,
        deliveries: dict[uuid.UUID, OptimizationDelivery],
        vehicle: OptimizationVehicle,
        travel_matrix: TravelMatrix,
        operation_start_at: datetime | None,
        operation_end_at: datetime | None,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        def fail(code: str, message: str) -> None:
            issues.append(ValidationIssue(code, message, vehicle_id=vehicle.id))

        if not route.delivery_ids:
            fail("EMPTY_ROUTE", "A used vehicle must have at least one delivery.")
        if any(delivery_id not in deliveries for delivery_id in route.delivery_ids):
            return issues  # Unknown delivery is already reported by validate().
        actual = [deliveries[delivery_id] for delivery_id in route.delivery_ids]
        weight = sum((delivery.weight_kg for delivery in actual), ZERO)
        volume = sum((delivery.volume_m3 for delivery in actual), ZERO)
        if weight != route.total_weight_kg or volume != route.total_volume_m3:
            fail("LOAD_TOTAL_MISMATCH", "Declared load differs from original deliveries.")
        if weight > vehicle.max_payload_kg:
            fail("CAPACITY_EXCEEDED", "Original delivery payload exceeds vehicle capacity.")
        if volume > vehicle.max_volume_m3:
            fail("VOLUME_EXCEEDED", "Original delivery volume exceeds vehicle capacity.")
        helper_required = vehicle.helper_policy is HelperPolicy.REQUIRED or any(
            d.handling_requirement is HandlingRequirement.TWO_PERSON for d in actual
        )
        if helper_required and (
            not vehicle.helper_available or vehicle.helper_policy is HelperPolicy.FORBIDDEN
        ):
            fail("TEAM_INFEASIBLE", "Route requires a compatible helper.")

        sequence = (None, *route.delivery_ids, None)
        try:
            metrics = [
                travel_matrix.metric(a, b) for a, b in zip(sequence, sequence[1:], strict=False)
            ]
        except KeyError:
            fail("ROUTE_DISCONNECTED", "A route leg has no travel metric, including depot return.")
            return issues
        if any(m.distance_km < ZERO or m.travel_minutes < ZERO for m in metrics):
            fail("INVALID_TRAVEL_METRIC", "Travel metrics must be nonnegative.")
        distance = sum((m.distance_km for m in metrics), ZERO)
        travel = sum((m.travel_minutes for m in metrics), ZERO)
        service = sum(d.service_minutes for d in actual)
        if distance != route.distance_km or travel != route.travel_minutes:
            fail("TRAVEL_TOTAL_MISMATCH", "Route metrics differ from original travel matrix.")
        if service != route.service_minutes:
            fail("SERVICE_TOTAL_MISMATCH", "Service total differs from original deliveries.")
        if distance > vehicle.max_range_km:
            fail("RANGE_IMPOSSIBLE", "Recomputed distance exceeds vehicle autonomy.")
        waiting = ZERO
        clock = operation_start_at
        if clock is not None:
            if tuple(stop.delivery_id for stop in route.stops) != route.delivery_ids:
                fail("STOP_SEQUENCE_MISMATCH", "Stops must match delivery order exactly.")
            for index, delivery in enumerate(actual):
                arrival = clock + timedelta(minutes=float(metrics[index].travel_minutes))
                beginning = arrival
                window_start = delivery.time_window_start
                window_end = delivery.time_window_end
                # Datetimes are normalized independently of the route decoder.
                if clock.tzinfo is None and any(
                    value is not None and value.tzinfo is not None
                    for value in (window_start, window_end)
                ):
                    fail("SCHEDULE_TIMEZONE_MISMATCH", "Window and operation timezones disagree.")
                    return issues
                if window_start is not None and window_start.tzinfo is None and clock.tzinfo:
                    window_start = window_start.replace(tzinfo=clock.tzinfo)
                if window_end is not None and window_end.tzinfo is None and clock.tzinfo:
                    window_end = window_end.replace(tzinfo=clock.tzinfo)
                if window_start is not None and beginning < window_start:
                    waiting += Decimal(str((window_start - beginning).total_seconds())) / 60
                    beginning = window_start
                lateness = ZERO
                if window_end is not None and beginning > window_end:
                    lateness = Decimal(str((beginning - window_end).total_seconds())) / 60
                    if delivery.time_window_policy is TimeWindowPolicy.HARD:
                        fail(
                            "HARD_TIME_WINDOW_IMPOSSIBLE", "Recomputed service misses hard window."
                        )
                departure = beginning + timedelta(minutes=delivery.service_minutes)
                if index < len(route.stops):
                    stop = route.stops[index]
                    if (
                        stop.arrival_at != arrival
                        or stop.service_start_at != beginning
                        or stop.departure_at != departure
                        or stop.lateness_minutes != lateness
                        or stop.priority is not delivery.priority
                    ):
                        fail("STOP_CHRONOLOGY_MISMATCH", "Stop differs from recomputed schedule.")
                clock = departure
            returned_at = clock + timedelta(minutes=float(metrics[-1].travel_minutes))
            if operation_end_at is not None:
                end = operation_end_at
                if returned_at.tzinfo is None and end.tzinfo is not None:
                    fail("SCHEDULE_TIMEZONE_MISMATCH", "Operation end timezone disagrees.")
                    return issues
                if end.tzinfo is None and returned_at.tzinfo:
                    end = end.replace(tzinfo=returned_at.tzinfo)
                if returned_at > end:
                    fail("END_OF_SHIFT_IMPOSSIBLE", "Recomputed return exceeds operation end.")
        elif route.stops or any(d.time_window_start or d.time_window_end for d in actual):
            fail(
                "SCHEDULE_CONTEXT_REQUIRED", "Cannot validate timed stops without operation start."
            )
        if (
            route.waiting_minutes != waiting
            or route.total_duration_minutes != travel + service + waiting
        ):
            fail(
                "DURATION_TOTAL_MISMATCH",
                "Elapsed duration must include travel, service and waiting.",
            )
        return issues


def better_fitness(left: FitnessVector, right: FitnessVector) -> bool:
    return left.sort_key() < right.sort_key()


def fitness_equal(left: FitnessVector, right: FitnessVector) -> bool:
    return left.sort_key() == right.sort_key()


def decimal_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")
