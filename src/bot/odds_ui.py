from __future__ import annotations

import asyncio
from dataclasses import dataclass

import discord

from .odds_models import OddsCandidate
from .odds_pipeline import OddsPipelineContext, OddsPipelineWriter, OddsRecommendation, select_top_recommendations
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
            f"{candidate.market}{_candidate_line_suffix(candidate)} | "
            f"{candidate.site or 'unknown-site'} | odds {candidate.odds or '(missing)'}"
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
    picks_by_metric, suppressed_by_metric = _select_unique_market_picks_by_metric(recommendations)

    def lines(metric: str) -> str:
        picks = picks_by_metric.get(metric, [])
        if not picks:
            if suppressed_by_metric.get(metric, 0) > 0:
                return "game already mentioned"
            return "No picks available"

        blocks = [_format_pick_block(pick, odds_mode=odds_mode) for pick in picks]
        return _join_blocks_with_limit(blocks, limit=1024)

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


def build_over_under_embed(candidates: list[OddsCandidate], *, odds_mode: str = "both") -> discord.Embed:
    return build_over_under_embeds(candidates, odds_mode=odds_mode)[0]


def build_over_under_embeds(candidates: list[OddsCandidate], *, odds_mode: str = "both") -> list[discord.Embed]:
    analysis = _analyze_over_under_candidates(candidates)
    totals = analysis["totals"]
    recommendations = analysis["ranked"]
    color = discord.Color.green() if recommendations else discord.Color.orange()
    embeds: list[discord.Embed] = [discord.Embed(title="Over/Under Recommendations", color=color)]

    if not totals:
        embeds[0].description = "No Over/Under rows extracted from this batch."
        return embeds

    embeds[0].description = "Best Over/Under hedge opportunities from this extraction batch."
    picks_by_metric, suppressed_by_metric = _select_unique_market_picks_by_metric(recommendations)

    def lines(metric: str) -> list[str]:
        picks = picks_by_metric.get(metric, [])
        if not picks:
            if suppressed_by_metric.get(metric, 0) > 0:
                return ["game already mentioned"]
            return ["No picks available"]
        blocks = [_format_ou_pick_block(pick, odds_mode=odds_mode) for pick in picks]
        return _split_blocks_to_field_chunks(blocks, limit=1024)

    _append_metric_chunks(embeds, "Top 2 ROI", lines("roi"), color=color)
    _append_metric_chunks(embeds, "Top 2 Profit", lines("profit"), color=color)
    _append_metric_chunks(embeds, "Top 2 Rake (Lowest)", lines("rake"), color=color)
    why_no_picks = _build_why_no_picks_note(analysis, market_label="over/under")
    if why_no_picks:
        _append_embed_field(embeds, name="Why No Picks?", value=why_no_picks, color=color)

    if len(recommendations) < 6:
        _append_embed_field(
            embeds,
            name="Note",
            value="Fewer than 2 games were available for one or more metrics.",
            color=color,
        )
    return embeds


def build_spread_embed(candidates: list[OddsCandidate], *, odds_mode: str = "both") -> discord.Embed:
    return build_spread_embeds(candidates, odds_mode=odds_mode)[0]


def build_spread_embeds(candidates: list[OddsCandidate], *, odds_mode: str = "both") -> list[discord.Embed]:
    analysis = _analyze_spread_candidates(candidates)
    recommendations = analysis["ranked"]
    spreads = analysis["spreads"]
    color = discord.Color.green() if recommendations else discord.Color.orange()
    embeds: list[discord.Embed] = [discord.Embed(title="Spread Recommendations", color=color)]

    if not spreads:
        embeds[0].description = "No spread rows extracted from this batch."
        return embeds

    embeds[0].description = "Best spread hedge opportunities from this extraction batch."
    picks_by_metric, suppressed_by_metric = _select_unique_market_picks_by_metric(recommendations)

    def lines(metric: str) -> list[str]:
        picks = picks_by_metric.get(metric, [])
        if not picks:
            if suppressed_by_metric.get(metric, 0) > 0:
                return ["game already mentioned"]
            return ["No picks available"]
        blocks = [_format_spread_pick_block(pick, odds_mode=odds_mode) for pick in picks]
        return _split_blocks_to_field_chunks(blocks, limit=1024)

    _append_metric_chunks(embeds, "Top 2 ROI", lines("roi"), color=color)
    _append_metric_chunks(embeds, "Top 2 Profit", lines("profit"), color=color)
    _append_metric_chunks(embeds, "Top 2 Rake (Lowest)", lines("rake"), color=color)
    why_no_picks = _build_why_no_picks_note(analysis, market_label="spread")
    if why_no_picks:
        _append_embed_field(embeds, name="Why No Picks?", value=why_no_picks, color=color)

    if len(recommendations) < 6:
        _append_embed_field(
            embeds,
            name="Note",
            value="Fewer than 2 games were available for one or more metrics.",
            color=color,
        )
    return embeds


