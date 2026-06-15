from __future__ import annotations

from ..schemas import DetachedGroupState, EnemyState, PartyMemberState, SessionState
from .combat import CombatRound, resolve_combat_round
from .dice import roll_d6

# Stealth modifiers by class (base formula applied to member.level).
# "full" = +L, "half" = +floor(L/2), missing = 0 (may gain +half via the EE Stealth Training flag).
_STEALTH_CLASS_FORMULA: dict[str, str] = {
    "rogue": "full",
    "assassin": "full",
    "halfling": "full",
    "elf": "half",
    "cleric": "half",
    "ranger": "half",
    "swashbuckler": "half",
}


def stealth_modifier(member: PartyMemberState, session: SessionState | None = None, tile=None) -> int:  # noqa: ARG001
    """Return the total Stealth Save modifier for a party member.

    Base class bonuses (EE p.105 / class descriptions):
    - Rogue, Assassin, Halfling: +L
    - Ranger: +L outdoors, +½L indoors
    - Elf, Cleric, Swashbuckler: +½L (floor)
    - All others: 0, or +½L with the EE Stealth Training flag (L5+).
    """
    class_id = member.class_id.lower()
    if class_id == "ranger":
        try:
            from .terrain import tile_is_outdoors

            if tile is not None and tile_is_outdoors(tile.terrain):
                return member.level
        except Exception:
            pass
    formula = _STEALTH_CLASS_FORMULA.get(member.class_id.lower(), "none")
    level = member.level
    if formula == "full":
        return level
    if formula == "half":
        return level // 2
    # No inherent stealth — check for the separated EE Stealth Training flag.
    if "stealth_training" in (member.learned_expert_skills or []):
        return level // 2
    return 0


def tile_by_id(session: SessionState, tile_id: str):
    return next((tile for tile in session.map_state.tiles if tile.id == tile_id), None)


def active_tile_id(session: SessionState) -> str:
    """Return the tile ID of the active navigation group.

    Returns ``active_group_tile_id`` if it corresponds to a valid detached group
    with at least one living hero; otherwise falls back to ``current_tile_id``.
    """
    atid = session.active_group_tile_id
    if not atid or atid == session.map_state.current_tile_id:
        return session.map_state.current_tile_id
    living_ids = {m.character_id for m in session.party if m.current_life > 0}
    for group in session.detached_groups:
        if group.tile_id == atid and group.reason == "call_of_the_wild":
            session.active_group_tile_id = None
            return session.map_state.current_tile_id
        if group.tile_id == atid and any(cid in living_ids for cid in group.character_ids):
            return atid
    # Group dissolved or no living heroes — clear stale field and fall back.
    session.active_group_tile_id = None
    return session.map_state.current_tile_id


def is_active_detached(session: SessionState) -> bool:
    """True when a detached group (not the main party) is the active navigation group."""
    return active_tile_id(session) != session.map_state.current_tile_id


def call_of_wild_unavailable_ids(session: SessionState) -> set[str]:
    return {
        character_id
        for character_id, turns in (session.druid_call_of_wild_turns or {}).items()
        if int(turns) > 0
    }


def set_active_group(session: SessionState, tile_id: str | None) -> list[str]:
    """Switch navigation focus to the detached group at *tile_id*, or back to main if None.

    Validates that the target tile has a living detached group and that the session
    is in exploration mode (not mid-combat).
    """
    if tile_id is None or tile_id == session.map_state.current_tile_id:
        session.active_group_tile_id = None
        return ["Main group is now active for navigation."]
    if session.mode != "exploration":
        return ["Switch the active group during exploration only."]
    group = next((g for g in session.detached_groups if g.tile_id == tile_id), None)
    if group is None:
        return ["No detached group at that location."]
    if group.reason == "call_of_the_wild":
        return ["A druid answering Call of the Wild cannot be used for navigation until they return."]
    living_ids = {m.character_id for m in session.party if m.current_life > 0}
    if not any(cid in living_ids for cid in group.character_ids):
        return ["No living heroes in that detached group."]
    tile = tile_by_id(session, tile_id)
    session.active_group_tile_id = tile_id
    tile_name = tile.title if tile else tile_id
    return [f"Detached group at {tile_name} is now active. Use Exits or the door panel to move them."]


def detached_elsewhere(session: SessionState, tile_id: str) -> set[str]:
    ids: set[str] = set()
    for group in session.detached_groups:
        if group.tile_id != tile_id:
            ids.update(group.character_ids)
    return ids


def detached_on_tile(session: SessionState, tile_id: str) -> set[str]:
    ids: set[str] = set()
    for group in session.detached_groups:
        if group.tile_id == tile_id:
            ids.update(group.character_ids)
    return ids


