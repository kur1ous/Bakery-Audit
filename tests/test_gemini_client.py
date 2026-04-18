from __future__ import annotations

import pytest

from src.bot.gemini_client import _extract_json


def test_extract_json_plain() -> None:
    payload = _extract_json('{"team":"A"}')
    assert payload["team"] == "A"


def test_extract_json_wrapped_text() -> None:
    payload = _extract_json('result: {"team":"A","return":"1"}')
    assert payload["return"] == "1"


def test_extract_json_raises_when_missing() -> None:
    with pytest.raises(ValueError):
        _extract_json("no json here")