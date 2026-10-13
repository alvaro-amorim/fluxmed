import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from fluxmed.application.assistant.tools import AssistantToolRegistry
from fluxmed.application.optimization.results import (
    OptimizationResultNotFoundError,
    OptimizationResultService,
    TeamSimulationError,
    TeamSimulationView,
)
from fluxmed.llm import ToolCall, ToolDefinition, ToolResult


class AssistantSimulationToolset:
    """Safe what-if tools. These tools validate alternatives and never persist plan changes."""

    NAMES = {
        "simulate_driver_swap",
        "simulate_helper_removal",
    }

    def __init__(self, session: Session, *, context_operation_id: uuid.UUID | None) -> None:
        self._session = session
        self._read = AssistantToolRegistry(
            session,
            context_operation_id=context_operation_id,
        )

    def definitions(self) -> tuple[ToolDefinition, ...]:
        operation = {
            "type": "string",
            "format": "uuid",
            "description": "UUID da operação selecionada no contexto.",
        }
        route = {
            "type": "string",
            "format": "uuid",
            "description": "UUID da rota atual pertencente ao plano selecionado.",
        }
        worker = {
            "type": "string",
            "format": "uuid",
            "description": "UUID do motorista alternativo já selecionado na operação.",
        }
        return (
            self._definition(
                "simulate_driver_swap",
                (
                    "Simula a troca do motorista de uma rota usando o validador oficial. "
                    "Não altera a operação."
                ),
                {
                    "operation_id": operation,
                    "route_id": route,
                    "new_driver_id": worker,
                },
                ["operation_id", "route_id", "new_driver_id"],
            ),
            self._definition(
                "simulate_helper_removal",
                (
                    "Simula remover o ajudante atual de uma rota e valida o impacto. "
                    "Não altera a operação."
                ),
                {"operation_id": operation, "route_id": route},
                ["operation_id", "route_id"],
            ),
        )

    def execute(self, call: ToolCall) -> ToolResult:
        if call.name not in self.NAMES:
            return self._failed(call, "Tool de simulação não autorizada.")

        operation_id = call.arguments.get("operation_id")
        route_id = call.arguments.get("route_id")
        route_result = self._read.execute(
            ToolCall(
                id=f"{call.id}-route",
                name="get_route_details",
                arguments={"operation_id": operation_id, "entity_id": route_id},
            )
        )
        if not route_result.success:
            return self._failed(call, route_result.error or "Rota não encontrada.")

        try:
            parsed_route_id = uuid.UUID(str(route_id))
        except (ValueError, AttributeError):
            return self._failed(call, "route_id inválido.")

        team = route_result.content.get("team")
        if not isinstance(team, dict):
            return self._failed(call, "Equipe atual da rota indisponível.")
        current_primary = self._nested_uuid(team, "primary_worker")
        current_helper = self._nested_uuid(team, "helper")
        current_cost = self._decimal(route_result.content.get("cost_brl"))

        try:
            if call.name == "simulate_driver_swap":
                try:
                    new_driver_id = uuid.UUID(str(call.arguments.get("new_driver_id")))
                except (ValueError, AttributeError):
                    return self._failed(call, "new_driver_id inválido.")
                simulation = OptimizationResultService(self._session).simulate_team(
                    parsed_route_id,
                    primary_worker_id=new_driver_id,
                    helper_worker_id=current_helper,
                    apply=False,
                )
                return self._result(call, simulation, current_cost)

            simulation = OptimizationResultService(self._session).simulate_team(
                parsed_route_id,
                primary_worker_id=current_primary,
                helper_worker_id=None,
                apply=False,
            )
        except (OptimizationResultNotFoundError, TeamSimulationError) as exc:
            return self._failed(call, str(exc))
        return self._result(call, simulation, current_cost)

    @staticmethod
    def _result(
        call: ToolCall,
        simulation: TeamSimulationView,
        current_cost: Decimal | None,
    ) -> ToolResult:
        simulated_cost = (
            simulation.route_cost.total_brl if simulation.route_cost is not None else None
        )
        delta = (
            simulated_cost - current_cost
            if simulated_cost is not None and current_cost is not None
            else None
        )
        content: dict[str, object] = {
            "simulation_only": True,
            "applied": False,
            "valid": simulation.valid,
            "route_id": str(simulation.route_id),
            "issues": list(simulation.issues),
            "current_route_cost_brl": str(current_cost) if current_cost is not None else None,
            "simulated_route_cost_brl": (
                str(simulated_cost) if simulated_cost is not None else None
            ),
            "cost_delta_brl": str(delta) if delta is not None else None,
        }
        if simulation.team is not None:
            content["simulated_team"] = {
                "primary_worker_id": (
                    str(simulation.team.primary_worker.id)
                    if simulation.team.primary_worker is not None
                    else None
                ),
                "primary_worker_name": (
                    simulation.team.primary_worker.name
                    if simulation.team.primary_worker is not None
                    else None
                ),
                "helper_id": (
                    str(simulation.team.helper.id) if simulation.team.helper is not None else None
                ),
                "helper_name": (
                    simulation.team.helper.name if simulation.team.helper is not None else None
                ),
                "team_cost_brl": str(simulation.team.team_cost_brl),
            }
        return ToolResult(call_id=call.id, name=call.name, content=content)

    @staticmethod
    def _nested_uuid(team: dict[str, object], field: str) -> uuid.UUID | None:
        value = team.get(field)
        if not isinstance(value, dict):
            return None
        raw = value.get("id")
        try:
            return uuid.UUID(str(raw))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

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
    def _failed(call: ToolCall, error: str) -> ToolResult:
        return ToolResult(
            call_id=call.id,
            name=call.name,
            content={},
            success=False,
            error=error,
        )
