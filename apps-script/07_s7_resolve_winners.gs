/**
 * S7
 * Updates clean_bets Winner/Result/Profit for rows matching targetDate (yyyy-MM-dd)
 * using ESPN NBA scoreboard API for that date.
 */
function s7_resolveWinnersForDate(targetDate) {
  targetDate = resolveTargetYmd_(targetDate);

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(CLEAN_SHEET_NAME);
  if (!sh) throw new Error(`Sheet not found: ${CLEAN_SHEET_NAME}`);

  const values = sh.getDataRange().getValues();
  if (values.length < 2) return;

  const header = values[0];
  const idx = indexMap_(header);
  const need = ['Date', 'Team A', 'Against A', 'Stake A (USD)', 'Return A (USD)', 'Stake B (USD)', 'Return B (USD)', 'Winner', 'Result', 'Profit'];
  for (const c of need) {
    if (idx[c] == null) throw new Error(`Missing column: ${c}`);
  }

  const winnersMap = fetchEspnWinnersMap_(targetDate);
  const updates = [];

  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    const rowDate = normalizeDateFromDisplay_(row[idx['Date']], targetDate);
    if (rowDate !== targetDate) continue;

    const teamA = normalizeTeamCode_(row[idx['Team A']]);
    const againstA = normalizeTeamCode_(row[idx['Against A']]);
    if (!teamA || !againstA) continue;

    const key = matchupKey_(teamA, againstA);
    const winner = winnersMap.get(key);
    if (!winner) continue;

    const stakeA = toNum_(row[idx['Stake A (USD)']]);
    const retA = toNum_(row[idx['Return A (USD)']]);
    const stakeB = toNum_(row[idx['Stake B (USD)']]);
    const retB = toNum_(row[idx['Return B (USD)']]);

    let result = '';
    let profit = '';

    if (winner === teamA) {
      result = round2_(retA);
      profit = round2_(retA - stakeA - stakeB);
    } else if (winner === againstA) {
      result = round2_(retB);
      profit = round2_(retB - stakeA - stakeB);
    } else {
      continue;
    }

    updates.push({ row: r + 1, winner, result, profit });
  }

  for (const u of updates) {
    sh.getRange(u.row, idx['Winner'] + 1).setValue(u.winner);
    sh.getRange(u.row, idx['Result'] + 1).setValue(u.result);
    sh.getRange(u.row, idx['Profit'] + 1).setValue(u.profit);
  }
}

function fetchEspnWinnersMap_(ymd) {
  const ymdNoDash = ymd.replace(/-/g, '');
  const url = `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=${ymdNoDash}`;
  const resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  const status = resp.getResponseCode();
  if (status !== 200) return new Map();

  const payload = JSON.parse(resp.getContentText());
  const events = Array.isArray(payload.events) ? payload.events : [];
  const winners = new Map();

  for (const ev of events) {
    const comps = Array.isArray(ev.competitions) ? ev.competitions : [];
    for (const comp of comps) {
      const competitors = Array.isArray(comp.competitors) ? comp.competitors : [];
      if (competitors.length < 2) continue;

      const a = competitors[0];
      const b = competitors[1];
      const aCode = normalizeTeamCode_((a.team && (a.team.abbreviation || a.team.displayName || '')) || '');
      const bCode = normalizeTeamCode_((b.team && (b.team.abbreviation || b.team.displayName || '')) || '');
      const aScore = Number(a.score);
      const bScore = Number(b.score);

      if (!aCode || !bCode || isNaN(aScore) || isNaN(bScore) || aScore === bScore) continue;

      const statusType = (((comp.status || {}).type || {}).name || '').toUpperCase();
      if (statusType && statusType !== 'STATUS_FINAL') continue;

      const winner = aScore > bScore ? aCode : bCode;
      winners.set(matchupKey_(aCode, bCode), winner);
    }
  }

  return winners;
}

function indexMap_(headerRow) {
  const m = {};
  for (let i = 0; i < headerRow.length; i++) m[String(headerRow[i]).trim()] = i;
  return m;
}

function matchupKey_(a, b) {
  return [normalizeTeamCode_(a), normalizeTeamCode_(b)].sort().join('|');
}

function toNum_(v) {
  const n = Number(String(v == null ? '' : v).replace(/,/g, '').trim());
  return isNaN(n) ? 0 : n;
}

function round2_(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

function normalizeDateFromDisplay_(v, targetDate) {
  const s = String(v || '').trim();
  if (!s) return '';

  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

  const m = s.match(/^(\d{1,2})-([A-Za-z]{3})$/);
  if (m) {
    const year = String(targetDate || '').slice(0, 4) || Utilities.formatDate(new Date(), TZ, 'yyyy');
    const d = new Date(`${m[1]} ${m[2]} ${year}`);
    if (!isNaN(d.getTime())) return Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
  }

  const d = new Date(s);
  if (isNaN(d.getTime())) return '';
  return Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
}

function normalizeTeamCode_(v) {
  const s = String(v || '').trim().toUpperCase();
  const map = {
    ATL: 'ATL', BKN: 'BKN', BOS: 'BOS', CHA: 'CHA', CHI: 'CHI', CLE: 'CLE',
    DAL: 'DAL', DEN: 'DEN', DET: 'DET', GS: 'GS', GSW: 'GS', HOU: 'HOU',
    IND: 'IND', LAC: 'LAC', LAL: 'LAL', MEM: 'MEM', MIA: 'MIA', MIL: 'MIL',
    MIN: 'MIN', NO: 'NO', NOP: 'NO', NY: 'NY', NYK: 'NY', OKC: 'OKC',
    ORL: 'ORL', PHI: 'PHI', PHO: 'PHX', PHX: 'PHX', POR: 'POR', SAC: 'SAC',
    SA: 'SA', SAS: 'SA', TOR: 'TOR', UTA: 'UTA', WAS: 'WAS'
  };
  return map[s] || s;
}
