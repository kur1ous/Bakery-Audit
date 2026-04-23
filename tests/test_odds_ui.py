from __future__ import annotations

import pytest

from src.bot.odds_pipeline import OddsRecommendation
from src.bot.odds_ui import (
    OddsResultPaginationView,
    build_odds_result_embed,
    build_odds_review_embed,
    build_over_under_embed,
    build_over_under_recommendations,
    _select_unique_ou_picks_by_metric,
)
from src.bot.odds_models import OddsCandidate


def test_build_odds_result_embed_uses_site_aware_pick_blocks() -> None:
    recs = [
        OddsRecommendation(
            metric="roi",
            rank=1,
            date="2026-04-18",
            bet_team="POR",
            hedge_team="SAS",
            bet_site="xbet",
            hedge_site="cloudbet",
            odds_bet=4.99,
            odds_hedge=1.92,
            b_stake=100.0,
            h_hedge=259.9,
            total_bet=359.9,
            total_return=499.0,
            net=139.1,
            roi=0.38655,
            rake=-0.2782,
            recommendation="BET",
        )
    ]

    embed = build_odds_result_embed(recs, insufficient_data=True)

    assert embed.description
    assert "underdog/hedge" in embed.description
    roi_field = next(field for field in embed.fields if field.name == "Top 2 ROI")
    assert "**1) Bet POR @ xbet**" in roi_field.value
    assert "On site `xbet`, bet `b=100.00` (`real`) on `POR`." in roi_field.value
    assert "On site `cloudbet`, bet `h=259.90` (`real`) on `SAS`." in roi_field.value
    assert "REAL: Either way, result is `profit` `139.10` (floor)," in roi_field.value
    assert "Odds (bet/hedge): `4.99 (xbet)` / `1.92 (cloudbet)`" in roi_field.value
    assert "Real (bet/hedge/floor): `139.10` / `139.11` / `139.10`" in roi_field.value
    assert "BONUS: On site `cloudbet`, bet `h=207.81` (`real`) on `SAS`." in roi_field.value
    assert "BONUS: Either way, result is `profit` `191.19` (guaranteed worst-case)," in roi_field.value
    assert "of total real cash bet `207.81` (bonus excluded)." in roi_field.value
    assert "Bonus h (optimized): `207.81`" in roi_field.value
    assert "Bonus (bet/hedge/floor): `191.19` / `191.19` / `191.19`" in roi_field.value
    assert "Status: `BET`" in roi_field.value


def test_build_odds_review_embed_has_site_breakdown() -> None:
    candidates = [
        OddsCandidate(date="2026-04-18", team="ATL", against="NYK", odds="3.01", site="xbet"),
        OddsCandidate(date="2026-04-18", team="NYK", against="ATL", odds="1.90", site="cloudbet"),
    ]

    embed = build_odds_review_embed(candidates, confirmed=False, failed_files=[])
    site_field = next(field for field in embed.fields if field.name == "Site Breakdown")
    assert "cloudbet: 1" in site_field.value
    assert "xbet: 1" in site_field.value


def test_build_over_under_embed_renders_ranked_recommendations() -> None:
    candidates = [
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.93",
            market="total_over",
            total_line="222.5",
            site="cloudbet",
        ),
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.90",
            market="total_under",
            total_line="222.5",
            site="xbet",
        ),
        OddsCandidate(
            date="2026-04-21",
            team="NYK",
            against="ATL",
            odds="1.91",
            market="total_over",
            total_line="217.5",
            site="cloudbet",
        ),
        OddsCandidate(
            date="2026-04-21",
            team="NYK",
            against="ATL",
            odds="1.92",
            market="total_under",
            total_line="217.5",
            site="xbet",
        ),
    ]

    embed = build_over_under_embed(candidates)

    assert embed.title == "Over/Under Recommendations"
    roi_field = next(field for field in embed.fields if field.name == "Top 2 ROI")
    assert "OVER" in roi_field.value or "UNDER" in roi_field.value
    assert "Odds (bet/hedge)" in roi_field.value
    assert "Status: `BET`" in roi_field.value


def test_build_over_under_embed_handles_no_rows() -> None:
    embed = build_over_under_embed(
        [OddsCandidate(date="2026-04-20", team="TOR", against="CLE", odds="3.75", market="moneyline", site="xbet")]
    )
    assert embed.description == "No Over/Under rows extracted from this batch."


