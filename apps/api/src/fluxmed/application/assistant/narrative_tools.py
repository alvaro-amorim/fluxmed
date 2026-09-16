import uuid

from sqlalchemy.orm import Session

from fluxmed.application.assistant.tools import AssistantToolRegistry
from fluxmed.llm import ToolCall, ToolDefinition, ToolResult


class AssistantNarrativeToolset:
    NAMES = {
        "generate_driver_instructions",
        "generate_dispatch_report",
        "generate_daily_operation_report",
        "generate_executive_summary",
    }

    def __init__(self, session: Session, *, context_operation_id: uuid.UUID | None) -> None:
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
            "description": "UUID da rota atual usada para gerar instruções ao motorista.",
        }
        return (
            self._definition(
                "generate_driver_instructions",
                (
                    "Fornece contexto estruturado para redigir instruções operacionais ao "
                    "motorista de uma rota. Não altera o plano."
                ),
                {"operation_id": operation, "route_id": route},
                ["operation_id", "route_id"],
            ),
            self._definition(
                "generate_dispatch_report",
                "Fornece contexto estruturado do plano validado para um relatório de despacho.",
                {"operation_id": operation},
                ["operation_id"],
            ),
            self._definition(
                "generate_daily_operation_report",
                "Fornece contexto estruturado para narrativa do relatório diário da operação.",
                {"operation_id": operation},
                ["operation_id"],
            ),
            self._definition(
                "generate_executive_summary",
                "Fornece contexto estruturado conciso para um resumo executivo da operação.",
                {"operation_id": operation},
                ["operation_id"],
            ),
        )

    def execute(self, call: ToolCall) -> ToolResult:
        if call.name not in self.NAMES:
            return self._unknown(call)
        operation_id = call.arguments.get("operation_id")
        summary = self._read_result(
            ToolCall(
                id=f"{call.id}-summary",
                name="get_operation_summary",
                arguments={"operation_id": operation_id},
            )
        )
        if summary is None:
            return self._failed(call, "Não foi possível obter o resumo oficial da operação.")

        if call.name == "generate_driver_instructions":
            route_id = call.arguments.get("route_id")
            route = self._read_result(
                ToolCall(
                    id=f"{call.id}-route",
                    name="get_route_details",
                    arguments={"operation_id": operation_id, "entity_id": route_id},
                )
            )
            if route is None:
                return self._failed(call, "Rota não encontrada no plano atual da operação.")
            content: dict[str, object] = {
                "generation_kind": "driver_instructions",
                "operation": summary.get("operation"),
                "route": route,
                "instructions": [
                    "Use a ordem das paradas exatamente como fornecida no plano validado.",
                    "Destaque prioridades e janelas de atendimento sem inventar horários.",
                    "Não altere rota, equipe, veículo ou sequência durante a redação.",
                ],
            }
            return ToolResult(call_id=call.id, name=call.name, content=content)

        cost = self._read_result(
            ToolCall(
                id=f"{call.id}-cost",
                name="get_cost_breakdown",
                arguments={"operation_id": operation_id},
            )
        )
        team = self._read_result(
            ToolCall(
                id=f"{call.id}-team",
                name="get_team_assignment_details",
                arguments={"operation_id": operation_id},
            )
        )
        content = {
            "generation_kind": call.name.removeprefix("generate_"),
            "summary": summary,
            "cost": cost,
            "team": team,
            "instructions": [
                "Use apenas os valores presentes neste payload.",
                "Separe fatos operacionais de recomendações textuais.",
                "Não afirme causas ou riscos que não estejam sustentados pelos dados.",
            ],
        }
        return ToolResult(call_id=call.id, name=call.name, content=content)

    def _read_result(self, call: ToolCall) -> dict[str, object] | None:
        result = self._read.execute(call)
        return result.content if result.success else None

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

    @staticmethod
    def _unknown(call: ToolCall) -> ToolResult:
        return AssistantNarrativeToolset._failed(call, "Tool narrativa não autorizada.")
