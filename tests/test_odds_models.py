from __future__ import annotations

from datetime import date

from src.bot.odds_models import OddsCandidate, candidate_site_scope, reconcile_candidate_date_years


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


def test_candidate_site_scope_uses_source_image_when_site_missing() -> None:
    candidate = OddsCandidate.model_validate(
        {
            "date": "2026-04-20",
            "team": "Toronto Raptors",
            "against": "Cleveland Cavaliers",
            "odds": "1.93",
            "market": "OVER",
            "total_line": "222.5",
            "site": "",
            "source_image": "tor-cle-cloudbet-1.png",
        }
    )

    assert candidate.site == "cloudbet"
    assert candidate_site_scope(candidate) == "site:cloudbet"


def test_odds_candidate_resolves_relative_date_from_reference_date() -> None:
    candidate = OddsCandidate.model_validate(
        {
            "date": "today • 3:30 PM",
            "team": "Phoenix Suns",
            "against": "Oklahoma City Thunder",
            "odds": "1.92",
            "market": "spread",
            "spread_line": "+9",
            "site": "cloudbet",
        },
        context={"reference_date": date(2026, 4, 25)},
    )

    assert candidate.date == "2026-04-25"


def test_odds_candidate_parses_month_day_without_year_from_reference_date() -> None:
    candidate = OddsCandidate.model_validate(
        {
            "date": "Apr 26 1:00 PM",
            "team": "Toronto Raptors",
            "against": "Cleveland Cavaliers",
            "odds": "1.95",
            "market": "spread",
            "spread_line": "+3.5",
            "site": "xbet",
        },
        context={"reference_date": date(2026, 4, 25)},
    )

    assert candidate.date == "2026-04-26"


def test_odds_candidate_parses_weekday_day_month_sportsbook_format() -> None:
    candidate = OddsCandidate.model_validate(
        {
            "date": "Mon 27 Apr • 8:00 PM",
            "team": "Orlando Magic",
            "against": "Detroit Pistons",
            "odds": "2.20",
            "market": "moneyline",
            "site": "cloudbet",
        },
        context={"reference_date": date(2026, 4, 25)},
    )

    assert candidate.date == "2026-04-27"


def test_reconcile_candidate_date_years_aligns_same_matchup_month_day_across_sites() -> None:
    candidates = [
        OddsCandidate(date="2024-04-27", team="BOS", against="PHI", odds="1.30", market="moneyline", site="cloudbet"),
        OddsCandidate(date="2026-04-27", team="PHI", against="BOS", odds="3.47", market="moneyline", site="xbet"),
        OddsCandidate(date="2024-04-27", team="BOS", against="PHI", odds="1.92", market="spread", spread_line="-7.5", site="cloudbet"),
    ]

    reconcile_candidate_date_years(candidates)

    assert [candidate.date for candidate in candidates] == ["2026-04-27", "2026-04-27", "2026-04-27"]


def test_reconcile_candidate_date_years_does_not_change_different_month_day() -> None:
    candidates = [
        OddsCandidate(date="2024-04-27", team="BOS", against="PHI", odds="1.30", market="moneyline", site="cloudbet"),
        OddsCandidate(date="2026-04-28", team="PHI", against="BOS", odds="3.47", market="moneyline", site="xbet"),
    ]

    reconcile_candidate_date_years(candidates)

    assert [candidate.date for candidate in candidates] == ["2024-04-27", "2026-04-28"]
