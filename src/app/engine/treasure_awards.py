"""Shared treasure-award planning for defeated encounter groups."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

from ..schemas import EnemyState, PartyMemberState, TileState
from .dungeon_table_roller import TreasureOutcome
from .inventory import distribute_gold_among, distribute_items_among
from .monster_combat_hooks import treasure_roll_count_from_defeated


@dataclass(frozen=True)
class TreasureDistribution:
    """Carry-capacity outcome for a claimable cache of gold and items."""

    remaining_gold: int
    payouts: list[str]
    uncarried_items: list[str]
    placed_items: list[str]
    assigned_items: dict[str, list[str]]


def distribute_claimed_treasure(
    survivors: list[PartyMemberState],
    *,
    gold_total: int,
    items: list[str],
    servant_owner_ids: set[str] | None = None,
) -> TreasureDistribution:
    """Distribute treasure to living heroes and report any capacity-limited remainder."""
    remaining_gold, payouts = distribute_gold_among(
        survivors,
        gold_total,
        servant_owner_ids=servant_owner_ids,
    )
    inventory_lengths = {member.character_id: len(member.inventory) for member in survivors}
    uncarried_items, placed_items = distribute_items_among(survivors, list(items))
    assigned_items = {
        member.character_id: list(member.inventory[inventory_lengths[member.character_id] :])
        for member in survivors
    }
    return TreasureDistribution(
        remaining_gold=remaining_gold,
        payouts=payouts,
        uncarried_items=uncarried_items,
        placed_items=placed_items,
        assigned_items=assigned_items,
    )


def abyss_group_treasure_roll_count(defeated: list[EnemyState]) -> int:
    """Return explicit Abyss treasure rolls once per named encounter group."""
    rolls_by_group: dict[str, int] = {}
    for enemy in defeated:
        if "no_treasure" in {tag.lower() for tag in enemy.tags}:
            continue
        group_rolls = 0
        for tag in enemy.tags:
            if not tag.startswith("abyss_treasure_rolls:"):
                continue
            try:
                group_rolls = max(group_rolls, int(tag.split(":", 1)[1]))
            except ValueError:
                continue
        if group_rolls:
            rolls_by_group.setdefault(enemy.name, max(0, group_rolls))
    return sum(rolls_by_group.values())


def treasure_roll_count_for_defeated(
    defeated: list[EnemyState],
    *,
    lookup_template: Callable[[EnemyState], dict | None],
    log: list[str],
    fd_ruleset: bool,
) -> int:
    """Resolve one rule-table roll count for a defeated encounter's treasure."""
    abyss_rolls = abyss_group_treasure_roll_count(defeated)
    if abyss_rolls:
        return abyss_rolls
    return treasure_roll_count_from_defeated(
        defeated,
        lookup_template=lookup_template,
        log=log,
        fd_ruleset=fd_ruleset,
    )


def final_boss_summary_gold_cap(*, is_final_boss: bool, summary: str | None) -> int | None:
    """Read the displayed Final Boss gp total for legacy-save corruption guards."""
    if not is_final_boss or not summary:
        return None
    amounts = [int(match) for match in re.findall(r"(\d+)\s*gp", summary, flags=re.IGNORECASE)]
    return max(amounts) if amounts else None


def merge_treasure_outcomes(outcomes: list[TreasureOutcome]) -> TreasureOutcome:
    """Combine independent treasure rolls into one claimable outcome."""
    if not outcomes:
        return TreasureOutcome("", 0, [], [])
    gold = sum(outcome.gold for outcome in outcomes)
    items = [item for outcome in outcomes for item in outcome.items]
    log = [entry for outcome in outcomes for entry in outcome.log]
    summaries = [outcome.summary for outcome in outcomes if outcome.summary]
    return TreasureOutcome("; ".join(summaries) if summaries else "Treasure", gold, items, log)


def apply_secret_door_treasure_doubling(tile: TileState) -> bool:
    """Apply a secret-door treasure double once, including legacy-save detection."""
    if not tile.treasure_doubled or not tile.treasure_gold:
        return False
    summary = tile.treasure_summary or ""
    if tile.treasure_doubling_applied or "doubled behind secret door:" in summary.lower():
        tile.treasure_doubling_applied = True
        return False
    tile.treasure_gold *= 2
    tile.treasure_doubling_applied = True
    if summary:
        tile.treasure_summary = f"{summary} (doubled behind secret door: {tile.treasure_gold}gp)."
    return True
