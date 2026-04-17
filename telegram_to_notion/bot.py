"""Telegram bot: long-polling listener that forwards messages to Notion."""

import asyncio
import sys
import tempfile
from collections.abc import Callable, Coroutine
from datetime import timezone
from pathlib import Path
from typing import Any

from loguru import logger
from notion_client import APIResponseError, Client as NotionClient
from telegram import Message, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
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
    extract_voice,
)
from telegram_to_notion.models import IncomingMessage, MediaPayload, MediaType
from telegram_to_notion.notion import NotionWriter
from telegram_to_notion.openrouter import interpret_message
from telegram_to_notion.transcribe import transcribe_file


async def _transcribe_voice_note(settings: Settings, message: Message) -> str | None:
    """Download voice bytes to a temp file and run faster-whisper in a worker thread."""
    payload = await extract_voice(message)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(payload.content)
        path = tmp.name
    try:
        return await asyncio.to_thread(
            transcribe_file,
            path,
            settings.whisper_language,
            settings.whisper_model_size,
        )
    finally:
        Path(path).unlink(missing_ok=True)


async def _build_message(settings: Settings, tg_message: Message) -> IncomingMessage:
    """Map a Telegram ``Message`` to our internal ``IncomingMessage`` model."""
    user = tg_message.from_user
    if user is not None:
        sender = user.username or user.full_name or "unknown"
    else:
        sender = "unknown"
    sent_at = tg_message.date
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)

    if tg_message.voice is not None:
        transcript = await _transcribe_voice_note(settings, tg_message)
        text = transcript or (
            "[voice] Transcription unavailable (check uv sync / faster-whisper import)."
        )
        return IncomingMessage(
            text=text,
            caption=tg_message.caption,
            sender=sender,
            sent_at=sent_at,
            media_type=MediaType.VOICE,
            media=None,
        )

    media_type, media = await _resolve_media(tg_message)
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


async def _ping_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Lightweight health check in Telegram."""
    if update.message is not None:
        await update.message.reply_text("telegram-to-notion: ok")


def _make_handler(
    settings: Settings,
    writer: NotionWriter,
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]:
    """Build a handler that forwards each message to ``writer``."""

    async def handle(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if msg is None:
            return
        try:
            logger.info(
                "incoming message chat_id={} from_user={}",
                msg.chat_id,
                msg.from_user.id if msg.from_user else None,
            )
            incoming = await _build_message(settings, msg)
            enrichment = await interpret_message(settings, incoming)
            page_id = await writer.create_page(incoming, enrichment)
            logger.info("wrote notion page {} from {}", page_id, incoming.sender)
            await msg.reply_text(
                f"Saved to Notion.\nTitle: {incoming.title[:120]}\nPage id: {page_id}"
            )
        except APIResponseError as exc:
            logger.error("notion API error: {}", exc)
            detail = str(exc).replace("\n", " ").strip()
            if len(detail) > 450:
                detail = f"{detail[:447]}..."
            await msg.reply_text(
                "Notion API error:\n"
                f"{detail}\n"
                "If columns differ, rename them to match the README or set NOTION_TITLE_PROPERTY "
                "(e.g. Name). Check NOTION_DATABASE_ID from the database page URL."
            )
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            logger.exception("failed to forward telegram message to notion")
            await msg.reply_text("Could not forward to Notion. See server logs.")

    return handle


def build_application(settings: Settings) -> Application[Any, Any, Any, Any, Any, Any]:
    """Wire Telegram ``Application`` with Notion-backed message handlers."""
    notion_client = NotionClient(auth=settings.notion_token.get_secret_value())
    writer = NotionWriter(
        client=notion_client,
        database_id=settings.notion_database_id,
        data_source_id=settings.notion_data_source_id,
        title_property=settings.notion_title_property,
    )

    app = ApplicationBuilder().token(settings.telegram_bot_token.get_secret_value()).build()
    app.add_handler(CommandHandler("ping", _ping_cmd))
    handler = _make_handler(settings, writer)
    app.add_handler(
        MessageHandler(
            filters.TEXT
            | filters.PHOTO
            | filters.Document.ALL
            | filters.VIDEO
            | filters.ANIMATION
            | filters.VOICE,
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
