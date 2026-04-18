# Development Log

Last Updated: 2026-04-18
Owner: Bread Audit bot project

## Update Policy
- This file is the source-of-truth changelog for implemented behavior.
- Update this file whenever a feature is added, removed, or behavior changes.
- The `@bot devlog` command returns this file directly.

## Current Feature Set
1. Mention-based invocation.
2. Image parsing with Gemini 2.5 Flash using strict JSON extraction.
3. Multi-image parsing in one message.
4. Combined extraction embed output.
5. Invoker-only controls for edit and confirm.
6. Per-bet selector when multiple bets are detected.
7. Hedge/arb pair detection for opposite sides of same matchup.
8. Date normalization to `yyyy-mm-dd`.
9. Confirmation logging to spreadsheet backends:
   - Excel (`openpyxl`)
   - Google Sheets (`gspread` + service account)
10. Help command (`@bot help`).
11. Devlog command (`@bot devlog`).
12. Cancel button for extraction confirmation UI.
13. Phase 2 command: `@bot odds` with confirm/cancel automation flow.

## Command Behavior
- `@bot help`
  - Returns concise usage steps and command references.
- `@bot devlog`
  - Attaches `docs/DEVLOG.md` in-channel.
- `@bot` + image attachment(s)
  - Runs extraction pipeline and posts editable embed.
- `@bot odds` + image attachment(s)
  - Runs moneyline odds extraction review and waits for `Confirm Odds`.
  - On confirm: writes raw/clean/ranked tabs and posts top picks.

## Spreadsheet Logging Details
- Phase 1 (`confirmed_bets`): date/team/against/odds/stake/return + numeric stake/return.
- Phase 2 (same spreadsheet, new tabs by env):
  - `ODDS_RAW_WORKSHEET` (default `odds_raw`)
  - `ODDS_CLEAN_WORKSHEET` (default `odds_clean`)
  - `ODDS_RANKED_WORKSHEET` (default `odds_ranked`)

## Recent Changes

### 2026-04-18
- Implemented phase-2 odds automation command `@bot odds`.
- Added dedicated Gemini multi-row moneyline extraction contract.
- Added odds-specific pending session store and invoker-only confirm/cancel view.
- Added odds pipeline writer for Google Sheets stages:
  - Stage 1 raw rows
  - Stage 2 cleaned paired rows
  - Stage 3 ranked rows
- Added top-pick summary output (Top 2 ROI, Top 2 Profit, Top 2 Rake lowest).
- Added new env variables for odds worksheets and enable flag.

### 2026-04-06
- Deployment stabilized on DigitalOcean/CentOS with systemd service and externalized env file.

### 2026-04-03
- Confirmation logging now writes team and against as 3-letter codes.
- Date normalization fallback finalized to today when parse is uncertain.
