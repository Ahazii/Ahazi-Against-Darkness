"""Forsaken Depths citadel type modifiers on side-dungeon sheets (FD p.60)."""

from __future__ import annotations

import copy
import uuid
from typing import TYPE_CHECKING

from ..schemas import EnemyState, SessionState, TileState
from .dice import roll_d6, roll_formula
from .forsaken_depths_map import is_fd_ruleset

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

PRISONERS_ESCAPE_CLUES = 4


def fd_citadel_side_sheet_active(session: SessionState) -> bool:
    return bool(
        is_fd_ruleset(session)
        and session.fd_side_sheet_active
        and session.fd_side_sheet_kind == "citadel"
        and session.fd_citadel_type
    )


def fd_citadel_type(session: SessionState) -> str | None:
    if not fd_citadel_side_sheet_active(session):
        return None
    return session.fd_citadel_type


def fd_citadel_is_final_room(session: SessionState) -> bool:
    if not fd_citadel_side_sheet_active(session):
        return False
    total = session.fd_side_sheet_rooms_total or 0
    entered = session.fd_side_sheet_rooms_entered or 0
    return total > 0 and entered >= total


def fd_citadel_reaction_adjust(session: SessionState, tile: TileState | None) -> tuple[int, list[str]]:
    if not tile or not fd_citadel_side_sheet_active(session) or not tile.fd_side_sheet:
        return 0, []
    if session.fd_citadel_type == "crowded_citadel":
        return -1, ["Crowded Citadel: −1 on Reaction rolls (FD p.60)."]
    return 0, []


def fd_magic_citadel_mr_suspended(session: SessionState, tile: TileState | None) -> bool:
    return (
        fd_citadel_side_sheet_active(session)
        and session.fd_citadel_type == "magic_citadel"
        and tile is not None
        and tile.fd_side_sheet
    )


def fd_citadel_of_dead_blocks_healing(
    session: SessionState,
    tile: TileState | None,
    *,
    source: str,
) -> str | None:
    """Block non-bandage healing in Citadel of Dead Things."""
    if source == "bandage":
        return None
    if (
        fd_citadel_side_sheet_active(session)
        and session.fd_citadel_type == "citadel_of_dead"
        and tile is not None
        and tile.fd_side_sheet
    ):
        return (
            f"Citadel of Dead Things: no {source} healing except bandages (FD p.60)."
        )
    return None


def fd_prisoners_escape_available(session: SessionState) -> bool:
    return (
        fd_citadel_side_sheet_active(session)
        and session.fd_citadel_type == "prisoners_citadel"
    )


def apply_fd_citadel_room(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool,
) -> None:
    citadel_key = session.fd_citadel_type or "ghost_citadel"
    is_final = fd_citadel_is_final_room(session)

    if citadel_key == "ghost_citadel" and is_final:
        _spawn_citadel_weird_final(engine, session, tile, hcl=hcl, show_rolls=show_rolls, label="Ghost Citadel Final Boss")
        return

    if citadel_key == "magic_citadel" and is_final:
        _spawn_citadel_weird_final(
            engine,
            session,
            tile,
            hcl=hcl,
            show_rolls=show_rolls,
            label="Cyclopean Idol",
            table_roll=1,
        )
        if "Cyclopean Idol" not in tile.objects:
            tile.objects.append("Cyclopean Idol")
        return

    content = engine._roll_fd_content(session, tile.tile_type, hcl)
    tile.content_key = content["key"]
    tile.description = engine._tile_description(tile.description, content["description"])
    tile.objects = list(content.get("objects") or [])
    if content.get("enemies"):
        tile.enemies.extend(content["enemies"])
        tile.initial_enemy_count = len(tile.enemies)

    if citadel_key == "crowded_citadel" and content.get("key") == "fd_minions" and tile.enemies:
        _double_minion_enemies(tile)
        if show_rolls:
            session.log.append(
                f"Crowded Citadel: doubled minions to {len(tile.enemies)} (FD p.60)."
            )

    if citadel_key == "citadel_of_traps":
        _apply_traps_citadel_room(engine, session, tile, hcl=hcl, content_key=content.get("key", ""), show_rolls=show_rolls)

    if citadel_key == "magic_citadel" and roll_d6() <= 3:
        feature = "Idol" if roll_d6() % 2 else "Altar"
        if feature not in tile.objects:
            tile.objects.append(feature)
        if show_rolls:
            session.log.append(f"Magic Citadel: {feature} in this chamber (FD p.60).")

    if citadel_key == "citadel_of_dead" and show_rolls and session.fd_side_sheet_rooms_entered == 1:
        session.log.append(
            "Citadel of Dead Things: only bandages restore Life here (FD p.60)."
        )

    if citadel_key == "prisoners_citadel" and show_rolls and session.fd_side_sheet_rooms_entered == 1:
        session.log.append(
            f"Prisoners of the Citadel: spend {PRISONERS_ESCAPE_CLUES} Clues on the map panel to escape (FD p.60)."
        )


