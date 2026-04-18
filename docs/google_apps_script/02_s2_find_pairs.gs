/**
 * S2
 * Looks only at rows matching targetDate (yyyy-MM-dd),
 * finds opposite-side pairs, and logs unique matches to MATCHED_SHEET_NAME.
 */
function findMatchedPairsForDate(targetDate) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const source = ss.getSheetByName(SOURCE_SHEET_NAME);
  if (!source) throw new Error(`Sheet not found: ${SOURCE_SHEET_NAME}`);

  const matched = getOrCreateMatchedSheet_(ss, MATCHED_SHEET_NAME);
  const values = source.getDataRange().getValues();
  if (values.length < 2) return;

  const rows = [];
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    const dateStr = normalizeDateString_(row[0]);
    if (dateStr !== targetDate) continue;

    const teamNorm = normalizeTeam_(row[1]);
    const againstNorm = normalizeTeam_(row[2]);
    if (!teamNorm || !againstNorm) continue;

    rows.push({
      rowNumber: r + 1,
      date: dateStr,
      teamRaw: String(row[1] || '').trim(),
      againstRaw: String(row[2] || '').trim(),
      teamNorm,
      againstNorm,
      odds: row[3],
      stake: row[4],
      ret: row[5]
    });
  }

  if (!rows.length) return;

  const existingKeys = new Set(
    matched.getLastRow() > 1
      ? matched.getRange(2, 1, matched.getLastRow() - 1, 1).getValues().flat().map(String)
      : []
  );

  const grouped = new Map();
  for (const bet of rows) {
    const matchupKey = canonicalMatchupKey_(bet.date, bet.teamNorm, bet.againstNorm);
    if (!grouped.has(matchupKey)) grouped.set(matchupKey, []);
    grouped.get(matchupKey).push(bet);
  }

  const output = [];
  for (const [, bets] of grouped) {
    const bySide = new Map();
    for (const b of bets) {
      const sideKey = `${b.teamNorm}|${b.againstNorm}`;
      if (!bySide.has(sideKey)) bySide.set(sideKey, []);
      bySide.get(sideKey).push(b);
    }

    for (const [sideAKey, sideAList] of bySide.entries()) {
      const [aTeam, aAgainst] = sideAKey.split('|');
      const sideBKey = `${aAgainst}|${aTeam}`;
      if (!bySide.has(sideBKey)) continue;

      const sideBList = bySide.get(sideBKey);
      sideAList.sort((x, y) => x.rowNumber - y.rowNumber);
      sideBList.sort((x, y) => x.rowNumber - y.rowNumber);

      const pairCount = Math.min(sideAList.length, sideBList.length);
      for (let i = 0; i < pairCount; i++) {
        const a = sideAList[i];
        const b = sideBList[i];
        const lowRow = Math.min(a.rowNumber, b.rowNumber);
        const highRow = Math.max(a.rowNumber, b.rowNumber);

        const pairKey = `${a.date}|${aTeam}|${aAgainst}|${lowRow}|${highRow}`;
        if (existingKeys.has(pairKey)) continue;
        existingKeys.add(pairKey);

        output.push([
          pairKey,
          new Date(),
          a.date,
          a.teamRaw, a.againstRaw, a.odds, a.stake, a.ret, a.rowNumber,
          b.teamRaw, b.againstRaw, b.odds, b.stake, b.ret, b.rowNumber
        ]);
      }
    }
  }

  if (output.length) {
    matched.getRange(matched.getLastRow() + 1, 1, output.length, output[0].length).setValues(output);
  }
}

function getOrCreateMatchedSheet_(ss, name) {
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);

  if (sh.getLastRow() === 0) {
    sh.appendRow([
      'pair_key', 'logged_at', 'bet_date',
      'team_a', 'against_a', 'odds_a', 'stake_a', 'return_a', 'source_row_a',
      'team_b', 'against_b', 'odds_b', 'stake_b', 'return_b', 'source_row_b'
    ]);
  }
  return sh;
}

function normalizeDateString_(v) {
  const s = String(v || '').trim();
  if (!s) return '';

  const m = s.match(/^(\d{4})[-/](\d{2})[-/](\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;

  const d = new Date(s);
  if (isNaN(d.getTime())) return '';
  return Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
}

function canonicalMatchupKey_(date, t1, t2) {
  const teams = [t1, t2].sort();
  return `${date}|${teams[0]}|${teams[1]}`;
}

function normalizeTeam_(v) {
  let s = String(v || '').trim().toLowerCase();
  s = s.replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();

  const prefixes = {
    'atl ': 'atlanta ', 'bos ': 'boston ', 'bkn ': 'brooklyn ', 'cha ': 'charlotte ',
    'chi ': 'chicago ', 'cle ': 'cleveland ', 'dal ': 'dallas ', 'den ': 'denver ',
    'det ': 'detroit ', 'gs ': 'golden state ', 'hou ': 'houston ', 'ind ': 'indiana ',
    'lac ': 'la clippers ', 'lal ': 'la lakers ', 'mem ': 'memphis ', 'mia ': 'miami ',
    'mil ': 'milwaukee ', 'min ': 'minnesota ', 'nop ': 'new orleans ', 'ny ': 'new york ',
    'nyk ': 'new york ', 'okc ': 'oklahoma city ', 'orl ': 'orlando ', 'phi ': 'philadelphia ',
    'phx ': 'phoenix ', 'por ': 'portland ', 'sac ': 'sacramento ', 'sas ': 'san antonio ',
    'tor ': 'toronto ', 'uta ': 'utah ', 'wsh ': 'washington '
  };

  for (const k in prefixes) {
    if (s.startsWith(k)) {
      s = prefixes[k] + s.slice(k.length);
      break;
    }
  }
  return s;
}
