/**
 * S6
 * Runs daily around 4:30 AM, resolves winners for yesterday.
 */
function s6_runResolveWinnersYesterday() {
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const ymd = Utilities.formatDate(yesterday, TZ, 'yyyy-MM-dd');
  s7_resolveWinnersForDate(ymd);
}

/**
 * Manual helper: resolve winners for today.
 */
function runResolveTodayNow() {
  s7_resolveWinnersForDate(todayYmd_());
}

/**
 * Manual helper: resolve winners for one date.
 * - If ymd is omitted, uses TEST_DATE (or today if TEST_DATE is blank).
 */
function runResolveForDate(ymd) {
  const targetDate = resolveTargetYmd_(ymd);
  s7_resolveWinnersForDate(targetDate);
}

/**
 * Optional helper: create 4:30 AM trigger once.
 */
function s6_createTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 's6_runResolveWinnersYesterday')
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger('s6_runResolveWinnersYesterday')
    .timeBased()
    .everyDays(1)
    .atHour(4)
    .nearMinute(30)
    .create();
}
