import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.application.deliveries import DeliveryService
from fluxmed.application.operations import OperationService
from fluxmed.application.optimization.results import (
    OptimizationResultNotFoundError,
    OptimizationResultService,
)
from fluxmed.application.resources import ResourceService
from fluxmed.infrastructure.models.optimization_result import OptimizationTraceEventModel
from fluxmed.llm import ToolCall, ToolDefinition, ToolResult


class AssistantToolError(RuntimeError):
    pass


class AssistantToolPermissionError(AssistantToolError):
    pass


ToolHandler = Callable[[dict[str, object]], dict[str, object]]


class AssistantToolRegistry:
    def __init__(self, session: Session, *, context_operation_id: uuid.UUID | None) -> None:
        self._session = session
        self._context_operation_id = context_operation_id
        self._handlers: dict[str, ToolHandler] = {
            "get_operation_summary": self._get_operation_summary,
            "get_route_details": self._get_route_details,
            "get_vehicle_details": self._get_vehicle_details,
            "get_delivery_details": self._get_delivery_details,
            "get_cost_breakdown": self._get_cost_breakdown,
            "get_comparison_results": self._get_comparison_results,
            "get_algorithm_run_summary": self._get_algorithm_run_summary,
            "get_team_assignment_details": self._get_team_assignment_details,
        }

    def definitions(self) -> tuple[ToolDefinition, ...]:
        operation_schema = self._operation_schema()
        scoped_entity_properties = {
            "operation_id": operation_schema,
            "entity_id": {
                "type": "string",
                "format": "uuid",
                "description": "UUID do recurso dentro da operação selecionada.",
            },
        }
        return (
            self._definition(
                "get_operation_summary",
                "Resumo oficial da operação e do plano otimizado atual, incluindo IDs das rotas.",
                {"operation_id": operation_schema},
                ["operation_id"],
            ),
            self._definition(
                "get_route_details",
                "Detalhes de uma rota do plano atual, paradas, equipe, custo e utilização.",
                scoped_entity_properties,
                ["operation_id", "entity_id"],
            ),
            self._definition(
                "get_vehicle_details",
                "Características e custos cadastrados de um veículo usado no plano atual.",
                scoped_entity_properties,
                ["operation_id", "entity_id"],
            ),
            self._definition(
                "get_delivery_details",
                "Dados operacionais de uma entrega pertencente à operação selecionada.",
                scoped_entity_properties,
                ["operation_id", "entity_id"],
            ),
            self._definition(
                "get_cost_breakdown",
                "Decompõe os custos oficiais por rota e mostra o custo total do plano atual.",
                {"operation_id": operation_schema},
                ["operation_id"],
            ),
            self._definition(
                "get_comparison_results",
                "Retorna a comparação final persistida entre GA e baselines, quando disponível.",
                {"operation_id": operation_schema},
                ["operation_id"],
            ),
            self._definition(
                "get_algorithm_run_summary",
                "Resumo auditável da execução do algoritmo genético e das podas realizadas.",
                {"operation_id": operation_schema},
                ["operation_id"],
            ),
            self._definition(
                "get_team_assignment_details",
                "Equipe oficialmente atribuída a cada rota do plano otimizado atual.",
                {"operation_id": operation_schema},
                ["operation_id"],
            ),
        )

    def execute(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.name)
        if handler is None:
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={},
                success=False,
                error="Tool não autorizada para este contexto.",
            )
        try:
            content = handler(call.arguments)
        except AssistantToolError as exc:
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={},
                success=False,
                error=str(exc),
            )
        except LookupError:
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={},
                success=False,
                error="Recurso não encontrado no contexto autorizado.",
            )
        return ToolResult(call_id=call.id, name=call.name, content=content)

    def _get_operation_summary(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        operation = OperationService(self._session).get(operation_id)
        result = self._latest_result_or_none(operation_id)
        optimization: dict[str, object] | None = None
        if result is not None:
            optimization = {
                "run_id": str(result.run_id),
                "revision_number": result.revision_number,
                "validated": result.validated,
                "delivery_count": result.delivery_count,
                "vehicles_used": result.vehicles_used,
                "total_cost_brl": str(result.total_cost_brl),
                "distance_km": str(result.distance_km),
                "makespan_minutes": str(result.makespan_minutes),
                "critical_delays": result.critical_delays,
                "on_time_percentage": str(result.on_time_percentage),
                "average_weight_utilization_pct": str(
                    result.average_weight_utilization_pct
                ),
                "average_volume_utilization_pct": str(
                    result.average_volume_utilization_pct
                ),
                "routes": [
                    {
                        "route_id": str(route.id),
                        "route_code": route.route_code,
                        "vehicle_id": str(route.vehicle.id),
                        "vehicle_plate": route.vehicle.plate,
                        "delivery_count": route.delivery_count,
                        "distance_km": str(route.distance_km),
                        "cost_brl": str(route.cost.total_brl),
                    }
                    for route in result.routes
                ],
            }
        return {
            "operation": {
                "id": str(operation.id),
                "operation_code": operation.operation_code,
                "operation_date": operation.operation_date.isoformat(),
                "status": operation.status.value,
                "traffic_mode": operation.traffic_mode.value,
                "revision_number": operation.current_revision_number,
            },
            "optimization": optimization,
        }

    def _get_route_details(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        route_id = self._entity_id(arguments)
        route = self._current_route(operation_id, route_id)
        return {
            "route_id": str(route.id),
            "route_code": route.route_code,
            "vehicle": {
                "id": str(route.vehicle.id),
                "plate": route.vehicle.plate,
                "type": route.vehicle.type,
                "ownership_type": route.vehicle.ownership_type,
            },
            "delivery_count": route.delivery_count,
            "distance_km": str(route.distance_km),
            "duration_minutes": str(route.duration_minutes),
            "total_weight_kg": str(route.total_weight_kg),
            "total_volume_m3": str(route.total_volume_m3),
            "weight_utilization_pct": str(route.weight_utilization_pct),
            "volume_utilization_pct": str(route.volume_utilization_pct),
            "cost_brl": str(route.cost.total_brl),
            "team": self._team_payload(route.team),
            "stops": [
                {
                    "delivery_id": str(stop.delivery_id),
                    "delivery_code": stop.delivery_code,
                    "sequence": stop.sequence,
                    "priority": stop.priority,
                    "planned_arrival_at": (
                        stop.planned_arrival_at.isoformat()
                        if stop.planned_arrival_at is not None
                        else None
                    ),
                    "lateness_minutes": str(stop.lateness_minutes),
                }
                for stop in route.stops
            ],
        }

    def _get_vehicle_details(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        vehicle_id = self._entity_id(arguments)
        result = self._require_latest_result(operation_id)
        if all(route.vehicle.id != vehicle_id for route in result.routes):
            raise AssistantToolPermissionError("Veículo fora do plano atual da operação.")
        vehicle = ResourceService(self._session).get_vehicle(vehicle_id)
        return {
            "id": str(vehicle.id),
            "plate": vehicle.plate,
            "type": vehicle.type.value,
            "ownership_type": vehicle.ownership_type.value,
            "max_payload_kg": str(vehicle.max_payload_kg),
            "max_volume_m3": str(vehicle.max_volume_m3),
            "max_range_km": str(vehicle.max_range_km),
            "refrigerated": vehicle.refrigerated,
            "helper_policy": vehicle.helper_policy.value,
            "fuel_type": vehicle.fuel_type.value if vehicle.fuel_type is not None else None,
            "fuel_efficiency_km_per_l": (
                str(vehicle.fuel_efficiency_km_per_l)
                if vehicle.fuel_efficiency_km_per_l is not None
                else None
            ),
            "cost": {
                "depreciation_per_km": self._optional_decimal(
                    vehicle.cost.depreciation_per_km
                ),
                "maintenance_per_km": self._optional_decimal(
                    vehicle.cost.maintenance_per_km
                ),
                "fixed_cost_per_hour": self._optional_decimal(
                    vehicle.cost.fixed_cost_per_hour
                ),
                "contract_price_brl": self._optional_decimal(
                    vehicle.cost.contract_price_brl
                ),
                "fuel_included": vehicle.cost.fuel_included,
                "driver_included": vehicle.cost.driver_included,
                "helper_included": vehicle.cost.helper_included,
            },
        }

    def _get_delivery_details(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        delivery_id = self._entity_id(arguments)
        delivery = DeliveryService(self._session).get(delivery_id)
        if delivery.operation_id != operation_id:
            raise AssistantToolPermissionError("Entrega fora da operação selecionada.")
        return {
            "id": str(delivery.id),
            "delivery_code": delivery.delivery_code,
            "recipient_name": delivery.recipient_name,
            "destination_address": delivery.destination_address,
            "district_name": delivery.district_name,
            "package_count": delivery.package_count,
            "total_weight_kg": str(delivery.total_weight_kg),
            "total_volume_m3": str(delivery.total_volume_m3),
            "priority": delivery.priority.value,
            "time_window_start": self._optional_datetime(delivery.time_window_start),
            "time_window_end": self._optional_datetime(delivery.time_window_end),
            "time_window_policy": delivery.time_window_policy.value,
            "service_time_minutes": delivery.service_time_minutes,
            "temperature_class": delivery.temperature_class.value,
            "handling_requirement": delivery.handling_requirement.value,
            "status": delivery.status.value,
        }

    def _get_cost_breakdown(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        result = self._require_latest_result(operation_id)
        return {
            "operation_id": str(operation_id),
            "run_id": str(result.run_id),
            "total_cost_brl": str(result.total_cost_brl),
            "routes": [
                {
                    "route_id": str(route.id),
                    "route_code": route.route_code,
                    "vehicle_plate": route.vehicle.plate,
                    "depreciation_brl": str(route.cost.depreciation_brl),
                    "maintenance_brl": str(route.cost.maintenance_brl),
                    "fixed_time_brl": str(route.cost.fixed_time_brl),
                    "fuel_brl": str(route.cost.fuel_brl),
                    "team_brl": str(route.cost.team_brl),
                    "contract_brl": str(route.cost.contract_brl),
                    "total_brl": str(route.cost.total_brl),
                }
                for route in result.routes
            ],
        }

    def _get_comparison_results(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        result = self._require_latest_result(operation_id)
        event = self._session.scalar(
            select(OptimizationTraceEventModel)
            .where(
                OptimizationTraceEventModel.optimization_run_id == result.run_id,
                OptimizationTraceEventModel.event_type == "final_comparison",
            )
            .order_by(OptimizationTraceEventModel.sequence.desc())
            .limit(1)
        )
        return {
            "operation_id": str(operation_id),
            "run_id": str(result.run_id),
            "comparison": event.payload if event is not None else None,
        }

    def _get_algorithm_run_summary(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        result = self._require_latest_result(operation_id)
        return {
            "operation_id": str(operation_id),
            "run_id": str(result.run_id),
            "random_seed": result.random_seed,
            "generations_completed": result.generations_completed,
            "stop_reason": result.stop_reason,
            "validated": result.validated,
            "pruning_counts": result.pruning_counts,
            "delivery_count": result.delivery_count,
            "vehicles_used": result.vehicles_used,
            "total_cost_brl": str(result.total_cost_brl),
            "distance_km": str(result.distance_km),
            "makespan_minutes": str(result.makespan_minutes),
        }

    def _get_team_assignment_details(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        result = self._require_latest_result(operation_id)
        return {
            "operation_id": str(operation_id),
            "run_id": str(result.run_id),
            "routes": [
                {
                    "route_id": str(route.id),
                    "route_code": route.route_code,
                    "vehicle_plate": route.vehicle.plate,
                    "team": self._team_payload(route.team),
                }
                for route in result.routes
            ],
        }

    def _current_route(self, operation_id: uuid.UUID, route_id: uuid.UUID):
        result = self._require_latest_result(operation_id)
        for route in result.routes:
            if route.id == route_id:
                return route
        raise AssistantToolPermissionError("Rota fora do plano atual da operação.")

    def _latest_result_or_none(self, operation_id: uuid.UUID):
        try:
            return OptimizationResultService(self._session).latest_for_operation(operation_id)
        except OptimizationResultNotFoundError:
            return None

    def _require_latest_result(self, operation_id: uuid.UUID):
        result = self._latest_result_or_none(operation_id)
        if result is None:
            raise AssistantToolError("A operação ainda não possui plano otimizado validado.")
        return result

    def _operation_id(self, arguments: dict[str, object]) -> uuid.UUID:
        operation_id = self._uuid(arguments.get("operation_id"), "operation_id")
        if (
            self._context_operation_id is not None
            and operation_id != self._context_operation_id
        ):
            raise AssistantToolPermissionError(
                "A tool tentou acessar uma operação diferente do contexto selecionado."
            )
        return operation_id

    @staticmethod
    def _entity_id(arguments: dict[str, object]) -> uuid.UUID:
        return AssistantToolRegistry._uuid(arguments.get("entity_id"), "entity_id")

    @staticmethod
    def _uuid(raw: object, field: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(raw))
        except (ValueError, AttributeError) as exc:
            raise AssistantToolError(f"{field} inválido.") from exc

    @staticmethod
    def _operation_schema() -> dict[str, object]:
        return {
            "type": "string",
            "format": "uuid",
            "description": "UUID da operação selecionada no contexto.",
        }

    @staticmethod
    def _definition(
        name: str,
        description: str,
        properties: dict[str, object],
        required: list[str],
    ) -> ToolDefinition:
        return ToolDefinition(
            name=name,
            description=description,
            input_schema={
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        )

    @staticmethod
    def _team_payload(team: object) -> dict[str, object]:
        primary_role = getattr(team, "primary_role", None)
        primary_worker = getattr(team, "primary_worker", None)
        helper = getattr(team, "helper", None)
        team_cost = getattr(team, "team_cost_brl", None)
        return {
            "primary_role": primary_role,
            "primary_worker": (
                {
                    "id": str(primary_worker.id),
                    "name": primary_worker.name,
                    "role": primary_worker.role,
                }
                if primary_worker is not None
                else None
            ),
            "helper": (
                {"id": str(helper.id), "name": helper.name, "role": helper.role}
                if helper is not None
                else None
            ),
            "team_cost_brl": str(team_cost) if team_cost is not None else "0",
        }

    @staticmethod
    def _optional_decimal(value: object) -> str | None:
        return None if value is None else str(value)

    @staticmethod
    def _optional_datetime(value: object) -> str | None:
        return value.isoformat() if hasattr(value, "isoformat") else None
