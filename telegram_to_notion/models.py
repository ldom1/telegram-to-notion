"""Pydantic data models for internal message flow."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, computed_field


class MediaType(str, Enum):
    TEXT = "text"
    PHOTO = "photo"
    DOCUMENT = "document"
    VIDEO = "video"
    ANIMATION = "animation"


class MediaPayload(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    content: bytes
    filename: str
    mime_type: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def size_bytes(self) -> int:
        return len(self.content)


class IncomingMessage(BaseModel):
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
        source = self.text or self.caption
        if source:
            first_line = source.strip().splitlines()[0]
            return first_line[:200] or f"[{self.media_type.value}]"
        return f"[{self.media_type.value}]"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def body(self) -> str:
        return self.text or self.caption or ""
