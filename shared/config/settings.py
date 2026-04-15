from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.constants.domain import EnvironmentMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "gold-ai-trading"
    env: EnvironmentMode = EnvironmentMode.DEVELOP
    service_name: str = "api_server"
    strategy_version: str = "stage2"
    model_version: str = "ai-stage2-v1"
    config_version: str = "2026.04.stage2"

    db_url: str = Field(default="postgresql+psycopg2://gold:gold@db:5432/gold_ai")
    redis_url: str = Field(default="redis://redis:6379/0")
    jwt_secret: str = Field(default="CHANGE_ME", min_length=8)
    session_ttl_minutes: int = 15

    # Telegram notification
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # AI provider configuration
    ai_provider: str = Field(default="mock", description="AI provider: mock|deepseek")
    deepseek_api_base: str = Field(default="https://api.deepseek.com", description="DeepSeek API base URL")
    deepseek_api_key: str = Field(default="", description="DeepSeek API key")
    ai_timeout_ms: int = Field(default=10000, description="AI request timeout in milliseconds")
    ai_max_retries: int = Field(default=3, description="Maximum retry attempts for AI requests")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
