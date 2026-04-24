# Architecture

Bakery-Audit is intentionally small. The fastest way to keep it powerful for human and agent contributors is to preserve clear module boundaries and external contracts.

## Runtime Flow

1. Discord receives a message that mentions the bot.
2. `src/bot/app.py` routes the message to help, devlog, standard extraction, or odds extraction.
3. `src/bot/gemini_client.py` sends image bytes to Gemini and parses strict JSON into Pydantic models.
4. Discord UI modules build review embeds and invoker-only confirmation controls.
5. Confirmed data is written to Excel or Google Sheets.

## Standard Extraction Flow

The standard flow handles `@bot` plus one or more screenshots.

- Models: `src/bot/models.py`
- UI: `src/bot/discord_ui.py`
- State: `PendingBetStore` in `src/bot/state.py`
- Persistence: `src/bot/confirmation_log.py`

Confirmed rows intentionally stay narrow: date, team, against, odds, stake, and return.

## Odds Automation Flow

The odds flow handles `@bot odds [real|bonus|both]` plus one or more screenshots.

- Models: `src/bot/odds_models.py`
- UI: `src/bot/odds_ui.py`
- State: `PendingOddsStore` in `src/bot/state.py`
- Pipeline: `src/bot/odds_pipeline.py`

The pipeline writes three stages:

1. Raw extracted candidates.
2. Clean paired rows.
3. Ranked recommendations.

Ranking currently focuses on moneyline candidates, opposite-side matchup pairs, cross-site pairs, and the configured site minimum odds rules.

## Spreadsheet and Apps Script

Python code owns the Discord extraction and primary spreadsheet writes. Google Apps Script helpers live in `apps-script/` because they are spreadsheet-side automation references, not documentation pages.

Use Apps Script when the workflow belongs inside the spreadsheet, such as trigger-based pairing, daily cleanup, or resolving winners from an external scoreboard. Keep bot runtime behavior in Python.

## Design Principles

- Keep responsibilities separate. A UI change should not require touching Gemini parsing or persistence unless the contract changes.
- Keep data contracts explicit. Header names, header order, command names, and model fields are integration points.
- Prefer simple typed data over implicit dictionaries at module boundaries.
- Add abstraction only when it removes real duplication or isolates a volatile dependency.
- Keep tests close to the behavior they protect.

## Extension Guidelines

When adding a command:

1. Add routing in `src/bot/app.py`.
2. Put command-specific UI in its own UI module if it has persistent views or modals.
3. Add focused tests for routing and user-visible behavior.

When changing parsing:

1. Update the relevant model first.
2. Update Gemini prompt expectations.
3. Add tests for valid JSON, malformed JSON, and schema edge cases.

When changing spreadsheet output:

1. Update header constants and writers together.
2. Update docs and Apps Script assumptions if affected.
3. Add or update tests that assert output columns and row values.
