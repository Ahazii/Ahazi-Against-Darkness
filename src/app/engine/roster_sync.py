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
        "enchanted weapon",
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
        if status.lower().startswith("prep:"):
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
    return session.camped_outside


def _recovery_character_ids(session: SessionState) -> set[str]:
    ids: set[str] = set(session.fallen_outside_character_ids or [])
    if session.carried_body_id:
        ids.add(session.carried_body_id)
    for tile in session.map_state.tiles:
        ids.update(tile.fallen_character_ids or [])
    return ids


def replace_session_party(
    session: SessionState,
    character_ids: list[str],
    store: Store,
    *,
    member_state,
) -> None:
    if not session_allows_party_edit(session):
        raise ValueError("Party changes are only allowed while camped outside.")
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
    recovery_ids = _recovery_character_ids(session)

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

    preserved_recovery: list = []
    for character_id in sorted((old_ids - new_ids) & recovery_ids):
        member = old_by_id[character_id].model_copy(deep=True)
        member.marching_order = len(new_party) + len(preserved_recovery) + 1
        preserved_recovery.append(member)

    for character_id in old_ids - new_ids:
        if character_id in recovery_ids:
            continue
        character = store.get("characters", character_id, Character.model_validate)
        if character is None:
            continue
        if character.active_session_id == session.id:
            character.active_session_id = None
            character.updated_at = timestamp
            store.save("characters", character)

    session.party = new_party + preserved_recovery
    party_member_ids = {member.character_id for member in session.party}
    if session.body_carrier_id and session.body_carrier_id not in new_ids:
        session.carried_body_id = None
        session.body_carrier_id = None
    if session.carried_body_id and session.carried_body_id not in party_member_ids:
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


def reconcile_stale_character_locks(store: Store) -> int:
    """Clear active_session_id when the linked session is missing or finished."""
    cleared = 0
    timestamp = now_utc()
    for character in store.list("characters", Character.model_validate):
        session_id = character.active_session_id
        if not session_id:
            continue
        session = store.get("sessions", session_id, SessionState.model_validate)
        if session is not None and session.mode != "complete":
            continue
        character.active_session_id = None
        character.updated_at = timestamp
        store.save("characters", character)
        cleared += 1
    return cleared


def sync_party_members_to_roster(
    session: SessionState,
    store: Store,
    character_ids: set[str],
) -> None:
    """Mirror in-dungeon inventory/gold changes onto locked roster records."""
    if not character_ids:
        return
    timestamp = now_utc()
    for member in session.party:
        if member.character_id not in character_ids:
            continue
        character = store.get("characters", member.character_id, Character.model_validate)
        if character is None:
            continue
        character.gold = member.gold + member.bank_gold
        character.inventory = list(member.inventory)
        character.item_containers = [container.model_copy(deep=True) for container in member.item_containers]
        character.class_traits = list(member.class_traits)
        character.default_melee_weapon = member.default_melee_weapon
        character.default_melee_weapon_secondary = member.default_melee_weapon_secondary
        character.default_missile_weapon = member.default_missile_weapon
        character.updated_at = timestamp
        store.save("characters", character)


def sync_party_states_to_roster(session: SessionState, store: Store) -> None:
    """Expose persistent in-adventure conditions on the locked home roster."""
    timestamp = now_utc()
    for member in session.party:
        character = store.get("characters", member.character_id, Character.model_validate)
        if character is None:
            continue
        character.statuses = roster_statuses(member.statuses)
        character.madness = member.madness
        character.updated_at = timestamp
        store.save("characters", character)


def persist_session_to_roster(session: SessionState, store: Store) -> list[str]:
    timestamp = now_utc()
    notes: list[str] = []
    member_clue_total = sum(max(0, member.clues) for member in session.party)
    if session.clues_found > member_clue_total and session.party:
        clue_holder = next(
            (member for member in session.party if member.current_life > 0),
            session.party[0],
        )
        clue_holder.clues += session.clues_found - member_clue_total
    else:
        session.clues_found = member_clue_total
    secret_diet_ids = set(session.secret_diet_character_ids or [])
    for member in session.party:
        character = store.get("characters", member.character_id, Character.model_validate)
        if character is None:
            continue
        max_life = member.max_life - (1 if member.character_id in secret_diet_ids else 0)
        max_life = max(1, max_life)
        current_life = min(member.current_life, max_life)
        character.level = member.level
        character.xp = roster_xp(session, member.xp)
        character.gold = member.gold + member.bank_gold
        character.current_life = current_life
        character.max_life = max_life
        character.attack_bonus = member.attack_bonus
        character.defense_bonus = member.defense_bonus
        character.save_bonus = member.save_bonus
        character.inventory = list(member.inventory)
        character.item_containers = [container.model_copy(deep=True) for container in member.item_containers]
        temporary_spells = list(session.secret_temporary_spells.get(member.character_id, []))
        persisted_spells = list(member.spells)
        for spell in temporary_spells:
            try:
                persisted_spells.remove(spell)
            except ValueError:
                continue
        character.spells = persisted_spells
        character.abilities = list(member.abilities)
        character.class_traits = list(member.class_traits)
        character.secrets = list(member.secrets)
        character.statuses = roster_statuses(member.statuses)
        character.madness = member.madness
        character.default_melee_weapon = member.default_melee_weapon
        character.default_melee_weapon_secondary = member.default_melee_weapon_secondary
        character.default_missile_weapon = member.default_missile_weapon
        character.clues = max(0, member.clues)
        character.minor_encounters_cleared = session.minor_encounters_defeated
        character.expert_trained = member.expert_trained
        character.heroic_trained = member.heroic_trained
        character.legendary_trained = member.legendary_trained
        character.epic_trained = member.epic_trained
        character.learned_expert_skills = list(member.learned_expert_skills)
        character.learned_heroic_skills = list(member.learned_heroic_skills)
        character.learned_legendary_skills = list(member.learned_legendary_skills)
        character.expert_skill_targets = dict(member.expert_skill_targets or {})
        character.companion_kind = member.companion_kind
        character.milestones = member.milestones.model_copy(deep=True)
        character.updated_at = timestamp
        store.save("characters", character)
        if member.current_life > 0:
            clue_note = f", {character.clues} Clue(s)" if character.clues else ""
            notes.append(
                f"{member.name}: Level {character.level}, {character.gold} gp, "
                f"{character.current_life}/{character.max_life} Life{clue_note} saved to roster."
            )
        else:
            notes.append(
                f"{member.name}: fallen ({character.current_life}/{character.max_life} Life) saved to roster."
            )
    return notes
