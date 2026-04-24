# Bakery-Audit

Discord bot for extracting betting slip fields from screenshots, reviewing the parsed data in Discord, and writing confirmed rows to a spreadsheet backend.

The bot also includes an odds automation flow for moneyline screenshots. That flow extracts candidate rows, builds opposite-side pairs, ranks opportunities, and writes raw, clean, and ranked worksheet outputs.

## What It Does

- Responds to direct bot mentions in Discord.
- Parses one or more image attachments with Gemini.
- Shows editable Discord embeds before anything is logged.
- Keeps confirmation controls limited to the invoking user.
- Logs confirmed bets to Excel by default or Google Sheets when configured.
- Supports a separate `@bot odds [real|bonus|both]` workflow for moneyline opportunity review.
- Sends the project devlog with `@bot devlog`.

## Repository Layout

```text
apps-script/        Google Apps Script spreadsheet automation helpers
docs/               project notes, devlog, and architecture docs
src/main.py         application entry point
src/bot/            Discord bot, Gemini parsing, UI, state, and logging code
tests/              pytest coverage for bot behavior and pipeline rules
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Copy the example environment file and fill in required secrets.

```bash
copy .env.example .env
```

Required values:

- `DISCORD_TOKEN`
- `GEMINI_API_KEY`

Common optional values:

- `GEMINI_MODEL` defaults to `gemini-2.5-flash`.
- `CONFIRM_LOG_BACKEND` is `excel` or `google_sheets`.
- `CONFIRM_EXCEL_PATH` defaults to `data/confirmed_bets.xlsx`.
- `USD_TO_CAD_RATE` defaults to `1.36`.

Google Sheets mode also requires:

- `CONFIRM_GOOGLE_SHEET_ID`
- `CONFIRM_GOOGLE_CREDENTIALS_JSON`
- `CONFIRM_GOOGLE_WORKSHEET`, defaulting to `confirmed_bets`.

## Run

```bash
python -m src.main
```

## Discord Commands

- `@bot help` shows usage help.
- `@bot devlog` attaches `docs/DEVLOG.md`.
- `@bot` with image attachments runs standard bet extraction.
- `@bot odds [real|bonus|both]` with image attachments runs odds automation.

## Spreadsheet Contracts

Confirmed bet rows write these fields in order:

1. `date`
2. `team`
3. `against`
4. `odds`
5. `stake`
6. `return`

Odds automation writes to worksheet names controlled by:

- `ODDS_RAW_WORKSHEET`
- `ODDS_CLEAN_WORKSHEET`
- `ODDS_RANKED_WORKSHEET`

Do not reorder spreadsheet headers without updating readers, writers, and tests together.

## Tests

```bash
pytest
```

For architecture and contribution guidance, see `docs/ARCHITECTURE.md` and `AGENTS.md`.
