from __future__ import annotations

import asyncio

import discord

from .odds_models import OddsCandidate
from .odds_pipeline import OddsPipelineContext, OddsPipelineWriter, OddsRecommendation
from .state import PendingOddsStore


def build_odds_review_embed(
    candidates: list[OddsCandidate],
    *,
    confirmed: bool,
    failed_files: list[str],
    odds_mode: str = "both",
) -> discord.Embed:
    needs_review = any(item.needs_review for item in candidates)

    if confirmed:
        color = discord.Color.blue()
        status = "Confirmed"
    elif needs_review:
        color = discord.Color.orange()
        status = "Needs review"
    else:
        color = discord.Color.green()
        status = "Ready"

    embed = discord.Embed(title=f"Odds Extraction Review ({len(candidates)} Rows)", color=color)

    preview = []
    for idx, candidate in enumerate(candidates[:10], start=1):
        line = (
            f"{idx}. {candidate.date} | {candidate.team} vs {candidate.against} | "
            f"{candidate.market} | {candidate.site or 'unknown-site'} | odds {candidate.odds or '(missing)'}"
        )
        preview.append(line)

    embed.add_field(name="Preview", value="\n".join(preview) or "(no rows)", inline=False)

    site_counts: dict[str, int] = {}
    for item in candidates:
        key = item.site or "unknown-site"
        site_counts[key] = site_counts.get(key, 0) + 1
    site_summary = " | ".join(f"{k}: {v}" for k, v in sorted(site_counts.items()))
    embed.add_field(name="Site Breakdown", value=site_summary or "(none)", inline=False)

    if failed_files:
        embed.add_field(name="Failed Files", value=", ".join(failed_files), inline=False)

    missing_count = sum(1 for item in candidates if item.missing_fields)
    embed.add_field(name="Needs Review Rows", value=str(missing_count), inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Mode", value=odds_mode.upper(), inline=True)
    embed.set_footer(text="Confirm Odds to write raw/clean/ranked sheets. Cancel to discard.")
    return embed


def build_odds_result_embed(
    recommendations: list[OddsRecommendation],
    *,
    insufficient_data: bool,
    odds_mode: str = "both",
) -> discord.Embed:
    color = discord.Color.green() if recommendations else discord.Color.orange()
    embed = discord.Embed(title="Odds Recommendations", color=color)
    embed.description = "Best underdog/hedge opportunities from this extraction batch."

    def lines(metric: str) -> str:
        picks = [item for item in recommendations if item.metric == metric]
        if not picks:
            return "No picks available"

        out = []
        for pick in picks:
            out.append(_format_pick_block(pick, odds_mode=odds_mode))
        return "\n\n".join(out)

    embed.add_field(name="Top 2 ROI", value=lines("roi"), inline=False)
    embed.add_field(name="Top 2 Profit", value=lines("profit"), inline=False)
    embed.add_field(name="Top 2 Rake (Lowest)", value=lines("rake"), inline=False)

    if insufficient_data:
        embed.add_field(
            name="Note",
            value="Fewer than 2 games were available for one or more metrics.",
            inline=False,
        )

    return embed


def _format_pick_block(pick: OddsRecommendation, *, odds_mode: str = "both") -> str:
    real_if_bet, real_if_hedge, real_floor = _compute_real_outcomes(pick)
    bonus_h_hedge, bonus_if_bet, bonus_if_hedge, bonus_floor = _compute_bonus_outcomes(pick)
    bet_site = pick.bet_site or "unknown-site"
    hedge_site = pick.hedge_site or "unknown-site"
    mode = (odds_mode or "both").strip().lower()

    instructions: list[str] = []
    if mode in ("real", "both"):
        instructions.extend(_build_real_instruction_lines(pick, bet_site, hedge_site, real_floor))
    if mode in ("bonus", "both"):
        instructions.extend(_build_bonus_instruction_lines(pick, bet_site, hedge_site, bonus_floor))
    instructions_text = "\n".join(instructions)

    return (
        f"**{pick.rank}) Bet {pick.bet_team} @ {bet_site}**\n"
        f"{instructions_text}\n"
        f"Date: `{pick.date}`\n"
        f"Odds (bet/hedge): `{pick.odds_bet:.2f} ({bet_site})` / `{pick.odds_hedge:.2f} ({hedge_site})`\n"
        f"T: `{pick.total_bet:.2f}` | r: `{pick.total_return:.2f}`\n"
        f"Real (bet/hedge/floor): `{real_if_bet:.2f}` / `{real_if_hedge:.2f}` / `{real_floor:.2f}`\n"
        f"Bonus h (optimized): `{bonus_h_hedge:.2f}`\n"
        f"Bonus (bet/hedge/floor): `{bonus_if_bet:.2f}` / `{bonus_if_hedge:.2f}` / `{bonus_floor:.2f}`\n"
        f"Status: `{pick.recommendation}` | Net: `{pick.net:.2f}` | ROI: `{pick.roi:.2%}` | Rake: `{pick.rake:.4f}`"
    )

def _compute_real_outcomes(pick: OddsRecommendation) -> tuple[float, float, float]:
    real_if_bet = (pick.b_stake * pick.odds_bet) - pick.total_bet
    real_if_hedge = (pick.h_hedge * pick.odds_hedge) - pick.total_bet
    real_floor = min(real_if_bet, real_if_hedge)
    return real_if_bet, real_if_hedge, real_floor


def _compute_bonus_outcomes(pick: OddsRecommendation) -> tuple[float, float, float, float]:
    # Free-bet style assumption: bonus stake is not returned when bet side wins.
    bonus_h_hedge = 0.0
    if pick.odds_hedge > 0:
        bonus_h_hedge = (pick.b_stake * (pick.odds_bet - 1.0)) / pick.odds_hedge
    bonus_if_bet = (pick.b_stake * (pick.odds_bet - 1.0)) - bonus_h_hedge
    bonus_if_hedge = (bonus_h_hedge * pick.odds_hedge) - bonus_h_hedge
    bonus_floor = min(bonus_if_bet, bonus_if_hedge)
    return bonus_h_hedge, bonus_if_bet, bonus_if_hedge, bonus_floor


def _build_real_instruction_lines(
    pick: OddsRecommendation,
    bet_site: str,
    hedge_site: str,
    floor_value: float,
) -> list[str]:
    result_word = "profit" if floor_value >= 0 else "loss"
    result_amount = abs(floor_value)
    real_total = pick.total_bet
    real_pct = _percent_of_total(floor_value, real_total)
    return [
        f"REAL: On site `{bet_site}`, bet `b={pick.b_stake:.2f}` (`real`) on `{pick.bet_team}`.",
        f"REAL: On site `{hedge_site}`, bet `h={pick.h_hedge:.2f}` (`real`) on `{pick.hedge_team}`.",
        (
            f"REAL: Either way, result is `{result_word}` `{result_amount:.2f}` (floor), "
            f"`{real_pct}` of total real money bet `{real_total:.2f}`."
        ),
    ]


def _build_bonus_instruction_lines(
    pick: OddsRecommendation,
    bet_site: str,
    hedge_site: str,
    floor_value: float,
) -> list[str]:
    bonus_h_hedge, _, _, _ = _compute_bonus_outcomes(pick)
    result_word = "profit" if floor_value >= 0 else "loss"
    result_amount = abs(floor_value)
    real_total = bonus_h_hedge
    real_pct = _percent_of_total(floor_value, real_total)
    return [
        f"BONUS: On site `{bet_site}`, bet `b={pick.b_stake:.2f}` (`bonus`) on `{pick.bet_team}`.",
        f"BONUS: On site `{hedge_site}`, bet `h={bonus_h_hedge:.2f}` (`real`) on `{pick.hedge_team}`.",
        (
            f"BONUS: Either way, result is `{result_word}` `{result_amount:.2f}` (guaranteed worst-case), "
            f"`{real_pct}` of total real cash bet `{real_total:.2f}` (bonus excluded)."
        ),
    ]


def _percent_of_total(value: float, total: float) -> str:
    if total == 0:
        return "0.00%"
    return f"{(value / total):.2%}"

class OddsExtractionView(discord.ui.View):
    def __init__(
        self,
        store: PendingOddsStore,
        odds_pipeline: OddsPipelineWriter,
        message_id: int,
    ) -> None:
        super().__init__(timeout=900)
        self.store = store
        self.odds_pipeline = odds_pipeline
        self.message_id = message_id

    async def _authorize(self, interaction: discord.Interaction) -> bool:
        if not self.store.is_authorized(self.message_id, interaction.user.id):
            await interaction.response.send_message(
                "Only the user who triggered this odds parse can use these buttons.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Confirm Odds", style=discord.ButtonStyle.success, custom_id="odds:confirm")
    async def confirm_odds(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._authorize(interaction):
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This odds session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("This odds session is already confirmed.", ephemeral=True)
            return

        await interaction.response.defer()

        context = OddsPipelineContext(
            session_id=str(self.message_id),
            message_id=self.message_id,
            channel_id=interaction.channel_id,
            guild_id=interaction.guild_id,
            invoker_user_id=interaction.user.id,
        )

        try:
            result = await asyncio.to_thread(
                self.odds_pipeline.process_confirmed,
                context,
                pending.candidates,
            )
        except Exception as exc:
            await interaction.followup.send(f"Failed to process odds pipeline: {exc}", ephemeral=True)
            return

        pending.confirmed = True
        review_embed = build_odds_review_embed(
            pending.candidates,
            confirmed=True,
            failed_files=pending.failed_files,
            odds_mode=pending.odds_mode,
        )
        result_embed = build_odds_result_embed(
            result.recommendations,
            insufficient_data=len(result.recommendations) < 6,
            odds_mode=pending.odds_mode,
        )

        for child in self.children:
            child.disabled = True

        await interaction.edit_original_response(embed=review_embed, view=self)
        await interaction.followup.send(
            embed=result_embed,
            content=(
                f"{interaction.user.mention} confirmed odds extraction. "
                f"Raw: {result.raw_rows_written}, Clean: {result.clean_rows_written}, Ranked: {result.ranked_rows_written}."
            ),
            allowed_mentions=discord.AllowedMentions(users=[interaction.user]),
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="odds:cancel")
    async def cancel_odds(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._authorize(interaction):
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This odds session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("This odds session is already confirmed.", ephemeral=True)
            return

        pending.confirmed = True
        self.store.delete(self.message_id)

        for child in self.children:
            child.disabled = True

        embed = build_odds_review_embed(
            pending.candidates,
            confirmed=False,
            failed_files=pending.failed_files,
            odds_mode=pending.odds_mode,
        )
        embed.color = discord.Color.dark_grey()
        status_idx = next((i for i, f in enumerate(embed.fields) if f.name == "Status"), None)
        if status_idx is not None:
            embed.set_field_at(status_idx, name="Status", value="Canceled", inline=True)
        embed.set_footer(text="Odds extraction canceled. Send @bot odds with images to restart.")
        await interaction.response.edit_message(embed=embed, view=self)


