from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Iterable

import discord
from discord.ext import commands

from .config import Settings
from .confirmation_log import ConfirmationLogger
from .discord_ui import CURRENCY_USD, ExtractionView, build_extraction_embed, detect_hedge_pair
from .gemini_client import ExtractionService, GeminiExtractionError
from .odds_models import OddsCandidate
from .odds_pipeline import OddsPipelineWriter
from .odds_ui import OddsExtractionView, build_odds_review_embed
from .state import PendingBetBatch, PendingBetStore, PendingOddsBatch, PendingOddsStore

LOGGER = logging.getLogger(__name__)


class EVBetBot(commands.Bot):
    def __init__(
        self,
        settings: Settings,
        extraction_service: ExtractionService,
        confirmation_logger: ConfirmationLogger,
        odds_pipeline: OddsPipelineWriter | None,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=intents)
        self.settings = settings
        self.extraction_service = extraction_service
        self.confirmation_logger = confirmation_logger
        self.odds_pipeline = odds_pipeline
        self.pending_store = PendingBetStore()
        self.pending_odds_store = PendingOddsStore()

    async def setup_hook(self) -> None:
        LOGGER.info("Bot setup complete")

    async def on_ready(self) -> None:
        if not self.user:
            return
        LOGGER.info("Logged in as %s (%s)", self.user.name, self.user.id)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if not self.user:
            return

        is_mentioned = self.user in message.mentions
        if not is_mentioned:
            await self.process_commands(message)
            return

        if _is_help_request(message.content):
            await message.reply(_help_message(), mention_author=False)
            await self.process_commands(message)
            return

        if _is_devlog_request(message.content):
            await _send_devlog(message)
            await self.process_commands(message)
            return

        if _is_odds_request(message.content):
            await self._handle_odds_request(message)
            await self.process_commands(message)
            return

        await self._handle_standard_request(message)
        await self.process_commands(message)

    async def _handle_standard_request(self, message: discord.Message) -> None:
        image_attachments = _image_attachments(message.attachments)
        if not image_attachments:
            await message.reply(
                "Please tag me with at least one image attachment so I can extract bet fields. Try `@bot help` for usage.",
                mention_author=False,
            )
            return

        extractions = []
        failed_files = []

        async with message.channel.typing():
            for attachment in image_attachments:
                try:
                    image_bytes = await attachment.read()
                    mime_type = attachment.content_type or _guess_mime_type(attachment.filename)
                    if not mime_type.startswith("image/"):
                        raise ValueError("Attachment is not an image")

                    extraction = await asyncio.to_thread(
                        self.extraction_service.extract_from_image,
                        image_bytes,
                        mime_type,
                    )
                    extractions.append(extraction)
                except GeminiExtractionError as exc:
                    LOGGER.warning("Gemini extraction failed for %s: %s", attachment.filename, exc)
                    failed_files.append(attachment.filename or "unknown-file")
                except Exception:  # pragma: no cover - unexpected runtime path
                    LOGGER.exception("Unexpected extraction failure for %s", attachment.filename)
                    failed_files.append(attachment.filename or "unknown-file")

        if not extractions:
            await message.reply(
                "I could not extract any valid bet data from the provided image(s).",
                mention_author=False,
            )
            return

        has_hedge_pair = detect_hedge_pair(extractions)
        bet_currencies = [CURRENCY_USD for _ in extractions]
        embed = build_extraction_embed(
            extractions,
            confirmed=False,
            has_hedge_pair=has_hedge_pair,
            bet_currencies=bet_currencies,
            usd_to_cad_rate=self.settings.usd_to_cad_rate,
        )
        placeholder = await message.reply(embed=embed, mention_author=False)

        self.pending_store.save(
            placeholder.id,
            PendingBetBatch(
                invoker_id=message.author.id,
                extractions=extractions,
                has_hedge_pair=has_hedge_pair,
                bet_currencies=bet_currencies,
            ),
        )

        view = ExtractionView(
            self.pending_store,
            self.confirmation_logger,
            placeholder.id,
            self.settings.usd_to_cad_rate,
        )
        await placeholder.edit(view=view)

        if failed_files:
            joined = ", ".join(failed_files)
            await message.reply(
                f"Processed {len(extractions)} image(s). Failed to parse: {joined}",
                mention_author=False,
            )

    async def _handle_odds_request(self, message: discord.Message) -> None:
        if not self.settings.odds_enabled or not self.odds_pipeline:
            await message.reply("Odds flow is currently disabled by configuration.", mention_author=False)
            return

        image_attachments = _image_attachments(message.attachments)
        if not image_attachments:
            await message.reply(
                "For odds automation, send `@bot odds` with at least one screenshot attachment.",
                mention_author=False,
            )
            return

        candidates: list[OddsCandidate] = []
        failed_files: list[str] = []

        async with message.channel.typing():
            for attachment in image_attachments:
                try:
                    image_bytes = await attachment.read()
                    mime_type = attachment.content_type or _guess_mime_type(attachment.filename)
                    if not mime_type.startswith("image/"):
                        raise ValueError("Attachment is not an image")

                    batch = await asyncio.to_thread(
                        self.extraction_service.extract_odds_from_image,
                        image_bytes,
                        mime_type,
                        attachment.filename or "",
                    )
                    candidates.extend(batch.bets)
                except GeminiExtractionError as exc:
                    LOGGER.warning("Gemini odds extraction failed for %s: %s", attachment.filename, exc)
                    failed_files.append(attachment.filename or "unknown-file")
                except Exception:  # pragma: no cover - unexpected runtime path
                    LOGGER.exception("Unexpected odds extraction failure for %s", attachment.filename)
                    failed_files.append(attachment.filename or "unknown-file")

        if not candidates:
            await message.reply(
                "I could not extract any valid moneyline odds candidates from the provided image(s).",
                mention_author=False,
            )
            return

        embed = build_odds_review_embed(
            candidates,
            confirmed=False,
            failed_files=failed_files,
        )
        placeholder = await message.reply(embed=embed, mention_author=False)

        self.pending_odds_store.save(
            placeholder.id,
            PendingOddsBatch(
                invoker_id=message.author.id,
                candidates=candidates,
                failed_files=failed_files,
            ),
        )

        view = OddsExtractionView(
            self.pending_odds_store,
            self.odds_pipeline,
            placeholder.id,
        )
        await placeholder.edit(view=view)


