import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from fluxmed.api.errors import ApiError
from fluxmed.api.v1 import assistant as assistant_api
from fluxmed.api.v1.assistant import (
    AssistantContextRequest,
    AssistantMessageRequest,
)
from fluxmed.llm import (
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
)
from fluxmed.llm.config import LLMSettings
from fluxmed.llm.factory import LLMProviderUnavailableError


def _settings() -> LLMSettings:
    return LLMSettings(
        provider="gemini",
        model="gemini-3.5-flash-lite",
        timeout_seconds=5,
        max_tool_calls_per_request=5,
        max_output_chars=6000,
        thinking_level="minimal",
        max_context_chars=30000,
    )


def _payload() -> AssistantMessageRequest:
    return AssistantMessageRequest(
        message="Qual o custo total da operação?",
        context=AssistantContextRequest(operation_id=uuid.uuid4()),
    )


def _current_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


def _raise_from_service(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    class FailingAssistantService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def answer(self, *_args: object, **_kwargs: object) -> None:
            raise error

    monkeypatch.setattr(assistant_api, "AssistantService", FailingAssistantService)


def test_assistant_provider_configuration_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assistant_api.LLMSettings, "from_env", classmethod(lambda cls: _settings()))
    monkeypatch.setattr(
        assistant_api,
        "build_llm_provider",
        lambda _settings: (_ for _ in ()).throw(
            LLMProviderUnavailableError("GEMINI_API_KEY=super-secret")
        ),
    )
    monkeypatch.setattr(assistant_api, "_record_failure", lambda **_kwargs: None)

    with pytest.raises(ApiError) as captured:
        assistant_api.assistant_message(_payload(), Mock(), _current_user())

    error = captured.value
    assert error.status_code == 503
    assert error.code == "LLM_PROVIDER_UNAVAILABLE"
    assert "super-secret" not in error.message


@pytest.mark.parametrize(
    ("provider_error", "expected_status", "expected_code"),
    [
        (LLMProviderTimeoutError("secret timeout detail"), 504, "LLM_PROVIDER_TIMEOUT"),
        (
            LLMProviderRateLimitError("secret rate limit detail"),
            503,
            "LLM_PROVIDER_RATE_LIMITED",
        ),
        (
            LLMProviderResponseError("secret invalid response detail"),
            502,
            "LLM_INVALID_RESPONSE",
        ),
        (LLMProviderError("secret transport detail"), 503, "LLM_PROVIDER_UNAVAILABLE"),
    ],
)
def test_assistant_provider_failures_map_to_sanitized_api_errors(
    monkeypatch: pytest.MonkeyPatch,
    provider_error: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    monkeypatch.setattr(assistant_api.LLMSettings, "from_env", classmethod(lambda cls: _settings()))
    monkeypatch.setattr(
        assistant_api,
        "build_llm_provider",
        lambda _settings: SimpleNamespace(
            name="gemini",
            model="gemini-3.5-flash-lite",
        ),
    )
    _raise_from_service(monkeypatch, provider_error)
    monkeypatch.setattr(assistant_api, "_record_provider_failure", lambda *_args, **_kwargs: None)

    with pytest.raises(ApiError) as captured:
        assistant_api.assistant_message(_payload(), Mock(), _current_user())

    error = captured.value
    assert error.status_code == expected_status
    assert error.code == expected_code
    assert "secret" not in error.message


def test_assistant_rate_limit_blocks_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    monkeypatch.setattr(
        assistant_api.LLMSettings,
        "from_env",
        classmethod(lambda cls: settings),
    )
    monkeypatch.setattr(
        assistant_api.AssistantTelemetryRecorder,
        "count_since",
        staticmethod(lambda _user_id, _since: settings.rate_limit_requests),
    )
    provider_builder = Mock()
    monkeypatch.setattr(assistant_api, "build_llm_provider", provider_builder)

    with pytest.raises(ApiError) as captured:
        assistant_api.assistant_message(_payload(), Mock(), _current_user())

    error = captured.value
    assert error.status_code == 429
    assert error.code == "ASSISTANT_RATE_LIMITED"
    provider_builder.assert_not_called()


def test_assistant_rate_limit_fails_open_when_telemetry_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    monkeypatch.setattr(
        assistant_api.LLMSettings,
        "from_env",
        classmethod(lambda cls: settings),
    )
    monkeypatch.setattr(
        assistant_api.AssistantTelemetryRecorder,
        "count_since",
        staticmethod(lambda _user_id, _since: None),
    )
    monkeypatch.setattr(
        assistant_api,
        "build_llm_provider",
        lambda _settings: (_ for _ in ()).throw(
            LLMProviderUnavailableError("provider unavailable")
        ),
    )
    monkeypatch.setattr(assistant_api, "_record_failure", lambda **_kwargs: None)

    with pytest.raises(ApiError) as captured:
        assistant_api.assistant_message(_payload(), Mock(), _current_user())

    assert captured.value.code == "LLM_PROVIDER_UNAVAILABLE"
