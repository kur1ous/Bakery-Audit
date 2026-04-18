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


def test_select_top_recommendations_returns_rows_even_if_no_bet() -> None:
    pool_candidates = [
        OddsCandidate(date="2026-04-03", team="ATL", against="BKN", odds="3.01", site="xbet"),
        OddsCandidate(date="2026-04-03", team="BKN", against="ATL", odds="1.39", site="xbet"),
        OddsCandidate(date="2026-04-03", team="TOR", against="DET", odds="3.82", site="xbet"),
        OddsCandidate(date="2026-04-03", team="DET", against="TOR", odds="1.27", site="xbet"),
        OddsCandidate(date="2026-04-03", team="ORL", against="DET", odds="3.90", site="cloudbet"),
        OddsCandidate(date="2026-04-03", team="DET", against="ORL", odds="1.26", site="cloudbet"),
    ]

    _, recommendation_pool = build_clean_rows(_ctx(), pool_candidates)
    ranked = select_top_recommendations(recommendation_pool)

    assert len([item for item in ranked if item.metric == "roi"]) <= 2
    assert len([item for item in ranked if item.metric == "profit"]) <= 2
    assert len([item for item in ranked if item.metric == "rake"]) <= 2
    assert len(ranked) > 0
