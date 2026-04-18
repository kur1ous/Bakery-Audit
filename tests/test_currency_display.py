from __future__ import annotations

from src.bot.discord_ui import _format_money_display


def test_format_money_display_usd() -> None:
    assert _format_money_display("55.00", "USD", 1.36) == "USD 55.00"


def test_format_money_display_cad_label_only() -> None:
    assert _format_money_display("55.00", "CAD", 1.36) == "CAD 55.00"


def test_format_money_display_missing() -> None:
    assert _format_money_display("", "USD", 1.36) == "(missing)"
