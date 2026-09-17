from dataclasses import dataclass, field

import pytest
from google.genai import types

from fluxmed.llm import (
    LLMProviderRateLimitError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    ProviderRequest,
)
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


class _FailingInteractions:
    def __init__(self, error: Exception) -> None:
        self._error = error
        self.calls = 0

    def create(self, **_kwargs: object) -> object:
        self.calls += 1
        raise self._error


class _FailingClient:
    def __init__(self, error: Exception) -> None:
        self._interactions = _FailingInteractions(error)

    @property
    def interactions(self) -> _FailingInteractions:
        return self._interactions

    def close(self) -> None:
        return None


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


def test_gemini_provider_generates_once_from_grounded_context() -> None:
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
    assert len(client.interactions.requests) == 1
    sent = client.interactions.requests[0]
    assert sent["model"] == "gemini-3.5-flash-lite"
    assert sent["input"] == "Qual o custo total da operação?"
    assert sent["timeout"] == 20
    assert sent["store"] is False
    assert sent["generation_config"] == {
        "thinking_level": "minimal",
        "max_output_tokens": 4096,
    }
    assert "tools" not in sent
    system_instruction = sent["system_instruction"]
    assert isinstance(system_instruction, str)
    assert "backend já executou as consultas autorizadas" in system_instruction
    assert '"total_cost_brl":"400.38"' in system_instruction
    assert client.closed is False


def test_gemini_provider_maps_interactions_bad_request() -> None:
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        timeout_seconds=20,
        client=_FailingClient(BadRequestError()),
    )

    with pytest.raises(LLMProviderResponseError, match="HTTP 400"):
        provider.generate(_request())


def test_gemini_provider_maps_sdk_timeout() -> None:
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        timeout_seconds=20,
        client=_FailingClient(APITimeoutError()),
    )

    with pytest.raises(LLMProviderTimeoutError):
        provider.generate(_request())


def test_gemini_provider_maps_rate_limit_and_opens_local_cooldown() -> None:
    client = _FailingClient(RateLimitError())
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        timeout_seconds=20,
        client=client,
    )

    with pytest.raises(LLMProviderRateLimitError):
        provider.generate(_request())
    assert provider.cooldown_remaining_seconds > 0
    assert client.interactions.calls == 1

    with pytest.raises(LLMProviderRateLimitError, match="cooldown"):
        provider.generate(_request())
    assert client.interactions.calls == 1


def test_gemini_provider_builds_v1beta_client_without_retrying_429(
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
