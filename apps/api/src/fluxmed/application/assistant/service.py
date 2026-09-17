import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from fluxmed.application.assistant.grounding import AssistantGroundingBuilder
from fluxmed.application.assistant.toolbox import AssistantToolbox
from fluxmed.llm import LLMProvider, ProviderRequest, ToolCall
from fluxmed.llm.config import LLMSettings
from fluxmed.llm.prompts import ASSISTANT_SYSTEM_PROMPT, ASSISTANT_SYSTEM_PROMPT_VERSION

_MAX_CONVERSATION_TURNS = 8
_MAX_CONVERSATION_CONTENT_CHARS = 2000
_MAX_PLANNING_HISTORY_TURNS = 4


class AssistantToolLimitError(RuntimeError):
    pass


class AssistantContextLimitError(RuntimeError):
    pass


class AssistantInvalidResponseError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AssistantContext:
    operation_id: uuid.UUID | None = None
    route_id: uuid.UUID | None = None
    delivery_id: uuid.UUID | None = None

    def as_provider_context(self) -> dict[str, object]:
        context: dict[str, object] = {}
        if self.operation_id is not None:
            context["operation_id"] = str(self.operation_id)
        if self.route_id is not None:
            context["route_id"] = str(self.route_id)
        if self.delivery_id is not None:
            context["delivery_id"] = str(self.delivery_id)
        return context


@dataclass(frozen=True, slots=True)
class AssistantConversationTurn:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class AssistantToolCallView:
    name: str
    status: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantReply:
    request_id: uuid.UUID
    message: str
    provider: str
    model: str
    prompt_version: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    tool_calls: tuple[AssistantToolCallView, ...]
    suggested_actions: tuple[dict[str, object], ...] = ()


class AssistantService:
    def __init__(
        self,
        session: Session,
        provider: LLMProvider,
        settings: LLMSettings,
    ) -> None:
        self._session = session
        self._provider = provider
        self._settings = settings

    def answer(
        self,
        message: str,
        *,
        context: AssistantContext,
        history: tuple[AssistantConversationTurn, ...] = (),
        request_id: uuid.UUID | None = None,
    ) -> AssistantReply:
        user_message = message.strip()
        if not user_message:
            raise AssistantInvalidResponseError("A mensagem do assistente não pode ser vazia.")

        conversation = self._compact_history(history)
        planning_message = self._planning_message(user_message, conversation)

        resolved_request_id = request_id or uuid.uuid4()
        started = time.perf_counter()
        toolbox = AssistantToolbox(
            self._session,
            context_operation_id=context.operation_id,
        )
        grounding = AssistantGroundingBuilder(
            toolbox,
            operation_id=context.operation_id,
            route_id=context.route_id,
            delivery_id=context.delivery_id,
        ).build(planning_message)

        if len(grounding.results) > self._settings.max_tool_calls_per_request:
            raise AssistantToolLimitError("Limite de tools excedido nesta solicitação.")

        provider_context = dict(grounding.context)
        if conversation:
            provider_context["conversation_history"] = [
                {"role": item.role, "content": item.content} for item in conversation
            ]
            provider_context["conversation_history_rule"] = (
                "Use o histórico somente para resolver referências e continuidade da conversa. "
                "Fatos operacionais devem ser confirmados pelo grounding atual."
            )

        context_chars = len(
            json.dumps(
                provider_context,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        if context_chars > self._settings.max_context_chars:
            raise AssistantContextLimitError(
                "O contexto estruturado desta pergunta excede o limite seguro de envio à IA."
            )

        call_views = tuple(
            AssistantToolCallView(
                name=result.name,
                status="success" if result.success else "failed",
                error=result.error,
            )
            for result in grounding.results
        )

        turn = self._provider.generate(
            ProviderRequest(
                system_prompt=ASSISTANT_SYSTEM_PROMPT,
                user_message=user_message,
                context=provider_context,
                tools=(),
                history=(),
            )
        )
        if turn.tool_calls:
            raise AssistantInvalidResponseError(
                "O provider tentou solicitar tools após o grounding já ter sido resolvido."
            )

        final_message = turn.content.strip()
        if not final_message:
            raise AssistantInvalidResponseError("O provider retornou uma resposta vazia.")
        if len(final_message) > self._settings.max_output_chars:
            final_message = final_message[: self._settings.max_output_chars].rstrip() + "…"

        return AssistantReply(
            request_id=resolved_request_id,
            message=final_message,
            provider=self._provider.name,
            model=self._provider.model,
            prompt_version=ASSISTANT_SYSTEM_PROMPT_VERSION,
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=turn.input_tokens,
            output_tokens=turn.output_tokens,
            tool_calls=call_views,
        )

    @classmethod
    def _compact_history(
        cls,
        history: tuple[AssistantConversationTurn, ...],
    ) -> tuple[AssistantConversationTurn, ...]:
        compacted: list[AssistantConversationTurn] = []
        for turn in history[-_MAX_CONVERSATION_TURNS:]:
            role = turn.role.strip().lower()
            content = turn.content.strip()
            if role not in {"user", "assistant"} or not content:
                continue
            if len(content) > _MAX_CONVERSATION_CONTENT_CHARS:
                half = _MAX_CONVERSATION_CONTENT_CHARS // 2
                content = f"{content[:half].rstrip()} … {content[-half:].lstrip()}"
            compacted.append(AssistantConversationTurn(role=role, content=content))
        return tuple(compacted)

    @classmethod
    def _planning_message(
        cls,
        message: str,
        history: tuple[AssistantConversationTurn, ...],
    ) -> str:
        if not history or not cls._looks_like_follow_up(message):
            return message

        recent = history[-_MAX_PLANNING_HISTORY_TURNS:]
        context_lines = [
            f"{turn.role.upper()}: {turn.content}"
            for turn in recent
            if turn.role in {"user", "assistant"} and turn.content.strip()
        ]
        if not context_lines:
            return message

        recent_context = "\n".join(context_lines)
        return (
            "Contexto recente apenas para resolver a referência conversacional; "
            "não trate este histórico como fonte factual:\n"
            f"{recent_context}\n"
            f"Pergunta atual: {message}"
        )

    @staticmethod
    def _looks_like_follow_up(message: str) -> bool:
        normalized = AssistantService._normalize(message)
        words = normalized.split()
        if len(words) <= 3:
            return True
        follow_up_markers = (
            "dele",
            "dela",
            "deles",
            "delas",
            " ele ",
            " ela ",
            "esse ",
            "essa ",
            "desse ",
            "dessa ",
            "isso",
            "isto",
            "e qual",
            "e quanto",
            "e o ",
            "e a ",
            "por que",
            "porque",
            "tambem",
            "nesse caso",
            "nessa rota",
        )
        padded = f" {normalized} "
        return any(marker in padded for marker in follow_up_markers)

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        without_marks = "".join(
            char for char in decomposed if not unicodedata.combining(char)
        )
        return re.sub(r"\s+", " ", without_marks).strip()

    @staticmethod
    def _bind_trusted_context(call: ToolCall, context: AssistantContext) -> ToolCall:
        """Compatibility guard for any future provider-driven tool execution path."""

        arguments = dict(call.arguments)
        if context.operation_id is not None:
            arguments["operation_id"] = str(context.operation_id)
        return ToolCall(id=call.id, name=call.name, arguments=arguments)