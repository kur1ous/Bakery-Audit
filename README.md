# Bakery-Audit

Discord bot for extracting bet slip fields from screenshots using Gemini 2.5 Flash.

## Features
- Mention-driven trigger (`@bot` + image attachment)
- Mention help command (`@bot help`)
- Multi-image parsing in one message
- Combined embed output with date, team, against, odds, stake, return (USD base)
- Invoker-only edit + confirm controls`r`n- Currency toggle button (`Switch to CAD` / `Switch to USD`) for display conversion
- Hedge/arb pair flag for opposite sides of the same matchup
- Confirm logging to spreadsheet (Excel default, Google Sheets optional)

## Setup
1. Create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set:
   - `DISCORD_TOKEN`
   - `GEMINI_API_KEY`
   - optional `GEMINI_MODEL` (default: `gemini-2.5-flash`)
   - `CONFIRM_LOG_BACKEND` = `excel` or `google_sheets`\r\n   - optional `USD_TO_CAD_RATE` (default: `1.36`)

### Excel backend (default)
- `CONFIRM_EXCEL_PATH` (default: `data/confirmed_bets.xlsx`)

### Google Sheets backend
- `CONFIRM_GOOGLE_SHEET_ID`
- `CONFIRM_GOOGLE_CREDENTIALS_JSON` (path to service account JSON)
- `CONFIRM_GOOGLE_WORKSHEET` (default: `confirmed_bets`)

## Run
```bash
python -m src.main
```

## Confirm Log Columns
Each confirmed bet writes one row with only:
- `date`
- `team`
- `against`
- `odds`
- `stake`
- `return`

## Test
```bash
pytest
```