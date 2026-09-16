import time
import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.application.assistant import (
    AssistantContext,
    AssistantInvalidResponseError,
    AssistantService,
    AssistantToolLimitError,
)
from fluxmed.application.assistant.telemetry import (
    AssistantTelemetryInput,
    AssistantTelemetryRecorder,
)
from fluxmed.llm import (
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
)
from fluxmed.llm.config import LLMSettings
from fluxmed.llm.factory import LLMProviderUnavailableError, build_llm_provider

router = APIRouter(tags=["assistant"])


class AssistantContextRequest(BaseModel):
    operation_id: uuid.UUID | None = None
    route_id: uuid.UUID | None = None
    delivery_id: uuid.UUID | None = None


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    context: AssistantContextRequest = Field(default_factory=AssistantContextRequest)


class AssistantToolCallResponse(BaseModel):
    name: str
    status: str
    error: str | None = None


class AssistantMessageResponse(BaseModel):
    request_id: uuid.UUID
    message: str
    provider: str
    model: str
    prompt_version: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    tool_calls: list[AssistantToolCallResponse]
    suggested_actions: list[dict[str, object]]


class AssistantStatusResponse(BaseModel):
    status: str
    provider: str
    model: str


@router.get("/assistant/status", response_model=AssistantStatusResponse)
def assistant_status(_current_user: CurrentUser) -> AssistantStatusResponse:
    settings = LLMSettings.from_env()
    try:
        provider = build_llm_provider(settings)
    except LLMProviderUnavailableError:
        return AssistantStatusResponse(
            status="DEGRADED",
            provider=settings.provider,
            model=settings.model,
        )
    return AssistantStatusResponse(
        status="HEALTHY",
        provider=provider.name,
        model=provider.model,
    )


@router.post("/assistant/messages", response_model=AssistantMessageResponse)
def assistant_message(
    payload: AssistantMessageRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> AssistantMessageResponse:
    request_id = uuid.uuid4()
    started = time.perf_counter()
    settings = LLMSettings.from_env()
    try:
        provider = build_llm_provider(settings)
    except LLMProviderUnavailableError as exc:
        _record_failure(
            request_id=request_id,
            user_id=current_user.id,
            operation_id=payload.context.operation_id,
            provider=settings.provider,
            model=settings.model,
            started=started,
            error_code="LLM_PROVIDER_UNAVAILABLE",
        )
        raise ApiError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_PROVIDER_UNAVAILABLE",
            "Assistente IA temporariamente indisponível.",
        ) from exc

    service = AssistantService(session, provider, settings)
    try:
        reply = service.answer(
            payload.message,
            context=AssistantContext(
                operation_id=payload.context.operation_id,
                route_id=payload.context.route_id,
                delivery_id=payload.context.delivery_id,
            ),
            request_id=request_id,
        )
    except LLMProviderTimeoutError as exc:
        _record_provider_failure(
            request_id, current_user.id, payload, provider.name, provider.model, started,
            "LLM_PROVIDER_TIMEOUT",
        )
        raise ApiError(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "LLM_PROVIDER_TIMEOUT",
            "O provider de IA excedeu o tempo limite.",
        ) from exc
    except LLMProviderRateLimitError as exc:
        _record_provider_failure(
            request_id, current_user.id, payload, provider.name, provider.model, started,
            "LLM_PROVIDER_RATE_LIMITED",
        )
        raise ApiError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_PROVIDER_RATE_LIMITED",
            "O provider de IA está temporariamente limitado.",
        ) from exc
    except LLMProviderResponseError as exc:
        _record_provider_failure(
            request_id, current_user.id, payload, provider.name, provider.model, started,
            "LLM_INVALID_RESPONSE",
        )
        raise ApiError(
            status.HTTP_502_BAD_GATEWAY,
            "LLM_INVALID_RESPONSE",
            "O provider de IA retornou uma resposta inválida.",
        ) from exc
    except LLMProviderError as exc:
        _record_provider_failure(
            request_id, current_user.id, payload, provider.name, provider.model, started,
            "LLM_PROVIDER_UNAVAILABLE",
        )
        raise ApiError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_PROVIDER_UNAVAILABLE",
            "Assistente IA temporariamente indisponível.",
        ) from exc
    except AssistantToolLimitError as exc:
        _record_provider_failure(
            request_id, current_user.id, payload, provider.name, provider.model, started,
            "LLM_TOOL_LIMIT_EXCEEDED",
        )
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "LLM_TOOL_LIMIT_EXCEEDED",
            str(exc),
        ) from exc
    except AssistantInvalidResponseError as exc:
        _record_provider_failure(
            request_id, current_user.id, payload, provider.name, provider.model, started,
            "LLM_INVALID_RESPONSE",
        )
        raise ApiError(
            status.HTTP_502_BAD_GATEWAY,
            "LLM_INVALID_RESPONSE",
            "O Assistente IA retornou uma resposta inválida.",
        ) from exc
    except LookupError as exc:
        _record_provider_failure(
            request_id, current_user.id, payload, provider.name, provider.model, started,
            "ASSISTANT_CONTEXT_NOT_FOUND",
        )
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "ASSISTANT_CONTEXT_NOT_FOUND",
            "O contexto operacional solicitado não foi encontrado.",
        ) from exc

    telemetry_calls = tuple(
        {"name": item.name, "status": item.status}
        for item in reply.tool_calls
    )
    AssistantTelemetryRecorder.record(
        AssistantTelemetryInput(
            request_id=reply.request_id,
            user_id=current_user.id,
            operation_id=payload.context.operation_id,
            provider=reply.provider,
            model=reply.model,
            latency_ms=reply.latency_ms,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            tool_calls=telemetry_calls,
            tool_failures=sum(1 for item in reply.tool_calls if item.status == "failed"),
            status="SUCCESS",
        )
    )

    return AssistantMessageResponse(
        request_id=reply.request_id,
        message=reply.message,
        provider=reply.provider,
        model=reply.model,
        prompt_version=reply.prompt_version,
        latency_ms=reply.latency_ms,
        input_tokens=reply.input_tokens,
        output_tokens=reply.output_tokens,
        tool_calls=[
            AssistantToolCallResponse(name=item.name, status=item.status, error=item.error)
            for item in reply.tool_calls
        ],
        suggested_actions=list(reply.suggested_actions),
    )


def _record_provider_failure(
    request_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: AssistantMessageRequest,
    provider: str,
    model: str,
    started: float,
    error_code: str,
) -> None:
    _record_failure(
        request_id=request_id,
        user_id=user_id,
        operation_id=payload.context.operation_id,
        provider=provider,
        model=model,
        started=started,
        error_code=error_code,
    )


def _record_failure(
    *,
    request_id: uuid.UUID,
    user_id: uuid.UUID,
    operation_id: uuid.UUID | None,
    provider: str,
    model: str,
    started: float,
    error_code: str,
) -> None:
    AssistantTelemetryRecorder.record(
        AssistantTelemetryInput(
            request_id=request_id,
            user_id=user_id,
            operation_id=operation_id,
            provider=provider,
            model=model or "unconfigured",
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=0,
            output_tokens=0,
            tool_calls=(),
            tool_failures=0,
            status="FAILED",
            error_code=error_code,
        )
    )