def _select_unique_market_picks_by_metric(
    recommendations: list[OddsRecommendation],
) -> tuple[dict[str, list[OddsRecommendation]], dict[str, int]]:
    picked_keys: set[str] = set()
    out: dict[str, list[OddsRecommendation]] = {}
    suppressed: dict[str, int] = {}

    for metric in ("roi", "profit", "rake"):
        metric_items = [item for item in recommendations if item.metric == metric]
        selected: list[OddsRecommendation] = []
        suppressed_count = 0
        for item in metric_items:
            key = _market_game_key(item)
            if key in picked_keys:
                suppressed_count += 1
                continue
            selected.append(item)
            picked_keys.add(key)
            if len(selected) == 2:
                break
        out[metric] = selected
        suppressed[metric] = suppressed_count

    return out, suppressed


def _market_game_key(item: OddsRecommendation) -> str:
    teams = sorted([item.bet_team, item.hedge_team])
    return f"{item.date}|{teams[0]}|{teams[1]}"


def build_over_under_recommendations(candidates: list[OddsCandidate], *, b_stake: float = 100.0) -> list[OddsRecommendation]:
    analysis = _analyze_over_under_candidates(candidates, b_stake=b_stake)
    return analysis["ranked"]


def build_spread_recommendations(candidates: list[OddsCandidate], *, b_stake: float = 100.0) -> list[OddsRecommendation]:
    analysis = _analyze_spread_candidates(candidates, b_stake=b_stake)
    return analysis["ranked"]


def _analyze_spread_candidates(candidates: list[OddsCandidate], *, b_stake: float = 100.0) -> dict[str, object]:
    grouped: dict[str, dict[str, list[OddsCandidate]]] = {}
    spreads: list[OddsCandidate] = []
    skipped_missing = 0
    skipped_bad_odds = 0

    for candidate in candidates:
        if candidate.market != "spread":
            continue
        spreads.append(candidate)
        if not all([candidate.date, candidate.team, candidate.against, candidate.spread_line]):
            skipped_missing += 1
            continue
        odds_value = _to_float(candidate.odds)
        spread_value = _to_float(candidate.spread_line)
        if odds_value is None or odds_value <= 1 or spread_value is None:
            skipped_bad_odds += 1
            continue

        matchup_left, matchup_right = sorted([candidate.team, candidate.against])
        key = f"{candidate.date}|{matchup_left}|{matchup_right}"
        side_key = f"{candidate.team}|{candidate.against}"
        grouped.setdefault(key, {}).setdefault(side_key, []).append(candidate)

    pool: list[OddsRecommendation] = []
    groups_with_both_sides = 0
    same_site_pairs_rejected = 0
    cross_site_pairs_checked = 0
    site_min_rejected = 0
    eligible_in_pool = 0
    for sides in grouped.values():
        for left_key, left_candidates in list(sides.items()):
            left_team, left_against = left_key.split("|", 1)
            right_key = f"{left_against}|{left_team}"
            if right_key not in sides or left_key > right_key:
                continue
            groups_with_both_sides += 1

            best: tuple[tuple[float, float, float, float], OddsRecommendation] | None = None
            for left in left_candidates:
                left_odds = _to_float(left.odds)
                left_spread = _to_float(left.spread_line)
                if left_odds is None or left_spread is None:
                    continue

                for right in sides[right_key]:
                    right_odds = _to_float(right.odds)
                    right_spread = _to_float(right.spread_line)
                    if right_odds is None or right_spread is None:
                        continue

                    if (left.site or "").strip().lower() == (right.site or "").strip().lower():
                        same_site_pairs_rejected += 1
                        continue
                    cross_site_pairs_checked += 1

                    left_h = _optimize_spread_hedge_stake(
                        b_stake=b_stake,
                        odds_bet=left_odds,
                        odds_hedge=right_odds,
                        bet_spread=left_spread,
                        hedge_spread=right_spread,
                    )
                    left_outcomes = _spread_profit_outcomes(
                        b_stake=b_stake,
                        h_hedge=left_h,
                        odds_bet=left_odds,
                        odds_hedge=right_odds,
                        bet_spread=left_spread,
                        hedge_spread=right_spread,
                    )
                    left_floor = min(item.profit for item in left_outcomes)

                    right_h = _optimize_spread_hedge_stake(
                        b_stake=b_stake,
                        odds_bet=right_odds,
                        odds_hedge=left_odds,
                        bet_spread=right_spread,
                        hedge_spread=left_spread,
                    )
                    right_outcomes = _spread_profit_outcomes(
                        b_stake=b_stake,
                        h_hedge=right_h,
                        odds_bet=right_odds,
                        odds_hedge=left_odds,
                        bet_spread=right_spread,
                        hedge_spread=left_spread,
                    )
                    right_floor = min(item.profit for item in right_outcomes)

                    if left_floor >= right_floor:
                        bet_candidate = left
                        hedge_candidate = right
                        odds_bet = left_odds
                        odds_hedge = right_odds
                        bet_spread = left_spread
                        hedge_spread = right_spread
                        h_hedge = left_h
                        outcomes = left_outcomes
                    else:
                        bet_candidate = right
                        hedge_candidate = left
                        odds_bet = right_odds
                        odds_hedge = left_odds
                        bet_spread = right_spread
                        hedge_spread = left_spread
                        h_hedge = right_h
                        outcomes = right_outcomes

                    total_bet = b_stake + h_hedge
                    net = min(item.profit for item in outcomes)
                    total_return = total_bet + net
                    roi = (net / total_bet) if total_bet else 0.0
                    rake = (1 / odds_bet) + (1 / odds_hedge) - 1
                    recommendation = (
                        "BET"
                        if _meets_site_min_odds(odds_bet, bet_candidate.site)
                        and _meets_site_min_odds(odds_hedge, hedge_candidate.site)
                        else "NO BET"
                    )
                    if recommendation == "BET":
                        eligible_in_pool += 1
                    else:
                        site_min_rejected += 1

                    rec = OddsRecommendation(
                        metric="",
                        rank=0,
                        date=bet_candidate.date,
                        bet_team=f"{bet_candidate.team}/{bet_candidate.against} {bet_candidate.spread_line}",
                        hedge_team=f"{hedge_candidate.team}/{hedge_candidate.against} {hedge_candidate.spread_line}",
                        bet_site=bet_candidate.site,
                        hedge_site=hedge_candidate.site,
                        odds_bet=round(odds_bet, 4),
                        odds_hedge=round(odds_hedge, 4),
                        b_stake=round(b_stake, 2),
                        h_hedge=round(h_hedge, 2),
                        total_bet=round(total_bet, 2),
                        total_return=round(total_return, 2),
                        net=round(net, 2),
                        roi=round(roi, 6),
                        rake=round(rake, 6),
                        recommendation=recommendation,
                    )
                    best_profit = max(item.profit for item in outcomes)
                    score = (rec.net, rec.roi, best_profit, rec.odds_bet, rec.odds_hedge)
                    if best is None or score > best[0]:
                        best = (score, rec)

            if best:
                pool.append(best[1])

    ranked = select_top_recommendations(pool)
    return {
        "spreads": spreads,
        "pool": pool,
        "ranked": ranked,
        "input_rows": len(candidates),
        "market_rows": len(spreads),
        "skipped_missing": skipped_missing,
        "skipped_bad_odds": skipped_bad_odds,
        "group_keys": len(grouped),
        "groups_with_both_sides": groups_with_both_sides,
        "same_site_pairs_rejected": same_site_pairs_rejected,
        "cross_site_pairs_checked": cross_site_pairs_checked,
        "site_min_rejected": site_min_rejected,
        "eligible_in_pool": eligible_in_pool,
    }


