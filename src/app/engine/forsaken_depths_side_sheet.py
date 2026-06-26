"""Forsaken Depths side-dungeon sheets (citadel / river ruins) on the live map."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import SessionState, TileState
from .dice import roll_d6, roll_formula
from .forsaken_depths_map import is_fd_ruleset, tile_has_room_code

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


def fd_side_sheet_kind_label(kind: str | None) -> str:
    if kind == "ruins":
        return "Forsaken Ruins"
    if kind == "citadel":
        return "Citadel"
    return "Side dungeon"


def fd_side_sheet_entry_available(session: SessionState, tile: TileState) -> tuple[bool, str | None]:
    """Return whether Enter side dungeon is offered on this tile."""
    if not is_fd_ruleset(session) or session.fd_side_sheet_active or tile.fd_side_sheet_entry_used:
        return False, None
    if tile_has_room_code(tile, "Ru"):
        return True, "ruins"
    if tile_has_room_code(tile, "ETC") or (
        session.fd_citadel_entry_tile_id == tile.id and session.fd_citadel_type
    ):
        return True, "citadel"
    return False, None


def fd_side_sheet_can_expand(session: SessionState) -> bool:
    if not session.fd_side_sheet_active:
        return True
    return session.fd_side_sheet_rooms_entered < session.fd_side_sheet_rooms_total


def _side_sheet_room_budget(session: SessionState, kind: str) -> int:
    if kind == "ruins":
        return roll_d6() + 2
    return int(session.fd_citadel_room_count or roll_formula("3d6"))


def apply_fd_side_sheet_room(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    if not session.fd_side_sheet_active or not tile.fd_side_sheet:
        return
    if tile.id in session.fd_side_sheet_visited_tile_ids:
        return
    session.fd_side_sheet_visited_tile_ids.append(tile.id)
    session.fd_side_sheet_rooms_entered += 1
    hcl = engine._highest_character_level(session.party)
    kind = session.fd_side_sheet_kind or "ruins"
    label = fd_side_sheet_kind_label(kind)
    if show_rolls:
        session.log.append(
            f"{label} room {session.fd_side_sheet_rooms_entered}/{session.fd_side_sheet_rooms_total} "
            f"(separate sheet, FD p.{'56' if kind == 'ruins' else '60'})."
        )
    if kind == "ruins":
        from .forsaken_depths_content import apply_ruins_room_content

        apply_ruins_room_content(engine, session, tile, hcl=hcl, show_rolls=show_rolls)
    else:
        _apply_citadel_side_room(engine, session, tile, hcl=hcl, show_rolls=show_rolls)
    if session.fd_side_sheet_rooms_entered >= session.fd_side_sheet_rooms_total and show_rolls:
        session.log.append(
            f"{label} side sheet complete — use Return to main map when ready (FD p.60)."
        )
    tile.resolved = True


def _apply_citadel_side_room(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool,
) -> None:
    citadel_key = session.fd_citadel_type or "ghost_citadel"
    content = engine._roll_fd_content(session, tile.tile_type, hcl)
    tile.content_key = content["key"]
    tile.description = engine._tile_description(tile.description, content["description"])
    tile.objects = list(content.get("objects") or [])
    if content.get("enemies"):
        tile.enemies.extend(content["enemies"])
        tile.initial_enemy_count = len(tile.enemies)
    if citadel_key == "citadel_of_traps" and roll_d6() <= 4 and show_rolls:
        trap = engine.table_roller.roll_fd_trap(hcl, show_rolls=show_rolls, explain_math=False)
        tile.trap_key = trap.trap_key
        tile.trap_level = trap.trap_level
        if trap.summary not in tile.objects:
            tile.objects.append(trap.summary)
        session.log.append("Citadel of Traps: minions often replaced by traps (FD p.60).")
    elif citadel_key == "crowded_citadel" and tile.enemies and show_rolls:
        session.log.append("Crowded Citadel: double minion counts and −1 Reaction (FD p.60).")
    elif show_rolls and session.fd_citadel_room_count:
        row = next(
            (
                item
                for item in engine.table_roller.tables.get("fd_citadel_table", [])
                if item.get("key") == citadel_key
            ),
            None,
        )
        if row and row.get("summary"):
            session.log.append(str(row["summary"]))


def enter_fd_side_sheet(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    kind: str | None = None,
    show_rolls: bool = True,
) -> bool:
    available, inferred = fd_side_sheet_entry_available(session, tile)
    if not available:
        session.log.append("No side dungeon entrance is available here.")
        return False
    chosen = kind or inferred
    if chosen not in {"citadel", "ruins"}:
        session.log.append("Unknown side dungeon type.")
        return False
    if chosen == "citadel" and not session.fd_citadel_type:
        from .forsaken_depths_content import roll_fd_citadel

        roll_fd_citadel(engine, session, tile, show_rolls=show_rolls)
        session.fd_citadel_entry_tile_id = tile.id
    rooms = _side_sheet_room_budget(session, chosen)
    session.fd_side_sheet_active = True
    session.fd_side_sheet_kind = chosen  # type: ignore[assignment]
    session.fd_side_sheet_origin_tile_id = tile.id
    session.fd_side_sheet_rooms_total = rooms
    session.fd_side_sheet_rooms_entered = 0
    session.fd_side_sheet_visited_tile_ids = []
    tile.fd_side_sheet_entry_used = True
    label = fd_side_sheet_kind_label(chosen)
    if show_rolls:
        session.log.append(
            f"The party enters the {label} side sheet ({rooms} rooms). "
            f"Map these areas in a different color (FD p.{'39' if chosen == 'ruins' else '60'})."
        )
    side_exit = engine._ensure_side_sheet_exit(session, tile)
    if side_exit is None:
        session.fd_side_sheet_active = False
        session.log.append("No open edge to place the first side-sheet room.")
        return False
    engine._explore(
        session,
        exit_id=side_exit.id,
        show_rolls=show_rolls,
        explain_math=False,
    )
    return session.fd_side_sheet_active


def exit_fd_side_sheet(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.fd_side_sheet_active:
        session.log.append("The party is not on a side dungeon sheet.")
        return False
    origin_id = session.fd_side_sheet_origin_tile_id
    if not origin_id:
        session.log.append("Side sheet origin is unknown.")
        return False
    origin = engine._tile_by_id(session, origin_id)
    if origin is None:
        session.log.append("The side sheet origin map element is no longer on the map.")
        return False
    session.fd_side_sheet_active = False
    session.map_state.current_tile_id = origin.id
    session.current_tile_entry_exit_id = None
    if show_rolls:
        session.log.append(
            f"The party returns to {origin.title} from the "
            f"{fd_side_sheet_kind_label(session.fd_side_sheet_kind)} side sheet."
        )
    return True
