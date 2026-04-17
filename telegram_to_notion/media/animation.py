"""Download Telegram animation (GIF) payloads as ``MediaPayload``."""

from telegram import Message

from telegram_to_notion.media.base import download_telegram_file
from telegram_to_notion.models import MediaPayload


async def extract_animation(message: Message) -> MediaPayload:
    """Resolve ``message.animation``; often reported as ``video/mp4`` without a file name."""
    anim = message.animation
    if anim is None:
        raise ValueError("message has no animation")
    filename = anim.file_name or f"{anim.file_unique_id}.mp4"
    mime = anim.mime_type or "video/mp4"
    return await download_telegram_file(message.get_bot(), anim.file_id, filename, mime)
