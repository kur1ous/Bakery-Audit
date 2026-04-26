from __future__ import annotations

import pytest

from src.bot.odds_models import OddsCandidate
from src.bot.odds_pipeline import OddsPipelineContext, OddsRecommendation, _to_raw_rows, build_clean_rows, select_top_recommendations


def _ctx() -> OddsPipelineContext:
    return OddsPipelineContext(
        session_id="session-1",
        message_id=1,
        channel_id=10,
        guild_id=20,
        invoker_user_id=30,
    )


def test_build_clean_rows_pairs_sites_and_uses_underdog_favorite() -> None:
    candidates = [
        OddsCandidate(date="2026-04-03", team="ATL", against="BKN", odds="3.01", site="xbet"),
        OddsCandidate(date="2026-04-03", team="BKN", against="ATL", odds="1.92", site="cloudbet"),
    ]

    rows, pool = build_clean_rows(_ctx(), candidates)

    assert len(rows) == 1
    assert len(pool) == 1
    assert rows[0][3] == "ATL"
    assert rows[0][4] == "BKN"
    assert rows[0][7] == "xbet"
    assert rows[0][8] == "cloudbet"
    assert pool[0].bet_site == "xbet"


def test_select_top_recommendations_excludes_no_bet_rows() -> None:
    pool_candidates = [
        OddsCandidate(date="2026-04-03", team="POR", against="SAS", odds="5.15", site="cloudbet"),
        OddsCandidate(date="2026-04-03", team="SAS", against="POR", odds="1.18", site="xbet"),
    ]

    _, recommendation_pool = build_clean_rows(_ctx(), pool_candidates)
    ranked = select_top_recommendations(recommendation_pool)

    assert len(recommendation_pool) == 1
    assert recommendation_pool[0].recommendation == "NO BET"
    assert ranked == []


def test_select_top_recommendations_includes_only_bet_rows() -> None:
    pool_candidates = [
        OddsCandidate(date="2026-04-03", team="ATL", against="BKN", odds="3.01", site="cloudbet"),
        OddsCandidate(date="2026-04-03", team="BKN", against="ATL", odds="1.60", site="xbet"),
        OddsCandidate(date="2026-04-03", team="POR", against="SAS", odds="5.15", site="cloudbet"),
        OddsCandidate(date="2026-04-03", team="SAS", against="POR", odds="1.18", site="xbet"),
    ]

    _, recommendation_pool = build_clean_rows(_ctx(), pool_candidates)
    ranked = select_top_recommendations(recommendation_pool)

    assert len(recommendation_pool) == 2
    assert any(item.recommendation == "BET" for item in recommendation_pool)
    assert all(item.recommendation == "BET" for item in ranked)

def test_build_clean_rows_prefers_cross_site_pair_when_available() -> None:
    candidates = [
        OddsCandidate(date="2026-04-18", team="ATL", against="NYK", odds="3.00", site="cloudbet"),
        OddsCandidate(date="2026-04-18", team="ATL", against="NYK", odds="2.90", site="xbet"),
        OddsCandidate(date="2026-04-18", team="NYK", against="ATL", odds="1.40", site="cloudbet"),
        OddsCandidate(date="2026-04-18", team="NYK", against="ATL", odds="1.35", site="xbet"),
    ]

    rows, pool = build_clean_rows(_ctx(), candidates)

    assert len(rows) == 1
    assert len(pool) == 1
    assert rows[0][7] != rows[0][8]
    assert pool[0].bet_site != pool[0].hedge_site


def test_build_clean_rows_ignores_totals_candidates() -> None:
    candidates = [
        OddsCandidate(date="2026-04-20", team="TOR", against="CLE", odds="3.75", market="moneyline", site="xbet"),
        OddsCandidate(date="2026-04-20", team="CLE", against="TOR", odds="1.28", market="moneyline", site="cloudbet"),
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.93",
            market="total_over",
            total_line="222.5",
            site="cloudbet",
        ),
    ]

    rows, pool = build_clean_rows(_ctx(), candidates)
    assert len(rows) == 1
    assert len(pool) == 1
    assert rows[0][3] == "TOR"
    assert rows[0][4] == "CLE"


def test_build_clean_rows_match_workbook_example() -> None:
    candidates = [
        OddsCandidate(date="2026-04-20", team="TOR", against="CLE", odds="3.81", market="moneyline", site="xbet"),
        OddsCandidate(date="2026-04-20", team="CLE", against="TOR", odds="1.28", market="moneyline", site="cloudbet"),
    ]

    rows, pool = build_clean_rows(_ctx(), candidates)

    assert len(rows) == 1
    assert len(pool) == 1
    assert rows[0][10] == pytest.approx(297.66, abs=0.01)
    assert rows[0][11] == pytest.approx(397.66, abs=0.01)
    assert rows[0][12] == pytest.approx(381.0, abs=0.01)
    assert rows[0][13] == pytest.approx(61.47, abs=0.01)
    assert rows[0][14] == pytest.approx(0.2800, abs=0.0001)
    assert rows[0][15] == pytest.approx(-0.043717, abs=0.000001)
    assert pool[0].h_hedge == pytest.approx(297.66, abs=0.01)
    assert pool[0].total_bet == pytest.approx(397.66, abs=0.01)
    assert pool[0].total_return == pytest.approx(381.0, abs=0.01)
    assert pool[0].net == pytest.approx(61.47, abs=0.01)
    assert pool[0].roi == pytest.approx(0.2800, abs=0.0001)
    assert pool[0].rake == pytest.approx(-0.043717, abs=0.000001)


