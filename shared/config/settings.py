from functools import lru_cache
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.constants.domain import EnvironmentMode


class Settings(BaseSettings):
    """Stage 2 configuration with environment variable support and backward compatibility."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="GOLD_"  # Prefix for environment variables
    )

    # Application
    app_name: str = Field(default="gold-ai-trading", description="Application name")
    env: EnvironmentMode = Field(default=EnvironmentMode.DEVELOP, description="Environment mode")
    service_name: str = Field(default="api_server", description="Service identifier")
    
    # Version tracking (configurable for stage2)
    strategy_version: str = Field(default="stage2", description="Strategy version tag")
    model_version: str = Field(default="ai-stage2-v1", description="AI model version")
    config_version: str = Field(default="2026.04.stage2", description="Configuration version")

    # Database
    db_url: str = Field(
        default="postgresql+psycopg2://gold:gold@db:5432/gold_ai",
        description="Database connection URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL"
    )

    # Security
    jwt_secret: str = Field(
        default="CHANGE_ME",
        min_length=8,
        description="JWT signing secret (must be set in production)"
    )
    session_ttl_minutes: int = Field(default=15, ge=1, le=1440, description="Session TTL in minutes")

    # Telegram notifications (optional)
    telegram_bot_token: str = Field(default="", description="Telegram bot token for notifications")
    telegram_chat_id: str = Field(default="", description="Telegram chat ID for notifications")

    # AI provider configuration (configurable with backward compatible defaults)
    ai_provider: str = Field(
        default="mock",
        description="AI provider: mock|deepseek"
    )
    deepseek_api_base: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API base URL"
    )
    deepseek_api_key: str = Field(
        default="",
        description="DeepSeek API key (required when ai_provider=deepseek)"
    )
    ai_timeout_ms: int = Field(
        default=10000,
        ge=1000,
        le=60000,
        description="AI request timeout in milliseconds"
    )
    ai_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for AI requests"
    )

    # Stage 2 specific settings (backward compatible - defaults match stage1)
    entry_protection_mode: str = Field(
        default="protective",
        description="Entry mode: protective|aggressive (stage2 feature)"
    )
    ai_review_required: bool = Field(
        default=True,
        description="Require AI review for signals (stage2 feature)"
    )
    event_window_blocking: bool = Field(
        default=True,
        description="Block entries during event windows (stage2 feature)"
    )

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables (for containerized deployments)."""
        return cls()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