def _analyze_over_under_candidates(candidates: list[OddsCandidate], *, b_stake: float = 100.0) -> dict[str, object]:
    grouped: dict[str, dict[str, list[OddsCandidate]]] = {}
    totals: list[OddsCandidate] = []
    skipped_missing = 0
    skipped_bad_odds = 0

    for candidate in candidates:
        if candidate.market not in ("total_over", "total_under"):
            continue
        totals.append(candidate)
        if not all([candidate.date, candidate.team, candidate.against, candidate.total_line]):
            skipped_missing += 1
            continue
        odds_value = _to_float(candidate.odds)
        if odds_value is None or odds_value <= 1:
            skipped_bad_odds += 1
            continue

        matchup_left, matchup_right = sorted([candidate.team, candidate.against])
        key = f"{candidate.date}|{matchup_left}|{matchup_right}"
        side_map = grouped.setdefault(key, {"total_over": [], "total_under": []})
        side_map[candidate.market].append(candidate)

    pool: list[OddsRecommendation] = []
    groups_with_both_sides = 0
    cross_site_pairs_checked = 0
    same_site_pairs_rejected = 0
    site_min_rejected = 0
    eligible_in_pool = 0

    for key, side_map in grouped.items():
        over_candidates = side_map["total_over"]
        under_candidates = side_map["total_under"]
        if not over_candidates or not under_candidates:
            continue
        groups_with_both_sides += 1

        best: tuple[tuple[float, float, float, float], OddsRecommendation] | None = None
        for over in over_candidates:
            over_odds = _to_float(over.odds)
            if over_odds is None:
                continue

            for under in under_candidates:
                under_odds = _to_float(under.odds)
                if under_odds is None:
                    continue

                if (over.site or "").strip().lower() == (under.site or "").strip().lower():
                    same_site_pairs_rejected += 1
                    continue
                cross_site_pairs_checked += 1

                if over_odds >= under_odds:
                    bet_side = "OVER"
                    hedge_side = "UNDER"
                    bet_candidate = over
                    hedge_candidate = under
                    odds_bet = over_odds
                    odds_hedge = under_odds
                else:
                    bet_side = "UNDER"
                    hedge_side = "OVER"
                    bet_candidate = under
                    hedge_candidate = over
                    odds_bet = under_odds
                    odds_hedge = over_odds

                h_hedge = _optimize_ou_hedge_stake(
                    b_stake=b_stake,
                    odds_bet=odds_bet,
                    odds_hedge=odds_hedge,
                    bet_side=bet_side,
                    bet_line=_to_float(bet_candidate.total_line) or 0.0,
                    hedge_side=hedge_side,
                    hedge_line=_to_float(hedge_candidate.total_line) or 0.0,
                )
                total_bet = b_stake + h_hedge
                outcomes = _ou_profit_outcomes(
                    b_stake=b_stake,
                    h_hedge=h_hedge,
                    odds_bet=odds_bet,
                    odds_hedge=odds_hedge,
                    bet_side=bet_side,
                    bet_line=_to_float(bet_candidate.total_line) or 0.0,
                    hedge_side=hedge_side,
                    hedge_line=_to_float(hedge_candidate.total_line) or 0.0,
                )
                net = min(outcome.profit for outcome in outcomes)
                total_return = total_bet + net
                roi = (net / total_bet) if total_bet else 0.0
                rake = (1 / odds_bet) + (1 / odds_hedge) - 1
                recommendation = (
                    "BET"
                    if _meets_site_min_odds(odds_bet, bet_candidate.site)
                    and _meets_site_min_odds(odds_hedge, hedge_candidate.site)
                    else "NO BET"
                )
                if recommendation == "BET":
                    eligible_in_pool += 1
                else:
                    site_min_rejected += 1

                bet_label = (
                    f"{bet_candidate.team}/{bet_candidate.against} "
                    f"{bet_side} {bet_candidate.total_line or '(missing line)'}"
                )
                hedge_label = (
                    f"{hedge_candidate.team}/{hedge_candidate.against} "
                    f"{hedge_side} {hedge_candidate.total_line or '(missing line)'}"
                )
                rec = OddsRecommendation(
                    metric="",
                    rank=0,
                    date=bet_candidate.date,
                    bet_team=bet_label,
                    hedge_team=hedge_label,
                    bet_site=bet_candidate.site,
                    hedge_site=hedge_candidate.site,
                    odds_bet=round(odds_bet, 4),
                    odds_hedge=round(odds_hedge, 4),
                    b_stake=round(b_stake, 2),
                    h_hedge=round(h_hedge, 2),
                    total_bet=round(total_bet, 2),
                    total_return=round(total_return, 2),
                    net=round(net, 2),
                    roi=round(roi, 6),
                    rake=round(rake, 6),
                    recommendation=recommendation,
                )
                best_profit = max(outcome.profit for outcome in outcomes)
                score = (rec.net, rec.roi, best_profit, rec.odds_bet, rec.odds_hedge)
                if best is None or score > best[0]:
                    best = (score, rec)

        if best:
            pool.append(best[1])

    ranked = select_top_recommendations(pool)
    return {
        "input_rows": len(candidates),
        "market_rows": len(totals),
        "totals": totals,
        "pool": pool,
        "ranked": ranked,
        "skipped_missing": skipped_missing,
        "skipped_bad_odds": skipped_bad_odds,
        "group_keys": len(grouped),
        "groups_with_both_sides": groups_with_both_sides,
        "same_site_pairs_rejected": same_site_pairs_rejected,
        "cross_site_pairs_checked": cross_site_pairs_checked,
        "site_min_rejected": site_min_rejected,
        "eligible_in_pool": eligible_in_pool,
    }


