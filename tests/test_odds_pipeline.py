from __future__ import annotations

from src.bot.odds_models import OddsCandidate
from src.bot.odds_pipeline import OddsPipelineContext, build_clean_rows, select_top_recommendations


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

