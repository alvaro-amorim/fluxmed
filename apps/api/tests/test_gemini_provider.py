import logging
from dataclasses import dataclass, field

import httpx
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


class _FakeClient:
    def __init__(
        self,
        *,
        interaction: object | None = None,
        interaction_error: Exception | None = None,
    ) -> None:
        self._interactions = _FakeInteractions(interaction, interaction_error)
        self.closed = False

    @property
    def interactions(self) -> _FakeInteractions:
        return self._interactions

    def close(self) -> None:
        self.closed = True


class _FakeHttpResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else _success_payload()
        self.headers = httpx.Headers(headers or {})

    def json(self) -> object:
        return self._payload


def _success_payload() -> dict[str, object]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "O custo total da operação é R$ 400,38."},
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 21,
            "candidatesTokenCount": 9,
        },
    }


def _install_http_post(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: _FakeHttpResponse | None = None,
    error: Exception | None = None,
) -> list[dict[str, object]]:
    requests: list[dict[str, object]] = []

    def fake_post(url: str, **kwargs: object) -> _FakeHttpResponse:
        requests.append({"url": url, **kwargs})
        if error is not None:
            raise error
        return response or _FakeHttpResponse()

    monkeypatch.setattr("fluxmed.llm.providers.gemini.httpx.post", fake_post)
    return requests


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


def test_gemini_provider_uses_direct_rest_for_grounded_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = _install_http_post(monkeypatch)
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
        thinking_level="minimal",
    )

    turn = provider.generate(_request())

    assert turn.content == "O custo total da operação é R$ 400,38."
    assert turn.tool_calls == ()
    assert turn.input_tokens == 21
    assert turn.output_tokens == 9
    assert len(requests) == 1
    sent = requests[0]
    assert sent["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.5-flash-lite:generateContent"
    )
    headers = sent["headers"]
    assert isinstance(headers, dict)
    assert headers["x-goog-api-key"] == "test-key"
    payload = sent["json"]
    assert isinstance(payload, dict)
    assert payload["generationConfig"] == {
        "maxOutputTokens": 2048,
        "thinkingConfig": {"thinkingLevel": "minimal"},
    }
    system_instruction = payload["systemInstruction"]
    assert isinstance(system_instruction, dict)
    assert "backend já executou as consultas autorizadas" in str(system_instruction)
    assert '"total_cost_brl":"400.38"' in str(system_instruction)
    timeout = sent["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.read == 20


def test_gemini_provider_logs_only_safe_latency_metadata(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_http_post(monkeypatch)
    caplog.set_level(logging.INFO, logger="fluxmed.llm.providers.gemini")
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
        thinking_level="minimal",
    )

    provider.generate(_request())

    assert "gemini_request_started" in caplog.text
    assert "gemini_request_completed" in caplog.text
    assert "api=rest_generate_content" in caplog.text
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


def test_gemini_provider_maps_rest_bad_request(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_post(monkeypatch, response=_FakeHttpResponse(status_code=400))
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
    )

    with pytest.raises(LLMProviderResponseError, match="HTTP 400"):
        provider.generate(_request())


def test_gemini_provider_maps_rest_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_post(monkeypatch, error=httpx.ReadTimeout("timed out"))
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
    )

    with pytest.raises(LLMProviderTimeoutError):
        provider.generate(_request())


def test_gemini_provider_maps_rest_rate_limit_and_opens_local_cooldown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = _install_http_post(
        monkeypatch,
        response=_FakeHttpResponse(
            status_code=429,
            headers={"retry-after": "8.5"},
        ),
    )
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.5-flash-lite",
        timeout_seconds=20,
    )

    with pytest.raises(LLMProviderRateLimitError):
        provider.generate(_request())
    assert provider.cooldown_remaining_seconds > 0
    assert len(requests) == 1

    with pytest.raises(LLMProviderRateLimitError, match="cooldown"):
        provider.generate(_request())
    assert len(requests) == 1


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