def _build_why_no_picks_note(analysis: dict[str, object], *, market_label: str) -> str:
    ranked = analysis["ranked"]
    if ranked:
        return ""

    market_rows = int(analysis.get("market_rows", 0))
    if market_rows == 0:
        return f"No {market_label} rows were extracted from these screenshots."

    reasons: list[str] = []
    skipped_missing = int(analysis.get("skipped_missing", 0))
    skipped_bad_odds = int(analysis.get("skipped_bad_odds", 0))
    groups_with_both_sides = int(analysis.get("groups_with_both_sides", 0))
    cross_site_pairs_checked = int(analysis.get("cross_site_pairs_checked", 0))
    same_site_pairs_rejected = int(analysis.get("same_site_pairs_rejected", 0))
    eligible_in_pool = int(analysis.get("eligible_in_pool", 0))
    site_min_rejected = int(analysis.get("site_min_rejected", 0))

    if skipped_missing:
        reasons.append(f"{skipped_missing} row(s) were missing required fields.")
    if skipped_bad_odds:
        reasons.append(f"{skipped_bad_odds} row(s) had invalid odds or line values.")
    if groups_with_both_sides == 0:
        reasons.append("No games had both opposite sides extracted.")
    elif cross_site_pairs_checked == 0 and same_site_pairs_rejected > 0:
        reasons.append("Only same-site opposite-side pairs were found.")
    elif cross_site_pairs_checked == 0:
        reasons.append("No cross-site opposite-side pairs could be formed.")
    if site_min_rejected > 0 and eligible_in_pool == 0:
        reasons.append("All candidate pairs failed the site minimum odds rule.")

    if not reasons:
        reasons.append("No valid recommendation pairs remained after filtering.")

    return " ".join(reasons)


