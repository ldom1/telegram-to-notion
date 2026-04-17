# telegram-to-notion

Self-hosted Telegram → Notion bridge. A Telegram bot listens for messages (text,
photos, documents, videos, GIFs, **voice notes**) via long polling and forwards each one as a
structured page into a Notion database. Voice is transcribed locally with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (optional install).
Optional [OpenRouter](https://openrouter.ai/) (`google/gemini-2.5-flash-lite` by default) fills
**Title**, **Label**, **Type**, **URL**, **Description**, and **Interest** from each message;
without `OPENROUTER_API_KEY`, the same columns are filled with simple heuristics.

No HTTP server. No webhooks. No third-party SaaS.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A [Notion internal integration](https://www.notion.so/my-integrations) token
- A Notion database shared with that integration, containing the properties:
  - `Title` (title)
  - `Label` (rich text)
  - `Type` (rich text) — LLM or heuristic “kind” (e.g. note, link, media)
  - `URL` (url) — set when a link is detected or proposed by the LLM
  - `Description` (rich text)
  - `Interest` (rich text) — e.g. Low / Medium / High
  - `Sender` (rich text) — Telegram username or display name
  - `Date` (date)
  - `Media type` (select with options: `text`, `photo`, `document`, `video`, `animation`, `voice`)

## Setup

```bash
cp .env.example .env
# edit .env: TELEGRAM_BOT_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID; optional OPENROUTER_API_KEY
uv sync
# optional: local voice transcription (faster-whisper; downloads model on first use)
uv sync --group transcribe
```

## Run

```bash
uv run python -m telegram_to_notion
```

The bot will begin long-polling. Send it a message in Telegram and a new page
should appear in your Notion database.

## Deploy (devbox, systemd user)

The bot runs on **`devbox`** under your user as **`telegram-to-notion.service`**
(user systemd, `loginctl` linger is enabled so it stays up after logout).

- **Repo on server:** `~/Lab/dom-telegram-to-notion`
- **Secrets:** `.env` in that directory (not in git). After editing locally, copy again if needed:  
  `scp .env devbox:/home/lgiron/Lab/dom-telegram-to-notion/.env`

**Update the running bot after you push from your laptop:**

```bash
ssh devbox 'cd ~/Lab/dom-telegram-to-notion && git pull && ~/.local/bin/uv sync --group transcribe && systemctl --user restart telegram-to-notion.service'
```

**Logs / status:**

```bash
ssh devbox 'systemctl --user status telegram-to-notion.service'
ssh devbox 'journalctl --user -u telegram-to-notion.service -f'
```

## Development

```bash
uv run pytest tests/unit -v              # unit tests only (no network)
uv run pytest tests/integration -v       # live Notion (needs repo-root .env)
uv run pytest tests/unit tests/integration -v  # everything
uv run ruff check .
uv run ruff format --check .
PYLINTHOME=.pylint_cache uv run pylint telegram_to_notion --fail-under=9.5
uv run mypy telegram_to_notion
```

## Project layout

```
telegram_to_notion/
├── config.py      # Pydantic settings (env var validation)
├── models.py      # Internal Pydantic data types
├── notion.py      # Notion page + file_upload wrapper
├── openrouter.py  # Optional LLM enrichment via OpenRouter
├── transcribe.py  # faster-whisper wrapper (optional dependency group)
├── bot.py         # Telegram polling + handlers
└── media/         # Per-media-type extractors + shared downloader
```
