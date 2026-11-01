import uuid
from collections import OrderedDict
from dataclasses import replace
from decimal import Decimal

from fluxmed.application.optimization.cost_engine import FinalCostEngine
from fluxmed.application.optimization.team_assignment import (
    TeamAssignmentError,
    TeamAssignmentSolver,
)
from fluxmed.application.resources import VehicleView, WorkerView
from fluxmed.domain.enums import HandlingRequirement
from fluxmed.optimization import (
    DecodedSolution,
    FitnessEvaluator,
    FitnessVector,
    OptimizationDelivery,
)
from fluxmed.optimization.models import ZERO

CostKey = tuple[tuple[uuid.UUID, Decimal, Decimal, bool], ...]


class OperationalFitnessEvaluator(FitnessEvaluator):
    """Use the same global team assignment and cost rules as final persistence."""

    def __init__(
        self,
        *,
        deliveries: list[OptimizationDelivery],
        vehicles: list[VehicleView],
        workers: list[WorkerView],
    ) -> None:
        self._deliveries = list(deliveries)
        self._vehicles = list(vehicles)
        self._workers = list(workers)
        self._vehicle_by_id = {vehicle.id: vehicle for vehicle in vehicles}
        self._teams = TeamAssignmentSolver()
        self._costs = FinalCostEngine()
        self._two_person_ids = {
            delivery.id
            for delivery in deliveries
            if delivery.handling_requirement is HandlingRequirement.TWO_PERSON
        }
        # This evaluator belongs to one immutable operation snapshot. Cache only
        # the inputs used by team assignment and costing, not chromosome/stop objects.
        self._cache: OrderedDict[CostKey, tuple[bool, Decimal]] = OrderedDict()
        self.cache_hits = 0
        self.cache_misses = 0

    def evaluate(self, solution: DecodedSolution) -> FitnessVector:
        fitness = super().evaluate(solution)
        key = tuple(
            sorted(
                (
                    (
                        route.vehicle_id,
                        route.distance_km,
                        route.total_duration_minutes,
                        any(d in self._two_person_ids for d in route.delivery_ids),
                    )
                    for route in solution.routes
                ),
                key=lambda item: str(item[0]),
            )
        )
        if key in self._cache:
            self.cache_hits += 1
            self._cache.move_to_end(key)
            team_feasible, cost = self._cache[key]
        else:
            self.cache_misses += 1
            team_feasible, cost = self._operational_cost(solution)
            self._cache[key] = (team_feasible, cost)
            if len(self._cache) > 512:
                self._cache.popitem(last=False)
        if not team_feasible:
            return replace(
                fitness,
                feasible=False,
                hard_violations=fitness.hard_violations + 1,
                team_feasible=False,
            )
        return replace(fitness, total_cost_brl=cost)

    def _operational_cost(self, solution: DecodedSolution) -> tuple[bool, Decimal]:
        try:
            team_plan = self._teams.solve(
                routes=solution.routes,
                deliveries=self._deliveries,
                vehicles=self._vehicles,
                workers=self._workers,
            )
        except TeamAssignmentError:
            return False, ZERO
        teams = team_plan.by_vehicle()
        cost = sum(
            (
                self._costs.calculate(
                    route=route,
                    vehicle=self._vehicle_by_id[route.vehicle_id],
                    team=teams[route.vehicle_id],
                ).total_brl
                for route in solution.routes
            ),
            start=ZERO,
        )
        return True, cost
