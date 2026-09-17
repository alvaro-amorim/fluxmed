import os
from dataclasses import dataclass

DEFAULT_MODELS = {
    "mock": "fluxmed-mock-v1",
    "cohere": "command-a-plus-05-2026",
    "gemini": "gemini-3.5-flash-lite",
}

DEFAULT_THINKING_LEVELS = {
    "gemini-3.5-flash-lite": "minimal",
    "gemini-3.5-flash": "minimal",
    "gemini-3.6-flash": "minimal",
    "gemini-3.7-flash": "low",
    "gemini-3.8-flash": "low",
    "gemini-2.5-flash": "low",
}


@dataclass(frozen=True, slots=True)
class LLMSettings:
    provider: str
    model: str
    timeout_seconds: float
    max_tool_calls_per_request: int
    max_output_chars: int
    thinking_level: str = "low"
    max_context_chars: int = 30000

    @classmethod
    def from_env(cls) -> "LLMSettings":
        provider = os.getenv("LLM_PROVIDER", "mock").strip().lower() or "mock"
        default_model = DEFAULT_MODELS.get(provider, "")
        model = os.getenv("LLM_MODEL", default_model).strip() or default_model
        default_thinking = DEFAULT_THINKING_LEVELS.get(model, "low")
        thinking_level = (
            os.getenv("LLM_THINKING_LEVEL", default_thinking).strip().lower()
            or default_thinking
        )
        return cls(
            provider=provider,
            model=model,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
            max_tool_calls_per_request=int(os.getenv("LLM_MAX_TOOL_CALLS", "5")),
            max_output_chars=int(os.getenv("LLM_MAX_OUTPUT_CHARS", "6000")),
            thinking_level=thinking_level,
            max_context_chars=int(os.getenv("LLM_MAX_CONTEXT_CHARS", "30000")),
        )