def _join_blocks_with_limit(blocks: list[str], *, limit: int) -> str:
    if not blocks:
        return "No picks available"

    out: list[str] = []
    used = 0
    for idx, raw_block in enumerate(blocks):
        block = raw_block.strip()
        if not block:
            continue
        separator = "\n\n" if out else ""
        candidate = f"{separator}{block}"
        if used + len(candidate) <= limit:
            out.append(block)
            used += len(candidate)
            continue

        remaining = limit - used - len(separator)
        if remaining <= 0:
            break
        if remaining <= 3:
            out.append("." * remaining)
            used = limit
            break
        trimmed = f"{block[:remaining - 3].rstrip()}..."
        out.append(trimmed)
        used = limit
        break

    if not out:
        first = blocks[0].strip()
        if len(first) <= limit:
            return first
        return f"{first[: max(0, limit - 3)].rstrip()}..."
    return "\n\n".join(out)


def _split_blocks_to_field_chunks(blocks: list[str], *, limit: int) -> list[str]:
    if not blocks:
        return ["No picks available"]

    chunks: list[str] = []
    current = ""
    for raw_block in blocks:
        block = raw_block.strip()
        if not block:
            continue

        if len(block) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_text_by_limit(block, limit=limit))
            continue

        if not current:
            current = block
            continue

        candidate = f"{current}\n\n{block}"
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = block

    if current:
        chunks.append(current)
    return chunks or ["No picks available"]


def _split_text_by_limit(text: str, *, limit: int) -> list[str]:
    normalized = text.strip()
    if len(normalized) <= limit:
        return [normalized]

    parts = normalized.split("\n")
    out: list[str] = []
    current = ""
    for part in parts:
        part_text = part.strip()
        if not part_text:
            continue

        if len(part_text) > limit:
            if current:
                out.append(current)
                current = ""
            start = 0
            while start < len(part_text):
                segment = part_text[start : start + limit]
                out.append(segment)
                start += limit
            continue

        candidate = part_text if not current else f"{current}\n{part_text}"
        if len(candidate) <= limit:
            current = candidate
        else:
            out.append(current)
            current = part_text

    if current:
        out.append(current)
    return out or [normalized[:limit]]


def _append_metric_chunks(
    embeds: list[discord.Embed],
    label: str,
    chunks: list[str],
    *,
    color: discord.Colour,
) -> None:
    for idx, value in enumerate(chunks, start=1):
        suffix = "" if idx == 1 else f" (cont. {idx})"
        _append_embed_field(embeds, name=f"{label}{suffix}", value=value, color=color)


def _append_embed_field(
    embeds: list[discord.Embed],
    *,
    name: str,
    value: str,
    color: discord.Colour,
) -> None:
    if not embeds:
        embeds.append(discord.Embed(title="Over/Under Recommendations", color=color))

    target = embeds[-1]
    if len(target.fields) >= 25 or (_embed_char_count(target) + len(name) + len(value)) > 5800:
        next_idx = len(embeds) + 1
        target = discord.Embed(title=f"Over/Under Recommendations (cont. {next_idx})", color=color)
        embeds.append(target)

    target.add_field(name=name, value=value, inline=False)


def _embed_char_count(embed: discord.Embed) -> int:
    total = len(embed.title or "") + len(embed.description or "")
    for field in embed.fields:
        total += len(field.name or "") + len(field.value or "")
    if embed.footer and embed.footer.text:
        total += len(embed.footer.text)
    return total


def _candidate_line_suffix(candidate: OddsCandidate) -> str:
    if candidate.market == "spread" and candidate.spread_line:
        return f" {candidate.spread_line}"
    if candidate.total_line:
        return f" {candidate.total_line}"
    return ""


