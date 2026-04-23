from __future__ import annotations

import pytest

from src.bot.gemini_client import GeminiExtractionService, _extract_json


def test_extract_json_plain() -> None:
    payload = _extract_json('{"team":"A"}')
    assert payload["team"] == "A"


def test_extract_json_wrapped_text() -> None:
    payload = _extract_json('result: {"team":"A","return":"1"}')
    assert payload["return"] == "1"


def test_extract_json_raises_when_missing() -> None:
    with pytest.raises(ValueError):
        _extract_json("no json here")


def test_extract_odds_from_image_parses_moneyline_and_totals_rows() -> None:
    payload = (
        '{"site":"cloudbet","bets":['
        '{"date":"2026-04-20","team":"TOR","against":"CLE","odds":"3.75","market":"moneyline","total_line":"","site":"cloudbet","confidence":0.9},'
        '{"date":"2026-04-20","team":"TOR","against":"CLE","odds":"1.93","market":"total_over","total_line":"222.5","site":"cloudbet","confidence":0.9},'
        '{"date":"2026-04-20","team":"TOR","against":"CLE","odds":"1.90","market":"total_under","total_line":"222.5","site":"cloudbet","confidence":0.9}'
        ']}'
    )

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakeModels:
        def __init__(self, text: str) -> None:
            self._text = text

        def generate_content(self, **_: object) -> _FakeResponse:
            return _FakeResponse(self._text)

    class _FakeClient:
        def __init__(self, text: str) -> None:
            self.models = _FakeModels(text)

    def _factory(*, api_key: str) -> _FakeClient:
        assert api_key == "k1"
        return _FakeClient(payload)

    service = GeminiExtractionService(
        api_key="k1",
        model_name="gemini-test",
        client_factory=_factory,
    )

    batch = service.extract_odds_from_image(b"image", "image/png", "snap-1.png")
    assert batch.site == "cloudbet"
    assert len(batch.bets) == 3
    assert [item.market for item in batch.bets] == ["moneyline", "total_over", "total_under"]
    assert batch.bets[0].total_line == ""
    assert batch.bets[1].total_line == "222.5"
    assert batch.bets[2].total_line == "222.5"
    assert all(item.site == "cloudbet" for item in batch.bets)
    assert all(item.source_image == "snap-1.png" for item in batch.bets)


def test_extract_odds_from_image_parses_spread_rows() -> None:
    payload = (
        '{"site":"xbet","bets":['
        '{"date":"2026-04-22","team":"DAL","against":"MIN","odds":"1.42","market":"spread","total_line":"","spread_line":"+1.5","site":"xbet","confidence":0.9},'
        '{"date":"2026-04-22","team":"MIN","against":"DAL","odds":"2.91","market":"spread","total_line":"","spread_line":"-1.5","site":"xbet","confidence":0.9}'
        ']}'
    )

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakeModels:
        def __init__(self, text: str) -> None:
            self._text = text

        def generate_content(self, **_: object) -> _FakeResponse:
            return _FakeResponse(self._text)

    class _FakeClient:
        def __init__(self, text: str) -> None:
            self.models = _FakeModels(text)

    def _factory(*, api_key: str) -> _FakeClient:
        return _FakeClient(payload)

    service = GeminiExtractionService(
        api_key="k1",
        model_name="gemini-test",
        client_factory=_factory,
    )

    batch = service.extract_odds_from_image(b"image", "image/png", "snap-2.png")
    assert [item.market for item in batch.bets] == ["spread", "spread"]
    assert batch.bets[0].spread_line == "+1.5"
    assert batch.bets[1].spread_line == "-1.5"
    assert all(item.total_line == "" for item in batch.bets)
