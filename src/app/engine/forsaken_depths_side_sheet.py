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
    if kind == "dark_pits":
        return "Dark Pits"
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
    if kind == "dark_pits":
        quest = session.active_quest
        if quest and quest.fd_quest_dark_pits_rooms:
            return quest.fd_quest_dark_pits_rooms
        return roll_d6() + 3
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
        page = "56" if kind in {"ruins", "dark_pits"} else "60"
        session.log.append(
            f"{label} room {session.fd_side_sheet_rooms_entered}/{session.fd_side_sheet_rooms_total} "
            f"(separate sheet, FD p.{page})."
        )
    if kind == "ruins" or kind == "dark_pits":
        from .forsaken_depths_content import apply_ruins_room_content

        apply_ruins_room_content(engine, session, tile, hcl=hcl, show_rolls=show_rolls)
    else:
        from .forsaken_depths_citadel import apply_fd_citadel_room

        apply_fd_citadel_room(engine, session, tile, hcl=hcl, show_rolls=show_rolls)
    if session.fd_side_sheet_rooms_entered >= session.fd_side_sheet_rooms_total:
        if kind == "dark_pits":
            _maybe_complete_fd_dark_pits(session, tile, show_rolls=show_rolls)
        elif show_rolls:
            session.log.append(
                f"{label} side sheet complete — use Return to main map when ready (FD p.60)."
            )
    tile.resolved = True


def _maybe_complete_fd_dark_pits(
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    quest = session.active_quest
    if quest is None or quest.key != "fd_dark_pits":
        return
    if not tile.enemies:
        quest.fd_quest_dark_pits_cleared = True
        if show_rolls:
            session.log.append(
                "Dark Pits cleared — return to the Lady in Gray for your reward (FD p.54)."
            )
        return
    if show_rolls:
        session.log.append(
            "Dark Pits room budget reached — clear remaining occupants, then return to the Quest-giver (FD p.54)."
        )


def enter_fd_dark_pits(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    quest = session.active_quest
    if quest is None or quest.key != "fd_dark_pits" or quest.fd_quest_dark_pits_cleared:
        session.log.append("No Dark Pits quest is ready to enter.")
        return False
    if session.fd_side_sheet_active:
        session.log.append("Finish or exit the current side sheet before entering the Dark Pits.")
        return False
    tile = engine._current_tile(session)
    if tile is None:
        return False
    return enter_fd_side_sheet(engine, session, tile, kind="dark_pits", show_rolls=show_rolls)


def enter_fd_side_sheet(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    kind: str | None = None,
    room_budget: int | None = None,
    force: bool = False,
    show_rolls: bool = True,
) -> bool:
    if kind == "dark_pits":
        chosen = "dark_pits"
    else:
        if force:
            chosen = kind or "ruins"
        else:
            available, inferred = fd_side_sheet_entry_available(session, tile)
            if not available:
                session.log.append("No side dungeon entrance is available here.")
                return False
            chosen = kind or inferred
    if chosen not in {"citadel", "ruins", "dark_pits"}:
        session.log.append("Unknown side dungeon type.")
        return False
    if chosen == "citadel" and not session.fd_citadel_type:
        from .forsaken_depths_content import roll_fd_citadel

        roll_fd_citadel(engine, session, tile, show_rolls=show_rolls)
        session.fd_citadel_entry_tile_id = tile.id
    rooms = room_budget if room_budget is not None else _side_sheet_room_budget(session, chosen)
    session.fd_side_sheet_active = True
    session.fd_side_sheet_kind = chosen  # type: ignore[assignment]
    session.fd_side_sheet_origin_tile_id = tile.id
    session.fd_side_sheet_rooms_total = rooms
    session.fd_side_sheet_rooms_entered = 0
    session.fd_side_sheet_visited_tile_ids = []
    tile.fd_side_sheet_entry_used = True
    if chosen == "citadel" and session.fd_citadel_type == "magic_citadel":
        session.fd_magic_citadel_mr_active = True
        if show_rolls:
            session.log.append("Magic Citadel: magic resistance is suspended on this side sheet (FD p.60).")
    label = fd_side_sheet_kind_label(chosen)
    if show_rolls:
        session.log.append(
            f"The party enters the {label} side sheet ({rooms} rooms). "
            f"Map these areas in a different color (FD p.{'54' if chosen == 'dark_pits' else '39' if chosen == 'ruins' else '60'})."
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
    session.fd_magic_citadel_mr_active = False
    session.map_state.current_tile_id = origin.id
    session.current_tile_entry_exit_id = None
    if show_rolls:
        session.log.append(
            f"The party returns to {origin.title} from the "
            f"{fd_side_sheet_kind_label(session.fd_side_sheet_kind)} side sheet."
        )
    return True
