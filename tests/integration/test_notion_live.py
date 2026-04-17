"""Live Notion API checks (requires valid ``.env`` at repo root)."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest
from dotenv import load_dotenv
from notion_client import APIResponseError
from notion_client import Client as NotionClient
from pydantic import ValidationError

from telegram_to_notion.config import Settings
from telegram_to_notion.models import IncomingMessage, MediaType, NotionEnrichment
from telegram_to_notion.notion import NotionWriter

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def integration_settings() -> Settings:
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        pytest.skip(f"missing {env_path}")
    load_dotenv(env_path)
    try:
        return Settings(_env_file=None)  # type: ignore[call-arg]
    except ValidationError as exc:
        pytest.skip(f"invalid settings: {exc}")


@pytest.mark.asyncio
async def test_notion_database_retrieve_live(integration_settings: Settings) -> None:
    """Verify token and database id: integration can read the target database."""
    client = NotionClient(auth=integration_settings.notion_token.get_secret_value())
    db = await asyncio.to_thread(
        client.databases.retrieve, database_id=integration_settings.notion_database_id
    )
    assert db["id"]
    assert "properties" in db or "data_sources" in db


@pytest.mark.asyncio
async def test_create_text_page_notion_live(integration_settings: Settings) -> None:
    """Create a text-only page then archive it (needs DB properties from README)."""
    client = NotionClient(auth=integration_settings.notion_token.get_secret_value())
    writer = NotionWriter(client=client, database_id=integration_settings.notion_database_id)
    msg = IncomingMessage(
        text="[integration-test] telegram-to-notion",
        caption=None,
        sender="pytest",
        sent_at=datetime.now(timezone.utc),
        media_type=MediaType.TEXT,
        media=None,
    )
    enrichment = NotionEnrichment.from_incoming(msg)
    page_id: str | None = None
    try:
        try:
            page_id = await writer.create_page(msg, enrichment)
        except APIResponseError as exc:
            if "not a property that exists" in str(exc):
                pytest.skip(
                    "Notion database schema does not match README (Title, Label, Type, URL, "
                    "Description, Interest, Sender, Date, Media type)."
                )
            raise
        assert page_id
        assert len(page_id) == 36
        assert page_id.count("-") == 4
    finally:
        if page_id:
            await asyncio.to_thread(client.pages.update, page_id, archived=True)