def escape_fd_prisoners_citadel(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not fd_prisoners_escape_available(session):
        session.log.append("Prisoners escape is only available in the Prisoners of the Citadel side sheet.")
        return False
    if session.clues_found < PRISONERS_ESCAPE_CLUES:
        session.log.append(
            f"Need {PRISONERS_ESCAPE_CLUES} Clues to escape the citadel (party has {session.clues_found}, FD p.60)."
        )
        return False
    if not engine._spend_clues(session, PRISONERS_ESCAPE_CLUES):
        session.log.append(
            f"Need {PRISONERS_ESCAPE_CLUES} Clues to escape the citadel (party has {session.clues_found})."
        )
        return False
    if show_rolls:
        session.log.append(
            f"The party escapes the citadel with secret knowledge ({PRISONERS_ESCAPE_CLUES} Clues spent, FD p.60)."
        )
    from .forsaken_depths_side_sheet import exit_fd_side_sheet

    return exit_fd_side_sheet(engine, session, show_rolls=show_rolls)


def _double_minion_enemies(tile: TileState) -> None:
    clones: list[EnemyState] = []
    for enemy in tile.enemies:
        if enemy.life <= 0:
            continue
        duplicate = copy.deepcopy(enemy)
        duplicate.id = str(uuid.uuid4())
        clones.append(duplicate)
    tile.enemies.extend(clones)
    tile.initial_enemy_count = len(tile.enemies)


def _apply_traps_citadel_room(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    content_key: str,
    show_rolls: bool,
) -> None:
    if content_key != "fd_minions" or roll_d6() > 4:
        return
    tile.enemies = []
    tile.initial_enemy_count = 0
    trap = engine.table_roller.roll_fd_trap(hcl, show_rolls=show_rolls, explain_math=False)
    tile.trap_key = trap.trap_key
    tile.trap_level = trap.trap_level
    tile.content_key = "fd_trap"
    if trap.summary not in tile.objects:
        tile.objects = [obj for obj in tile.objects if obj.lower() != "servitors"]
        tile.objects.append(trap.summary)
    if roll_d6() <= 2:
        outcome = engine.table_roller.roll_fd_treasure(
            show_rolls=False,
            silk_already_found=session.fd_silk_treasure_used,
        )
        engine._stage_treasure_outcome(session, tile, outcome, show_rolls=show_rolls)
    if show_rolls:
        session.log.append("Citadel of Traps: minions replaced by a trap (FD p.60).")


def _spawn_citadel_weird_final(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool,
    label: str,
    table_roll: int | None = None,
) -> None:
    roll = table_roll if table_roll is not None else roll_d6()
    row = engine.table_roller.lookup("fd_citadel_weird_table", roll)
    if row is None:
        if show_rolls:
            session.log.append(f"{label}: Citadel Weird roll {roll} — no table row (FD p.61).")
        return
    name = row.get("name") or f"Citadel Weird {roll}"
    if show_rolls:
        session.log.append(
            f"{label}: Citadel Weird Table d6 = {roll} → {name} (FD p.{'60' if 'Idol' in label else '61'})."
        )
    spawned = engine._fd_spawn_from_table_row(session, row, hcl)
    if spawned:
        tile.enemies.extend(spawned)
        tile.initial_enemy_count = len(tile.enemies)
        tile.content_key = "fd_weird"
        tile.description = engine._tile_description(
            tile.description,
            f"The final chamber holds {name}.",
        )
        if "Boss Monster" not in tile.objects and "Weird Monster" not in tile.objects:
            tile.objects.append("Weird Monster")
        if session.mode == "exploration":
            engine._announce_encounter(session, tile, show_rolls=show_rolls)
