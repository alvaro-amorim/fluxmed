from dataclasses import dataclass
from typing import Protocol

JsonObject = dict[str, object]


class LLMProviderError(RuntimeError):
    pass


class LLMProviderTimeoutError(LLMProviderError):
    pass


class LLMProviderRateLimitError(LLMProviderError):
    pass


class LLMProviderResponseError(LLMProviderError):
    pass


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: JsonObject


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: JsonObject


@dataclass(frozen=True, slots=True)
class ToolResult:
    call_id: str
    name: str
    content: JsonObject
    success: bool = True
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ToolExchange:
    call: ToolCall
    result: ToolResult


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    system_prompt: str
    user_message: str
    context: JsonObject
    tools: tuple[ToolDefinition, ...]
    history: tuple[ToolExchange, ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderTurn:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def generate(self, request: ProviderRequest) -> ProviderTurn: ...
