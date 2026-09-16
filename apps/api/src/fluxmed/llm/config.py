import os
from dataclasses import dataclass

DEFAULT_MODELS = {
    "mock": "fluxmed-mock-v1",
    "cohere": "command-a-plus-05-2026",
    "gemini": "gemini-2.5-flash",
}


@dataclass(frozen=True, slots=True)
class LLMSettings:
    provider: str
    model: str
    timeout_seconds: float
    max_tool_calls_per_request: int
    max_output_chars: int

    @classmethod
    def from_env(cls) -> "LLMSettings":
        provider = os.getenv("LLM_PROVIDER", "mock").strip().lower() or "mock"
        default_model = DEFAULT_MODELS.get(provider, "")
        model = os.getenv("LLM_MODEL", default_model).strip() or default_model
        return cls(
            provider=provider,
            model=model,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
            max_tool_calls_per_request=int(os.getenv("LLM_MAX_TOOL_CALLS", "5")),
            max_output_chars=int(os.getenv("LLM_MAX_OUTPUT_CHARS", "6000")),
        )
