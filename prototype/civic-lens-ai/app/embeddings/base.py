from abc import ABC, abstractmethod
from typing import List


class EmbeddingProviderError(Exception):
    """Raised when the text embedding provider service fails."""
    pass


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers in CivicLens AI Engine."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a dense vector embedding for input text.

        Args:
            text: Input string (English, Hindi, Odia, etc.)

        Returns:
            List of floats representing dense embedding vector (e.g. 768 dimensions).
        """
        pass
