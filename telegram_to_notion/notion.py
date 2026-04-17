"""Notion API wrapper for database page creation and file uploads."""

import asyncio
from typing import Any, cast

import httpx
from notion_client import Client

from telegram_to_notion.models import IncomingMessage, MediaPayload, NotionEnrichment


class NotionWriter:  # pylint: disable=too-few-public-methods
    """Create Notion database pages from ``IncomingMessage`` values (text + file uploads)."""

    def __init__(self, client: Client, database_id: str) -> None:
        self._client = client
        self._database_id = database_id

    async def create_page(self, message: IncomingMessage, enrichment: NotionEnrichment) -> str:
        """Create a page in the configured database; returns the new page id."""
        file_upload_id: str | None = None
        if message.media is not None:
            file_upload_id = await self._upload_file(message.media)

        properties = self._build_properties(message, enrichment)
        children = self._build_children(message, enrichment, file_upload_id)

        response = await asyncio.to_thread(
            self._client.pages.create,
            parent={"database_id": self._database_id},
            properties=properties,
            children=children,
        )
        return response["id"]  # type: ignore[index,no-any-return]

    async def _upload_file(self, payload: MediaPayload) -> str:
        """Start a Notion file upload, POST bytes to the upload URL, return upload id."""
        upload = cast(dict[str, Any], await asyncio.to_thread(self._client.file_uploads.create))
        upload_id: str = upload["id"]
        upload_url: str = upload["upload_url"]

        async with httpx.AsyncClient(timeout=60.0) as http:
            auth_token = cast(str, self._client.options.auth)
            resp = await http.post(
                upload_url,
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Notion-Version": "2022-06-28",
                },
                files={"file": (payload.filename, payload.content, payload.mime_type)},
            )
            resp.raise_for_status()
        return upload_id

    @staticmethod
    def _rich(text: str) -> dict[str, Any]:
        """Notion rich_text property value (truncated)."""
        chunk = (text or "")[:2000]
        if not chunk:
            return {"rich_text": []}
        return {"rich_text": [{"type": "text", "text": {"content": chunk}}]}

    @staticmethod
    def _build_properties(message: IncomingMessage, enrichment: NotionEnrichment) -> dict[str, Any]:
        """Database row properties: Title, Label, Type, URL, Description, Interest, metadata."""
        props: dict[str, Any] = {
            "Title": {"title": [{"text": {"content": enrichment.title[:2000]}}]},
            "Label": NotionWriter._rich(enrichment.label),
            "Type": NotionWriter._rich(enrichment.entry_type),
            "Description": NotionWriter._rich(enrichment.description[:2000]),
            "Interest": NotionWriter._rich(enrichment.interest),
            "Sender": NotionWriter._rich(message.sender),
            "Date": {"date": {"start": message.sent_at.isoformat()}},
            "Media type": {"select": {"name": message.media_type.value}},
        }
        if enrichment.url and enrichment.url.strip():
            props["URL"] = {"url": enrichment.url.strip()[:2000]}
        return props

    @staticmethod
    def _build_children(
        message: IncomingMessage,
        enrichment: NotionEnrichment,
        file_upload_id: str | None,
    ) -> list[dict[str, Any]]:
        """Page body blocks: optional paragraph, optional file/image/video block."""
        blocks: list[dict[str, Any]] = []
        body_text = (message.body or enrichment.description or "").strip()
        if body_text:
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": body_text[:2000]}}]
                    },
                }
            )
        if file_upload_id is not None and message.media is not None:
            block_type = _notion_block_for_mime(message.media.mime_type)
            blocks.append(
                {
                    "object": "block",
                    "type": block_type,
                    block_type: {
                        "type": "file_upload",
                        "file_upload": {"id": file_upload_id},
                    },
                }
            )
        return blocks


def _notion_block_for_mime(mime_type: str) -> str:
    """Map a MIME type to a Notion block type (image, video, audio, or generic file)."""
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type.startswith("audio/"):
        return "audio"
    return "file"
