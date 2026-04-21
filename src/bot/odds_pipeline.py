from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .odds_models import OddsCandidate


RAW_HEADERS = [
    "logged_at",
    "session_id",
    "message_id",
    "channel_id",
    "guild_id",
    "invoker_user_id",
    "date",
    "team",
    "against",
    "odds",
    "market",
    "site",
    "source_image",
    "confidence",
    "missing_fields",
]

CLEAN_HEADERS = [
    "logged_at",
    "session_id",
    "date",
    "underdog_team",
    "favorite_team",
    "odds_underdog",
    "odds_favorite",
    "site_underdog",
    "site_favorite",
    "b_stake",
    "h_hedge",
    "total_bet",
    "total_return",
    "net",
    "roi",
    "rake",
    "recommendation",
]

RANKED_HEADERS = [
    "logged_at",
    "session_id",
    "metric",
    "rank",
    "date",
    "bet_team",
    "hedge_team",
    "bet_site",
    "hedge_site",
    "odds_bet",
    "odds_hedge",
    "b_stake",
    "h_hedge",
    "total_bet",
    "total_return",
    "net",
    "roi",
    "rake",
    "recommendation",
]


@dataclass(frozen=True)
class OddsPipelineContext:
    session_id: str
    message_id: int
    channel_id: int
    guild_id: int | None
    invoker_user_id: int


@dataclass(frozen=True)
class OddsRecommendation:
    metric: str
    rank: int
    date: str
    bet_team: str
    hedge_team: str
    bet_site: str
    hedge_site: str
    odds_bet: float
    odds_hedge: float
    b_stake: float
    h_hedge: float
    total_bet: float
    total_return: float
    net: float
    roi: float
    rake: float
    recommendation: str


@dataclass(frozen=True)
class OddsPipelineResult:
    raw_rows_written: int
    clean_rows_written: int
    ranked_rows_written: int
    recommendations: list[OddsRecommendation]


class OddsPipelineWriter(Protocol):
    def process_confirmed(self, context: OddsPipelineContext, candidates: list[OddsCandidate]) -> OddsPipelineResult:
        ...


class GoogleSheetsOddsPipeline:
    def __init__(
        self,
        spreadsheet_id: str,
        credentials_json_path: str,
        raw_worksheet_name: str,
        clean_worksheet_name: str,
        ranked_worksheet_name: str,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.credentials_json_path = credentials_json_path
        self.raw_worksheet_name = raw_worksheet_name
        self.clean_worksheet_name = clean_worksheet_name
        self.ranked_worksheet_name = ranked_worksheet_name

    def _spreadsheet(self):
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(self.credentials_json_path, scopes=scopes)
        client = gspread.authorize(credentials)
        return client.open_by_key(self.spreadsheet_id)

    def _worksheet(self, spreadsheet: Any, title: str, headers: list[str]):
        import gspread

        try:
            worksheet = spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=title, rows=3000, cols=max(40, len(headers) + 6))
            worksheet.append_row(headers)
            return worksheet

        top = worksheet.get("1:1")
        current = top[0] if top else []
        if current[: len(headers)] != headers:
            worksheet.clear()
            worksheet.append_row(headers)

        return worksheet

    def process_confirmed(self, context: OddsPipelineContext, candidates: list[OddsCandidate]) -> OddsPipelineResult:
        spreadsheet = self._spreadsheet()

        raw_ws = self._worksheet(spreadsheet, self.raw_worksheet_name, RAW_HEADERS)
        clean_ws = self._worksheet(spreadsheet, self.clean_worksheet_name, CLEAN_HEADERS)
        ranked_ws = self._worksheet(spreadsheet, self.ranked_worksheet_name, RANKED_HEADERS)

        raw_rows = _to_raw_rows(context, candidates)
        if raw_rows:
            raw_ws.append_rows(raw_rows, value_input_option="RAW")

        clean_rows, recommendation_pool = build_clean_rows(context, candidates)
        if clean_rows:
            start_row = len(clean_ws.get_all_values()) + 1
            clean_rows = _apply_clean_formulas(clean_rows, start_row)
            clean_ws.append_rows(clean_rows, value_input_option="USER_ENTERED")

        recommendations = select_top_recommendations(recommendation_pool)
        ranked_rows = _to_ranked_rows(context, recommendations)
        if ranked_rows:
            ranked_ws.append_rows(ranked_rows, value_input_option="RAW")

        return OddsPipelineResult(
            raw_rows_written=len(raw_rows),
            clean_rows_written=len(clean_rows),
            ranked_rows_written=len(ranked_rows),
            recommendations=recommendations,
        )


