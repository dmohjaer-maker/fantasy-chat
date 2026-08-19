from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    admin_bot_token: str
    admin_ids: str = ""            # comma separated
    postgres_dsn: str
    redis_url: str

    env: str = "development"
    log_level: str = "INFO"
    # Render injects PORT; HEALTH_PORT remains supported for local runs.
    health_port: int = Field(
        default=8080,
        validation_alias=AliasChoices("PORT", "HEALTH_PORT"),
    )

    min_age: int = 18
    message_rate_limit: int = 10
    rate_limit_window_sec: int = 10
    media_retention_days: int = 7

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
