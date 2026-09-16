from fluxmed.llm import LLMProvider
from fluxmed.llm.config import LLMSettings
from fluxmed.llm.providers import MockLLMProvider


class LLMProviderUnavailableError(RuntimeError):
    pass


def build_llm_provider(settings: LLMSettings) -> LLMProvider:
    if settings.provider == "mock":
        return MockLLMProvider(settings.model or "fluxmed-mock-v1")
    raise LLMProviderUnavailableError(
        f"Provider LLM '{settings.provider}' ainda não está configurado neste ambiente."
    )
