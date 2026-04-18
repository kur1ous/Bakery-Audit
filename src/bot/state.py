from __future__ import annotations

from dataclasses import dataclass, field

from .models import BetExtraction
from .odds_models import OddsCandidate


@dataclass
class PendingBetBatch:
    invoker_id: int
    extractions: list[BetExtraction]
    has_hedge_pair: bool = False
    confirmed: bool = False
    bet_currencies: list[str] = field(default_factory=list)


@dataclass
class PendingOddsBatch:
    invoker_id: int
    candidates: list[OddsCandidate]
    failed_files: list[str] = field(default_factory=list)
    confirmed: bool = False


class PendingBetStore:
    def __init__(self) -> None:
        self._data: dict[int, PendingBetBatch] = {}

    def save(self, message_id: int, pending: PendingBetBatch) -> None:
        self._data[message_id] = pending

    def get(self, message_id: int) -> PendingBetBatch | None:
        return self._data.get(message_id)

    def delete(self, message_id: int) -> None:
        self._data.pop(message_id, None)

    def is_authorized(self, message_id: int, user_id: int) -> bool:
        state = self.get(message_id)
        if not state:
            return False
        return state.invoker_id == user_id

    def mark_confirmed(self, message_id: int) -> PendingBetBatch | None:
        state = self.get(message_id)
        if not state:
            return None
        state.confirmed = True
        return state


class PendingOddsStore:
    def __init__(self) -> None:
        self._data: dict[int, PendingOddsBatch] = {}

    def save(self, message_id: int, pending: PendingOddsBatch) -> None:
        self._data[message_id] = pending

    def get(self, message_id: int) -> PendingOddsBatch | None:
        return self._data.get(message_id)

    def delete(self, message_id: int) -> None:
        self._data.pop(message_id, None)

    def is_authorized(self, message_id: int, user_id: int) -> bool:
        state = self.get(message_id)
        if not state:
            return False
        return state.invoker_id == user_id
