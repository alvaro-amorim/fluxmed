import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fluxmed.application.optimization.cost_engine import FinalCostEngine, RouteCostBreakdown
from fluxmed.application.optimization.routing_matrix import RoutingMatrixBuilder
from fluxmed.application.optimization.team_assignment import (
    RouteTeamAssignment,
    TeamAssignmentError,
    TeamAssignmentSolver,
)
from fluxmed.application.resources import ResourceService, VehicleView, WorkerView
from fluxmed.domain.enums import (
    DeliveryPriority,
    HandlingRequirement,
    OperationStatus,
    OptimizationRunStatus,
    RevisionStatus,
    VehicleType,
    WorkerRole,
)
from fluxmed.domain.resources import WorkerCompensationCalculator
from fluxmed.infrastructure.models.city import AddressModel, DistrictModel, StreetModel
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.operation_revision import OperationRevisionModel
from fluxmed.infrastructure.models.optimization_result import (
    OptimizationRunModel,
    RoutePlanModel,
    RouteStopModel,
    RouteTeamAssignmentModel,
)
from fluxmed.infrastructure.models.resource import VehicleModel, WorkerModel
from fluxmed.optimization import (
    DecodedRoute,
    OptimizationDelivery,
    OptimizationResult,
    ValidationResult,
)

ZERO = Decimal("0")
HUNDRED = Decimal("100")


class OptimizationResultNotFoundError(LookupError):
    pass


class OptimizationApprovalError(ValueError):
    pass


class TeamSimulationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WorkerResultView:
    id: uuid.UUID
    name: str
    role: str


@dataclass(frozen=True, slots=True)
class VehicleResultView:
    id: uuid.UUID
    plate: str
    type: str
    ownership_type: str


@dataclass(frozen=True, slots=True)
class RouteCostView:
    depreciation_brl: Decimal
    maintenance_brl: Decimal
    fixed_time_brl: Decimal
    fuel_brl: Decimal
    team_brl: Decimal
    contract_brl: Decimal
    total_brl: Decimal


@dataclass(frozen=True, slots=True)
class RouteTeamView:
    primary_role: str | None
    primary_worker: WorkerResultView | None
    helper: WorkerResultView | None
    primary_included: bool
    helper_included: bool
    team_cost_brl: Decimal


@dataclass(frozen=True, slots=True)
class RouteStopView:
    id: uuid.UUID
    sequence: int
    delivery_id: uuid.UUID
    delivery_code: str
    recipient_name: str
    address_label: str
    priority: str
    longitude: float
    latitude: float
    planned_arrival_at: datetime | None
    planned_departure_at: datetime | None
    time_window_start: datetime | None
    time_window_end: datetime | None
    time_window_policy: str
    service_time_minutes: int
    lateness_minutes: Decimal


@dataclass(frozen=True, slots=True)
class RouteResultView:
    id: uuid.UUID
    route_code: str
    vehicle: VehicleResultView
    team: RouteTeamView
    delivery_count: int
    distance_km: Decimal
    duration_minutes: Decimal
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    weight_utilization_pct: Decimal
    volume_utilization_pct: Decimal
    cost: RouteCostView
    geometry: dict[str, object]
    stops: tuple[RouteStopView, ...]


@dataclass(frozen=True, slots=True)
class OptimizationResultView:
    run_id: uuid.UUID
    operation_id: uuid.UUID
    revision_number: int
    status: str
    validated: bool
    random_seed: int
    generations_completed: int
    stop_reason: str
    delivery_count: int
    vehicles_used: int
    total_cost_brl: Decimal
    distance_km: Decimal
    makespan_minutes: Decimal
    critical_delays: int
    on_time_percentage: Decimal
    average_weight_utilization_pct: Decimal
    average_volume_utilization_pct: Decimal
    pruning_counts: dict[str, int]
    routes: tuple[RouteResultView, ...]


@dataclass(frozen=True, slots=True)
class TeamSimulationView:
    valid: bool
    route_id: uuid.UUID
    team: RouteTeamView | None
    route_cost: RouteCostView | None
    issues: tuple[str, ...]


