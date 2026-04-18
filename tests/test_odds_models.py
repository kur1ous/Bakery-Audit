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
