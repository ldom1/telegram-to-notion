"""Media extraction + download helpers."""

from telegram_to_notion.media.animation import extract_animation
from telegram_to_notion.media.base import download_telegram_file
from telegram_to_notion.media.document import extract_document
from telegram_to_notion.media.img import extract_photo
from telegram_to_notion.media.video import extract_video

__all__ = [
    "download_telegram_file",
    "extract_animation",
    "extract_document",
    "extract_photo",
    "extract_video",
]