def _format_ou_pick_block(pick: OddsRecommendation, *, odds_mode: str = "both") -> str:
    block = _format_pick_block(pick, odds_mode=odds_mode)
    parsed = _parse_ou_label(pick.bet_team), _parse_ou_label(pick.hedge_team)
    if not parsed[0] or not parsed[1]:
        return block

    bet_meta = parsed[0]
    hedge_meta = parsed[1]
    outcomes = _ou_profit_outcomes(
        b_stake=pick.b_stake,
        h_hedge=pick.h_hedge,
        odds_bet=pick.odds_bet,
        odds_hedge=pick.odds_hedge,
        bet_side=bet_meta.side,
        bet_line=bet_meta.line,
        hedge_side=hedge_meta.side,
        hedge_line=hedge_meta.line,
    )
    worst = min(outcomes, key=lambda item: item.profit)
    best = max(outcomes, key=lambda item: item.profit)
    middle_outcome = next((item for item in outcomes if "middle" in item.label.lower()), None)
    middle_text = (
        f"Middle: `{middle_outcome.label}` -> `{middle_outcome.profit:.2f}`"
        if middle_outcome
        else "Middle: `none`"
    )
    return (
        f"{block}\n"
        f"Worst Case: `{worst.label}` -> `{worst.profit:.2f}`\n"
        f"Best Case: `{best.label}` -> `{best.profit:.2f}`\n"
        f"{middle_text}"
    )


def _format_spread_pick_block(pick: OddsRecommendation, *, odds_mode: str = "both") -> str:
    block = _format_pick_block(pick, odds_mode=odds_mode)
    bet_spread = _parse_trailing_signed_number(pick.bet_team)
    hedge_spread = _parse_trailing_signed_number(pick.hedge_team)
    if bet_spread is None or hedge_spread is None:
        return block

    outcomes = _spread_profit_outcomes(
        b_stake=pick.b_stake,
        h_hedge=pick.h_hedge,
        odds_bet=pick.odds_bet,
        odds_hedge=pick.odds_hedge,
        bet_spread=bet_spread,
        hedge_spread=hedge_spread,
    )
    worst = min(outcomes, key=lambda item: item.profit)
    best = max(outcomes, key=lambda item: item.profit)
    middle_outcome = next((item for item in outcomes if "window" in item.label.lower()), None)
    middle_text = (
        f"Middle: `{middle_outcome.label}` -> `{middle_outcome.profit:.2f}`"
        if middle_outcome
        else "Middle: `none`"
    )
    return (
        f"{block}\n"
        f"Worst Case: `{worst.label}` -> `{worst.profit:.2f}`\n"
        f"Best Case: `{best.label}` -> `{best.profit:.2f}`\n"
        f"{middle_text}"
    )


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


def _to_float(value: object) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _meets_site_min_odds(odds_value: float, site: str) -> bool:
    site_key = (site or "").strip().lower()
    min_required = 1.0 if site_key == "cloudbet" else 1.5
    return odds_value >= min_required


@dataclass(frozen=True)
class _OUSideMeta:
    side: str
    line: float


@dataclass(frozen=True)
class _OUOutcome:
    label: str
    profit: float


def _parse_ou_label(label: str) -> _OUSideMeta | None:
    text = (label or "").strip()
    parts = text.split()
    if len(parts) < 2:
        return None
    side = parts[-2].upper()
    if side not in ("OVER", "UNDER"):
        return None
    line = _to_float(parts[-1])
    if line is None:
        return None
    return _OUSideMeta(side=side, line=line)


def _parse_trailing_signed_number(label: str) -> float | None:
    parts = (label or "").strip().split()
    if not parts:
        return None
    return _to_float(parts[-1])


def _optimize_ou_hedge_stake(
    *,
    b_stake: float,
    odds_bet: float,
    odds_hedge: float,
    bet_side: str,
    bet_line: float,
    hedge_side: str,
    hedge_line: float,
) -> float:
    # One-variable maximin: maximize minimum scenario profit over hedge stake h >= 0.
    # Profit per scenario is linear in h, so optimum is at h=0 or at an intersection.
    scenarios = _ou_scenarios_for_lines(bet_side, bet_line, hedge_side, hedge_line)
    if not scenarios:
        return 0.0

    def profit_at(total_points: float, h_hedge: float) -> float:
        bet_mult = _result_multiplier(bet_side, bet_line, total_points, odds_bet)
        hedge_mult = _result_multiplier(hedge_side, hedge_line, total_points, odds_hedge)
        payout = (b_stake * bet_mult) + (h_hedge * hedge_mult)
        return payout - (b_stake + h_hedge)

    candidate_h_values: set[float] = {0.0}
    linear_models: list[tuple[float, float]] = []  # slope, intercept
    for scenario in scenarios:
        # profit(h) = intercept + slope * h
        bet_mult = _result_multiplier(bet_side, bet_line, scenario, odds_bet)
        hedge_mult = _result_multiplier(hedge_side, hedge_line, scenario, odds_hedge)
        intercept = (b_stake * bet_mult) - b_stake
        slope = hedge_mult - 1.0
        linear_models.append((slope, intercept))

    for i in range(len(linear_models)):
        s1, c1 = linear_models[i]
        for j in range(i + 1, len(linear_models)):
            s2, c2 = linear_models[j]
            if abs(s1 - s2) < 1e-9:
                continue
            h = (c2 - c1) / (s1 - s2)
            if h >= 0:
                candidate_h_values.add(h)

    # Guardrail bound for practical display and to avoid runaway edge-cases.
    candidate_h_values = {max(0.0, min(h, 10000.0)) for h in candidate_h_values}

    best_h = 0.0
    best_floor = float("-inf")
    for h in candidate_h_values:
        floor = min(profit_at(total_points, h) for total_points in scenarios)
        if floor > best_floor:
            best_floor = floor
            best_h = h
    return round(best_h, 2)


