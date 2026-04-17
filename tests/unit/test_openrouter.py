"""Tests for OpenRouter enrichment."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from telegram_to_notion.config import Settings
from telegram_to_notion.models import IncomingMessage, MediaType
from telegram_to_notion.llm.openrouter import interpret_message


@pytest.fixture
def sample_message():
    return IncomingMessage(
        text="See https://example.com/path for details",
        caption=None,
        sender="bob",
        sent_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        media_type=MediaType.TEXT,
        media=None,
    )


async def test_interpret_without_api_key(sample_message):
    settings = Settings(
        telegram_bot_token=SecretStr("t"),
        notion_token=SecretStr("n"),
        notion_database_id="d",
        openrouter_api_key=None,
        _env_file=None,  # type: ignore[call-arg]
    )
    out = await interpret_message(settings, sample_message)
    assert out.title == sample_message.title
    assert out.url == "https://example.com/path"


@patch("telegram_to_notion.llm.openrouter.httpx.AsyncClient")
async def test_interpret_openrouter_success(mock_client_cls, sample_message, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t:ok")
    monkeypatch.setenv("NOTION_TOKEN", "secret")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"title":"T","label":"work","type":"link","source":"Twitter / X",'
                    '"url":"https://x.com","description":"D","interest":"High"}'
                }
            }
        ]
    }
    instance = MagicMock()
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=None)
    instance.post = AsyncMock(return_value=response)
    mock_client_cls.return_value = instance

    out = await interpret_message(settings, sample_message)
    assert out.title == "T"
    assert out.label == "work"
    assert out.entry_type == "link"
    assert out.url == "https://x.com"
    assert out.description == "D"
    assert out.interest == "High"
    assert out.source == "Twitter / X"


@patch("telegram_to_notion.llm.openrouter.httpx.AsyncClient")
async def test_interpret_openrouter_http_error(mock_client_cls, sample_message, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t:ok")
    monkeypatch.setenv("NOTION_TOKEN", "secret")
    monkeypatch.setenv("NOTION_DATABASE_ID", "db")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    response = MagicMock()
    req = MagicMock()
    res = MagicMock()
    res.status_code = 500
    response.raise_for_status.side_effect = httpx.HTTPStatusError("err", request=req, response=res)
    instance = MagicMock()
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=None)
    instance.post = AsyncMock(return_value=response)
    mock_client_cls.return_value = instance

    out = await interpret_message(settings, sample_message)
    assert out.label == "telegram"
