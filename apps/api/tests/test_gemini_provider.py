import logging
from dataclasses import dataclass, field

import pytest
from google.genai import types

from fluxmed.llm import (
    LLMProviderRateLimitError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    ProviderRequest,
    ToolDefinition,
)
from fluxmed.llm.providers import GeminiProvider


@dataclass
class _FakeInteractionUsage:
    total_input_tokens: int = 21
    total_output_tokens: int = 9


@dataclass
class _FakeGenerateUsage:
    prompt_token_count: int = 21
    candidates_token_count: int = 9


@dataclass
class _FakeFunctionCallStep:
    id: str = "call-1"
    name: str = "select_assistant_context"
    arguments: dict[str, object] = field(default_factory=lambda: {"tools": ["get_cost_breakdown"]})
    type: str = "function_call"


@dataclass
class _FakeInteraction:
    output_text: str = ""
    usage: _FakeInteractionUsage = field(default_factory=_FakeInteractionUsage)
    steps: list[object] = field(default_factory=list)


@dataclass
class _FakeGenerateResponse:
    text: str = "O custo total da operação é R$ 400,38."
    usage_metadata: _FakeGenerateUsage = field(default_factory=_FakeGenerateUsage)


class _FakeInteractions:
    def __init__(self, interaction: object | None = None, error: Exception | None = None) -> None:
        self.requests: list[dict[str, object]] = []
        self._interaction = interaction or _FakeInteraction()
        self._error = error

    def create(self, **kwargs: object) -> object:
        self.requests.append(dict(kwargs))
        if self._error is not None:
            raise self._error
        return self._interaction


class _FakeModels:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.requests: list[dict[str, object]] = []
        self._response = response or _FakeGenerateResponse()
        self._error = error

    def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: object | None = None,
    ) -> object:
        self.requests.append({"model": model, "contents": contents, "config": config})
        if self._error is not None:
            raise self._error
        return self._response


class _FakeClient:
    def __init__(
        self,
        *,
        interaction: object | None = None,
        response: object | None = None,
        interaction_error: Exception | None = None,
        model_error: Exception | None = None,
    ) -> None:
        self._interactions = _FakeInteractions(interaction, interaction_error)
        self._models = _FakeModels(response, model_error)
        self.closed = False

    @property
    def interactions(self) -> _FakeInteractions:
        return self._interactions

    @property
    def models(self) -> _FakeModels:
        return self._models

    def close(self) -> None:
        self.closed = True


class BadRequestError(Exception):
    status_code = 400
    message = "invalid request"


class RateLimitError(Exception):
    status_code = 429
    message = "quota exceeded; Please retry in 8.5s"


class APITimeoutError(Exception):
    message = "Request timed out"


def _request() -> ProviderRequest:
    return ProviderRequest(
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


def test_gemini_provider_uses_generate_content_for_grounded_reply() -> None:
    client = _FakeClient()
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
        thinking_level="minimal",
        client=client,
    )

    turn = provider.generate(_request())

    assert turn.content == "O custo total da operação é R$ 400,38."
    assert turn.tool_calls == ()
    assert turn.input_tokens == 21
    assert turn.output_tokens == 9
    assert len(client.models.requests) == 1
    assert client.interactions.requests == []
    sent = client.models.requests[0]
    assert sent["model"] == "gemini-3.5-flash-lite"
    assert sent["contents"] == "Qual o custo total da operação?"
    config = sent["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.max_output_tokens == 2048
    assert config.system_instruction is not None
    assert "backend já executou as consultas autorizadas" in str(config.system_instruction)
    assert '"total_cost_brl":"400.38"' in str(config.system_instruction)
    assert config.http_options is not None
    assert config.http_options.timeout == 20000
    assert config.http_options.retry_options is not None
    assert config.http_options.retry_options.attempts == 1
    assert client.closed is False


def test_gemini_provider_logs_only_safe_latency_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="fluxmed.llm.providers.gemini")
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
        thinking_level="minimal",
        client=_FakeClient(),
    )

    provider.generate(_request())

    assert "gemini_request_started" in caplog.text
    assert "gemini_request_completed" in caplog.text
    assert "api=generate_content" in caplog.text
    assert "system_chars=" in caplog.text
    assert "user_chars=" in caplog.text
    assert "elapsed_ms=" in caplog.text
    assert "test-key" not in caplog.text
    assert "Qual o custo total da operação?" not in caplog.text
    assert "400.38" not in caplog.text