def _ou_profit_outcomes(
    *,
    b_stake: float,
    h_hedge: float,
    odds_bet: float,
    odds_hedge: float,
    bet_side: str,
    bet_line: float,
    hedge_side: str,
    hedge_line: float,
) -> list[_OUOutcome]:
    points = _ou_scenarios_for_lines(bet_side, bet_line, hedge_side, hedge_line)
    out: list[_OUOutcome] = []
    for total_points in points:
        label = _label_total_bucket(total_points, bet_line, hedge_line)
        bet_mult = _result_multiplier(bet_side, bet_line, total_points, odds_bet)
        hedge_mult = _result_multiplier(hedge_side, hedge_line, total_points, odds_hedge)
        payout = (b_stake * bet_mult) + (h_hedge * hedge_mult)
        profit = payout - (b_stake + h_hedge)
        out.append(_OUOutcome(label=label, profit=round(profit, 2)))
    return out


def _ou_scenarios_for_lines(bet_side: str, bet_line: float, hedge_side: str, hedge_line: float) -> list[float]:
    del bet_side, hedge_side  # side is not needed for breakpoint generation
    low = min(bet_line, hedge_line)
    high = max(bet_line, hedge_line)
    points = [low - 1.0, low, (low + high) / 2.0, high, high + 1.0]
    unique = sorted({round(point, 4) for point in points})
    return unique


def _result_multiplier(side: str, line: float, total_points: float, odds: float) -> float:
    side_upper = side.upper()
    if side_upper == "OVER":
        if total_points > line:
            return odds
        if total_points < line:
            return 0.0
        return 1.0
    if side_upper == "UNDER":
        if total_points < line:
            return odds
        if total_points > line:
            return 0.0
        return 1.0
    return 0.0


def _label_total_bucket(total_points: float, line_a: float, line_b: float) -> str:
    low = min(line_a, line_b)
    high = max(line_a, line_b)
    if total_points < low:
        return f"Below {low:g}"
    if total_points > high:
        return f"Above {high:g}"
    if abs(total_points - low) < 1e-9 and abs(total_points - high) < 1e-9:
        return f"At {low:g}"
    if abs(total_points - low) < 1e-9:
        return f"At lower line {low:g}"
    if abs(total_points - high) < 1e-9:
        return f"At upper line {high:g}"
    return f"Middle window ({low:g}, {high:g})"


def _optimize_spread_hedge_stake(
    *,
    b_stake: float,
    odds_bet: float,
    odds_hedge: float,
    bet_spread: float,
    hedge_spread: float,
) -> float:
    scenarios = _spread_scenarios_for_lines(bet_spread, hedge_spread)
    if not scenarios:
        return 0.0

    def profit_at(margin: float, h_hedge: float) -> float:
        bet_mult = _spread_result_multiplier(margin, bet_spread, odds_bet)
        hedge_mult = _spread_result_multiplier(-margin, hedge_spread, odds_hedge)
        payout = (b_stake * bet_mult) + (h_hedge * hedge_mult)
        return payout - (b_stake + h_hedge)

    candidate_h_values: set[float] = {0.0}
    linear_models: list[tuple[float, float]] = []
    for margin in scenarios:
        bet_mult = _spread_result_multiplier(margin, bet_spread, odds_bet)
        hedge_mult = _spread_result_multiplier(-margin, hedge_spread, odds_hedge)
        intercept = (b_stake * bet_mult) - b_stake
        slope = hedge_mult - 1.0
        linear_models.append((slope, intercept))

    for i in range(len(linear_models)):
        s1, c1 = linear_models[i]
        for j in range(i + 1, len(linear_models)):
            s2, c2 = linear_models[j]
            if abs(s1 - s2) < 1e-9:
                continue
            h = (c2 - c1) / (s1 - s2)
            if h >= 0:
                candidate_h_values.add(h)

    candidate_h_values = {max(0.0, min(h, 10000.0)) for h in candidate_h_values}

    best_h = 0.0
    best_floor = float("-inf")
    for h in candidate_h_values:
        floor = min(profit_at(margin, h) for margin in scenarios)
        if floor > best_floor:
            best_floor = floor
            best_h = h
    return round(best_h, 2)


