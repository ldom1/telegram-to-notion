"""Document extraction."""

from telegram import Message

from telegram_to_notion.media.base import download_telegram_file
from telegram_to_notion.models import MediaPayload


async def extract_document(message: Message) -> MediaPayload:
    doc = message.document
    if doc is None:
        raise ValueError("message has no document")
    filename = doc.file_name or f"{doc.file_unique_id}"
    mime = doc.mime_type or "application/octet-stream"
    return await download_telegram_file(message.get_bot(), doc.file_id, filename, mime)