@pytest.mark.asyncio
async def test_odds_result_pagination_view_toggles_button_state() -> None:
    recs = [
        OddsRecommendation(
            metric="roi",
            rank=1,
            date="2026-04-18",
            bet_team="POR",
            hedge_team="SAS",
            bet_site="xbet",
            hedge_site="cloudbet",
            odds_bet=4.99,
            odds_hedge=1.92,
            b_stake=100.0,
            h_hedge=259.9,
            total_bet=359.9,
            total_return=499.0,
            net=139.1,
            roi=0.38655,
            rake=-0.2782,
            recommendation="BET",
        )
    ]

    view = OddsResultPaginationView(
        invoker_user_id=123,
        recommendations=recs,
        candidates=[],
        insufficient_data=True,
        odds_mode="both",
    )

    next_button = next(child for child in view.children if getattr(child, "custom_id", "") == "odds:result:next")
    back_button = next(child for child in view.children if getattr(child, "custom_id", "") == "odds:result:back")

    assert next_button.disabled is False
    assert back_button.disabled is True

    view.page = 1
    view._sync_buttons()
    assert next_button.disabled is True
    assert back_button.disabled is False


def test_build_over_under_recommendations_returns_ranked_metrics() -> None:
    candidates = [
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.93",
            market="total_over",
            total_line="222.5",
            site="cloudbet",
        ),
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.90",
            market="total_under",
            total_line="222.5",
            site="xbet",
        ),
        OddsCandidate(
            date="2026-04-21",
            team="NYK",
            against="ATL",
            odds="1.91",
            market="total_over",
            total_line="217.5",
            site="cloudbet",
        ),
        OddsCandidate(
            date="2026-04-21",
            team="NYK",
            against="ATL",
            odds="1.92",
            market="total_under",
            total_line="217.5",
            site="xbet",
        ),
    ]

    ranked = build_over_under_recommendations(candidates)
    assert len(ranked) >= 3
    assert {item.metric for item in ranked} == {"roi", "profit", "rake"}
    assert all(item.recommendation == "BET" for item in ranked)


def test_build_over_under_embed_field_values_respect_discord_limit() -> None:
    candidates: list[OddsCandidate] = []
    for idx in range(1, 9):
        date = f"2026-04-{idx + 10:02d}"
        team = f"T{idx:02d}A"
        against = f"T{idx:02d}B"
        candidates.append(
            OddsCandidate(
                date=date,
                team=team,
                against=against,
                odds="1.95",
                market="total_over",
                total_line=str(210 + idx),
                site="cloudbet",
            )
        )
        candidates.append(
            OddsCandidate(
                date=date,
                team=team,
                against=against,
                odds="1.90",
                market="total_under",
                total_line=str(211 + idx),
                site="xbet",
            )
        )

    embed = build_over_under_embed(candidates, odds_mode="both")
    for field in embed.fields:
        assert len(field.value) <= 1024


def test_select_unique_ou_picks_by_metric_avoids_repeat_game() -> None:
    rec_a_roi = OddsRecommendation(
        metric="roi",
        rank=1,
        date="2026-04-20",
        bet_team="NYK/ATL UNDER 217.5",
        hedge_team="NYK/ATL OVER 217.5",
        bet_site="xbet",
        hedge_site="cloudbet",
        odds_bet=1.95,
        odds_hedge=1.90,
        b_stake=100.0,
        h_hedge=102.0,
        total_bet=202.0,
        total_return=195.0,
        net=-7.0,
        roi=-0.034653,
        rake=0.039,
        recommendation="BET",
    )
    rec_a_profit = OddsRecommendation(**{**rec_a_roi.__dict__, "metric": "profit", "rank": 1})
    rec_b_profit = OddsRecommendation(
        **{
            **rec_a_roi.__dict__,
            "metric": "profit",
            "rank": 2,
            "date": "2026-04-21",
            "bet_team": "TOR/CLE OVER 222.5",
            "hedge_team": "TOR/CLE UNDER 223.5",
        }
    )

    selected, suppressed = _select_unique_ou_picks_by_metric([rec_a_roi, rec_a_profit, rec_b_profit])
    assert len(selected["roi"]) == 1
    assert len(selected["profit"]) == 1
    assert selected["profit"][0].date == "2026-04-21"
    assert suppressed["profit"] == 1


def test_build_over_under_embed_marks_suppressed_metric_as_already_mentioned() -> None:
    candidates = [
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.93",
            market="total_over",
            total_line="222.5",
            site="cloudbet",
        ),
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.90",
            market="total_under",
            total_line="223.5",
            site="xbet",
        ),
    ]

    embed = build_over_under_embed(candidates, odds_mode="both")
    profit_field = next(field for field in embed.fields if field.name == "Top 2 Profit")
    rake_field = next(field for field in embed.fields if field.name == "Top 2 Rake (Lowest)")
    assert profit_field.value == "game already mentioned"
    assert rake_field.value == "game already mentioned"
