from app.config import settings
from app.embeddings.base import EmbeddingProvider, EmbeddingProviderError
from app.embeddings.gemini_embedding import GeminiEmbeddingProvider


def get_embedding_provider(provider_name: str = None) -> EmbeddingProvider:
    """
    Factory function to return an instance of EmbeddingProvider based on configuration.
    """
    name = (provider_name or settings.LLM_PROVIDER).lower().strip()
    if name in ["gemini", "google"]:
        return GeminiEmbeddingProvider()
    else:
        raise EmbeddingProviderError(f"Unsupported Embedding provider: '{name}'. Supported: 'gemini'")
