"""
Application configuration management via Pydantic BaseSettings.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Server Settings
    PORT: int = 4000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # LLM Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    DEFAULT_LLM_PROVIDER: str = "gemini"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Search API Providers
    TAVILY_API_KEY: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None

    # Pipeline Tuning Settings
    MAX_SEARCH_RESULTS_PER_PLATFORM: int = 5
    RELEVANCE_THRESHOLD: float = 0.35
    REQUEST_TIMEOUT_SECONDS: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
