from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.constants.domain import EnvironmentMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "gold-ai-trading"
    env: EnvironmentMode = EnvironmentMode.DEVELOP
    service_name: str = "api_server"
    strategy_version: str = "stage1"
    model_version: str = "stub-v1"
    config_version: str = "2026.04.stage1"

    db_url: str = Field(default="postgresql+psycopg2://gold:gold@db:5432/gold_ai")
    redis_url: str = Field(default="redis://redis:6379/0")
    jwt_secret: str = Field(default="CHANGE_ME", min_length=8)
    session_ttl_minutes: int = 15

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
