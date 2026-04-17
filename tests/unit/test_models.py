"""Tests for ``telegram_to_notion.models``."""

from datetime import datetime, timezone

from telegram_to_notion.models import IncomingMessage, MediaPayload, MediaType, NotionEnrichment


def test_media_type_values():
    assert MediaType.TEXT.value == "text"
    assert MediaType.PHOTO.value == "photo"
    assert MediaType.DOCUMENT.value == "document"
    assert MediaType.VIDEO.value == "video"
    assert MediaType.ANIMATION.value == "animation"
    assert MediaType.VOICE.value == "voice"


def test_incoming_message_text_only():
    msg = IncomingMessage(
        text="hello world",
        caption=None,
        sender="alice",
        sent_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        media_type=MediaType.TEXT,
        media=None,
    )
    assert msg.title == "hello world"


def test_incoming_message_title_first_line():
    msg = IncomingMessage(
        text="line one\nline two",
        caption=None,
        sender="alice",
        sent_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        media_type=MediaType.TEXT,
        media=None,
    )
    assert msg.title == "line one"


def test_incoming_message_title_falls_back_to_media_label():
    msg = IncomingMessage(
        text=None,
        caption=None,
        sender="bob",
        sent_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        media_type=MediaType.PHOTO,
        media=MediaPayload(content=b"\x00", filename="img.jpg", mime_type="image/jpeg"),
    )
    assert msg.title == "[photo]"


def test_media_payload_size():
    payload = MediaPayload(content=b"abc", filename="x.txt", mime_type="text/plain")
    assert payload.size_bytes == 3


def test_notion_enrichment_from_incoming_extracts_url():
    msg = IncomingMessage(
        text="read https://example.org/a) ok",
        caption=None,
        sender="u",
        sent_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        media_type=MediaType.TEXT,
        media=None,
    )
    en = NotionEnrichment.from_incoming(msg)
    assert en.url == "https://example.org/a"
