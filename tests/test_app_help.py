from __future__ import annotations

from src.bot.app import (
    _gemini_retry_later_message,
    _help_message,
    _is_devlog_request,
    _is_help_request,
    _is_odds_request,
    _is_temporary_gemini_issue,
)


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


def test_is_temporary_gemini_issue_detects_unavailable_response() -> None:
    exc = RuntimeError("Gemini request failed: 503 UNAVAILABLE. Please try again later.")
    assert _is_temporary_gemini_issue(exc) is True


def test_is_temporary_gemini_issue_ignores_parse_failure() -> None:
    exc = RuntimeError("Gemini response parse failed: No JSON object found")
    assert _is_temporary_gemini_issue(exc) is False


def test_gemini_retry_later_message_mentions_issue_and_retry() -> None:
    exc = RuntimeError("503 UNAVAILABLE")
    text = _gemini_retry_later_message(exc)
    assert "Gemini is currently experiencing availability issues" in text
    assert "Please try again later." in text
    assert "503 UNAVAILABLE" in text
