from app.config import settings
from app.stt.base import SpeechToTextProvider, STTProviderError
from app.stt.gemini_stt import GeminiSTTProvider


def get_stt_provider(provider_name: str = None) -> SpeechToTextProvider:
    """
    Factory function to return an instance of SpeechToTextProvider based on configuration.
    Allows seamlessly switching STT providers (gemini, etc.) via environment variables.
    """
    name = (provider_name or settings.STT_PROVIDER).lower().strip()
    if name == "gemini":
        return GeminiSTTProvider()
    else:
        raise STTProviderError(f"Unsupported STT provider: '{name}'. Supported providers: 'gemini'")
