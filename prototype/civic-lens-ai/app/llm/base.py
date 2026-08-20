from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProviderError(Exception):
    """Raised when the underlying LLM provider service fails or is unreachable."""
    pass


class LLMInvalidOutputError(Exception):
    """Raised when the LLM returns malformed or non-schema-compliant output after retries."""
    pass


class LLMProvider(ABC):
    """Abstract interface for LLM providers in CivicLens AI Engine."""

    @abstractmethod
    async def extract_structured(
        self, text: str, language: str, retry_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured JSON output from input complaint text.

        Args:
            text: Complaint text (either original or normalized).
            language: Detected language code (e.g. 'en', 'hi', 'or').
            retry_prompt: Optional error guidance string for correction retries.

        Returns:
            Dict containing raw JSON structure matching Classification schema.
        """
        pass

    @abstractmethod
    async def extract_location_clues(self, text: str) -> Dict[str, Any]:
        """
        Extract location clues from complaint text for geocoding.
        
        Args:
            text: Complaint text.
            
        Returns:
            Dict containing raw JSON structure matching LocationClues schema.
        """
        pass

