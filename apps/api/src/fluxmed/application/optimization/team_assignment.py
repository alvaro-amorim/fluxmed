import uuid
from dataclasses import dataclass
from decimal import Decimal

from fluxmed.application.resources import VehicleView, WorkerView
from fluxmed.domain.enums import (
    HandlingRequirement,
    HelperPolicy,
    VehicleType,
    WorkerRole,
)
from fluxmed.domain.resources import WorkerCompensationCalculator
from fluxmed.optimization import DecodedRoute, OptimizationDelivery

ZERO = Decimal("0")


class TeamAssignmentError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RouteTeamAssignment:
    vehicle_id: uuid.UUID
    primary_role: WorkerRole | None
    primary_worker_id: uuid.UUID | None
    helper_worker_id: uuid.UUID | None
    primary_included: bool
    helper_included: bool
    team_cost_brl: Decimal


@dataclass(frozen=True, slots=True)
class TeamAssignmentPlan:
    assignments: tuple[RouteTeamAssignment, ...]
    total_team_cost_brl: Decimal

    def by_vehicle(self) -> dict[uuid.UUID, RouteTeamAssignment]:
        return {item.vehicle_id: item for item in self.assignments}


@dataclass(frozen=True, slots=True)
class _Requirement:
    vehicle_id: uuid.UUID
    duration_hours: Decimal


class TeamAssignmentSolver:
    """Assign one compatible team per route with deterministic minimum worker cost."""

    def solve(
        self,
        *,
        routes: tuple[DecodedRoute, ...],
        deliveries: list[OptimizationDelivery],
        vehicles: list[VehicleView],
        workers: list[WorkerView],
    ) -> TeamAssignmentPlan:
        vehicle_by_id = {vehicle.id: vehicle for vehicle in vehicles}
        delivery_by_id = {delivery.id: delivery for delivery in deliveries}
        selected_workers = [worker for worker in workers if worker.active]

        primary_requirements: dict[WorkerRole, list[_Requirement]] = {
            WorkerRole.DRIVER: [],
            WorkerRole.MOTORCYCLE_COURIER: [],
        }
        helper_requirements: list[_Requirement] = []
        primary_included: set[uuid.UUID] = set()
        helper_included: set[uuid.UUID] = set()

        for route in routes:
            vehicle = vehicle_by_id.get(route.vehicle_id)
            if vehicle is None:
                raise TeamAssignmentError(
                    f"Veículo {route.vehicle_id} não está nos recursos selecionados."
                )
            duration_hours = route.total_duration_minutes / Decimal("60")
            if vehicle.cost.driver_included:
                primary_included.add(vehicle.id)
            else:
                role = (
                    WorkerRole.MOTORCYCLE_COURIER
                    if vehicle.type is VehicleType.MOTO
                    else WorkerRole.DRIVER
                )
                primary_requirements[role].append(
                    _Requirement(vehicle_id=vehicle.id, duration_hours=duration_hours)
                )

            helper_required = vehicle.helper_policy is HelperPolicy.REQUIRED or any(
                delivery_by_id[delivery_id].handling_requirement
                is HandlingRequirement.TWO_PERSON
                for delivery_id in route.delivery_ids
            )
            if not helper_required:
                continue
            if vehicle.helper_policy is HelperPolicy.FORBIDDEN:
                raise TeamAssignmentError(
                    f"A rota do veículo {vehicle.plate} exige ajudante, mas o veículo o proíbe."
                )
            if vehicle.cost.helper_included:
                helper_included.add(vehicle.id)
            else:
                helper_requirements.append(
                    _Requirement(vehicle_id=vehicle.id, duration_hours=duration_hours)
                )

        primary_workers: dict[uuid.UUID, WorkerView] = {}
        for role, requirements in primary_requirements.items():
            candidates = [worker for worker in selected_workers if worker.role is role]
            primary_workers.update(self._minimum_cost_matching(requirements, candidates, role))

        helper_workers = self._minimum_cost_matching(
            helper_requirements,
            [worker for worker in selected_workers if worker.role is WorkerRole.HELPER],
            WorkerRole.HELPER,
        )

        assignments: list[RouteTeamAssignment] = []
        for route in routes:
            vehicle = vehicle_by_id[route.vehicle_id]
            primary = primary_workers.get(vehicle.id)
            helper = helper_workers.get(vehicle.id)
            included_primary = vehicle.id in primary_included
            included_helper = vehicle.id in helper_included
            primary_role: WorkerRole | None
            if included_primary:
                primary_role = None
            else:
                primary_role = (
                    WorkerRole.MOTORCYCLE_COURIER
                    if vehicle.type is VehicleType.MOTO
                    else WorkerRole.DRIVER
                )
            team_cost = ZERO
            duration_hours = route.total_duration_minutes / Decimal("60")
            if primary is not None:
                team_cost += self._worker_cost(primary, duration_hours)
            if helper is not None:
                team_cost += self._worker_cost(helper, duration_hours)
            assignments.append(
                RouteTeamAssignment(
                    vehicle_id=vehicle.id,
                    primary_role=primary_role,
                    primary_worker_id=primary.id if primary is not None else None,
                    helper_worker_id=helper.id if helper is not None else None,
                    primary_included=included_primary,
                    helper_included=included_helper,
                    team_cost_brl=team_cost,
                )
            )

        return TeamAssignmentPlan(
            assignments=tuple(assignments),
            total_team_cost_brl=sum((item.team_cost_brl for item in assignments), ZERO),
        )

    def _minimum_cost_matching(
        self,
        requirements: list[_Requirement],
        candidates: list[WorkerView],
        role: WorkerRole,
    ) -> dict[uuid.UUID, WorkerView]:
        if not requirements:
            return {}
        if len(candidates) < len(requirements):
            raise TeamAssignmentError(
                f"Equipe insuficiente para {role.value}: "
                f"{len(requirements)} rota(s), {len(candidates)} pessoa(s)."
            )

        ordered_requirements = sorted(requirements, key=lambda item: str(item.vehicle_id))
        ordered_candidates = sorted(
            candidates,
            key=lambda item: (item.compensation_value_brl, str(item.id)),
        )
        states: dict[int, tuple[Decimal, tuple[int, ...]]] = {0: (ZERO, ())}
        for requirement in ordered_requirements:
            next_states: dict[int, tuple[Decimal, tuple[int, ...]]] = {}
            for mask, (cost, choices) in states.items():
                for index, worker in enumerate(ordered_candidates):
                    bit = 1 << index
                    if mask & bit:
                        continue
                    next_mask = mask | bit
                    candidate_cost = cost + self._worker_cost(worker, requirement.duration_hours)
                    candidate_choices = (*choices, index)
                    current = next_states.get(next_mask)
                    if current is None or (candidate_cost, candidate_choices) < current:
                        next_states[next_mask] = (candidate_cost, candidate_choices)
            states = next_states

        if not states:
            raise TeamAssignmentError(f"Não foi possível alocar equipe para {role.value}.")
        _mask, (_cost, choices) = min(states.items(), key=lambda item: item[1])
        return {
            requirement.vehicle_id: ordered_candidates[worker_index]
            for requirement, worker_index in zip(ordered_requirements, choices, strict=True)
        }

    @staticmethod
    def _worker_cost(worker: WorkerView, duration_hours: Decimal) -> Decimal:
        return WorkerCompensationCalculator.estimate(
            model=worker.compensation_model,
            value_brl=worker.compensation_value_brl,
            duration_hours=duration_hours,
        )
