"""Photo extraction."""

from telegram import Message

from telegram_to_notion.media.base import download_telegram_file
from telegram_to_notion.models import MediaPayload


async def extract_photo(message: Message) -> MediaPayload:
    """Take the largest available photo size from a Telegram message."""
    if not message.photo:
        raise ValueError("message has no photo")
    largest = message.photo[-1]
    filename = f"{largest.file_unique_id}.jpg"
    return await download_telegram_file(
        message.get_bot(), largest.file_id, filename, "image/jpeg"
    )
