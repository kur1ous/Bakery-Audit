from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    discord_token: str
    gemini_api_key: str
    gemini_api_keys: tuple[str, ...]
    gemini_model: str = "gemini-2.5-flash"
    log_level: str = "INFO"
    confirm_log_backend: str = "excel"
    confirm_excel_path: str = "data/confirmed_bets.xlsx"
    confirm_google_sheet_id: str = ""
    confirm_google_credentials_json: str = ""
    confirm_google_worksheet_name: str = "confirmed_bets"
    usd_to_cad_rate: float = 1.36
    odds_enabled: bool = True
    odds_raw_worksheet: str = "odds_raw"
    odds_clean_worksheet: str = "odds_clean"
    odds_ranked_worksheet: str = "odds_ranked"


def load_settings() -> Settings:
    load_dotenv()

    discord_token = os.getenv("DISCORD_TOKEN", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_api_key_2 = os.getenv("GEMINI_API_KEY_2", "").strip()
    gemini_api_key2 = os.getenv("GEMINI_API_KEY2", "").strip()
    gemini_api_key_secondary = os.getenv("GEMINI_API_KEY_SECONDARY", "").strip()
    gemini_api_key_fallback = os.getenv("GEMINI_API_KEY_FALLBACK", "").strip()
    gemini_api_key_backup = os.getenv("GEMINI_API_KEY_BACKUP", "").strip()
    gemini_api_keys_csv = os.getenv("GEMINI_API_KEYS", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    log_level = os.getenv("LOG_LEVEL", "INFO").strip() or "INFO"

    confirm_log_backend = os.getenv("CONFIRM_LOG_BACKEND", "excel").strip() or "excel"
    confirm_excel_path = os.getenv("CONFIRM_EXCEL_PATH", "data/confirmed_bets.xlsx").strip() or "data/confirmed_bets.xlsx"
    confirm_google_sheet_id = os.getenv("CONFIRM_GOOGLE_SHEET_ID", "").strip()
    confirm_google_credentials_json = os.getenv("CONFIRM_GOOGLE_CREDENTIALS_JSON", "").strip()
    confirm_google_worksheet_name = (
        os.getenv("CONFIRM_GOOGLE_WORKSHEET", "confirmed_bets").strip() or "confirmed_bets"
    )

    usd_to_cad_rate_raw = os.getenv("USD_TO_CAD_RATE", "1.36").strip() or "1.36"
    try:
        usd_to_cad_rate = float(usd_to_cad_rate_raw)
    except ValueError:
        raise RuntimeError("USD_TO_CAD_RATE must be a valid number") from None

    odds_enabled_raw = (os.getenv("ODDS_ENABLED", "true").strip() or "true").lower()
    odds_enabled = odds_enabled_raw in ("1", "true", "yes", "on")
    odds_raw_worksheet = os.getenv("ODDS_RAW_WORKSHEET", "odds_raw").strip() or "odds_raw"
    odds_clean_worksheet = os.getenv("ODDS_CLEAN_WORKSHEET", "odds_clean").strip() or "odds_clean"
    odds_ranked_worksheet = os.getenv("ODDS_RANKED_WORKSHEET", "odds_ranked").strip() or "odds_ranked"

    missing = []
    if not discord_token:
        missing.append("DISCORD_TOKEN")
    if not gemini_api_key:
        missing.append("GEMINI_API_KEY")

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variables: {joined}")

    ordered_keys: list[str] = []

    def _append_key(key: str) -> None:
        value = key.strip()
        if value and value not in ordered_keys:
            ordered_keys.append(value)

    _append_key(gemini_api_key)
    _append_key(gemini_api_key_2)
    _append_key(gemini_api_key2)
    _append_key(gemini_api_key_secondary)
    _append_key(gemini_api_key_fallback)
    _append_key(gemini_api_key_backup)
    if gemini_api_keys_csv:
        for key in gemini_api_keys_csv.split(","):
            _append_key(key)

    return Settings(
        discord_token=discord_token,
        gemini_api_key=gemini_api_key,
        gemini_api_keys=tuple(ordered_keys),
        gemini_model=gemini_model,
        log_level=log_level,
        confirm_log_backend=confirm_log_backend,
        confirm_excel_path=confirm_excel_path,
        confirm_google_sheet_id=confirm_google_sheet_id,
        confirm_google_credentials_json=confirm_google_credentials_json,
        confirm_google_worksheet_name=confirm_google_worksheet_name,
        usd_to_cad_rate=usd_to_cad_rate,
        odds_enabled=odds_enabled,
        odds_raw_worksheet=odds_raw_worksheet,
        odds_clean_worksheet=odds_clean_worksheet,
        odds_ranked_worksheet=odds_ranked_worksheet,
    )
