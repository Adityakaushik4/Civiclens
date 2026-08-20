from app.config import settings
from app.vision.base import VisionProvider, VisionProviderError
from app.vision.gemini_vision import GeminiVisionProvider


def get_vision_provider(provider_name: str = None) -> VisionProvider:
    """
    Factory function to return an instance of VisionProvider based on configuration.
    Allows seamlessly switching Vision providers (gemini, etc.) via environment variables.
    """
    name = (provider_name or settings.VISION_PROVIDER).lower().strip()
    if name == "gemini":
        return GeminiVisionProvider()
    else:
        raise VisionProviderError(f"Unsupported Vision provider: '{name}'. Supported providers: 'gemini'")