def create_odds_pipeline(
    *,
    enabled: bool,
    spreadsheet_id: str,
    credentials_json_path: str,
    raw_worksheet_name: str,
    clean_worksheet_name: str,
    ranked_worksheet_name: str,
) -> OddsPipelineWriter | None:
    if not enabled:
        return None

    if not spreadsheet_id:
        raise RuntimeError("CONFIRM_GOOGLE_SHEET_ID is required when ODDS_ENABLED=true")
    if not credentials_json_path:
        raise RuntimeError("CONFIRM_GOOGLE_CREDENTIALS_JSON is required when ODDS_ENABLED=true")

    return GoogleSheetsOddsPipeline(
        spreadsheet_id=spreadsheet_id,
        credentials_json_path=credentials_json_path,
        raw_worksheet_name=raw_worksheet_name,
        clean_worksheet_name=clean_worksheet_name,
        ranked_worksheet_name=ranked_worksheet_name,
    )


def build_clean_rows(
    context: OddsPipelineContext,
    candidates: list[OddsCandidate],
    *,
    b_stake: float = 100.0,
) -> tuple[list[list[Any]], list[OddsRecommendation]]:
    grouped: dict[str, dict[str, list[OddsCandidate]]] = {}

    for candidate in candidates:
        if candidate.market != "moneyline":
            continue
        odds_value = _to_float(candidate.odds)
        if odds_value is None or odds_value <= 1:
            continue
        if not candidate.team or not candidate.against:
            continue

        matchup_key = _canonical_matchup_key(candidate.date, candidate.team, candidate.against)
        side_key = f"{candidate.team}|{candidate.against}"

        sides = grouped.setdefault(matchup_key, {})
        side_candidates = sides.setdefault(side_key, [])
        side_candidates.append(candidate)

    clean_rows: list[list[Any]] = []
    pool: list[OddsRecommendation] = []
    now = datetime.utcnow().isoformat(timespec="seconds")

    for sides in grouped.values():
        for left_key, left_candidates in list(sides.items()):
            left_team, left_against = left_key.split("|", 1)
            right_key = f"{left_against}|{left_team}"
            if right_key not in sides:
                continue

            if left_key > right_key:
                continue

            best_pair = _pick_best_site_pair(left_candidates, sides[right_key], b_stake)
            if not best_pair:
                continue

            underdog, favorite, odds_u, odds_f = best_pair

            h_hedge = (b_stake * odds_u) / odds_f if odds_f > 0 else 0.0
            total_bet = b_stake + h_hedge
            total_return = b_stake * odds_u
            net = total_return - total_bet
            roi = (net / total_bet) if total_bet else 0.0
            rake = (1 / odds_u) + (1 / odds_f) - 1

            eligible = (
                _meets_site_min_odds(odds_u, underdog.site)
                and _meets_site_min_odds(odds_f, favorite.site)
            )
            recommendation = "BET" if eligible else "NO BET"

            clean_rows.append(
                [
                    now,
                    context.session_id,
                    underdog.date,
                    underdog.team,
                    favorite.team,
                    round(odds_u, 4),
                    round(odds_f, 4),
                    underdog.site,
                    favorite.site,
                    round(b_stake, 2),
                    round(h_hedge, 2),
                    round(total_bet, 2),
                    round(total_return, 2),
                    round(net, 2),
                    round(roi, 6),
                    round(rake, 6),
                    recommendation,
                ]
            )

            pool.append(
                OddsRecommendation(
                    metric="",
                    rank=0,
                    date=underdog.date,
                    bet_team=underdog.team,
                    hedge_team=favorite.team,
                    bet_site=underdog.site,
                    hedge_site=favorite.site,
                    odds_bet=round(odds_u, 4),
                    odds_hedge=round(odds_f, 4),
                    b_stake=round(b_stake, 2),
                    h_hedge=round(h_hedge, 2),
                    total_bet=round(total_bet, 2),
                    total_return=round(total_return, 2),
                    net=round(net, 2),
                    roi=round(roi, 6),
                    rake=round(rake, 6),
                    recommendation=recommendation,
                )
            )

    return clean_rows, pool


def _pick_best_site_pair(
    left_candidates: list[OddsCandidate],
    right_candidates: list[OddsCandidate],
    b_stake: float,
) -> tuple[OddsCandidate, OddsCandidate, float, float] | None:
    cross_site_options: list[tuple[tuple[float, float, float, float], tuple[OddsCandidate, OddsCandidate, float, float]]] = []

    for left in left_candidates:
        odds_left = _to_float(left.odds)
        if odds_left is None or odds_left <= 1:
            continue

        for right in right_candidates:
            odds_right = _to_float(right.odds)
            if odds_right is None or odds_right <= 1:
                continue

            if odds_left >= odds_right:
                underdog = left
                favorite = right
                odds_u = odds_left
                odds_f = odds_right
            else:
                underdog = right
                favorite = left
                odds_u = odds_right
                odds_f = odds_left

            h_hedge = (b_stake * odds_u) / odds_f if odds_f > 0 else 0.0
            total_bet = b_stake + h_hedge
            total_return = b_stake * odds_u
            net = total_return - total_bet
            roi = (net / total_bet) if total_bet else 0.0

            cross_site = (left.site or "").strip().lower() != (right.site or "").strip().lower()
            score = (net, roi, odds_u, odds_f)
            payload = (score, (underdog, favorite, odds_u, odds_f))
            if cross_site:
                cross_site_options.append(payload)

    if cross_site_options:
        return max(cross_site_options, key=lambda item: item[0])[1]
    return None

