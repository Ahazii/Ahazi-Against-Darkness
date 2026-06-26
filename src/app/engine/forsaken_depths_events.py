"""Forsaken Depths event mechanics (fd_event_table, FD p.63)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState, TileState
from .dice import roll_d3, roll_d6, roll_exploding_for_level, roll_tile_key
from .forsaken_depths_content import apply_fd_hallucination
from .forsaken_depths_items import grant_fd_magic_item_to_party, roll_fd_magic_item

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


def _living_party(session: SessionState) -> list[PartyMemberState]:
    return [member for member in session.party if member.current_life > 0]


def _fd_save_vs_level(
    member: PartyMemberState,
    level: int,
    *,
    label: str,
    show_rolls: bool,
    swim: bool = False,
) -> tuple[bool, list[str]]:
    from .class_combat import save_modifier

    total, rolls = roll_exploding_for_level(member)
    modifier = save_modifier(member, trap=True, swim=swim)
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier} vs {level}."
        )
    failed = rolls[0] == 1 or total + modifier < level
    if failed and member.class_id.lower() == "halfling":
        total, rolls = roll_exploding_for_level(member)
        if show_rolls:
            log.append(
                f"Halfling reroll: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier}."
            )
        failed = rolls[0] == 1 or total + modifier < level
    log.append(f"{member.name} {'fails' if failed else 'passes'} the {label}.")
    return failed, log


def apply_fd_event_flood(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    swim_level = hcl + 2
    if show_rolls:
        session.log.append(f"Flood (FD p.63): each hero makes 3 Swimming Saves vs {swim_level}.")
    for member in _living_party(session):
        for attempt in range(1, 4):
            failed, save_log = _fd_save_vs_level(
                member,
                swim_level,
                label=f"Swimming Save {attempt}/3",
                show_rolls=show_rolls,
                swim=True,
            )
            session.log.extend(save_log)
            if failed:
                member.current_life = max(0, member.current_life - 1)
                session.log.append(f"{member.name} loses 1 Life to the flood ({member.current_life}/{member.max_life}).")
    for member in _living_party(session):
        destroyed: list[str] = []
        kept: list[str] = []
        for item in list(member.inventory):
            if "scroll" not in item.lower():
                kept.append(item)
                continue
            if roll_d6() <= 2:
                destroyed.append(item)
            else:
                kept.append(item)
        if destroyed:
            member.inventory = kept
            session.log.append(f"Flood ruins {member.name}'s scroll(s): {', '.join(destroyed)} (2-in-6 each, FD p.63).")
    session.fd_flood_bow_penalty_rooms = 12
    for member in _living_party(session):
        if any(
            token in item.lower()
            for item in member.inventory
            for token in ("bow", "crossbow", "sling")
        ) or (member.default_missile_weapon and "bow" in member.default_missile_weapon.lower()):
            if "Flood-damaged bowstrings (-2 Attack)" not in member.statuses:
                member.statuses.append("Flood-damaged bowstrings (-2 Attack)")
    session.log.append(
        "Bows and crossbows suffer -2 Attack until the strings dry (12 rooms / 2 hours, FD p.63)."
    )


def apply_fd_event_earthquake(
    session: SessionState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    stone_level = roll_d3() + hcl
    if show_rolls:
        session.log.append(f"Earthquake (FD p.63): falling stones at level {stone_level} (d3+HCL).")
    for member in _living_party(session):
        failed, save_log = _fd_save_vs_level(
            member,
            stone_level,
            label="Earthquake Save",
            show_rolls=show_rolls,
        )
        session.log.extend(save_log)
        if failed:
            member.current_life = max(0, member.current_life - 1)
            session.log.append(f"{member.name} takes 1 Life from falling stone ({member.current_life}/{member.max_life}).")


def apply_fd_event_labyrinth_shift(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> None:
    visited = list(session.visited_tile_ids or [])
    targets = visited[-5:] if len(visited) >= 5 else visited
    if not targets:
        session.log.append("Labyrinth shifts, but no visited rooms are reshaped yet (FD p.63).")
        return
    if show_rolls:
        session.log.append(
            f"Labyrinth shifts (FD p.63): rerolling shapes (not content) for {len(targets)} visited room(s)."
        )
    for tile_id in targets:
        tile = engine._tile_by_id(session, tile_id)
        if tile is None or tile.content_key == "entrance":
            continue
        catalog = getattr(tile, "tile_catalog", None) or (
            "forsaken_depths" if session.ruleset == "forsaken_depths" else "ee"
        )
        old_key = tile.tile_key
        for _ in range(8):
            new_key = roll_tile_key()
            tile_def = engine._load_tile_catalog(catalog).get(new_key)
            if tile_def is None:
                continue
            if engine._tile_type(tile_def.tile_type) == tile.tile_type:
                tile.tile_key = new_key
                engine._resync_tile_from_definition(tile)
                if show_rolls:
                    session.log.append(f"{tile.title}: shape {old_key} → {new_key} (content unchanged).")
                break


def apply_fd_event_nightmare_mist(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    save_level = hcl + 2
    if show_rolls:
        session.log.append(f"Nightmare Mist (FD p.63): Save vs {save_level} or roll Hallucinations Table.")
    for member in _living_party(session):
        if any("mask of thar-tizan" in item.lower() for item in member.inventory):
            session.log.append(f"{member.name}'s Mask of Thar-Tizan ignores the mist (FD p.63).")
            continue
        failed, save_log = _fd_save_vs_level(
            member,
            save_level,
            label="Nightmare Mist Save",
            show_rolls=show_rolls,
        )
        session.log.extend(save_log)
        if failed:
            apply_fd_hallucination(engine, session, tile, hcl=hcl, show_rolls=show_rolls)


def offer_fd_event_portal(session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
    tile.fd_portal_available = True
    session.fd_portal_tile_id = tile.id
    if show_rolls:
        session.log.append(
            "The Portal (FD p.63): choose Abyss, Netherworld, or Demesne on this tile. "
            "Each crossing hero takes 1 Life."
        )


def choose_fd_event_portal(
    engine: RandomDungeonEngine,
    session: SessionState,
    destination: str | None,
    *,
    show_rolls: bool = True,
    explain_math: bool = False,
) -> bool:
    if session.mode != "exploration":
        session.log.append("Use the Portal during exploration.")
        return False
    tile_id = session.fd_portal_tile_id
    if not tile_id:
        session.log.append("No Portal is awaiting a destination choice.")
        return False
    tile = engine._tile_by_id(session, tile_id)
    if tile is None:
        session.fd_portal_tile_id = None
        session.log.append("The Portal tile is no longer on the map.")
        return False
    if destination not in {"abyss", "netherworld", "demesne"}:
        session.log.append("Choose Abyss, Netherworld, or Demesne for the Portal.")
        return False
    if destination == "demesne":
        from .courtship_demesne import enter_courtship_demesne

        return enter_courtship_demesne(engine, session, tile, show_rolls=show_rolls)
    previous = session.environment
    env = "fungal_grottoes" if destination == "abyss" else "caverns"
    label = "Abyss" if destination == "abyss" else "Netherworld"
    for member in _living_party(session):
        member.current_life = max(0, member.current_life - 1)
        session.log.append(
            f"{member.name} crosses the Portal to the {label} and takes 1 Life ({member.current_life}/{member.max_life})."
        )
    ok = engine._open_secret_passage_destination(
        session,
        tile,
        env,
        previous_environment=previous,
        show_rolls=show_rolls,
        explain_math=explain_math,
    )
    if ok:
        session.log.append(f"Portal branch opened to {label} ({env} environment, FD p.63).")
        tile.fd_portal_available = False
        session.fd_portal_tile_id = None
    return ok


def setup_fd_hidden_treasure_chamber(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    tile.fd_hidden_treasure_chamber = True
    if "Hidden Treasure Chamber" not in tile.objects:
        tile.objects.append("Hidden Treasure Chamber")
    session.log.append(
        "Hidden Treasure Chamber (FD p.63): defeat the guarded Weird Monster, then claim three tier-appropriate magic items."
    )


def claim_fd_hidden_treasure_chamber(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    tile = engine._current_tile(session)
    if not tile.fd_hidden_treasure_chamber:
        session.log.append("No Hidden Treasure Chamber loot is ready here.")
        return False
    if tile.enemies or not tile.resolved:
        session.log.append("Clear the chamber guardian before claiming the magic items.")
        return False
    if tile.fd_hidden_treasure_claimed:
        session.log.append("The Hidden Treasure Chamber has already been looted.")
        return False
    hcl = engine._highest_character_level(session.party)
    recipients = _living_party(session) or session.party
    holder = recipients[0]
    items: list[str] = []
    for _ in range(3):
        item, log = roll_fd_magic_item(engine, session, hcl=hcl, show_rolls=show_rolls)
        session.log.extend(log)
        items.append(item)
        grant_fd_magic_item_to_party(engine, session, holder, item, show_rolls=show_rolls)
    tile.fd_hidden_treasure_claimed = True
    tile.treasure_items = list(tile.treasure_items or []) + items
    session.log.append(
        f"Hidden Treasure Chamber claimed: {', '.join(items)} awarded to {holder.name} (FD p.63)."
    )
    return True


def tick_fd_flood_bow_penalty(session: SessionState, *, show_rolls: bool = False) -> None:
    if session.fd_flood_bow_penalty_rooms <= 0:
        return
    session.fd_flood_bow_penalty_rooms -= 1
    if session.fd_flood_bow_penalty_rooms <= 0:
        for member in session.party:
            member.statuses = [
                status
                for status in member.statuses
                if status != "Flood-damaged bowstrings (-2 Attack)"
            ]
        if show_rolls:
            session.log.append("Flood-damaged bowstrings have dried — ranged Attack penalty ends (FD p.63).")