def present_party(session: SessionState, tile_id: str | None = None) -> list[PartyMemberState]:
    """Heroes with the main marching group (excludes detached guards on this tile)."""
    active_tile = tile_id or session.map_state.current_tile_id
    blocked = detached_elsewhere(session, active_tile) | detached_on_tile(session, active_tile) | call_of_wild_unavailable_ids(session)
    return [member for member in session.party if member.character_id not in blocked and member.current_life > 0]


def combat_party(session: SessionState, tile_id: str | None = None) -> list[PartyMemberState]:
    """Living heroes physically on a tile who may fight there."""
    active_tile = tile_id or session.map_state.current_tile_id
    on_tile_ids: set[str] = set()
    for group in session.detached_groups:
        if group.tile_id == active_tile and group.reason != "call_of_the_wild":
            on_tile_ids.update(group.character_ids)
    if session.map_state.current_tile_id == active_tile:
        on_tile_ids.update(member.character_id for member in present_party(session, active_tile))
    blocked = detached_elsewhere(session, active_tile) | call_of_wild_unavailable_ids(session)
    return [
        member
        for member in session.party
        if member.character_id in on_tile_ids
        and member.character_id not in blocked
        and member.current_life > 0
    ]


def detached_groups_on_tile(session: SessionState, tile_id: str) -> list[DetachedGroupState]:
    return [group for group in session.detached_groups if group.tile_id == tile_id]


def is_detached_on_tile(session: SessionState, character_id: str, tile_id: str) -> bool:
    for group in session.detached_groups:
        if group.tile_id == tile_id and character_id in group.character_ids:
            return True
    return False


def detach_heroes(
    session: SessionState,
    character_ids: list[str],
    *,
    reason: str = "guard",
) -> list[str]:
    tile = tile_by_id(session, session.map_state.current_tile_id)
    if tile is None:
        return ["No active map element."]
    if session.mode != "exploration":
        return ["Split the party during exploration only."]
    living = {member.character_id for member in session.party if member.current_life > 0}
    chosen = [cid for cid in character_ids if cid in living]
    if not chosen:
        return ["Choose living heroes to leave behind."]
    main_ids = {member.character_id for member in present_party(session, tile.id)}
    if len(main_ids) - len(set(chosen) & main_ids) < 1:
        return ["At least one hero must stay with the main group."]
    for cid in chosen:
        if cid not in main_ids:
            continue
        session.detached_groups = [
            group
            for group in session.detached_groups
            if cid not in group.character_ids or group.tile_id != tile.id
        ]
    existing = next((group for group in session.detached_groups if group.tile_id == tile.id), None)
    if existing is None:
        session.detached_groups.append(
            DetachedGroupState(tile_id=tile.id, character_ids=list(dict.fromkeys(chosen)), reason=reason)
        )
    else:
        merged = list(dict.fromkeys([*existing.character_ids, *chosen]))
        existing.character_ids = merged
        existing.reason = reason or existing.reason
    names = [
        next(member.name for member in session.party if member.character_id == cid)
        for cid in chosen
    ]
    return [f"{', '.join(names)} remain at {tile.title} ({reason})."]


def reattach_heroes(session: SessionState, character_ids: list[str] | None = None) -> list[str]:
    tile = tile_by_id(session, session.map_state.current_tile_id)
    if tile is None:
        return ["No active map element."]
    if session.mode != "exploration":
        return ["Regroup during exploration."]
    target_ids = set(character_ids or [])
    rejoined: list[str] = []
    kept: list[DetachedGroupState] = []
    for group in session.detached_groups:
        if group.tile_id != tile.id:
            kept.append(group)
            continue
        if group.reason == "call_of_the_wild":
            blocked = [
                cid
                for cid in group.character_ids
                if int((session.druid_call_of_wild_turns or {}).get(cid, 0)) > 0
            ]
            if blocked:
                kept.append(group)
                names = [
                    next((member.name for member in session.party if member.character_id == cid), cid)
                    for cid in blocked
                ]
                return [f"{', '.join(names)} must finish Call of the Wild before rejoining."]
        if not target_ids:
            rejoined.extend(group.character_ids)
            continue
        staying = [cid for cid in group.character_ids if cid not in target_ids]
        joining = [cid for cid in group.character_ids if cid in target_ids]
        rejoined.extend(joining)
        if staying:
            kept.append(DetachedGroupState(tile_id=group.tile_id, character_ids=staying, reason=group.reason))
    session.detached_groups = kept
    if not rejoined:
        return ["No detached heroes are here to regroup."]
    names = [
        next(member.name for member in session.party if member.character_id == cid)
        for cid in rejoined
    ]
    return [f"{', '.join(names)} rejoin the main group at {tile.title}."]


