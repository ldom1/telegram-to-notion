"""Tests for LLM system prompt builder."""

from datetime import datetime, timezone

from telegram_to_notion.llm.prompt import build_openrouter_system_prompt
from telegram_to_notion.models import IncomingMessage, MediaType


def test_build_prompt_wraps_body_in_message_tags() -> None:
    """Prompt uses XML-style delimiters around user content."""
    msg = IncomingMessage(
        text="hello",
        caption=None,
        sender="alice",
        sent_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        media_type=MediaType.TEXT,
        media=None,
    )
    p = build_openrouter_system_prompt(msg)
    assert "<message>" in p and "</message>" in p
    assert "hello" in p
    assert '"source"' in p


def test_build_prompt_includes_source_hint_for_instagram() -> None:
    """Known domains inject a SOURCE HINT for the model."""
    msg = IncomingMessage(
        text="https://instagram.com/p/abc",
        caption=None,
        sender="bob",
        sent_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        media_type=MediaType.TEXT,
        media=None,
    )
    p = build_openrouter_system_prompt(msg)
    assert "SOURCE HINT:" in p
    assert "Instagram" in p
