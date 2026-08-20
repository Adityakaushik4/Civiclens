from abc import ABC, abstractmethod
from app.schemas import TranscriptionResult


class STTProviderError(Exception):
    """Raised when the Speech-to-Text provider service fails or is unreachable."""
    pass


class STTInvalidAudioError(Exception):
    """Raised when the input audio file is empty, corrupted, or unsupported."""
    pass


class SpeechToTextProvider(ABC):
    """Abstract interface for Speech-to-Text providers in CivicLens AI Engine."""

    @abstractmethod
    async def transcribe(self, file_path: str, mime_type: str) -> TranscriptionResult:
        """
        Transcribe an audio file into text.

        Args:
            file_path: Absolute path to local temporary audio file.
            mime_type: MIME type of audio (e.g. 'audio/wav', 'audio/mp3', 'audio/webm', 'audio/m4a').

        Returns:
            TranscriptionResult object with transcribed text, language, confidence, and provider name.
        """
        pass
