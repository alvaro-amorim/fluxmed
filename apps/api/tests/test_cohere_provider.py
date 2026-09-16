import json

import httpx

from fluxmed.llm import ProviderRequest, ToolCall, ToolDefinition, ToolExchange, ToolResult
from fluxmed.llm.providers import CohereProvider


def test_cohere_provider_parses_strict_tool_call() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": [],
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "get_operation_summary",
                                "arguments": '{"operation_id":"operation-id"}',
                            },
                        }
                    ],
                },
                "usage": {"tokens": {"input_tokens": 20, "output_tokens": 8}},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = CohereProvider(
        api_key="test-key",
        model="command-a-plus-05-2026",
        timeout_seconds=1,
        client=client,
    )
    request = ProviderRequest(
        system_prompt="system",
        user_message="Qual o custo?",
        context={"operation_id": "operation-id"},
        tools=(
            ToolDefinition(
                name="get_operation_summary",
                description="Resumo",
                input_schema={
                    "type": "object",
                    "properties": {"operation_id": {"type": "string"}},
                    "required": ["operation_id"],
                },
            ),
        ),
    )

    turn = provider.generate(request)

    assert captured["strict_tools"] is True
    assert turn.content == ""
    assert turn.input_tokens == 20
    assert turn.output_tokens == 8
    assert turn.tool_calls == (
        ToolCall(
            id="call-1",
            name="get_operation_summary",
            arguments={"operation_id": "operation-id"},
        ),
    )


def test_cohere_provider_sends_tool_result_and_returns_text() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Custo total: R$ 400,38."}],
                    "tool_calls": [],
                },
                "usage": {"tokens": {"input_tokens": 42, "output_tokens": 11}},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = CohereProvider(
        api_key="test-key",
        model="command-a-plus-05-2026",
        timeout_seconds=1,
        client=client,
    )
    call = ToolCall(
        id="call-1",
        name="get_operation_summary",
        arguments={"operation_id": "operation-id"},
    )

    turn = provider.generate(
        ProviderRequest(
            system_prompt="system",
            user_message="Qual o custo?",
            context={"operation_id": "operation-id"},
            tools=(),
            history=(
                ToolExchange(
                    call=call,
                    result=ToolResult(
                        call_id="call-1",
                        name="get_operation_summary",
                        content={"optimization": {"total_cost_brl": "400.38"}},
                    ),
                ),
            ),
        )
    )

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert any(isinstance(message, dict) and message.get("role") == "tool" for message in messages)
    assert turn.content == "Custo total: R$ 400,38."
    assert turn.tool_calls == ()
