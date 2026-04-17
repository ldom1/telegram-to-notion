"""Runtime configuration loaded from environment variables."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_bot_token: SecretStr
    notion_token: SecretStr
    notion_database_id: str


def load_settings() -> Settings:
    """Load settings, failing fast with a clear error on missing vars."""
    return Settings()  # type: ignore[call-arg]
