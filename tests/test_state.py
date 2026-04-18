from __future__ import annotations

from src.bot.models import BetExtraction
from src.bot.odds_models import OddsCandidate
from src.bot.state import PendingBetBatch, PendingBetStore, PendingOddsBatch, PendingOddsStore


def test_store_authorization() -> None:
    store = PendingBetStore()
    store.save(100, PendingBetBatch(invoker_id=42, extractions=[BetExtraction()]))

    assert store.is_authorized(100, 42) is True
    assert store.is_authorized(100, 43) is False
    assert store.is_authorized(999, 42) is False


def test_mark_confirmed() -> None:
    store = PendingBetStore()
    store.save(100, PendingBetBatch(invoker_id=42, extractions=[BetExtraction()]))

    pending = store.mark_confirmed(100)
    assert pending is not None
    assert pending.confirmed is True


def test_odds_store_authorization() -> None:
    store = PendingOddsStore()
    store.save(200, PendingOddsBatch(invoker_id=55, candidates=[OddsCandidate(team="TOR", against="BOS", odds="2.1")]))

    assert store.is_authorized(200, 55) is True
    assert store.is_authorized(200, 56) is False
    assert store.is_authorized(999, 55) is False
