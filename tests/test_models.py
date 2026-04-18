from __future__ import annotations

from src.bot.models import BetExtraction, format_date_for_discord, normalize_money, normalize_odds, today_ymd


def test_normalize_odds_from_text() -> None:
    assert normalize_odds("odds: 7.4900") == "7.49"
    assert normalize_odds("+145") == "145"


def test_normalize_money() -> None:
    assert normalize_money("Risk: $0.00") == "0.00"
    assert normalize_money("Win 126.23") == "126.23"
    assert normalize_money(10) == "10.00"


def test_missing_fields_auto_inferred() -> None:
    extraction = BetExtraction.model_validate(
        {
            "date": "2026-04-01",
            "team": "Memphis Grizzlies",
            "against": "New York Knicks",
            "odds": "7.49",
            "stake": "0",
            "return": "126.23",
            "confidence": 0.92,
            "missing_fields": [],
        }
    )
    assert extraction.missing_fields == []
    assert extraction.needs_review is False


def test_partial_data_sets_missing_fields_without_date() -> None:
    extraction = BetExtraction.model_validate(
        {
            "team": "Memphis Grizzlies",
            "against": "New York Knicks",
            "odds": "7.49",
            "confidence": 0.4,
        }
    )
    assert extraction.date == today_ymd()
    assert set(extraction.missing_fields) == {"stake", "return_amount"}
    assert extraction.needs_review is True


def test_alias_return_field_maps_to_return_amount() -> None:
    extraction = BetExtraction.model_validate({"return": "12.5"})
    assert extraction.return_amount == "12.50"


def test_format_date_for_discord_returns_yyyy_mm_dd_only() -> None:
    assert format_date_for_discord("2026-04-01 8:00 PM") == "2026-04-01"


def test_format_date_for_discord_unparsed_defaults_to_today() -> None:
    assert format_date_for_discord("tomorrow evening") == today_ymd()
def test_format_date_for_discord_parses_weekday_timestamp() -> None:
    assert format_date_for_discord("Thursday, April 02, 2026 8:00 PM") == "2026-04-02"


def test_format_date_for_discord_prefers_legacy_pipe_left_date() -> None:
    assert format_date_for_discord("2026/04/02 | Thursday, April 02, 2026 8:00 PM") == "2026-04-02"