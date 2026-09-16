from dataclasses import dataclass, field

from fluxmed.llm import ProviderRequest
from fluxmed.llm.providers import GeminiProvider


@dataclass
class _FakeUsage:
    total_input_tokens: int = 21
    total_output_tokens: int = 9


@dataclass
class _FakeInteraction:
    output_text: str = "O custo total da operação é R$ 400,38."
    usage: _FakeUsage = field(default_factory=_FakeUsage)


class _FakeInteractions:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.requests.append(dict(kwargs))
        return _FakeInteraction()


class _FakeClient:
    def __init__(self) -> None:
        self._interactions = _FakeInteractions()
        self.closed = False

    @property
    def interactions(self) -> _FakeInteractions:
        return self._interactions

    def close(self) -> None:
        self.closed = True


def test_gemini_provider_generates_once_from_grounded_context() -> None:
    client = _FakeClient()
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        timeout_seconds=20,
        client=client,
    )
    request = ProviderRequest(
        system_prompt="system",
        user_message="Qual o custo total da operação?",
        context={
            "scope": {"operation_id": "operation-id"},
            "grounding": [
                {
                    "tool": "get_cost_breakdown",
                    "status": "success",
                    "data": {"total_cost_brl": "400.38"},
                }
            ],
        },
        tools=(),
    )

    turn = provider.generate(request)

    assert turn.content == "O custo total da operação é R$ 400,38."
    assert turn.tool_calls == ()
    assert turn.input_tokens == 21
    assert turn.output_tokens == 9
    assert len(client.interactions.requests) == 1
    sent = client.interactions.requests[0]
    assert sent["model"] == "gemini-2.5-flash"
    assert sent["input"] == "Qual o custo total da operação?"
    assert sent["timeout"] == 20
    assert sent["store"] is False
    assert sent["generation_config"] == {
        "thinking_level": "low",
        "max_output_tokens": 4096,
    }
    assert "tools" not in sent
    system_instruction = sent["system_instruction"]
    assert isinstance(system_instruction, str)
    assert "backend já executou as consultas autorizadas" in system_instruction
    assert '"total_cost_brl":"400.38"' in system_instruction
    assert client.closed is False


def test_gemini_provider_keeps_empty_context_out_of_system_instruction() -> None:
    request = ProviderRequest(
        system_prompt="system",
        user_message="Olá",
        context={},
        tools=(),
    )

    assert GeminiProvider._system_instruction(request) == "system"
