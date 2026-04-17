"""Telegram bot: long-polling listener that forwards messages to Notion."""

import logging
from datetime import timezone

from notion_client import Client as NotionClient
from telegram import Message, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram_to_notion.config import Settings
from telegram_to_notion.media import (
    extract_animation,
    extract_document,
    extract_photo,
    extract_video,
)
from telegram_to_notion.models import IncomingMessage, MediaPayload, MediaType
from telegram_to_notion.notion import NotionWriter

log = logging.getLogger(__name__)


async def _build_message(tg_message: Message) -> IncomingMessage:
    media_type, media = await _resolve_media(tg_message)
    sender = (
        tg_message.from_user.username
        or (tg_message.from_user.full_name if tg_message.from_user else None)
        or "unknown"
    )
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
    if tg_message.photo:
        return MediaType.PHOTO, await extract_photo(tg_message)
    if tg_message.animation:  # check before video — animation is also a video
        return MediaType.ANIMATION, await extract_animation(tg_message)
    if tg_message.video:
        return MediaType.VIDEO, await extract_video(tg_message)
    if tg_message.document:
        return MediaType.DOCUMENT, await extract_document(tg_message)
    return MediaType.TEXT, None


def _make_handler(writer: NotionWriter):
    async def handle(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_message is None:
            return
        try:
            incoming = await _build_message(update.effective_message)
            page_id = await writer.create_page(incoming)
            log.info("wrote notion page %s from %s", page_id, incoming.sender)
        except Exception:
            log.exception("failed to forward telegram message to notion")

    return handle


def build_application(settings: Settings) -> Application:
    notion_client = NotionClient(auth=settings.notion_token.get_secret_value())
    writer = NotionWriter(client=notion_client, database_id=settings.notion_database_id)

    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token.get_secret_value())
        .build()
    )
    handler = _make_handler(writer)
    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO | filters.Document.ALL
            | filters.VIDEO | filters.ANIMATION,
            handler,
        )
    )
    return app


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    from telegram_to_notion.config import load_settings

    settings = load_settings()
    app = build_application(settings)
    log.info("starting telegram-to-notion polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
