# AGENTS.md

This is the operating guide for coding agents and contributors working in Bakery-Audit. Keep changes small, verified, and easy for the next agent to continue.

## Mission

Bakery-Audit is a Discord bot that turns betting screenshots into reviewed spreadsheet rows. It has two main flows:

1. Standard extraction: `@bot` plus screenshots creates editable bet embeds and logs confirmed rows.
2. Odds automation: `@bot odds [real|bonus|both]` plus screenshots extracts moneyline candidates, builds cross-site pairs, ranks opportunities, and writes raw, clean, and ranked worksheet tabs.

## Engineering Principles

- SOLID: keep responsibilities narrow. Parsing, Discord UI, state, and persistence should stay in separate modules.
- DRY: reuse domain helpers when behavior is truly shared, especially for parsing, normalization, and spreadsheet headers.
- YAGNI: do not add speculative abstractions, providers, commands, or config flags before a real use case exists.
- KISS: prefer direct data flow and explicit contracts over clever indirection.
- Agentic iteration: optimize for fast orientation, small diffs, deterministic tests, and clear rollback points.

## Repository Map

- `src/main.py`: process entry point and dependency wiring.
- `src/bot/app.py`: Discord event routing and command behavior.
- `src/bot/config.py`: environment loading and typed settings.
- `src/bot/gemini_client.py`: Gemini calls and JSON parsing contracts.
- `src/bot/models.py`: standard extraction models.
- `src/bot/odds_models.py`: odds automation models.
- `src/bot/discord_ui.py`: standard extraction embeds, buttons, and modals.
- `src/bot/odds_ui.py`: odds review embeds and confirmation UI.
- `src/bot/odds_pipeline.py`: odds cleaning, pairing, ranking, and sheet writes.
- `src/bot/confirmation_log.py`: Excel and Google Sheets confirmation logging.
- `src/bot/state.py`: pending Discord interaction state.
- `tests/`: pytest coverage for command routing, parsing, UI, state, and pipeline behavior.
- `docs/`: devlog, architecture notes, and project documentation.
- `apps-script/`: standalone Google Apps Script spreadsheet helpers.

## Local Workflow

```bash
pip install -r requirements.txt
copy .env.example .env
python -m src.main
pytest
```

Required environment variables:

- `DISCORD_TOKEN`
- `GEMINI_API_KEY`

Do not commit `.env`, service account JSON, spreadsheet exports, Discord tokens, Gemini keys, or generated data files.

## Command Contracts

- `@bot help` returns concise usage help.
- `@bot devlog` sends `docs/DEVLOG.md` as an attachment.
- `@bot` plus image attachments runs standard extraction.
- `@bot odds [real|bonus|both]` plus image attachments runs odds automation.

Mention routing lives in `src/bot/app.py`. Keep routing changes backward compatible unless the user explicitly asks for a command break.

## Spreadsheet Contracts

Standard confirmation rows write these columns in this order:

1. `date`
2. `team`
3. `against`
4. `odds`
5. `stake`
6. `return`

Odds worksheets use the `RAW_HEADERS`, `CLEAN_HEADERS`, and `RANKED_HEADERS` constants in `src/bot/odds_pipeline.py`.

Header order is an external contract. If you change it, update every reader, writer, test, and doc in the same PR.

## Gemini Contracts

When changing Gemini prompts or parsing:

- Preserve JSON-only responses.
- Preserve schema compatibility with `models.py` and `odds_models.py`.
- Keep multi-key failover behavior stable.
- Keep site attribution explicit for odds candidates.
- Add tests around parsing edge cases before changing behavior.

## Testing Expectations

Run the focused tests for the area you changed. Before merging, prefer the full suite:

```bash
pytest
```

Minimum focused coverage:

- Command routing or help text: `pytest tests/test_app_help.py`
- Gemini parsing: `pytest tests/test_gemini_client.py`
- Standard extraction UI: `pytest tests/test_currency_display.py tests/test_confirmation_log.py`
- Odds pipeline: `pytest tests/test_odds_pipeline.py tests/test_pair_detection.py`
- Odds UI: `pytest tests/test_odds_ui.py`

## Change Safety Checklist

- Keep Discord edit and confirm controls invoker-only.
- Keep spreadsheet writes explicit and test-covered.
- Keep generated output out of Git.
- Keep Apps Script reference files in `apps-script/`, not under `docs/`.
- Update `docs/DEVLOG.md` when behavior changes.
- Do not update `docs/DEVLOG.md` for pure documentation or file organization changes unless the user asks for changelog noise.

## Deployment Notes

Production deployments may rely on a systemd `WorkingDirectory`. When deploying manually, sync files to the exact directory used by the service before restarting the bot.
