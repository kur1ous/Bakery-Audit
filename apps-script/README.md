# Apps Script Helpers

This folder contains Google Apps Script helpers for spreadsheet-side automation. These scripts are separate from the Python Discord bot and are kept at the repository root so they are not confused with project documentation.

## Files

- `00_config.gs`: shared sheet names, timezone, currency rate, and date helpers.
- `01_s1_on_change.gs`: trigger entry point for sheet changes.
- `02_s2_find_pairs.gs`: finds opposite-side pairs for a target date.
- `03_s3_daily_pairs.gs`: daily wrapper for pair detection.
- `04_s4_process_pairs.gs`: processes matched pairs into clean rows.
- `05_s5_clean_rows.gs`: normalizes clean-row values and USD amounts.
- `06_s6_winner_trigger.gs`: trigger wrapper for winner resolution.
- `07_s7_resolve_winners.gs`: resolves NBA winners from ESPN scoreboard data and updates clean rows.

## Spreadsheet Assumptions

Default sheet names are defined in `00_config.gs`:

- `confirmed_bets`
- `matched_pairs`
- `clean_bets`

The source `confirmed_bets` sheet is expected to match the bot confirmation contract:

1. date
2. team
3. against
4. odds
5. stake
6. return

## Installation

1. Open the target Google Sheet.
2. Go to Extensions, then Apps Script.
3. Copy these `.gs` files into the Apps Script project in numeric order.
4. Review `00_config.gs` and adjust sheet names, timezone behavior, and `CAD_TO_USD_RATE` if needed.
5. Configure triggers for the wrapper functions you want to run automatically.

Keep Apps Script edits small and mirrored back into this folder so spreadsheet automation remains reviewable in Git.
