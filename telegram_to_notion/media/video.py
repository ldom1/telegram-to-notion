"""Video extraction."""

from telegram import Message

from telegram_to_notion.media.base import download_telegram_file
from telegram_to_notion.models import MediaPayload


async def extract_video(message: Message) -> MediaPayload:
    video = message.video
    if video is None:
        raise ValueError("message has no video")
    filename = video.file_name or f"{video.file_unique_id}.mp4"
    mime = video.mime_type or "video/mp4"
    return await download_telegram_file(message.get_bot(), video.file_id, filename, mime)
