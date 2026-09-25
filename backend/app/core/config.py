from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "JevFlow Adaptive Gateway"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # TypeSafe / Jev Settings
    TYPESAFE_API_KEY: Optional[str] = None
    TYPESAFE_BASE_URL: str = "https://api.typesafe.ai"
    JEV_DEFAULT_MODEL: str = "jev-latest"
    JEV_TIMEOUT_MS: int = 1500

    # Policy Engine Deterministic Thresholds
    HIGH_CONFIDENCE_THRESHOLD: float = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD: float = 0.60
    MAX_LATENCY_BUDGET_MS: int = 2000
    MAX_COST_PER_REQUEST: float = 0.05
    HIGH_LOAD_THRESHOLD: float = 0.80
    MAX_CONCURRENCY: int = 100
    ENABLE_HUMAN_REVIEW: bool = True
    ENABLE_CACHE: bool = True


settings = Settings()
