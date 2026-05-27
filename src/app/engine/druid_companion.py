"""Druid animal companion (EE p.32)."""

from __future__ import annotations

from ..schemas import PartyMemberState, SessionState, TileState
from .dice import roll_d6
from .terrain import tile_is_outdoors


COMPANION_KINDS: dict[str, dict[str, int | str]] = {
    "wolf": {"name": "Wolf", "level": 3, "life": 4},
    "bear": {"name": "Bear", "level": 4, "life": 6},
    "panther": {"name": "Panther", "level": 3, "life": 3},
}


def druid_in_party(party: list[PartyMemberState]) -> PartyMemberState | None:
    return next(
        (member for member in party if member.class_id.lower() == "druid" and member.current_life > 0),
        None,
    )


def companion_kind(member: PartyMemberState) -> str:
    kind = (member.companion_kind or "wolf").strip().lower()
    return kind if kind in COMPANION_KINDS else "wolf"


def companion_profile(kind: str) -> dict[str, int | str]:
    return COMPANION_KINDS.get(kind, COMPANION_KINDS["wolf"])


def consume_food_ration(member: PartyMemberState) -> bool:
    for index, item in enumerate(member.inventory):
        if "food" in item.lower() and "ration" in item.lower():
            member.inventory.pop(index)
            return True
    return False


def wilderness_tile(tile: TileState | None) -> bool:
    if tile is None:
        return False
    return tile_is_outdoors(tile.terrain)


def summon_companion(
    session: SessionState,
    druid: PartyMemberState,
    *,
    tile: TileState | None = None,
    force: bool = False,
) -> list[str]:
    log: list[str] = []
    if session.druid_companion_life > 0 and not force:
        return log
    if not force:
        if tile is None:
            tile = next(
                (item for item in session.map_state.tiles if item.id == session.map_state.current_tile_id),
                None,
            )
        if not wilderness_tile(tile):
            return log
    if not consume_food_ration(druid):
        log.append(f"{druid.name} needs 1 Food ration to welcome an animal companion.")
        return log
    kind = companion_kind(druid)
    profile = companion_profile(kind)
    session.druid_companion_owner_id = druid.character_id
    session.druid_companion_kind = kind
    session.druid_companion_life = int(profile["life"])
    session.druid_companion_max_life = int(profile["life"])
    session.druid_companion_level = int(profile["level"])
    log.append(
        f"A {profile['name']} joins {druid.name} "
        f"({session.druid_companion_life} Life, L{session.druid_companion_level}; 1 Food ration offered)."
    )
    return log


def maybe_summon_on_wilderness_entry(session: SessionState, tile: TileState) -> list[str]:
    if not wilderness_tile(tile):
        return []
    druid = druid_in_party(session.party)
    if druid is None or session.druid_companion_life > 0:
        return []
    return summon_companion(session, druid, tile=tile)


def companion_attack_log(session: SessionState, target_name: str) -> list[str]:
    if session.druid_companion_life <= 0:
        return []
    profile = companion_profile(session.druid_companion_kind or "wolf")
    return [
        f"The druid's {profile['name']} attacks {target_name} for 1 Life "
        f"({session.druid_companion_life} Life remaining)."
    ]


def companion_take_damage(session: SessionState, party: list[PartyMemberState], amount: int = 1) -> list[str]:
    if session.druid_companion_life <= 0:
        return []
    profile = companion_profile(session.druid_companion_kind or "wolf")
    session.druid_companion_life = max(0, session.druid_companion_life - amount)
    if session.druid_companion_life <= 0:
        owner_id = session.druid_companion_owner_id
        session.druid_companion_owner_id = None
        session.druid_companion_kind = None
        log = [f"The {profile['name']} companion is slain!"]
        druid = next((member for member in party if member.character_id == owner_id), None)
        if druid is not None:
            if not any(status.lower().startswith("madness") for status in druid.statuses):
                druid.statuses.append("Madness 1")
            log.append(f"{druid.name} gains 1 Madness.")
        return log
    return [f"The {profile['name']} companion takes {amount} damage ({session.druid_companion_life} Life left)."]


def foes_strike_companion(
    session: SessionState,
    party: list[PartyMemberState],
    foe_level: int,
    *,
    show_rolls: bool,
) -> list[str]:
    if session.druid_companion_life <= 0:
        return []
    total = roll_d6() + foe_level
    companion_level = session.druid_companion_level or 3
    log: list[str] = []
    if show_rolls:
        log.append(f"Foe vs companion: {total} vs L{companion_level}.")
    if total >= companion_level:
        log.extend(companion_take_damage(session, party, 1))
    else:
        profile = companion_profile(session.druid_companion_kind or "wolf")
        log.append(f"A foe misses the {profile['name']} companion.")
    return log
