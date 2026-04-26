import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

import {
  auto,
  Presentation,
  PresentationFile,
  column,
  fill,
  fixed,
  fr,
  grid,
  hug,
  layers,
  panel,
  row,
  rule,
  shape,
  text,
  wrap,
} from "@oai/artifact-tool";

const require = createRequire(import.meta.url);
const artifactEntry = require.resolve("@oai/artifact-tool");
const skiaPath = require.resolve("skia-canvas", { paths: [path.dirname(artifactEntry)] });
const { Canvas } = await import(new URL(`file:///${skiaPath.replace(/\\/g, "/")}`));

const workspaceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputDir = path.join(workspaceRoot, "output");
const scratchDir = path.join(workspaceRoot, "scratch");
const previewDir = path.join(scratchDir, "previews");
const repoRoot = path.resolve(workspaceRoot, "..", "..", "..");
const finalDeckPath = path.join(repoRoot, "program_overview.pptx");

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const COLORS = {
  bg: "#FBF6EE",
  paper: "#FFFDF9",
  ink: "#1F1A17",
  muted: "#6D655D",
  line: "#D9CCBA",
  accent: "#C85C3D",
  teal: "#1D7B6E",
  gold: "#B18428",
  dark: "#222420",
  darkCard: "#302A24",
  rose: "#F6E0D8",
  mint: "#E7F3EE",
  sand: "#F5E9D3",
  slate: "#EDF1F6",
};

const fonts = {
  title: "Georgia",
  body: "Aptos",
};

const presentation = Presentation.create({
  slideSize: { width: 1920, height: 1080 },
});

function baseFrame() {
  return { frame: { left: 0, top: 0, width: 1920, height: 1080 }, baseUnit: 8 };
}

function lineStyle(color = COLORS.line, width = 1) {
  return { style: "solid", width, fill: color };
}

function eyebrow(value, color = COLORS.accent) {
  return text(value.toUpperCase(), {
    width: fill,
    height: hug,
    style: {
      fontFace: fonts.body,
      fontSize: 16,
      bold: true,
      color,
      characterSpacing: 2,
    },
  });
}

function titleText(value, width = wrap(1200), color = COLORS.ink, size = 58) {
  return text(value, {
    width,
    height: hug,
    style: {
      fontFace: fonts.title,
      fontSize: size,
      bold: true,
      color,
    },
  });
}

function subtitleText(value, width = wrap(900), color = COLORS.muted, size = 25) {
  return text(value, {
    width,
    height: hug,
    style: {
      fontFace: fonts.body,
      fontSize: size,
      color,
    },
  });
}

function bullet(value, color = COLORS.ink, size = 22) {
  return text(`- ${value}`, {
    width: fill,
    height: hug,
    style: {
      fontFace: fonts.body,
      fontSize: size,
      color,
    },
  });
}

function smallLabel(value, color = COLORS.muted) {
  return text(value.toUpperCase(), {
    width: fill,
    height: hug,
    style: {
      fontFace: fonts.body,
      fontSize: 14,
      bold: true,
      color,
      characterSpacing: 1.2,
    },
  });
}

function card(children, options = {}) {
  return panel(
    {
      width: options.width ?? fill,
      height: options.height ?? hug,
      padding: options.padding ?? { x: 24, y: 22 },
      fill: options.fill ?? COLORS.paper,
      line: options.line ?? lineStyle(COLORS.line, 1),
      borderRadius: "rounded-lg",
      columnSpan: options.columnSpan,
    },
    column(
      {
        width: fill,
        height: hug,
        gap: options.gap ?? 10,
      },
      children,
    ),
  );
}

function metric(value, label, accent) {
  return column(
    { width: fill, height: hug, gap: 8 },
    [
      text(value, {
        width: fill,
        height: hug,
        style: {
          fontFace: fonts.title,
          fontSize: 42,
          bold: true,
          color: accent,
        },
      }),
      smallLabel(label),
    ],
  );
}

function exampleRows(lines) {
  return column(
    { width: fill, height: hug, gap: 8 },
    lines.map((line) =>
      text(line, {
        width: fill,
        height: hug,
        style: {
          fontFace: fonts.body,
          fontSize: 20,
          color: COLORS.ink,
        },
      }),
    ),
  );
}

function addCoverSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.bg }),
        shape({ width: fixed(580), height: fixed(1080), fill: COLORS.dark }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(1.18), fr(0.82)],
            rows: [fr(1)],
            columnGap: 64,
            padding: { x: 86, y: 74 },
          },
          [
            column(
              { width: fill, height: hug, gap: 18, justify: "center" },
              [
                eyebrow("New Betting Odds Features"),
                titleText("Bakery-Audit Odds Automation", wrap(880), COLORS.ink, 82),
                subtitleText(
                  "A focused walkthrough of the newer moneyline, over/under, and spread analysis features.",
                  wrap(840),
                  COLORS.muted,
                  29,
                ),
                rule({ width: fixed(220), stroke: COLORS.accent, weight: 5 }),
                subtitleText(
                  "Built from the repository’s odds parsing, pairing, ranking, and Discord review flow.",
                  wrap(760),
                  COLORS.muted,
                  22,
                ),
              ],
            ),
            column(
              { width: fill, height: fill, gap: 18, justify: "end" },
              [
                card(
                  [
                    smallLabel("Focus"),
                    text("Only the newer odds features", {
                      width: fill,
                      height: hug,
                      style: {
                        fontFace: fonts.body,
                        fontSize: 26,
                        bold: true,
                        color: "#FFFFFF",
                      },
                    }),
                  ],
                  { fill: COLORS.darkCard, line: lineStyle("#5E5449", 1) },
                ),
                card(
                  [
                    bullet("Moneyline pairing + ranking", "#FFFFFF", 20),
                    bullet("O/U scenario-window logic", "#FFFFFF", 20),
                    bullet("Spread margin-window logic", "#FFFFFF", 20),
                    bullet("Updated market-first Discord output", "#FFFFFF", 20),
                  ],
                  { fill: COLORS.darkCard, line: lineStyle("#5E5449", 1), gap: 8 },
                ),
              ],
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

function addContextSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.paper }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(1.02), fr(0.98)],
            rows: [auto, fr(1)],
            columnGap: 56,
            rowGap: 30,
            padding: { x: 86, y: 70 },
          },
          [
            column(
              { width: fill, height: hug, gap: 14, columnSpan: 2 },
              [
                eyebrow("Why The Odds Flow Matters"),
                titleText("The newer work moves Bakery-Audit from logging bets to comparing odds opportunities."),
              ],
            ),
            card(
              [
                text("Before the newer odds work", {
                  width: fill,
                  height: hug,
                  style: { fontFace: fonts.title, fontSize: 34, bold: true, color: COLORS.accent },
                }),
                bullet("Primary flow was screenshot extraction plus confirmation logging."),
                bullet("Great for record-keeping, but not built for comparing sportsbooks."),
                bullet("No dedicated totals or spread recommendation logic."),
              ],
              { fill: COLORS.rose },
            ),
            card(
              [
                text("After the newer odds work", {
                  width: fill,
                  height: hug,
                  style: { fontFace: fonts.title, fontSize: 34, bold: true, color: COLORS.teal },
                }),
                bullet("`@bot odds [real|bonus|both]` triggers a dedicated automation flow."),
                bullet("The bot extracts market-specific odds candidates from screenshots."),
                bullet("It pairs opposite sides across sites, scores them, ranks them, and writes three sheet stages."),
                bullet("Final Discord output now shows one best pick each for moneyline, O/U, and spread."),
              ],
              { fill: COLORS.mint },
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

function addWorkflowSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.bg }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(1), fr(1), fr(1), fr(1), fr(1)],
            rows: [auto, fr(1), auto],
            columnGap: 18,
            rowGap: 26,
            padding: { x: 86, y: 70 },
          },
          [
            column(
              { width: fill, height: hug, gap: 14, columnSpan: 5 },
              [
                eyebrow("Odds Workflow"),
                titleText("The new odds flow has a clear input -> pairing -> ranking -> output sequence."),
              ],
            ),
            card([text("1", { width: fill, height: hug, style: { fontFace: fonts.title, fontSize: 44, bold: true, color: COLORS.accent } }), bullet("User sends `@bot odds real|bonus|both` with screenshots.", COLORS.ink, 20)], { fill: COLORS.rose, gap: 12 }),
            card([text("2", { width: fill, height: hug, style: { fontFace: fonts.title, fontSize: 44, bold: true, color: COLORS.gold } }), bullet("Gemini extracts `OddsCandidate` rows with market, site, odds, and line fields.", COLORS.ink, 20)], { fill: COLORS.sand, gap: 12 }),
            card([text("3", { width: fill, height: hug, style: { fontFace: fonts.title, fontSize: 44, bold: true, color: COLORS.teal } }), bullet("Models normalize dates, team codes, sites, totals, and spreads.", COLORS.ink, 20)], { fill: COLORS.mint, gap: 12 }),
            card([text("4", { width: fill, height: hug, style: { fontFace: fonts.title, fontSize: 44, bold: true, color: "#58739A" } }), bullet("Discord shows an invoker-only review embed before confirmation.", COLORS.ink, 20)], { fill: COLORS.slate, gap: 12 }),
            card([text("5", { width: fill, height: hug, style: { fontFace: fonts.title, fontSize: 44, bold: true, color: COLORS.accent } }), bullet("Confirm writes raw, clean, and ranked sheets, then returns best market picks.", COLORS.ink, 20)], { fill: "#F3E7DD", gap: 12 }),
            card(
              [
                row(
                  { width: fill, height: hug, gap: 24 },
                  [
                    metric("odds_raw", "stage 1 extracted rows", COLORS.accent),
                    metric("odds_clean", "stage 2 paired rows", COLORS.teal),
                    metric("odds_ranked", "stage 3 recommendations", COLORS.gold),
                  ],
                ),
              ],
              { fill: COLORS.paper, columnSpan: 5, padding: { x: 28, y: 22 } },
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

function addMoneylineSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.paper }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(1), fr(1)],
            rows: [auto, fr(1)],
            columnGap: 48,
            rowGap: 26,
            padding: { x: 86, y: 70 },
          },
          [
            column(
              { width: fill, height: hug, gap: 14, columnSpan: 2 },
              [
                eyebrow("New Feature: Moneyline"),
                titleText("Moneyline now has dedicated pairing, workbook-style calculations, and ranking."),
              ],
            ),
            card(
              [
                bullet("Gemini extracts rows as `market=\"moneyline\"`."),
                bullet("`build_clean_rows(...)` groups opposite sides of the same matchup on the same date."),
                bullet("`_pick_best_site_pair(...)` rejects same-site pairs and chooses the best cross-site direction."),
                bullet("Moneyline uses workbook-style formulas for hedge, profit, ROI, and rake."),
                bullet("Bonus mode now blocks Cloudbet as the bonus side."),
              ],
              { fill: COLORS.rose },
            ),
            card(
              [
                smallLabel("Code-Backed Example"),
                text("TOR @ 3.81 vs CLE @ 1.28", {
                  width: fill,
                  height: hug,
                  style: { fontFace: fonts.title, fontSize: 38, bold: true, color: COLORS.ink },
                }),
                exampleRows([
                  "Bet side: TOR on xbet",
                  "Hedge side: CLE on cloudbet",
                  "Base stake: 100.00",
                  "Real hedge: 297.66",
                  "Bonus profit: 61.47",
                  "Bonus ROI: 28.0%",
                  "Recommendation: BET",
                ]),
              ],
              { fill: "#FFF8F3" },
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

function addOUSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.bg }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(1), fr(1)],
            rows: [auto, fr(1)],
            columnGap: 48,
            rowGap: 26,
            padding: { x: 86, y: 70 },
          },
          [
            column(
              { width: fill, height: hug, gap: 14, columnSpan: 2 },
              [
                eyebrow("New Feature: Over / Under"),
                titleText("Totals bets are evaluated as score windows instead of a simple win/lose pair."),
              ],
            ),
            card(
              [
                bullet("Gemini extracts totals as `total_over` / `total_under` with `total_line`."),
                bullet("The bot pairs Over and Under across different sites for the same game."),
                bullet("`_optimize_ou_hedge_stake(...)` maximizes the worst-case outcome."),
                bullet("`_ou_profit_outcomes(...)` evaluates buckets below, at, between, and above the lines."),
                bullet("If only same-site pairs exist, the review embed explains why there is no pick."),
              ],
              { fill: COLORS.mint },
            ),
            card(
              [
                smallLabel("Code-Backed Example"),
                text("OVER 222.5 vs UNDER 223.5", {
                  width: fill,
                  height: hug,
                  style: { fontFace: fonts.title, fontSize: 38, bold: true, color: COLORS.ink },
                }),
                exampleRows([
                  "Chosen bet side: OVER 222.5 @ 1.93",
                  "Hedge side: UNDER 223.5 @ 1.90",
                  "Optimized hedge: 101.58",
                  "Worst case: -8.58",
                  "Middle window (222.5, 223.5): 184.42",
                  "The feature’s value is the protected middle-score window.",
                ]),
              ],
              { fill: "#F7FCFA" },
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

function addSpreadSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.paper }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(1), fr(1)],
            rows: [auto, fr(1)],
            columnGap: 48,
            rowGap: 26,
            padding: { x: 86, y: 70 },
          },
          [
            column(
              { width: fill, height: hug, gap: 14, columnSpan: 2 },
              [
                eyebrow("New Feature: Spread"),
                titleText("Spread bets add margin-based pairing and line-window analysis."),
              ],
            ),
            card(
              [
                bullet("Gemini extracts `market=\"spread\"` plus signed `spread_line`."),
                bullet("The bot pairs opposite spread sides across sites for the same matchup."),
                bullet("`_optimize_spread_hedge_stake(...)` solves for the strongest downside protection."),
                bullet("`_spread_profit_outcomes(...)` checks outcomes around the spread thresholds."),
                bullet("Spread results can expose middle-margin windows when two lines leave room in between."),
              ],
              { fill: COLORS.sand },
            ),
            card(
              [
                smallLabel("Code-Backed Example"),
                text("MIN -1.5 vs DAL +2.5", {
                  width: fill,
                  height: hug,
                  style: { fontFace: fonts.title, fontSize: 38, bold: true, color: COLORS.ink },
                }),
                exampleRows([
                  "The helper evaluates margin outcomes around 1.5 and 2.5",
                  "Optimized hedge from the spread helper: 143.66",
                  "Worst case: -39.66",
                  "At lower line 1.5: 60.34",
                  "Middle window (1.5, 2.5): 164.34",
                  "This is the line-sensitive behavior spread logic adds.",
                ]),
              ],
              { fill: "#FFF9F1" },
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

function addRankingSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.bg }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(1.05), fr(0.95)],
            rows: [auto, fr(1)],
            columnGap: 54,
            rowGap: 28,
            padding: { x: 86, y: 70 },
          },
          [
            column(
              { width: fill, height: hug, gap: 14, columnSpan: 2 },
              [
                eyebrow("Ranking + Output Changes"),
                titleText("The recent work also improved recommendation quality and the final Discord presentation."),
              ],
            ),
            card(
              [
                bullet("`select_top_recommendations(...)` now skips games already used by earlier metric buckets."),
                bullet("Site attribution is preserved more aggressively per screenshot and can backfill from image names."),
                bullet("Rake / edge sign was aligned to the workbook display: `1 - implied probability sum`."),
                bullet("Moneyline bonus instructions are suppressed when the bet site is Cloudbet."),
              ],
              { fill: COLORS.slate },
            ),
            card(
              [
                text("Visible product change", {
                  width: fill,
                  height: hug,
                  style: { fontFace: fonts.title, fontSize: 36, bold: true, color: COLORS.teal },
                }),
                bullet("Old: multi-page odds result view", COLORS.ink, 21),
                bullet("New: one market-first recommendations embed", COLORS.ink, 21),
                bullet("Output fields: Best Moneyline, Best O/U, Best Spread", COLORS.ink, 21),
                bullet("Result: faster scanning for non-technical reviewers and operators", COLORS.ink, 21),
              ],
              { fill: COLORS.mint },
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

function addExampleSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.paper }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(0.9), fr(1), fr(0.9)],
            rows: [auto, fr(1)],
            columnGap: 24,
            rowGap: 28,
            padding: { x: 86, y: 70 },
          },
          [
            column(
              { width: fill, height: hug, gap: 14, columnSpan: 3 },
              [
                eyebrow("Example End-To-End"),
                titleText("One odds request can produce reviewable outputs for all three new markets."),
              ],
            ),
            card(
              [
                smallLabel("Input"),
                bullet("Screenshot A: TOR/CLE moneyline"),
                bullet("Screenshot B: TOR/CLE total"),
                bullet("Screenshot C: MIN/DAL spread"),
                bullet("User sends `@bot odds both`"),
              ],
              { fill: COLORS.rose },
            ),
            card(
              [
                smallLabel("Processing"),
                bullet("Gemini returns `OddsCandidate` rows"),
                bullet("Dates, teams, sites, odds, totals, and spread lines are normalized"),
                bullet("Cross-site opposite sides are paired"),
                bullet("Moneyline, O/U, and spread are ranked separately"),
              ],
              { fill: COLORS.sand },
            ),
            card(
              [
                smallLabel("Output"),
                bullet("Discord review embed before confirmation"),
                bullet("Best Moneyline / Best O/U / Best Spread after confirmation"),
                bullet("Sheet writes to `odds_raw`, `odds_clean`, `odds_ranked`"),
                bullet("Counts of raw, clean, and ranked rows returned to the user"),
              ],
              { fill: COLORS.mint },
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

function addClosingSlide() {
  const slide = presentation.slides.add();
  slide.compose(
    layers(
      { width: fill, height: fill },
      [
        shape({ width: fill, height: fill, fill: COLORS.dark }),
        grid(
          {
            width: fill,
            height: fill,
            columns: [fr(1.04), fr(0.96)],
            rows: [auto, fr(1)],
            columnGap: 48,
            rowGap: 28,
            padding: { x: 86, y: 74 },
          },
          [
            column(
              { width: fill, height: hug, gap: 14, columnSpan: 2 },
              [
                eyebrow("Technical Highlights / Impact", "#DAB982"),
                titleText("The newer odds features are the strongest product step-change in the repository.", wrap(1260), "#FFFFFF", 58),
              ],
            ),
            column(
              { width: fill, height: fill, gap: 14 },
              [
                bullet("Strict JSON odds prompt keeps extraction structured.", "#FFFFFF", 22),
                bullet("`OddsCandidate` makes market, site, total, and spread fields explicit.", "#FFFFFF", 22),
                bullet("Cross-site pairing prevents weak same-site comparisons.", "#FFFFFF", 22),
                bullet("Per-market optimization gives each bet type its own logic instead of one generic ranking rule.", "#FFFFFF", 22),
                bullet("The new Discord summary makes the results presentation-ready.", "#FFFFFF", 22),
              ],
            ),
            column(
              { width: fill, height: fill, gap: 22, justify: "between" },
              [
                row(
                  { width: fill, height: hug, gap: 20 },
                  [
                    card([metric("3 markets", "moneyline, O/U, spread", "#E9A38B")], { fill: COLORS.darkCard, line: lineStyle("#5E5449", 1) }),
                    card([metric("1 summary", "best pick per market", "#7CCFC1")], { fill: COLORS.darkCard, line: lineStyle("#5E5449", 1) }),
                  ],
                ),
                card(
                  [
                    text("Bottom line", {
                      width: fill,
                      height: hug,
                      style: { fontFace: fonts.body, fontSize: 16, bold: true, color: "#D8BE95" },
                    }),
                    text("Bakery-Audit now does more than read betting slips. It compares odds, finds structured opportunities, and explains the best pick by market.", {
                      width: wrap(760),
                      height: hug,
                      style: { fontFace: fonts.title, fontSize: 34, bold: true, color: "#FFFFFF" },
                    }),
                  ],
                  { fill: COLORS.darkCard, line: lineStyle("#5E5449", 1), padding: { x: 26, y: 24 } },
                ),
              ],
            ),
          ],
        ),
      ],
    ),
    baseFrame(),
  );
}

addCoverSlide();
addContextSlide();
addWorkflowSlide();
addMoneylineSlide();
addOUSlide();
addSpreadSlide();
addRankingSlide();
addExampleSlide();
addClosingSlide();

for (let i = 0; i < presentation.slides.items.length; i += 1) {
  const canvas = new Canvas(1920, 1080);
  const ctx = canvas.getContext("2d");
  const pngBuffer = await canvas.toBuffer("png");
  const previewPath = path.join(previewDir, `slide-${String(i + 1).padStart(2, "0")}.png`);
  await fs.writeFile(previewPath, pngBuffer);
}

const pptxBlob = await PresentationFile.exportPptx(presentation);
const workspaceDeckPath = path.join(outputDir, "output.pptx");
await pptxBlob.save(workspaceDeckPath);
await fs.copyFile(workspaceDeckPath, finalDeckPath);

console.log(
  JSON.stringify(
    {
      slides: presentation.slides.items.length,
      workspaceDeckPath,
      finalDeckPath,
      previewDir,
    },
    null,
    2,
  ),
);
