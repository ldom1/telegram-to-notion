"""Runtime configuration loaded from environment variables."""

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_notion_uuid(value: str) -> str:
    """Turn a 32-char hex id (common in Notion URLs) into hyphenated UUID form."""
    raw = value.strip()
    compact = raw.replace("-", "").lower()
    if len(compact) == 32 and all(c in "0123456789abcdef" for c in compact):
        return f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"
    return raw


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
    notion_title_property: str = Field(
        default="Title",
        description="Notion title column name (use Name if your DB uses the default title)",
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

    @field_validator("notion_database_id", mode="before")
    @classmethod
    def _normalize_database_id(cls, value: object) -> str:
        if value is None:
            raise ValueError("NOTION_DATABASE_ID is required")
        return normalize_notion_uuid(str(value))

    @field_validator("notion_data_source_id", mode="before")
    @classmethod
    def _normalize_data_source_id(cls, value: object) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        return normalize_notion_uuid(s)


def load_settings() -> Settings:
    """Load settings, failing fast with a clear error on missing vars."""
    return Settings()  # type: ignore[call-arg]
