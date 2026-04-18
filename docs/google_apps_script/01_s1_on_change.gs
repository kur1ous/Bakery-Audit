/**
 * S1
 * Trigger entrypoint. Install as: From spreadsheet -> On change
 */
function onBotSheetChange(e) {
  const today = Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
  findMatchedPairsForDate(today);
}
