"""Interpret Telegram payloads for Notion rows via OpenRouter chat completions."""

import asyncio
import json
import re
from typing import Any

import httpx
from loguru import logger
from pydantic import ValidationError

from telegram_to_notion.config import Settings
from telegram_to_notion.models import IncomingMessage, NotionEnrichment

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _merge_enrichment(base: NotionEnrichment, data: dict[str, Any]) -> NotionEnrichment:
    """Overlay parsed LLM keys onto ``base`` (validated)."""
    merged: dict[str, Any] = dict(base.model_dump(by_alias=True))
    for key in ("title", "label", "type", "url", "description", "interest"):
        if key not in data:
            continue
        val = data[key]
        if val is None:
            if key == "url":
                merged[key] = None
            continue
        if isinstance(val, str) and val.strip() == "":
            continue
        merged[key] = val
    return NotionEnrichment.model_validate(merged)


async def interpret_message(settings: Settings, incoming: IncomingMessage) -> NotionEnrichment:
    """Ask OpenRouter for Notion fields; on error or missing key use ``from_incoming``."""
    base = NotionEnrichment.from_incoming(incoming)
    key = settings.openrouter_api_key
    if key is None or not key.get_secret_value().strip():
        return base

    system = (
        "You help file Telegram messages into a Notion database. Reply with ONLY a JSON object, "
        "no markdown fences, using these keys: "
        '"title" (string, concise page title), '
        '"label" (short tag e.g. work, personal, finance, idea), '
        '"type" (one of: note, task, link, media, question, other), '
        '"url" (string URL or null if none), '
        '"description" (1-3 sentences summarizing the message for humans), '
        '"interest" (one of: Low, Medium, High). '
        "Use the user's language when appropriate. "
        f"Telegram sender: {incoming.sender}. "
        f"Media channel: {incoming.media_type.value}. "
        f"Raw text/caption:\n{incoming.body[:12000]}"
    )
    payload: dict[str, Any] = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "Produce the JSON object now."},
        ],
    }
    headers = {
        "Authorization": f"Bearer {key.get_secret_value()}",
        "Content-Type": "application/json",
    }
    if settings.openrouter_http_referer:
        headers["HTTP-Referer"] = settings.openrouter_http_referer
    if settings.openrouter_app_title:
        headers["X-OpenRouter-Title"] = settings.openrouter_app_title

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await asyncio.wait_for(
                client.post(OPENROUTER_URL, headers=headers, json=payload),
                timeout=45.0,
            )
            resp.raise_for_status()
            body = resp.json()
        raw_content = body["choices"][0]["message"]["content"]
        if isinstance(raw_content, list):
            parts = [p.get("text", "") for p in raw_content if isinstance(p, dict)]
            raw_content = "".join(parts)
        if not isinstance(raw_content, str):
            logger.warning("OpenRouter returned unexpected content type")
            return base
        parsed = json.loads(_strip_json_fence(raw_content))
        if not isinstance(parsed, dict):
            return base
        return _merge_enrichment(base, parsed)
    except (
        asyncio.TimeoutError,
        httpx.HTTPError,
        json.JSONDecodeError,
        KeyError,
        ValidationError,
        TypeError,
    ) as exc:
        logger.warning("OpenRouter enrichment failed, using heuristics: {}", exc)
        return base
