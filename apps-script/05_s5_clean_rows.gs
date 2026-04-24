/**
 * S5
 * Writes ONE cleaned row per matchup/date into clean_bets.
 * Dedupes by canonical matchup key so DET/TOR and TOR/DET do NOT duplicate.
 */
function s5_writeCleanRow(pair) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = getOrCreateCleanSheet_(ss, CLEAN_SHEET_NAME);

  const teamA = toTeamCode_(pair.teamA);
  const againstA = toTeamCode_(pair.againstA);
  const teamB = toTeamCode_(pair.teamB);
  const againstB = toTeamCode_(pair.againstB);

  const canonicalKey = `${pair.betDate}|${[teamA, againstA].sort().join('|')}`;

  const lastRow = sh.getLastRow();
  const existingCanon = new Set(
    lastRow > 1
      ? sh.getRange(2, 22, lastRow - 1, 1).getValues().flat().map(String)
      : []
  );
  if (existingCanon.has(canonicalKey)) return;

  const pairKey = pair.pairKey || buildFallbackPairKey_(pair);
  const dateDisplay = toDisplayDate_(pair.betDate);

  // If source values are CAD and you want USD columns converted, apply rate here.
  const stakeAUsd = pair.stakeA;
  const returnAUsd = pair.returnA;
  const stakeBUsd = pair.stakeB;
  const returnBUsd = pair.returnB;

  sh.appendRow([
    pairKey, dateDisplay, pair.rawBetA, pair.rawBetB,
    teamA, againstA, pair.oddsA, pair.stakeA, pair.returnA,
    teamB, againstB, pair.oddsB, pair.stakeB, pair.returnB,
    stakeAUsd, returnAUsd, stakeBUsd, returnBUsd,
    '', '', '',
    canonicalKey
  ]);
}

function getOrCreateCleanSheet_(ss, name) {
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);

  if (sh.getLastRow() === 0) {
    sh.appendRow([
      'pair_key', 'Date', 'Raw Bet A', 'Raw Bet B',
      'Team A', 'Against A', 'Odds A', 'Stake A (CAD)', 'Return A (CAD)',
      'Team B', 'Against B', 'Odds B', 'Stake B (CAD)', 'Return B (CAD)',
      'Stake A (USD)', 'Return A (USD)', 'Stake B (USD)', 'Return B (USD)',
      'Winner', 'Result', 'Profit', 'canonical_key'
    ]);
  }
  return sh;
}

function toDisplayDate_(ymd) {
  const d = new Date(`${ymd}T00:00:00`);
  if (isNaN(d.getTime())) return ymd;
  return Utilities.formatDate(d, TZ, 'dd-MMM');
}

function buildFallbackPairKey_(pair) {
  return `${pair.betDate}|${pair.teamA}|${pair.againstA}|${pair.rawBetA}|${pair.rawBetB}`;
}

function toTeamCode_(name) {
  const s = String(name || '').trim().toLowerCase();
  const map = {
    'detroit pistons': 'DET', 'toronto raptors': 'TOR', 'new york knicks': 'NY',
    'memphis grizzlies': 'MEM', 'miami heat': 'MIA', 'boston celtics': 'BOS',
    'orlando magic': 'ORL', 'phoenix suns': 'PHX', 'chicago bulls': 'CHI',
    'indiana pacers': 'IND'
  };
  if (map[s]) return map[s];

  const token = s.replace(/[^a-z0-9\s]/g, ' ').trim().split(/\s+/)[0] || '';
  return token.substring(0, 3).toUpperCase() || String(name || '').trim();
}
