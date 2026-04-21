# AGENTS.md

This file is the working guide for contributors and coding agents in this repository.

## Project Snapshot

- Name: `Bakery-Audit`
- Runtime: Python Discord bot (`discord.py`)
- Primary purpose:
1. Parse bet screenshots from Discord mentions.
2. Support a standard extraction flow (`@bot` + images).
3. Support an odds automation flow (`@bot odds [real|bonus|both]` + images).
4. Write confirmations and odds pipeline outputs to Excel or Google Sheets.

## Repo Layout

- Entry point: `src/main.py`
- Core bot logic: `src/bot/app.py`
- Config loading: `src/bot/config.py`
- Gemini integration: `src/bot/gemini_client.py`
- Standard extraction UI: `src/bot/discord_ui.py`
- Odds models/pipeline/UI:
1. `src/bot/odds_models.py`
2. `src/bot/odds_pipeline.py`
3. `src/bot/odds_ui.py`
- Confirmation logging backend: `src/bot/confirmation_log.py`
- Session state stores: `src/bot/state.py`
- Tests: `tests/`
- Apps Script reference docs: `docs/google_apps_script/`

## Local Development

1. Create and activate a virtual environment.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Configure environment:
```bash
copy .env.example .env
```
4. Run:
```bash
python -m src.main
```
5. Test:
```bash
pytest
```

## Environment Variables

Required:
1. `DISCORD_TOKEN`
2. `GEMINI_API_KEY`

Gemini options:
1. `GEMINI_MODEL` (default `gemini-2.5-flash`)
2. `GEMINI_API_KEY_2` (optional fallback)
3. `GEMINI_API_KEY_SECONDARY` (optional fallback)
4. `GEMINI_API_KEY_BACKUP` (optional fallback)
5. `GEMINI_API_KEYS` (optional comma-separated list)

Logging:
1. `LOG_LEVEL` (default `INFO`)

Confirmation backend:
1. `CONFIRM_LOG_BACKEND` = `excel` or `google_sheets`
2. `CONFIRM_EXCEL_PATH` (excel mode)
3. `CONFIRM_GOOGLE_SHEET_ID` (google sheets mode)
4. `CONFIRM_GOOGLE_CREDENTIALS_JSON` (google sheets mode)
5. `CONFIRM_GOOGLE_WORKSHEET` (default `confirmed_bets`)

Currency display:
1. `USD_TO_CAD_RATE` (default `1.36`)

Odds pipeline:
1. `ODDS_ENABLED` (default `true`)
2. `ODDS_RAW_WORKSHEET` (default `odds_raw`)
3. `ODDS_CLEAN_WORKSHEET` (default `odds_clean`)
4. `ODDS_RANKED_WORKSHEET` (default `odds_ranked`)

## Command Behavior

Mention routing in `src/bot/app.py`:

1. `@bot help`
- Returns usage help text.

2. `@bot devlog`
- Sends `docs/DEVLOG.md` as attachment.

3. `@bot odds [real|bonus|both]` + image(s)
- Runs odds extraction flow.
- Creates review embed with preview/site breakdown.
- Requires button confirm before writing pipeline sheets.

4. `@bot` + image(s)
- Runs standard extraction flow.
- Creates editable extraction embed.
- Confirm writes selected fields to configured backend.

## Odds Pipeline Notes

Current clean/ranking logic (`src/bot/odds_pipeline.py`):

1. Moneyline rows only.
2. Builds opposite-side matchup pairs.
3. Uses cross-site pairs only (same-site fallback is not used).
4. Applies site minimum rule:
- `cloudbet`: any odds (`>= 1.0`)
- all other sites: min odds `>= 1.5`
5. Recommendation pool includes only rows marked `BET`.
6. Ranked outputs include top 2 by:
- ROI (desc)
- Profit/Net (desc)
- Rake (asc)

## Sheets Contracts

Standard confirm logging writes one row per confirmed bet with:
1. `date`
2. `team`
3. `against`
4. `odds`
5. `stake`
6. `return`

Odds pipeline worksheets:
1. raw tab headers: `RAW_HEADERS`
2. clean tab headers: `CLEAN_HEADERS`
3. ranked tab headers: `RANKED_HEADERS`

Do not change header order without updating readers/writers/tests.

## Gemini Parsing Constraints

`src/bot/gemini_client.py` drives both extraction modes.

When changing prompts/parsing:
1. Keep JSON-only expectation.
2. Preserve schema compatibility with `models.py` and `odds_models.py`.
3. Keep site attribution behavior explicit (candidate-level vs batch-level assumptions).
4. Keep multi-key failover behavior stable.

## Testing Expectations Before Merge

Minimum:
1. `pytest tests/test_app_help.py tests/test_gemini_client.py`
2. `pytest tests/test_odds_pipeline.py tests/test_odds_ui.py`

Preferred:
1. `pytest`

If changing command routing, parsing, or recommendation logic, add or update tests in the corresponding test modules.

## Change Safety Checklist

1. Do not commit secrets (`.env`, credential JSON).
2. Keep Discord interaction authorization invoker-only.
3. Preserve backward compatibility for existing commands.
4. For odds changes, validate:
- review embed still renders,
- confirm path still writes raw/clean/ranked,
- ranking output is non-empty only when rules allow.

## Deployment Reminder

When deploying via file sync, ensure you upload to the same path systemd runs from (check `WorkingDirectory` in service file) before restarting the bot.
