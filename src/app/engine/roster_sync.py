from __future__ import annotations

from ..db import Store, now_utc
from ..schemas import Character, SessionState

_COMBAT_STATUS_ROOTS = frozenset(
    {
        "protection",
        "barkskin",
        "illusionary armor",
        "bear form",
        "illusionary sword",
        "specter swarm",
        "mirror image",
    }
)


def roster_statuses(statuses: list[str]) -> list[str]:
    kept: list[str] = []
    for status in statuses:
        root = status.split("(")[0].strip().lower()
        if root in _COMBAT_STATUS_ROOTS:
            continue
        if status.lower().startswith("mirror image"):
            continue
        kept.append(status)
    return kept


def roster_xp(session: SessionState, member_xp: int) -> int:
    if session.xp_system == "old_school":
        return session.old_school_xp_tally
    if session.xp_system == "slower_advancement":
        return session.slower_xp_bank
    return member_xp


def initial_xp_tally(party_xp: list[int]) -> int:
    return max(party_xp, default=0)


def persist_session_to_roster(session: SessionState, store: Store) -> list[str]:
    timestamp = now_utc()
    notes: list[str] = []
    for member in session.party:
        character = store.get("characters", member.character_id, Character.model_validate)
        if character is None:
            continue
        character.level = member.level
        character.xp = roster_xp(session, member.xp)
        character.gold = member.gold
        character.current_life = member.current_life
        character.max_life = member.max_life
        character.attack_bonus = member.attack_bonus
        character.defense_bonus = member.defense_bonus
        character.save_bonus = member.save_bonus
        character.inventory = list(member.inventory)
        character.spells = list(member.spells)
        character.abilities = list(member.abilities)
        character.statuses = roster_statuses(member.statuses)
        character.default_melee_weapon = member.default_melee_weapon
        character.default_missile_weapon = member.default_missile_weapon
        character.updated_at = timestamp
        store.save("characters", character)
        if member.current_life > 0:
            notes.append(
                f"{member.name}: Level {character.level}, {character.gold} gp, "
                f"{character.current_life}/{character.max_life} Life saved to roster."
            )
        else:
            notes.append(
                f"{member.name}: fallen ({character.current_life}/{character.max_life} Life) saved to roster."
            )
    return notes
