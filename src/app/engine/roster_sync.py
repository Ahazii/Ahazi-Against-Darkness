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


def sync_minor_encounters_to_roster(session: SessionState, store: Store) -> None:
    timestamp = now_utc()
    progress = session.minor_encounters_defeated
    for member in session.party:
        character = store.get("characters", member.character_id, Character.model_validate)
        if character is None:
            continue
        character.minor_encounters_cleared = progress
        character.updated_at = timestamp
        store.save("characters", character)


def session_allows_party_edit(session: SessionState) -> bool:
    if session.mode in {"complete", "combat"}:
        return False
    return session.camped_outside or session.saved_at is not None


def replace_session_party(
    session: SessionState,
    character_ids: list[str],
    store: Store,
    *,
    member_state,
) -> None:
    if not session_allows_party_edit(session):
        raise ValueError("Party changes are only allowed while camped outside or from a saved game.")
    if len(set(character_ids)) != 4:
        raise ValueError("Choose four different heroes.")

    characters = []
    for character_id in character_ids:
        character = store.get("characters", character_id, Character.model_validate)
        if character is None:
            raise ValueError(f"Character {character_id} not found.")
        busy_session_id = character_busy_session_id(character, store)
        if busy_session_id and busy_session_id != session.id:
            raise ValueError(f"{character.name} is already in another active adventure.")
        characters.append(character)

    old_by_id = {member.character_id: member for member in session.party}
    old_ids = set(old_by_id)
    new_ids = set(character_ids)

    timestamp = now_utc()
    new_party: list = []
    for index, character_id in enumerate(character_ids, start=1):
        if character_id in old_by_id:
            member = old_by_id[character_id].model_copy(deep=True)
            member.marching_order = index
            new_party.append(member)
            continue
        character = next(item for item in characters if item.id == character_id)
        member = member_state(character)
        member.marching_order = index
        new_party.append(member)

    for character_id in old_ids - new_ids:
        character = store.get("characters", character_id, Character.model_validate)
        if character is None:
            continue
        if character.active_session_id == session.id:
            character.active_session_id = None
            character.updated_at = timestamp
            store.save("characters", character)

    session.party = new_party
    if session.carried_body_id and session.carried_body_id not in new_ids:
        session.carried_body_id = None
        session.body_carrier_id = None
    if session.body_carrier_id and session.body_carrier_id not in new_ids:
        session.body_carrier_id = None
        session.carried_body_id = None

    lock_characters_for_session(session, store)
    session.updated_at = timestamp


def lock_characters_for_session(session: SessionState, store: Store) -> None:
    timestamp = now_utc()
    for member in session.party:
        character = store.get("characters", member.character_id, Character.model_validate)
        if character is None:
            continue
        character.active_session_id = session.id
        character.updated_at = timestamp
        store.save("characters", character)


def unlock_characters_for_session(session: SessionState, store: Store) -> None:
    timestamp = now_utc()
    for member in session.party:
        character = store.get("characters", member.character_id, Character.model_validate)
        if character is None:
            continue
        if character.active_session_id == session.id:
            character.active_session_id = None
            character.updated_at = timestamp
            store.save("characters", character)


def character_busy_session_id(character: Character, store: Store) -> str | None:
    session_id = character.active_session_id
    if not session_id:
        return None
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None or session.mode == "complete":
        return None
    return session_id


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
        character.minor_encounters_cleared = session.minor_encounters_defeated
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
