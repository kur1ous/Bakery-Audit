const SOURCE_SHEET_NAME = 'confirmed_bets';
const MATCHED_SHEET_NAME = 'matched_pairs';
const CLEAN_SHEET_NAME = 'clean_bets';
const TZ = Session.getScriptTimeZone();
const CAD_TO_USD_RATE = 0.73; // adjust as needed

// Optional global test date for manual runs. Keep '' to use today's date.
// Format: yyyy-MM-dd
const TEST_DATE = '';

function isValidYmd_(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value || '').trim());
}

function todayYmd_() {
  return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
}

function testOrTodayYmd_() {
  if (isValidYmd_(TEST_DATE)) return String(TEST_DATE).trim();
  return todayYmd_();
}

function resolveTargetYmd_(candidate) {
  const raw = String(candidate || '').trim();
  if (!raw) return testOrTodayYmd_();
  if (!isValidYmd_(raw)) throw new Error(`Invalid date '${raw}'. Use yyyy-MM-dd.`);
  return raw;
}
