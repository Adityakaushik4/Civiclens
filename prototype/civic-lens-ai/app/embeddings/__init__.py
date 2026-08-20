"""Text and Multimodal Embedding Providers module."""
from app.embeddings.base import EmbeddingProvider, EmbeddingProviderError
from app.embeddings.factory import get_embedding_provider

__all__ = ["EmbeddingProvider", "EmbeddingProviderError", "get_embedding_provider"]
