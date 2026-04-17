"""Notion API wrapper for database page creation and file uploads."""

import asyncio
from typing import Any, cast

import httpx
from loguru import logger
from notion_client import Client
from notion_client.errors import APIResponseError, UnknownHTTPResponseError

from telegram_to_notion.models import IncomingMessage, MediaPayload, NotionEnrichment


def _required_notion_property_names(title_key: str) -> frozenset[str]:
    """Property names that must exist on the data source for ``pages.create`` to succeed."""
    return frozenset(
        {
            title_key,
            "Label",
            "Type",
            "Description",
            "Interest",
            "Sender",
            "Date",
            "Media type",
        }
    )


class NotionWriter:  # pylint: disable=too-few-public-methods
    """Create Notion database pages from ``IncomingMessage`` values (text + file uploads)."""

    def __init__(
        self,
        client: Client,
        database_id: str,
        *,
        data_source_id: str | None = None,
        title_property: str = "Title",
    ) -> None:
        self._client = client
        self._database_id = database_id
        self._data_source_id_override = (data_source_id or "").strip() or None
        self._title_property = (title_property or "Title").strip() or "Title"
        self._cached_parent: dict[str, Any] | None = None

    def _required_props(self) -> frozenset[str]:
        return _required_notion_property_names(self._title_property)

    async def _pick_data_source_id(self, db: dict[str, Any]) -> str | None:
        """Pick a data source id whose schema includes all columns this bridge writes."""
        sources = db.get("data_sources") or []
        if not isinstance(sources, list) or not sources:
            return None
        required = self._required_props()
        summaries: list[str] = []
        for entry in sources:
            ds_id = str(entry.get("id", "")).strip()
            if not ds_id:
                continue
            try:
                detail = cast(
                    dict[str, Any],
                    await asyncio.to_thread(self._client.data_sources.retrieve, ds_id),
                )
            except (APIResponseError, UnknownHTTPResponseError, httpx.HTTPError) as exc:
                logger.warning("notion data_sources.retrieve failed for {}: {}", ds_id, exc)
                continue
            props = detail.get("properties") or {}
            names = set(props) if isinstance(props, dict) else set()
            sample = sorted(names)[:12]
            tail = "…" if len(names) > 12 else ""
            summaries.append(f"{ds_id[:8]}… keys={sample}{tail}")
            if required <= names:
                logger.info(
                    "using notion data_source_id={} (schema matches bridge properties)",
                    ds_id,
                )
                return ds_id
        if summaries:
            logger.warning(
                "no notion data source matched required columns {}; tried: {}",
                sorted(required),
                "; ".join(summaries),
            )
        first = str(sources[0].get("id", "")).strip()
        if first:
            logger.warning("falling back to first notion data_source_id={}", first)
        return first or None

    async def _resolve_parent(self) -> dict[str, Any]:
        """Build ``parent`` for ``pages.create`` (database vs data source per Notion 2025+)."""
        if self._cached_parent is not None:
            return self._cached_parent

        if self._data_source_id_override:
            self._cached_parent = {
                "type": "data_source_id",
                "data_source_id": self._data_source_id_override,
            }
            return self._cached_parent

        db = cast(
            dict[str, Any],
            await asyncio.to_thread(
                self._client.databases.retrieve, database_id=self._database_id
            ),
        )
        db_id = str(db.get("id", self._database_id))

        ds_id = await self._pick_data_source_id(db)
        if ds_id:
            self._cached_parent = {"type": "data_source_id", "data_source_id": ds_id}
            return self._cached_parent

        self._cached_parent = {"type": "database_id", "database_id": db_id}
        return self._cached_parent

    async def create_page(self, message: IncomingMessage, enrichment: NotionEnrichment) -> str:
        """Create a page in the configured database; returns the new page id."""
        file_upload_id: str | None = None
        if message.media is not None:
            file_upload_id = await self._upload_file(message.media)

        properties = self._build_properties(message, enrichment)
        children = self._build_children(message, enrichment, file_upload_id)
        parent = await self._resolve_parent()

        response = await asyncio.to_thread(
            self._client.pages.create,
            parent=parent,
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

    def _build_properties(
        self, message: IncomingMessage, enrichment: NotionEnrichment
    ) -> dict[str, Any]:
        """Database row properties: title column, Label, Type, URL, Description, Interest."""
        desc = enrichment.description.strip()
        if enrichment.source and enrichment.source.strip():
            desc = f"{desc}\n\nSource: {enrichment.source.strip()}".strip()
        props: dict[str, Any] = {
            self._title_property: {
                "title": [{"text": {"content": enrichment.title[:2000]}}],
            },
            "Label": self._rich(enrichment.label),
            "Type": self._rich(enrichment.entry_type),
            "Description": self._rich(desc[:2000]),
            "Interest": self._rich(enrichment.interest),
            "Sender": self._rich(message.sender),
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
