import logging
from typing import List, Optional
from google import genai
from google.genai.errors import APIError

from app.config import settings
from app.embeddings.base import EmbeddingProvider, EmbeddingProviderError

logger = logging.getLogger("civiclens.embeddings.gemini")


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or "gemini-embedding-001"
        if not self.api_key:
            raise EmbeddingProviderError("GEMINI_API_KEY environment variable is not configured.")
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client for Embeddings: {e}")
            raise EmbeddingProviderError(f"Gemini Embedding Client initialization failed: {str(e)}")

    async def generate_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise EmbeddingProviderError("Text cannot be empty for embedding generation.")

        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=text.strip()
            )

            if not response or not hasattr(response, "embeddings") or not response.embeddings:
                raise EmbeddingProviderError("Empty embedding vector returned by Gemini API.")

            vector = response.embeddings[0].values
            return list(vector)
        except APIError as e:
            logger.error(f"Gemini Embedding API Error: {e}")
            raise EmbeddingProviderError(f"Gemini Embedding service failed: {str(e)}")
        except Exception as e:
            if isinstance(e, EmbeddingProviderError):
                raise e
            logger.error(f"Unexpected error during embedding generation: {e}")
            raise EmbeddingProviderError(f"Embedding Error: {str(e)}")