class OptimizationResultService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._cost_engine = FinalCostEngine()

    def persist(
        self,
        *,
        operation: OperationModel,
        algorithm_result: OptimizationResult,
        validation: ValidationResult,
        deliveries: list[OptimizationDelivery],
        delivery_models: list[DeliveryModel],
        vehicles: list[VehicleView],
        workers: list[WorkerView],
        actor_user_id: uuid.UUID,
        run_id: uuid.UUID | None = None,
    ) -> OptimizationResultView:
        if not validation.valid:
            raise OptimizationApprovalError("Somente uma solução validada pode ser persistida.")
        team_plan = TeamAssignmentSolver().solve(
            routes=algorithm_result.best.solution.routes,
            deliveries=deliveries,
            vehicles=vehicles,
            workers=workers,
        )
        team_by_vehicle = team_plan.by_vehicle()
        vehicle_by_id = {vehicle.id: vehicle for vehicle in vehicles}
        delivery_model_by_id = {delivery.id: delivery for delivery in delivery_models}
        delivery_addresses = {
            delivery.id: delivery.destination_address_id for delivery in delivery_models
        }
        geometry_builder = RoutingMatrixBuilder(self._session)

        revision_number = operation.current_revision_number + 1
        revision = OperationRevisionModel(
            operation_id=operation.id,
            revision_number=revision_number,
            status=RevisionStatus.OPTIMIZED,
            operation_date=operation.operation_date,
            operation_start_time=operation.operation_start_time,
            operation_end_time=operation.operation_end_time,
            traffic_mode=operation.traffic_mode,
            created_by_user_id=actor_user_id,
            notes="Resultado validado do algoritmo genético.",
            optimized_at=datetime.now(UTC),
        )
        self._session.add(revision)
        self._session.flush()

        route_rows: list[tuple[RoutePlanModel, RouteCostBreakdown]] = []
        critical_delays = 0
        on_time_count = 0
        total_stops = 0
        for route in algorithm_result.best.solution.routes:
            vehicle = vehicle_by_id[route.vehicle_id]
            team = team_by_vehicle[route.vehicle_id]
            breakdown = self._cost_engine.calculate(route=route, vehicle=vehicle, team=team)
            weight_utilization = self._percentage(
                route.total_weight_kg,
                vehicle.max_payload_kg,
            )
            volume_utilization = self._percentage(
                route.total_volume_m3,
                vehicle.max_volume_m3,
            )
            geometry = geometry_builder.build_route_geometry(
                operation=operation,
                delivery_addresses=delivery_addresses,
                delivery_ids=route.delivery_ids,
            )
            route_row = RoutePlanModel(
                route_code=f"R-{len(route_rows) + 1:02d}",
                sequence=len(route_rows) + 1,
                vehicle_id=route.vehicle_id,
                total_weight_kg=route.total_weight_kg,
                total_volume_m3=route.total_volume_m3,
                distance_km=route.distance_km,
                duration_minutes=route.total_duration_minutes,
                weight_utilization_pct=weight_utilization,
                volume_utilization_pct=volume_utilization,
                depreciation_brl=breakdown.depreciation_brl,
                maintenance_brl=breakdown.maintenance_brl,
                fixed_time_brl=breakdown.fixed_time_brl,
                fuel_brl=breakdown.fuel_brl,
                team_brl=breakdown.team_brl,
                contract_brl=breakdown.contract_brl,
                total_cost_brl=breakdown.total_brl,
                geometry=geometry,
            )
            route_rows.append((route_row, breakdown))
            for stop in route.stops:
                total_stops += 1
                if stop.lateness_minutes <= ZERO:
                    on_time_count += 1
                delivery = delivery_model_by_id[stop.delivery_id]
                if delivery.priority is DeliveryPriority.CRITICAL and stop.lateness_minutes > ZERO:
                    critical_delays += 1

        total_cost = sum((breakdown.total_brl for _row, breakdown in route_rows), ZERO)
        total_distance = sum((row.distance_km for row, _breakdown in route_rows), ZERO)
        makespan = max(
            (row.duration_minutes for row, _breakdown in route_rows),
            default=ZERO,
        )
        avg_weight = self._average([row.weight_utilization_pct for row, _breakdown in route_rows])
        avg_volume = self._average([row.volume_utilization_pct for row, _breakdown in route_rows])
        on_time = (
            HUNDRED if total_stops == 0 else Decimal(on_time_count) / Decimal(total_stops) * HUNDRED
        )

        if run_id is None:
            run = OptimizationRunModel(
                operation_id=operation.id,
                operation_revision_id=revision.id,
                status=OptimizationRunStatus.COMPLETED.value,
                random_seed=algorithm_result.random_seed,
                generations_completed=algorithm_result.generations_completed,
                stop_reason=algorithm_result.stop_reason,
                validated=True,
                delivery_count=len(deliveries),
                vehicles_used=len(route_rows),
                total_cost_brl=total_cost,
                distance_km=total_distance,
                makespan_minutes=makespan,
                critical_delays=critical_delays,
                on_time_percentage=on_time,
                average_weight_utilization_pct=avg_weight,
                average_volume_utilization_pct=avg_volume,
                pruning_counts=algorithm_result.pruning_counts,
                completed_at=datetime.now(UTC),
            )
            self._session.add(run)
        else:
            run = self._session.get(OptimizationRunModel, run_id)
            if run is None or run.operation_id != operation.id:
                raise OptimizationResultNotFoundError(run_id)
            run.operation_revision_id = revision.id
            run.status = OptimizationRunStatus.COMPLETED.value
            run.random_seed = algorithm_result.random_seed
            run.generations_completed = algorithm_result.generations_completed
            run.stop_reason = algorithm_result.stop_reason
            run.validated = True
            run.delivery_count = len(deliveries)
            run.vehicles_used = len(route_rows)
            run.total_cost_brl = total_cost
            run.distance_km = total_distance
            run.makespan_minutes = makespan
            run.critical_delays = critical_delays
            run.on_time_percentage = on_time
            run.average_weight_utilization_pct = avg_weight
            run.average_volume_utilization_pct = avg_volume
            run.pruning_counts = algorithm_result.pruning_counts
            run.error_code = None
            run.error_message = None
            run.completed_at = datetime.now(UTC)
        self._session.flush()

        for route_row, _breakdown in route_rows:
            route_row.optimization_run_id = run.id
            self._session.add(route_row)
            self._session.flush()
            team = team_by_vehicle[route_row.vehicle_id]
            self._session.add(
                RouteTeamAssignmentModel(
                    route_id=route_row.id,
                    primary_role=(
                        team.primary_role.value if team.primary_role is not None else None
                    ),
                    primary_worker_id=team.primary_worker_id,
                    helper_worker_id=team.helper_worker_id,
                    primary_included=team.primary_included,
                    helper_included=team.helper_included,
                    team_cost_brl=team.team_cost_brl,
                )
            )
            decoded_route = next(
                route
                for route in algorithm_result.best.solution.routes
                if route.vehicle_id == route_row.vehicle_id
            )
            stops_by_delivery = {stop.delivery_id: stop for stop in decoded_route.stops}
            for sequence, delivery_id in enumerate(decoded_route.delivery_ids, start=1):
                route_stop = stops_by_delivery.get(delivery_id)
                self._session.add(
                    RouteStopModel(
                        route_id=route_row.id,
                        delivery_id=delivery_id,
                        sequence=sequence,
                        planned_arrival_at=(
                            route_stop.arrival_at if route_stop is not None else None
                        ),
                        planned_departure_at=(
                            route_stop.departure_at if route_stop is not None else None
                        ),
                        lateness_minutes=(
                            route_stop.lateness_minutes if route_stop is not None else ZERO
                        ),
                    )
                )

        operation.current_revision_number = revision_number
        operation.status = OperationStatus.OPTIMIZED
        self._session.flush()
        return self.get_result(run.id)

    def latest_for_operation(self, operation_id: uuid.UUID) -> OptimizationResultView:
        run_id = self._session.scalar(
            select(OptimizationRunModel.id)
            .where(
                OptimizationRunModel.operation_id == operation_id,
                OptimizationRunModel.status == OptimizationRunStatus.COMPLETED.value,
                OptimizationRunModel.validated.is_(True),
            )
            .order_by(OptimizationRunModel.created_at.desc())
            .limit(1)
        )
        if run_id is None:
            raise OptimizationResultNotFoundError(operation_id)
        return self.get_result(run_id)

    def get_result(self, run_id: uuid.UUID) -> OptimizationResultView:
        run = self._session.get(OptimizationRunModel, run_id)
        if (
            run is None
            or run.status != OptimizationRunStatus.COMPLETED.value
            or run.operation_revision_id is None
        ):
            raise OptimizationResultNotFoundError(run_id)
        revision = self._session.get(OperationRevisionModel, run.operation_revision_id)
        if revision is None:
            raise OptimizationResultNotFoundError(run.operation_revision_id)
        routes = list(
            self._session.scalars(
                select(RoutePlanModel)
                .where(RoutePlanModel.optimization_run_id == run.id)
                .order_by(RoutePlanModel.sequence)
            )
        )
        return OptimizationResultView(
            run_id=run.id,
            operation_id=run.operation_id,
            revision_number=revision.revision_number,
            status=run.status,
            validated=run.validated,
            random_seed=run.random_seed,
            generations_completed=run.generations_completed,
            stop_reason=run.stop_reason,
            delivery_count=run.delivery_count,
            vehicles_used=run.vehicles_used,
            total_cost_brl=run.total_cost_brl,
            distance_km=run.distance_km,
            makespan_minutes=run.makespan_minutes,
            critical_delays=run.critical_delays,
            on_time_percentage=run.on_time_percentage,
            average_weight_utilization_pct=run.average_weight_utilization_pct,
            average_volume_utilization_pct=run.average_volume_utilization_pct,
            pruning_counts=run.pruning_counts,
            routes=tuple(self._route_view(route) for route in routes),
        )

    def get_route(self, route_id: uuid.UUID) -> RouteResultView:
        route = self._session.get(RoutePlanModel, route_id)
        if route is None:
            raise OptimizationResultNotFoundError(route_id)
        return self._route_view(route)

    def approve(self, run_id: uuid.UUID) -> OptimizationResultView:
        run = self._session.get(OptimizationRunModel, run_id)
        if run is None:
            raise OptimizationResultNotFoundError(run_id)
        if not run.validated or run.status != OptimizationRunStatus.COMPLETED.value:
            raise OptimizationApprovalError("O resultado precisa estar concluído e validado.")
        operation = self._session.get(OperationModel, run.operation_id)
        revision = (
            self._session.get(OperationRevisionModel, run.operation_revision_id)
            if run.operation_revision_id is not None
            else None
        )
        if operation is None or revision is None:
            raise OptimizationResultNotFoundError(run.operation_id)
        if operation.current_revision_number != revision.revision_number:
            raise OptimizationApprovalError(
                "O resultado não corresponde à revisão atual da operação."
            )
        if operation.status is OperationStatus.OUTDATED:
            raise OptimizationApprovalError("Plano desatualizado precisa ser reotimizado.")
        if operation.status is OperationStatus.DISPATCHED:
            raise OptimizationApprovalError("Operação já despachada é imutável.")
        operation.status = OperationStatus.APPROVED
        revision.status = RevisionStatus.APPROVED
        revision.approved_at = datetime.now(UTC)
        self._session.flush()
        return self.get_result(run.id)

    def simulate_team(
        self,
        route_id: uuid.UUID,
        *,
        primary_worker_id: uuid.UUID | None,
        helper_worker_id: uuid.UUID | None,
        apply: bool = False,
    ) -> TeamSimulationView:
        route = self._session.get(RoutePlanModel, route_id)
        if route is None:
            raise OptimizationResultNotFoundError(route_id)
        run = self._session.get(OptimizationRunModel, route.optimization_run_id)
        vehicle_model = self._session.get(VehicleModel, route.vehicle_id)
        if run is None or vehicle_model is None:
            raise OptimizationResultNotFoundError(route_id)
        resource_view = ResourceService(self._session).get_operation_resources(run.operation_id)
        selected_worker_ids = set(resource_view.selected_worker_ids)
        workers = [worker for worker in resource_view.workers if worker.id in selected_worker_ids]
        vehicle = next(
            (item for item in resource_view.vehicles if item.id == route.vehicle_id),
            None,
        )
        if vehicle is None:
            raise TeamSimulationError("Veículo da rota não está mais disponível no cadastro.")
        issues: list[str] = []
        primary = self._selected_worker(
            primary_worker_id,
            workers,
            selected_worker_ids,
            issues,
        )
        helper = self._selected_worker(
            helper_worker_id,
            workers,
            selected_worker_ids,
            issues,
        )
        required_primary_role = (
            WorkerRole.MOTORCYCLE_COURIER if vehicle.type is VehicleType.MOTO else WorkerRole.DRIVER
        )
        if vehicle.cost.driver_included:
            if primary is not None:
                issues.append("Motorista já está incluído no contrato do veículo.")
        elif primary is None or primary.role is not required_primary_role:
            issues.append(f"A rota exige uma pessoa com função {required_primary_role.value}.")

        delivery_models = list(
            self._session.scalars(
                select(DeliveryModel)
                .join(RouteStopModel, RouteStopModel.delivery_id == DeliveryModel.id)
                .where(RouteStopModel.route_id == route.id)
            )
        )
        helper_required = vehicle.helper_policy.value == "REQUIRED" or any(
            delivery.handling_requirement is HandlingRequirement.TWO_PERSON
            for delivery in delivery_models
        )
        if vehicle.cost.helper_included:
            if helper is not None:
                issues.append("Ajudante já está incluído no contrato do veículo.")
        elif helper_required and (helper is None or helper.role is not WorkerRole.HELPER):
            issues.append("A rota exige ajudante selecionado.")
        elif helper is not None and helper.role is not WorkerRole.HELPER:
            issues.append("A pessoa selecionada como ajudante não possui função HELPER.")

        occupied = self._workers_used_by_other_routes(route)
        for worker in (primary, helper):
            if worker is not None and worker.id in occupied:
                issues.append(f"{worker.name} já está alocado em outra rota desta operação.")
        if issues:
            return TeamSimulationView(
                valid=False,
                route_id=route.id,
                team=None,
                route_cost=None,
                issues=tuple(dict.fromkeys(issues)),
            )

        duration_hours = route.duration_minutes / Decimal("60")
        team_cost = ZERO
        for worker in (primary, helper):
            if worker is not None:
                team_cost += WorkerCompensationCalculator.estimate(
                    model=worker.compensation_model,
                    value_brl=worker.compensation_value_brl,
                    duration_hours=duration_hours,
                )
        assignment = RouteTeamAssignment(
            vehicle_id=route.vehicle_id,
            primary_role=None if vehicle.cost.driver_included else required_primary_role,
            primary_worker_id=primary.id if primary is not None else None,
            helper_worker_id=helper.id if helper is not None else None,
            primary_included=vehicle.cost.driver_included,
            helper_included=vehicle.cost.helper_included,
            team_cost_brl=team_cost,
        )
        decoded_route = self._decoded_route_proxy(route)
        breakdown = self._cost_engine.calculate(
            route=decoded_route,
            vehicle=vehicle,
            team=assignment,
        )
        if apply:
            team_row = self._session.get(RouteTeamAssignmentModel, route.id)
            if team_row is None:
                raise OptimizationResultNotFoundError(route.id)
            team_row.primary_role = (
                assignment.primary_role.value if assignment.primary_role is not None else None
            )
            team_row.primary_worker_id = assignment.primary_worker_id
            team_row.helper_worker_id = assignment.helper_worker_id
            team_row.primary_included = assignment.primary_included
            team_row.helper_included = assignment.helper_included
            team_row.team_cost_brl = assignment.team_cost_brl
            route.team_brl = breakdown.team_brl
            route.total_cost_brl = breakdown.total_brl
            self._recalculate_run_total(run)
            self._session.flush()
        return TeamSimulationView(
            valid=True,
            route_id=route.id,
            team=self._team_view_from_assignment(assignment, primary, helper),
            route_cost=self._cost_view(breakdown),
            issues=(),
        )

    @staticmethod
    def _percentage(value: Decimal, capacity: Decimal) -> Decimal:
        if capacity <= ZERO:
            return ZERO
        return value / capacity * HUNDRED

    @staticmethod
    def _average(values: list[Decimal]) -> Decimal:
        if not values:
            return ZERO
        return sum(values, ZERO) / Decimal(len(values))

    def _route_view(self, route: RoutePlanModel) -> RouteResultView:
        vehicle = self._session.get(VehicleModel, route.vehicle_id)
        team = self._session.get(RouteTeamAssignmentModel, route.id)
        if vehicle is None or team is None:
            raise OptimizationResultNotFoundError(route.id)
        stop_rows = list(
            self._session.scalars(
                select(RouteStopModel)
                .where(RouteStopModel.route_id == route.id)
                .order_by(RouteStopModel.sequence)
            )
        )
        return RouteResultView(
            id=route.id,
            route_code=route.route_code,
            vehicle=VehicleResultView(
                id=vehicle.id,
                plate=vehicle.plate,
                type=vehicle.type.value,
                ownership_type=vehicle.ownership_type.value,
            ),
            team=self._team_view(team),
            delivery_count=len(stop_rows),
            distance_km=route.distance_km,
            duration_minutes=route.duration_minutes,
            total_weight_kg=route.total_weight_kg,
            total_volume_m3=route.total_volume_m3,
            weight_utilization_pct=route.weight_utilization_pct,
            volume_utilization_pct=route.volume_utilization_pct,
            cost=RouteCostView(
                depreciation_brl=route.depreciation_brl,
                maintenance_brl=route.maintenance_brl,
                fixed_time_brl=route.fixed_time_brl,
                fuel_brl=route.fuel_brl,
                team_brl=route.team_brl,
                contract_brl=route.contract_brl,
                total_brl=route.total_cost_brl,
            ),
            geometry=route.geometry,
            stops=tuple(self._stop_view(stop) for stop in stop_rows),
        )

    def _stop_view(self, stop: RouteStopModel) -> RouteStopView:
        delivery = self._session.get(DeliveryModel, stop.delivery_id)
        if delivery is None:
            raise OptimizationResultNotFoundError(stop.delivery_id)
        address_row = self._session.execute(
            select(
                AddressModel,
                StreetModel.name,
                DistrictModel.name,
                func.ST_X(AddressModel.location),
                func.ST_Y(AddressModel.location),
            )
            .join(StreetModel, StreetModel.id == AddressModel.street_id)
            .join(DistrictModel, DistrictModel.id == AddressModel.district_id)
            .where(AddressModel.id == delivery.destination_address_id)
        ).one()
        address, street_name, district_name, longitude, latitude = address_row
        return RouteStopView(
            id=stop.id,
            sequence=stop.sequence,
            delivery_id=delivery.id,
            delivery_code=delivery.delivery_code,
            recipient_name=delivery.recipient_name,
            address_label=f"{street_name}, {address.house_number} — {district_name}",
            priority=delivery.priority.value,
            longitude=float(longitude),
            latitude=float(latitude),
            planned_arrival_at=stop.planned_arrival_at,
            planned_departure_at=stop.planned_departure_at,
            time_window_start=delivery.time_window_start,
            time_window_end=delivery.time_window_end,
            time_window_policy=delivery.time_window_policy.value,
            service_time_minutes=delivery.service_time_minutes,
            lateness_minutes=stop.lateness_minutes,
        )

    def _team_view(self, team: RouteTeamAssignmentModel) -> RouteTeamView:
        primary = (
            self._session.get(WorkerModel, team.primary_worker_id)
            if team.primary_worker_id is not None
            else None
        )
        helper = (
            self._session.get(WorkerModel, team.helper_worker_id)
            if team.helper_worker_id is not None
            else None
        )
        return RouteTeamView(
            primary_role=team.primary_role,
            primary_worker=self._worker_result(primary),
            helper=self._worker_result(helper),
            primary_included=team.primary_included,
            helper_included=team.helper_included,
            team_cost_brl=team.team_cost_brl,
        )

    @staticmethod
    def _worker_result(worker: WorkerModel | None) -> WorkerResultView | None:
        if worker is None:
            return None
        return WorkerResultView(id=worker.id, name=worker.name, role=worker.role.value)

    @staticmethod
    def _team_view_from_assignment(
        assignment: RouteTeamAssignment,
        primary: WorkerView | None,
        helper: WorkerView | None,
    ) -> RouteTeamView:
        return RouteTeamView(
            primary_role=(
                assignment.primary_role.value if assignment.primary_role is not None else None
            ),
            primary_worker=(
                WorkerResultView(id=primary.id, name=primary.name, role=primary.role.value)
                if primary is not None
                else None
            ),
            helper=(
                WorkerResultView(id=helper.id, name=helper.name, role=helper.role.value)
                if helper is not None
                else None
            ),
            primary_included=assignment.primary_included,
            helper_included=assignment.helper_included,
            team_cost_brl=assignment.team_cost_brl,
        )

    @staticmethod
    def _cost_view(breakdown: RouteCostBreakdown) -> RouteCostView:
        return RouteCostView(
            depreciation_brl=breakdown.depreciation_brl,
            maintenance_brl=breakdown.maintenance_brl,
            fixed_time_brl=breakdown.fixed_time_brl,
            fuel_brl=breakdown.fuel_brl,
            team_brl=breakdown.team_brl,
            contract_brl=breakdown.contract_brl,
            total_brl=breakdown.total_brl,
        )

    @staticmethod
    def _selected_worker(
        worker_id: uuid.UUID | None,
        workers: list[WorkerView],
        selected_ids: set[uuid.UUID],
        issues: list[str],
    ) -> WorkerView | None:
        if worker_id is None:
            return None
        worker = next((item for item in workers if item.id == worker_id), None)
        if worker is None or worker_id not in selected_ids:
            issues.append("A pessoa informada não está selecionada para a operação.")
            return None
        return worker

    def _workers_used_by_other_routes(self, route: RoutePlanModel) -> set[uuid.UUID]:
        rows = self._session.execute(
            select(
                RouteTeamAssignmentModel.primary_worker_id,
                RouteTeamAssignmentModel.helper_worker_id,
            )
            .join(RoutePlanModel, RoutePlanModel.id == RouteTeamAssignmentModel.route_id)
            .where(
                RoutePlanModel.optimization_run_id == route.optimization_run_id,
                RoutePlanModel.id != route.id,
            )
        ).all()
        return {
            worker_id
            for primary_worker_id, helper_worker_id in rows
            for worker_id in (primary_worker_id, helper_worker_id)
            if worker_id is not None
        }

    @staticmethod
    def _decoded_route_proxy(route: RoutePlanModel) -> DecodedRoute:
        return DecodedRoute(
            vehicle_id=route.vehicle_id,
            delivery_ids=(),
            total_weight_kg=route.total_weight_kg,
            total_volume_m3=route.total_volume_m3,
            distance_km=route.distance_km,
            travel_minutes=route.duration_minutes,
            service_minutes=0,
            total_duration_minutes=route.duration_minutes,
            total_cost_brl=route.total_cost_brl,
        )

    def _recalculate_run_total(self, run: OptimizationRunModel) -> None:
        total = self._session.scalar(
            select(func.coalesce(func.sum(RoutePlanModel.total_cost_brl), 0)).where(
                RoutePlanModel.optimization_run_id == run.id
            )
        )
        run.total_cost_brl = Decimal(str(total))


__all__ = [
    "OptimizationApprovalError",
    "OptimizationResultNotFoundError",
    "OptimizationResultService",
    "OptimizationResultView",
    "RouteResultView",
    "TeamAssignmentError",
    "TeamSimulationError",
    "TeamSimulationView",
]
