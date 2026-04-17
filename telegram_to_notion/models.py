"""Pydantic data models for internal message flow."""

import re
from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field

from telegram_to_notion.llm.source_hints import infer_source_label

_URL_RE = re.compile(r"https?://[^\s<>\[\]()]+", re.IGNORECASE)


def _first_url(text: str) -> str | None:
    """Return the first HTTP(S) URL in ``text``, with trailing punctuation trimmed."""
    match = _URL_RE.search(text)
    if not match:
        return None
    return match.group(0).rstrip(").,]\\\"'")


class MediaType(str, Enum):
    """Kind of Telegram content we persist to Notion."""

    TEXT = "text"
    PHOTO = "photo"
    DOCUMENT = "document"
    VIDEO = "video"
    ANIMATION = "animation"
    VOICE = "voice"


class MediaPayload(BaseModel):
    """Downloaded file bytes plus filename and MIME type for Notion upload."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    content: bytes
    filename: str
    mime_type: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def size_bytes(self) -> int:
        """Length of ``content`` in bytes."""
        return len(self.content)


class IncomingMessage(BaseModel):
    """Normalized inbound message: text/caption, sender, time, media."""

    model_config = ConfigDict(frozen=True)

    text: str | None
    caption: str | None
    sender: str
    sent_at: datetime
    media_type: MediaType
    media: MediaPayload | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def title(self) -> str:
        """First line of text or caption (trimmed, max 200 chars), else ``[media_type]``."""
        source = self.text or self.caption
        if source:
            first_line = source.strip().splitlines()[0]
            return first_line[:200] or f"[{self.media_type.value}]"
        return f"[{self.media_type.value}]"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def body(self) -> str:
        """Full text or caption for the page body (empty string if neither)."""
        return self.text or self.caption or ""


class NotionEnrichment(BaseModel):
    """Structured row fields for Notion (from OpenRouter or heuristics)."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, populate_by_name=True)

    title: str
    label: str = ""
    entry_type: str = Field(default="", alias="type")
    url: str | None = None
    source: str | None = None
    description: str = ""
    interest: str = ""

    @classmethod
    def from_incoming(cls, msg: IncomingMessage) -> Self:
        """Heuristic mapping when OpenRouter is disabled or fails."""
        body = msg.body
        url = _first_url(body) if body else None
        desc = body if body else msg.title
        src = infer_source_label(body) if body else None
        return cls(
            title=msg.title[:2000],
            label="telegram",
            type=msg.media_type.value,
            url=url,
            source=src,
            description=desc[:8000],
            interest="Medium",
        )