def test_gemini_provider_exposes_function_tools_and_parses_selection_call() -> None:
    interaction = _FakeInteraction(
        output_text="",
        steps=[_FakeFunctionCallStep()],
    )
    client = _FakeClient(interaction=interaction)
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
        thinking_level="minimal",
        client=client,
    )
    selector = ToolDefinition(
        name="select_assistant_context",
        description="Seleciona fontes read-only.",
        input_schema={
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["get_cost_breakdown"]},
                }
            },
            "required": ["tools"],
        },
    )
    request = ProviderRequest(
        system_prompt="semantic planner",
        user_message="Onde parece estar o maior desperdício?",
        context={"scope": {"operation_id": "operation-id"}},
        tools=(selector,),
    )

    turn = provider.generate(request)

    assert turn.content == ""
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].name == "select_assistant_context"
    assert turn.tool_calls[0].arguments == {"tools": ["get_cost_breakdown"]}
    assert client.models.requests == []
    sent = client.interactions.requests[0]
    assert sent["tools"] == [
        {
            "type": "function",
            "name": "select_assistant_context",
            "description": "Seleciona fontes read-only.",
            "parameters": selector.input_schema,
        }
    ]
    assert sent["generation_config"] == {
        "thinking_level": "minimal",
        "max_output_tokens": 1024,
        "tool_choice": {
            "allowed_tools": {
                "mode": "any",
                "tools": ["select_assistant_context"],
            }
        },
    }
    system_instruction = sent["system_instruction"]
    assert isinstance(system_instruction, str)
    assert "Contexto confiável desta etapa de planejamento" in system_instruction


def test_gemini_provider_maps_generate_content_bad_request() -> None:
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        timeout_seconds=20,
        client=_FakeClient(model_error=BadRequestError()),
    )

    with pytest.raises(LLMProviderResponseError, match="HTTP 400"):
        provider.generate(_request())


def test_gemini_provider_maps_sdk_timeout() -> None:
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        timeout_seconds=20,
        client=_FakeClient(model_error=APITimeoutError()),
    )

    with pytest.raises(LLMProviderTimeoutError):
        provider.generate(_request())


def test_gemini_provider_maps_rate_limit_and_opens_local_cooldown() -> None:
    client = _FakeClient(model_error=RateLimitError())
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        timeout_seconds=20,
        client=client,
    )

    with pytest.raises(LLMProviderRateLimitError):
        provider.generate(_request())
    assert provider.cooldown_remaining_seconds > 0
    assert len(client.models.requests) == 1

    with pytest.raises(LLMProviderRateLimitError, match="cooldown"):
        provider.generate(_request())
    assert len(client.models.requests) == 1


def test_gemini_provider_builds_v1beta_client_with_single_attempt_retry_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    fake_client = _FakeClient()

    def fake_sdk_client(**kwargs: object) -> _FakeClient:
        captured.update(kwargs)
        return fake_client

    monkeypatch.setattr("fluxmed.llm.providers.gemini.genai.Client", fake_sdk_client)
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
        thinking_level="minimal",
    )

    built = provider._build_client()

    assert built is fake_client
    http_options = captured["http_options"]
    assert isinstance(http_options, types.HttpOptions)
    assert http_options.api_version == "v1beta"
    retry_options = http_options.retry_options
    assert retry_options is not None
    assert retry_options.attempts == 1
    status_codes = retry_options.http_status_codes or []
    assert 429 not in status_codes


def test_gemini_provider_keeps_empty_context_out_of_system_instruction() -> None:
    request = ProviderRequest(
        system_prompt="system",
        user_message="Olá",
        context={},
        tools=(),
    )

    assert GeminiProvider._system_instruction(request) == "system"
