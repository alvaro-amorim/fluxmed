import uuid
from unittest.mock import Mock

from fluxmed.application.assistant.tools import AssistantToolRegistry
from fluxmed.llm import ProviderRequest, ToolCall, ToolExchange, ToolResult
from fluxmed.llm.providers import MockLLMProvider


def test_mock_provider_selects_operation_summary_tool() -> None:
    operation_id = uuid.uuid4()
    provider = MockLLMProvider()

    turn = provider.generate(
        ProviderRequest(
            system_prompt="system",
            user_message="Qual o custo total da operação?",
            context={"operation_id": str(operation_id)},
            tools=(),
        )
    )

    assert turn.content == ""
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].name == "get_operation_summary"
    assert turn.tool_calls[0].arguments == {"operation_id": str(operation_id)}


def test_mock_provider_uses_tool_value_without_recalculating() -> None:
    operation_id = uuid.uuid4()
    call = ToolCall(
        id="call-1",
        name="get_operation_summary",
        arguments={"operation_id": str(operation_id)},
    )
    result = ToolResult(
        call_id="call-1",
        name="get_operation_summary",
        content={
            "operation": {"operation_code": "OP-20260915-001", "status": "OPTIMIZED"},
            "optimization": {"total_cost_brl": "400.38"},
        },
    )

    turn = MockLLMProvider().generate(
        ProviderRequest(
            system_prompt="system",
            user_message="Qual o custo total da operação?",
            context={"operation_id": str(operation_id)},
            tools=(),
            history=(ToolExchange(call=call, result=result),),
        )
    )

    assert turn.tool_calls == ()
    assert turn.content == "O custo total da OP-20260915-001 é R$ 400,38."


def test_mock_provider_requires_explicit_operation_context() -> None:
    turn = MockLLMProvider().generate(
        ProviderRequest(
            system_prompt="system",
            user_message="Qual o custo total?",
            context={},
            tools=(),
        )
    )

    assert "Selecione uma operação" in turn.content
    assert turn.tool_calls == ()


def test_tool_registry_blocks_cross_operation_access_before_query() -> None:
    selected_operation_id = uuid.uuid4()
    other_operation_id = uuid.uuid4()
    registry = AssistantToolRegistry(
        Mock(),
        context_operation_id=selected_operation_id,
    )

    result = registry.execute(
        ToolCall(
            id="call-1",
            name="get_operation_summary",
            arguments={"operation_id": str(other_operation_id)},
        )
    )

    assert result.success is False
    assert result.error is not None
    assert "diferente do contexto" in result.error
