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
    _current_user: CurrentUser,
) -> AssistantMessageResponse:
    settings = LLMSettings.from_env()
    try:
        provider = build_llm_provider(settings)
    except LLMProviderUnavailableError as exc:
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
        )
    except AssistantToolLimitError as exc:
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "LLM_TOOL_LIMIT_EXCEEDED",
            str(exc),
        ) from exc
    except AssistantInvalidResponseError as exc:
        raise ApiError(
            status.HTTP_502_BAD_GATEWAY,
            "LLM_INVALID_RESPONSE",
            "O Assistente IA retornou uma resposta inválida.",
        ) from exc
    except LookupError as exc:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "ASSISTANT_CONTEXT_NOT_FOUND",
            "O contexto operacional solicitado não foi encontrado.",
        ) from exc

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
