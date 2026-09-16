import os
from dataclasses import dataclass


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
        default_model = "fluxmed-mock-v1" if provider == "mock" else ""
        model = os.getenv("LLM_MODEL", default_model).strip() or default_model
        return cls(
            provider=provider,
            model=model,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
            max_tool_calls_per_request=int(os.getenv("LLM_MAX_TOOL_CALLS", "5")),
            max_output_chars=int(os.getenv("LLM_MAX_OUTPUT_CHARS", "6000")),
        )
