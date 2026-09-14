from collections import Counter
from decimal import Decimal

from fluxmed.domain.enums import TemperatureClass, TimeWindowPolicy
from fluxmed.optimization.models import (
    ZERO,
    DecodedSolution,
    FitnessVector,
    OptimizationContext,
    OptimizationDelivery,
    OptimizationVehicle,
    ValidationIssue,
    ValidationResult,
)

_REFRIGERATION_MESSAGE = (
    "Refrigerated delivery is assigned to a non-refrigerated "
    "vehicle."
)


class FitnessEvaluator:
    def evaluate(self, solution: DecodedSolution) -> FitnessVector:
        hard_violations = len(solution.unassigned_delivery_ids)
        distance_km = sum((route.distance_km for route in solution.routes), ZERO)
        travel_minutes = sum((route.travel_minutes for route in solution.routes), ZERO)
        total_cost = sum((route.total_cost_brl for route in solution.routes), ZERO)
        service_penalty = sum(
            (stop.service_penalty for route in solution.routes for stop in route.stops),
            ZERO,
        )
        critical_risk = sum(
            (stop.critical_risk for route in solution.routes for stop in route.stops),
            ZERO,
        )
        makespan = max(
            (route.total_duration_minutes for route in solution.routes),
            default=ZERO,
        )
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
        )


class SolutionValidator:
    def validate(
        self,
        *,
        solution: DecodedSolution,
        deliveries: list[OptimizationDelivery],
        vehicles: list[OptimizationVehicle],
        context: OptimizationContext | None = None,
    ) -> ValidationResult:
        expected_ids = {delivery.id for delivery in deliveries}
        delivery_by_id = {delivery.id: delivery for delivery in deliveries}
        assigned = [delivery_id for route in solution.routes for delivery_id in route.delivery_ids]
        counts = Counter(assigned)
        vehicle_by_id = {vehicle.id: vehicle for vehicle in vehicles}
        issues: list[ValidationIssue] = []

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
            range_factor = context.range_safety_factor if context is not None else Decimal("1")
            if route.distance_km > vehicle.max_range_km * range_factor:
                issues.append(
                    ValidationIssue(
                        code="RANGE_EXCEEDED",
                        message="Route exceeds the vehicle safe operating range.",
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
            if context is not None and (
                route.return_at is None or route.return_at > context.operation_end_at
            ):
                issues.append(
                    ValidationIssue(
                        code="END_OF_SHIFT_EXCEEDED",
                        message="Route does not return before the operation ends.",
                        vehicle_id=route.vehicle_id,
                    )
                )

            route_deliveries = [
                delivery_by_id[delivery_id]
                for delivery_id in route.delivery_ids
                if delivery_id in delivery_by_id
            ]
            for delivery in route_deliveries:
                if (
                    delivery.temperature_class is TemperatureClass.REFRIGERATED
                    and not vehicle.refrigerated
                ):
                    issues.append(
                        ValidationIssue(
                            code="REFRIGERATION_INCOMPATIBLE",
                            message=_REFRIGERATION_MESSAGE,
                            delivery_id=delivery.id,
                            vehicle_id=vehicle.id,
                        )
                    )

            if route.stops:
                if tuple(stop.delivery_id for stop in route.stops) != route.delivery_ids:
                    issues.append(
                        ValidationIssue(
                            code="STOP_SEQUENCE_MISMATCH",
                            message="Route stops do not match the route delivery sequence.",
                            vehicle_id=route.vehicle_id,
                        )
                    )
                for stop in route.stops:
                    delivery = delivery_by_id.get(stop.delivery_id)
                    if delivery is None:
                        continue
                    if (
                        delivery.time_window_policy is TimeWindowPolicy.HARD
                        and delivery.time_window_end is not None
                        and (
                            stop.service_start_at is None
                            or stop.service_start_at > delivery.time_window_end
                        )
                    ):
                        issues.append(
                            ValidationIssue(
                                code="HARD_TIME_WINDOW_MISSED",
                                message="Delivery starts service after its HARD window closes.",
                                delivery_id=delivery.id,
                                vehicle_id=route.vehicle_id,
                            )
                        )

        return ValidationResult(valid=not issues, issues=tuple(issues))


def better_fitness(left: FitnessVector, right: FitnessVector) -> bool:
    return left.sort_key() < right.sort_key()


def fitness_equal(left: FitnessVector, right: FitnessVector) -> bool:
    return left.sort_key() == right.sort_key()


def decimal_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")
