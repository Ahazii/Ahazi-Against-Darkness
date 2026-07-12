"""Reusable search-roll resolution before the engine applies the selected result."""

from __future__ import annotations

from dataclasses import dataclass

from ..schemas import SessionState, TileState
from .dice import roll_d6
from .dungeon_table_roller import DungeonTableRoller, SearchOutcome
from .expert_skill_effects import adjust_search_roll


@dataclass(frozen=True)
class SearchRollResolution:
    """The adjusted search-table result and player-visible roll explanation."""

    effective_roll: int
    outcome: SearchOutcome
    log: list[str]


def resolve_search_roll(
    session: SessionState,
    tile: TileState,
    table_roller: DungeonTableRoller,
    *,
    show_rolls: bool,
    explain_math: bool,
) -> SearchRollResolution:
    """Roll and adjust a standard search without applying its reward or encounter effect."""
    roll = roll_d6()
    effective_roll = roll - 1 if tile.tile_type == "corridor" else roll
    log: list[str] = []
    if show_rolls:
        if tile.tile_type == "corridor":
            log.append(f"Search roll: d6 = {roll} (corridor -1 = {effective_roll}).")
        else:
            log.append(f"Search roll: d6 = {roll}.")
    effective_roll, search_notes = adjust_search_roll(
        session.party,
        effective_roll,
        choice=None,
        session=session,
        environment=tile.environment,
        tile_id=tile.id,
    )
    log.extend(search_notes)
    if show_rolls and search_notes:
        log.append(f"Adjusted search roll: {effective_roll}.")
    if explain_math:
        log.append(f"Search table: {table_roller.search_table_summary()}.")
    return SearchRollResolution(
        effective_roll=effective_roll,
        outcome=table_roller.lookup_search(effective_roll),
        log=log,
    )
