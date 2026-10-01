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

    # Real Model Providers (OpenAI, Groq, OpenRouter, DeepSeek, Ollama)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    SMALL_MODEL_NAME: str = "gpt-4o-mini"
    FRONTIER_MODEL_NAME: str = "gpt-4o"
    SMALL_MODEL_INPUT_COST_PER_M: float = 0.15
    SMALL_MODEL_OUTPUT_COST_PER_M: float = 0.60
    FRONTIER_MODEL_INPUT_COST_PER_M: float = 2.50
    FRONTIER_MODEL_OUTPUT_COST_PER_M: float = 10.00

    # Policy Engine Deterministic Thresholds
    HIGH_CONFIDENCE_THRESHOLD: float = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD: float = 0.60
    MAX_LATENCY_BUDGET_MS: int = 2000
    MAX_COST_PER_REQUEST: float = 0.05
    HIGH_LOAD_THRESHOLD: float = 0.80
    MAX_CONCURRENCY: int = 100
    ENABLE_HUMAN_REVIEW: bool = True
    ENABLE_CACHE: bool = True

    # Cache & Rate Limiting (Redis)
    REDIS_URL: Optional[str] = None
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST_CAPACITY: int = 10

    # Database
    DATABASE_URL: Optional[str] = "sqlite+aiosqlite:///./jevflow_telemetry.db"

    # OpenRouter Specific (JEV Decisions API & JEV Smart Router)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DECISIONS_URL: str = "https://openrouter.ai/api/alpha/decisions"
    JEV_DECISION_MODEL: str = "typesafe/jev-1.13"
    JEV_ROUTER_MODEL: str = "typesafe/jev-router"


settings = Settings()
