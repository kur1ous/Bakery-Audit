# Betting Odds Features Deck

## 1. Bakery-Audit Odds Automation
- Focused on the newer odds-analysis capabilities
- Covers moneyline, over/under, and spread logic
- Designed for non-technical viewers

## 2. Why The Odds Flow Matters
- The older flow logged confirmed bets
- The newer odds flow compares opportunities across sportsbooks
- It turns screenshots into ranked, reviewable market picks

## 3. Odds Workflow
- User sends `@bot odds [real|bonus|both]` with screenshots
- Gemini extracts `OddsCandidate` rows with market, site, odds, and line data
- Discord shows an odds review embed before confirmation
- Confirm writes raw, clean, and ranked sheet tabs
- Bot returns best pick by market

## 4. New Feature: Moneyline
- Extracts `market="moneyline"` candidates
- Groups opposite sides of the same matchup by date
- Rejects same-site pairs
- Picks the best cross-site bet/hedge direction
- Applies bonus restrictions, including no Cloudbet bonus side
- Example: TOR 3.81 @ xbet vs CLE 1.28 @ cloudbet

## 5. New Feature: Over / Under
- Extracts `total_over` / `total_under` plus `total_line`
- Pairs Over and Under across sites for the same game
- Optimizes hedge size with `_optimize_ou_hedge_stake(...)`
- Evaluates worst case, push points, and middle windows
- Example: OVER 222.5 vs UNDER 223.5

## 6. New Feature: Spread
- Extracts `market="spread"` plus signed `spread_line`
- Pairs opposite spread sides across sites
- Optimizes hedge size with `_optimize_spread_hedge_stake(...)`
- Evaluates margin buckets around the spread thresholds
- Example: MIN -1.5 vs DAL +2.5

## 7. Ranking + Output Changes
- Ranking skips duplicate games across metric buckets
- Site attribution is preserved per screenshot more aggressively
- Rake/edge sign now matches the workbook display
- Final UX changed from multi-page results to one best pick per market

## 8. Example End-To-End
- Inputs: moneyline, total, and spread screenshots from different sportsbooks
- System normalizes teams, dates, sites, odds, and lines
- Cross-site pairs are formed and filtered by site rules
- Moneyline, O/U, and spread are ranked separately
- Discord outputs Best Moneyline, Best O/U, and Best Spread
- Sheets store raw rows, cleaned pairs, and ranked recommendations

## 9. Technical Highlights / Impact
- Strict JSON Gemini prompt for structured odds extraction
- Typed odds model keeps market fields explicit
- Cross-site pairing logic prevents weak same-site comparisons
- New market coverage expands the bot from logging bets to comparing opportunities
