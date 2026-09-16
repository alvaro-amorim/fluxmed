import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from fluxmed.application.operations import OperationService
from fluxmed.application.optimization.results import (
    OptimizationResultNotFoundError,
    OptimizationResultService,
)
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
        }

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return (
            ToolDefinition(
                name="get_operation_summary",
                description=(
                    "Retorna o resumo oficial de uma operação FluxMed e, quando disponível, "
                    "as métricas do plano otimizado validado."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "operation_id": {
                            "type": "string",
                            "description": "UUID da operação selecionada no contexto.",
                        }
                    },
                    "required": ["operation_id"],
                    "additionalProperties": False,
                },
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
        return ToolResult(call_id=call.id, name=call.name, content=content)

    def _get_operation_summary(self, arguments: dict[str, object]) -> dict[str, object]:
        operation_id = self._operation_id(arguments)
        operation = OperationService(self._session).get(operation_id)
        optimization: dict[str, object] | None = None
        try:
            result = OptimizationResultService(self._session).latest_for_operation(operation_id)
        except OptimizationResultNotFoundError:
            result = None
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

    def _operation_id(self, arguments: dict[str, object]) -> uuid.UUID:
        raw = arguments.get("operation_id")
        try:
            operation_id = uuid.UUID(str(raw))
        except (ValueError, AttributeError) as exc:
            raise AssistantToolError("operation_id inválido.") from exc
        if (
            self._context_operation_id is not None
            and operation_id != self._context_operation_id
        ):
            raise AssistantToolPermissionError(
                "A tool tentou acessar uma operação diferente do contexto selecionado."
            )
        return operation_id
