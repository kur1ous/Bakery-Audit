from __future__ import annotations

from src.bot.app import _help_message, _is_devlog_request, _is_help_request, _is_odds_request


def test_help_request_detected_with_mention() -> None:
    assert _is_help_request("<@123456> help") is True
    assert _is_help_request("<@!123456>   HELP   ") is True


def test_help_request_detected_with_extra_words() -> None:
    assert _is_help_request("<@123456> help me") is True


def test_help_request_not_detected() -> None:
    assert _is_help_request("<@123456> parse this") is False
    assert _is_help_request("<@123456>") is False


def test_devlog_request_detected_with_mention() -> None:
    assert _is_devlog_request("<@123456> devlog") is True
    assert _is_devlog_request("<@!123456> DEVLOG latest") is True


def test_devlog_request_not_detected() -> None:
    assert _is_devlog_request("<@123456> help") is False
    assert _is_devlog_request("<@123456>") is False


def test_odds_request_detected_with_mention() -> None:
    assert _is_odds_request("<@123456> odds") is True
    assert _is_odds_request("<@!123456> ODDS now") is True


def test_odds_request_not_detected() -> None:
    assert _is_odds_request("<@123456> help") is False
    assert _is_odds_request("<@123456>") is False


def test_help_message_has_usage_steps() -> None:
    text = _help_message()
    assert "EV Bet Extractor Help" in text
    assert "Confirm All" in text
    assert "@bot devlog" in text
    assert "@bot odds" in text
