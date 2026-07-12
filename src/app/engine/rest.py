from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Literal

from ..schemas import ExitState, PartyMemberState, SessionState, TileState
from .dice import roll_d6
from .class_abilities import (
    apply_nourishing_meal,
    member_has_recoverable_class_ability,
    recover_acrobat_tricks_on_rest,
    recover_class_ability,
)
from .heroic_skill_effects import apply_copy_grimoire_on_rest, apply_heroes_rest_bonus, apply_heros_banquet_bonus
from .hunger import feed_all_living_heroes
from .spells import HEALING_PRAYER_USES_PER_ADVENTURE, REPEATABLE_PRAYERS, normalize_spell_name

RestChoice = Literal["life", "ability"]
NAIL_BAG_NAMES = ("bag of nails", "bags of nails")
NAIL_BAG_ITEM = "Bag of nails"


@dataclass
class RestResolution:
    """Resolved rest state before the engine synchronizes doors or spawns an ambush."""

    completed: bool
    log: list[str]
    nailed_doors: list[ExitState]
    wandering_triggered: bool = False
    wandering_door: ExitState | None = None


def reset_between_foray_resources(session: SessionState) -> None:
    """Reset per-foray resources after the party reaches camp outside a dungeon."""
    session.missile_used_character_ids = []
    session.spell_used_character_ids = []
    session.alchemist_potion_bought = []
    session.alchemist_poison_bought = []
    session.potion_used_character_ids = []
    session.bandage_used_character_ids = []
    session.herbal_tonic_used_character_ids = []
    session.expended_spells = {}
    session.healing_prayer_uses = {}
    session.rest_used = False
    session.rest_available = False
    session.rest_block_reason = ""
    session.rage_uses_spent = {}
    session.luck_points_spent = {}
    session.panache_points = {}
    session.paladin_prayer_spent = {}
    session.nourishing_meal_used = False
    session.pending_save_reroll = None
    session.acrobat_tricks_spent = {}
    session.gnome_gadgets_spent = {}
    session.mushroom_spore_uses = {}
    session.foe_level_penalties = {}
    session.assassin_hidden_id = None
    session.assassin_mark_enemy_id = None
    session.gnome_smokescreen_ready = False
    session.skip_parting_flee = False
    session.puffball_flee = False
    session.acrobat_skip_attack = {}
    session.prisoner_chain_skip_attack = {}
    session.gladiator_counter_pending = {}
    session.gladiator_counter_used = []
    from .swashbuckler_traits import reset_swashbuckler_combat_flags

    reset_swashbuckler_combat_flags(session)
    session.swashbuckler_lucky_hat_used = []
    session.swashbuckler_daring_escape_used = []
    session.swashbuckler_blade_dance_used = []
    session.swashbuckler_blade_dance_bonus = {}
    session.swashbuckler_blade_dance_attack_spent = []
    session.swashbuckler_daring_escape_bonus = {}
    session.evasion_character_ids = []
    session.expert_encounter_spent = {}
    session.expert_protective_incense_target = None
    session.expert_knife_thrown = {}
    session.pending_treasure_reroll_tile_id = None
    session.pending_hidden_complication_reroll_tile_id = None
    session.pending_search_reroll_tile_id = None
    session.pending_pole_search_reroll_tile_id = None
    session.pending_search_reward_tile_id = None
    session.pending_tile_content_choice_tile_id = None
    session.firearm_broken = {}
    session.firearm_reload_turns = {}
    session.crossbow_needs_reload = []
    session.pole_carrier_id = None
    session.divine_smite_used = []
    session.army_of_dolls_deployed = []
    session.sacrifice_shield_used = []
    session.hyphae_used = []
    session.kukla_doll_active = []
    session.graceful_save_reroll_id = None
    session.hyphae_search_bonus_id = None
    session.paladin_steed_active_id = None
    session.continual_light_owner_id = None
    session.heroes_rest_used = False
    session.heroic_courage_used = []
    session.legendary_courage_used = []
    session.training_focus_bonus = {}
    session.aggressive_stance_penalty = []
    session.heroic_carnage_bonus = {}
    session.heros_banquet_used = False
    session.alter_weather_active = False
    session.forest_pathway_active = False
    session.glamour_mask_character_id = None
    session.glamour_mask_reroll_available = False
    session.song_of_elidra_used = False
    session.mass_blessing_used = False
    session.mass_blessing_active_round = -1
    session.protected_by_fate_used = []
    session.yogic_preservation_used = []
    session.restore_mental_capacity_used = False
    session.copy_grimoire_used = []
    session.ward_of_protection_targets = {}
    for member in session.party:
        member.statuses = [
            status for status in member.statuses if status.strip().lower() != "continual light"
        ]
    if session.druid_companion_life > 0 and session.druid_companion_max_life > 0:
        session.druid_companion_life = session.druid_companion_max_life


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
    from .forsaken_depths_river import fd_tears_river_blocks_rest

    if fd_tears_river_blocks_rest(session):
        return False, "Rest is not possible on the River of Tears (FD p.32)."
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


