from __future__ import annotations

import pytest

from src.bot.odds_pipeline import OddsRecommendation
from src.bot.odds_ui import (
    build_best_by_market_embed,
    build_odds_result_embed,
    build_odds_review_embed,
    build_over_under_embed,
    build_over_under_recommendations,
    build_spread_embed,
    build_spread_recommendations,
    _select_unique_market_picks_by_metric,
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
    assert "1) Bet **POR** @ **xbet**" in roi_field.value
    assert "Apr-18" in roi_field.value
    assert "SUMMARY" in roi_field.value
    assert "Odds (bet/hedge): 4.99 (xbet) / 1.92 (cloudbet)" in roi_field.value
    assert "Real (bet/hedge/profit/%): 100.00 / 259.90 / 139.10 / 38.65%" in roi_field.value
    assert "Bonus (bet/hedge/profit/%): 100.00 / 207.81 / 191.19 / 92.00%" in roi_field.value
    assert "REAL" in roi_field.value
    assert "On xbet, bet 100.00 (real) on POR." in roi_field.value
    assert "On cloudbet, bet 259.90 (real) on SAS." in roi_field.value
    assert "Either way, result is profit 139.10, 38.65% of total real money bet 359.90." in roi_field.value
    assert "BONUS" in roi_field.value
    assert "On cloudbet, bet 207.81 (real) on SAS." in roi_field.value
    assert "Either way, result is profit 191.19, 92.00% of total real cash bet 207.81." in roi_field.value


def test_build_odds_result_embed_hides_bonus_when_bet_site_is_cloudbet() -> None:
    recs = [
        OddsRecommendation(
            metric="roi",
            rank=1,
            date="2026-04-18",
            bet_team="PHI",
            hedge_team="PIT",
            bet_site="cloudbet",
            hedge_site="xbet",
            odds_bet=2.00,
            odds_hedge=1.85,
            b_stake=100.0,
            h_hedge=108.11,
            total_bet=208.11,
            total_return=200.0,
            net=45.95,
            roi=0.85,
            rake=-0.0405,
            recommendation="BET",
        )
    ]

    embed = build_odds_result_embed(recs, insufficient_data=True, odds_mode="both")

    roi_field = next(field for field in embed.fields if field.name == "Top 2 ROI")
    assert "Bonus: unavailable when the bet site is cloudbet" in roi_field.value
    assert "Bonus is unavailable when the bet site is cloudbet." in roi_field.value
    assert "On cloudbet, bet 100.00 (bonus)" not in roi_field.value


def test_build_odds_result_embed_marks_duplicate_metric_game_as_already_mentioned() -> None:
    shared = {
        "date": "2026-04-18",
        "bet_team": "POR",
        "hedge_team": "SAS",
        "bet_site": "xbet",
        "hedge_site": "cloudbet",
        "odds_bet": 4.99,
        "odds_hedge": 1.92,
        "b_stake": 100.0,
        "h_hedge": 259.9,
        "total_bet": 359.9,
        "total_return": 499.0,
        "net": 139.1,
        "roi": 0.38655,
        "rake": -0.2782,
        "recommendation": "BET",
    }
    recs = [
        OddsRecommendation(metric="roi", rank=1, **shared),
        OddsRecommendation(metric="profit", rank=1, **shared),
        OddsRecommendation(metric="rake", rank=1, **shared),
    ]

    embed = build_odds_result_embed(recs, insufficient_data=True)
    profit_field = next(field for field in embed.fields if field.name == "Top 2 Profit")
    rake_field = next(field for field in embed.fields if field.name == "Top 2 Rake (Best Edge)")
    assert profit_field.value == "game already mentioned"
    assert rake_field.value == "game already mentioned"


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
    assert "SUMMARY" in roi_field.value


def test_build_over_under_embed_handles_no_rows() -> None:
    embed = build_over_under_embed(
        [OddsCandidate(date="2026-04-20", team="TOR", against="CLE", odds="3.75", market="moneyline", site="xbet")]
    )
    assert embed.description == "No Over/Under rows extracted from this batch."


def test_build_best_by_market_embed_shows_one_pick_per_market() -> None:
    moneyline_recommendations = [
        OddsRecommendation(
            metric="roi",
            rank=1,
            date="2026-04-20",
            bet_team="TOR",
            hedge_team="CLE",
            bet_site="xbet",
            hedge_site="cloudbet",
            odds_bet=3.81,
            odds_hedge=1.28,
            b_stake=100.0,
            h_hedge=297.66,
            total_bet=397.66,
            total_return=381.0,
            net=61.47,
            roi=0.28,
            rake=-0.043717,
            recommendation="BET",
        )
    ]
    over_under_recommendations = [
        OddsRecommendation(
            metric="roi",
            rank=1,
            date="2026-04-21",
            bet_team="NYK/ATL UNDER 217.5",
            hedge_team="NYK/ATL OVER 217.5",
            bet_site="xbet",
            hedge_site="cloudbet",
            odds_bet=1.92,
            odds_hedge=1.91,
            b_stake=100.0,
            h_hedge=100.52,
            total_bet=200.52,
            total_return=193.0,
            net=-7.52,
            roi=-0.0375,
            rake=-0.0443,
            recommendation="BET",
        )
    ]
    spread_recommendations = [
        OddsRecommendation(
            metric="roi",
            rank=1,
            date="2026-04-22",
            bet_team="ANA/EDM -1.5",
            hedge_team="EDM/ANA +1.5",
            bet_site="cloudbet",
            hedge_site="xbet",
            odds_bet=2.22,
            odds_hedge=1.67,
            b_stake=100.0,
            h_hedge=132.93,
            total_bet=232.93,
            total_return=222.0,
            net=40.12,
            roi=0.4310,
            rake=-0.0470,
            recommendation="BET",
        )
    ]

    embed = build_best_by_market_embed(
        moneyline_recommendations=moneyline_recommendations,
        over_under_recommendations=over_under_recommendations,
        spread_recommendations=spread_recommendations,
        odds_mode="both",
    )

    assert embed.title == "Odds Recommendations"
    assert embed.description == "Best pick per market from this extraction batch."
    assert next(field for field in embed.fields if field.name == "Best Moneyline").value.startswith("1) Bet **TOR**")
    assert "UNDER 217.5" in next(field for field in embed.fields if field.name == "Best O/U").value
    assert "-1.5" in next(field for field in embed.fields if field.name == "Best Spread").value


def test_build_best_by_market_embed_prioritizes_profit_in_bonus_mode() -> None:
    moneyline_recommendations = [
        OddsRecommendation(
            metric="roi",
            rank=1,
            date="2026-04-27",
            bet_team="ORL",
            hedge_team="DET",
            bet_site="xbet",
            hedge_site="cloudbet",
            odds_bet=2.18,
            odds_hedge=1.71,
            b_stake=100.0,
            h_hedge=127.49,
            total_bet=227.49,
            total_return=218.0,
            net=48.99,
            roi=0.71,
            rake=-0.044,
            recommendation="BET",
        ),
        OddsRecommendation(
            metric="profit",
            rank=1,
            date="2026-04-26",
            bet_team="PHI",
            hedge_team="BOS",
            bet_site="xbet",
            hedge_site="cloudbet",
            odds_bet=3.47,
            odds_hedge=1.30,
            b_stake=100.0,
            h_hedge=266.92,
            total_bet=366.92,
            total_return=347.0,
            net=57.00,
            roi=0.30,
            rake=-0.058,
            recommendation="BET",
        ),
    ]

    embed = build_best_by_market_embed(
        moneyline_recommendations=moneyline_recommendations,
        over_under_recommendations=[],
        spread_recommendations=[],
        odds_mode="bonus",
    )

    best_moneyline = next(field for field in embed.fields if field.name == "Best Moneyline")
    assert best_moneyline.value.startswith("1) Bet **PHI**")


def test_build_best_by_market_embed_prioritizes_rake_in_real_mode() -> None:
    moneyline_recommendations = [
        OddsRecommendation(
            metric="profit",
            rank=1,
            date="2026-04-26",
            bet_team="PHI",
            hedge_team="BOS",
            bet_site="xbet",
            hedge_site="cloudbet",
            odds_bet=3.47,
            odds_hedge=1.30,
            b_stake=100.0,
            h_hedge=266.92,
            total_bet=366.92,
            total_return=347.0,
            net=57.00,
            roi=0.30,
            rake=-0.058,
            recommendation="BET",
        ),
        OddsRecommendation(
            metric="rake",
            rank=1,
            date="2026-04-27",
            bet_team="ORL",
            hedge_team="DET",
            bet_site="xbet",
            hedge_site="cloudbet",
            odds_bet=2.18,
            odds_hedge=1.71,
            b_stake=100.0,
            h_hedge=127.49,
            total_bet=227.49,
            total_return=218.0,
            net=48.99,
            roi=0.71,
            rake=-0.044,
            recommendation="BET",
        ),
    ]

    embed = build_best_by_market_embed(
        moneyline_recommendations=moneyline_recommendations,
        over_under_recommendations=[],
        spread_recommendations=[],
        odds_mode="real",
    )

    best_moneyline = next(field for field in embed.fields if field.name == "Best Moneyline")
    assert best_moneyline.value.startswith("1) Bet **ORL**")


def test_build_best_by_market_embed_explains_moneyline_date_drift() -> None:
    candidates = [
        OddsCandidate(date="2026-04-26", team="BOS", against="PHI", odds="1.30", market="moneyline", site="cloudbet"),
        OddsCandidate(date="2026-04-27", team="PHI", against="BOS", odds="3.47", market="moneyline", site="xbet"),
    ]

    embed = build_best_by_market_embed(
        moneyline_recommendations=[],
        over_under_recommendations=[],
        spread_recommendations=[],
        candidates=candidates,
        odds_mode="both",
    )

    diagnostics = next(field for field in embed.fields if field.name == "Moneyline Diagnostics")
    assert "Moneyline rows: 2" in diagnostics.value
    assert "Exact reverse groups: 0; cross-site groups: 0" in diagnostics.value
    assert "Possible date drift:" in diagnostics.value
    assert "BOS/PHI: 2026-04-26 (cloudbet), 2026-04-27 (xbet)" in diagnostics.value


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
    assert len(ranked) == 2
    assert {item.metric for item in ranked} == {"roi"}
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


def test_select_unique_market_picks_by_metric_avoids_repeat_game() -> None:
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
        rake=-0.039,
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

    selected, suppressed = _select_unique_market_picks_by_metric([rec_a_roi, rec_a_profit, rec_b_profit])
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
    rake_field = next(field for field in embed.fields if field.name == "Top 2 Rake (Best Edge)")
    assert profit_field.value == "No picks available"
    assert rake_field.value == "No picks available"


def test_build_over_under_embed_includes_why_no_picks_note_for_same_site_only() -> None:
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
            site="cloudbet",
        ),
    ]

    embed = build_over_under_embed(candidates, odds_mode="both")
    why_field = next(field for field in embed.fields if field.name == "Why No Picks?")
    assert "Only same-site opposite-side pairs were found." in why_field.value


