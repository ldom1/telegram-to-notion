import pytest
from pydantic import ValidationError

from telegram_to_notion.config import Settings


def test_settings_requires_all_fields(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("NOTION_TOKEN", "secret_xyz")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db-uuid")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.telegram_bot_token.get_secret_value() == "123:abc"
    assert settings.notion_token.get_secret_value() == "secret_xyz"
    assert settings.notion_database_id == "db-uuid"
