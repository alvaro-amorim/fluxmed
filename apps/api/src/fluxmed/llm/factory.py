import os
from functools import lru_cache

from fluxmed.llm import LLMProvider
from fluxmed.llm.config import LLMSettings
from fluxmed.llm.providers import CohereProvider, GeminiProvider
from fluxmed.llm.providers.grounded_mock import GroundedMockLLMProvider


class LLMProviderUnavailableError(RuntimeError):
    pass


def build_llm_provider(settings: LLMSettings) -> LLMProvider:
    if settings.provider == "mock":
        return _build_cached_provider(
            "mock",
            settings.model or "fluxmed-mock-v2",
            settings.timeout_seconds,
            settings.thinking_level,
            "",
        )
    if settings.provider == "cohere":
        api_key = os.getenv("COHERE_API_KEY", "").strip()
        if not api_key:
            raise LLMProviderUnavailableError("COHERE_API_KEY não configurada.")
        return _build_cached_provider(
            "cohere",
            settings.model or "command-a-plus-05-2026",
            settings.timeout_seconds,
            settings.thinking_level,
            api_key,
        )
    if settings.provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise LLMProviderUnavailableError("GEMINI_API_KEY não configurada.")
        return _build_cached_provider(
            "gemini",
            settings.model or "gemini-3.5-flash-lite",
            settings.timeout_seconds,
            settings.thinking_level,
            api_key,
        )
    raise LLMProviderUnavailableError(
        f"Provider LLM '{settings.provider}' ainda não está configurado neste ambiente."
    )


@lru_cache(maxsize=8)
def _build_cached_provider(
    provider: str,
    model: str,
    timeout_seconds: float,
    thinking_level: str,
    api_key: str,
) -> LLMProvider:
    if provider == "mock":
        return GroundedMockLLMProvider(model)
    if provider == "cohere":
        return CohereProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    if provider == "gemini":
        return GeminiProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            thinking_level=thinking_level,
        )
    raise LLMProviderUnavailableError(f"Provider LLM '{provider}' não suportado.")


def clear_llm_provider_cache() -> None:
    """Test/development hook for explicit provider reconfiguration in-process."""

    _build_cached_provider.cache_clear()
