from __future__ import annotations

import asyncio
import re

import discord

from .confirmation_log import ConfirmationLogContext, ConfirmationLogger
from .models import BetExtraction
from .state import PendingBetStore

CURRENCY_USD = "USD"
CURRENCY_CAD = "CAD"


def build_extraction_embed(
    extractions: list[BetExtraction],
    *,
    confirmed: bool,
    canceled: bool = False,
    has_hedge_pair: bool,
    bet_currencies: list[str],
    usd_to_cad_rate: float,
) -> discord.Embed:
    needs_review = any(item.needs_review for item in extractions)

    if canceled:
        color = discord.Color.dark_grey()
        status = "Canceled"
    elif confirmed:
        color = discord.Color.blue()
        status = "Confirmed"
    elif needs_review:
        color = discord.Color.orange()
        status = "Needs review"
    else:
        color = discord.Color.green()
        status = "Ready"

    embed = discord.Embed(title=f"EV Bet Extraction ({len(extractions)} Bets)", color=color)

    currency_lines = []
    for index, extraction in enumerate(extractions, start=1):
        currency = _currency_for_index(bet_currencies, index - 1)
        lines = [
            f"Date: {extraction.display_date}",
            f"Team: {extraction.team or '(missing)'}",
            f"Against: {extraction.against or '(missing)'}",
            f"Odds: {extraction.odds or '(missing)'}",
            f"Stake: {_format_money_display(extraction.stake, currency, usd_to_cad_rate)}",
            f"Return: {_format_money_display(extraction.return_amount, currency, usd_to_cad_rate)}",
        ]
        if extraction.missing_fields:
            lines.append(f"Missing: {', '.join(extraction.missing_fields)}")

        currency_lines.append(f"Bet {index}: {currency}")
        embed.add_field(name=f"Bet {index}", value="\n".join(lines), inline=False)

    if has_hedge_pair:
        embed.add_field(
            name="Pair Detection",
            value="Potential Hedge/Arb Pair Detected",
            inline=False,
        )

    embed.add_field(name="Currency", value=" | ".join(currency_lines), inline=False)

    combined_summary = "\n".join(
        f"Bet {index}: {extraction.readable_summary or '(none)'}"
        for index, extraction in enumerate(extractions, start=1)
    )
    embed.add_field(name="Model Summary", value=combined_summary[:1024] or "(none)", inline=False)
    embed.add_field(name="Status", value=status, inline=False)
    if canceled:
        embed.set_footer(text="Extraction canceled. Send a new image + mention to restart.")
    else:
        embed.set_footer(text="Use picker + edit buttons to adjust selected bet before confirming.")
    return embed