def recover_life(member: PartyMemberState, *, session: SessionState | None = None, tile: TileState | None = None) -> str | None:
    if member.current_life <= 0:
        return None
    if member.current_life >= member.max_life:
        return None
    if session is not None and tile is not None:
        from .forsaken_depths_citadel import fd_citadel_of_dead_blocks_healing

        dead_block = fd_citadel_of_dead_blocks_healing(session, tile, source="rest")
        if dead_block:
            return dead_block
    member.current_life += 1
    if session is not None:
        from .forsaken_depths_river import fd_death_river_healing_multiplier

        multiplier = fd_death_river_healing_multiplier(session)
        if multiplier < 1.0 and member.current_life > 1:
            member.current_life = max(member.current_life - 1, 1)
            return (
                f"{member.name} recovers 1 Life on the River of Death (half healing — "
                f"{member.current_life}/{member.max_life}) (FD p.32)."
            )
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
    *,
    tile: TileState | None = None,
) -> list[str]:
    log: list[str] = []
    if tile is None:
        tile = next(
            (entry for entry in session.map_state.tiles if entry.id == session.map_state.current_tile_id),
            None,
        )
    for member in party:
        if member.current_life <= 0:
            continue
        choice = choices.get(member.character_id, "life")
        if choice == "ability":
            message = recover_ability(session, member)
            if message is None:
                message = recover_life(member, session=session, tile=tile)
                if message is None:
                    log.append(f"{member.name} had nothing to recover.")
                    continue
                log.append(f"{member.name} had no spent ability; recovered 1 Life instead.")
            log.append(message)
            continue
        message = recover_life(member, session=session, tile=tile)
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


def resolve_rest(
    session: SessionState,
    tile: TileState,
    *,
    nail_doors: bool = False,
    rest_choices: dict[str, str] | None = None,
    show_rolls: bool = True,
    nourishing_meal: bool = False,
    nourishing_meal_eaters: list[str] | None = None,
    everyone_eats: bool = False,
) -> RestResolution:
    """Apply a legal rest through its wandering-monster check, without engine-specific combat work."""
    living = [member for member in session.party if member.current_life > 0]
    choices = dict(rest_choices or {})
    for member in living:
        if member.character_id in choices:
            continue
        if member.current_life < member.max_life:
            choices[member.character_id] = "life"
        elif member_has_recoverable_ability(session, member):
            choices[member.character_id] = "ability"
        else:
            choices[member.character_id] = "life"

    ok, reason = validate_rest_request(session, tile, nail_doors=nail_doors, choices=choices)
    if not ok:
        return RestResolution(False, [reason], [])

    doors = nailable_doors(tile)
    log = ["The party rests (once per adventure, rulebook p.114)."]
    nailed_doors: list[ExitState] = []
    if nail_doors:
        if not consume_nail_bags(session.party, len(doors)):
            return RestResolution(False, log + ["Not enough bags of nails to seal the doors."], [])
        for exit_state in doors:
            exit_state.nailed_shut = True
            exit_state.door_open = False
            exit_state.status = "blocked"
        nailed_doors = doors
        log.append(f"The party nails {len(doors)} door(s) shut ({len(doors)} bag(s) of nails used).")
    else:
        log.append("The party does not nail the doors shut.")

    session.rest_used = True
    session.alter_weather_active = False
    session.forest_pathway_active = False
    session.glamour_mask_character_id = None
    session.glamour_mask_reroll_available = False
    log.extend(apply_rest_recovery(session, session.party, choices, tile=tile))
    for member in living:
        trick_note = recover_acrobat_tricks_on_rest(session, member)
        if trick_note:
            log.append(trick_note)
    if everyone_eats:
        log.extend(feed_all_living_heroes(session, session.party))
    if nourishing_meal:
        eaters = nourishing_meal_eaters or [member.character_id for member in living]
        log.extend(apply_nourishing_meal(session, session.party, eaters))

    triggered, roll = wandering_roll_triggers(
        tile.cavern_feature_key,
        roll_bonus=session.next_wandering_roll_bonus,
    )
    if session.next_wandering_roll_bonus:
        if show_rolls:
            log.append(
                f"Firearm noise increases wandering risk (+{session.next_wandering_roll_bonus} on d6)."
            )
        session.next_wandering_roll_bonus = 0
    if show_rolls:
        log.append(f"Rest wandering-monster roll: d6 = {roll}.")
    if not triggered:
        log.append("The rest is undisturbed.")
        return RestResolution(True, log, nailed_doors)

    tile.wandering_ambush = False
    return RestResolution(
        True,
        log,
        nailed_doors,
        wandering_triggered=True,
        wandering_door=pick_wandering_door(doors),
    )


def pick_wandering_door(doors: list[ExitState]) -> ExitState | None:
    if not doors:
        return None
    return random.choice(doors)


def wandering_roll_triggers(cavern_feature_key: str | None = None, *, roll_bonus: int = 0) -> tuple[bool, int]:
    from .cavern_features import wandering_check_triggers

    return wandering_check_triggers(cavern_feature_key, roll_bonus=roll_bonus)
