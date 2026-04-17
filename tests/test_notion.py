from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from telegram_to_notion.models import IncomingMessage, MediaType
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


async def test_create_page_text_only(text_message):
    mock_client = MagicMock()
    mock_client.pages.create.return_value = {"id": "page-123"}
    writer = NotionWriter(client=mock_client, database_id="db-1")

    page_id = await writer.create_page(text_message)

    assert page_id == "page-123"
    mock_client.pages.create.assert_called_once()
    call_kwargs = mock_client.pages.create.call_args.kwargs
    assert call_kwargs["parent"] == {"database_id": "db-1"}
    props = call_kwargs["properties"]
    assert props["Title"]["title"][0]["text"]["content"] == "hello"
    assert props["Sender"]["rich_text"][0]["text"]["content"] == "alice"
    assert props["Media type"]["select"]["name"] == "text"
