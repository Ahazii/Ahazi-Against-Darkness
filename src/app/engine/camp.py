from __future__ import annotations

from ..schemas import SessionState


def fallen_in_dungeon(session: SessionState) -> list[str]:
    fallen: list[str] = []
    for tile in session.map_state.tiles:
        for character_id in tile.fallen_character_ids:
            if character_id not in fallen:
                fallen.append(character_id)
    return fallen


def heal_living_party(session: SessionState) -> list[str]:
    healed_names: list[str] = []
    for member in session.party:
        if member.current_life <= 0:
            continue
        if member.current_life < member.max_life:
            healed_names.append(member.name)
        member.current_life = member.max_life
    return healed_names


def append_between_foray_refresh_log(session: SessionState, healed_names: list[str]) -> None:
    if healed_names:
        session.log.append(f"Living heroes recover to full Life: {', '.join(healed_names)}.")
    else:
        session.log.append("Living heroes are ready to return when preparations are done.")
    session.log.append("Spells, prayers, rest, and per-foray class resources refresh at camp.")


def explored_map_element_count(session: SessionState) -> int:
    visited = set(session.visited_tile_ids or [])
    if session.map_state.current_tile_id:
        visited.add(session.map_state.current_tile_id)
    return max(1, len(visited), len(session.map_state.tiles or []))
