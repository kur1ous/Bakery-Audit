/**
 * S3
 * Run daily at ~3:30 AM (installable time trigger).
 * Passes yesterday's date to S4.
 */
function s3_runDailyYesterday() {
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const ymd = Utilities.formatDate(yesterday, TZ, 'yyyy-MM-dd');
  s4_processPairsForDate(ymd);
}

/**
 * Manual helper: run pairs/clean pipeline for today.
 */
function runTodayNow() {
  s4_processPairsForDate(todayYmd_());
}

/**
 * Manual helper: run pairs/clean pipeline.
 * - If ymd is provided, uses it.
 * - If ymd is omitted, uses TEST_DATE (or today if TEST_DATE is blank).
 */
function runPairsForDate(ymd) {
  const targetDate = resolveTargetYmd_(ymd);
  s4_processPairsForDate(targetDate);
}

/**
 * Manual helper: run everything for one date.
 * - If ymd is omitted, uses TEST_DATE (or today if TEST_DATE is blank).
 */
function runAllForDate(ymd) {
  const targetDate = resolveTargetYmd_(ymd);
  findMatchedPairsForDate(targetDate);
  s4_processPairsForDate(targetDate);
  s7_resolveWinnersForDate(targetDate);
}

/**
 * Optional helper: create trigger programmatically.
 */
function s3_createTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 's3_runDailyYesterday')
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger('s3_runDailyYesterday')
    .timeBased()
    .everyDays(1)
    .atHour(3)
    .nearMinute(30)
    .create();
}
