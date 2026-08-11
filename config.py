from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "AlphaPulse"

    bot_token: str
    admin_telegram_id: int
    mini_app_url: str = "http://localhost:3000"
    api_base_url: str = "http://api:8080"

    database_url: str = "postgresql+asyncpg://user:pass@postgres:5432/signals_db"
    redis_url: str = "redis://redis:6379/0"

    exchangerate_api_key: str = ""
    alpha_vantage_key: str = ""

    jwt_secret: str
    admin_token: str
    jwt_expires_hours: int = 24

    confidence_threshold: float = Field(default=0.72, ge=0.0, le=1.0)
    max_active_signals: int = Field(default=15, ge=1)
    retrain_interval_days: int = Field(default=7, ge=1)
    ml_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    cooldown_seconds: int = Field(default=15, ge=0)

    cryptobot_api_token: str = ""
    usdt_trc20_wallet: str = ""
    cf_tunnel_token: str = ""

    @property
    def indicator_weight(self) -> float:
        return 1.0 - self.ml_weight


@lru_cache
def get_settings() -> Settings:
    return Settings()