def scout_ahead(session: SessionState, scout_id: str) -> list[str]:
    """Mark a hero as ready to scout.  The actual scout move is performed by
    the engine's ``_do_scout_move`` when the caller also supplies an *exit_id*
    (dispatched via the ``scout_ahead`` action in random_dungeon.py).
    When called without an exit_id this simply confirms the hero is valid and
    tells the player to choose an exit via the UI.
    """
    member = next((item for item in session.party if item.character_id == scout_id), None)
    if member is None or member.current_life <= 0:
        return ["Choose a living hero to scout."]
    if session.mode != "exploration":
        return ["Scout ahead during exploration only."]
    return [f"{member.name} is ready to scout. Choose an exit to send them through."]


def apply_scout_lag_on_move(session: SessionState, origin_tile_id: str) -> list[str]:  # noqa: ARG001
    """Legacy stub — clears a stale flag from old saved sessions.  The
    old 'lag behind' scout behaviour has been replaced by the proper
    stealth-save scout-ahead mechanic.
    """
    if session.scout_lag_character_id:
        session.scout_lag_character_id = None
    return []


def mixed_encounter(enemies: list[EnemyState]) -> bool:
    living = [enemy for enemy in enemies if enemy.life > 0]
    has_major = any(enemy.category in {"boss", "weird", "major"} for enemy in living)
    has_minor = any(enemy.category in {"minions", "vermin"} for enemy in living)
    return has_major and has_minor


def split_party_ranks(party: list[PartyMemberState]) -> tuple[list[PartyMemberState], list[PartyMemberState]]:
    living = [member for member in sorted(party, key=lambda item: item.marching_order) if member.current_life > 0]
    if len(living) <= 2:
        mid = max(1, len(living) // 2)
        return living[:mid], living[mid:]
    front = [member for member in living if member.marching_order <= 2]
    rear = [member for member in living if member.marching_order >= 3]
    if not front:
        front = living[:2]
    if not rear:
        rear = [member for member in living if member not in front]
    return front, rear


def split_enemy_groups(enemies: list[EnemyState]) -> tuple[list[EnemyState], list[EnemyState]]:
    living = [enemy for enemy in enemies if enemy.life > 0]
    major = [enemy for enemy in living if enemy.category in {"boss", "weird", "major"}]
    minor = [enemy for enemy in living if enemy.category in {"minions", "vermin"}]
    return major, minor


def resolve_simultaneous_combat_round(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool,
    explain_math: bool,
    initial_minor_count: int | None,
    context,
    party_surprised: bool,
    party_attacked_immediately: bool,
    foes_strike_first: bool,
    subdual: bool,
    encounter_round: int,
    missile_used: set[str],
    attack_targets: dict[str, str] | None,
    attack_secondary_targets: dict[str, str] | None,
) -> CombatRound:
    front, rear = split_party_ranks(party)
    major_foes, minor_foes = split_enemy_groups(enemies)
    combined_log: list[str] = ["Simultaneous fight: front rank vs major foes, rear rank vs minions."]
    merged_missile = set(missile_used)
    morale_failed = False
    for label, fighters, foe_group in (
        ("Front rank vs major foes", front, major_foes),
        ("Rear rank vs minions", rear, minor_foes),
    ):
        if not fighters or not foe_group:
            continue
        combined_log.append(label + ".")
        round_result = resolve_combat_round(
            fighters,
            foe_group,
            show_rolls=show_rolls,
            explain_math=explain_math,
            initial_minor_count=initial_minor_count,
            context=context,
            party_surprised=party_surprised,
            party_attacked_immediately=party_attacked_immediately,
            foes_strike_first=foes_strike_first,
            subdual=subdual,
            encounter_round=encounter_round,
            missile_used=merged_missile,
            attack_targets=attack_targets,
            attack_secondary_targets=attack_secondary_targets,
        )
        combined_log.extend(round_result.log)
        merged_missile |= set(round_result.missile_used or [])
        morale_failed = morale_failed or round_result.morale_failed
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return CombatRound(
        party=party,
        enemies=enemies,
        log=combined_log,
        combat_over=combat_over,
        morale_failed=morale_failed,
        missile_used=merged_missile,
    )


def wandering_check_detached_groups(
    session: SessionState,
    *,
    show_rolls: bool,
    exclude_tile_id: str | None = None,
) -> tuple[list[str], list[str]]:
    logs: list[str] = []
    triggered: list[str] = []
    for group in session.detached_groups:
        if group.reason == "call_of_the_wild":
            continue
        if exclude_tile_id and group.tile_id == exclude_tile_id:
            continue
        tile = tile_by_id(session, group.tile_id)
        if tile is None:
            continue
        if any(enemy.life > 0 for enemy in tile.enemies):
            continue
        roll = roll_d6()
        if show_rolls:
            title = tile.title or tile.tile_key
            logs.append(f"Detached group wandering roll at {title}: d6 = {roll}.")
        if roll != 1:
            continue
        triggered.append(group.tile_id)
        logs.append(
            f"Wandering Monsters threaten the group left at {tile.title} — fight when the party regroups there."
        )
    return triggered, logs
