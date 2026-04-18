from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


_REQUIRED_FIELDS = ("date", "team", "against", "odds", "stake", "return_amount")
_NUMBER_RE = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?")
_DATE_PATTERNS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %I:%M %p",
    "%Y/%m/%d %I:%M %p",
    "%A, %B %d, %Y %I:%M %p",
    "%A %B %d, %Y %I:%M %p",
    "%a, %b %d, %Y %I:%M %p",
    "%a %b %d, %Y %I:%M %p",
    "%A, %B %d, %Y",
    "%A %B %d, %Y",
    "%a, %b %d, %Y",
    "%a %b %d, %Y",
    "%b %d %Y",
    "%B %d %Y",
    "%b %d, %Y",
    "%B %d, %Y",
)


class BetExtraction(BaseModel):
    date: str = ""
    team: str = ""
    against: str = ""
    odds: str = ""
    stake: str = ""
    return_amount: str = Field(default="", alias="return")
    confidence: float = 0.0
    missing_fields: list[str] = Field(default_factory=list)
    readable_summary: str = ""
    raw_text: str = ""

    @field_validator("date", "team", "against", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("odds", mode="before")
    @classmethod
    def _normalize_odds_field(cls, value: Any) -> str:
        return normalize_odds(value)

    @field_validator("stake", "return_amount", mode="before")
    @classmethod
    def _normalize_money_fields(cls, value: Any) -> str:
        return normalize_money(value)

    @field_validator("missing_fields", mode="before")
    @classmethod
    def _normalize_missing_fields(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        try:
            candidate = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, candidate))

    @model_validator(mode="after")
    def _finalize(self) -> "BetExtraction":
        # Always keep date in yyyy-mm-dd format. If missing/unparseable, default to today.
        self.date = normalize_date_or_today(self.date)

        if not self.missing_fields:
            inferred_missing = [field for field in _REQUIRED_FIELDS if not getattr(self, field)]
            self.missing_fields = inferred_missing
        else:
            canonical = {field for field in self.missing_fields if field in _REQUIRED_FIELDS}
            for field in _REQUIRED_FIELDS:
                if not getattr(self, field):
                    canonical.add(field)
            self.missing_fields = sorted(canonical)

        # date is never treated as missing after fallback defaulting.
        self.missing_fields = [field for field in self.missing_fields if field != "date"]

        if not self.readable_summary:
            self.readable_summary = self.to_readable_summary()
        return self

    @property
    def needs_review(self) -> bool:
        return bool(self.missing_fields) or self.confidence < 0.75

    @property
    def display_date(self) -> str:
        return format_date_for_discord(self.date)

    def to_embed_lines(self) -> list[tuple[str, str]]:
        return [
            ("Date", self.display_date),
            ("Team", self.team or "(missing)"),
            ("Against", self.against or "(missing)"),
            ("Odds", self.odds or "(missing)"),
            ("Stake", self.stake or "(missing)"),
            ("Return", self.return_amount or "(missing)"),
        ]

    def to_readable_summary(self) -> str:
        return (
            f"Date: {self.date or 'unknown'}, Team: {self.team or 'unknown'}, "
            f"Against: {self.against or 'unknown'}, Odds: {self.odds or 'unknown'}, "
            f"Stake: {self.stake or 'unknown'}, Return: {self.return_amount or 'unknown'}."
        )


def format_date_for_discord(date_text: Any) -> str:
    # Kept function name for compatibility with existing imports.
    return normalize_date_or_today(date_text)


def normalize_date_or_today(date_text: Any) -> str:
    raw = "" if date_text is None else str(date_text).strip()
    if not raw:
        return today_ymd()

    parsed = parse_date(raw)
    if not parsed:
        return today_ymd()

    return parsed.strftime("%Y-%m-%d")


def today_ymd() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def parse_date(text: str) -> datetime | None:
    candidate = text.strip()
    if not candidate:
        return None

    # Older bot versions stored "YYYY/MM/DD | Thursday, April 02, 2026 8:00 PM".
    # Prefer the canonical date portion when this appears.
    if "|" in candidate:
        candidate = candidate.split("|", 1)[0].strip()

    try:
        normalized_iso = candidate.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized_iso)
    except ValueError:
        pass

    for pattern in _DATE_PATTERNS:
        try:
            return datetime.strptime(candidate, pattern)
        except ValueError:
            continue

    return None


def normalize_odds(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return _strip_trailing_zeros(f"{value}")

    text = str(value).strip()
    if not text:
        return ""

    match = _NUMBER_RE.search(text)
    if not match:
        return ""
    return _strip_trailing_zeros(match.group(0).replace(",", ""))


def normalize_money(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"

    text = str(value).strip()
    if not text:
        return ""

    match = _NUMBER_RE.search(text)
    if not match:
        return ""

    numeric_text = match.group(0).replace(",", "")
    try:
        return f"{float(numeric_text):.2f}"
    except ValueError:
        return ""


def _strip_trailing_zeros(value: str) -> str:
    if "." not in value:
        return value
    value = value.rstrip("0")
    return value[:-1] if value.endswith(".") else value
