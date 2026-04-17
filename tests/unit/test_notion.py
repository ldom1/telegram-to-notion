"""Unit tests for ``NotionWriter`` with a mocked Notion SDK client."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from telegram_to_notion.models import IncomingMessage, MediaType, NotionEnrichment
from telegram_to_notion.notion import NotionWriter


@pytest.fixture
def text_message():
    return IncomingMessage(
        text="hello",
        caption=None,
        sender="alice",
        sent_at=datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc),
        media_type=MediaType.TEXT,
        media=None,
    )


async def test_create_page_text_only_database_parent(text_message):
    mock_client = MagicMock()
    mock_client.databases.retrieve.return_value = {"id": "db-1", "properties": {"Title": {}}}
    mock_client.pages.create.return_value = {"id": "page-123"}
    writer = NotionWriter(client=mock_client, database_id="db-1")
    enrichment = NotionEnrichment.from_incoming(text_message)

    page_id = await writer.create_page(text_message, enrichment)

    assert page_id == "page-123"
    mock_client.pages.create.assert_called_once()
    call_kwargs = mock_client.pages.create.call_args.kwargs
    assert call_kwargs["parent"] == {"type": "database_id", "database_id": "db-1"}
    props = call_kwargs["properties"]
    assert props["Title"]["title"][0]["text"]["content"] == "hello"
    assert props["Sender"]["rich_text"][0]["text"]["content"] == "alice"
    assert props["Media type"]["select"]["name"] == "text"
    assert props["Label"]["rich_text"][0]["text"]["content"] == "telegram"
    assert props["Type"]["rich_text"][0]["text"]["content"] == "text"
    assert props["Interest"]["rich_text"][0]["text"]["content"] == "Medium"


async def test_create_page_uses_first_data_source(text_message):
    mock_client = MagicMock()
    mock_client.databases.retrieve.return_value = {
        "id": "db-1",
        "data_sources": [{"id": "ds-aaa", "name": "Main"}],
    }
    mock_client.pages.create.return_value = {"id": "page-456"}
    writer = NotionWriter(client=mock_client, database_id="db-1")
    enrichment = NotionEnrichment.from_incoming(text_message)

    await writer.create_page(text_message, enrichment)

    parent = mock_client.pages.create.call_args.kwargs["parent"]
    assert parent == {
        "type": "data_source_id",
        "data_source_id": "ds-aaa",
        "database_id": "db-1",
    }


async def test_create_page_explicit_data_source_override(text_message):
    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "page-789"}
    writer = NotionWriter(client=mock_client, database_id="db-1", data_source_id="ds-fixed")
    enrichment = NotionEnrichment.from_incoming(text_message)

    await writer.create_page(text_message, enrichment)

    mock_client.databases.retrieve.assert_not_called()
    parent = mock_client.pages.create.call_args.kwargs["parent"]
    assert parent == {
        "type": "data_source_id",
        "data_source_id": "ds-fixed",
        "database_id": "db-1",
    }
