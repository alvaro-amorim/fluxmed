import os

from fluxmed.llm import LLMProvider
from fluxmed.llm.config import LLMSettings
from fluxmed.llm.providers import CohereProvider, MockLLMProvider


class LLMProviderUnavailableError(RuntimeError):
    pass


def build_llm_provider(settings: LLMSettings) -> LLMProvider:
    if settings.provider == "mock":
        return MockLLMProvider(settings.model or "fluxmed-mock-v1")
    if settings.provider == "cohere":
        api_key = os.getenv("COHERE_API_KEY", "").strip()
        if not api_key:
            raise LLMProviderUnavailableError("COHERE_API_KEY não configurada.")
        return CohereProvider(
            api_key=api_key,
            model=settings.model or "command-a-plus-05-2026",
            timeout_seconds=settings.timeout_seconds,
        )
    raise LLMProviderUnavailableError(
        f"Provider LLM '{settings.provider}' ainda não está configurado neste ambiente."
    )
