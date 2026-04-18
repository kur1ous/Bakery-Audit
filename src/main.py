from __future__ import annotations

import logging

from .bot.app import EVBetBot
from .bot.config import load_settings
from .bot.confirmation_log import create_confirmation_logger
from .bot.gemini_client import GeminiExtractionService
from .bot.odds_pipeline import create_odds_pipeline


def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    extraction_service = GeminiExtractionService(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
    )
    confirmation_logger = create_confirmation_logger(
        backend=settings.confirm_log_backend,
        excel_path=settings.confirm_excel_path,
        google_sheet_id=settings.confirm_google_sheet_id,
        google_credentials_json_path=settings.confirm_google_credentials_json,
        google_worksheet_name=settings.confirm_google_worksheet_name,
    )
    odds_pipeline = create_odds_pipeline(
        enabled=settings.odds_enabled,
        spreadsheet_id=settings.confirm_google_sheet_id,
        credentials_json_path=settings.confirm_google_credentials_json,
        raw_worksheet_name=settings.odds_raw_worksheet,
        clean_worksheet_name=settings.odds_clean_worksheet,
        ranked_worksheet_name=settings.odds_ranked_worksheet,
    )
    bot = EVBetBot(
        settings=settings,
        extraction_service=extraction_service,
        confirmation_logger=confirmation_logger,
        odds_pipeline=odds_pipeline,
    )
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
