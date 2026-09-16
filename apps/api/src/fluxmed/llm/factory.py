import os

from fluxmed.llm import LLMProvider
from fluxmed.llm.config import LLMSettings
from fluxmed.llm.providers import CohereProvider, GeminiProvider
from fluxmed.llm.providers.grounded_mock import GroundedMockLLMProvider


class LLMProviderUnavailableError(RuntimeError):
    pass


def build_llm_provider(settings: LLMSettings) -> LLMProvider:
    if settings.provider == "mock":
        return GroundedMockLLMProvider(settings.model or "fluxmed-mock-v2")
    if settings.provider == "cohere":
        api_key = os.getenv("COHERE_API_KEY", "").strip()
        if not api_key:
            raise LLMProviderUnavailableError("COHERE_API_KEY não configurada.")
        return CohereProvider(
            api_key=api_key,
            model=settings.model or "command-a-plus-05-2026",
            timeout_seconds=settings.timeout_seconds,
        )
    if settings.provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise LLMProviderUnavailableError("GEMINI_API_KEY não configurada.")
        return GeminiProvider(
            api_key=api_key,
            model=settings.model or "gemini-2.5-flash",
            timeout_seconds=settings.timeout_seconds,
        )
    raise LLMProviderUnavailableError(
        f"Provider LLM '{settings.provider}' ainda não está configurado neste ambiente."
    )
