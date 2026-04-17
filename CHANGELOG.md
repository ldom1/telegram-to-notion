# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-04-17

### Fixed

- **Notion `pages.create` parent** for databases that expose `data_sources`: use
  `type: data_source_id` (schema-matching source, or `NOTION_DATA_SOURCE_ID`) so properties resolve.
- **`NOTION_DATABASE_ID`** accepts 32-char hex from Notion URLs (auto-normalize to dashed UUID).
- **`NOTION_TITLE_PROPERTY`** when the title column is not named `Title` (e.g. Notion’s `Name`).
- **Telegram feedback:** reply on success/failure; `/ping` command; log incoming `chat_id`.
- **OpenRouter:** HTTP call capped with a **45s** `asyncio.wait_for` timeout (falls back to heuristics).

### Added

- **OpenRouter LLM enrichment** for Notion row fields: `Title`, `Label`, `Type`, `URL`,
  `Description`, `Interest` (default model `google/gemini-2.5-flash-lite`). Heuristic fallback
  when `OPENROUTER_API_KEY` is unset.
- `NotionEnrichment` model and `telegram_to_notion/openrouter.py`.

### Changed

- **faster-whisper** (`>=1.2.1`) is a **default** project dependency again (voice works after
  `uv sync` only; no separate dependency group).

## [0.2.0] - 2026-04-17

### Added

- **Voice messages:** Telegram voice notes are downloaded and transcribed locally with
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (optional `transcribe` dependency
  group; no API key). Notion `Media type` value `voice`.
- `telegram_to_notion/transcribe.py` and `media/voice.py`.
- Optional settings `WHISPER_LANGUAGE` (default `fr`) and `WHISPER_MODEL_SIZE` (default `base`).
- This changelog.

## [0.1.0] - 2026-04-17

### Added

- Initial release: long-polling Telegram bot forwarding text, photos, documents, videos, and
  animations to a Notion database via `file_upload` and structured properties.
