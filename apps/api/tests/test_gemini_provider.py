import json

import httpx

from fluxmed.llm import ProviderRequest, ToolDefinition, ToolExchange, ToolResult
from fluxmed.llm.contracts import ToolCall
from fluxmed.llm.providers import GeminiProvider


def test_gemini_provider_parses_function_call_and_uses_stateful_result() -> None:
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "id": "interaction-1",
                    "status": "requires_action",
                    "steps": [
                        {
                            "type": "function_call",
                            "id": "call-1",
                            "name": "get_operation_summary",
                            "arguments": {"operation_id": "operation-id"},
                        }
                    ],
                    "usage": {"total_input_tokens": 12, "total_output_tokens": 4},
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "interaction-2",
                "status": "completed",
                "steps": [
                    {
                        "type": "model_output",
                        "content": [{"type": "text", "text": "Custo total: R$ 400,38."}],
                    }
                ],
                "usage": {"total_input_tokens": 20, "total_output_tokens": 8},
            },
        )

    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.8-flash",
        timeout_seconds=1,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    tool = ToolDefinition(
        name="get_operation_summary",
        description="Resumo",
        input_schema={
            "type": "object",
            "properties": {"operation_id": {"type": "string"}},
            "required": ["operation_id"],
        },
    )
    first = provider.generate(
        ProviderRequest(
            system_prompt="system",
            user_message="Qual o custo?",
            context={"operation_id": "operation-id"},
            tools=(tool,),
        )
    )

    assert first.tool_calls == (
        ToolCall(
            id="call-1",
            name="get_operation_summary",
            arguments={"operation_id": "operation-id"},
        ),
    )
    assert requests[0]["system_instruction"] == "system"
    assert requests[0]["model"] == "gemini-3.8-flash"

    call = first.tool_calls[0]
    second = provider.generate(
        ProviderRequest(
            system_prompt="system",
            user_message="Qual o custo?",
            context={"operation_id": "operation-id"},
            tools=(tool,),
            history=(
                ToolExchange(
                    call=call,
                    result=ToolResult(
                        call_id=call.id,
                        name=call.name,
                        content={"optimization": {"total_cost_brl": "400.38"}},
                    ),
                ),
            ),
        )
    )

    assert requests[1]["previous_interaction_id"] == "interaction-1"
    result_input = requests[1]["input"]
    assert isinstance(result_input, list)
    assert result_input[0]["type"] == "function_result"
    assert result_input[0]["call_id"] == "call-1"
    assert second.content == "Custo total: R$ 400,38."
    assert second.tool_calls == ()
