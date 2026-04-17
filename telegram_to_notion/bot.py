"""Telegram bot: long-polling listener that forwards messages to Notion."""

import sys
from collections.abc import Callable, Coroutine
from datetime import timezone
from typing import Any

from loguru import logger
from notion_client import Client as NotionClient
from telegram import Message, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram_to_notion.config import Settings, load_settings
from telegram_to_notion.media import (
    extract_animation,
    extract_document,
    extract_photo,
    extract_video,
)
from telegram_to_notion.models import IncomingMessage, MediaPayload, MediaType
from telegram_to_notion.notion import NotionWriter


async def _build_message(tg_message: Message) -> IncomingMessage:
    """Map a Telegram ``Message`` to our internal ``IncomingMessage`` model."""
    media_type, media = await _resolve_media(tg_message)
    user = tg_message.from_user
    if user is not None:
        sender = user.username or user.full_name or "unknown"
    else:
        sender = "unknown"
    sent_at = tg_message.date
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)

    return IncomingMessage(
        text=tg_message.text,
        caption=tg_message.caption,
        sender=sender,
        sent_at=sent_at,
        media_type=media_type,
        media=media,
    )


async def _resolve_media(
    tg_message: Message,
) -> tuple[MediaType, MediaPayload | None]:
    """Pick media type and downloaded payload; animation is checked before video (GIFs)."""
    if tg_message.photo:
        return MediaType.PHOTO, await extract_photo(tg_message)
    if tg_message.animation:
        return MediaType.ANIMATION, await extract_animation(tg_message)
    if tg_message.video:
        return MediaType.VIDEO, await extract_video(tg_message)
    if tg_message.document:
        return MediaType.DOCUMENT, await extract_document(tg_message)
    return MediaType.TEXT, None


def _make_handler(
    writer: NotionWriter,
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]:
    """Build a handler that forwards each message to ``writer``."""

    async def handle(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message is None:
            return
        try:
            incoming = await _build_message(update.effective_message)
            page_id = await writer.create_page(incoming)
            logger.info("wrote notion page {} from {}", page_id, incoming.sender)
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            logger.exception("failed to forward telegram message to notion")

    return handle


def build_application(settings: Settings) -> Application[Any, Any, Any, Any, Any, Any]:
    """Wire Telegram ``Application`` with Notion-backed message handlers."""
    notion_client = NotionClient(auth=settings.notion_token.get_secret_value())
    writer = NotionWriter(client=notion_client, database_id=settings.notion_database_id)

    app = ApplicationBuilder().token(settings.telegram_bot_token.get_secret_value()).build()
    handler = _make_handler(writer)
    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.ANIMATION,
            handler,
        )
    )
    return app


def run() -> None:
    """Load settings, configure logging, and start long polling."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function} - {message}",
    )
    settings = load_settings()
    app = build_application(settings)
    logger.info("starting telegram-to-notion polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
