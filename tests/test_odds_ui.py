from __future__ import annotations

from src.bot.odds_pipeline import OddsRecommendation
from src.bot.odds_ui import build_odds_result_embed, build_odds_review_embed
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
    assert "Hedge: `SAS` @ `cloudbet`" in roi_field.value
    assert "Odds (bet/hedge): `4.99` / `1.92`" in roi_field.value
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
