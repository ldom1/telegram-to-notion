"""Runtime configuration loaded from environment variables."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # pylint: disable=too-many-instance-attributes
    """Application secrets and ids from the environment (and optional ``.env`` file)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_bot_token: SecretStr
    notion_token: SecretStr
    notion_database_id: str
    notion_data_source_id: str | None = Field(
        default=None,
        description="Optional data source UUID; if unset, first data source from DB is used",
    )

    whisper_language: str = Field(default="fr", description="Whisper language code for voice")
    whisper_model_size: str = Field(
        default="base",
        description="Whisper model size: tiny, base, small, medium, large",
    )

    openrouter_api_key: SecretStr | None = Field(
        default=None,
        description="OpenRouter API key; when set, rows are enriched via chat completions",
    )
    openrouter_model: str = Field(
        default="google/gemini-2.5-flash-lite",
        description="OpenRouter model id",
    )
    openrouter_http_referer: str = Field(
        default="",
        description="Optional HTTP-Referer for OpenRouter rankings",
    )
    openrouter_app_title: str = Field(
        default="telegram-to-notion",
        description="Optional X-OpenRouter-Title header",
    )


def load_settings() -> Settings:
    """Load settings, failing fast with a clear error on missing vars."""
    return Settings()  # type: ignore[call-arg]