class BetSelection(discord.ui.Select):
    def __init__(self, total_bets: int) -> None:
        options = [
            discord.SelectOption(label=f"Bet {idx}", value=str(idx - 1))
            for idx in range(1, min(total_bets, 25) + 1)
        ]
        super().__init__(
            placeholder="Choose bet to edit",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="evbet:select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not isinstance(view, ExtractionView):
            await interaction.response.send_message("Selection state unavailable.", ephemeral=True)
            return

        if not await view.authorize(interaction):
            return

        view.selected_bet_index = int(self.values[0])
        view._sync_currency_button_label()
        await interaction.response.edit_message(view=view)


class EditBetModal(discord.ui.Modal, title="Edit Selected Bet"):
    def __init__(
        self,
        store: PendingBetStore,
        confirmation_logger: ConfirmationLogger,
        message_id: int,
        user_id: int,
        bet_index: int,
        usd_to_cad_rate: float,
    ) -> None:
        super().__init__(timeout=300)
        self.store = store
        self.confirmation_logger = confirmation_logger
        self.message_id = message_id
        self.user_id = user_id
        self.bet_index = bet_index
        self.usd_to_cad_rate = usd_to_cad_rate

        pending = self.store.get(message_id)
        if pending and 0 <= bet_index < len(pending.extractions):
            extraction = pending.extractions[bet_index]
        else:
            extraction = BetExtraction()

        self.date_input = discord.ui.TextInput(label="Date", default=extraction.date, required=False, max_length=100)
        self.team_input = discord.ui.TextInput(label="Team", default=extraction.team, required=False, max_length=100)
        self.against_input = discord.ui.TextInput(
            label="Against", default=extraction.against, required=False, max_length=100
        )
        self.odds_input = discord.ui.TextInput(label="Odds", default=extraction.odds, required=False, max_length=50)
        self.stake_input = discord.ui.TextInput(label="Stake", default=extraction.stake, required=False, max_length=50)

        self.add_item(self.date_input)
        self.add_item(self.team_input)
        self.add_item(self.against_input)
        self.add_item(self.odds_input)
        self.add_item(self.stake_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id or not self.store.is_authorized(self.message_id, interaction.user.id):
            await interaction.response.send_message("Only the original user can edit this extraction.", ephemeral=True)
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This extraction session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("This extraction has already been confirmed.", ephemeral=True)
            return

        if not (0 <= self.bet_index < len(pending.extractions)):
            await interaction.response.send_message("Selected bet is out of range.", ephemeral=True)
            return

        payload = pending.extractions[self.bet_index].model_dump(by_alias=True)
        payload.update(
            {
                "date": self.date_input.value,
                "team": self.team_input.value,
                "against": self.against_input.value,
                "odds": self.odds_input.value,
                "stake": self.stake_input.value,
            }
        )

        pending.extractions[self.bet_index] = BetExtraction.model_validate(payload)
        pending.has_hedge_pair = detect_hedge_pair(pending.extractions)

        embed = build_extraction_embed(
            pending.extractions,
            confirmed=False,
            has_hedge_pair=pending.has_hedge_pair,
            bet_currencies=pending.bet_currencies,
            usd_to_cad_rate=self.usd_to_cad_rate,
        )
        view = ExtractionView(self.store, self.confirmation_logger, self.message_id, self.usd_to_cad_rate)
        view.selected_bet_index = min(self.bet_index, max(len(pending.extractions) - 1, 0))
        view._sync_currency_button_label()
        await interaction.response.edit_message(embed=embed, view=view)


class EditReturnModal(discord.ui.Modal, title="Edit Return"):
    def __init__(
        self,
        store: PendingBetStore,
        confirmation_logger: ConfirmationLogger,
        message_id: int,
        user_id: int,
        bet_index: int,
        usd_to_cad_rate: float,
    ) -> None:
        super().__init__(timeout=300)
        self.store = store
        self.confirmation_logger = confirmation_logger
        self.message_id = message_id
        self.user_id = user_id
        self.bet_index = bet_index
        self.usd_to_cad_rate = usd_to_cad_rate

        pending = self.store.get(message_id)
        if pending and 0 <= bet_index < len(pending.extractions):
            extraction = pending.extractions[bet_index]
        else:
            extraction = BetExtraction()

        self.return_input = discord.ui.TextInput(
            label="Return",
            default=extraction.return_amount,
            required=False,
            max_length=50,
        )
        self.add_item(self.return_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.user_id or not self.store.is_authorized(self.message_id, interaction.user.id):
            await interaction.response.send_message("Only the original user can edit this extraction.", ephemeral=True)
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This extraction session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("This extraction has already been confirmed.", ephemeral=True)
            return

        if not (0 <= self.bet_index < len(pending.extractions)):
            await interaction.response.send_message("Selected bet is out of range.", ephemeral=True)
            return

        payload = pending.extractions[self.bet_index].model_dump(by_alias=True)
        payload.update({"return": self.return_input.value})

        pending.extractions[self.bet_index] = BetExtraction.model_validate(payload)
        pending.has_hedge_pair = detect_hedge_pair(pending.extractions)

        embed = build_extraction_embed(
            pending.extractions,
            confirmed=False,
            has_hedge_pair=pending.has_hedge_pair,
            bet_currencies=pending.bet_currencies,
            usd_to_cad_rate=self.usd_to_cad_rate,
        )
        view = ExtractionView(self.store, self.confirmation_logger, self.message_id, self.usd_to_cad_rate)
        view.selected_bet_index = min(self.bet_index, max(len(pending.extractions) - 1, 0))
        view._sync_currency_button_label()
        await interaction.response.edit_message(embed=embed, view=view)


class ExtractionView(discord.ui.View):
    def __init__(
        self,
        store: PendingBetStore,
        confirmation_logger: ConfirmationLogger,
        message_id: int,
        usd_to_cad_rate: float,
    ) -> None:
        super().__init__(timeout=900)
        self.store = store
        self.confirmation_logger = confirmation_logger
        self.message_id = message_id
        self.usd_to_cad_rate = usd_to_cad_rate
        self.selected_bet_index = 0

        pending = self.store.get(message_id)
        total_bets = len(pending.extractions) if pending else 0
        if total_bets > 1:
            self.add_item(BetSelection(total_bets=total_bets))
        self._sync_currency_button_label()

    def _deny_message(self) -> str:
        return "Only the user who triggered this parse can use these buttons."

    async def authorize(self, interaction: discord.Interaction) -> bool:
        if not self.store.is_authorized(self.message_id, interaction.user.id):
            await interaction.response.send_message(self._deny_message(), ephemeral=True)
            return False
        return True

    def _sync_currency_button_label(self) -> None:
        pending = self.store.get(self.message_id)
        selected_currency = _currency_for_index(
            pending.bet_currencies if pending else [],
            self.selected_bet_index,
        )
        next_currency = CURRENCY_CAD if selected_currency == CURRENCY_USD else CURRENCY_USD

        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "evbet:currency":
                child.label = f"Switch Bet {self.selected_bet_index + 1} to {next_currency}"
                break

    @discord.ui.button(label="Edit Selected", style=discord.ButtonStyle.secondary, custom_id="evbet:edit")
    async def edit_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.authorize(interaction):
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This extraction session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("This extraction is already confirmed.", ephemeral=True)
            return

        if self.selected_bet_index >= len(pending.extractions):
            self.selected_bet_index = 0

        modal = EditBetModal(
            self.store,
            self.confirmation_logger,
            self.message_id,
            interaction.user.id,
            self.selected_bet_index,
            self.usd_to_cad_rate,
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Edit Return", style=discord.ButtonStyle.secondary, custom_id="evbet:editreturn")
    async def edit_return_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.authorize(interaction):
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This extraction session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("This extraction is already confirmed.", ephemeral=True)
            return

        if self.selected_bet_index >= len(pending.extractions):
            self.selected_bet_index = 0

        modal = EditReturnModal(
            self.store,
            self.confirmation_logger,
            self.message_id,
            interaction.user.id,
            self.selected_bet_index,
            self.usd_to_cad_rate,
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Switch Bet 1 to CAD", style=discord.ButtonStyle.secondary, custom_id="evbet:currency")
    async def currency_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.authorize(interaction):
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This extraction session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("This extraction is already confirmed.", ephemeral=True)
            return

        if self.selected_bet_index >= len(pending.extractions):
            self.selected_bet_index = 0

        if len(pending.bet_currencies) < len(pending.extractions):
            pending.bet_currencies = [CURRENCY_USD for _ in pending.extractions]

        current = _currency_for_index(pending.bet_currencies, self.selected_bet_index)
        pending.bet_currencies[self.selected_bet_index] = CURRENCY_CAD if current == CURRENCY_USD else CURRENCY_USD
        self._sync_currency_button_label()

        embed = build_extraction_embed(
            pending.extractions,
            confirmed=False,
            has_hedge_pair=pending.has_hedge_pair,
            bet_currencies=pending.bet_currencies,
            usd_to_cad_rate=self.usd_to_cad_rate,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Confirm All", style=discord.ButtonStyle.success, custom_id="evbet:confirm")
    async def confirm_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.authorize(interaction):
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This extraction session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("Already confirmed.", ephemeral=True)
            return

        # Acknowledge quickly to avoid Discord's 3-second interaction timeout while Sheets I/O runs.
        await interaction.response.defer()

        context = ConfirmationLogContext(
            message_id=self.message_id,
            channel_id=interaction.channel_id,
            guild_id=interaction.guild_id,
            invoker_user_id=interaction.user.id,
            has_hedge_pair=pending.has_hedge_pair,
        )

        try:
            logged_rows = await asyncio.to_thread(
                self.confirmation_logger.log_batch,
                context,
                pending.extractions,
                pending.bet_currencies,
                self.usd_to_cad_rate,
            )
        except Exception as exc:
            await interaction.followup.send(
                f"Failed to log confirmation to spreadsheet: {exc}",
                ephemeral=True,
            )
            return

        pending.confirmed = True
        embed = build_extraction_embed(
            pending.extractions,
            confirmed=True,
            has_hedge_pair=pending.has_hedge_pair,
            bet_currencies=pending.bet_currencies,
            usd_to_cad_rate=self.usd_to_cad_rate,
        )

        for child in self.children:
            child.disabled = True

        await interaction.edit_original_response(embed=embed, view=self)
        await interaction.followup.send(
            f"{interaction.user.mention} confirmed this extraction batch. Logged {logged_rows} row(s).",
            allowed_mentions=discord.AllowedMentions(users=[interaction.user]),
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="evbet:cancel")
    async def cancel_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.authorize(interaction):
            return

        pending = self.store.get(self.message_id)
        if not pending:
            await interaction.response.send_message("This extraction session has expired.", ephemeral=True)
            return

        if pending.confirmed:
            await interaction.response.send_message("This extraction is already confirmed.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        embed = build_extraction_embed(
            pending.extractions,
            confirmed=False,
            canceled=True,
            has_hedge_pair=pending.has_hedge_pair,
            bet_currencies=pending.bet_currencies,
            usd_to_cad_rate=self.usd_to_cad_rate,
        )

        self.store.delete(self.message_id)
        await interaction.response.edit_message(embed=embed, view=self)

def detect_hedge_pair(extractions: list[BetExtraction]) -> bool:
    for i in range(len(extractions)):
        for j in range(i + 1, len(extractions)):
            left = extractions[i]
            right = extractions[j]
            if _is_opposite_side_same_match(left, right):
                return True
    return False


def _is_opposite_side_same_match(left: BetExtraction, right: BetExtraction) -> bool:
    left_team = _normalize_team(left.team)
    left_against = _normalize_team(left.against)
    right_team = _normalize_team(right.team)
    right_against = _normalize_team(right.against)

    if not all([left_team, left_against, right_team, right_against]):
        return False

    if {left_team, left_against} != {right_team, right_against}:
        return False

    return left_team == right_against and left_against == right_team


def _normalize_team(value: str) -> str:
    lowered = value.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _format_money_display(raw_value: str, display_currency: str, usd_to_cad_rate: float) -> str:
    value = (raw_value or "").strip()
    if not value:
        return "(missing)"

    parsed = _parse_money(value)
    if parsed is None:
        return value

    # Currency toggle represents source-currency tagging for logging, not UI conversion.
    # Keep the extracted numeric amount stable in the embed and only relabel currency.
    return f"{display_currency} {parsed:.2f}"


def _parse_money(value: str) -> float | None:
    cleaned = value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _currency_for_index(currencies: list[str], idx: int) -> str:
    if 0 <= idx < len(currencies):
        candidate = currencies[idx]
        if candidate in (CURRENCY_USD, CURRENCY_CAD):
            return candidate
    return CURRENCY_USD