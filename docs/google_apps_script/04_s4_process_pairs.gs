/**
 * S4
 * Finds matched_pairs rows for targetDate, loops and calls S5 for each pair.
 */
function s4_processPairsForDate(targetDate) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const matched = ss.getSheetByName(MATCHED_SHEET_NAME);
  if (!matched) throw new Error(`Sheet not found: ${MATCHED_SHEET_NAME}`);

  const values = matched.getDataRange().getValues();
  if (values.length < 2) return;

  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    const betDate = normalizeDateString_(row[2]);
    if (betDate !== targetDate) continue;

    const pair = {
      pairKey: String(row[0] || '').trim(),
      betDate,
      teamA: String(row[3] || '').trim(),
      againstA: String(row[4] || '').trim(),
      oddsA: toNumber_(row[5]),
      stakeA: toNumber_(row[6]),
      returnA: toNumber_(row[7]),
      rawBetA: String(row[8] || '').trim(),
      teamB: String(row[9] || '').trim(),
      againstB: String(row[10] || '').trim(),
      oddsB: toNumber_(row[11]),
      stakeB: toNumber_(row[12]),
      returnB: toNumber_(row[13]),
      rawBetB: String(row[14] || '').trim()
    };

    s5_writeCleanRow(pair);
  }
}

function toNumber_(value) {
  if (value === null || value === undefined || value === '') return null;
  const cleaned = String(value).replace(/[^0-9.-]/g, '');
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}