def _spread_profit_outcomes(
    *,
    b_stake: float,
    h_hedge: float,
    odds_bet: float,
    odds_hedge: float,
    bet_spread: float,
    hedge_spread: float,
) -> list[_OUOutcome]:
    margins = _spread_scenarios_for_lines(bet_spread, hedge_spread)
    out: list[_OUOutcome] = []
    for margin in margins:
        label = _label_spread_bucket(margin, bet_spread, hedge_spread)
        bet_mult = _spread_result_multiplier(margin, bet_spread, odds_bet)
        hedge_mult = _spread_result_multiplier(-margin, hedge_spread, odds_hedge)
        payout = (b_stake * bet_mult) + (h_hedge * hedge_mult)
        profit = payout - (b_stake + h_hedge)
        out.append(_OUOutcome(label=label, profit=round(profit, 2)))
    return out


def _spread_scenarios_for_lines(bet_spread: float, hedge_spread: float) -> list[float]:
    left_threshold = -bet_spread
    right_threshold = hedge_spread
    low = min(left_threshold, right_threshold)
    high = max(left_threshold, right_threshold)
    values = [low - 1.0, low, (low + high) / 2.0, high, high + 1.0]
    return sorted({round(value, 4) for value in values})


def _spread_result_multiplier(margin: float, spread_line: float, odds: float) -> float:
    adjusted = margin + spread_line
    if adjusted > 0:
        return odds
    if adjusted < 0:
        return 0.0
    return 1.0


def _label_spread_bucket(margin: float, bet_spread: float, hedge_spread: float) -> str:
    left_threshold = -bet_spread
    right_threshold = hedge_spread
    low = min(left_threshold, right_threshold)
    high = max(left_threshold, right_threshold)
    if margin < low:
        return f"Below {low:g}"
    if margin > high:
        return f"Above {high:g}"
    if abs(margin - low) < 1e-9 and abs(margin - high) < 1e-9:
        return f"At {low:g}"
    if abs(margin - low) < 1e-9:
        return f"At lower line {low:g}"
    if abs(margin - high) < 1e-9:
        return f"At upper line {high:g}"
    return f"Middle window ({low:g}, {high:g})"


class OddsResultPaginationView(discord.ui.View):
    def __init__(
        self,
        *,
        invoker_user_id: int,
        recommendations: list[OddsRecommendation],
        candidates: list[OddsCandidate],
        insufficient_data: bool,
        odds_mode: str = "both",
    ) -> None:
        super().__init__(timeout=900)
        self.invoker_user_id = invoker_user_id
        self.recommendations = recommendations
        self.candidates = candidates
        self.insufficient_data = insufficient_data
        self.odds_mode = odds_mode
        self.page = 0
        self._sync_buttons()

    async def _authorize(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_user_id:
            await interaction.response.send_message(
                "Only the user who triggered this odds parse can use these buttons.",
                ephemeral=True,
            )
            return False
        return True

    def _current_embeds(self) -> list[discord.Embed]:
        if self.page == 0:
            return [
                build_odds_result_embed(
                    self.recommendations,
                    insufficient_data=self.insufficient_data,
                    odds_mode=self.odds_mode,
                )
            ]
        if self.page == 1:
            return build_over_under_embeds(self.candidates, odds_mode=self.odds_mode)
        return build_spread_embeds(self.candidates, odds_mode=self.odds_mode)

    def _sync_buttons(self) -> None:
        for child in self.children:
            if not isinstance(child, discord.ui.Button):
                continue
            if child.custom_id == "odds:result:next":
                child.disabled = self.page == 2
                child.label = "Next: Over/Under" if self.page == 0 else "Next: Spread"
            elif child.custom_id == "odds:result:back":
                child.disabled = self.page == 0
                child.label = "Back: Recommendations" if self.page == 1 else "Back: Over/Under"

    @discord.ui.button(label="Next: Over/Under", style=discord.ButtonStyle.secondary, custom_id="odds:result:next")
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._authorize(interaction):
            return

        if self.page < 2:
            self.page += 1
        self._sync_buttons()
        await interaction.response.edit_message(embeds=self._current_embeds(), view=self)

    @discord.ui.button(
        label="Back: Recommendations",
        style=discord.ButtonStyle.secondary,
        custom_id="odds:result:back",
        disabled=True,
    )
    async def previous_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self._authorize(interaction):
            return

        if self.page > 0:
            self.page -= 1
        self._sync_buttons()
        await interaction.response.edit_message(embeds=self._current_embeds(), view=self)


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
        result_view = OddsResultPaginationView(
            invoker_user_id=interaction.user.id,
            recommendations=result.recommendations,
            candidates=pending.candidates,
            insufficient_data=len(result.recommendations) < 6,
            odds_mode=pending.odds_mode,
        )

        for child in self.children:
            child.disabled = True

        await interaction.edit_original_response(embed=review_embed, view=self)
        await interaction.followup.send(
            embed=result_embed,
            view=result_view,
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


