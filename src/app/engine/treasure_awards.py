"""Shared treasure-award planning for defeated encounter groups."""

from __future__ import annotations

import re
from typing import Callable

from ..schemas import EnemyState
from .monster_combat_hooks import treasure_roll_count_from_defeated


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
