from __future__ import annotations

from src.bot.odds_models import OddsCandidate


def test_odds_candidate_normalizes_date_team_and_site() -> None:
    candidate = OddsCandidate.model_validate(
        {
            "date": "Thursday, April 02, 2026 8:00 PM",
            "team": "Toronto Raptors",
            "against": "Boston Celtics",
            "odds": "2.40",
            "market": "MoneyLine",
            "site": "CloudBet",
            "confidence": 0.88,
        }
    )

    assert candidate.date == "2026-04-02"
    assert candidate.team == "TOR"
    assert candidate.against == "BOS"
    assert candidate.market == "moneyline"
    assert candidate.site == "cloudbet"
    assert candidate.missing_fields == []
    assert candidate.total_line == ""


def test_odds_candidate_missing_fields_and_default_date() -> None:
    candidate = OddsCandidate.model_validate(
        {
            "team": "",
            "against": "DET",
            "odds": "",
            "confidence": 0.2,
        }
    )

    assert candidate.date
    assert "team" in candidate.missing_fields
    assert "odds" in candidate.missing_fields
    assert candidate.needs_review is True


def test_odds_candidate_total_market_and_line_are_normalized() -> None:
    candidate = OddsCandidate.model_validate(
        {
            "date": "2026-04-20",
            "team": "Toronto Raptors",
            "against": "Cleveland Cavaliers",
            "odds": "1.93",
            "market": "OVER",
            "total_line": "222.5 pts",
            "site": "cloudbet.com",
        }
    )

    assert candidate.market == "total_over"
    assert candidate.total_line == "222.5"
    assert candidate.team == "TOR"
    assert candidate.against == "CLE"


def test_odds_candidate_spread_market_and_signed_line_are_normalized() -> None:
    candidate = OddsCandidate.model_validate(
        {
            "date": "2026-04-22",
            "team": "Dallas Stars",
            "against": "Minnesota Wild",
            "odds": "1.42",
            "market": "Handicap",
            "spread_line": "1.5",
            "site": "xbet.ag",
        }
    )

    assert candidate.market == "spread"
    assert candidate.spread_line == "+1.5"
    assert candidate.total_line == ""
    assert candidate.team == "DAL"
    assert candidate.against == "MIN"
