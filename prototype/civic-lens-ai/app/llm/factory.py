from app.config import settings
from app.llm.base import LLMProvider, LLMProviderError
from app.llm.gemini_provider import GeminiLLMProvider


def get_llm_provider(provider_name: str = None) -> LLMProvider:
    """
    Factory function to return an instance of LLMProvider based on configuration.
    Allows seamlessly switching LLM providers (gemini, etc.) via environment variables.
    """
    name = (provider_name or settings.LLM_PROVIDER).lower().strip()
    if name == "gemini":
        return GeminiLLMProvider()
    else:
        raise LLMProviderError(f"Unsupported LLM provider: '{name}'. Supported providers: 'gemini'")