def test_build_clean_rows_pairs_sportsbook_day_month_dates() -> None:
    candidates = [
        OddsCandidate(
            date="Mon 27 Apr • 8:00 PM",
            team="Orlando Magic",
            against="Detroit Pistons",
            odds="2.20",
            market="moneyline",
            site="cloudbet",
        ),
        OddsCandidate(
            date="Apr 27 8:00 PM",
            team="Detroit Pistons",
            against="Orlando Magic",
            odds="1.69",
            market="moneyline",
            site="xbet",
        ),
    ]

    rows, pool = build_clean_rows(_ctx(), candidates)

    assert len(rows) == 1
    assert len(pool) == 1
    assert rows[0][2] == "2026-04-27"


def test_build_clean_rows_prefers_non_cloudbet_bonus_side() -> None:
    candidates = [
        OddsCandidate(date="2026-04-24", team="PIT", against="PHI", odds="1.85", market="moneyline", site="xbet"),
        OddsCandidate(date="2026-04-24", team="PHI", against="PIT", odds="2.00", market="moneyline", site="cloudbet"),
    ]

    rows, pool = build_clean_rows(_ctx(), candidates)

    assert len(rows) == 1
    assert len(pool) == 1
    assert rows[0][3] == "PIT"
    assert rows[0][4] == "PHI"
    assert rows[0][7] == "xbet"
    assert rows[0][8] == "cloudbet"
    assert rows[0][10] == pytest.approx(92.50, abs=0.01)
    assert rows[0][13] == pytest.approx(42.50, abs=0.01)
    assert rows[0][14] == pytest.approx(1.0, abs=0.0001)
    assert pool[0].bet_site == "xbet"
    assert pool[0].hedge_site == "cloudbet"
    assert pool[0].net == pytest.approx(42.50, abs=0.01)


def test_select_top_recommendations_uses_next_game_when_metric_would_repeat() -> None:
    shared = {
        "rank": 0,
        "bet_site": "xbet",
        "hedge_site": "cloudbet",
        "odds_bet": 3.81,
        "odds_hedge": 1.28,
        "b_stake": 100.0,
        "h_hedge": 297.66,
        "total_bet": 397.66,
        "total_return": 381.0,
        "recommendation": "BET",
    }
    pool = [
        OddsRecommendation(metric="", date="2026-04-20", bet_team="TOR", hedge_team="CLE", net=61.47, roi=0.28, rake=-0.0440, **shared),
        OddsRecommendation(metric="", date="2026-04-21", bet_team="ATL", hedge_team="NYK", net=55.00, roi=0.20, rake=-0.0300, **shared),
        OddsRecommendation(metric="", date="2026-04-22", bet_team="MIN", hedge_team="DEN", net=50.00, roi=0.18, rake=-0.0200, **shared),
        OddsRecommendation(metric="", date="2026-04-23", bet_team="LAL", hedge_team="HOU", net=45.00, roi=0.15, rake=-0.0100, **shared),
    ]

    ranked = select_top_recommendations(pool)

    roi_games = [(item.date, item.bet_team, item.hedge_team) for item in ranked if item.metric == "roi"]
    profit_games = [(item.date, item.bet_team, item.hedge_team) for item in ranked if item.metric == "profit"]
    rake_games = [(item.date, item.bet_team, item.hedge_team) for item in ranked if item.metric == "rake"]
    assert roi_games == [("2026-04-20", "TOR", "CLE"), ("2026-04-21", "ATL", "NYK")]
    assert profit_games == [("2026-04-22", "MIN", "DEN"), ("2026-04-23", "LAL", "HOU")]
    assert rake_games == []


def test_to_raw_rows_writes_only_moneyline_candidates() -> None:
    candidates = [
        OddsCandidate(date="2026-04-20", team="TOR", against="CLE", odds="3.75", market="moneyline", site="xbet"),
        OddsCandidate(
            date="2026-04-20",
            team="TOR",
            against="CLE",
            odds="1.93",
            market="total_over",
            total_line="222.5",
            site="cloudbet",
        ),
    ]

    rows = _to_raw_rows(_ctx(), candidates)
    assert len(rows) == 1
    assert rows[0][9] == "3.75"
    assert rows[0][10] == "moneyline"

