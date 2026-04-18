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
    notion_title_property: str = Field(
        default="Name",
        description="Notion title column name (use Name if your DB uses the default title)",
    )

    openrouter_api_key: SecretStr | None = Field(
        default=None,
        description="OpenRouter API key; when set, rows are enriched via chat completions",
    )
    openrouter_model: str = Field(
        default="google/gemini-2.5-flash-lite",
        description="OpenRouter model id",
    )
    openrouter_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API URL",
    )
    openrouter_http_referer: str = Field(
        default="",
        description="HTTP-Referer header sent to OpenRouter for cost attribution",
    )
    openrouter_app_title: str = Field(
        default="telegram-to-notion",
        description="X-Title header sent to OpenRouter for dashboard display",
    )

    whisper_language: str = Field(default="fr", description="faster-whisper language code")
    whisper_model_size: str = Field(default="base", description="faster-whisper model size")


def load_settings() -> Settings:
    """Load settings, failing fast with a clear error on missing vars."""
    return Settings()  # type: ignore[call-arg]
