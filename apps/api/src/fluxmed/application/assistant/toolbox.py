import uuid

from sqlalchemy.orm import Session

from fluxmed.application.assistant.narrative_tools import AssistantNarrativeToolset
from fluxmed.application.assistant.simulation_tools import AssistantSimulationToolset
from fluxmed.application.assistant.tools import AssistantToolRegistry
from fluxmed.llm import ToolCall, ToolDefinition, ToolResult


class AssistantToolbox:
    """Composes the approved read, narrative and what-if tools exposed to LLM providers."""

    def __init__(self, session: Session, *, context_operation_id: uuid.UUID | None) -> None:
        self._read = AssistantToolRegistry(
            session,
            context_operation_id=context_operation_id,
        )
        self._narrative = AssistantNarrativeToolset(
            session,
            context_operation_id=context_operation_id,
        )
        self._simulation = AssistantSimulationToolset(
            session,
            context_operation_id=context_operation_id,
        )

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return (
            *self._read.definitions(),
            *self._narrative.definitions(),
            *self._simulation.definitions(),
        )

    def execute(self, call: ToolCall) -> ToolResult:
        if call.name in AssistantNarrativeToolset.NAMES:
            return self._narrative.execute(call)
        if call.name in AssistantSimulationToolset.NAMES:
            return self._simulation.execute(call)
        return self._read.execute(call)