async def _send_devlog(message: discord.Message) -> None:
    devlog_path = _devlog_path()
    if not devlog_path.exists():
        await message.reply("Development log not found at docs/DEVLOG.md", mention_author=False)
        return

    await message.reply(
        "Current development log attached.",
        file=discord.File(str(devlog_path), filename="DEVLOG.md"),
        mention_author=False,
    )


def _devlog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "DEVLOG.md"


def _is_help_request(content: str) -> bool:
    normalized = _normalize_mention_text(content)
    if not normalized:
        return False
    parts = normalized.split()
    return bool(parts) and parts[0] == "help"


def _is_devlog_request(content: str) -> bool:
    normalized = _normalize_mention_text(content)
    if not normalized:
        return False
    parts = normalized.split()
    return bool(parts) and parts[0] == "devlog"


def _is_odds_request(content: str) -> bool:
    normalized = _normalize_mention_text(content)
    if not normalized:
        return False
    parts = normalized.split()
    return bool(parts) and parts[0] == "odds"


def _normalize_mention_text(content: str) -> str:
    text = re.sub(r"<@!?\d+>", " ", content or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _help_message() -> str:
    return (
        "EV Bet Extractor Help\n"
        "1. Mention me with one or more betting screenshots in the same message.\n"
        "2. I will parse each image and return a combined embed with bet fields.\n"
        "3. Use `Edit Selected` (and `Edit Return`) before pressing `Confirm All`.\n"
        "4. Use `Switch Bet X to CAD/USD` to set the selected bet currency tag.\n"
        "5. Confirm writes one row per bet into your configured spreadsheet log.\n"
        "6. Use `@bot odds` with screenshot(s) to run moneyline odds automation (raw -> clean -> ranked).\n"
        "7. Use `@bot devlog` to get the full development log."
    )


def _image_attachments(attachments: Iterable[discord.Attachment]) -> list[discord.Attachment]:
    results = []
    for attachment in attachments:
        content_type = (attachment.content_type or "").lower()
        if content_type.startswith("image/"):
            results.append(attachment)
            continue

        filename = (attachment.filename or "").lower()
        if filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
            results.append(attachment)
    return results


def _guess_mime_type(filename: str | None) -> str:
    if not filename:
        return "application/octet-stream"
    lowered = filename.lower()
    if lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
        return "image/jpeg"
    if lowered.endswith(".webp"):
        return "image/webp"
    if lowered.endswith(".gif"):
        return "image/gif"
    if lowered.endswith(".bmp"):
        return "image/bmp"
    return "application/octet-stream"
