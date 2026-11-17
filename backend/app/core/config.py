from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "CS2 OPEN CASE BOT"
    secret_key: str = "development-only-replace-before-deploy"
    database_url: str = "sqlite:///./cs2bot.db"
    frontend_origin: str = "http://localhost:5173"
    webapp_url: str = "https://example.invalid"
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    admin_username: str = "admin"
    admin_password: str = "change-this-before-use"
    admin_token_ttl_minutes: int = 60
    rate_limit_per_minute: int = 90
    steam_delivery_enabled: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.frontend_origin.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
