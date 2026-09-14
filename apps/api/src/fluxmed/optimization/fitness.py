from collections import Counter
from decimal import Decimal

from fluxmed.optimization.models import (
    ZERO,
    DecodedSolution,
    FitnessVector,
    OptimizationDelivery,
    OptimizationVehicle,
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
        service_penalty = sum((route.soft_lateness_minutes for route in solution.routes), ZERO)
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
        )


class SolutionValidator:
    def validate(
        self,
        *,
        solution: DecodedSolution,
        deliveries: list[OptimizationDelivery],
        vehicles: list[OptimizationVehicle],
    ) -> ValidationResult:
        expected_ids = {delivery.id for delivery in deliveries}
        assigned = [delivery_id for route in solution.routes for delivery_id in route.delivery_ids]
        counts = Counter(assigned)
        vehicle_by_id = {vehicle.id: vehicle for vehicle in vehicles}
        delivery_by_id = {delivery.id: delivery for delivery in deliveries}
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
                if delivery.handling_requirement.value == "TWO_PERSON" and not vehicle.helper_available:
                    issues.append(
                        ValidationIssue(
                            code="TEAM_INFEASIBLE",
                            message="Two-person delivery assigned without helper capability.",
                            delivery_id=delivery_id,
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
