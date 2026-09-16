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
            route = self._enrich_route_stops(operation_id, route, call.id)
            content: dict[str, object] = {
                "generation_kind": "driver_instructions",
                "operation": summary.get("operation"),
                "route": route,
                "instructions": [
                    "Use a ordem das paradas exatamente como fornecida no plano validado.",
                    "Destaque prioridades e janelas de atendimento sem inventar horários.",
                    "Informe endereço e requisitos especiais somente quando presentes nos dados.",
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
        algorithm = self._read_result(
            ToolCall(
                id=f"{call.id}-algorithm",
                name="get_algorithm_run_summary",
                arguments={"operation_id": operation_id},
            )
        )
        comparison = self._read_result(
            ToolCall(
                id=f"{call.id}-comparison",
                name="get_comparison_results",
                arguments={"operation_id": operation_id},
            )
        )
        content = {
            "generation_kind": call.name.removeprefix("generate_"),
            "summary": summary,
            "cost": cost,
            "team": team,
            "algorithm": algorithm,
            "comparison": comparison,
            "instructions": [
                "Use apenas os valores presentes neste payload.",
                "Separe fatos operacionais de recomendações textuais.",
                "Não afirme causas, ganhos ou riscos que não estejam sustentados pelos dados.",
                "Quando comparação ou métrica estiver ausente, declare a indisponibilidade.",
            ],
        }
        return ToolResult(call_id=call.id, name=call.name, content=content)

    def _enrich_route_stops(
        self,
        operation_id: object,
        route: dict[str, object],
        call_id: str,
    ) -> dict[str, object]:
        stops = route.get("stops")
        if not isinstance(stops, list):
            return route
        enriched: list[object] = []
        for index, stop in enumerate(stops):
            if not isinstance(stop, dict):
                enriched.append(stop)
                continue
            delivery_id = stop.get("delivery_id")
            delivery = self._read_result(
                ToolCall(
                    id=f"{call_id}-delivery-{index}",
                    name="get_delivery_details",
                    arguments={"operation_id": operation_id, "entity_id": delivery_id},
                )
            )
            if delivery is None:
                enriched.append(dict(stop))
                continue
            merged = dict(stop)
            for field in (
                "recipient_name",
                "destination_address",
                "district_name",
                "time_window_start",
                "time_window_end",
                "time_window_policy",
                "temperature_class",
                "handling_requirement",
                "service_time_minutes",
            ):
                merged[field] = delivery.get(field)
            enriched.append(merged)
        result = dict(route)
        result["stops"] = enriched
        return result

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
