from __future__ import annotations

import random
from typing import Literal

from ..schemas import ExitState, PartyMemberState, SessionState, TileState
from .dice import roll_d6
from .class_abilities import member_has_recoverable_class_ability, recover_acrobat_tricks_on_rest, recover_class_ability
from .heroic_skill_effects import apply_copy_grimoire_on_rest, apply_heroes_rest_bonus, apply_heros_banquet_bonus
from .spells import HEALING_PRAYER_USES_PER_ADVENTURE, REPEATABLE_PRAYERS, normalize_spell_name

RestChoice = Literal["life", "ability"]
NAIL_BAG_NAMES = ("bag of nails", "bags of nails")
NAIL_BAG_ITEM = "Bag of nails"


def tile_is_cleared(tile: TileState) -> bool:
    return not any(enemy.life > 0 for enemy in tile.enemies)


def nailable_doors(tile: TileState) -> list[ExitState]:
    return [
        exit_state
        for exit_state in tile.exits
        if exit_state.kind == "door" and not exit_state.door_destroyed
    ]


def count_party_nail_bags(party: list[PartyMemberState]) -> int:
    total = 0
    for member in party:
        for item in member.inventory:
            if any(name in item.lower() for name in NAIL_BAG_NAMES):
                total += 1
    return total


def consume_nail_bags(party: list[PartyMemberState], count: int) -> bool:
    if count <= 0:
        return True
    remaining = count
    for member in party:
        kept: list[str] = []
        for item in member.inventory:
            if remaining > 0 and any(name in item.lower() for name in NAIL_BAG_NAMES):
                remaining -= 1
                continue
            kept.append(item)
        member.inventory = kept
        if remaining <= 0:
            break
    return remaining == 0


def _neighbor_tiles(session: SessionState, tile: TileState) -> list[TileState]:
    tiles_by_id = {entry.id: entry for entry in session.map_state.tiles}
    neighbors: list[TileState] = []
    for exit_state in tile.exits:
        if not exit_state.destination_tile_id:
            continue
        neighbor = tiles_by_id.get(exit_state.destination_tile_id)
        if neighbor is not None:
            neighbors.append(neighbor)
    return neighbors


def rest_eligibility(session: SessionState, tile: TileState) -> tuple[bool, str]:
    if session.mode != "exploration":
        return False, "The party cannot rest during combat."
    if session.rest_used:
        return False, "The party has already rested once this adventure (rulebook p.114)."
    if tile.tile_type != "room":
        return False, "Rest requires a cleared room, not a corridor."
    if not tile_is_cleared(tile):
        return False, "Rest requires a room cleared of foes."
    neighbors = _neighbor_tiles(session, tile)
    if not neighbors:
        return False, "Rest requires adjacent explored map elements; none are connected yet."
    uncleared = [neighbor.title for neighbor in neighbors if not tile_is_cleared(neighbor)]
    if uncleared:
        return False, "Adjacent rooms or corridors must also be cleared before resting."
    doors = nailable_doors(tile)
    if not doors:
        return False, "Rest requires doors that can be nailed shut (cavern openings do not qualify)."
    return True, ""


def member_has_recoverable_ability(session: SessionState, member: PartyMemberState) -> bool:
    if member.current_life <= 0:
        return False
    character_id = member.character_id
    expended = session.expended_spells.get(character_id, [])
    if expended:
        return True
    prayer_uses = session.healing_prayer_uses.get(character_id, 0)
    if prayer_uses > 0 and any(
        normalize_spell_name(spell) in REPEATABLE_PRAYERS for spell in member.spells
    ):
        return True
    return member_has_recoverable_class_ability(session, member)


def recover_life(member: PartyMemberState) -> str | None:
    if member.current_life <= 0:
        return None
    if member.current_life >= member.max_life:
        return None
    member.current_life += 1
    return f"{member.name} recovers 1 Life ({member.current_life}/{member.max_life})."


def recover_ability(session: SessionState, member: PartyMemberState) -> str | None:
    if member.current_life <= 0:
        return None
    character_id = member.character_id
    expended = session.expended_spells.setdefault(character_id, [])
    if expended:
        restored = expended.pop()
        return f"{member.name} recovers spent {restored}."
    prayer_uses = session.healing_prayer_uses.get(character_id, 0)
    if prayer_uses > 0:
        session.healing_prayer_uses[character_id] = prayer_uses - 1
        remaining = HEALING_PRAYER_USES_PER_ADVENTURE - (prayer_uses - 1)
        return f"{member.name} recovers 1 Healing prayer use ({remaining} remaining)."
    message = recover_class_ability(session, member)
    if message:
        return message
    return None


def apply_rest_recovery(
    session: SessionState,
    party: list[PartyMemberState],
    choices: dict[str, RestChoice],
) -> list[str]:
    log: list[str] = []
    for member in party:
        if member.current_life <= 0:
            continue
        choice = choices.get(member.character_id, "life")
        if choice == "ability":
            message = recover_ability(session, member)
            if message is None:
                message = recover_life(member)
                if message is None:
                    log.append(f"{member.name} had nothing to recover.")
                    continue
                log.append(f"{member.name} had no spent ability; recovered 1 Life instead.")
            log.append(message)
            continue
        message = recover_life(member)
        if message is None:
            if member_has_recoverable_ability(session, member):
                message = recover_ability(session, member)
                if message:
                    log.append(f"{member.name} is at full Life; recovered a spent ability instead.")
                    log.append(message)
                    continue
            log.append(f"{member.name} is at full Life with no spent abilities to recover.")
        else:
            log.append(message)
    log.extend(apply_heroes_rest_bonus(session, party))
    log.extend(apply_heros_banquet_bonus(session, party))
    log.extend(apply_copy_grimoire_on_rest(session, party))
    return log


def acrobat_trick_recovery_note(session: SessionState, member: PartyMemberState) -> str | None:
    return recover_acrobat_tricks_on_rest(session, member)


def validate_rest_request(
    session: SessionState,
    tile: TileState,
    *,
    nail_doors: bool,
    choices: dict[str, RestChoice],
) -> tuple[bool, str]:
    ok, reason = rest_eligibility(session, tile)
    if not ok:
        return False, reason
    doors = nailable_doors(tile)
    if nail_doors:
        needed = len(doors)
        if count_party_nail_bags(session.party) < needed:
            return False, f"Nailing doors shut requires {needed} bag(s) of nails (4gp each)."
    living = [member for member in session.party if member.current_life > 0]
    if not living:
        return False, "No living heroes can rest."
    for member in living:
        if member.character_id not in choices:
            return False, f"Choose Life or ability recovery for {member.name}."
        if choices[member.character_id] not in {"life", "ability"}:
            return False, f"Invalid rest choice for {member.name}."
    return True, ""


def pick_wandering_door(doors: list[ExitState]) -> ExitState | None:
    if not doors:
        return None
    return random.choice(doors)


def wandering_roll_triggers(cavern_feature_key: str | None = None, *, roll_bonus: int = 0) -> tuple[bool, int]:
    from .cavern_features import wandering_check_triggers

    return wandering_check_triggers(cavern_feature_key, roll_bonus=roll_bonus)
