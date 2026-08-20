from abc import ABC, abstractmethod
from typing import Optional, Tuple
from app.schemas import VisualAnalysis, ComplaintAnalysis


class VisionProviderError(Exception):
    """Raised when the Vision provider service fails or is unreachable."""
    pass


class VisionInvalidImageError(Exception):
    """Raised when the input image file is corrupt, unreadable, or empty."""
    pass


class VisionProvider(ABC):
    """Abstract interface for Vision LLM providers in CivicLens AI Engine."""

    @abstractmethod
    async def analyze_image(
        self, file_path: str, mime_type: str, optional_text: Optional[str] = None
    ) -> Tuple[VisualAnalysis, ComplaintAnalysis, bool, Optional[str]]:
        """
        Analyze an uploaded civic issue image with optional accompanying text.

        Args:
            file_path: Absolute path to local temporary image file.
            mime_type: MIME type of image (e.g. 'image/jpeg', 'image/png', 'image/webp').
            optional_text: Optional text complaint accompanying the image.

        Returns:
            Tuple of (VisualAnalysis, ComplaintAnalysis, evidence_disagreement: bool, disagreement_reason: Optional[str]).
        """
        pass
