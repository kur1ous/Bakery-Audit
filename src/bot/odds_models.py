from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .models import normalize_date_or_today, normalize_odds

_REQUIRED_FIELDS = ("date", "team", "against", "odds")


class OddsCandidate(BaseModel):
    date: str = ""
    team: str = ""
    against: str = ""
    odds: str = ""
    market: str = "moneyline"
    total_line: str = ""
    spread_line: str = ""
    site: str = ""
    source_image: str = ""
    confidence: float = 0.0
    missing_fields: list[str] = Field(default_factory=list)
    readable_summary: str = ""
    raw_text: str = ""

    @field_validator("date", "team", "against", "site", "source_image", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("market", mode="before")
    @classmethod
    def _normalize_market(cls, value: Any) -> str:
        raw = "" if value is None else str(value).strip().lower()
        if not raw:
            return "moneyline"

        compact = raw.replace("-", "_").replace(" ", "_")
        if compact in {"moneyline", "money_line", "ml"}:
            return "moneyline"
        if "spread" in compact or "handicap" in compact:
            return "spread"
        if "over" in compact:
            return "total_over"
        if "under" in compact:
            return "total_under"
        return "moneyline"

    @field_validator("odds", mode="before")
    @classmethod
    def _normalize_odds(cls, value: Any) -> str:
        return normalize_odds(value)

    @field_validator("total_line", mode="before")
    @classmethod
    def _normalize_total_line(cls, value: Any) -> str:
        return normalize_odds(value)

    @field_validator("spread_line", mode="before")
    @classmethod
    def _normalize_spread_line(cls, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip().replace(",", "")
        if not text:
            return ""

        sign = "+"
        if text.startswith("-"):
            sign = "-"
            text = text[1:]
        elif text.startswith("+"):
            text = text[1:]

        normalized = normalize_odds(text)
        if not normalized:
            return ""
        return f"{sign}{normalized}"

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
    def _finalize(self) -> "OddsCandidate":
        self.date = normalize_date_or_today(self.date)
        self.team = _to_team_code(self.team)
        self.against = _to_team_code(self.against)
        self.market = (self.market or "moneyline").lower()
        self.site = _normalize_site(self.site or self.source_image)

        if not self.missing_fields:
            self.missing_fields = [field for field in _REQUIRED_FIELDS if not getattr(self, field)]
        else:
            canonical = {field for field in self.missing_fields if field in _REQUIRED_FIELDS}
            for field in _REQUIRED_FIELDS:
                if not getattr(self, field):
                    canonical.add(field)
            self.missing_fields = sorted(canonical)

        if not self.readable_summary:
            line_suffix = ""
            if self.market == "spread" and self.spread_line:
                line_suffix = f" (line {self.spread_line})"
            elif self.total_line:
                line_suffix = f" (line {self.total_line})"
            self.readable_summary = (
                f"{self.team or 'UNK'} vs {self.against or 'UNK'} "
                f"{self.market} at {self.odds or 'unknown'}"
                f"{line_suffix} "
                f"on {self.date} ({self.site or 'unknown site'})."
            )

        return self

    @property
    def needs_review(self) -> bool:
        return bool(self.missing_fields) or self.confidence < 0.75


class OddsExtractionBatch(BaseModel):
    bets: list[OddsCandidate] = Field(default_factory=list)
    site: str = ""
    readable_summary: str = ""
    raw_text: str = ""

    @field_validator("bets", mode="before")
    @classmethod
    def _normalize_bets(cls, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return []

    @field_validator("site", mode="before")
    @classmethod
    def _normalize_batch_site(cls, value: Any) -> str:
        if value is None:
            return ""
        return _normalize_site(str(value))


def _to_team_code(value: str) -> str:
    text = (value or "").strip().upper()
    if not text:
        return ""

    if len(text) == 3 and text.isalnum():
        return text

    normalized = "".join(ch if ch.isalnum() else " " for ch in text)
    tokens = [tok for tok in normalized.split() if tok]
    if not tokens:
        return ""

    first = tokens[0]
    if len(first) >= 3:
        return first[:3]

    compact = "".join(tokens)
    return (compact + "XXX")[:3]


def _normalize_site(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""

    if "cloudbet" in raw or "cloudbet.com" in raw:
        return "cloudbet"
    if "xbet" in raw or "xbet.ag" in raw:
        return "xbet"
    if "mybookie" in raw:
        return "mybookie"

    return raw[:40]
