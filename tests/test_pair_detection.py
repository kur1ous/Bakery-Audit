from __future__ import annotations

from src.bot.discord_ui import detect_hedge_pair
from src.bot.models import BetExtraction


def test_detect_hedge_pair_true_for_opposite_sides() -> None:
    bets = [
        BetExtraction.model_validate(
            {
                "team": "Miami Heat",
                "against": "Boston Celtics",
                "odds": "2.69",
                "stake": "0",
                "return": "283.41",
            }
        ),
        BetExtraction.model_validate(
            {
                "team": "Boston Celtics",
                "against": "Miami Heat",
                "odds": "1.52",
                "stake": "260.00",
                "return": "395.2",
            }
        ),
    ]

    assert detect_hedge_pair(bets) is True


def test_detect_hedge_pair_false_for_unrelated_games() -> None:
    bets = [
        BetExtraction.model_validate(
            {
                "team": "Miami Heat",
                "against": "Boston Celtics",
                "odds": "2.69",
            }
        ),
        BetExtraction.model_validate(
            {
                "team": "Memphis Grizzlies",
                "against": "New York Knicks",
                "odds": "7.49",
            }
        ),
    ]

    assert detect_hedge_pair(bets) is False