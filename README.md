# telegram-to-notion

Self-hosted Telegram → Notion bridge. A Telegram bot listens for messages (text,
photos, documents, videos, GIFs) via long polling and forwards each one as a
structured page into a Notion database.

No HTTP server. No webhooks. No third-party SaaS.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A [Notion internal integration](https://www.notion.so/my-integrations) token
- A Notion database shared with that integration, containing the properties:
  - `Title` (title)
  - `Sender` (rich text)
  - `Date` (date)
  - `Media type` (select with options: `text`, `photo`, `document`, `video`, `animation`)

## Setup

```bash
cp .env.example .env
# edit .env and fill in TELEGRAM_BOT_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID
uv sync
```

## Run

```bash
uv run python -m telegram_to_notion
```

The bot will begin long-polling. Send it a message in Telegram and a new page
should appear in your Notion database.

## Development

```bash
uv run pytest           # test suite
uv run ruff check .     # lint
uv run mypy telegram_to_notion  # type-check
```

## Project layout

```
telegram_to_notion/
├── config.py      # Pydantic settings (env var validation)
├── models.py      # Internal Pydantic data types
├── notion.py      # Notion page + file_upload wrapper
├── bot.py         # Telegram polling + handlers
└── media/         # Per-media-type extractors + shared downloader
```
