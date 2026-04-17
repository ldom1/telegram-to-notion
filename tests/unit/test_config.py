"""Tests for ``telegram_to_notion.config.Settings``."""

import pytest
from pydantic import ValidationError

from telegram_to_notion.config import Settings, normalize_notion_uuid


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


def test_normalize_notion_uuid_from_32_hex():
    assert normalize_notion_uuid("3456c45194658025ac90ff3627b14bbf") == (
        "3456c451-9465-8025-ac90-ff3627b14bbf"
    )


def test_settings_normalizes_notion_database_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1:a")
    monkeypatch.setenv("NOTION_TOKEN", "s")
    monkeypatch.setenv("NOTION_DATABASE_ID", "3456c45194658025ac90ff3627b14bbf")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.notion_database_id == "3456c451-9465-8025-ac90-ff3627b14bbf"