def select_top_recommendations(pool: list[OddsRecommendation]) -> list[OddsRecommendation]:
    if not pool:
        return []

    eligible_pool = [item for item in pool if item.recommendation == "BET"]
    if not eligible_pool:
        return []

    results: list[OddsRecommendation] = []

    def top(metric: str, reverse: bool) -> list[OddsRecommendation]:
        key_fn = {
            "roi": lambda item: item.roi,
            "profit": lambda item: item.net,
            "rake": lambda item: item.rake,
        }[metric]
        ranked = sorted(eligible_pool, key=key_fn, reverse=reverse)[:2]
        labeled: list[OddsRecommendation] = []
        for idx, item in enumerate(ranked, start=1):
            labeled.append(
                OddsRecommendation(
                    metric=metric,
                    rank=idx,
                    date=item.date,
                    bet_team=item.bet_team,
                    hedge_team=item.hedge_team,
                    bet_site=item.bet_site,
                    hedge_site=item.hedge_site,
                    odds_bet=item.odds_bet,
                    odds_hedge=item.odds_hedge,
                    b_stake=item.b_stake,
                    h_hedge=item.h_hedge,
                    total_bet=item.total_bet,
                    total_return=item.total_return,
                    net=item.net,
                    roi=item.roi,
                    rake=item.rake,
                    recommendation=item.recommendation,
                )
            )
        return labeled

    results.extend(top("roi", True))
    results.extend(top("profit", True))
    results.extend(top("rake", False))

    return results

def _to_raw_rows(context: OddsPipelineContext, candidates: list[OddsCandidate]) -> list[list[Any]]:
    now = datetime.utcnow().isoformat(timespec="seconds")
    rows: list[list[Any]] = []
    for candidate in candidates:
        rows.append(
            [
                now,
                context.session_id,
                context.message_id,
                context.channel_id,
                context.guild_id or "",
                context.invoker_user_id,
                candidate.date,
                candidate.team,
                candidate.against,
                candidate.odds,
                candidate.market,
                candidate.site,
                candidate.source_image,
                candidate.confidence,
                ",".join(candidate.missing_fields),
            ]
        )
    return rows


def _to_ranked_rows(context: OddsPipelineContext, recommendations: list[OddsRecommendation]) -> list[list[Any]]:
    now = datetime.utcnow().isoformat(timespec="seconds")
    rows: list[list[Any]] = []
    for rec in recommendations:
        rows.append(
            [
                now,
                context.session_id,
                rec.metric,
                rec.rank,
                rec.date,
                rec.bet_team,
                rec.hedge_team,
                rec.bet_site,
                rec.hedge_site,
                rec.odds_bet,
                rec.odds_hedge,
                rec.b_stake,
                rec.h_hedge,
                rec.total_bet,
                rec.total_return,
                rec.net,
                rec.roi,
                rec.rake,
                rec.recommendation,
            ]
        )
    return rows


def _apply_clean_formulas(clean_rows: list[list[Any]], start_row: int) -> list[list[Any]]:
    output: list[list[Any]] = []
    for offset, row in enumerate(clean_rows):
        row_idx = start_row + offset
        local = list(row)
        # H/I=sites, J=b, K=h, L=T, M=r, N=net, O=roi, P=rake, Q=recommendation
        local[10] = f"=IF(G{row_idx}=0,0,(J{row_idx}*F{row_idx})/G{row_idx})"
        local[11] = f"=J{row_idx}+K{row_idx}"
        local[12] = f"=J{row_idx}*F{row_idx}"
        local[13] = f"=M{row_idx}-L{row_idx}"
        local[14] = f"=IF(L{row_idx}=0,0,N{row_idx}/L{row_idx})"
        local[15] = f"=(1/F{row_idx})+(1/G{row_idx})-1"
        local[16] = (
            f"=IF(AND("
            f"IF(LOWER(H{row_idx})=\"cloudbet\",F{row_idx}>=1,F{row_idx}>=1.5),"
            f"IF(LOWER(I{row_idx})=\"cloudbet\",G{row_idx}>=1,G{row_idx}>=1.5)),"
            "\"BET\",\"NO BET\")"
        )
        output.append(local)
    return output

def _canonical_matchup_key(date: str, team: str, against: str) -> str:
    left, right = sorted([team, against])
    return f"{date}|{left}|{right}"


def _to_float(value: Any) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None

def _meets_site_min_odds(odds_value: float, site: str) -> bool:
    site_key = (site or "").strip().lower()
    # Client rule:
    # - cloudbet: any odds acceptable
    # - all other sites: min odds 1.5
    min_required = 1.0 if site_key == "cloudbet" else 1.5
    return odds_value >= min_required