def test_build_over_under_embed_pairs_different_source_images_when_site_is_missing() -> None:
    candidates = [
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.93",
            market="total_over",
            total_line="222.5",
            site="",
            source_image="cloudbet-tor-cle.png",
        ),
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.91",
            market="total_under",
            total_line="223.5",
            site="",
            source_image="xbet-tor-cle.png",
        ),
    ]

    embed = build_over_under_embed(candidates, odds_mode="both")
    roi_field = next(field for field in embed.fields if field.name == "Top 2 ROI")
    why_fields = [field for field in embed.fields if field.name == "Why No Picks?"]
    assert "No picks available" not in roi_field.value
    assert why_fields == []


def test_build_spread_embed_renders_ranked_recommendations() -> None:
    candidates = [
        OddsCandidate(
            date="2026-04-22",
            team="DAL",
            against="MIN",
            odds="1.42",
            market="spread",
            spread_line="+2.5",
            site="xbet",
        ),
        OddsCandidate(
            date="2026-04-22",
            team="MIN",
            against="DAL",
            odds="2.04",
            market="spread",
            spread_line="-1.5",
            site="cloudbet",
        ),
        OddsCandidate(
            date="2026-04-22",
            team="EDM",
            against="ANA",
            odds="1.67",
            market="spread",
            spread_line="+1.5",
            site="xbet",
        ),
        OddsCandidate(
            date="2026-04-22",
            team="ANA",
            against="EDM",
            odds="2.22",
            market="spread",
            spread_line="-1.5",
            site="cloudbet",
        ),
    ]

    embed = build_spread_embed(candidates)
    assert embed.title == "Spread Recommendations"
    roi_field = next(field for field in embed.fields if field.name == "Top 2 ROI")
    assert "Odds (bet/hedge)" in roi_field.value
    assert "SUMMARY" in roi_field.value
    assert "Worst Case:" in roi_field.value
    assert "Middle:" in roi_field.value


