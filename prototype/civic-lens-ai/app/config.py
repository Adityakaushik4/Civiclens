import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.6-flash"

    STT_PROVIDER: str = "gemini"
    STT_API_KEY: str = ""
    STT_MODEL: str = "gemini-3.6-flash"
    MAX_AUDIO_SIZE_MB: int = 10

    VISION_PROVIDER: str = "gemini"
    VISION_API_KEY: str = ""
    VISION_MODEL: str = "gemini-3.6-flash"
    MAX_IMAGE_SIZE_MB: int = 10

    CONFIDENCE_HIGH_THRESHOLD: float = 0.80
    CONFIDENCE_MEDIUM_THRESHOLD: float = 0.50

    JURISDICTION_CITY: str = "Bhubaneswar"
    JURISDICTION_STATE: str = "Odisha"
    JURISDICTION_COUNTRY: str = "India"
    JURISDICTION_VIEWBOX: str = "85.60,20.15,86.00,20.45"

    JWT_SECRET_KEY: str = "civiclens-super-secret-jwt-signing-key-2026"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_stt_api_key(self) -> str:
        return self.STT_API_KEY or self.GEMINI_API_KEY

    def get_stt_model(self) -> str:
        return self.STT_MODEL or self.LLM_MODEL

    def get_vision_api_key(self) -> str:
        return self.VISION_API_KEY or self.GEMINI_API_KEY

    def get_vision_model(self) -> str:
        return self.VISION_MODEL or self.LLM_MODEL


settings = Settings()
