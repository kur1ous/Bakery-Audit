from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Protocol

from google import genai
from google.genai import types
from pydantic import ValidationError

from .models import BetExtraction
from .odds_models import OddsExtractionBatch

LOGGER = logging.getLogger(__name__)

PROMPT = """
You are extracting a single primary accepted sports bet from a screenshot.
Return strict JSON only with no markdown fences and no extra text.
Schema:
{
  "date": "string",
  "team": "string",
  "against": "string",
  "odds": "string|number",
  "stake": "string|number",
  "return": "string|number",
  "confidence": 0.0,
  "missing_fields": ["date|team|against|odds|stake|return_amount"],
  "readable_summary": "short sentence summary"
}
Rules:
- Extract a single accepted bet slip if present.
- Use empty string for unknown values.
- team and against should be 3-letter team codes whenever possible (for example: TOR, BOS, GSW).
- confidence must be between 0 and 1.
- missing_fields must list required fields still missing.
- If date not visible, leave empty.
""".strip()

ODDS_PROMPT = """
You are extracting moneyline odds candidates from sportsbook screenshot(s).
Return strict JSON only with no markdown fences and no extra text.
Schema:
{
  "site": "string",
  "bets": [
    {
      "date": "string",
      "team": "string",
      "against": "string",
      "odds": "string|number",
      "market": "moneyline",
      "site": "string",
      "source_image": "string",
      "confidence": 0.0,
      "missing_fields": ["date|team|against|odds"],
      "readable_summary": "short sentence"
    }
  ],
  "readable_summary": "short summary"
}
Rules:
- Extract as many valid moneyline candidates as visible.
- Ignore spreads/totals/props in this phase.
- Keep team/against as 3-letter codes when possible.
- Use empty strings for unknown values.
- confidence is 0..1.
- Determine `site` from the browser URL/domain if visible (highest priority), then sportsbook branding.
- If URL shows cloudbet.com use "cloudbet". If xbet.ag/1xbet use "xbet". If mybookie use "mybookie".
- All bets in one image should normally have the same site as the image-level site.
""".strip()


class ExtractionService(Protocol):
    def extract_from_image(self, image_bytes: bytes, mime_type: str) -> BetExtraction:
        ...

    def extract_odds_from_image(self, image_bytes: bytes, mime_type: str, source_image: str = "") -> OddsExtractionBatch:
        ...


class GeminiExtractionError(RuntimeError):
    pass


class GeminiExtractionService:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        *,
        api_keys: list[str] | tuple[str, ...] | None = None,
        client_factory: Callable[..., Any] = genai.Client,
    ) -> None:
        keys = _normalize_api_keys(api_key=api_key, api_keys=api_keys)
        self._clients = [client_factory(api_key=key) for key in keys]
        self._model_name = model_name

    def extract_from_image(self, image_bytes: bytes, mime_type: str) -> BetExtraction:
        try:
            response = self._generate_content_with_failover(
                contents=[
                    PROMPT,
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ]
            )
        except Exception as exc:
            raise GeminiExtractionError(f"Gemini request failed: {exc}") from exc

        raw_text = (response.text or "").strip()
        if not raw_text:
            raise GeminiExtractionError("Gemini returned an empty response")

        try:
            payload = _extract_json(raw_text)
            extraction = BetExtraction.model_validate(payload)
            extraction.raw_text = raw_text
            return extraction
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            LOGGER.exception("Failed to parse Gemini extraction payload")
            raise GeminiExtractionError(f"Gemini response parse failed: {exc}") from exc

    def extract_odds_from_image(self, image_bytes: bytes, mime_type: str, source_image: str = "") -> OddsExtractionBatch:
        try:
            response = self._generate_content_with_failover(
                contents=[
                    ODDS_PROMPT,
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ]
            )
        except Exception as exc:
            raise GeminiExtractionError(f"Gemini request failed: {exc}") from exc

        raw_text = (response.text or "").strip()
        if not raw_text:
            raise GeminiExtractionError("Gemini returned an empty response")

        try:
            payload = _extract_json(raw_text)
            batch = OddsExtractionBatch.model_validate(payload)
            batch.raw_text = raw_text

            image_site = batch.site
            for candidate in batch.bets:
                if not candidate.source_image and source_image:
                    candidate.source_image = source_image
                if image_site:
                    candidate.site = image_site

            return batch
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            LOGGER.exception("Failed to parse Gemini odds payload")
            raise GeminiExtractionError(f"Gemini response parse failed: {exc}") from exc

    def _generate_content_with_failover(self, *, contents: list[Any]) -> Any:
        last_error: Exception | None = None
        for idx, client in enumerate(self._clients):
            try:
                return client.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                    ),
                )
            except Exception as exc:
                last_error = exc
                has_next = idx < (len(self._clients) - 1)
                if has_next and _is_retryable_key_error(exc):
                    LOGGER.warning("Gemini key %d failed with retryable error; trying fallback key", idx + 1)
                    continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError("No Gemini clients configured")


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Gemini response")
    return json.loads(match.group(0))


def _normalize_api_keys(*, api_key: str, api_keys: list[str] | tuple[str, ...] | None) -> list[str]:
    keys: list[str] = []

    def _append(value: str) -> None:
        key = (value or "").strip()
        if key and key not in keys:
            keys.append(key)

    _append(api_key)
    for value in api_keys or []:
        _append(value)

    if not keys:
        raise ValueError("At least one Gemini API key is required")

    return keys


def _is_retryable_key_error(exc: Exception) -> bool:
    text = str(exc).lower()
    retry_markers = (
        "quota",
        "resource_exhausted",
        "rate limit",
        "too many requests",
        "429",
        "unavailable",
        "temporarily unavailable",
    )
    return any(marker in text for marker in retry_markers)