def test_build_spread_embed_handles_no_rows() -> None:
    embed = build_spread_embed(
        [OddsCandidate(date="2026-04-22", team="DAL", against="MIN", odds="1.42", market="moneyline", site="xbet")]
    )
    assert embed.description == "No spread rows extracted from this batch."


def test_build_spread_embed_includes_why_no_picks_note_for_same_site_only() -> None:
    candidates = [
        OddsCandidate(
            date="2026-04-22",
            team="DAL",
            against="MIN",
            odds="1.42",
            market="spread",
            spread_line="+1.5",
            site="xbet",
        ),
        OddsCandidate(
            date="2026-04-22",
            team="MIN",
            against="DAL",
            odds="2.91",
            market="spread",
            spread_line="-1.5",
            site="xbet",
        ),
    ]

    embed = build_spread_embed(candidates)
    why_field = next(field for field in embed.fields if field.name == "Why No Picks?")
    assert "Only same-site opposite-side pairs were found." in why_field.value


def test_build_spread_recommendations_returns_ranked_metrics() -> None:
    candidates = [
        OddsCandidate(
            date="2026-04-22",
            team="DAL",
            against="MIN",
            odds="1.42",
            market="spread",
            spread_line="+2.5",
            site="xbet",
        ),
        OddsCandidate(
            date="2026-04-22",
            team="MIN",
            against="DAL",
            odds="2.04",
            market="spread",
            spread_line="-1.5",
            site="cloudbet",
        ),
        OddsCandidate(
            date="2026-04-22",
            team="EDM",
            against="ANA",
            odds="1.67",
            market="spread",
            spread_line="+1.5",
            site="xbet",
        ),
        OddsCandidate(
            date="2026-04-22",
            team="ANA",
            against="EDM",
            odds="2.22",
            market="spread",
            spread_line="-1.5",
            site="cloudbet",
        ),
    ]

    ranked = build_spread_recommendations(candidates)
    assert len(ranked) == 1
    assert {item.metric for item in ranked} == {"roi"}
    assert all(item.recommendation == "BET" for item in ranked)
