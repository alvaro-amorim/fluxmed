import json
from collections.abc import Mapping

import httpx

from fluxmed.llm import (
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    ProviderRequest,
    ProviderTurn,
    ToolCall,
    ToolDefinition,
)

GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


class GeminiProvider:
    """Gemini Interactions API adapter with provider-side state for one assistant request."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("GEMINI_API_KEY ausente.")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._previous_interaction_id: str | None = None
        self._sent_tool_results = 0

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, request: ProviderRequest) -> ProviderTurn:
        payload: dict[str, object] = {
            "model": self._model,
            "system_instruction": request.system_prompt,
            "tools": [self._tool(tool) for tool in request.tools],
            "generation_config": self._generation_config(request.tools),
        }
        if self._previous_interaction_id is None:
            payload["input"] = request.user_message
        else:
            payload["previous_interaction_id"] = self._previous_interaction_id
            payload["input"] = [
                self._function_result(exchange.call.id, exchange.call.name, exchange.result.content)
                for exchange in request.history[self._sent_tool_results :]
            ]

        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                response = self._client.post(GEMINI_INTERACTIONS_URL, headers=headers, json=payload)
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(GEMINI_INTERACTIONS_URL, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMProviderTimeoutError("Gemini excedeu o tempo limite.") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError("Falha de comunicação com Gemini.") from exc

        if response.status_code == 429:
            raise LLMProviderRateLimitError("Gemini limitou temporariamente as requisições.")
        if response.status_code >= 400:
            raise LLMProviderError(f"Gemini retornou HTTP {response.status_code}.")

        try:
            data = response.json()
            if not isinstance(data, dict):
                raise TypeError("Resposta Gemini não é um objeto JSON.")
            interaction_id = data.get("id")
            if not isinstance(interaction_id, str):
                raise TypeError("Resposta Gemini sem interaction id.")
            self._previous_interaction_id = interaction_id
            self._sent_tool_results = len(request.history)
            return self._turn(data)
        except (ValueError, TypeError, KeyError) as exc:
            raise LLMProviderResponseError("Resposta Gemini inválida.") from exc

    @staticmethod
    def _tool(tool: ToolDefinition) -> dict[str, object]:
        return {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        }

    @staticmethod
    def _generation_config(tools: tuple[ToolDefinition, ...]) -> dict[str, object]:
        config: dict[str, object] = {
            "temperature": 0,
            "thinking_level": "low",
            "max_output_tokens": 1200,
        }
        if tools:
            config["tool_choice"] = {
                "allowed_tools": {
                    "mode": "validated",
                    "tools": [tool.name for tool in tools],
                }
            }
        return config

    @staticmethod
    def _function_result(
        call_id: str,
        name: str,
        content: dict[str, object],
    ) -> dict[str, object]:
        return {
            "type": "function_result",
            "name": name,
            "call_id": call_id,
            "result": [
                {
                    "type": "text",
                    "text": json.dumps(content, ensure_ascii=False, separators=(",", ":")),
                }
            ],
        }

    @staticmethod
    def _turn(data: Mapping[str, object]) -> ProviderTurn:
        status = data.get("status")
        if status == "failed":
            raise LLMProviderResponseError("Gemini marcou a interação como failed.")

        texts: list[str] = []
        calls: list[ToolCall] = []
        steps = data.get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, Mapping):
                    continue
                step_type = step.get("type")
                if step_type == "function_call":
                    call_id = step.get("id")
                    name = step.get("name")
                    arguments = step.get("arguments", {})
                    if (
                        isinstance(call_id, str)
                        and isinstance(name, str)
                        and isinstance(arguments, dict)
                    ):
                        calls.append(
                            ToolCall(
                                id=call_id,
                                name=name,
                                arguments={str(key): value for key, value in arguments.items()},
                            )
                        )
                elif step_type == "model_output":
                    content = step.get("content", [])
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, Mapping) and part.get("type") == "text":
                                text = part.get("text")
                                if isinstance(text, str):
                                    texts.append(text)

        input_tokens = 0
        output_tokens = 0
        usage = data.get("usage")
        if isinstance(usage, Mapping):
            input_tokens = GeminiProvider._int(usage.get("total_input_tokens"))
            output_tokens = GeminiProvider._int(usage.get("total_output_tokens"))

        return ProviderTurn(
            content="\n".join(texts).strip(),
            tool_calls=tuple(calls),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    @staticmethod
    def _int(value: object) -> int:
        return value if isinstance(value, int) and not isinstance(value, bool) else 0
