from __future__ import annotations

from dataclasses import dataclass
import inspect
import random
import re
from pathlib import Path
from uuid import uuid4

from ..db import now_utc
from ..rules.repository import RulesRepository
from ..schemas import (
    ActiveQuestState,
    CapturedEquipmentState,
    DealWithFoeEntry,
    DetachedGroupState,
    EnemyState,
    ExitState,
    MapState,
    PartyMemberState,
    PendingEchoSpellState,
    PendingFallenTransferState,
    PendingMadnessChoiceState,
    SessionState,
    TileDefinition,
    TileState,
)
from .combat import CombatContext, CombatRound, apply_enemy_damage, attack_damage, attack_hits, foe_display_labels, resolve_combat_round, resolve_flee, resolve_flee_strike, resolve_withdraw
from .combat_summary import summarize_combat_log
from .subdual import apply_major_foe_level_drop
from .fiendish_foes import (
    fiendish_foes_session_label,
    normalize_fiendish_foes_enabled,
    party_fiendish_foes_eligible,
    resolve_monster_table_key,
    resolve_use_fiendish_foes_table,
    template_never_wandering,
)
from .death_recovery import (
    accept_fallen_loss,
    attempt_resurrection,
    deliver_carried_body_outside,
    drop_carried_body,
    start_carrying_body,
)
from .equipment_effects import enforce_single_pole_carrier, pole_carrier
from .firearm import gnome_repair_firearm
from .gem_items import remove_inventory_item
from .hunger import eat_food_ration, feed_all_living_heroes, feed_hungry_heroes
from .combat_modifiers import consume_clarity_bonus
from .consumables import (
    is_acid_vial,
    is_holy_water,
    is_lantern_oil,
    is_mushroom,
    is_undead_foe,
    mushroom_kind,
    mushroom_resale_value,
    mushroom_standard_buy_price,
    puffball_parting_foe,
    splash_lantern_oil,
    throw_acid_vial,
    throw_holy_water,
    use_mushroom,
)
from .madness import (
    apply_envenom_weapon,
    apply_madness_gain,
    heal_madness_on_dungeon_exit,
    is_paranoid,
    resolve_madness_choice,
)
from .druid_companion import (
    companion_attack_log,
    foes_strike_companion,
    maybe_summon_on_wilderness_entry,
)
from .roster_sync import initial_xp_tally
from .tag_compat import is_generated_tag_manifest
from .split_party import (
    active_tile_id,
    apply_scout_lag_on_move,
    detach_heroes,
    is_active_detached,
    mixed_encounter,
    combat_party,
    present_party,
    reattach_heroes,
    resolve_simultaneous_combat_round,
    scout_ahead,
    set_active_group,
    stealth_modifier,
    wandering_check_detached_groups,
)
from .weapons import _parse_weapon_item, infer_default_weapons, prune_weapon_defaults, select_melee_weapon, select_missile_weapon, set_weapon_default
from .experience import (
    CLUES_FOR_SECRET_XP,
    MINOR_ENCOUNTERS_FOR_XP,
    advancement_succeeds,
    apply_final_boss_treasure_bonus,
    apply_level_up,
    assign_level_up_spell,
    advancement_roll_explain,
    campaign_mode_label,
    defeated_mixed_major_minor,
    dungeon_has_final_boss,
    force_final_boss_designation,
    is_minor_encounter,
    level_up_gate_reason,
    major_foes_defeated,
    map_elements_at_cap,
    mark_final_boss_candidate,
    normalize_unlimited_map_element_cap,
    old_school_level_cost,
    old_school_xp_for_defeated,
    perform_advancement_roll,
    potion_in_inventory,
    potion_kind,
    tier_entry_blocked_reason,
    tier_entry_requirements,
    tier_for_level,
    unlimited_map_element_cap,
    usable_potions_in_inventory,
)
from .tier_skills import (
    advancement_fork_label,
    apply_tier_skill_learn,
    available_advancement_forks,
    validate_tier_skill_choice,
)
from .expert_skill_effects import (
    adjust_reaction_roll,
    adjust_search_roll,
    expert_puzzle_bonus,
    grant_spore_doses_after_combat,
    has_skill,
    encounter_spent,
    mark_encounter_spent,
    member_carries_shield,
    prepare_adventure_expert_items,
    rearguard_has_danger_sense,
    reset_expert_encounter,
)
from .expert_skills import apply_expert_skill_learn, eligible_expert_spells, validate_expert_skill_choice
from .inventory import (
    MAX_CARRIED_GOLD,
    can_add_item,
    bandages_in_inventory,
    can_apply_bandage,
    can_receive_bandage,
    can_use_bandage,
    distribute_gold_among,
    distribute_items_among,
    encumbrance_penalty,
    has_illusionary_servant,
    snapshot_carry_baseline,
    transfer_gold,
    transfer_inventory_item,
)
from .magic_weapons import resolve_treasure_item_list
from .gremlin_events import gremlin_protection_active, resolve_invisible_gremlins
from .special_items import (
    BERSERKER_MUSHROOM_STATUS,
    apply_enchanted_paint,
    apply_wand_cast_bonus,
    climb_from_pit,
    member_has_prayer_bead_necklace,
    consume_prayer_bead,
    consume_torch,
    consume_wand_cast_bonus,
    consume_wand_power_charges,
    eat_berserkers_mushroom,
    equip_glittering_crystal,
    flee_blocked_by_web,
    is_berserkers_mushroom,
    is_enchanted_paint,
    is_glittering_crystal,
    is_herbal_tonic,
    is_map_fragment,
    is_miners_amulet,
    is_miners_ointment,
    is_wand_of_power,
    is_wolfsbane,
    parse_wand_of_power_charges,
    resolve_special_treasure_items,
    throw_wolfsbane,
    use_herbal_tonic,
    use_miners_ointment,
)
from .foe_weapon_restrictions import template_weapon_allow_tags
from .monster_template_effects import (
    template_combat_tags,
    template_encounter_start_effects,
    template_on_hit_effects,
    template_per_turn_effects,
    template_special_attacks,
    roll_random_power_tag,
)
from .cavern_features import (
    boulder_surprise_triggers,
    echo_spell_repeats,
    template_surprise_tags,
)
from .rest import (
    apply_rest_recovery,
    consume_nail_bags,
    member_has_recoverable_ability,
    nailable_doors,
    pick_wandering_door,
    rest_eligibility,
    validate_rest_request,
    wandering_roll_triggers,
)
from .secrets import (
    SPELLCASTER_CLASSES,
    consume_secret,
    deal_entry_matches_foe,
    has_secret,
    is_chaos_fanatic,
    normalize_deal_foe_name,
    record_secret,
    secret_by_id,
    secret_label,
    set_true_name_alignment,
    true_name_alignment,
    true_name_mode_family,
)
from .reactions import (
    ReactionOutcome,
    build_reaction_outcome,
    bribe_requirements_met,
    consume_bribe_food_value,
    count_bribe_food_value,
    count_party_weapons,
    dwarf_miser_blocks_bribe,
    flee_if_outnumbered,
    apply_reaction_overlays,
    is_bribe_reaction,
    lookup_reaction_row,
    normalize_reaction_row,
    pay_bribe_cost,
    resolve_reaction_source,
)
from .quests import epic_reward_item, quest_from_row, quest_ready_to_complete
from .adventure_allowlists import major_foe_table_keys
from .adventure_runtime import (
    IMPORTED_ROOM_PREFIX,
    fire_imported_triggers,
    log_imported_departure_narrative,
    update_imported_quest_on_combat_end,
)
from .class_combat import save_modifier
from .class_abilities import (
    acrobat_distract,
    acrobat_evade,
    acrobat_graceful_move,
    acrobat_leap_out_of_harm,
    acrobat_shift_position,
    acrobat_serpent_twist,
    apply_nourishing_meal,
    count_food_rations,
    consume_food_rations,
    party_has_halfling,
    assassin_hide,
    attempt_gnome_gadget_door,
    attempt_gnome_trap_disarm,
    bulwark_magical_healing_blocked,
    clear_assassin_mark,
    gnome_smokescreen,
    gnome_gadget_free_prisoner,
    illusionist_continual_light,
    illusionist_distract,
    kukla_compartment_retrieve,
    kukla_compartment_retrieve_gold,
    kukla_compartment_stash,
    kukla_deploy_dolls,
    kukla_doll_round_attacks,
    kukla_green_ring_revive,
    kukla_red_ring_poison,
    resolve_social_save,
    make_kill_callback,
    mushroom_hyphae_communion,
    mushroom_spore_cloud,
    open_lever_door_with_gnome_gadget,
    paladin_heal,
    paladin_summon_steed,
    spend_caster_spell_slot,
    recover_acrobat_tricks_on_rest,
    luck_points_remaining,
    reroll_failed_save_with_luck,
    spend_acrobat_trick,
    spend_gnome_gadgets,
    spend_luck_point,
    spend_panache_point,
    spend_paladin_prayer,
    spend_rage_use,
)
from .class_profiles import (
    DRUID_SPELLS,
    ELF_BASIC_SPELLS,
    EXPLORATION_SPELLS,
    ILLUSIONIST_SPELLS,
    WIZARD_BASIC_SPELLS,
)
from .magic_items import (
    charged_magic_item_use_error,
    consume_magic_item_charge,
    find_magic_item,
    find_magic_item_by_name,
    parse_charged_magic_item,
)
from .scrolls import (
    barbarian_cannot_use_magic,
    barbarian_cannot_use_scrolls,
    consume_skalitos_page,
    find_scroll_item,
    find_skalitos_book,
    is_scroll_item,
    scroll_casting_modifier,
    scroll_spell_name,
)
from .combat_modifiers import is_spellcaster, spellcasting_modifier
from .spells import (
    can_cast_spell,
    cast_sleep_effect,
    knows_spell,
    magical_power_bonus_uses,
    mark_spell_expended,
    normalize_spell_name,
    resolve_spell_cast,
    spellcasting_roll_vs_level,
)
from .dice import roll_2d6, roll_d3, roll_d6, roll_d10, roll_die, roll_exploding_d6, roll_exploding_for_level, roll_formula, roll_start_tile_key, roll_tile_key, tier_die_sides
from .dungeon_table_roller import (
    DungeonTableRoller,
    SubtableOutcome,
    TreasureOutcome,
    attempt_open_door,
    door_discovery_log,
    resolve_gold_formula,
)
from .equipment_shop import can_class_use_item, jewelry_bribe_counted_gp
from .forsaken_depths_map import (
    fd_river_type_label,
    is_fd_ruleset,
    normalize_ruleset,
    roll_fd_dungeon_start_key,
    session_tile_catalog,
    should_enter_river_from_etr,
    starting_tile_catalog,
)
from .forsaken_depths_river import (
    apply_fd_dungeon_room_codes_on_enter,
    apply_fd_tears_death_madness_spread,
    apply_flame_river_entry,
    apply_room_codes_on_stretch_entry,
    apply_river_type_on_stretch_entry,
    apply_special_feature_hazard,
    consult_fd_conjuration_spirits,
    fd_acquire_boat_at_etr,
    fd_death_river_combat_adjustments,
    fd_disembark_at_bridge,
    fd_narrow_corridor_weapon_adjustment,
    fd_on_waste_of_time_hazard,
    fd_serpent_boating_modifier,
    fd_travel_mode_label,
    fd_validate_river_exit_travel,
    resolve_ghosts_of_the_river,
    resolve_river_teleport,
    tile_is_narrow_corridor,
)
from .tile_catalogs import TileCatalogId


# ---------------------------------------------------------------------------
# Monster stat formula helpers
# ---------------------------------------------------------------------------
import re as _re


def _hcl_to_tier(hcl: int) -> int:
    """Approximate tier for a given HCL (Tier 1 = HCL 1-3, Tier 2 = 4-6, …)."""
    return max(1, (hcl + 2) // 3)


def _parse_monster_life(value: object, hcl: int) -> int:
    """Convert a monster 'life' field to an integer, resolving formula strings.

    Supported formats:
      - int: returned as-is (min 1)
      - "HCL"   → hcl
      - "HCL+N" → hcl + N
      - "Tier+N" → _hcl_to_tier(hcl) + N
    """
    if isinstance(value, int):
        return max(1, value)
    s = str(value).strip()
    m = _re.match(r'^HCL(?:\+(\d+))?$', s, _re.IGNORECASE)
    if m:
        return max(1, hcl + int(m.group(1) or 0))
    m = _re.match(r'^Tier\+(\d+)$', s, _re.IGNORECASE)
    if m:
        return max(1, _hcl_to_tier(hcl) + int(m.group(1)))
    try:
        return max(1, int(s))
    except ValueError:
        return max(1, hcl)


def _parse_monster_attacks(value: object, hcl: int) -> int:
    """Convert a monster 'attacks' field to an integer, resolving formula strings.

    Supported formats:
      - int: returned as-is (min 0)
      - "Tier+N" → _hcl_to_tier(hcl) + N
      - dice expressions ("d3+1", etc.): evaluated via roll_formula
    """
    if isinstance(value, int):
        return max(0, value)
    s = str(value).strip()
    m = _re.match(r'^Tier\+(\d+)$', s, _re.IGNORECASE)
    if m:
        return max(1, _hcl_to_tier(hcl) + int(m.group(1)))
    try:
        return max(1, roll_formula(s))
    except ValueError:
        pass
    try:
        return max(1, int(s))
    except ValueError:
        return 1


# ---------------------------------------------------------------------------
DIRECTIONS: dict[str, tuple[int, int]] = {
    "north": (0, -1),
    "northeast": (1, -1),
    "east": (1, 0),
    "southeast": (1, 1),
    "south": (0, 1),
    "southwest": (-1, 1),
    "west": (-1, 0),
    "northwest": (-1, -1),
}
OPPOSITE = {
    "north": "south",
    "northeast": "southwest",
    "east": "west",
    "southeast": "northwest",
    "south": "north",
    "southwest": "northeast",
    "west": "east",
    "northwest": "southeast",
}
DIRECTION_ORDER = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
CARDINAL_DIRECTION_ORDER = ["north", "east", "south", "west"]
CARDINAL_DIRECTIONS = {
    key: DIRECTIONS[key] for key in ("north", "east", "south", "west")
}
EXIT_SPAN_STEPS = {
    "north": (1, 0),
    "south": (1, 0),
    "east": (0, 1),
    "west": (0, 1),
    "northeast": (1, 1),
    "southwest": (1, 1),
    "southeast": (1, -1),
    "northwest": (1, -1),
}
ROTATIONS = [0, 90, 180, 270]
FALLBACK_MAP_ELEMENT_KEY = "00"
ENTRANCE_TILE_KEYS = {f"0{die}" for die in range(1, 7)}
KERRAK_DAR_STATUS = "Kerrak Dar Hoard"
ENCHANTED_WEAPON_STATUS = "Enchanted weapon"
KERRAK_DAR_GOLD = 500
ENVIRONMENT_EVENT_KEYS = {
    "cavemen_explorers",
    "morlock_spy",
    "cave_goblin_scout",
    "dwarf_miner",
    "dwarf_party_gem",
    "fungal_cavemen",
    "halfling_scout",
    "fungal_merchant",
    "mycelial_warning",
}


@dataclass
class Placement:
    x: int
    y: int
    rotation: int
    exits: list[ExitState]
    walkable: list[str]
    cell_shapes: list[str]
    visible: list[str]
    truncated: bool = False


class RandomDungeonEngine:
    def __init__(self, rules: RulesRepository, asset_dir: Path) -> None:
        self.rules = rules
        self.asset_dir = asset_dir
        self.table_roller = DungeonTableRoller.from_rules(rules)

    def _tiles_for_session(self, session: SessionState | None = None, *, catalog: TileCatalogId | None = None) -> dict:
        if catalog is not None:
            return self._load_tile_catalog(catalog)
        if session is not None:
            return self._load_tile_catalog(session_tile_catalog(session))
        return self._load_tile_catalog("ee")

    def _load_tile_catalog(self, catalog: TileCatalogId) -> dict:
        try:
            return self.rules.tiles(catalog)
        except TypeError:
            return self.rules.tiles()

    def _apply_session_tile_catalog(self, session: SessionState, tile: TileState) -> None:
        session.tile_catalog = getattr(tile, "tile_catalog", None) or (
            "forsaken_depths" if is_fd_ruleset(session) else "ee"
        )

    def create_session(
        self,
        session_id: str,
        party_id: str,
        party: list[PartyMemberState],
        *,
        xp_system: str = "classical",
        map_bounds_mode: str = "unlimited",
        unlimited_map_element_cap: int = 60,
        fiendish_foes_enabled: bool = True,
        start_camped_outside: bool = False,
        ruleset: str = "ee",
        courtship_enabled: bool | None = None,
        ruleset_profile_id: str | None = None,
        tag_banking_enabled: bool = False,
    ) -> SessionState:
        chosen_fiendish = normalize_fiendish_foes_enabled(fiendish_foes_enabled)
        eligible = party_fiendish_foes_eligible(party)
        from .ruleset_profiles import resolve_profile_for_adventure

        profile = resolve_profile_for_adventure(
            "random",
            profile_id=ruleset_profile_id,
            ruleset=ruleset,
            courtship_enabled=courtship_enabled,
        )
        chosen_ruleset = normalize_ruleset(profile.ruleset)
        fd_ruleset = chosen_ruleset == "forsaken_depths"
        chosen_courtship = (
            courtship_enabled if courtship_enabled is not None else profile.courtship_enabled
        )
        start_catalog = starting_tile_catalog(chosen_ruleset)
        if fd_ruleset:
            tile_key = roll_fd_dungeon_start_key()
        else:
            tile_key = roll_start_tile_key()
        tile_def = self._load_tile_catalog(start_catalog).get(tile_key)
        tile_type = self._tile_type(tile_def.tile_type if tile_def else "room")
        width = tile_def.footprint_width if tile_def else 1
        height = tile_def.footprint_height if tile_def else 1
        exits = self._starting_exits(
            tile_key,
            tile_def,
            width,
            height,
            ensure_dungeon_exit=True,
        )
        entrance = TileState(
            id=uuid4().hex,
            x=0,
            y=0,
            tile_key=tile_key,
            tile_type=tile_type,
            rotation=0,
            footprint_width=width,
            footprint_height=height,
            editor_cell_size=tile_def.editor_cell_size if tile_def else 80,
            image_scale=tile_def.image_scale if tile_def else 1.0,
            image_offset_x=tile_def.image_offset_x if tile_def else 0,
            image_offset_y=tile_def.image_offset_y if tile_def else 0,
            walkable=self._normalized_walkable(tile_def, width, height, catalog=start_catalog),
            cell_shapes=self._normalized_cell_shapes(tile_def, width, height),
            visible=self._visible_rows(width, height),
            image=self._tile_image(tile_key, tile_def.image if tile_def else None),
            title=tile_def.name if tile_def else f"Entrance Map Element {tile_key}",
            description=(
                "The party enters the forsaken depths."
                if fd_ruleset
                else "The party enters the dungeon."
            ),
            content_key="entrance",
            objects=["Entrance"] if not fd_ruleset else ["Forsaken Depths"],
            exits=exits,
            environment="dungeon",
            terrain=tile_def.terrain if tile_def and fd_ruleset else "outdoor",
            tile_catalog=start_catalog,
            room_codes=list(tile_def.room_codes) if tile_def else [],
        )
        for index, member in enumerate(party, start=1):
            member.marching_order = index
            prune_weapon_defaults(member)
        timestamp = now_utc()
        valid_xp = {"classical", "slow_and_sure", "old_school", "slower_advancement"}
        chosen_xp = xp_system if xp_system in valid_xp else "classical"
        valid_bounds = {"unlimited", "paper"}
        chosen_bounds = map_bounds_mode if map_bounds_mode in valid_bounds else "unlimited"
        chosen_cap = normalize_unlimited_map_element_cap(unlimited_map_element_cap)
        map_width = 20 if chosen_bounds == "paper" else 31
        map_height = 28 if chosen_bounds == "paper" else 31
        party_xp = [member.xp for member in party]
        log = [
            (
                f"Forsaken Depths start roll: d66 = {tile_key}."
                if fd_ruleset
                else f"Entrance map element roll: d6 = {tile_key[1]} -> {tile_key}."
            ),
            (
                "The party will camp outside before the first foray."
                if start_camped_outside
                else "Adventure begins at the dungeon entrance."
            ),
            f"Campaign mode: {campaign_mode_label(chosen_xp)}.",
        ]
        if chosen_bounds == "paper":
            log.append(f"Paper map mode: placement limited to a {map_width}×{map_height} grid (p.149).")
        elif chosen_bounds == "unlimited":
            log.append(
                f"Unlimited map mode: growth capped at {chosen_cap} map elements before the Final Boss must appear."
            )
        if chosen_fiendish != "off":
            log.append(fiendish_foes_session_label(chosen_fiendish, eligible=eligible) + ".")
        if fd_ruleset:
            if chosen_courtship:
                log.append(
                    "Courtship of Flower Demons enabled — Portal events may branch to the Blossoms' Demesne (TCOTFD)."
                )
            else:
                log.append("Courtship of Flower Demons disabled — Portal Demesne branch unavailable this adventure.")
        starting_clues = sum(max(0, member.clues) for member in party)
        if starting_clues:
            log.append(f"Party begins with {starting_clues} carried Clue(s).")
        self._initialize_outside_entrance(entrance, log=log)
        prepare_adventure_expert_items(party, log)
        for member in party:
            snapshot_carry_baseline(member)
        session = SessionState(
            id=session_id,
            party_id=party_id,
            adventure_id="random",
            adventure_type="random",
            mode="exploration",
            party=party,
            map_state=MapState(
                width=map_width,
                height=map_height,
                tiles=[entrance],
                current_tile_id=entrance.id,
            ),
            log=log,
            clues_found=starting_clues,
            xp_system=chosen_xp,
            map_bounds_mode=chosen_bounds,
            unlimited_map_element_cap=chosen_cap,
            environment="dungeon",
            fiendish_foes_enabled=chosen_fiendish,
            ruleset=chosen_ruleset,  # type: ignore[arg-type]
            ruleset_profile_id=profile.id,
            tag_banking_enabled=tag_banking_enabled,
            tile_catalog=start_catalog,
            courtship_enabled=bool(chosen_courtship),
            old_school_xp_tally=initial_xp_tally(party_xp) if chosen_xp == "old_school" else 0,
            slower_xp_bank=initial_xp_tally(party_xp) if chosen_xp == "slower_advancement" else 0,
            created_at=timestamp,
            updated_at=timestamp,
        )
        if start_camped_outside:
            from .adventure_session import apply_start_camped_outside

            apply_start_camped_outside(self, session)
        return session

    def create_courtship_demesne_session(
        self,
        session_id: str,
        party_id: str,
        party: list[PartyMemberState],
        *,
        xp_system: str = "classical",
        map_bounds_mode: str = "unlimited",
        unlimited_map_element_cap: int = 60,
        tag_banking_enabled: bool = False,
    ) -> SessionState:
        from .courtship_demesne import COURTSHIP_DEMESNE_ADVENTURE_ID

        for index, member in enumerate(party, start=1):
            member.marching_order = index
            prune_weapon_defaults(member)
        timestamp = now_utc()
        valid_xp = {"classical", "slow_and_sure", "old_school", "slower_advancement"}
        chosen_xp = xp_system if xp_system in valid_xp else "classical"
        valid_bounds = {"unlimited", "paper"}
        chosen_bounds = map_bounds_mode if map_bounds_mode in valid_bounds else "unlimited"
        chosen_cap = normalize_unlimited_map_element_cap(unlimited_map_element_cap)
        map_width = 20 if chosen_bounds == "paper" else 31
        map_height = 28 if chosen_bounds == "paper" else 31
        party_xp = [member.xp for member in party]
        seaside = TileState(
            id=uuid4().hex,
            x=0,
            y=0,
            tile_key="courtship-seaside",
            tile_type="room",
            title="Blossoms' Demesne — Seaside",
            description="The party explores the Seaside of the Blossoms' Demesne (TCOTFD).",
            content_key="courtship_demesne",
            objects=["Demesne"],
            environment="dungeon",
            terrain="outdoor",
        )
        starting_clues = sum(max(0, member.clues) for member in party)
        log = [
            "Adventure: Courtship of Flower Demons — Blossoms' Demesne (TCOTFD).",
            "The party arrives at the Seaside. Roll Demesne encounters here; cast Flower Portal from Seaside to end the visit.",
            f"Campaign mode: {campaign_mode_label(chosen_xp)}.",
        ]
        if chosen_bounds == "paper":
            log.append(f"Paper map mode: placement limited to a {map_width}×{map_height} grid (p.149).")
        elif chosen_bounds == "unlimited":
            log.append(
                f"Unlimited map mode: growth capped at {chosen_cap} map elements before the Final Boss must appear."
            )
        if starting_clues:
            log.append(f"Party begins with {starting_clues} carried Clue(s).")
        prepare_adventure_expert_items(party, log)
        for member in party:
            snapshot_carry_baseline(member)
        session = SessionState(
            id=session_id,
            party_id=party_id,
            adventure_id=COURTSHIP_DEMESNE_ADVENTURE_ID,
            adventure_type="random",
            mode="exploration",
            party=party,
            map_state=MapState(
                width=map_width,
                height=map_height,
                tiles=[seaside],
                current_tile_id=seaside.id,
            ),
            log=log,
            clues_found=starting_clues,
            xp_system=chosen_xp,
            map_bounds_mode=chosen_bounds,
            unlimited_map_element_cap=chosen_cap,
            environment="dungeon",
            fiendish_foes_enabled="off",
            ruleset="forsaken_depths",
            ruleset_profile_id="courtship_demesne",
            tag_banking_enabled=tag_banking_enabled,
            courtship_enabled=True,
            courtship_demesne_active=True,
            courtship_demesne_region="seaside",
            courtship_entry_source="standalone",
            courtship_return_tile_id=seaside.id,
            old_school_xp_tally=initial_xp_tally(party_xp) if chosen_xp == "old_school" else 0,
            slower_xp_bank=initial_xp_tally(party_xp) if chosen_xp == "slower_advancement" else 0,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return session

    def advance(
        self,
        session: SessionState,
        action: str,
        exit_id: str | None = None,
        direction: str | None = None,
        character_id: str | None = None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        search_choice: str | None = None,
        special_feature_choice: str | None = None,
        tile_content_choice: str | None = None,
        secret_passage_environment: str | None = None,
        environment_event_choice: str | None = None,
        secret_id: str | None = None,
        spell_name: str | None = None,
        pay_bribe: bool = False,
        trade_information_choice: str | None = None,
        reaction_choice: str | None = None,
        reaction_bribe_mode: str | None = None,
        subdual: bool = False,
        marching_order: int | None = None,
        alchemist_item: str | None = None,
        xp_spent: int | None = None,
        target_character_id: str | None = None,
        item_name: str | None = None,
        target_weapon: str | None = None,
        gold_amount: int | None = None,
        weapon_kind: str | None = None,
        attack_targets: dict[str, str] | None = None,
        attack_secondary_targets: dict[str, str] | None = None,
        double_kick_targets: dict[str, list[str]] | None = None,
        protective_incense_targets: dict[str, str] | None = None,
        nail_doors: bool = False,
        rest_choices: dict[str, str] | None = None,
        combat_abilities: dict[str, str] | None = None,
        guard_targets: dict[str, str] | None = None,
        gadget_points: int | None = None,
        use_luck_flee: bool = False,
        use_daring_escape: bool = False,
        panache_spend: int | None = None,
        class_ability: str | None = None,
        nourishing_meal: bool = False,
        nourishing_meal_eaters: list[str] | None = None,
        everyone_eats: bool = False,
        feed_character_ids: list[str] | None = None,
        milestone_id: str | None = None,
        scroll_librarian_spell: str | None = None,
        panoplia_favor_kind: str | None = None,
        foe_id: str | None = None,
        secondary_foe_id: str | None = None,
        spell_target_mode: str | None = None,
        tier_training: str | None = None,
        use_xp_for_tier: bool = False,
        advancement_fork: str | None = None,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
        heroic_skill_id: str | None = None,
        legendary_skill_id: str | None = None,
        heroic_skill_target: str | None = None,
        reaction_adjust: int | None = None,
        glamour_mask_reroll: bool = False,
        life_transfer_amount: int | None = None,
        teleport_tile_id: str | None = None,
        teleport_character_ids: list[str] | None = None,
        mass_blessing_target_ids: list[str] | None = None,
        mass_blessing_condition_choices: dict[str, list[str]] | None = None,
        dungeon_exit_intent: str | None = None,
        detached_character_ids: list[str] | None = None,
        detached_tile_id: str | None = None,
        trap_boulder_origin: str | None = None,
        trap_boulder_block_exit_id: str | None = None,
        trap_snare_item_name: str | None = None,
        madness_choice: str | None = None,
        bodyguard_intercept_choice: str | None = None,
        acolyte_blessing_choice: str | None = None,
        envenom_weapon_kind: str | None = None,
        fallen_transfer_kind: str | None = None,
        free_slaves_choice: str | None = None,
        paint_choice: str | None = None,
        paint_direction: str | None = None,
        paint_quantity: int | None = None,
        paint_item_key: str | None = None,
        wand_power_charges: int | None = None,
        use_prayer_bead: bool = False,
        treasure_outcome_choice: str | None = None,
        fd_revelation_choice: str | None = None,
        fd_secret_passage_destination: str | None = None,
        fd_portal_destination: str | None = None,
        fd_cairn_natural_one_choice: str | None = None,
        fd_quest_reward_choice: str | None = None,
        fd_quest_from_treasure: bool = False,
        fd_quest_id: str | None = None,
        courtship_region: str | None = None,
        courtship_encounter_shift: str | None = None,
        courtship_choice: str | None = None,
        abyss_plot_choice: str | None = None,
        courtship_dominant_stance: bool | None = None,
        courtship_passionate_stance: bool | None = None,
        courtship_use_luck: bool = False,
        courtship_damsel_penalty: str | None = None,
        fd_idol_choice: str | None = None,
        hireling_id: str | None = None,
        retainer_type: str | None = None,
        professional_id: str | None = None,
        trained_professional_skill: str | None = None,
        professional_provider_id: str | None = None,
        hireling_marching_order: int | None = None,
        hireling_ability: str | None = None,
        fortune_roll_value: int | None = None,
        alchemist_potion_id: str | None = None,
    ) -> SessionState:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return self._touch(session)

        self._resolve_stale_combat(session)
        self._ensure_individual_clues(session)
        self._queue_fallen_transfer(session)
        if action != "resolve_trap" and session.pending_mycelium_snare is not None:
            session.log.append(
                "Choose which held object the mycelium snatches (use the trap menu on that tile)."
            )
            return self._touch(session)
        if action != "resolve_free_slaves" and session.pending_free_slaves_tile_id is not None:
            session.log.append(
                "The Fiendish Chaos Lord's slaves may be freed for 1 Clue (triggers Wandering Monsters). "
                "Choose Free Slaves or Decline."
            )
            return self._touch(session)
        if action != "resolve_fallen_transfer" and session.pending_fallen_transfer is not None:
            pending = session.pending_fallen_transfer
            fallen = next(
                (member for member in session.party if member.character_id == pending.from_character_id),
                None,
            )
            name = fallen.name if fallen else "A fallen hero"
            item = "Clues" if pending.kind == "clues" else "Secrets"
            session.log.append(f"{name} is fallen. Choose a living hero to inherit their {item}.")
            return self._touch(session)
        if action != "resolve_bodyguard_intercept" and session.pending_bodyguard_intercept is not None:
            session.log.append("Choose whether the bodyguard intercepts the attack.")
            return self._touch(session)
        if action != "resolve_acolyte_blessing" and session.pending_acolyte_blessing is not None:
            session.log.append("Choose whether the acolyte tries to preserve Blessing.")
            return self._touch(session)
        turn_actions = {
            "explore",
            "search",
            "look",
            "combat_round",
            "rest",
            "open_door",
            "listen_at_door",
            "resolve_trap",
            "resolve_special_feature",
            "resolve_environment_event",
            "resolve_tile_content_choice",
            "choose_secret_passage_environment",
            "dip_water_pool",
            "resolve_echo_spell",
            "resolve_madness_choice",
            "resolve_bodyguard_intercept",
            "resolve_acolyte_blessing",
            "envenom_weapon",
            "resolve_fallen_transfer",
            "resolve_free_slaves",
            "turn_back_from_mantlebeast",
            "use_map_fragment",
            "use_enchanted_paint",
            "use_berserkers_mushroom",
            "climb_from_pit",
            "probe_trap",
            "use_miners_ointment",
            "use_herbal_tonic",
            "apply_gremlin_repellant",
            "choose_treasure_outcome",
            "fd_oblivion_redeem_madness",
            "fd_spend_hallucination_revelation",
            "fd_prisoners_escape",
            "fd_secret_passage_unlock_clues",
            "choose_fd_secret_passage_destination",
            "choose_fd_event_portal",
            "claim_fd_hidden_treasure",
            "tap_fd_cairn_energy",
            "resolve_fd_cairn_natural_one",
            "consult_fd_conjuration_spirits",
            "fd_disembark_at_bridge",
            "accept_fd_quest",
            "refuse_fd_lady_in_gray",
            "claim_fd_quest_reward",
            "enter_fd_dark_pits",
            "turn_in_fd_quest_item",
            "fd_quest_spend_clue_enemy",
            "fd_quest_spend_clues_servitor",
            "recover_fd_lost_page",
            "report_fd_idol_visit",
            "resolve_fd_cyclopean_idol",
            "choose_fd_idol_outcome",
            "courtship_roll_encounter",
            "courtship_choose_pathway",
            "courtship_leave_demesne",
            "courtship_spend_encounter_clue",
            "courtship_woo_encounter",
            "courtship_fight_encounter",
            "courtship_occlith_choice",
            "courtship_lady_of_lament_choice",
            "courtship_lady_keepsake",
            "courtship_secret_trail_clue",
            "courtship_woo_giving",
            "courtship_woo_withholding",
            "courtship_woo_abort_fight",
            "courtship_seduce_reaction",
            "courtship_book_choice",
            "courtship_damsel_penalty",
            "courtship_libidinal_reroll",
            "courtship_brew_apothecary",
            "use_apothecary_brew",
            "use_blossoms_item",
            "use_abyss_item",
            "treat_lycanthropy",
            "start_abyss_campaign_plot",
            "abyss_plot_contribute_gold",
            "abyss_plot_take_artifact_piece",
            "abyss_plot_spend_clues",
            "abyss_plot_transfer_artifact",
            "abyss_plot_resolve_finale",
            "hunt_vampire_sire",
            "enter_fd_side_sheet",
            "exit_fd_side_sheet",
            "swap_weapon",
            "detached_combat_round",
        }

        if action == "explore":
            self._explore(
                session,
                exit_id,
                direction,
                show_rolls=show_rolls,
                explain_math=explain_math,
                dungeon_exit_intent=dungeon_exit_intent,
            )
        elif action == "return_to_dungeon":
            self._return_to_dungeon_from_camp(session)
        elif action == "search":
            self._search(
                session,
                search_choice=search_choice,
                character_id=character_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "look":
            self._look_around(session)
        elif action == "start_combat":
            self._start_combat(session, show_rolls=show_rolls)
        elif action == "turn_back_from_mantlebeast":
            self._turn_back_from_mantlebeast(session, show_rolls=show_rolls)
        elif action == "combat_round":
            self._combat_round(
                session,
                show_rolls=show_rolls,
                explain_math=explain_math,
                subdual=subdual,
                attack_targets=attack_targets,
                attack_secondary_targets=attack_secondary_targets,
                double_kick_targets=double_kick_targets,
                protective_incense_targets=protective_incense_targets,
                combat_abilities=combat_abilities,
                guard_targets=guard_targets,
            )
        elif action == "check_reaction":
            self._check_reaction(
                session,
                show_rolls=show_rolls,
                explain_math=explain_math,
                reaction_adjust=reaction_adjust,
                glamour_mask_reroll=glamour_mask_reroll,
            )
        elif action == "pay_bribe":
            self._pay_bribe(session, accept=pay_bribe, show_rolls=show_rolls)
        elif action == "pay_bribe_fools_gold":
            self._pay_bribe_fools_gold(session, show_rolls=show_rolls)
        elif action == "trade_information":
            self._trade_information(session, trade_information_choice)
        elif action == "reaction_choice":
            self._reaction_choice(
                session,
                reaction_choice,
                character_id=character_id,
                item_name=item_name,
                reaction_bribe_mode=reaction_bribe_mode,
                show_rolls=show_rolls,
            )
        elif action == "cast_spell":
            self._cast_spell(
                session,
                character_id,
                spell_name,
                exit_id=exit_id,
                target_character_id=target_character_id,
                target_foe_id=foe_id,
                secondary_foe_id=secondary_foe_id,
                spell_target_mode=spell_target_mode,
                life_transfer_amount=life_transfer_amount,
                teleport_tile_id=teleport_tile_id,
                teleport_character_ids=teleport_character_ids,
                mass_blessing_target_ids=mass_blessing_target_ids,
                mass_blessing_condition_choices=mass_blessing_condition_choices,
                courtship_choice=courtship_choice,
                wand_power_charges=wand_power_charges,
                use_prayer_bead=use_prayer_bead,
                item_name=item_name,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "choose_treasure_outcome":
            self._choose_treasure_outcome(
                session,
                treasure_outcome_choice,
                show_rolls=show_rolls,
            )
        elif action == "fd_oblivion_redeem_madness":
            self._fd_oblivion_redeem_madness(session, character_id, show_rolls=show_rolls)
        elif action == "fd_spend_hallucination_revelation":
            self._fd_spend_hallucination_revelation(session, fd_revelation_choice, show_rolls=show_rolls)
        elif action == "choose_fd_event_portal":
            from .forsaken_depths_events import choose_fd_event_portal

            choose_fd_event_portal(
                self,
                session,
                fd_portal_destination,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "claim_fd_hidden_treasure":
            from .forsaken_depths_events import claim_fd_hidden_treasure_chamber

            claim_fd_hidden_treasure_chamber(self, session, show_rolls=show_rolls)
        elif action == "tap_fd_cairn_energy":
            from .forsaken_depths_cairn import tap_fd_cairn_energy

            tap_fd_cairn_energy(
                self,
                session,
                character_id,
                spell_name,
                show_rolls=show_rolls,
            )
        elif action == "resolve_fd_cairn_natural_one":
            from .forsaken_depths_cairn import tap_fd_cairn_energy

            pending = session.pending_fd_cairn_natural_one
            if pending is None:
                session.log.append("No Cairn natural-1 choice is pending.")
            else:
                tap_fd_cairn_energy(
                    self,
                    session,
                    pending.get("character_id"),
                    pending.get("spell_name"),
                    show_rolls=show_rolls,
                    natural_one_choice=fd_cairn_natural_one_choice,
                )
                if fd_cairn_natural_one_choice:
                    session.pending_fd_cairn_natural_one = None
        elif action == "consult_fd_conjuration_spirits":
            consult_fd_conjuration_spirits(
                self,
                session,
                character_id,
                show_rolls=show_rolls,
            )
        elif action == "fd_disembark_at_bridge":
            tile = self._current_tile(session)
            fd_disembark_at_bridge(session, tile, show_rolls=show_rolls)
        elif action == "accept_fd_quest":
            from .forsaken_depths_quest import accept_fd_quest

            accept_fd_quest(self, session, show_rolls=show_rolls)
        elif action == "refuse_fd_lady_in_gray":
            from .forsaken_depths_quest import refuse_fd_lady_in_gray

            tile = self._current_tile(session)
            if tile is not None:
                refuse_fd_lady_in_gray(session, tile, show_rolls=show_rolls)
        elif action == "claim_fd_quest_reward":
            from .forsaken_depths_quest import claim_fd_quest_reward

            claim_fd_quest_reward(
                self,
                session,
                show_rolls=show_rolls,
                reward_choice=fd_quest_reward_choice,
                spell_name=spell_name,
                quest_id=fd_quest_id,
            )
        elif action == "enter_fd_dark_pits":
            from .forsaken_depths_side_sheet import enter_fd_dark_pits

            enter_fd_dark_pits(self, session, show_rolls=show_rolls)
        elif action == "turn_in_fd_quest_item":
            from .forsaken_depths_quest import turn_in_fd_quest_item

            turn_in_fd_quest_item(self, session, item_name, show_rolls=show_rolls, quest_id=fd_quest_id)
        elif action == "fd_quest_spend_clue_enemy":
            from .forsaken_depths_quest import spend_fd_quest_clue_for_enemy

            spend_fd_quest_clue_for_enemy(self, session, show_rolls=show_rolls, quest_id=fd_quest_id)
        elif action == "fd_quest_spend_clues_servitor":
            from .forsaken_depths_quest import spend_fd_quest_clues_for_servitor

            spend_fd_quest_clues_for_servitor(self, session, show_rolls=show_rolls, quest_id=fd_quest_id)
        elif action == "recover_fd_lost_page":
            from .forsaken_depths_quest import recover_fd_lost_page

            recover_fd_lost_page(
                self,
                session,
                item_name,
                from_treasure=fd_quest_from_treasure,
                show_rolls=show_rolls,
                quest_id=fd_quest_id,
            )
        elif action == "report_fd_idol_visit":
            from .forsaken_depths_quest import report_fd_idol_visit

            report_fd_idol_visit(self, session, show_rolls=show_rolls, quest_id=fd_quest_id)
        elif action == "resolve_fd_cyclopean_idol":
            from .forsaken_depths_cyclopean_idol import roll_fd_cyclopean_idol

            tile = self._tile_by_id(session, session.map_state.current_tile_id)
            roll_fd_cyclopean_idol(self, session, tile, show_rolls=show_rolls)
        elif action == "choose_fd_idol_outcome":
            from .forsaken_depths_cyclopean_idol import resolve_fd_idol_choice

            tile = self._tile_by_id(session, session.map_state.current_tile_id)
            resolve_fd_idol_choice(
                self,
                session,
                tile,
                fd_idol_choice,
                item_name=item_name,
                show_rolls=show_rolls,
            )
        elif action == "courtship_roll_encounter":
            from .courtship_demesne import roll_courtship_encounter

            roll_courtship_encounter(self, session, show_rolls=show_rolls)
        elif action == "courtship_choose_pathway":
            from .courtship_demesne import choose_courtship_pathway

            choose_courtship_pathway(session, courtship_region, show_rolls=show_rolls)
        elif action == "courtship_leave_demesne":
            from .courtship_demesne import leave_courtship_demesne

            leave_courtship_demesne(self, session, show_rolls=show_rolls)
        elif action == "courtship_spend_encounter_clue":
            from .courtship_demesne import spend_courtship_encounter_clue

            spend_courtship_encounter_clue(
                self,
                session,
                courtship_encounter_shift or "reroll",
                show_rolls=show_rolls,
            )
        elif action == "courtship_woo_encounter":
            from .courtship_demesne import resolve_courtship_woo_encounter

            resolve_courtship_woo_encounter(self, session, show_rolls=show_rolls)
        elif action == "courtship_fight_encounter":
            from .courtship_demesne import resolve_courtship_fight_encounter

            resolve_courtship_fight_encounter(self, session, show_rolls=show_rolls)
        elif action == "courtship_occlith_choice":
            from .courtship_demesne import resolve_courtship_occlith_choice

            resolve_courtship_occlith_choice(self, session, courtship_choice, show_rolls=show_rolls)
        elif action == "courtship_lady_of_lament_choice":
            from .courtship_demesne import resolve_courtship_lady_of_lament_choice

            resolve_courtship_lady_of_lament_choice(session, courtship_choice, show_rolls=show_rolls)
        elif action == "courtship_lady_keepsake":
            from .courtship_demesne import apply_lady_keepsake_bonus

            apply_lady_keepsake_bonus(session, show_rolls=show_rolls)
        elif action == "courtship_secret_trail_clue":
            from .courtship_demesne import spend_courtship_secret_trail_clue

            spend_courtship_secret_trail_clue(self, session, show_rolls=show_rolls)
        elif action == "courtship_woo_giving":
            from .courtship_demesne import resolve_courtship_woo_giving

            resolve_courtship_woo_giving(
                self,
                session,
                dominant_stance=bool(courtship_dominant_stance),
                passionate_stance=bool(courtship_passionate_stance),
                use_luck=bool(courtship_use_luck),
                show_rolls=show_rolls,
            )
        elif action == "courtship_woo_withholding":
            from .courtship_demesne import resolve_courtship_woo_withholding

            resolve_courtship_woo_withholding(
                self,
                session,
                dominant_stance=bool(courtship_dominant_stance),
                passionate_stance=bool(courtship_passionate_stance),
                use_luck=bool(courtship_use_luck),
                show_rolls=show_rolls,
            )
        elif action == "courtship_woo_abort_fight":
            from .courtship_demesne import resolve_courtship_woo_abort_fight

            resolve_courtship_woo_abort_fight(self, session, show_rolls=show_rolls)
        elif action == "courtship_seduce_reaction":
            from .courtship_demesne import resolve_courtship_seduce_reaction

            resolve_courtship_seduce_reaction(self, session, courtship_choice, show_rolls=show_rolls)
        elif action == "courtship_book_choice":
            from .courtship_demesne import resolve_courtship_book_choice

            resolve_courtship_book_choice(self, session, courtship_choice, show_rolls=show_rolls)
        elif action == "use_blossoms_item":
            self._use_blossoms_item(
                session,
                character_id,
                item_name,
                courtship_choice,
                show_rolls=show_rolls,
            )
        elif action == "use_abyss_item":
            self._use_abyss_item(
                session,
                character_id,
                item_name,
                mode=treasure_outcome_choice or courtship_choice,
                target_enemy_id=foe_id,
                show_rolls=show_rolls,
            )
        elif action == "treat_lycanthropy":
            self._treat_lycanthropy(session, character_id, show_rolls=show_rolls)
        elif action == "courtship_damsel_penalty":
            from .courtship_demesne import resolve_courtship_damsel_penalty

            resolve_courtship_damsel_penalty(
                session,
                courtship_damsel_penalty,
                show_rolls=show_rolls,
            )
        elif action == "courtship_libidinal_reroll":
            from .courtship_demesne import resolve_courtship_libidinal_reroll

            resolve_courtship_libidinal_reroll(self, session, show_rolls=show_rolls)
        elif action == "courtship_brew_apothecary":
            from .courtship_apothecary_brew import resolve_apothecary_brew_choice

            resolve_apothecary_brew_choice(
                self,
                session,
                courtship_choice,
                show_rolls=show_rolls,
            )
        elif action == "tag_settlement_brew_apothecary":
            from .courtship_apothecary_brew import resolve_tag_settlement_apothecary_brew

            resolve_tag_settlement_apothecary_brew(
                self,
                session,
                courtship_choice,
                show_rolls=show_rolls,
            )
        elif action == "use_apothecary_brew":
            self._use_apothecary_brew(
                session,
                character_id,
                item_name,
                show_rolls=show_rolls,
            )
        elif action == "fd_prisoners_escape":
            self._fd_prisoners_escape(session, show_rolls=show_rolls)
        elif action == "fd_secret_passage_unlock_clues":
            self._fd_secret_passage_unlock_clues(session, show_rolls=show_rolls)
        elif action == "choose_fd_secret_passage_destination":
            from .forsaken_depths_secret_passage import choose_fd_secret_passage_destination

            choose_fd_secret_passage_destination(
                self,
                session,
                fd_secret_passage_destination,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "enter_fd_side_sheet":
            self._enter_fd_side_sheet(session, show_rolls=show_rolls)
        elif action == "exit_fd_side_sheet":
            self._exit_fd_side_sheet(session, show_rolls=show_rolls)
        elif action == "burn_scroll":
            self._burn_scroll(
                session,
                character_id,
                spell_name,
                exit_id=exit_id,
                target_character_id=target_character_id,
                target_foe_id=foe_id,
                spell_target_mode=spell_target_mode,
                mass_blessing_target_ids=mass_blessing_target_ids,
                mass_blessing_condition_choices=mass_blessing_condition_choices,
                courtship_choice=courtship_choice,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "use_magic_item":
            self._use_magic_item(
                session,
                character_id,
                spell_name,
                item_name=item_name,
                exit_id=exit_id,
                target_character_id=target_character_id,
                target_foe_id=foe_id,
                spell_target_mode=spell_target_mode,
                mass_blessing_target_ids=mass_blessing_target_ids,
                mass_blessing_condition_choices=mass_blessing_condition_choices,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "copy_scroll":
            self._copy_scroll(session, character_id, spell_name)
        elif action == "spellcast_door":
            self._spellcast_door(session, exit_id, character_id, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "spend_clues_on_door":
            self._spend_clues_on_door(session, exit_id, show_rolls=show_rolls)
        elif action == "use_hidden_pit_clue":
            self._use_hidden_pit_clue(session, show_rolls=show_rolls)
        elif action == "claim_kerrak_dar_hoard":
            self._claim_kerrak_dar_hoard(session)
        elif action == "reveal_secret_with_clues":
            self._reveal_secret_with_clues(session, character_id, secret_id=secret_id, spell_id=spell_name)
        elif action == "learn_spell_with_clues":
            self._learn_spell_with_clues(session, character_id, expert_skill_id)
        elif action == "use_secret":
            self._use_secret(
                session,
                character_id,
                secret_id,
                foe_id,
                spell_id=expert_skill_id or spell_name,
                scroll_form=item_name,
                target_character_id=target_character_id,
            )
        elif action == "pass_using_deal":
            self._pass_using_deal(session, character_id)
        elif action == "break_prisoner_chains":
            self._break_prisoner_chains(session, character_id, show_rolls=show_rolls)
        elif action == "choose_prisoner_reward":
            self._choose_prisoner_reward(session, character_id, spell_name)
        elif action == "flee":
            self._flee(
                session,
                show_rolls=show_rolls,
                explain_math=explain_math,
                use_luck_flee=use_luck_flee,
                use_daring_escape=use_daring_escape,
                character_id=character_id,
                target_character_id=target_character_id,
                foe_id=foe_id,
            )
        elif action == "withdraw":
            self._withdraw(session, exit_id, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "rest":
            self._rest(
                session,
                nail_doors=nail_doors,
                rest_choices=rest_choices,
                show_rolls=show_rolls,
                nourishing_meal=nourishing_meal,
                nourishing_meal_eaters=nourishing_meal_eaters,
                everyone_eats=everyone_eats,
            )
        elif action == "open_door":
            self._open_door(session, exit_id, character_id, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "listen_at_door":
            self._listen_at_door(session, exit_id, character_id, show_rolls=show_rolls)
        elif action == "resolve_trap":
            self._resolve_trap(
                session,
                show_rolls=show_rolls,
                explain_math=explain_math,
                boulder_origin=trap_boulder_origin,
                boulder_block_exit_id=trap_boulder_block_exit_id,
                snare_item_name=trap_snare_item_name,
            )
        elif action == "resolve_special_feature":
            self._resolve_special_feature_choice(
                session,
                special_feature_choice,
                target_character_id=target_character_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "resolve_environment_event":
            self._resolve_environment_event(
                session,
                environment_event_choice,
                character_id=character_id,
                item_name=item_name,
                target_weapon=target_weapon,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "resolve_tile_content_choice":
            self._resolve_tile_content_choice(
                session,
                tile_content_choice,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "choose_secret_passage_environment":
            self._choose_secret_passage_environment(
                session,
                secret_passage_environment,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "dip_water_pool":
            self._dip_water_pool(session, character_id, show_rolls=show_rolls)
        elif action == "resolve_echo_spell":
            self._resolve_echo_spell(
                session,
                target_character_id=target_character_id,
                foe_id=foe_id,
                secondary_foe_id=secondary_foe_id,
                spell_target_mode=spell_target_mode,
                life_transfer_amount=life_transfer_amount,
                teleport_tile_id=teleport_tile_id,
                teleport_character_ids=teleport_character_ids,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "resolve_madness_choice":
            resolve_madness_choice(
                session,
                character_id=character_id,
                choice=madness_choice,
            )
        elif action == "resolve_bodyguard_intercept":
            from .hirelings import resolve_bodyguard_intercept

            session.log.extend(
                resolve_bodyguard_intercept(
                    session,
                    choice=bodyguard_intercept_choice,
                    show_rolls=show_rolls,
                )
            )
            self._resume_bodyguard_paused_combat(
                session,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "resolve_acolyte_blessing":
            from .hirelings import resolve_acolyte_blessing

            session.log.extend(
                resolve_acolyte_blessing(
                    session,
                    choice=acolyte_blessing_choice,
                    show_rolls=show_rolls,
                )
            )
        elif action == "envenom_weapon":
            self._envenom_weapon(session, character_id, envenom_weapon_kind)
        elif action == "use_map_fragment":
            self._use_map_fragment(session, character_id, show_rolls=show_rolls, explain_math=explain_math)
        elif action == "use_enchanted_paint":
            self._use_enchanted_paint(
                session,
                character_id,
                paint_choice=paint_choice,
                paint_direction=paint_direction or direction,
                paint_quantity=paint_quantity,
                paint_item_key=paint_item_key,
                show_rolls=show_rolls,
            )
        elif action == "probe_trap":
            self._probe_trap(session, show_rolls=show_rolls)
        elif action == "use_miners_ointment":
            self._use_miners_ointment(session, character_id)
        elif action == "use_herbal_tonic":
            self._use_herbal_tonic(session, character_id)
        elif action == "apply_gremlin_repellant":
            self._apply_gremlin_repellant(session, character_id)
        elif action == "use_berserkers_mushroom":
            self._use_berserkers_mushroom(session, character_id, item_name=item_name)
        elif action == "climb_from_pit":
            self._climb_from_pit(session, character_id, target_character_id)
        elif action == "use_wolfsbane":
            self._use_wolfsbane(
                session,
                character_id,
                item_name=item_name,
                target_enemy_id=foe_id or ((attack_targets or {}).get(character_id or "") if attack_targets else None),
                show_rolls=show_rolls,
            )
        elif action == "spend_torch":
            self._spend_torch(session, character_id, show_rolls=show_rolls)
        elif action == "resolve_fallen_transfer":
            self._resolve_fallen_transfer(
                session,
                to_character_id=target_character_id,
                kind=fallen_transfer_kind,
            )
        elif action == "resolve_free_slaves":
            from .monster_combat_hooks import apply_free_slaves_choice

            apply_free_slaves_choice(
                self,
                session,
                accept=free_slaves_choice == "free",
                show_rolls=show_rolls,
            )
        elif action == "claim_treasure":
            self._claim_treasure(session)
        elif action == "set_marching_order":
            self._set_marching_order(session, character_id, marching_order)
        elif action == "xp_roll":
            self._xp_roll(
                session,
                character_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
                new_spell=spell_name,
                advancement_fork=advancement_fork,
                expert_skill_id=expert_skill_id,
                expert_skill_target=expert_skill_target,
                heroic_skill_id=heroic_skill_id,
                legendary_skill_id=legendary_skill_id,
                heroic_skill_target=heroic_skill_target,
            )
        elif action == "bank_xp_roll":
            self._bank_xp_roll(session, character_id)
        elif action == "spend_banked_xp":
            self._spend_banked_xp(
                session,
                character_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
                new_spell=spell_name,
                advancement_fork=advancement_fork,
                expert_skill_id=expert_skill_id,
                expert_skill_target=expert_skill_target,
                heroic_skill_id=heroic_skill_id,
                legendary_skill_id=legendary_skill_id,
                heroic_skill_target=heroic_skill_target,
            )
        elif action == "buy_healing":
            self._buy_healing(session, character_id, show_rolls=show_rolls)
        elif action == "buy_alchemist":
            self._buy_alchemist(session, character_id, alchemist_item, show_rolls=show_rolls)
        elif action == "use_potion":
            self._use_potion(session, character_id, item_name, show_rolls=show_rolls)
        elif action == "use_holy_water":
            self._use_holy_water(
                session,
                character_id,
                item_name,
                target_enemy_id=(attack_targets or {}).get(character_id or "") if attack_targets else None,
                show_rolls=show_rolls,
            )
        elif action == "use_lantern_oil":
            self._use_lantern_oil(
                session,
                character_id,
                item_name,
                target_enemy_id=(attack_targets or {}).get(character_id or "") if attack_targets else None,
                show_rolls=show_rolls,
            )
        elif action == "use_mushroom":
            self._use_mushroom(
                session,
                character_id,
                item_name,
                target_enemy_id=(attack_targets or {}).get(character_id or "") if attack_targets else foe_id,
                show_rolls=show_rolls,
            )
        elif action == "eat_food_ration":
            self._eat_food_ration(session, character_id)
        elif action == "feed_hungry_heroes":
            self._feed_hungry_heroes(session, feed_character_ids)
        elif action == "assign_milestone":
            self._assign_milestone(session, character_id, milestone_id)
        elif action == "hire_retainer":
            from .hirelings import hire_retainer

            session.log.extend(
                hire_retainer(
                    session,
                    retainer_type or "",
                    assigned_character_id=target_character_id,
                    marching_order=hireling_marching_order,
                )
            )
        elif action == "dismiss_hireling":
            from .hirelings import dismiss_hireling

            session.log.extend(dismiss_hireling(session, hireling_id))
        elif action == "assign_hireling":
            from .hirelings import set_hireling_assignment

            session.log.extend(set_hireling_assignment(session, hireling_id, target_character_id))
        elif action == "set_hireling_marching_order":
            from .hirelings import set_hireling_marching_order

            session.log.extend(set_hireling_marching_order(session, hireling_id, hireling_marching_order))
        elif action == "pay_hireling_treasure_share":
            from .hirelings import pay_hireling_treasure_share

            session.log.extend(pay_hireling_treasure_share(session, hireling_id))
        elif action == "resurrect_hireling":
            from .hirelings import resurrect_hireling

            session.log.extend(resurrect_hireling(session, hireling_id))
        elif action == "use_professional_service":
            from .hirelings import use_professional_service

            session.log.extend(
                use_professional_service(
                    session,
                    professional_id or "",
                    character_id=target_character_id or character_id,
                    item_name=item_name,
                )
            )
        elif action == "use_trained_professional_skill":
            from .courtship_professional_skills import (
                use_trained_herbalist,
                use_trained_poison_expert,
                use_trained_surgeon_heal,
            )

            skill_key = (trained_professional_skill or "").strip().lower()
            provider_id = professional_provider_id or character_id
            if skill_key == "surgeon_heal":
                session.log.extend(use_trained_surgeon_heal(session, provider_id))
            elif skill_key == "herbalist_buff":
                session.log.extend(use_trained_herbalist(session, provider_id))
            elif skill_key == "poison_coat":
                session.log.extend(
                    use_trained_poison_expert(
                        session,
                        provider_id,
                        target_character_id=target_character_id,
                        item_name=item_name,
                    )
                )
            else:
                session.log.append("Choose a trained professional skill to use.")
        elif action == "commission_alchemist":
            from .alchemist_potions import commission_alchemist

            session.log.extend(
                commission_alchemist(
                    session,
                    potion_id=alchemist_potion_id or "",
                    character_id=target_character_id or character_id,
                    show_rolls=show_rolls,
                )
            )
        elif action == "use_hireling_ability":
            self._use_hireling_ability(
                session,
                hireling_id,
                hireling_ability,
                character_id=target_character_id or character_id,
                item_name=item_name,
                gold_amount=gold_amount,
                show_rolls=show_rolls,
            )
        elif action == "apply_silversmith_coating":
            from .hirelings import apply_silversmith_coating

            session.log.extend(
                apply_silversmith_coating(
                    session,
                    item_name=item_name,
                    character_id=target_character_id or character_id,
                )
            )
        elif action == "apply_poison_expert_coating":
            from .poison_expert import apply_poison_expert_coating

            session.log.extend(
                apply_poison_expert_coating(
                    session,
                    item_name=item_name,
                    character_id=target_character_id or character_id,
                )
            )
        elif action == "use_fortune_reroll":
            from .hirelings import use_fortune_reroll

            session.log.extend(
                use_fortune_reroll(
                    session,
                    target_character_id or character_id,
                    roll_value=fortune_roll_value,
                )
            )
        elif action == "bind_scroll_librarian":
            self._bind_scroll_librarian(session, character_id, scroll_librarian_spell)
        elif action == "craft_gem_collector_jewelry":
            self._craft_gem_collector_jewelry(session, character_id)
        elif action == "create_panoplia":
            self._create_panoplia(session, character_id)
        elif action == "use_panoplia_favor":
            self._use_panoplia_favor(session, character_id, panoplia_favor_kind)
        elif action == "pay_thrice_blessed_sacrifice":
            self._pay_thrice_blessed_sacrifice(session, character_id)
        elif action == "use_acid_vial":
            self._use_acid_vial(
                session,
                character_id,
                item_name,
                target_enemy_id=(attack_targets or {}).get(character_id or "") if attack_targets else None,
                show_rolls=show_rolls,
            )
        elif action == "use_arrow_of_slaying":
            self._use_arrow_of_slaying(
                session,
                character_id,
                item_name,
                target_enemy_id=(attack_targets or {}).get(character_id or "") if attack_targets else None,
                show_rolls=show_rolls,
            )
        elif action == "use_bandage":
            self._use_bandage(
                session,
                character_id,
                target_character_id=target_character_id,
                show_rolls=show_rolls,
            )
        elif action == "accept_quest":
            self._accept_quest(session, show_rolls=show_rolls)
        elif action == "refuse_quest":
            self._refuse_quest(session)
        elif action == "claim_quest_reward":
            self._claim_quest_reward(session, show_rolls=show_rolls)
        elif action == "old_school_level_up":
            self._old_school_level_up(session, character_id, show_rolls=show_rolls, new_spell=spell_name)
        elif action == "pick_level_up_spell":
            self._pick_level_up_spell(session, character_id, spell_name)
        elif action == "slower_xp_spend":
            self._slower_xp_spend(
                session,
                character_id,
                xp_spent=xp_spent,
                show_rolls=show_rolls,
                explain_math=explain_math,
                new_spell=spell_name,
                advancement_fork=advancement_fork,
                expert_skill_id=expert_skill_id,
                expert_skill_target=expert_skill_target,
                heroic_skill_id=heroic_skill_id,
                legendary_skill_id=legendary_skill_id,
                heroic_skill_target=heroic_skill_target,
            )
        elif action == "enter_tier_training":
            self._enter_tier_training(
                session,
                character_id,
                tier=tier_training,
                use_xp=use_xp_for_tier,
                show_rolls=show_rolls,
            )
        elif action == "transfer_item":
            self._transfer_item(session, character_id, target_character_id, item_name)
        elif action == "transfer_gold":
            self._transfer_gold(session, character_id, target_character_id, gold_amount)
        elif action == "deposit_bank_gold":
            self._deposit_bank_gold(session, character_id, gold_amount)
        elif action == "withdraw_bank_gold":
            self._withdraw_bank_gold(session, character_id, gold_amount)
        elif action == "deposit_party_bank_gold":
            self._deposit_party_bank_gold(session)
        elif action == "set_default_weapon":
            self._set_default_weapon(session, character_id, item_name, weapon_kind=weapon_kind)
        elif action == "swap_weapon":
            self._swap_weapon(session, character_id, item_name, show_rolls=show_rolls)
        elif action == "surgeon_burn_scroll":
            self._surgeon_burn_scroll(
                session,
                hireling_id,
                character_id,
                spell_name,
                professional_provider_id=professional_provider_id,
                exit_id=exit_id,
                target_character_id=target_character_id,
                target_foe_id=foe_id,
                spell_target_mode=spell_target_mode,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "ready_spear_shield":
            self._ready_spear_shield(session, character_id)
        elif action == "carry_body":
            self._carry_body(session, character_id, target_character_id)
        elif action == "drop_body":
            self._drop_body(session)
        elif action == "attempt_resurrection":
            self._attempt_resurrection(session, target_character_id or character_id, show_rolls=show_rolls)
        elif action == "accept_fallen_loss":
            self._accept_fallen_loss(session, target_character_id or character_id)
        elif action == "treat_lycanthropy":
            self._treat_lycanthropy(session, character_id, show_rolls=show_rolls)
        elif action == "start_abyss_campaign_plot":
            self._start_abyss_campaign_plot(
                session,
                abyss_plot_choice,
                character_id,
                show_rolls=show_rolls,
            )
        elif action == "abyss_plot_contribute_gold":
            self._abyss_plot_contribute_gold(session, gold_amount)
        elif action == "abyss_plot_take_artifact_piece":
            self._abyss_plot_take_artifact_piece(session)
        elif action == "abyss_plot_spend_clues":
            self._abyss_plot_spend_clues(session)
        elif action == "abyss_plot_transfer_artifact":
            self._abyss_plot_transfer_artifact(session, character_id)
        elif action == "abyss_plot_resolve_finale":
            self._abyss_plot_resolve_finale(session)
        elif action == "hunt_vampire_sire":
            self._hunt_vampire_sire(session)
        elif action == "use_class_ability":
            self._use_class_ability(
                session,
                character_id,
                class_ability,
                target_character_id=target_character_id,
                foe_id=foe_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
                exit_id=exit_id,
                gadget_points=gadget_points,
                panache_spend=panache_spend,
                search_choice=search_choice,
                item_name=item_name,
                gold_amount=gold_amount,
            )
        elif action == "detach_heroes":
            session.log.extend(detach_heroes(session, list(detached_character_ids or [])))
        elif action == "reattach_heroes":
            session.log.extend(
                reattach_heroes(session, list(detached_character_ids) if detached_character_ids else None)
            )
            # If the active group was just dissolved, reset navigation focus to main.
            if session.active_group_tile_id and not any(
                g.tile_id == session.active_group_tile_id for g in session.detached_groups
            ):
                session.active_group_tile_id = None
        elif action == "set_active_group":
            session.log.extend(set_active_group(session, detached_tile_id))
        elif action == "call_of_the_wild":
            self._call_of_the_wild(session, character_id, show_rolls=show_rolls)
        elif action == "scout_ahead":
            if character_id and exit_id:
                self._explore(
                    session,
                    exit_id=exit_id,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    scout_id=character_id,
                )
            elif character_id:
                session.log.extend(scout_ahead(session, character_id))
            else:
                session.log.append("Choose a hero to scout ahead.")
        elif action == "detached_combat_round":
            self._detached_combat_round(
                session,
                detached_tile_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "scout_reaction":
            self._scout_reaction(
                session,
                detached_tile_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
                reaction_adjust=reaction_adjust,
            )
        elif action == "rush_to_scout":
            self._rush_to_scout(session, detached_tile_id, show_rolls=show_rolls)
        elif action == "scout_flee_back":
            self._scout_flee_back(
                session,
                detached_tile_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif action == "bank_training_focus":
            self._bank_training_focus(session, character_id)
        elif action == "find_captive_hideout":
            self._find_captive_hideout(session, character_id, show_rolls=show_rolls)
        elif action == "pay_captive_ransom":
            self._pay_captive_ransom(session, show_rolls=show_rolls)
        else:
            session.log.append(f"Unknown action: {action}.")

        if action in turn_actions:
            self._advance_call_of_the_wild(session)

        return self._touch(session)

    def _call_of_the_wild(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Call of the Wild is handled during exploration.")
            return
        druid = next((member for member in session.party if member.character_id == character_id), None)
        if druid is None:
            session.log.append("Choose a druid for Call of the Wild.")
            return
        if druid.class_id.lower() != "druid" or druid.level < 10:
            session.log.append("Call of the Wild applies to druids of Level 10 or higher.")
            return
        if druid.current_life <= 0:
            session.log.append(f"{druid.name} cannot answer Call of the Wild while down.")
            return
        if druid.character_id in session.druid_call_of_wild_used:
            session.log.append(f"{druid.name} has already answered Call of the Wild this adventure.")
            return
        current_tile = self._current_tile(session)
        available_here = {member.character_id for member in present_party(session, current_tile.id)}
        if druid.character_id not in available_here:
            session.log.append(f"{druid.name} must be with the main group to answer Call of the Wild.")
            return
        if len(available_here) <= 1:
            session.log.append("At least one hero must remain with the main group.")
            return
        turns = roll_d6()
        if show_rolls:
            session.log.append(f"Call of the Wild duration: d6 = {turns} turn(s).")
        session.druid_call_of_wild_turns[druid.character_id] = turns
        session.druid_call_of_wild_used.append(druid.character_id)
        for group in session.detached_groups:
            if druid.character_id in group.character_ids:
                group.character_ids = [cid for cid in group.character_ids if cid != druid.character_id]
        session.detached_groups = [group for group in session.detached_groups if group.character_ids]
        existing = next(
            (
                group
                for group in session.detached_groups
                if group.tile_id == current_tile.id and group.reason == "call_of_the_wild"
            ),
            None,
        )
        if existing is None:
            session.detached_groups.append(
                DetachedGroupState(
                    tile_id=current_tile.id,
                    character_ids=[druid.character_id],
                    reason="call_of_the_wild",
                )
            )
        elif druid.character_id not in existing.character_ids:
            existing.character_ids.append(druid.character_id)
        session.log.append(
            f"{druid.name} leaves the party to commune with nature for {turns} turn(s)."
        )

    def _advance_call_of_the_wild(self, session: SessionState) -> None:
        if not session.druid_call_of_wild_turns:
            return
        updated: dict[str, int] = {}
        returned: list[str] = []
        for character_id, turns in session.druid_call_of_wild_turns.items():
            remaining = max(0, int(turns) - 1)
            member = next((item for item in session.party if item.character_id == character_id), None)
            name = member.name if member else character_id
            if remaining > 0:
                updated[character_id] = remaining
                session.log.append(f"Call of the Wild: {name} returns in {remaining} turn(s).")
            else:
                returned.append(name)
        session.druid_call_of_wild_turns = updated
        for name in returned:
            session.log.append(f"Call of the Wild: {name} may now rejoin the party.")

    def _explore(
        self,
        session: SessionState,
        exit_id: str | None = None,
        direction: str | None = None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        dungeon_exit_intent: str | None = None,
        scout_id: str | None = None,
    ) -> None:
        detached_move = is_active_detached(session)
        current = self._active_tile(session)
        if session.pending_search_reward_tile_id:
            session.log.append("Choose the pending Search reward before leaving this location.")
            return
        if exit_id:
            exit_state = next((item for item in current.exits if item.id == exit_id), None)
            if exit_state is None:
                session.log.append("That exit is not available from this map element.")
                return
        elif direction:
            exit_state = next((item for item in current.exits if item.direction == direction), None)
            if exit_state is None:
                session.log.append(f"There is no exit to the {direction}.")
                return
        else:
            exit_state = next((item for item in current.exits if item.status == "unexplored"), None)

        if exit_state is None:
            exit_state = self._add_emergency_exit(session, current)
            if exit_state is None:
                session.log.append("There are no open ways forward from this location.")
                return

        if session.mode != "exploration":
            if not exit_state.dungeon_exit:
                session.log.append("Exploration is blocked until the current encounter is resolved.")
                return
            if any(enemy.life > 0 for enemy in current.enemies):
                self._flee(session, show_rolls=show_rolls, explain_math=explain_math)
                if session.mode == "combat":
                    session.log.append("You must break contact before leaving the dungeon.")
                    return

        if exit_state.status == "blocked":
            session.log.append(f"The {exit_state.direction} exit is blocked.")
            return

        if exit_state.dungeon_exit:
            if detached_move:
                session.log.append("The detached group cannot exit the dungeon independently. Regroup at the entrance first.")
                return
            exit_state.status = "open"
            if exit_state.kind == "door":
                exit_state.door_open = True
            delivered_body = bool(session.carried_body_id)
            if delivered_body:
                session.log.extend(
                    deliver_carried_body_outside(
                        session,
                        servant_owner_ids=self._servant_owner_ids(session),
                    )
                )
            fallen = self._fallen_in_dungeon(session)
            if fallen:
                self._retreat_from_dungeon(session, fallen, show_rolls=show_rolls)
            elif session.fallen_outside_character_ids:
                self._camp_outside_with_recovery(session)
            elif delivered_body:
                session.log.append("The party regroups at the entrance and may continue the adventure.")
            elif dungeon_exit_intent == "return":
                self._camp_outside_to_return(session)
            else:
                self._complete_dungeon(session)
            return

        if not detached_move and session.camped_outside and current.content_key == "entrance":
            session.log.append("Return to the dungeon before moving deeper from the entrance.")
            return

        if exit_state.kind == "door" and not exit_state.door_open:
            self._inherit_connection_from_reciprocal(session, current, exit_state)
        if (
            current.content_key == "entrance"
            and not exit_state.dungeon_exit
            and exit_state.kind == "door"
            and not exit_state.door_open
            and exit_state.destination_tile_id is None
        ):
            self._open_entrance_threshold(session, exit_state, show_rolls=show_rolls)
        if exit_state.kind == "door" and not exit_state.door_open:
            session.log.append("The door is closed. Open it before moving through.")
            return

        if not fd_validate_river_exit_travel(
            self, session, current, exit_state, show_rolls=show_rolls
        ):
            return

        _, destination = self._exit_edge(current, exit_state)
        if destination in self._occupied_cells(current):
            session.log.append(
                "That exit points back into the same map element. Move the exit marker to an outside edge, "
                "or mark it as the dungeon exit if it leaves the dungeon."
            )
            return
        existing = (
            self._tile_by_id(session, exit_state.destination_tile_id)
            if exit_state.destination_tile_id
            else self._tile_occupying(session, *destination, exclude_tile_id=current.id)
        )
        if existing and existing.id == current.id:
            session.log.append(
                "That exit resolves to the current map element. Check the map element metadata before exploring it."
            )
            return
        # Clear any stale old-style scout-lag flag on every move.
        session.scout_lag_character_id = None
        exit_state.status = "open"
        if existing:
            exit_state.destination_tile_id = existing.id
            self._set_reciprocal_exit(existing, current, exit_state)
            entry_exit = self._reciprocal_exit_on_tile(
                existing,
                current.id,
                direction=OPPOSITE[exit_state.direction],
            )
            self._persist_open_connection(session, current, exit_state)
            if scout_id:
                self._do_scout_move(session, scout_id, existing, current, show_rolls=show_rolls)
                return
            from .heroic_skill_effects import mark_tile_visited

            was_visited = existing.id in session.visited_tile_ids
            mark_tile_visited(session, existing.id)
            self._fd_on_area_entered(session, existing, show_rolls=show_rolls)
            if was_visited:
                self._maybe_trigger_alchemist_revisit_trap(
                    session,
                    existing,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
            self._refresh_tile_connections(session, existing)
            if detached_move:
                for group in session.detached_groups:
                    if group.tile_id == current.id:
                        group.tile_id = existing.id
                session.active_group_tile_id = existing.id
                session.log.append(f"The detached group moves {exit_state.direction} to {existing.title}.")
                if any(enemy.life > 0 for enemy in existing.enemies):
                    if existing.id not in session.detached_wandering_pending:
                        session.detached_wandering_pending.append(existing.id)
                    session.log.append("Enemies present! Use 'Fight detached round' to resolve the encounter.")
            else:
                session.map_state.current_tile_id = existing.id
                session.current_tile_entry_exit_id = entry_exit.id if entry_exit else None
                self._sync_session_environment_from_tile(session, existing)
                self._apply_session_tile_catalog(session, existing)
                if is_fd_ruleset(session) and session_tile_catalog(session) == "forsaken_depths_rivers":
                    self._fd_on_river_stretch_entered(session, existing, show_rolls=show_rolls)
                if existing.content_key == "entrance":
                    self._initialize_outside_entrance(existing)
                if session.camped_outside and current.content_key == "entrance":
                    session.camped_outside = False
                    session.log.append("The party re-enters the dungeon.")
                session.log.append(f"The party moves {exit_state.direction} to {existing.title}.")
                self._ensure_capture_hideout_reaction(session, existing, show_rolls=show_rolls)
                if session.adventure_type == "imported":
                    session.log.append(existing.description)
                    fire_imported_triggers(self, session, existing, "on_enter", show_rolls=show_rolls)
                tag_finale_started = self._maybe_trigger_tag_underground_caves_finale(
                    session,
                    existing,
                    show_rolls=show_rolls,
                )
                self._tick_phoenix_mushrooms(session)
                self._tick_toxic_spores(session)
                self._tick_abyss_room_entry_afflictions(session, existing, show_rolls=show_rolls)
                self._tick_teleport_enemy_returns(session, reason="movement")
                if exit_state.acute_hearing_cleared and existing.id not in session.expert_acute_hearing_tiles:
                    session.expert_acute_hearing_tiles.append(existing.id)
                session.log.extend(maybe_summon_on_wilderness_entry(session, existing))
                self._maybe_wandering_on_backtrack(session, existing, show_rolls=show_rolls)
                self._maybe_resume_detached_encounter(session, existing, show_rolls=show_rolls)
                if (
                    not tag_finale_started
                    and session.mode == "exploration"
                    and any(enemy.life > 0 for enemy in existing.enemies)
                ):
                    if self._hideout_skips_auto_combat(session, existing):
                        session.log.append(
                            "The hideout guards may accept ransom. Pay ransom or start combat to rescue your comrades."
                        )
                    else:
                        self._announce_encounter(session, existing, show_rolls=show_rolls)
            return
        if session.adventure_type == "imported":
            session.log.append("That exit is not connected in this authored adventure.")
            return
        from .forsaken_depths_side_sheet import fd_side_sheet_can_expand

        if (
            session.fd_side_sheet_active
            and current.fd_side_sheet
            and not fd_side_sheet_can_expand(session)
        ):
            exit_state.status = "unexplored"
            session.log.append(
                "The side dungeon room budget is exhausted — return to the main map (FD p.60)."
            )
            return
        if is_fd_ruleset(session) and session_tile_catalog(session) == "forsaken_depths":
            session.tile_catalog = "forsaken_depths"
        if should_enter_river_from_etr(session, current, generating_new_tile=True):
            session.tile_catalog = "forsaken_depths_rivers"
            session.log.append(
                "ETR — the party enters the underground river (Four Against the Forsaken Depths p.32)."
            )
            self._fd_ensure_river_type(session, show_rolls=show_rolls)
            fd_acquire_boat_at_etr(session, current, show_rolls=show_rolls)
        cap = unlimited_map_element_cap(session)
        if cap is not None and len(session.map_state.tiles) >= cap:
            exit_state.status = "unexplored"
            session.log.append(
                f"The dungeon has reached its maximum extent ({cap} map elements). "
                "Seek the Final Boss in areas already explored."
            )
            return
        if cap is not None and len(session.map_state.tiles) + 1 >= cap and not dungeon_has_final_boss(session):
            session.log.append(
                f"This is the last map element the dungeon can hold ({cap} total). "
                "Any major foe encountered here becomes the Final Boss if none is already designated."
            )
        new_tile = self._generate_tile(
            session=session,
            origin=current,
            origin_exit=exit_state,
            hcl=self._highest_character_level(session.party),
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if new_tile is None:
            exit_state.status = "unexplored"
            exit_state.destination_tile_id = None
            session.log.append(
                "No legal placement is available for that map element without overlap. "
                "Even after truncation there is no usable entry square."
            )
            return
        if session.fd_side_sheet_active:
            new_tile.fd_side_sheet = True
        exit_state.destination_tile_id = new_tile.id
        session.map_state.tiles.append(new_tile)
        self._strip_neighbor_origin_overlap(current, new_tile, exit_state)
        entry_exit = self._set_reciprocal_exit(new_tile, current, exit_state)
        self._connect_reserved_exits_to_neighbor(session, new_tile, current, exit_state)
        for tile in session.map_state.tiles:
            if tile.id != new_tile.id:
                self._clip_origin_visible_for_neighbor(tile, new_tile)
        self._persist_open_connection(session, current, exit_state)
        from .heroic_skill_effects import mark_tile_visited

        mark_tile_visited(session, new_tile.id)
        self._maybe_fd_revelation_preview_room(session, new_tile, show_rolls=show_rolls)
        if scout_id:
            # Party stays; tile is generated and features prepared before stealth roll.
            session.log.append(f"Scouting {new_tile.title}: {new_tile.description}")
            self._prepare_tile_features(session, new_tile, show_rolls=show_rolls, explain_math=explain_math)
            self._do_scout_move(session, scout_id, new_tile, current, show_rolls=show_rolls)
            return
        if not detached_move:
            session.map_state.current_tile_id = new_tile.id
            session.current_tile_entry_exit_id = entry_exit.id
            self._sync_session_environment_from_tile(session, new_tile)
        self._prepare_tile_features(session, new_tile, show_rolls=show_rolls, explain_math=explain_math)
        if detached_move:
            for group in session.detached_groups:
                if group.tile_id == current.id:
                    group.tile_id = new_tile.id
            session.active_group_tile_id = new_tile.id
            session.log.append(f"The detached group enters {new_tile.title}: {new_tile.description}")
            if any(enemy.life > 0 for enemy in new_tile.enemies):
                if new_tile.id not in session.detached_wandering_pending:
                    session.detached_wandering_pending.append(new_tile.id)
                session.log.append("Enemies present! Use 'Fight detached round' to resolve the encounter.")
        else:
            if session.camped_outside and current.content_key == "entrance":
                session.camped_outside = False
                session.log.append("The party re-enters the dungeon.")
            session.log.append(f"Entered {new_tile.title}: {new_tile.description}")
            from .hunger import tick_party_hunger

            tick_party_hunger(session, [pc for pc in session.party if pc.current_life > 0], log=session.log)
            tag_finale_started = self._maybe_trigger_tag_underground_caves_finale(
                session,
                new_tile,
                show_rolls=show_rolls,
            )
            self._tick_phoenix_mushrooms(session)
            self._tick_toxic_spores(session)
            self._tick_abyss_room_entry_afflictions(session, new_tile, show_rolls=show_rolls)
            self._tick_teleport_enemy_returns(session, reason="movement")
            if exit_state.acute_hearing_cleared and new_tile.id not in session.expert_acute_hearing_tiles:
                session.expert_acute_hearing_tiles.append(new_tile.id)
            session.log.extend(maybe_summon_on_wilderness_entry(session, new_tile))
            self._maybe_resume_detached_encounter(session, new_tile, show_rolls=show_rolls)
            self._ensure_capture_hideout_reaction(session, new_tile, show_rolls=show_rolls)
            if not tag_finale_started and new_tile.enemies and session.mode == "exploration":
                self._announce_encounter(session, new_tile, show_rolls=show_rolls)
            if is_fd_ruleset(session) and session_tile_catalog(session) == "forsaken_depths_rivers":
                self._fd_on_river_stretch_entered(session, new_tile, show_rolls=show_rolls)
            self._fd_on_area_entered(session, new_tile, show_rolls=show_rolls)

    def _fd_on_area_entered(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        from .forsaken_depths_events import tick_fd_flood_bow_penalty
        from .forsaken_depths_map import is_fd_ruleset
        from .forsaken_depths_quest import fd_quest_on_new_tile_entered, tick_fd_quest_on_area_enter

        if not is_fd_ruleset(session):
            return
        tick_fd_flood_bow_penalty(session, show_rolls=show_rolls)
        tick_fd_quest_on_area_enter(self, session, tile, show_rolls=show_rolls)
        fd_quest_on_new_tile_entered(self, session, tile, show_rolls=show_rolls)
        apply_fd_dungeon_room_codes_on_enter(self, session, tile, show_rolls=show_rolls)

    def _tag_cave_room_count_state(self, session: SessionState) -> dict | None:
        quest = session.active_quest
        if quest is None or quest.completed:
            return None
        state = dict(quest.tag_procedure_state or {})
        recorded = state.get("map_cave_room_count")
        if not isinstance(recorded, dict) or not recorded.get("completed"):
            return None
        try:
            target = int(recorded.get("total") or 0)
        except (TypeError, ValueError):
            return None
        if target <= 0:
            return None
        recorded["total"] = target
        return {"state": state, "recorded": recorded, "target": target}

    def _tag_cave_rooms_explored(self, session: SessionState) -> int:
        return sum(
            1
            for tile in session.map_state.tiles
            if tile.tile_type == "room" and tile.content_key != "entrance"
        )

    def _maybe_trigger_tag_underground_caves_finale(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> bool:
        cave_state = self._tag_cave_room_count_state(session)
        if cave_state is None or tile.tile_type != "room" or tile.content_key == "entrance":
            return False
        state = cave_state["state"]
        recorded = cave_state["recorded"]
        target = cave_state["target"]
        if recorded.get("final_room_tile_id"):
            return False
        rooms_seen = self._tag_cave_rooms_explored(session)
        recorded["rooms_seen"] = rooms_seen
        if rooms_seen < target:
            remaining = target - rooms_seen
            state["map_cave_room_count"] = recorded
            state["next_action"] = (
                f"Underground caves progress: room {rooms_seen}/{target}. "
                f"Explore {remaining} more room{'s' if remaining != 1 else ''}; "
                "the target room becomes the final Boss room automatically."
            )
            if session.active_quest is not None:
                session.active_quest.tag_procedure_state = state
            session.log.append(f"TAG Underground caves progress: room {rooms_seen}/{target}.")
            return False

        boss = self._roll_enemy(
            session,
            "boss",
            self._highest_character_level(session.party),
        )[0]
        boss.life += 2
        boss.max_life += 2
        for tag in ("final_boss", "tag_treasure_map_finale"):
            if tag not in boss.tags:
                boss.tags.append(tag)
        tile.enemies = [boss]
        tile.defeated_enemies = []
        tile.resolved = False
        tile.content_key = "tag_treasure_map_final_boss"
        tile.final_boss_treasure = True
        tile.treasure_claimed = False
        tile.treasure_summary = None
        tile.treasure_gold = 0
        tile.treasure_items = []
        tile.pending_treasure_choice = None
        session.final_boss_designated = True
        recorded["rooms_seen"] = rooms_seen
        recorded["final_room_tile_id"] = tile.id
        recorded["final_boss_name"] = boss.name
        recorded["finale_spawned"] = True
        state["map_cave_room_count"] = recorded
        state["next_action"] = (
            f"Underground caves target reached: room {rooms_seen}/{target} is the map destination. "
            f"Defeat {boss.name}; the app will mark the Treasure Map objective complete after combat."
        )
        if session.active_quest is not None:
            session.active_quest.tag_procedure_state = state
        blocked = 0
        for exit_state in tile.exits:
            if not exit_state.destination_tile_id and not exit_state.dungeon_exit:
                exit_state.status = "blocked"
                blocked += 1
        session.log.append(
            f"TAG Underground caves target reached: room {rooms_seen}/{target}. "
            f"{boss.name} is the Treasure Map final Boss (+2 Life)."
        )
        if blocked:
            session.log.append(
                f"TAG Underground caves: {blocked} unopened exit{'s' if blocked != 1 else ''} "
                "from the destination room become dead ends."
            )
        self._begin_combat(
            session,
            "The Treasure Map destination is found!",
            show_rolls=show_rolls,
            allow_final_boss_check=False,
            tile=tile,
        )
        return True

    def _maybe_fd_revelation_preview_room(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        from .forsaken_depths_revelation import consume_fd_revelation_preview_explore

        foe_summary = self._format_living_foes(tile.enemies) if tile.enemies else ""
        consume_fd_revelation_preview_explore(
            session,
            tile,
            show_rolls=show_rolls,
            foe_summary=foe_summary,
        )

    def _do_scout_move(
        self,
        session: SessionState,
        scout_id: str,
        dest_tile,
        origin_tile,
        *,
        show_rolls: bool = True,
    ) -> None:
        """Detach the scout at *dest_tile* (party stays at *origin_tile*) and
        resolve a Stealth Save.

        Success (roll > foe level): scout is at the destination unseen; the party
        may follow normally or the scout may retreat (reattach).

        Failure (roll ≤ foe level): scout is spotted and must fight alone for one
        round — the tile is added to ``detached_wandering_pending`` so the
        'Detached combat' panel appears.
        """
        from ..schemas import DetachedGroupState

        scout = next((m for m in session.party if m.character_id == scout_id), None)
        if scout is None or scout.current_life <= 0:
            return

        # Detach scout at the destination tile.
        existing_group = next(
            (g for g in session.detached_groups if g.tile_id == dest_tile.id), None
        )
        if existing_group is None:
            session.detached_groups.append(
                DetachedGroupState(tile_id=dest_tile.id, character_ids=[scout_id], reason="scout")
            )
        elif scout_id not in existing_group.character_ids:
            existing_group.character_ids.append(scout_id)

        # Remove scout from any detached group at the origin tile (clean up).
        for group in session.detached_groups:
            if group.tile_id == origin_tile.id and scout_id in group.character_ids:
                group.character_ids.remove(scout_id)
        session.detached_groups = [g for g in session.detached_groups if g.character_ids]

        living_foes = [e for e in (dest_tile.enemies or []) if e.life > 0]
        if not living_foes:
            session.log.append(
                f"{scout.name} scouts {dest_tile.title} — no enemies present. "
                f"The party may follow or {scout.name} may retreat."
            )
            return

        self._mark_major_foe_encounter(
            session,
            dest_tile,
            show_rolls=show_rolls,
            allow_final_boss_check=True,
        )
        foe_summary = self._format_living_foes(living_foes)
        if foe_summary:
            session.log.append(f"{scout.name} sees: {foe_summary}.")

        target = max(e.level for e in living_foes)
        mod = stealth_modifier(scout, session, dest_tile)
        roll = roll_d6()
        total = roll + mod
        mod_str = f"+{mod}" if mod > 0 else str(mod) if mod < 0 else "±0"

        if show_rolls:
            session.log.append(
                f"{scout.name} Stealth Save: d6={roll} {mod_str} = {total} vs L{target}."
            )

        if total > target:
            session.log.append(
                f"Success — {scout.name} enters {dest_tile.title} unseen. "
                f"The party may follow or {scout.name} may retreat via Rejoin."
            )
        else:
            session.log.append(
                f"Spotted! {scout.name} must fight alone for one round at {dest_tile.title}. "
                f"Use 'Check scout reaction' or 'Fight scout round' in the party sheet; then the party may rush in or the scout may flee back."
            )
            session.scout_encounter_origin_tile_ids[dest_tile.id] = origin_tile.id
            if dest_tile.id not in session.detached_wandering_pending:
                session.detached_wandering_pending.append(dest_tile.id)

    def _search(
        self,
        session: SessionState,
        *,
        search_choice: str | None = None,
        character_id: str | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Search after the encounter is resolved.")
            return
        tile = self._current_tile(session)
        if session.pending_search_reward_tile_id:
            if session.pending_search_reward_tile_id != tile.id:
                session.log.append("Return to the searched location and choose its pending Search reward.")
                return
            if not search_choice:
                session.log.append("Search found something. Choose Hidden Treasure, Secret Door, Secret Passage, or 1 Clue.")
                return
            self._apply_search_choice(
                session,
                tile,
                search_choice,
                character_id=character_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            session.pending_search_reward_tile_id = None
            session.pending_search_reroll_tile_id = None
            session.pending_pole_search_reroll_tile_id = None
            return
        if search_choice:
            session.log.append("Roll Search first; choose a reward only if the roll finds something.")
            return
        if tile.searched:
            session.log.append("This location has already been searched.")
            return

        tile.searched = True
        from .forsaken_depths_revelation import consume_fd_revelation_auto_search

        if consume_fd_revelation_auto_search(session, show_rolls=show_rolls):
            session.pending_search_reward_tile_id = tile.id
            session.log.append(
                "Revelation: automatic search success — choose Hidden Treasure, Secret Door, Secret Passage, or 1 Clue."
            )
            session.pending_search_reroll_tile_id = tile.id
            return
        if session.adventure_type == "imported":
            fire_imported_triggers(self, session, tile, "on_search", show_rolls=show_rolls)
            session.log.append("Search complete.")
            return
        roll = roll_d6()
        effective_roll = roll - 1 if tile.tile_type == "corridor" else roll
        if show_rolls:
            if tile.tile_type == "corridor":
                session.log.append(f"Search roll: d6 = {roll} (corridor -1 = {effective_roll}).")
            else:
                session.log.append(f"Search roll: d6 = {roll}.")
        search_choice_key = None
        if search_choice == "clue":
            search_choice_key = "clue"
        elif search_choice in {"secret_door", "secret_passage"}:
            search_choice_key = "secret_door"
        effective_roll, search_notes = adjust_search_roll(
            session.party,
            effective_roll,
            choice=search_choice_key,
            session=session,
            environment=tile.environment,
            tile_id=tile.id,
        )
        session.log.extend(search_notes)
        if show_rolls and search_notes:
            session.log.append(f"Adjusted search roll: {effective_roll}.")
        if explain_math:
            session.log.append(f"Search table: {self.table_roller.search_table_summary()}.")
        outcome = self.table_roller.lookup_search(effective_roll)
        if outcome.effect == "wandering_monsters":
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)
        elif outcome.effect == "nothing":
            session.log.append(outcome.result or "The tile is really empty.")
        elif outcome.effect == "found_something":
            session.pending_search_reward_tile_id = tile.id
            session.log.append(
                outcome.result
                or "Search finds something. Choose Hidden Treasure, Secret Door, Secret Passage, or 1 Clue."
            )
            if session.courtship_enabled and not session.courtship_demesne_active:
                from .courtship_apothecary_brew import try_outdoor_ingredient_forage

                session.log.extend(
                    try_outdoor_ingredient_forage(session, session.party, show_rolls=show_rolls)
                )
        elif outcome.effect == "clue":
            self._grant_clue(session, tile, character_id=character_id)
        else:
            self._grant_hidden_treasure(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        session.pending_search_reroll_tile_id = tile.id
        if 2 <= effective_roll <= 4 and pole_carrier(session.party) is not None:
            session.pending_pole_search_reroll_tile_id = tile.id
            carrier = pole_carrier(session.party)
            session.log.append(
                f"{carrier.name}'s 10' pole allows rerolling this search result (2–4). Use Pole Search Reroll."
            )

    def _apply_search_choice(
        self,
        session: SessionState,
        tile: TileState,
        choice: str,
        *,
        character_id: str | None = None,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        labels = {
            "hidden_treasure": "hidden treasure",
            "secret_door": "a secret door",
            "secret_passage": "a secret passage",
            "clue": "1 Clue",
        }
        session.log.append(f"Search find: the party chooses {labels.get(choice, choice)}.")
        if choice == "hidden_treasure":
            self._grant_hidden_treasure(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        elif choice == "secret_door":
            self._reveal_secret_door(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        elif choice == "secret_passage":
            self._offer_secret_passage(session, tile, show_rolls=show_rolls)
        elif choice == "clue":
            self._grant_clue(session, tile, character_id=character_id)
        else:
            self._grant_hidden_treasure(session, tile, show_rolls=show_rolls, explain_math=explain_math)

    def _spawn_wandering_monsters(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        special_event: bool = False,
        combat_message: str | None = None,
        party_strikes_first: bool = False,
        foes_strike_first: bool = False,
        start_combat: bool = True,
    ) -> None:
        if self._consume_mycelial_warning(session, tile, "Wandering Monsters"):
            return
        if gremlin_protection_active(session, session.party):
            session.gremlin_wm_protection_pending = False
            session.log.append("Miners' Ointment or gremlin repellant wards off Wandering Monsters.")
            return
        hcl = self._highest_character_level(session.party)
        from .abyss_tables import is_abyss_profile

        abyss_profile = is_abyss_profile(session)
        if is_fd_ruleset(session) and not special_event:
            wandering = self.table_roller.roll_fd_wandering_monsters()
        else:
            wandering = self.table_roller.roll_wandering_monsters(special_event=special_event)
        if show_rolls:
            label = "Abyss Wandering Monsters" if abyss_profile and not special_event else (
                "Special event wandering" if special_event else "Wandering Monsters"
            )
            session.log.append(f"{label} table: d6 = {wandering.roll} -> {wandering.enemy_category}.")
        foe = self._roll_wandering_enemies(session, wandering.enemy_category, hcl)
        if not foe:
            session.log.append("Wandering Monsters were heard but none appeared.")
            return
        tile.enemies.extend(foe)
        self._resolve_event_foes(session, tile, show_rolls=show_rolls)
        tile.initial_enemy_count = len(tile.enemies)
        foe_summary = self._format_living_foes(foe)
        if foe_summary:
            session.log.append(f"Wandering foes: {foe_summary}.")
        if tile.tile_type == "corridor":
            tile.wandering_ambush = True
        if not start_combat:
            if tile.id not in session.detached_wandering_pending:
                session.detached_wandering_pending.append(tile.id)
            return
        self._begin_combat(
            session,
            combat_message or "Wandering Monsters attack!",
            show_rolls=show_rolls,
            allow_final_boss_check=False,
            party_strikes_first=party_strikes_first,
            foes_strike_first=foes_strike_first,
            tile=tile,
        )
        self._check_detached_wandering(session, show_rolls=show_rolls, exclude_tile_id=tile.id)

    def _check_detached_wandering(
        self,
        session: SessionState,
        *,
        show_rolls: bool,
        exclude_tile_id: str | None = None,
    ) -> None:
        triggered, logs = wandering_check_detached_groups(
            session,
            show_rolls=show_rolls,
            exclude_tile_id=exclude_tile_id,
        )
        session.log.extend(logs)
        for tile_id in triggered:
            tile = self._tile_by_id(session, tile_id)
            if tile is None:
                continue
            self._spawn_wandering_monsters(
                session,
                tile,
                show_rolls=show_rolls,
                start_combat=False,
                combat_message=f"Wandering Monsters attack the group at {tile.title}!",
            )

    def _maybe_resume_detached_encounter(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        if not any(enemy.life > 0 for enemy in tile.enemies):
            if tile.id in session.detached_wandering_pending:
                session.detached_wandering_pending.remove(tile.id)
            self._clear_detached_combat_state(session, tile.id)
            return
        if tile.id in session.detached_wandering_pending:
            if tile.id in session.scout_encounter_origin_tile_ids:
                self._rush_to_scout(session, tile.id, show_rolls=show_rolls)
                return
            session.detached_wandering_pending.remove(tile.id)
            self._clear_detached_combat_state(session, tile.id)
            self._begin_combat(
                session,
                "The left-behind group is fighting Wandering Monsters!",
                tile=tile,
                show_rolls=show_rolls,
            )
            return
        if session.mode == "exploration":
            self._announce_encounter(session, tile, show_rolls=show_rolls)

    def _clear_detached_combat_state(self, session: SessionState, tile_id: str) -> None:
        session.detached_combat_rounds.pop(tile_id, None)
        session.detached_missile_used_character_ids.pop(tile_id, None)
        session.scout_encounter_origin_tile_ids.pop(tile_id, None)
        session.scout_reaction_checked_tile_ids = [
            pending_id for pending_id in session.scout_reaction_checked_tile_ids if pending_id != tile_id
        ]
        session.detached_wandering_pending = [
            pending_id for pending_id in session.detached_wandering_pending if pending_id != tile_id
        ]

    def _detached_combat_round(
        self,
        session: SessionState,
        detached_tile_id: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Resolve the current encounter before handling detached combat.")
            return
        if not detached_tile_id:
            session.log.append("Choose a detached group fight to resolve.")
            return
        tile = self._tile_by_id(session, detached_tile_id)
        if tile is None:
            session.log.append("That detached combat location is no longer on the map.")
            self._clear_detached_combat_state(session, detached_tile_id)
            return
        if detached_tile_id not in session.detached_wandering_pending:
            session.log.append("There is no pending detached combat at that location.")
            return
        fighters = combat_party(session, tile.id)
        if not fighters:
            session.log.append(f"No living detached heroes remain at {tile.title}.")
            self._clear_detached_combat_state(session, tile.id)
            return
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append(f"The detached fight at {tile.title} is already over.")
            self._clear_detached_combat_state(session, tile.id)
            return

        round_index = max(0, int(session.detached_combat_rounds.get(tile.id, 0)))
        scout_encounter = tile.id in session.scout_encounter_origin_tile_ids
        if scout_encounter and round_index >= 1:
            session.log.append(
                "The scout has already held out for one round. Rush the party in, or have the scout flee back."
            )
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in fighters if pc.current_life > 0}
        missile_used = set(session.detached_missile_used_character_ids.get(tile.id, []))
        names = ", ".join(member.name for member in sorted(fighters, key=lambda item: item.marching_order))
        foes = self._format_living_foes([enemy for enemy in tile.enemies if enemy.life > 0])
        session.log.append(f"Detached combat at {tile.title}: {names} face {foes}.")

        combat_context = self._combat_context(session, tile)
        if mixed_encounter(tile.enemies):
            result = resolve_simultaneous_combat_round(
                fighters,
                tile.enemies,
                show_rolls=show_rolls,
                explain_math=explain_math,
                initial_minor_count=tile.initial_enemy_count or len(tile.enemies),
                context=combat_context,
                party_surprised=tile.wandering_ambush and round_index == 0,
                party_attacked_immediately=False,
                foes_strike_first=(tile.wandering_ambush or scout_encounter) and round_index == 0,
                subdual=False,
                encounter_round=round_index,
                missile_used=missile_used,
                attack_targets=None,
                attack_secondary_targets=None,
            )
        else:
            result = resolve_combat_round(
                fighters,
                tile.enemies,
                show_rolls=show_rolls,
                explain_math=explain_math,
                initial_minor_count=tile.initial_enemy_count or len(tile.enemies),
                context=combat_context,
                party_surprised=tile.wandering_ambush and round_index == 0,
                party_attacked_immediately=False,
                foes_strike_first=(tile.wandering_ambush or scout_encounter) and round_index == 0,
                subdual=False,
                encounter_round=round_index,
                missile_used=missile_used,
            )
        self._apply_detached_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )

    def _apply_detached_combat_result(
        self,
        session: SessionState,
        tile: TileState,
        result,
        *,
        show_rolls: bool,
        active_enemy_ids: set[str],
        standing_before: set[str],
    ) -> None:
        session.party = self._merge_party_outcome(session.party, result.party)
        tile.enemies = result.enemies
        session.log.extend(result.log)
        known_defeated_ids = {enemy.id for enemy in tile.defeated_enemies}
        for enemy in result.enemies:
            if enemy.id in active_enemy_ids and enemy.life <= 0 and enemy.id not in known_defeated_ids:
                tile.defeated_enemies.append(enemy.model_copy(deep=True))
                known_defeated_ids.add(enemy.id)
                if is_fd_ruleset(session):
                    from .forsaken_depths_secret_passage import note_fd_secret_passage_weird_defeated

                    note_fd_secret_passage_weird_defeated(session, enemy, show_rolls=show_rolls)
        fallen_now = [
            pc.character_id
            for pc in session.party
            if pc.character_id in standing_before and pc.current_life <= 0
        ]
        for character_id in fallen_now:
            if character_id not in tile.fallen_character_ids:
                tile.fallen_character_ids.append(character_id)
        apply_fd_tears_death_madness_spread(session, fallen_now, show_rolls=show_rolls)

        if not result.combat_over:
            session.detached_combat_rounds[tile.id] = max(0, int(session.detached_combat_rounds.get(tile.id, 0))) + 1
            session.detached_missile_used_character_ids[tile.id] = sorted(result.missile_used or [])
            if tile.id in session.scout_encounter_origin_tile_ids:
                session.log.append(
                    f"The scout survives the first round at {tile.title}. Rush the party in, or have the scout flee back."
                )
            else:
                session.log.append(f"Detached combat at {tile.title} continues.")
            return

        self._clear_detached_combat_state(session, tile.id)
        tile.wandering_ambush = False
        tile.enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if tile.enemies:
            session.log.append(
                f"The detached group at {tile.title} has fallen or withdrawn; foes remain there."
            )
        else:
            tile.resolved = True
            session.log.append(f"Detached combat at {tile.title} ends.")
            if result.morale_failed:
                self._award_treasure(session, tile, show_rolls=show_rolls)
            elif not tile.enemies:
                self._award_treasure(session, tile, show_rolls=show_rolls)
            defeated_this_fight = [
                enemy.model_copy(deep=True)
                for enemy in result.enemies
                if enemy.id in active_enemy_ids and enemy.life <= 0
            ]
            if defeated_this_fight:
                self._award_encounter_xp(session, defeated_this_fight, show_rolls=show_rolls)
                self._update_quest_on_combat_end(session, defeated_this_fight, show_rolls=show_rolls)
                if session.courtship_demesne_active:
                    from .courtship_demesne import update_courtship_on_combat_end

                    update_courtship_on_combat_end(
                        self, session, defeated_this_fight, show_rolls=show_rolls
                    )
                from .milestones import record_defeated_foes

                session.log.extend(record_defeated_foes(session.party, defeated_this_fight))
                session.log.extend(grant_spore_doses_after_combat(session, session.party, defeated_this_fight))
            self._announce_hidden_treasure_claimable(session, tile)
        if not any(pc.current_life > 0 for pc in session.party):
            session.mode = "complete"
            session.log.append("The party has fallen.")

    def _scout_group_for_tile(self, session: SessionState, tile_id: str) -> DetachedGroupState | None:
        for group in session.detached_groups:
            if group.tile_id == tile_id and str(group.reason or "").lower() == "scout":
                return group
        return None

    def _adjacent_tile_ids(self, session: SessionState, tile_id: str) -> set[str]:
        adjacent: set[str] = set()
        tile = self._tile_by_id(session, tile_id)
        if tile is not None:
            adjacent.update(exit_state.destination_tile_id for exit_state in tile.exits if exit_state.destination_tile_id)
        for other in session.map_state.tiles:
            if other.id == tile_id:
                continue
            if any(exit_state.destination_tile_id == tile_id for exit_state in other.exits):
                adjacent.add(other.id)
        adjacent.discard(tile_id)
        return adjacent

    def _song_of_elidra_party(self, session: SessionState, tile_id: str) -> list[PartyMemberState]:
        """Heroes on this map element or an adjacent connected one who can hear the song."""
        audible_tiles = {tile_id, *self._adjacent_tile_ids(session, tile_id)}
        unavailable = {
            character_id
            for character_id, turns in (session.druid_call_of_wild_turns or {}).items()
            if int(turns) > 0
        }
        member_tiles: dict[str, str] = {}
        for member in present_party(session, session.map_state.current_tile_id):
            member_tiles[member.character_id] = session.map_state.current_tile_id
        for group in session.detached_groups:
            if group.reason == "call_of_the_wild":
                continue
            for character_id in group.character_ids:
                member_tiles[character_id] = group.tile_id
        candidates: list[PartyMemberState] = []
        for member in sorted(session.party, key=lambda item: item.marching_order):
            if member.current_life <= 0 or member.character_id in unavailable:
                continue
            if member_tiles.get(member.character_id) in audible_tiles:
                candidates.append(member)
        return candidates

    def _scout_reaction(
        self,
        session: SessionState,
        detached_tile_id: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        reaction_adjust: int | None = None,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Resolve the current encounter before handling the scout.")
            return
        if not detached_tile_id:
            session.log.append("Choose a scout encounter.")
            return
        tile = self._tile_by_id(session, detached_tile_id)
        if tile is None or detached_tile_id not in session.scout_encounter_origin_tile_ids:
            session.log.append("There is no failed-scout encounter at that location.")
            return
        if detached_tile_id in session.scout_reaction_checked_tile_ids:
            session.log.append("The scout has already checked reactions for this encounter.")
            return
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            self._clear_detached_combat_state(session, detached_tile_id)
            session.log.append("No foes remain near the scout.")
            return
        fighters = combat_party(session, tile.id)
        if not fighters:
            session.log.append(f"No living scout remains at {tile.title}.")
            return
        session.scout_reaction_checked_tile_ids.append(detached_tile_id)
        scout_names = ", ".join(member.name for member in fighters)
        if any("final_boss" in enemy.tags for enemy in living_enemies):
            session.log.append(f"{scout_names} checks reactions: the Final Boss fights to the death.")
            return

        reaction_tables = self.rules.monsters().get("reaction_tables", {})
        if not isinstance(reaction_tables, dict):
            reaction_tables = {}
        source = resolve_reaction_source(living_enemies, reaction_tables)
        roll = roll_d6()
        adjust = max(-1, min(1, int(reaction_adjust or 0)))
        roll, negotiator_log = adjust_reaction_roll(fighters, roll, adjust)
        session.log.extend(negotiator_log)
        from .heroic_skill_effects import apply_song_of_elidra, beast_leadership_reaction_bonus

        song_party = self._song_of_elidra_party(session, tile.id)
        song_bonus, song_log = apply_song_of_elidra(session, song_party)
        if song_bonus:
            roll = max(1, min(6, roll + song_bonus))
            session.log.extend(song_log)
        beast_bonus, beast_log = beast_leadership_reaction_bonus(fighters, living_enemies)
        if beast_bonus:
            roll = max(1, min(6, roll + beast_bonus))
            session.log.extend(beast_log)
        from .forsaken_depths_citadel import fd_citadel_reaction_adjust

        citadel_adj, citadel_log = fd_citadel_reaction_adjust(session, tile)
        if citadel_adj:
            roll = max(1, min(6, roll + citadel_adj))
            session.log.extend(citadel_log)
        if source.inline_rows:
            row = lookup_reaction_row(source.inline_rows, roll)
            table_label = f"{source.label} reaction table"
        else:
            table_name = source.table_name or "default_reaction_table"
            row = self.table_roller.roll_reaction(table_name, roll)
            table_label = table_name
        if row is None:
            row = self.table_roller.roll_reaction("default_reaction_table", roll)
            table_label = "default_reaction_table"
        if row is None:
            row = {"key": "fight", "result": "The foes attack!", "foes_first": True}
        row = apply_reaction_overlays(row, living_enemies, roll)
        row = normalize_reaction_row(row)
        if show_rolls:
            session.log.append(f"Scout reaction roll: d6 = {roll} on {table_label}.")
        if explain_math:
            session.log.append("Scout reaction lookup uses the same foe reaction source as normal combat.")
        outcome = build_reaction_outcome(row, hcl=self._highest_character_level(fighters), foe_count=len(living_enemies))
        session.log.append(outcome.result)
        if self._try_resolve_scout_reaction(
            session,
            tile,
            fighters,
            living_enemies,
            outcome,
            row,
            show_rolls=show_rolls,
        ):
            return
        if outcome.key == "fight_to_death":
            session.log.append("Reaction outcome: foes fight to the death; the scout cannot rely on morale.")
        else:
            session.log.append("Reaction outcome: foes attack the scout.")
        session.log.append("The scout must fight the first round alone, or the party may rush in after that round.")

    def _finish_scout_peaceful(self, session: SessionState, tile: TileState) -> None:
        tile.resolved = True
        self._clear_detached_combat_state(session, tile.id)
        session.log.append(f"The scout encounter at {tile.title} ends without a fight.")

    def _apply_sleeping_foe_reaction(
        self,
        session: SessionState,
        fighters: list[PartyMemberState],
        bonus: int,
    ) -> None:
        bonus = max(1, int(bonus))
        session.reaction_sleep_attack_bonus = bonus
        for member in fighters:
            if member.current_life <= 0:
                continue
            member.statuses = [entry for entry in member.statuses if not entry.startswith("Sleeping foe +")]
            member.statuses.append(f"Sleeping foe +{bonus} first Attack")
        session.log.append(
            f"Reaction outcome: the foe is asleep; all PCs here gain +{bonus} on their first Attack roll."
        )
        session.reaction_pending = False
        session.foes_strike_first = False

    def _try_resolve_scout_reaction(
        self,
        session: SessionState,
        tile: TileState,
        fighters: list[PartyMemberState],
        living_enemies: list[EnemyState],
        outcome: ReactionOutcome,
        row: dict,
        *,
        show_rolls: bool,
    ) -> bool:
        """Return True when the scout encounter ends without a fight."""
        key = outcome.key
        foe_count = len(living_enemies)

        if key in {"flee", "peaceful", "ignore", "offer_food"}:
            if key == "flee":
                session.log.append("Reaction outcome: foes flee from the scout encounter.")
            elif key == "offer_food":
                session.log.append("Reaction outcome: the scout encounter ends peacefully with food offered.")
                for member in fighters:
                    if 0 < member.current_life < member.max_life:
                        member.current_life += 1
                        session.log.append(f"{member.name} eats and heals 1 Life.")
            else:
                session.log.append("Reaction outcome: the scout encounter ends peacefully.")
            self._end_peaceful_encounter(session, tile)
            self._finish_scout_peaceful(session, tile)
            return True

        if key == "flee_if_outnumbered" and flee_if_outnumbered(living_enemies, fighters):
            session.log.append("Reaction outcome: foes flee because the scout group outnumbers them.")
            self._end_peaceful_encounter(session, tile)
            self._finish_scout_peaceful(session, tile)
            return True

        if key == "sleep":
            self._apply_sleeping_foe_reaction(
                session,
                fighters,
                int(row.get("attack_bonus_first_round", 2)),
            )
            return False

        if key in {"trial_of_champions", "challenge_of_champions"}:
            session.log.append("Reaction outcome: the scout cannot resolve a champion trial alone.")
            return False

        if key == "quest":
            if session.active_quest is not None:
                session.log.append("A Quest is already in progress; the scout cannot accept another.")
                return False
            self._accept_reaction_quest(session, tile, show_rolls=show_rolls)
            self._finish_scout_peaceful(session, tile)
            return True

        if key == "blood_offering":
            jar_holder = self._find_reaction_item_holder(fighters, None, ["chicken blood"])
            if jar_holder is not None:
                member, index, item = jar_holder
                member.inventory.pop(index)
                session.log.append(f"{member.name} offers {item} for the Blood Offering.")
                self._end_peaceful_encounter(session, tile)
                self._finish_scout_peaceful(session, tile)
                return True
            donor = next((member for member in fighters if member.current_life > 2), None)
            if donor is None:
                session.log.append("No scout here can safely give 2 Life for the Blood Offering.")
                return False
            donor.current_life -= 2
            session.log.append(
                f"Effect: {donor.name} gives blood and loses 2 Life ({donor.current_life}/{donor.max_life})."
            )
            self._end_peaceful_encounter(session, tile)
            self._finish_scout_peaceful(session, tile)
            return True

        if key == "buy_weapons":
            if any(member.class_id.lower() in {"dwarf", "elf"} for member in fighters if member.current_life > 0):
                session.log.append("The cave orcs will not buy weapons while dwarves or elves are present.")
                return False
            sale = self._find_sale_weapon(fighters, character_id=None, item_name=None)
            if sale is None:
                session.log.append("The scout has no eligible weapon to sell to the cave orcs.")
                return False
            member, index, item, price = sale
            member.inventory.pop(index)
            carried_room = max(0, MAX_CARRIED_GOLD - member.gold)
            paid = min(price, carried_room)
            member.gold += paid
            leftover = price - paid
            if leftover:
                tile.treasure_gold = (tile.treasure_gold or 0) + leftover
            session.log.append(f"{member.name} sells {item} to the cave orcs for {price}gp.")
            if leftover:
                session.log.append(f"{leftover}gp cannot be carried and is left on the floor.")
            self._end_peaceful_encounter(session, tile)
            self._finish_scout_peaceful(session, tile)
            return True

        if key == "bribe_magic_item":
            if dwarf_miser_blocks_bribe(fighters):
                session.log.append("Reaction outcome: the dwarves refuse to pay (Miser trait with 2+ dwarves).")
                return False
            if self._pay_named_items(session, fighters, ["magic"], 1, quiet=True):
                session.log.append("Reaction outcome: the scout surrenders a magic item and passes peacefully.")
                self._end_peaceful_encounter(session, tile)
                self._finish_scout_peaceful(session, tile)
                return True
            session.log.append("Reaction outcome: the scout has no magic item to surrender here.")
            return False

        if key == "bribe":
            if dwarf_miser_blocks_bribe(fighters):
                session.log.append("Reaction outcome: the dwarves refuse to pay a bribe (Miser trait with 2+ dwarves).")
                return False
            session.log.append("Reaction outcome: scout-local bribe; only gear and gold carried here can pay.")
            if self._resolve_scout_bribe(session, tile, fighters, outcome, show_rolls=show_rolls):
                self._finish_scout_peaceful(session, tile)
                return True
            return False

        if is_bribe_reaction(key) and key not in {"bribe"}:
            if dwarf_miser_blocks_bribe(fighters):
                session.log.append("Reaction outcome: the dwarves refuse to pay (Miser trait with 2+ dwarves).")
                return False
            session.reaction_key = key
            session.reaction_bribe_foe_count = foe_count
            if self._accept_special_bribe(session, tile, fighters, key, character_id=None, item_name=None):
                self._finish_scout_peaceful(session, tile)
                return True
            session.log.append("Reaction outcome: the scout cannot pay this special bribe with carried gear.")
            return False

        if key == "puzzle":
            session.log.append("Reaction outcome: scout must solve the puzzle or the foes strike first.")
            self._resolve_reaction_challenge(
                session,
                tile,
                fighters,
                living_enemies,
                context="puzzle",
                label="Scout Puzzle",
                success_log="The scout solves the puzzle; the foes let the scout pass.",
                failure_log="The puzzle fails; the foes attack the scout first!",
                no_solver_log="No scout can attempt the puzzle; the foes attack first!",
                magical=False,
                show_rolls=show_rolls,
            )
            if not any(enemy.life > 0 for enemy in tile.enemies):
                self._finish_scout_peaceful(session, tile)
                return True
            return False

        if key == "magic_challenge":
            session.log.append("Reaction outcome: scout must answer the magical challenge or the foes strike first.")
            self._resolve_reaction_challenge(
                session,
                tile,
                fighters,
                living_enemies,
                context="magic_challenge",
                label="Scout Magic Challenge",
                success_log="The scout answers the magical challenge; the foes let the scout pass.",
                failure_log="The magical challenge fails; the foes attack the scout first!",
                no_solver_log="No scout can answer the magical challenge; the foes attack first!",
                magical=True,
                show_rolls=show_rolls,
            )
            if not any(enemy.life > 0 for enemy in tile.enemies):
                self._finish_scout_peaceful(session, tile)
                return True
            return False

        if key == "capture":
            session.capture_mode = True
            session.capture_foe_name = living_enemies[0].name if living_enemies else "Unknown Foe"
            session.capture_origin_tile_id = tile.id
            session.log.append(
                "Reaction outcome: capture mode begins for the scout; 0 Life means prisoner, not slain."
            )
            session.log.append(
                "The scout is at risk of capture: foes attack to subdue rather than kill and strike first."
            )
            return False

        return False

    def _resolve_scout_bribe(
        self,
        session: SessionState,
        tile: TileState,
        fighters: list[PartyMemberState],
        outcome: ReactionOutcome,
        *,
        show_rolls: bool = True,
    ) -> bool:
        living_foes = [enemy for enemy in tile.enemies if enemy.life > 0]
        foe_count = len(living_foes)
        gold_per_foe = outcome.bribe_gold_per_foe
        weapons_per_foe = outcome.bribe_weapons_per_foe
        if gold_per_foe <= 0 and outcome.bribe_gold > 0 and foe_count > 0:
            gold_per_foe = outcome.bribe_gold // foe_count
        if weapons_per_foe <= 0 and outcome.bribe_weapons > 0 and foe_count > 0:
            weapons_per_foe = outcome.bribe_weapons // foe_count
        if not bribe_requirements_met(
            fighters,
            foe_count=foe_count,
            gold_per_foe=gold_per_foe,
            weapons_per_foe=weapons_per_foe,
        ):
            available_gold = sum(member.gold for member in fighters if member.current_life > 0)
            available_weapons = count_party_weapons(fighters)
            if weapons_per_foe:
                session.log.append(
                    f"The scout cannot afford the bribe with gear carried here "
                    f"({available_gold}gp, {available_weapons} weapon(s) available)."
                )
            else:
                session.log.append(
                    f"The scout needs {outcome.bribe_gold}gp but only has {available_gold}gp here."
                )
            session.log.append("The scout must fight the first round alone, or the party may rush in after that round.")
            return False

        gold_paid, weapons_paid, payment_log = pay_bribe_cost(
            fighters,
            foe_count=foe_count,
            gold_per_foe=gold_per_foe,
            weapons_per_foe=weapons_per_foe,
        )
        session.log.extend(payment_log)
        if show_rolls:
            parts = []
            if gold_paid:
                parts.append(f"{gold_paid}gp")
            if weapons_paid:
                parts.append(f"{weapons_paid} weapon(s)")
            summary = " and ".join(parts) if parts else "nothing"
            session.log.append(f"The scout pays {summary}.")
        self._end_peaceful_encounter(session, tile)
        return True

    def _rush_to_scout(self, session: SessionState, detached_tile_id: str | None, *, show_rolls: bool = True) -> None:
        if session.mode != "exploration":
            session.log.append("Resolve the current encounter before rushing to the scout.")
            return
        if not detached_tile_id:
            session.log.append("Choose the scout to aid.")
            return
        tile = self._tile_by_id(session, detached_tile_id)
        if tile is None or detached_tile_id not in session.scout_encounter_origin_tile_ids:
            session.log.append("There is no failed-scout encounter at that location.")
            return
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._clear_detached_combat_state(session, detached_tile_id)
            session.log.append("No foes remain near the scout.")
            return
        session.map_state.current_tile_id = tile.id
        session.current_tile_entry_exit_id = None
        session.active_group_tile_id = None
        session.log.extend(reattach_heroes(session, None))
        self._clear_detached_combat_state(session, tile.id)
        session.log.append(f"The party rushes to the scout at {tile.title}.")
        self._begin_combat(session, "The party joins the scout's fight.", tile=tile, show_rolls=show_rolls)
        session.reaction_pending = False
        session.reaction_checked = True
        if not session.reaction_key:
            session.reaction_key = "fight"
        if session.log and session.log[-1].startswith("Choose: Check Reactions"):
            session.log.pop()
        session.log.append("Reactions are already committed by the failed scout contact; resolve the next combat round.")

    def _scout_flee_back(
        self,
        session: SessionState,
        detached_tile_id: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Resolve the current encounter before the scout flees.")
            return
        if not detached_tile_id:
            session.log.append("Choose the scout to flee.")
            return
        tile = self._tile_by_id(session, detached_tile_id)
        origin_id = session.scout_encounter_origin_tile_ids.get(detached_tile_id)
        if tile is None or not origin_id:
            session.log.append("There is no failed-scout encounter at that location.")
            return
        fighters = combat_party(session, tile.id)
        if not fighters:
            self._clear_detached_combat_state(session, detached_tile_id)
            session.log.append(f"No living scout remains at {tile.title}.")
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in fighters if pc.current_life > 0}
        result = resolve_flee(
            fighters,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            context=self._combat_context(session, tile),
            skip_parting_attacks=False,
        )
        self._apply_detached_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )
        if result.fled:
            group = self._scout_group_for_tile(session, tile.id)
            if group is not None:
                group.tile_id = origin_id
            self._clear_detached_combat_state(session, tile.id)
            origin = self._tile_by_id(session, origin_id)
            session.log.append(f"The scout flees back to {origin.title if origin else 'the previous room'}.")

    def _roll_wandering_enemies(self, session: SessionState, category: str, hcl: int) -> list[EnemyState]:
        from .abyss_tables import is_abyss_profile

        if is_abyss_profile(session):
            table_by_category = {
                "vermin": "abyss_vermin_table",
                "minions": "abyss_minions_table",
                "weird": "abyss_weird_table",
                "boss": "abyss_boss_table",
            }
            table_name = table_by_category.get(category, "abyss_minions_table")
            enemies, _ = self._roll_abyss_monster_row(session, table_name, category if category in table_by_category else "minions")
            for enemy in enemies:
                enemy.tags.append("wandering_spawn")
            return enemies
        for _ in range(6):
            enemies = self._roll_enemy(session, category, hcl, wandering=True)
            if not enemies:
                continue
            if category == "boss" and any("dragon" in enemy.tags for enemy in enemies):
                continue
            return enemies
        return self._roll_enemy(session, "minions", hcl, wandering=True)

    def _maybe_wandering_on_backtrack(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        if session.mode != "exploration":
            return
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Backtrack roll: d6 = {roll}.")
        if roll > 2:
            return
        self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)
        self._check_detached_wandering(session, show_rolls=show_rolls, exclude_tile_id=tile.id)

    def _reveal_secret_door(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        used_directions = {exit_state.direction for exit_state in tile.exits}
        direction = next((item for item in CARDINAL_DIRECTION_ORDER if item not in used_directions), None)
        if direction is None:
            direction = next((item for item in CARDINAL_DIRECTION_ORDER if item != "south"), "north")
        secret_exit = self._new_exit(
            direction=direction,
            kind="door",
            width=width,
            height=height,
            status="open",
            label="Secret door",
        )
        secret_exit.door_open = True
        tile.exits.append(secret_exit)
        session.log.append(f"A secret door appears on the {direction} wall.")
        hcl = self._highest_character_level(session.party)
        peek_tile = self._generate_tile(
            session=session,
            origin=tile,
            origin_exit=secret_exit,
            hcl=hcl,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if peek_tile is None:
            tile.exits = [exit_state for exit_state in tile.exits if exit_state.id != secret_exit.id]
            session.log.append("There is no space to place the chamber behind the secret door.")
            return
        peek_tile.treasure_doubled = True
        secret_exit.destination_tile_id = peek_tile.id
        session.map_state.tiles.append(peek_tile)
        self._clip_origin_visible_for_neighbor(tile, peek_tile)
        self._strip_neighbor_origin_overlap(tile, peek_tile, secret_exit)
        self._set_reciprocal_exit(peek_tile, tile, secret_exit)
        session.log.append(
            f"Peeking through the secret door: {peek_tile.title} — {peek_tile.description}"
        )
        if peek_tile.enemies:
            peek_tile.surprise_party = True
            session.log.append("Foes wait inside; entering will surprise them.")
        safe_roll = roll_d6()
        if show_rolls:
            session.log.append(f"Secret door shortcut roll: d6 = {safe_roll}.")
        if safe_roll == 6:
            secret_exit.dungeon_exit = True
            session.log.append("This secret door is a safe shortcut out of the dungeon.")

    def _offer_secret_passage(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        if "Secret Passage" not in tile.objects:
            tile.objects.append("Secret Passage")
        session.pending_secret_passage_tile_id = tile.id
        session.log.append(
            "Event: You find a secret passage leading to a different environment. "
            "Choose Dungeon, Caverns, or Fungal Grottoes."
        )

    def _choose_secret_passage_environment(
        self,
        session: SessionState,
        environment: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Choose a secret-passage destination during exploration.")
            return
        tile_id = session.pending_secret_passage_tile_id
        if not tile_id:
            session.log.append("No secret passage awaits an environment choice.")
            return
        tile = self._tile_by_id(session, tile_id)
        if tile is None:
            session.pending_secret_passage_tile_id = None
            session.log.append("The secret passage tile is no longer on the map.")
            return
        if environment not in {"dungeon", "caverns", "fungal_grottoes"}:
            session.log.append("Choose Dungeon, Caverns, or Fungal Grottoes for the secret passage.")
            return
        if session.pending_secret_passage_hidden_pit and environment not in {"dungeon", "fungal_grottoes"}:
            session.log.append("Hidden Pit secret passages lead to the Dungeon or Fungal Grottoes only.")
            return
        previous = session.environment
        if environment == previous:
            session.log.append("Choose a different environment than the one you are leaving.")
            return
        self._open_secret_passage_destination(
            session,
            tile,
            environment,  # type: ignore[arg-type]
            previous_environment=previous,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        session.pending_secret_passage_tile_id = None
        session.pending_secret_passage_hidden_pit = False
        session.pending_search_reroll_tile_id = None

    def _open_secret_passage_destination(
        self,
        session: SessionState,
        source_tile: TileState,
        environment: str,
        *,
        previous_environment: str,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> bool:
        from .dungeon_table_roller import environment_label
        from .heroic_skill_effects import mark_tile_visited

        label = environment_label(environment)  # type: ignore[arg-type]
        source_environment = source_tile.environment or previous_environment or "dungeon"
        width, height = self._rotated_size(
            source_tile.footprint_width,
            source_tile.footprint_height,
            source_tile.rotation,
        )
        used_directions = {exit_state.direction for exit_state in source_tile.exits}
        direction = next((item for item in CARDINAL_DIRECTION_ORDER if item not in used_directions), None)
        if direction is None:
            direction = next((item for item in CARDINAL_DIRECTION_ORDER if item != "south"), "north")
        passage_exit = self._new_exit(
            direction=direction,
            kind="passage",
            width=width,
            height=height,
            status="open",
            label=f"Secret passage ({label})",
        )
        passage_exit.door_open = True
        source_tile.exits.append(passage_exit)
        session.environment = environment  # type: ignore[assignment]
        self._clear_environment_warning_statuses(
            session,
            previous_environment=previous_environment,
            new_environment=environment,  # type: ignore[arg-type]
        )
        hcl = self._highest_character_level(session.party)
        destination_tile = self._generate_tile(
            session=session,
            origin=source_tile,
            origin_exit=passage_exit,
            hcl=hcl,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if destination_tile is None:
            source_tile.exits = [exit_state for exit_state in source_tile.exits if exit_state.id != passage_exit.id]
            session.environment = previous_environment  # type: ignore[assignment]
            session.log.append("There is no space to place the area beyond the secret passage.")
            return False
        passage_exit.destination_tile_id = destination_tile.id
        session.map_state.tiles.append(destination_tile)
        self._clip_origin_visible_for_neighbor(source_tile, destination_tile)
        self._strip_neighbor_origin_overlap(source_tile, destination_tile, passage_exit)
        entry_exit = self._set_reciprocal_exit(destination_tile, source_tile, passage_exit)
        source_tile.environment = source_environment  # type: ignore[assignment]
        if source_tile.content_key == "entrance":
            source_tile.environment = "dungeon"
        session.map_state.current_tile_id = destination_tile.id
        session.current_tile_entry_exit_id = entry_exit.id
        mark_tile_visited(session, destination_tile.id)
        self._prepare_tile_features(
            session,
            destination_tile,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        session.log.append(
            f"The party follows the secret passage into the {label}. "
            f"Entered {destination_tile.title}: {destination_tile.description} "
            "Draw new map elements in a different color; trap, event, and treasure rolls "
            f"now use {label} tables."
        )
        if destination_tile.enemies and session.mode == "exploration":
            self._announce_encounter(session, destination_tile, show_rolls=show_rolls)
        return True

    def _repair_incomplete_secret_passage(self, session: SessionState, *, show_rolls: bool = False) -> bool:
        """Sessions that switched environment without placing the passage destination."""
        if session.pending_secret_passage_tile_id:
            return False
        if len(session.map_state.tiles) != 1:
            return False
        source_tile = session.map_state.tiles[0]
        if "Secret Passage" not in source_tile.objects and "Secret Passage to caves" not in source_tile.objects:
            return False
        if any(
            exit_state.destination_tile_id
            and "secret passage" in (exit_state.label or "").lower()
            for exit_state in source_tile.exits
        ):
            return False
        target_environment = session.environment
        if target_environment == "dungeon":
            return False
        previous_environment = "dungeon" if source_tile.content_key == "entrance" else (source_tile.environment or "dungeon")
        if not self._open_secret_passage_destination(
            session,
            source_tile,
            target_environment,
            previous_environment=previous_environment,
            show_rolls=show_rolls,
            explain_math=False,
        ):
            return False
        session.pending_search_reroll_tile_id = None
        session.log.append("Repaired incomplete secret passage: placed the destination map element.")
        return True

    def _sync_session_environment_from_tile(self, session: SessionState, tile: TileState) -> None:
        tile_environment = tile.environment or "dungeon"
        if session.environment == tile_environment:
            return
        previous = session.environment
        session.environment = tile_environment
        self._clear_environment_warning_statuses(
            session,
            previous_environment=previous,
            new_environment=tile_environment,
        )

    def _reveal_secret_passage(self, session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
        self._offer_secret_passage(session, tile, show_rolls=show_rolls)

    def _finalize_treasure_items(
        self,
        session: SessionState,
        items: list[str],
        *,
        show_rolls: bool,
    ) -> list[str]:
        resolved, log = resolve_special_treasure_items(items)
        spell_resolved: list[str] = []
        for item in resolved:
            random_spell_item = self._resolve_random_spell_loot_item(session, item)
            if random_spell_item:
                spell_resolved.append(random_spell_item[0])
                log.extend(random_spell_item[1])
            else:
                from .fungal_rare_items import normalize_fungal_treasure_item

                spell_resolved.append(normalize_fungal_treasure_item(item))
        if show_rolls and log:
            session.log.extend(log)
        return spell_resolved

    def _resolve_random_spell_loot_item(
        self,
        session: SessionState,
        item: str,
    ) -> tuple[str, list[str]] | None:
        lowered = item.strip().lower()
        if "random spell" not in lowered and "random wizard spell" not in lowered:
            return None
        if "prism" in lowered or session.environment == "caverns":
            return self.table_roller.roll_random_spell_loot("caverns")
        if "bark" in lowered or session.environment == "fungal_grottoes":
            return self.table_roller.roll_random_spell_loot("fungal_grottoes")
        return self.table_roller.roll_random_spell_loot("dungeon")

    def _entry_treasure_bonus(self, session: SessionState) -> int:
        if not session.current_tile_entry_exit_id:
            return 0
        tile = self._current_tile(session)
        exit_state = next(
            (item for item in tile.exits if item.id == session.current_tile_entry_exit_id),
            None,
        )
        return max(0, exit_state.door_treasure_bonus if exit_state else 0)

    def _roll_treasure(self, session: SessionState) -> TreasureOutcome:
        tile = self._current_tile(session)
        bonus = self._entry_treasure_bonus(session)
        if is_fd_ruleset(session):
            outcome = self.table_roller.roll_fd_treasure(
                show_rolls=True,
                treasure_bonus=bonus,
                silk_already_found=session.fd_silk_treasure_used,
            )
            if "Precious silk worth" in outcome.summary:
                session.fd_silk_treasure_used = True
            return outcome
        if tile is not None and self._tile_has_fiendish_foes(tile):
            return self.table_roller.roll_fiendish_foes_treasure(treasure_bonus=bonus)
        return self.table_roller.roll_treasure(
            environment=session.environment,
            treasure_bonus=bonus,
        )

    def _tile_has_fiendish_foes(self, tile: TileState) -> bool:
        foes = list(tile.enemies) + list(tile.defeated_enemies)
        return any("fiendish" in {tag.lower() for tag in enemy.tags} for enemy in foes)

    def _resolve_event_foes(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        remaining: list[EnemyState] = []
        for enemy in tile.enemies:
            tags = {tag.lower() for tag in enemy.tags}
            if "gremlin" in enemy.name.lower() and ("event" in tags or "not_foe" in tags):
                session.log.extend(resolve_invisible_gremlins(session, session.party))
                continue
            if enemy.life <= 0 and ("event" in tags or "not_foe" in tags):
                if show_rolls:
                    session.log.append(f"{enemy.name}: event resolved.")
                continue
            remaining.append(enemy)
        tile.enemies = remaining
        tile.initial_enemy_count = len(tile.enemies)

    def _grant_hidden_treasure(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        hcl = self._highest_character_level(session.party)
        treasure = self.table_roller.roll_hidden_treasure(hcl)
        tile.treasure_summary = treasure.summary
        tile.treasure_gold = treasure.gold
        tile.treasure_items = self._finalize_treasure_items(session, treasure.items, show_rolls=show_rolls)
        tile.treasure_claimed = False
        session.log.extend(treasure.log)
        effect = treasure.complication_effect
        if not effect:
            self._announce_hidden_treasure_claimable(session, tile)
            return
        if self._halfling_with_luck_available(session):
            tile.hidden_treasure_complication_effect_pending = effect
            session.pending_hidden_complication_reroll_tile_id = tile.id
            session.log.append(
                "A halfling may spend 1 Luck to reroll the hidden treasure complication (EE p.108)."
            )
            return
        self._apply_hidden_treasure_complication(
            session,
            tile,
            effect,
            hcl=hcl,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )

    def _halfling_with_luck_available(self, session: SessionState) -> PartyMemberState | None:
        for member in session.party:
            if member.current_life > 0 and member.class_id.lower() == "halfling":
                if luck_points_remaining(session, member) > 0:
                    return member
        return None

    def _apply_hidden_treasure_complication(
        self,
        session: SessionState,
        tile: TileState,
        effect: str,
        *,
        hcl: int,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        tile.hidden_treasure_complication_effect_pending = None
        session.pending_hidden_complication_reroll_tile_id = None
        if effect == "alarm":
            tile.hidden_treasure_alarm_pending = True
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)
            session.log.append(
                "The alarm must be answered before the hidden treasure can be claimed."
            )
            return
        session.log.extend(
            self.table_roller.apply_hidden_complication(
                effect,
                hcl=hcl,
                party=session.party,
                marching_order=self._marching_order_ids(session),
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        )
        self._announce_hidden_treasure_claimable(session, tile)

    def _announce_hidden_treasure_claimable(self, session: SessionState, tile: TileState) -> None:
        if tile.treasure_claimed or (not tile.treasure_gold and not tile.treasure_items):
            return
        if tile.hidden_treasure_complication_effect_pending:
            return
        if tile.trap_key and not tile.trap_resolved:
            session.log.append(
                f"Hidden treasure ({self._treasure_value_label(tile)}) is here; resolve the trap before claiming."
            )
            return
        if any(enemy.life > 0 for enemy in tile.enemies):
            return
        tile.hidden_treasure_alarm_pending = False
        session.log.append(
            f"The hidden treasure ({self._treasure_value_label(tile)}) can be claimed here. Use Claim Treasure."
        )

    def _after_trap_resolved(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        tile.objects = [item for item in tile.objects if "trap" not in item.lower()]
        if tile.treasure_claimed:
            return
        if tile.treasure_gold or tile.treasure_items:
            self._announce_hidden_treasure_claimable(session, tile)
            return
        if tile.content_key == "trap_treasure" or tile.treasure_summary:
            summary = tile.treasure_summary or "No treasure found."
            session.log.append(f"Trap cleared. {summary.rstrip('.')}.")
            return
        if (
            is_fd_ruleset(session)
            and tile.content_key == "fd_trap"
            and tile.tile_type == "room"
            and not tile.treasure_summary
            and not tile.treasure_gold
            and not tile.treasure_items
        ):
            if roll_d6() <= 2:
                outcome = self._roll_treasure(session)
                if outcome.gold or outcome.items or outcome.summary or outcome.choice_key:
                    session.log.extend(outcome.log)
                    session.log.append("Forsaken Depths trap room: 2-in-6 treasure after the trap (FD p.59).")
                    self._stage_treasure_outcome(session, tile, outcome, show_rolls=True)
                    if tile.treasure_gold or tile.treasure_items or tile.pending_treasure_choice:
                        self._announce_hidden_treasure_claimable(session, tile)
                    return
        session.log.append("Trap cleared.")
        if is_fd_ruleset(session):
            from .forsaken_depths_secret_passage import note_fd_secret_passage_trap_cleared

            trap_level = tile.trap_level or self._highest_character_level(session.party)
            hcl = self._highest_character_level(session.party)
            note_fd_secret_passage_trap_cleared(
                session,
                trap_level=trap_level,
                hcl=hcl,
                show_rolls=show_rolls,
            )

    def _treasure_value_label(self, tile: TileState) -> str:
        parts: list[str] = []
        if tile.treasure_gold:
            parts.append(f"{tile.treasure_gold}gp")
        parts.extend(tile.treasure_items)
        if parts:
            return ", ".join(parts)
        return tile.treasure_summary or "loot"

    def _log_room_recap_after_combat(self, session: SessionState, tile: TileState) -> None:
        """Repeat room context after combat so the player need not scroll the log."""
        title = (tile.title or "This room").strip()
        session.log.append(f"── {title} ──")
        if tile.description:
            session.log.append(tile.description)
        if (tile.treasure_gold or tile.treasure_items) and not tile.treasure_claimed:
            session.log.append(
                f"Treasure here: {self._treasure_value_label(tile)} — use Claim Treasure."
            )
        elif tile.treasure_summary and not tile.treasure_claimed:
            session.log.append(f"Treasure here: {tile.treasure_summary} — use Claim Treasure.")

    def _look_around(self, session: SessionState) -> None:
        tile = self._current_tile(session)
        title = (tile.title or "This room").strip()
        session.log.append(f"── {title} ──")
        if tile.description:
            session.log.append(tile.description)
        exit_line = self._format_tile_exits_for_look(tile)
        if exit_line:
            session.log.append(exit_line)
        if any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("Enemies are present here.")
        if (tile.treasure_gold or tile.treasure_items) and not tile.treasure_claimed:
            session.log.append(f"Treasure: {self._treasure_value_label(tile)} (unclaimed).")
        elif tile.treasure_summary and not tile.treasure_claimed:
            session.log.append(f"Treasure: {tile.treasure_summary} (unclaimed).")
        if tile.trap_key and not tile.trap_resolved:
            session.log.append(f"Trap: {tile.trap_key} (unresolved).")
        if tile.searched:
            session.log.append("This room has been searched.")

    def _format_tile_exits_for_look(self, tile: TileState) -> str:
        counts: dict[str, int] = {}
        parts: list[str] = []
        for exit_state in tile.exits:
            direction = exit_state.direction
            if not direction:
                continue
            counts[direction] = counts.get(direction, 0) + 1
            index = counts[direction]
            label = f"{direction.title()} {index}"
            if exit_state.dungeon_exit:
                parts.append(f"{label} (dungeon exit)")
            elif exit_state.kind == "door":
                state = "open" if exit_state.door_open else "closed"
                parts.append(f"{label} door ({state})")
            else:
                parts.append(f"{label} {exit_state.kind}")
        if not parts:
            return ""
        return "Exits: " + "; ".join(parts) + ". Commands: go/open/listen + direction + number (e.g. go north 1)."

    def _format_living_foes(self, enemies: list[EnemyState]) -> str:
        living = [enemy for enemy in enemies if enemy.life > 0]
        if not living:
            return ""
        labels = foe_display_labels(living)
        return ", ".join(
            f"{labels[enemy.id]} (L{enemy.level}, {enemy.life}/{enemy.max_life} Life)" for enemy in living
        )

    def _mark_major_foe_encounter(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        allow_final_boss_check: bool = True,
    ) -> None:
        living_majors = [enemy for enemy in tile.enemies if enemy.life > 0 and enemy.category in {"weird", "boss"}]
        if not living_majors:
            return
        if tile.major_foe_encounter_counted:
            return
        tile.major_foe_encounter_counted = True
        session.major_foes_encountered += 1
        if allow_final_boss_check and not dungeon_has_final_boss(session):
            if map_elements_at_cap(session):
                boss_log, boss = force_final_boss_designation(
                    tile.enemies,
                    reason=(
                        f"Dungeon extent exhausted ({unlimited_map_element_cap(session)} map elements): "
                        "the major foe here is the Final Boss."
                    ),
                )
            else:
                boss_log, boss = mark_final_boss_candidate(
                    tile.enemies,
                    major_foes_encountered=session.major_foes_encountered,
                    show_rolls=show_rolls,
                )
            session.log.extend(boss_log)
            if boss is not None:
                tile.final_boss_treasure = True
                session.final_boss_designated = True
        from .forsaken_depths_map import is_fd_ruleset
        from .forsaken_depths_quest import maybe_spawn_fd_quest_servitor_in_lair

        if is_fd_ruleset(session):
            maybe_spawn_fd_quest_servitor_in_lair(self, session, tile, show_rolls=show_rolls)

    def _begin_combat(
        self,
        session: SessionState,
        message: str,
        *,
        show_rolls: bool = True,
        allow_final_boss_check: bool = True,
        party_strikes_first: bool = False,
        foes_strike_first: bool = False,
        tile: TileState | None = None,
    ) -> None:
        tile = tile or self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("No foes remain to fight.")
            return
        session.combat_round = 0
        reset_expert_encounter(session)
        session.ward_of_protection_targets = {}
        session.sacrifice_shield_used = []
        session.missile_used_character_ids = []
        session.spell_used_character_ids = []
        session.torch_spent_this_combat = False
        session.combat_lanterns_extinguished = False
        session.monster_encounter_start_applied = False
        session.wielded_melee_weapons = {}
        session.gladiator_counter_pending = {}
        session.gladiator_counter_used = []
        from .swashbuckler_traits import reset_swashbuckler_combat_flags

        reset_swashbuckler_combat_flags(session)
        session.evasion_character_ids = []
        session.secret_weakness_foe_id = None
        session.secret_weakness_character_id = None
        session.secret_enemy_foe_id = None
        session.secret_enemy_character_id = None
        session.terrifying_secret_pending_character_id = None
        fighters = combat_party(session, tile.id)
        for member in fighters:
            prune_weapon_defaults(member)
            weapon = select_melee_weapon(member)
            if weapon is not None:
                session.wielded_melee_weapons[member.character_id] = weapon.item
        session.mode = "combat"
        self._maybe_discover_prisoner(session, tile)
        session.firearm_fired_this_encounter = False
        session.reaction_pending = True
        session.reaction_checked = False
        session.reaction_key = None
        session.party_attacked_immediately = False
        session.party_surprised = bool(tile.wandering_ambush or tile.surprise_party)
        if not session.party_surprised:
            boulder_surprise, boulder_roll = boulder_surprise_triggers(tile.cavern_feature_key, tile.enemies)
            if boulder_surprise:
                session.party_surprised = True
                session.log.append(
                    f"Boulders help camouflaged foes surprise the party (2-in-6 roll = {boulder_roll})."
                )
        if session.environment == "caverns" and session.caverns_scout_warning and session.party_surprised:
            session.party_surprised = False
            session.log.append("Cave goblin scout warning: the party is not surprised.")
        elif session.environment == "caverns" and session.caverns_morlock_warning and self._tile_has_morlocks(tile) and session.party_surprised:
            session.party_surprised = False
            session.log.append("Morlock spy warning: morlocks do not surprise the party.")
        elif session.environment == "fungal_grottoes" and session.fungal_scout_warning and session.party_surprised:
            session.party_surprised = False
            session.log.append("Halfling scout warning: the party is not surprised.")
        if rearguard_has_danger_sense(fighters) and tile.wandering_ambush:
            session.party_surprised = False
            session.log.append("Danger Sense: the rearguard was not surprised.")
        if session.expert_acute_hearing_tiles and tile.id in session.expert_acute_hearing_tiles:
            session.party_surprised = False
            session.log.append("Acute Hearing: the party was not surprised.")
        if party_strikes_first:
            session.party_surprised = False
            session.party_attacked_immediately = True
        elif foes_strike_first:
            session.party_surprised = True
            session.foes_strike_first = True
        if session.party_surprised:
            from .forsaken_depths_revelation import consume_fd_revelation_negate_ambush

            if consume_fd_revelation_negate_ambush(session, show_rolls=show_rolls):
                session.party_surprised = False
        if session.party_surprised:
            session.log.append("The party is surprised!")
        tile.surprise_party = False
        session.reaction_bribe_gold = 0
        session.reaction_bribe_weapons = 0
        session.reaction_bribe_gold_per_foe = 0
        session.reaction_bribe_weapons_per_foe = 0
        session.reaction_bribe_foe_count = 0
        session.reaction_trade_stock = []
        session.reaction_trade_active = False
        session.reaction_no_fools_gold = False
        session.foe_flee_strike_pending = False
        session.log.append(message)
        foe_summary = self._format_living_foes(tile.enemies)
        if foe_summary:
            session.log.append(f"You face: {foe_summary}.")
        from .monster_combat_hooks import apply_mantlebeast_ambush_drop

        session.log.extend(
            apply_mantlebeast_ambush_drop(session, tile, fighters, show_rolls=show_rolls)
        )
        for hint in self._secret_timing_hints(session, tile):
            session.log.append(hint)
        self._mark_major_foe_encounter(
            session,
            tile,
            show_rolls=show_rolls,
            allow_final_boss_check=allow_final_boss_check,
        )
        if self._auto_check_surprise_reaction(session, show_rolls=show_rolls):
            return
        session.log.append(
            "Choose: Check Reactions, or attack immediately (Fight Round or any voluntary combat spell)."
        )

    def _reactions_unresolved(self, session: SessionState) -> bool:
        return (
            session.mode == "combat"
            and session.combat_round == 0
            and session.reaction_pending
            and not session.reaction_checked
        )

    def _commit_immediate_attack(self, session: SessionState) -> bool:
        if not self._reactions_unresolved(session):
            return True
        if session.party_surprised:
            session.log.append("The party is surprised; Check Reactions before any party action (p.146).")
            return False
        session.reaction_checked = True
        session.reaction_pending = False
        session.reaction_key = "fight"
        session.foes_strike_first = False
        session.party_attacked_immediately = True
        session.log.append("The party acts without waiting for a Reaction roll.")
        return True

    def _secret_timing_hints(self, session: SessionState, tile: TileState) -> list[str]:
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living:
            return []
        hints: list[str] = []
        majors = [enemy for enemy in living if enemy.category in {"weird", "boss"}]
        guarded = any(enemy.category in {"minions", "boss"} for enemy in living)
        living_minor = [enemy for enemy in living if enemy.category in {"vermin", "minions"}]
        initial_count = max(tile.initial_enemy_count or 0, len(tile.enemies), len(living_minor))
        morale_ready = bool(living) and not all(
            "final_boss" in {tag.lower() for tag in enemy.tags} for enemy in living
        )
        heroes = [member for member in combat_party(session, tile.id) if member.current_life > 0]
        for member in heroes:
            if majors and has_secret(member, "weakness_of_a_foe") and not session.secret_weakness_foe_id:
                hints.append(
                    f"Secret available: {member.name} has Weakness of a Foe. "
                    "Choose a Major Foe from the hero sheet or click that foe's chip/menu to apply it."
                )
            if has_secret(member, "deal_with_a_foe"):
                if self._deal_pass_available(session, tile):
                    hints.append(
                        f"Secret available: {member.name} may invoke Deal with a Foe to pass this room peacefully."
                    )
                else:
                    hints.append(
                        f"Secret available: {member.name} has Deal with a Foe. "
                        "Use it from the hero sheet and choose an eligible foe group to pass peacefully."
                    )
            if majors and has_secret(member, "enemy_in_dungeon") and not session.secret_enemy_foe_id:
                hints.append(
                    f"Secret available: {member.name} has Your Enemy Is in the Dungeon. "
                    "Choose a Major Foe from the hero sheet or click that foe's chip/menu to reveal it."
                )
            if guarded and has_secret(member, "prisoner"):
                hints.append(
                    f"Secret available: {member.name} has The Prisoner. "
                    "Open the hero sheet to choose the rescued NPC reward."
                )
            if morale_ready and has_secret(member, "terrifying_secret") and not session.terrifying_secret_pending_character_id:
                hints.append(
                    f"Secret available: {member.name} has Terrifying Secret. "
                    "Use it before the next foe morale test in this combat."
                )
            if has_secret(member, "true_name_spiritual_entity"):
                hints.append(
                    f"Secret available: {member.name} has True Name of a Spiritual Entity. "
                    "Use angelic rescue/healing from the hero sheet or click a foe for demonic damage."
                )
        return hints

    def _auto_check_surprise_reaction(self, session: SessionState, *, show_rolls: bool) -> bool:
        if not self._reactions_unresolved(session) or not session.party_surprised:
            return False
        session.log.append("Surprise: Reactions are mandatory, rolling now (p.146).")
        self._check_reaction(session, show_rolls=show_rolls)
        return True

    def _resolve_stale_combat(self, session: SessionState, *, log: bool = True) -> bool:
        if session.mode != "combat":
            return False
        tile = self._current_tile(session)
        if any(enemy.life > 0 for enemy in tile.enemies):
            return False
        self._clear_combat_statuses(session)
        session.combat_round = 0
        session.mode = "exploration"
        if log:
            session.log.append("No active foes remain; the encounter is over.")
        return True

    def _announce_encounter(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "exploration":
            return
        if not any(enemy.life > 0 for enemy in tile.enemies):
            return
        from .monster_combat_hooks import apply_mantlebeast_spot_on_entry, tile_has_lurking_mantlebeast

        if tile_has_lurking_mantlebeast(tile) and not tile.mantlebeast_ambush_resolved:
            fighters = combat_party(session, tile.id)
            apply_mantlebeast_spot_on_entry(session, tile, fighters, show_rolls=show_rolls)
            if tile.mantlebeast_spotted:
                return
        if not session.courtship_demesne_active:
            from .courtship_satyr_outdoor import try_satyr_auto_seduce_on_encounter

            if try_satyr_auto_seduce_on_encounter(self, session, tile, show_rolls=show_rolls):
                return
        self._ensure_capture_hideout_reaction(session, tile, show_rolls=show_rolls)
        if self._hideout_skips_auto_combat(session, tile):
            session.log.append(
                "The hideout guards may accept ransom. Pay ransom or start combat to rescue your comrades."
            )
            return
        self._begin_combat(
            session,
            "Encounter begins as foes are present.",
            tile=tile,
            show_rolls=show_rolls,
        )

    def _start_combat(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Combat is already underway.")
            return
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("There are no foes to fight.")
            return
        self._ensure_capture_hideout_reaction(session, tile, show_rolls=show_rolls)
        self._begin_combat(session, "Combat begins.", tile=tile, show_rolls=show_rolls)

    def _turn_back_from_mantlebeast(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Turn Back is only available during exploration.")
            return
        tile = self._current_tile(session)
        from .monster_combat_hooks import tile_has_lurking_mantlebeast

        if not tile.mantlebeast_spotted or not tile_has_lurking_mantlebeast(tile):
            session.log.append("There is no spotted lurking mantlebeast to avoid here.")
            return
        if not session.current_tile_entry_exit_id:
            session.log.append(
                "You cannot turn back — there is no recorded path to the room you came from."
            )
            return
        entry_exit = next(
            (item for item in tile.exits if item.id == session.current_tile_entry_exit_id),
            None,
        )
        if entry_exit is None or not entry_exit.destination_tile_id:
            session.log.append("You cannot turn back — the way you entered is blocked or unknown.")
            return
        previous = self._tile_by_id(session, entry_exit.destination_tile_id)
        if previous is None:
            session.log.append("You cannot turn back — the previous room is unreachable.")
            return
        reciprocal = next(
            (item for item in previous.exits if item.destination_tile_id == tile.id),
            None,
        )
        session.log.append(
            "Turn Back: having spotted the lurking mantlebeast on the ceiling, the party retreats "
            "through the passage they entered by, leaving it undisturbed (EE Fiendish Foes — no ambush, no combat)."
        )
        session.map_state.current_tile_id = previous.id
        session.current_tile_entry_exit_id = reciprocal.id if reciprocal else None
        self._sync_session_environment_from_tile(session, previous)
        self._maybe_wandering_on_backtrack(session, previous, show_rolls=show_rolls)

    def normalize_session(self, session: SessionState) -> tuple[SessionState, bool]:
        """Clear stale combat state before returning a session to the client."""
        changed = self._resolve_stale_combat(session, log=False)
        if self._ensure_individual_clues(session):
            changed = True
        entrance = self._entrance_tile(session)
        if self._ensure_entrance_dungeon_exit(entrance):
            changed = True
        if self._initialize_outside_entrance(entrance):
            changed = True
        if session.camped_outside and session.map_state.current_tile_id != entrance.id:
            session.map_state.current_tile_id = entrance.id
            session.current_tile_entry_exit_id = None
            changed = True
        if self._restore_entrance_visibility(session):
            changed = True
        if self._resume_orphaned_encounter(session):
            changed = True
        if self._auto_check_surprise_reaction(session, show_rolls=True):
            changed = True
        if self._resync_session_tile_layouts(session):
            changed = True
        if session.adventure_type == "imported":
            from .adventure_session import repair_imported_map_layout, repair_stuck_imported_treasure

            if repair_imported_map_layout(self, session):
                changed = True
            if repair_stuck_imported_treasure(session):
                changed = True
        if self._repair_incomplete_secret_passage(session, show_rolls=False):
            changed = True
        from .hirelings import repair_shared_marching_orders

        if repair_shared_marching_orders(session):
            changed = True
        if changed:
            self._touch(session)
        return session, changed

    def _sync_clue_total(self, session: SessionState) -> bool:
        total = sum(max(0, member.clues) for member in session.party)
        changed = session.clues_found != total
        session.clues_found = total
        return changed

    def _default_clue_holder(
        self, session: SessionState, character_id: str | None = None
    ) -> PartyMemberState | None:
        if character_id:
            selected = next(
                (
                    member
                    for member in session.party
                    if member.character_id == character_id and member.current_life > 0
                ),
                None,
            )
            if selected is not None:
                return selected
        living = [
            member
            for member in sorted(session.party, key=lambda item: item.marching_order)
            if member.current_life > 0
        ]
        if living:
            return living[0]
        return session.party[0] if session.party else None

    def _ensure_individual_clues(self, session: SessionState) -> bool:
        """Migrate legacy pooled Clues into an individual holder, then sync the display total."""
        member_total = sum(max(0, member.clues) for member in session.party)
        if session.clues_found > member_total:
            holder = self._default_clue_holder(session)
            if holder is not None:
                holder.clues += session.clues_found - member_total
                return self._sync_clue_total(session) or True
        return self._sync_clue_total(session)

    def _queue_fallen_transfer(self, session: SessionState) -> None:
        pending = session.pending_fallen_transfer
        if pending is not None:
            source = next((member for member in session.party if member.character_id == pending.from_character_id), None)
            if source is None or source.current_life > 0:
                session.pending_fallen_transfer = None
            elif pending.kind == "clues" and source.clues <= 0:
                session.pending_fallen_transfer = None
            elif pending.kind == "secrets" and not source.secrets:
                session.pending_fallen_transfer = None
        if session.pending_fallen_transfer is not None:
            return
        if not any(member.current_life > 0 for member in session.party):
            return
        clue_source = next((member for member in session.party if member.current_life <= 0 and member.clues > 0), None)
        if clue_source is not None:
            session.pending_fallen_transfer = PendingFallenTransferState(
                from_character_id=clue_source.character_id,
                kind="clues",
            )
            return
        secret_source = next((member for member in session.party if member.current_life <= 0 and member.secrets), None)
        if secret_source is not None:
            session.pending_fallen_transfer = PendingFallenTransferState(
                from_character_id=secret_source.character_id,
                kind="secrets",
            )

    def _resolve_fallen_transfer(
        self,
        session: SessionState,
        *,
        to_character_id: str | None,
        kind: str | None,
    ) -> None:
        pending = session.pending_fallen_transfer
        if pending is None:
            session.log.append("No fallen hero transfer is pending.")
            return
        source = next((member for member in session.party if member.character_id == pending.from_character_id), None)
        if source is None or source.current_life > 0:
            session.pending_fallen_transfer = None
            session.log.append("That fallen transfer is no longer needed.")
            return
        if kind and kind != pending.kind:
            session.log.append("Transfer kind does not match the pending inheritance.")
            return
        target = next(
            (member for member in session.party if member.character_id == to_character_id and member.current_life > 0),
            None,
        )
        if target is None:
            session.log.append("Choose a living hero to inherit from the fallen hero.")
            return
        if pending.kind == "clues":
            moved = max(0, source.clues)
            source.clues = 0
            target.clues += moved
            self._sync_clue_total(session)
            session.log.append(f"{target.name} inherits {moved} Clue(s) from fallen {source.name}.")
        else:
            moved = list(source.secrets)
            source.secrets = []
            target.secrets.extend(moved)
            session.log.append(f"{target.name} inherits {len(moved)} Secret(s) from fallen {source.name}.")
        session.pending_fallen_transfer = None
        self._queue_fallen_transfer(session)

    def _spend_clues(
        self,
        session: SessionState,
        amount: int,
        *,
        preferred_character_id: str | None = None,
    ) -> bool:
        if amount <= 0:
            return True
        from .hirelings import sage_clue_discount

        amount = sage_clue_discount(session, amount)
        self._ensure_individual_clues(session)
        if session.clues_found < amount:
            return False
        ordered: list[PartyMemberState] = []
        preferred = self._default_clue_holder(session, preferred_character_id)
        if preferred is not None:
            ordered.append(preferred)
        for member in sorted(session.party, key=lambda item: item.marching_order):
            if all(existing.character_id != member.character_id for existing in ordered):
                ordered.append(member)
        remaining = amount
        for member in ordered:
            if remaining <= 0:
                break
            held = max(0, member.clues)
            if held <= 0:
                continue
            spent = min(held, remaining)
            member.clues -= spent
            remaining -= spent
        self._sync_clue_total(session)
        return remaining == 0

    def _kerrak_dar_holder(self, session: SessionState) -> PartyMemberState | None:
        return next(
            (
                member
                for member in sorted(session.party, key=lambda item: item.marching_order)
                if member.current_life > 0 and KERRAK_DAR_STATUS in member.statuses
            ),
            None,
        )

    def _claim_kerrak_dar_hoard(self, session: SessionState) -> None:
        if session.mode != "exploration":
            session.log.append("Kerrak Dar's hoard can be searched for only during exploration.")
            return
        holder = self._kerrak_dar_holder(session)
        if holder is None:
            session.log.append("No active Kerrak Dar hoard reward is available.")
            return
        self._ensure_individual_clues(session)
        if not self._spend_clues(session, 1, preferred_character_id=holder.character_id):
            session.log.append(f"Kerrak Dar's hoard requires 1 held Clue (party has {session.clues_found}).")
            return
        tile = self._current_tile(session)
        survivors = [member for member in session.party if member.current_life > 0]
        servant_ids = {
            member.character_id
            for member in survivors
            if has_illusionary_servant(session, member.character_id)
        }
        leftover, payouts = distribute_gold_among(
            survivors,
            KERRAK_DAR_GOLD,
            servant_owner_ids=servant_ids,
        )
        if payouts:
            session.log.append(f"Kerrak Dar's hoard found: {', '.join(payouts)}.")
        if leftover:
            tile.treasure_gold += leftover
            tile.treasure_summary = (
                f"{tile.treasure_summary}; Kerrak Dar hoard remainder {leftover}gp"
                if tile.treasure_summary
                else f"Kerrak Dar hoard remainder {leftover}gp"
            )
            session.log.append(f"Kerrak Dar's hoard: {leftover}gp left on this tile due to carry limits.")
        holder.statuses = [status for status in holder.statuses if status != KERRAK_DAR_STATUS]
        session.log.append("Kerrak Dar's hoard reward is resolved.")

    def _resync_session_tile_layouts(self, session: SessionState) -> bool:
        """Refresh map element walkable/shape/image metadata from current tile definitions."""
        if self.rules is None:
            return False
        changed = False
        for tile in session.map_state.tiles:
            if self._resync_tile_from_definition(tile):
                changed = True
        return changed

    def _resync_tile_from_definition(self, tile: TileState) -> bool:
        if tile.content_key == "entrance":
            return False
        catalog = getattr(tile, "tile_catalog", "ee") or "ee"
        tile_def = self._load_tile_catalog(catalog).get(tile.tile_key)
        if tile_def is None:
            return False
        rotation = tile.rotation or 0
        width = tile.footprint_width
        height = tile.footprint_height
        rotated_width, rotated_height = self._rotated_size(width, height, rotation)
        changed = False
        for attr, value in (
            ("editor_cell_size", tile_def.editor_cell_size),
            ("image_scale", tile_def.image_scale),
            ("image_offset_x", tile_def.image_offset_x),
            ("image_offset_y", tile_def.image_offset_y),
            ("footprint_width", tile_def.footprint_width),
            ("footprint_height", tile_def.footprint_height),
        ):
            if getattr(tile, attr) != value:
                setattr(tile, attr, value)
                changed = True
        if self._is_truncated_tile(tile):
            return changed
        expected_walkable = self._rotated_walkable(tile_def, rotation, catalog=catalog)
        expected_shapes = self._rotated_cell_shapes(tile_def, rotation)
        if tile.walkable != expected_walkable:
            tile.walkable = expected_walkable
            changed = True
        if tile.cell_shapes != expected_shapes:
            tile.cell_shapes = expected_shapes
            changed = True
        expected_visible = self._visible_rows(rotated_width, rotated_height)
        if tile.visible != expected_visible and len(tile.visible or []) == rotated_height:
            if all(len(row) == rotated_width for row in tile.visible or []):
                if all(char == "1" for row in tile.visible or [] for char in row):
                    tile.visible = expected_visible
                    changed = True
        image = self._tile_image(tile.tile_key, tile_def.image if tile_def else None)
        if tile.image != image:
            tile.image = image
            changed = True
        return changed

    def _is_truncated_tile(self, tile: TileState) -> bool:
        return any("0" in row for row in tile.visible or [])

    def _is_entrance_tile(self, tile: TileState) -> bool:
        return tile.content_key == "entrance" or (
            tile.tile_key in ENTRANCE_TILE_KEYS and any(exit_state.dungeon_exit for exit_state in tile.exits)
        )

    def _restore_entrance_visibility(self, session: SessionState) -> bool:
        changed = False
        for tile in session.map_state.tiles:
            if not self._is_entrance_tile(tile):
                continue
            width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
            expected = self._visible_rows(width, height)
            if tile.visible != expected:
                tile.visible = expected
                changed = True
        return changed

    def _resume_orphaned_encounter(self, session: SessionState) -> bool:
        if session.mode != "exploration":
            return False
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            return False
        self._begin_combat(
            session,
            "Encounter resumes as foes are present.",
            tile=tile,
            show_rolls=False,
        )
        return True

    def _end_peaceful_encounter(self, session: SessionState, tile: TileState) -> None:
        tile.enemies = []
        session.reaction_pending = False
        session.reaction_checked = False
        session.reaction_key = None
        session.reaction_bribe_gold = 0
        session.reaction_bribe_weapons = 0
        session.reaction_bribe_gold_per_foe = 0
        session.reaction_bribe_weapons_per_foe = 0
        session.reaction_bribe_foe_count = 0
        session.reaction_trade_stock = []
        session.reaction_trade_active = False
        session.reaction_no_fools_gold = False
        session.reaction_sleep_attack_bonus = 0
        session.foes_strike_first = False
        session.foe_flee_strike_pending = False
        session.secret_weakness_foe_id = None
        session.secret_weakness_character_id = None
        session.secret_enemy_foe_id = None
        session.secret_enemy_character_id = None
        session.secret_chaos_fanatics_active = False
        session.terrifying_secret_pending_character_id = None
        session.combat_round = 0
        session.mode = "exploration"
        session.log.append("The encounter ends peacefully.")
        self._record_peaceful_quest_progress(session)

    def _clear_combat_statuses(self, session: SessionState) -> None:
        session.reaction_pending = False
        session.reaction_checked = False
        session.reaction_nudge_pending = False
        session.reaction_pre_adjust_roll = None
        session.reaction_key = None
        session.reaction_bribe_gold = 0
        session.reaction_bribe_weapons = 0
        session.reaction_bribe_gold_per_foe = 0
        session.reaction_bribe_weapons_per_foe = 0
        session.reaction_bribe_foe_count = 0
        session.reaction_trade_stock = []
        session.reaction_trade_active = False
        session.reaction_no_fools_gold = False
        session.reaction_sleep_attack_bonus = 0
        session.foes_strike_first = False
        session.party_surprised = False
        session.party_attacked_immediately = False
        session.foe_flee_strike_pending = False
        session.combat_lanterns_extinguished = False
        session.spear_shield_readied = []
        session.monster_encounter_start_applied = False
        session.missile_used_character_ids = []
        session.spell_used_character_ids = []
        session.summoned_beast_life = 0
        session.summoned_beast_owner_id = None
        self._end_bear_form(session)
        session.bear_form_owner_id = None
        session.bear_form_start_life = 0
        session.bear_form_pre_life = 0
        session.subdual_penalty_ignored = False
        session.illusionary_fog_active = False
        session.illusionary_servant_active = False
        session.illusionary_servant_owner_id = None
        session.wielded_melee_weapons = {}
        session.gladiator_counter_pending = {}
        session.gladiator_counter_used = []
        from .swashbuckler_traits import reset_swashbuckler_combat_flags

        reset_swashbuckler_combat_flags(session)
        session.evasion_character_ids = []
        session.secret_weakness_foe_id = None
        session.secret_weakness_character_id = None
        session.secret_chaos_fanatics_active = False
        session.terrifying_secret_pending_character_id = None
        for character_id, item in dict(session.expert_knife_thrown or {}).items():
            member = next((entry for entry in session.party if entry.character_id == character_id), None)
            if member is not None and item and item not in member.inventory:
                member.inventory.append(item)
        session.expert_knife_thrown = {}
        from .heroic_skill_effects import restore_forfeited_shields

        session.log.extend(restore_forfeited_shields(session))
        combat_statuses = {
            "protection",
            "barkskin",
            "illusionary armor",
            "bear form",
            "illusionary sword",
            "specter swarm",
            "mirror image",
            "strength +1",
        }
        for member in session.party:
            disease_statuses = [status for status in member.statuses if status.lower().startswith("disease pending:")]
            for status in disease_statuses:
                try:
                    damage = int(status.split(":", 1)[1].strip().split()[0])
                except (IndexError, ValueError):
                    damage = 1
                member.current_life = max(0, member.current_life - damage)
                session.log.append(f"{member.name} loses {damage} Life from lingering disease at encounter end.")
                if member.current_life <= 0:
                    session.log.append(f"{member.name} falls.")
            member.statuses = [
                status
                for status in member.statuses
                if status.split("(")[0].strip().lower() not in combat_statuses
                and not status.lower().startswith("mirror image")
                and not status.lower().startswith("poisoned")
                and not status.lower().startswith("disease pending:")
                and status.lower() not in {"attack penalty (poison) -1", "attack penalty (magic) -1", "no exploding attacks (fear)", "tar covered", "tar in eyes -1", "pinned by mantlebeast", "engulfed by acid cube", "confused (doppelganger)", "mantlebeast free strike"}
            ]

    def _check_reaction(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        reaction_adjust: int | None = None,
        glamour_mask_reroll: bool = False,
    ) -> None:
        if session.mode != "combat":
            session.log.append("There are no foes to check.")
            return
        tile = self._current_tile(session)
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            session.log.append("There are no active foes.")
            return
        if session.reaction_checked:
            session.log.append("Reactions were already checked this encounter.")
            return
        if any("final_boss" in enemy.tags for enemy in living_enemies):
            session.reaction_checked = True
            session.reaction_key = "fight_to_death"
            session.reaction_pending = False
            session.log.append("The Final Boss fights to the death!")
            return

        reaction_tables = self.rules.monsters().get("reaction_tables", {})
        if not isinstance(reaction_tables, dict):
            reaction_tables = {}
        source = resolve_reaction_source(living_enemies, reaction_tables)
        fighters = combat_party(session, tile.id)

        if session.reaction_nudge_pending:
            if reaction_adjust is None:
                session.log.append(
                    "Negotiator: Nudge the reaction roll ±1 using the buttons, or accept the result."
                )
                return
            roll = int(session.reaction_pre_adjust_roll or 1)
            session.reaction_nudge_pending = False
            session.reaction_pre_adjust_roll = None
            self._apply_reaction_outcome(
                session,
                tile,
                roll,
                max(-1, min(1, int(reaction_adjust))),
                source,
                living_enemies,
                fighters,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return

        roll = roll_d6()
        if glamour_mask_reroll:
            if not session.glamour_mask_reroll_available:
                session.log.append("Glamour Mask reroll is not available.")
                return
            mask_caster_id = session.glamour_mask_character_id
            if not mask_caster_id or not any(
                member.character_id == mask_caster_id for member in fighters
            ):
                session.log.append("The Glamour Mask wearer must be in this encounter to reroll.")
                return
            roll = roll_d6()
            session.glamour_mask_reroll_available = False
            if show_rolls:
                session.log.append(f"Glamour Mask reaction reroll: d6 = {roll}.")
        from .hirelings import apply_tailor_to_reaction_roll

        roll, tailor_log = apply_tailor_to_reaction_roll(
            session,
            roll,
            source=source,
            living_enemies=living_enemies,
            table_roller=self.table_roller,
        )
        session.log.extend(tailor_log)
        if source.inline_rows:
            table_label = f"{source.label} reaction table"
        else:
            table_label = source.table_name or "default_reaction_table"
        if show_rolls:
            session.log.append(f"Reaction roll: d6 = {roll} on {table_label}.")
        from .expert_skill_effects import has_skill
        from .heroic_skill_effects import has_heroic_skill

        can_nudge = any(has_skill(member, "negotiator") for member in fighters) or any(
            has_heroic_skill(member, "ambition") for member in fighters if member.current_life > 0
        )
        if can_nudge:
            session.reaction_nudge_pending = True
            session.reaction_pre_adjust_roll = roll
            labels: list[str] = []
            if any(has_skill(member, "negotiator") for member in fighters):
                labels.append("Negotiator")
            if any(has_heroic_skill(member, "ambition") for member in fighters if member.current_life > 0):
                labels.append("Ambition")
            session.log.append(
                f"{' / '.join(labels)}: you may Nudge this reaction result ±1 before the outcome is final."
            )
            return
        self._apply_reaction_outcome(
            session,
            tile,
            roll,
            0,
            source,
            living_enemies,
            fighters,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )

    def _apply_reaction_outcome(
        self,
        session: SessionState,
        tile: TileState,
        roll: int,
        reaction_adjust: int,
        source,
        living_enemies: list[EnemyState],
        fighters: list[PartyMemberState],
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        roll, negotiator_log = adjust_reaction_roll(fighters, roll, reaction_adjust)
        session.log.extend(negotiator_log)
        from .heroic_skill_effects import apply_song_of_elidra, beast_leadership_reaction_bonus

        song_party = self._song_of_elidra_party(session, tile.id)
        song_bonus, song_log = apply_song_of_elidra(session, song_party)
        if song_bonus:
            roll = max(1, min(6, roll + song_bonus))
            session.log.extend(song_log)
        beast_bonus, beast_log = beast_leadership_reaction_bonus(fighters, living_enemies)
        if beast_bonus:
            roll = max(1, min(6, roll + beast_bonus))
            session.log.extend(beast_log)
        from .forsaken_depths_citadel import fd_citadel_reaction_adjust

        citadel_adj, citadel_log = fd_citadel_reaction_adjust(session, tile)
        if citadel_adj:
            roll = max(1, min(6, roll + citadel_adj))
            session.log.extend(citadel_log)
        if source.inline_rows:
            row = lookup_reaction_row(source.inline_rows, roll)
            table_label = f"{source.label} reaction table"
        else:
            table_name = source.table_name or "default_reaction_table"
            row = self.table_roller.roll_reaction(table_name, roll)
            table_label = table_name
        if row is None:
            row = self.table_roller.roll_reaction("default_reaction_table", roll)
            table_label = "default_reaction_table"
        if row is None:
            row = {"key": "fight", "result": "The foes attack!", "foes_first": True}
        row = apply_reaction_overlays(row, living_enemies, roll)
        row = normalize_reaction_row(row)

        if explain_math:
            session.log.append("Reaction lookup uses monster bestiary tables when available, otherwise dungeon_tables.json.")

        hcl = self._highest_character_level(fighters)
        foe_count = len(living_enemies)
        outcome_foe_count = foe_count
        bribe_count_category = row.get("bribe_count_category")
        if bribe_count_category:
            counted = [
                enemy
                for enemy in living_enemies
                if enemy.category == str(bribe_count_category)
            ]
            if counted:
                outcome_foe_count = len(counted)
        outcome = build_reaction_outcome(row, hcl=hcl, foe_count=outcome_foe_count)
        session.reaction_checked = True
        session.reaction_key = outcome.key
        session.reaction_bribe_gold = outcome.bribe_gold
        session.reaction_bribe_weapons = outcome.bribe_weapons
        session.reaction_bribe_gold_per_foe = outcome.bribe_gold_per_foe
        session.reaction_bribe_weapons_per_foe = outcome.bribe_weapons_per_foe
        session.reaction_bribe_foe_count = outcome_foe_count
        session.reaction_no_fools_gold = bool(row.get("no_fools_gold"))
        session.log.append(outcome.result)

        if is_bribe_reaction(outcome.key) and dwarf_miser_blocks_bribe(fighters):
            session.log.append(
                "Reaction outcome: the dwarves refuse to pay (Miser trait with 2+ dwarves in the party)."
            )
            session.log.append("The party cannot bribe these foes; refuse and fight.")

        if outcome.key == "flee_if_outnumbered":
            if flee_if_outnumbered(living_enemies, fighters):
                session.log.append("Reaction outcome: foes flee because they are outnumbered; heroes may strike as they run.")
                session.log.append("The foes are outnumbered and flee.")
                session.reaction_pending = False
                self._resolve_foe_flee_strike(
                    session,
                    tile,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
            else:
                if row.get("fight_to_death_if_not_outnumbered"):
                    session.reaction_key = "fight_to_death"
                    session.log.append("Reaction outcome: foes are not outnumbered; they fight to the death.")
                else:
                    session.log.append("Reaction outcome: foes are not outnumbered; they attack first.")
                    session.log.append("The foes fight!")
                session.foes_strike_first = True
                session.reaction_pending = False
            return

        if outcome.key == "flee":
            session.log.append("Reaction outcome: foes flee; heroes may strike as they run.")
            session.reaction_pending = False
            self._resolve_foe_flee_strike(
                session,
                tile,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return

        if outcome.key in {"peaceful", "ignore", "offer_food"}:
            if outcome.key == "offer_food":
                session.log.append("Reaction outcome: the encounter ends peacefully and wounded heroes here may eat.")
            else:
                session.log.append("Reaction outcome: the encounter ends peacefully.")
            if outcome.key == "offer_food":
                for member in fighters:
                    if 0 < member.current_life < member.max_life:
                        member.current_life += 1
                        session.log.append(f"{member.name} eats and heals 1 Life.")
            self._end_peaceful_encounter(session, tile)
            return

        if outcome.key == "bribe":
            if dwarf_miser_blocks_bribe(fighters):
                session.log.append("Pay Bribe is unavailable while 2+ dwarves are in the party.")
                return
            if outcome.bribe_weapons:
                session.log.append(
                    "Reaction outcome: pay the demanded mix of gold/weapons to end peacefully, or refuse and fight."
                )
                session.log.append(
                    f"Bribe required: {outcome.bribe_gold}gp or {outcome.bribe_weapons} weapons "
                    f"({outcome.bribe_gold_per_foe}gp or {outcome.bribe_weapons_per_foe} weapon(s) per foe; mix allowed). "
                    "Pay bribe or fight."
                )
            else:
                session.log.append("Reaction outcome: pay the demanded gold to end peacefully, or refuse and fight.")
                session.log.append(f"Bribe required: {outcome.bribe_gold}gp total. Pay bribe or fight.")
            return

        if outcome.key == "trade_information":
            session.log.append("Reaction outcome: trade information, buy a Clue, or refuse and fight.")
            session.log.append(
                "Trade Information: sell shared clue information for 25gp per held Clue without losing Clues, "
                "buy 1 Clue for 100gp, or refuse and fight."
            )
            return

        if outcome.key == "offer_information":
            session.log.append("Reaction outcome: the foes offer information and the encounter ends peacefully.")
            if session.environment == "caverns":
                session.caverns_morlock_warning = True
                session.log.append("Effect: Morlock Spy warning recorded; morlocks cannot surprise the party until the caverns are left.")
            self._end_peaceful_encounter(session, tile)
            return

        if outcome.key == "sleep":
            self._apply_sleeping_foe_reaction(
                session,
                fighters,
                int(row.get("attack_bonus_first_round", 2)),
            )
            return

        if outcome.key in {
            "blood_offering",
            "quest",
            "buy_weapons",
            "bribe_food",
            "bribe_food_per_foe",
            "bribe_gold_or_food",
            "bribe_ration_gold_or_mushroom",
            "bribe_food_or_gem",
            "bribe_gem",
            "bribe_scrolls_or_potions",
            "bribe_gem_or_two_handed_weapon",
            "bribe_magic_item",
            "bribe_treasure_or_magic_item",
            "trial_of_champions",
            "challenge_of_champions",
            "trade",
        }:
            if outcome.key == "trade":
                stock, stock_log = self._roll_mushroom_picker_stock(show_rolls=show_rolls)
                session.reaction_trade_stock = stock
                session.reaction_trade_active = False
                session.log.extend(stock_log)
                if stock:
                    session.log.append(f"Stock for sale: {', '.join(stock)}.")
            session.log.append(
                "Reaction outcome: choose the offered reaction option to end peacefully, or refuse and fight."
            )
            return

        if outcome.key == "puzzle":
            session.log.append("Reaction outcome: solve the puzzle to end peacefully; failure gives foes the first strike.")
            self._resolve_reaction_challenge(
                session,
                tile,
                fighters,
                living_enemies,
                context="puzzle",
                label="Puzzle",
                success_log="The puzzle is solved; the foes let you pass.",
                failure_log="The puzzle fails; the foes attack first!",
                no_solver_log="No hero can attempt the puzzle; the foes attack first!",
                magical=False,
                show_rolls=show_rolls,
            )
            return

        if outcome.key == "magic_challenge":
            session.log.append(
                "Reaction outcome: answer the magical challenge to end peacefully; failure gives foes the first strike."
            )
            self._resolve_reaction_challenge(
                session,
                tile,
                fighters,
                living_enemies,
                context="magic_challenge",
                label="Magic Challenge",
                success_log="The magical challenge is answered; the foes let you pass.",
                failure_log="The magical challenge fails; the foes attack first!",
                no_solver_log="No hero can answer the magical challenge; the foes attack first!",
                magical=True,
                show_rolls=show_rolls,
            )
            return

        if outcome.key == "capture":
            tile = self._current_tile(session)
            living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
            foe_name = living_enemies[0].name if living_enemies else "Unknown Foe"
            session.capture_mode = True
            session.capture_foe_name = foe_name
            session.capture_origin_tile_id = session.map_state.current_tile_id
            session.log.append(
                "Reaction outcome: capture mode begins; heroes reduced to 0 Life are taken prisoner instead of slain."
            )
            session.log.append(
                "The foes try to take captives! They attack to subdue rather than kill. Foes attack first!"
            )
            session.foes_strike_first = True
            session.reaction_pending = False
            return

        session.foes_strike_first = outcome.foes_first or outcome.key in {"fight", "fight_to_death"}
        if outcome.key == "fight_to_death":
            session.log.append("Reaction outcome: foes attack first and will not make morale checks.")
        elif session.foes_strike_first:
            session.log.append("Reaction outcome: foes attack first.")
        else:
            session.log.append("Reaction outcome: combat begins.")
        session.reaction_pending = False

    def _resolve_reaction_challenge(
        self,
        session: SessionState,
        tile: TileState,
        fighters: list[PartyMemberState],
        living_enemies: list[EnemyState],
        *,
        context: str,
        label: str,
        success_log: str,
        failure_log: str,
        no_solver_log: str,
        magical: bool,
        show_rolls: bool = True,
    ) -> None:
        solver = next(
            (member for member in sorted(fighters, key=lambda item: item.marching_order) if member.current_life > 0),
            None,
        )
        challenge_level = max((enemy.level for enemy in living_enemies), default=1)
        if solver is None:
            session.log.append(no_solver_log)
            session.foes_strike_first = True
            session.reaction_pending = False
            return
        total, rolls = roll_exploding_for_level(solver)
        modifier = save_modifier(solver) + expert_puzzle_bonus(fighters)
        if magical and solver.class_id.lower() in {"wizard", "elf"}:
            modifier += solver.level
        elif not magical and solver.class_id.lower() in {"wizard", "elf", "illusionist", "druid"}:
            modifier += solver.level
        final_total = total + modifier
        if show_rolls:
            session.log.append(
                f"{label} Save: {solver.name} rolls {' + '.join(str(value) for value in rolls)} "
                f"+ {modifier} = {final_total} vs L{challenge_level}."
            )
        if final_total >= challenge_level:
            session.log.append(success_log)
            session.pending_save_reroll = None
            self._end_peaceful_encounter(session, tile)
            return
        session.pending_save_reroll = {
            "character_id": solver.character_id,
            "context": context,
            "level": challenge_level,
            "magical": magical,
            "modifier": modifier,
        }
        session.log.append(failure_log)
        session.foes_strike_first = True
        session.reaction_pending = False

    def _pay_bribe(self, session: SessionState, *, accept: bool, show_rolls: bool = True) -> None:
        if session.reaction_key != "bribe":
            session.log.append("No bribe is outstanding.")
            return
        tile = self._current_tile(session)
        fighters = combat_party(session, tile.id)
        if accept and dwarf_miser_blocks_bribe(fighters):
            session.log.append("Parties with 2+ dwarves cannot bribe foes (Miser trait).")
            return
        if not accept:
            session.log.append("You refuse to pay; the foes attack!")
            session.foes_strike_first = True
            session.reaction_pending = False
            return

        foe_count = session.reaction_bribe_foe_count or len([enemy for enemy in tile.enemies if enemy.life > 0])
        gold_per_foe = session.reaction_bribe_gold_per_foe
        weapons_per_foe = session.reaction_bribe_weapons_per_foe
        if gold_per_foe <= 0 and session.reaction_bribe_gold > 0 and foe_count > 0:
            gold_per_foe = session.reaction_bribe_gold // foe_count
        if weapons_per_foe <= 0 and session.reaction_bribe_weapons > 0 and foe_count > 0:
            weapons_per_foe = session.reaction_bribe_weapons // foe_count

        if not bribe_requirements_met(
            fighters,
            foe_count=foe_count,
            gold_per_foe=gold_per_foe,
            weapons_per_foe=weapons_per_foe,
        ):
            available_gold = sum(member.gold for member in fighters if member.current_life > 0)
            if weapons_per_foe > 0:
                session.log.append(
                    f"You cannot afford the bribe ({session.reaction_bribe_gold}gp or "
                    f"{session.reaction_bribe_weapons} weapons, mix allowed). The foes attack!"
                )
            else:
                session.log.append(
                    f"You need {session.reaction_bribe_gold}gp but only have "
                    f"{available_gold}gp here. The foes attack!"
                )
            session.foes_strike_first = True
            session.reaction_pending = False
            return

        gold_paid, weapons_paid, payment_log = pay_bribe_cost(
            fighters,
            foe_count=foe_count,
            gold_per_foe=gold_per_foe,
            weapons_per_foe=weapons_per_foe,
        )
        session.log.extend(payment_log)
        if show_rolls:
            parts = []
            if gold_paid:
                parts.append(f"{gold_paid}gp")
            if weapons_paid:
                parts.append(f"{weapons_paid} weapon(s)")
            summary = " and ".join(parts) if parts else "nothing"
            session.log.append(f"The party pays {summary}.")
        self._end_peaceful_encounter(session, tile)

    def _pay_bribe_fools_gold(self, session: SessionState, *, show_rolls: bool = True) -> None:
        if session.reaction_key != "bribe":
            session.log.append("No bribe is outstanding.")
            return
        if not (session.reaction_bribe_gold or session.reaction_bribe_gold_per_foe):
            session.log.append("Fools' Gold only satisfies gold bribes.")
            return
        if session.reaction_no_fools_gold:
            session.log.append("These foes cannot be fooled by Fools' Gold.")
            return
        tile = self._current_tile(session)
        fighters = combat_party(session, tile.id)
        if dwarf_miser_blocks_bribe(fighters):
            session.log.append("Parties with 2+ dwarves cannot bribe foes (Miser trait).")
            return
        from .equipment_effects import consume_fools_gold

        ok, message = consume_fools_gold(fighters)
        if not ok:
            session.log.append(message)
            return
        session.log.append(message)
        if show_rolls:
            session.log.append(
                "The magical pouch of fake gold satisfies the bribe no matter how much was demanded."
            )
        self._end_peaceful_encounter(session, tile)

    def _trade_information(self, session: SessionState, choice: str | None) -> None:
        if session.reaction_key != "trade_information":
            session.log.append("No Trade Information reaction is outstanding.")
            return
        self._ensure_individual_clues(session)
        tile = self._current_tile(session)
        fighters = combat_party(session, tile.id)
        if choice == "sell":
            clue_count = sum(max(0, member.clues) for member in fighters)
            if clue_count <= 0:
                session.log.append("The heroes here have no Clues to share as trade information.")
                return
            total_gold = clue_count * 25
            leftover, payouts = distribute_gold_among(
                fighters,
                total_gold,
                servant_owner_ids=self._servant_owner_ids(session),
            )
            if payouts:
                session.log.append(
                    f"The party shares information from {clue_count} Clue(s) for {total_gold - leftover}gp "
                    "(Clues are not spent)."
                )
                session.log.extend(payouts)
            if leftover:
                session.log.append(f"{leftover}gp cannot be carried and is left behind.")
            self._end_peaceful_encounter(session, tile)
            return
        if choice == "buy":
            if not bribe_requirements_met(
                fighters,
                foe_count=1,
                gold_per_foe=100,
                weapons_per_foe=0,
            ):
                available_gold = sum(member.gold for member in fighters if member.current_life > 0)
                session.log.append(f"The heroes here need 100gp to buy 1 Clue (have {available_gold}gp).")
                return
            gold_paid, _weapons_paid, payment_log = pay_bribe_cost(
                fighters,
                foe_count=1,
                gold_per_foe=100,
                weapons_per_foe=0,
            )
            session.log.extend(payment_log)
            holder_id = fighters[0].character_id if fighters else None
            self._grant_clue(session, tile, character_id=holder_id, add_object=False, source="buys")
            self._end_peaceful_encounter(session, tile)
            return
        if choice == "decline":
            session.log.append("The party refuses to trade information; the foes attack!")
            session.foes_strike_first = True
            session.reaction_pending = False
            return
        session.log.append("Choose whether to sell information, buy a Clue, or refuse.")

    def _reaction_choice(
        self,
        session: SessionState,
        choice: str | None,
        *,
        character_id: str | None = None,
        item_name: str | None = None,
        reaction_bribe_mode: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        key = session.reaction_key or ""
        tile = self._current_tile(session)
        fighters = combat_party(session, tile.id)
        if choice == "decline":
            self._reaction_declined(session, "The party refuses the reaction offer; the foes attack!")
            return
        if key == "trade" and choice == "done":
            if not session.reaction_trade_active:
                session.log.append("Open trade first, or refuse the offer.")
                return
            session.reaction_trade_stock = []
            session.reaction_trade_active = False
            self._end_peaceful_encounter(session, tile)
            return
        if choice != "accept":
            session.log.append("Choose whether to accept this reaction offer or refuse and fight.")
            return

        if key == "blood_offering":
            self._accept_blood_offering(session, tile, fighters, character_id=character_id, item_name=item_name)
            return
        if key == "quest":
            self._accept_reaction_quest(session, tile, show_rolls=show_rolls)
            return
        if key == "buy_weapons":
            self._accept_buy_weapons(session, tile, fighters, character_id=character_id, item_name=item_name)
            return
        if key in {"trial_of_champions", "challenge_of_champions"}:
            self._resolve_trial_of_champions(session, tile, fighters, character_id=character_id, show_rolls=show_rolls)
            return
        if key == "trade":
            if item_name:
                self._buy_mushroom_picker_stock(
                    session,
                    tile,
                    fighters,
                    character_id=character_id,
                    item_name=item_name,
                )
                return
            session.reaction_trade_active = True
            if session.reaction_trade_stock:
                session.log.append(
                    "Trade open: buy from the pickers' stock, then choose Done trading when finished."
                )
            else:
                session.log.append("The pickers have nothing left to sell; choose Done trading.")
            return
        if key.startswith("bribe_"):
            self._accept_special_bribe(
                session,
                tile,
                fighters,
                key,
                character_id=character_id,
                item_name=item_name,
                reaction_bribe_mode=reaction_bribe_mode,
            )
            return
        session.log.append("No special reaction offer is outstanding.")

    def _reaction_declined(self, session: SessionState, message: str) -> None:
        session.log.append(message)
        session.foes_strike_first = True
        session.reaction_pending = False

    def _resolve_trial_of_champions(
        self,
        session: SessionState,
        tile: TileState,
        fighters: list[PartyMemberState],
        *,
        character_id: str | None,
        show_rolls: bool,
    ) -> None:
        hero = self._reaction_member(fighters, character_id)
        if hero is None:
            session.log.append("Choose a living hero here as the party champion.")
            return
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        champion = next((enemy for enemy in living_enemies if "abyss_leader" in enemy.tags), None)
        if champion is None:
            champion = next((enemy for enemy in living_enemies if enemy.category == "boss"), None)
        if champion is None:
            champion = living_enemies[0] if living_enemies else None
        if champion is None:
            session.log.append("No foe champion remains for the Trial of Champions.")
            self._end_peaceful_encounter(session, tile)
            return
        original_level = champion.level
        if champion.category != "boss":
            champion.level += 2
            session.log.append(f"{champion.name} counts as L{champion.level} for the Trial of Champions.")
        turns = roll_d6()
        hero_first = roll_d6() <= 3
        if show_rolls:
            order = f"{hero.name} attacks first" if hero_first else f"{champion.name} attacks first"
            session.log.append(f"Trial of Champions: d6 = {turns} turn(s); initiative roll -> {order}.")
        hero_damage = 0
        foe_damage = 0
        for turn in range(1, turns + 1):
            if hero.current_life <= 0 or champion.life <= 0:
                break
            if hero_first:
                dealt = self._trial_hero_attack(session, hero, champion, turn=turn, show_rolls=show_rolls)
                hero_damage += dealt
                if champion.life <= 0:
                    break
                taken = self._trial_foe_attack(session, hero, champion, turn=turn, show_rolls=show_rolls)
                foe_damage += taken
            else:
                taken = self._trial_foe_attack(session, hero, champion, turn=turn, show_rolls=show_rolls)
                foe_damage += taken
                if hero.current_life <= 0:
                    break
                dealt = self._trial_hero_attack(session, hero, champion, turn=turn, show_rolls=show_rolls)
                hero_damage += dealt
        champion.level = original_level if champion.life > 0 else champion.level
        if champion.life <= 0:
            session.log.append(f"Trial won: {hero.name} defeats {champion.name}.")
            self._end_peaceful_encounter(session, tile)
            return
        if hero.current_life <= 0:
            session.log.append(f"Trial lost: {hero.name} falls to {champion.name}.")
            self._trial_lost(session, tile)
            return
        if hero_damage >= foe_damage:
            session.log.append(
                f"Trial won: {hero.name} inflicted {hero_damage} damage; {champion.name} inflicted {foe_damage}."
            )
            self._end_peaceful_encounter(session, tile)
            return
        session.log.append(
            f"Trial lost: {champion.name} inflicted {foe_damage} damage; {hero.name} inflicted {hero_damage}."
        )
        self._trial_lost(session, tile)

    def _trial_hero_attack(
        self,
        session: SessionState,
        hero: PartyMemberState,
        champion: EnemyState,
        *,
        turn: int,
        show_rolls: bool,
    ) -> int:
        total, rolls = roll_exploding_for_level(hero)
        total += hero.attack_bonus
        damage = attack_damage(total, champion.level)
        if damage:
            champion.life = max(0, champion.life - damage)
        if show_rolls:
            roll_text = " + ".join(str(value) for value in rolls)
            session.log.append(
                f"Trial turn {turn}: {hero.name} attacks {champion.name}: {roll_text} + {hero.attack_bonus} = "
                f"{total} vs L{champion.level}; {damage} damage."
            )
        return damage

    def _trial_foe_attack(
        self,
        session: SessionState,
        hero: PartyMemberState,
        champion: EnemyState,
        *,
        turn: int,
        show_rolls: bool,
    ) -> int:
        total, rolls = roll_exploding_for_level(hero)
        defense_total = total + hero.defense_bonus
        natural = rolls[0] if rolls else 1
        hit = natural == 1 or defense_total <= champion.level
        damage = 1 if hit else 0
        if damage:
            hero.current_life = max(0, hero.current_life - damage)
        if show_rolls:
            roll_text = " + ".join(str(value) for value in rolls)
            result = f"{damage} damage" if damage else "blocked"
            session.log.append(
                f"Trial turn {turn}: {hero.name} defends vs {champion.name}: {roll_text} + {hero.defense_bonus} = "
                f"{defense_total} vs L{champion.level}; {result}."
            )
        return damage

    def _trial_lost(self, session: SessionState, tile: TileState) -> None:
        for enemy in tile.enemies:
            if enemy.life > 0:
                enemy.level += 1
        session.log.append("The foes won the trial. If the party stays to fight, all surviving foes fight at +1 Level.")
        session.foes_strike_first = True
        session.reaction_pending = False

    def _accept_blood_offering(
        self,
        session: SessionState,
        tile: TileState,
        fighters: list[PartyMemberState],
        *,
        character_id: str | None,
        item_name: str | None,
    ) -> None:
        jar_holder = self._find_reaction_item_holder(fighters, item_name or "Jar of chicken blood", ["chicken blood"])
        if jar_holder is not None:
            member, index, item = jar_holder
            member.inventory.pop(index)
            session.log.append(f"{member.name} offers {item} for the Blood Offering.")
            self._end_peaceful_encounter(session, tile)
            return
        donor = self._reaction_member(fighters, character_id)
        if donor is None:
            session.log.append("Choose a living hero here to make the Blood Offering.")
            return
        if donor.current_life <= 2:
            session.log.append(f"{donor.name} cannot safely give 2 Life for the Blood Offering.")
            return
        donor.current_life -= 2
        session.log.append(f"Effect: {donor.name} gives blood and loses 2 Life ({donor.current_life}/{donor.max_life}).")
        self._end_peaceful_encounter(session, tile)

    def _accept_reaction_quest(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> None:
        if session.active_quest is not None:
            session.log.append("A Quest is already in progress; the party cannot accept another.")
            return
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Reaction Quest roll: d6 = {roll}.")
        row = self.table_roller.lookup("quest_table", roll)
        if row is None:
            session.log.append("Quest table lookup failed.")
            return
        gold_required = None
        item_name = None
        if row["key"] == "bring_gold":
            gold_required = roll * 50
            party_gold = sum(member.gold for member in combat_party(session, tile.id) if member.current_life > 0)
            if party_gold >= gold_required:
                gold_required *= 2
                session.log.append(f"Party already has {party_gold}gp; quest gold doubled to {gold_required}gp.")
        if row["key"] == "bring_item":
            magic_row = self.table_roller.lookup("dungeon_magic_treasure_table", roll_d6())
            if magic_row and magic_row.get("items"):
                item_name = magic_row["items"][0]
            elif magic_row:
                item_name = magic_row.get("result", "Magic item")
            else:
                item_name = "Magic item"
        boss_target_name = self._roll_quest_boss_target_name(session) if row["key"] == "bring_head" else None
        session.active_quest = quest_from_row(
            row,
            tile_id=tile.id,
            gold_required=gold_required,
            item_name=item_name,
            boss_target_name=boss_target_name,
        )
        session.log.append(f"Quest accepted from reaction: {session.active_quest.description}")
        if boss_target_name:
            session.log.append(
                f"Quest target: {boss_target_name}. The next Boss encounter may be treated as this Quest target."
            )
        self._end_peaceful_encounter(session, tile)

    def _roll_mushroom_picker_stock(self, *, show_rolls: bool) -> tuple[list[str], list[str]]:
        log: list[str] = []
        mushroom_count = roll_d6()
        ration_count = roll_formula("2d6")
        if show_rolls:
            log.append(f"Halfling mushroom picker stock: d6 = {mushroom_count} rare mushroom roll(s).")
            log.append(f"Halfling mushroom picker stock: 2d6 = {ration_count} Food ration(s).")
        stock: list[str] = []
        for _ in range(mushroom_count):
            sub_roll = roll_d6()
            row = self.table_roller.lookup("fungal_grottoes_rare_mushroom_table", sub_roll)
            if row and row.get("items"):
                item = str(row["items"][0])
                stock.append(item)
                if show_rolls:
                    log.append(f"  Rare mushroom roll: d6 = {sub_roll} -> {item}.")
        stock.extend(["Food ration"] * ration_count)
        return stock, log

    def _mushroom_picker_price(self, session: SessionState, fighters: list[PartyMemberState], item_name: str) -> int | None:
        base = mushroom_standard_buy_price(item_name)
        if base is None:
            return None
        if party_has_halfling(fighters):
            return (base * 9) // 10
        return base

    def _spend_members_gold(self, members: list[PartyMemberState], amount: int) -> tuple[bool, list[str]]:
        living = [member for member in members if member.current_life > 0]
        if sum(member.gold for member in living) < amount:
            return False, []
        remaining = amount
        paid: list[str] = []
        for member in living:
            take = min(member.gold, remaining)
            if take <= 0:
                continue
            member.gold -= take
            remaining -= take
            paid.append(f"{member.name} -{take}gp")
            if remaining <= 0:
                break
        return True, [f"Payment: {', '.join(paid)}."]

    def _buy_mushroom_picker_stock(
        self,
        session: SessionState,
        tile: TileState,
        fighters: list[PartyMemberState],
        *,
        character_id: str | None,
        item_name: str,
    ) -> None:
        session.reaction_trade_active = True
        trimmed = item_name.strip()
        try:
            stock_index = session.reaction_trade_stock.index(trimmed)
        except ValueError:
            session.log.append(f"{trimmed} is not in the pickers' stock.")
            return
        buyer = self._reaction_member(fighters, character_id)
        if buyer is None:
            session.log.append("Choose a living hero here to receive the purchase.")
            return
        price = self._mushroom_picker_price(session, fighters, trimmed)
        if price is None:
            session.log.append(f"The pickers cannot price {trimmed}.")
            return
        can_receive, reason = can_add_item(
            buyer,
            trimmed,
            servant_active=buyer.character_id in self._servant_owner_ids(session),
        )
        if not can_receive:
            session.log.append(reason)
            return
        paid, payment_log = self._spend_members_gold(fighters, price)
        if not paid:
            discount = " (-10% halfling discount)" if party_has_halfling(fighters) else ""
            session.log.append(f"The party needs {price}gp here to buy {trimmed}{discount}.")
            return
        del session.reaction_trade_stock[stock_index]
        buyer.inventory.append(trimmed)
        prune_weapon_defaults(buyer)
        session.log.extend(payment_log)
        discount_note = " (halfling discount applied)" if party_has_halfling(fighters) else ""
        session.log.append(f"{buyer.name} buys {trimmed} from the pickers for {price}gp{discount_note}.")

    def _accept_buy_weapons(
        self,
        session: SessionState,
        tile: TileState,
        fighters: list[PartyMemberState],
        *,
        character_id: str | None,
        item_name: str | None,
    ) -> None:
        if any(member.class_id.lower() in {"dwarf", "elf"} for member in fighters if member.current_life > 0):
            session.log.append("The cave orcs will not buy weapons while dwarves or elves are present.")
            self._reaction_declined(session, "The weapon sale fails; the cave orcs attack!")
            return
        sale = self._find_sale_weapon(fighters, character_id=character_id, item_name=item_name)
        if sale is None:
            session.log.append("Choose a weapon above Cheap quality to sell to the cave orcs.")
            return
        member, index, item, price = sale
        member.inventory.pop(index)
        carried_room = max(0, MAX_CARRIED_GOLD - member.gold)
        paid = min(price, carried_room)
        member.gold += paid
        leftover = price - paid
        if leftover:
            tile.treasure_gold = (tile.treasure_gold or 0) + leftover
        session.log.append(f"{member.name} sells {item} to the cave orcs for {price}gp.")
        if leftover:
            session.log.append(f"{leftover}gp cannot be carried and is left on the floor.")
        self._end_peaceful_encounter(session, tile)

    def _accept_special_bribe(
        self,
        session: SessionState,
        tile: TileState,
        fighters: list[PartyMemberState],
        key: str,
        *,
        character_id: str | None,
        item_name: str | None,
        reaction_bribe_mode: str | None = None,
    ) -> bool:
        if is_bribe_reaction(key) and dwarf_miser_blocks_bribe(fighters):
            session.log.append("Parties with 2+ dwarves cannot bribe foes (Miser trait).")
            return False
        foe_count = session.reaction_bribe_foe_count or len([enemy for enemy in tile.enemies if enemy.life > 0]) or 1
        catalog = self.rules.equipment_shop()

        def finish(ok: bool) -> bool:
            if ok:
                self._end_peaceful_encounter(session, tile)
            return ok

        if key == "bribe_magic_item":
            if self._pay_named_items(
                session,
                fighters,
                ["magic"],
                1,
                item_name=item_name,
                character_id=character_id,
                catalog=catalog,
            ):
                return finish(True)
            session.log.append("Need 1 magic item carried here to pay this bribe.")
            return False
        if key == "bribe_food":
            return finish(self._pay_food_bribe(session, fighters, 4))
        if key == "bribe_food_per_foe":
            return finish(self._pay_food_bribe(session, fighters, foe_count))
        if key == "bribe_gold_or_food":
            if reaction_bribe_mode == "food":
                ok = self._pay_food_bribe(session, fighters, 5)
            elif reaction_bribe_mode == "gold":
                ok = self._pay_gold_bribe(session, fighters, 15)
            else:
                ok = self._pay_food_bribe(session, fighters, 5, quiet=True) or self._pay_gold_bribe(
                    session, fighters, 15
                )
            if not ok:
                session.log.append("Need 5 Food rations or 15gp here to pay this bribe.")
            return finish(ok)
        if key == "bribe_ration_gold_or_mushroom":
            if reaction_bribe_mode == "food":
                ok = self._pay_food_bribe(session, fighters, foe_count)
            elif reaction_bribe_mode == "mushroom":
                ok = self._pay_named_items(
                    session,
                    fighters,
                    ["mushroom"],
                    foe_count,
                    item_name=item_name,
                    character_id=character_id,
                    catalog=catalog,
                )
            elif reaction_bribe_mode == "gold":
                ok = self._pay_gold_bribe(session, fighters, 5 * foe_count)
            else:
                ok = (
                    self._pay_food_bribe(session, fighters, foe_count, quiet=True)
                    or self._pay_named_items(
                        session,
                        fighters,
                        ["mushroom"],
                        foe_count,
                        item_name=item_name,
                        character_id=character_id,
                        quiet=True,
                        catalog=catalog,
                    )
                    or self._pay_gold_bribe(session, fighters, 5 * foe_count)
                )
            if not ok:
                session.log.append(f"Need {foe_count} Food/Mushroom item(s) or {5 * foe_count}gp here.")
            return finish(ok)
        if key == "bribe_food_or_gem":
            if reaction_bribe_mode == "food":
                ok = self._pay_food_bribe(session, fighters, foe_count)
            elif item_name:
                ok = self._pay_named_items(
                    session,
                    fighters,
                    ["gem"],
                    1,
                    item_name=item_name,
                    character_id=character_id,
                    catalog=catalog,
                )
            else:
                ok = self._pay_named_items(
                    session,
                    fighters,
                    ["gem"],
                    1,
                    item_name=item_name,
                    character_id=character_id,
                    quiet=True,
                    catalog=catalog,
                ) or self._pay_food_bribe(session, fighters, foe_count)
            if not ok:
                session.log.append(f"Need 1 gem or {foe_count} Food ration(s) here.")
            return finish(ok)
        if key == "bribe_gem":
            if self._pay_named_items(
                session,
                fighters,
                ["gem"],
                1,
                item_name=item_name,
                character_id=character_id,
                catalog=catalog,
            ):
                return finish(True)
            session.log.append("Need 1 gem carried here to pay this bribe.")
            return False
        if key == "bribe_scrolls_or_potions":
            if self._pay_named_items(
                session,
                fighters,
                ["scroll", "potion"],
                2,
                item_name=item_name,
                character_id=character_id,
                catalog=catalog,
            ):
                return finish(True)
            session.log.append("Need 2 scroll or potion items carried here to pay this bribe.")
            return False
        if key == "bribe_gem_or_two_handed_weapon":
            if self._pay_named_items(
                session,
                fighters,
                ["gem", "two-handed weapon", "heavy weapon"],
                1,
                item_name=item_name,
                character_id=character_id,
                catalog=catalog,
            ):
                return finish(True)
            session.log.append("Need 1 gem or heavy/two-handed weapon carried here to pay this bribe.")
            return False
        if key == "bribe_treasure_or_magic_item":
            if reaction_bribe_mode == "all_gold":
                total = sum(member.gold for member in fighters if member.current_life > 0)
                if total < 100:
                    session.log.append(
                        f"Need all carried gold with a minimum of 100gp, or 1 magic item (have {total}gp here)."
                    )
                    return False
                paid = 0
                for member in fighters:
                    paid += member.gold
                    member.gold = 0
                session.log.append(f"The party gives the dragon all carried gold here ({paid}gp).")
                return finish(True)
            if self._pay_named_items(
                session,
                fighters,
                ["magic"],
                1,
                item_name=item_name,
                character_id=character_id,
                quiet=True,
                catalog=catalog,
            ):
                return finish(True)
            if reaction_bribe_mode is None and item_name is None:
                total = sum(member.gold for member in fighters if member.current_life > 0)
                if total < 100:
                    session.log.append(
                        f"Need all carried gold with a minimum of 100gp, or 1 magic item (have {total}gp here)."
                    )
                    return False
                paid = 0
                for member in fighters:
                    paid += member.gold
                    member.gold = 0
                session.log.append(f"The party gives the dragon all carried gold here ({paid}gp).")
                return finish(True)
            session.log.append("Need 1 magic item or at least 100gp carried here to pay this bribe.")
            return False
        session.log.append("This bribe type is not yet automated.")
        return False

    def _reaction_member(
        self,
        fighters: list[PartyMemberState],
        character_id: str | None,
    ) -> PartyMemberState | None:
        living = [member for member in fighters if member.current_life > 0]
        if character_id:
            return next((member for member in living if member.character_id == character_id), None)
        return living[0] if living else None

    def _pay_gold_bribe(self, session: SessionState, fighters: list[PartyMemberState], amount: int) -> bool:
        if not bribe_requirements_met(fighters, foe_count=1, gold_per_foe=amount, weapons_per_foe=0):
            return False
        gold_paid, _weapons_paid, payment_log = pay_bribe_cost(
            fighters,
            foe_count=1,
            gold_per_foe=amount,
            weapons_per_foe=0,
        )
        session.log.extend(payment_log)
        session.log.append(f"The party pays {gold_paid}gp.")
        return True

    def _pay_food_bribe(
        self,
        session: SessionState,
        fighters: list[PartyMemberState],
        count: int,
        *,
        quiet: bool = False,
    ) -> bool:
        if count_bribe_food_value(fighters) < count:
            if not quiet:
                session.log.append(
                    f"Need {count} Food ration(s) here to pay this bribe "
                    f"(Brown Cap Delight counts as 3 rations)."
                )
            return False
        consume_bribe_food_value(fighters, count)
        session.log.append(f"The party gives {count} Food ration(s).")
        return True

    def _pay_named_items(
        self,
        session: SessionState,
        fighters: list[PartyMemberState],
        keywords: list[str],
        count: int,
        *,
        item_name: str | None = None,
        character_id: str | None = None,
        quiet: bool = False,
        catalog: dict | None = None,
    ) -> bool:
        paid: list[str] = []
        for _ in range(count):
            found = self._find_reaction_item_holder(fighters, item_name, keywords, character_id=character_id)
            if found is None:
                if not quiet:
                    label = " or ".join(keywords)
                    session.log.append(f"Need {count} item(s) matching {label} here.")
                return False
            member, index, item = found
            member.inventory.pop(index)
            paid.append(f"{member.name} gives {item}")
            if "gem" in keywords and catalog is not None:
                counted = jewelry_bribe_counted_gp(item, member.class_id, catalog)
                if counted is not None:
                    session.log.append(f"Counted gem value for bribe: {counted}gp ({item}).")
            item_name = None
            character_id = None
        session.log.extend(paid)
        return True

    def _find_reaction_item_holder(
        self,
        fighters: list[PartyMemberState],
        item_name: str | None,
        keywords: list[str],
        *,
        character_id: str | None = None,
    ) -> tuple[PartyMemberState, int, str] | None:
        normalized_item = item_name.strip().lower() if item_name else ""
        for member in fighters:
            if member.current_life <= 0:
                continue
            if character_id and member.character_id != character_id:
                continue
            for index, item in enumerate(member.inventory):
                lower = item.lower()
                if normalized_item and lower != normalized_item:
                    continue
                if "magic" in keywords:
                    if "magic" in lower or any(word in lower for word in ("wand", "staff of", "+1", "+2", "scroll", "potion")):
                        return member, index, item
                    continue
                if "gem" in keywords and "map fragment" in lower:
                    return member, index, item
                if any(keyword in lower for keyword in keywords):
                    return member, index, item
        return None

    def _find_sale_weapon(
        self,
        fighters: list[PartyMemberState],
        *,
        character_id: str | None,
        item_name: str | None,
    ) -> tuple[PartyMemberState, int, str, int] | None:
        for member in fighters:
            if member.current_life <= 0:
                continue
            if character_id and member.character_id != character_id:
                continue
            for index, item in enumerate(member.inventory):
                if item_name and item.lower() != item_name.lower():
                    continue
                if "cheap" in item.lower() or not self._reaction_weapon_price(item):
                    continue
                price = self._reaction_weapon_price(item)
                if price:
                    return member, index, item, price
        return None

    def _reaction_weapon_price(self, item: str) -> int:
        parsed = _parse_weapon_item(item)
        if parsed is None:
            return 0
        lower = item.lower()
        if "bow" in lower:
            return 15
        if "sling" in lower:
            return 4
        if "two-handed" in lower or "heavy weapon" in lower or "staff" in lower:
            return 15
        if "light" in lower or "dagger" in lower or "knife" in lower:
            return 5
        return 6

    def _resolve_captures(
        self,
        session: SessionState,
        tile: TileState,
        fallen_now: list[str],
    ) -> list[str]:
        """In capture mode, heroes who reached 0 Life are taken prisoner rather than fallen.

        One foe escapes with each captive (cannot be attacked during flight).
        Returns the subset of fallen_now that should still be treated as fallen (empty in full capture mode).
        """
        if not fallen_now:
            return fallen_now
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        newly_captured: list[str] = []
        truly_fallen: list[str] = []
        for character_id in fallen_now:
            member = next((pc for pc in session.party if pc.character_id == character_id), None)
            if member is None:
                truly_fallen.append(character_id)
                continue
            if living_enemies:
                escort = living_enemies.pop()
                escort.life = 0
                session.log.append(
                    f"{member.name} is knocked out and taken captive! "
                    f"One {escort.name} flees with them — it cannot be attacked."
                )
            else:
                session.log.append(
                    f"{member.name} is knocked out. The foes wanted to take them captive, "
                    "but have no escort left — they cannot carry another prisoner."
                )
                truly_fallen.append(character_id)
                continue
            if character_id not in session.captured_character_ids:
                session.captured_character_ids.append(character_id)
            stripped = self._strip_captive(session, member)
            if stripped:
                treasure_gp = stripped.get("gold", 0)
                if treasure_gp:
                    tile.treasure_gold = (tile.treasure_gold or 0) + treasure_gp
                equipment_count = stripped.get("equipment_count", 0)
                if equipment_count:
                    session.log.append(f"{member.name}'s equipment is carried off with them.")
            newly_captured.append(character_id)
        if newly_captured:
            session.log.append(
                f"Spend 3 Clues on the 'Someone Has Been Imprisoned' Secret to find the captive hideout."
            )
        return truly_fallen

    def _strip_captive(self, session: SessionState, member: "PartyMemberState") -> dict:
        """Remove a captured hero's gold and portable items; return stripped values."""
        stripped: dict = {}
        if member.gold > 0:
            stripped["gold"] = member.gold
            member.gold = 0
        has_equipment = bool(
            member.inventory
            or member.default_melee_weapon
            or member.default_melee_weapon_secondary
            or member.default_missile_weapon
        )
        if has_equipment:
            existing = session.captured_stripped_equipment.get(member.character_id)
            if isinstance(existing, dict):
                existing = CapturedEquipmentState(**existing)
            equipment = CapturedEquipmentState(
                inventory=list(existing.inventory if existing else []) + list(member.inventory),
                default_melee_weapon=(existing.default_melee_weapon if existing else None) or member.default_melee_weapon,
                default_melee_weapon_secondary=(
                    existing.default_melee_weapon_secondary if existing else None
                )
                or member.default_melee_weapon_secondary,
                default_missile_weapon=(existing.default_missile_weapon if existing else None)
                or member.default_missile_weapon,
            )
            session.captured_stripped_equipment[member.character_id] = equipment
            stripped["equipment_count"] = len(member.inventory)
            member.inventory = []
            member.default_melee_weapon = None
            member.default_melee_weapon_secondary = None
            member.default_missile_weapon = None
        return stripped

    def _restore_captive_equipment(self, session: SessionState, member: PartyMemberState) -> bool:
        equipment = session.captured_stripped_equipment.pop(member.character_id, None)
        if equipment is None:
            return False
        if isinstance(equipment, dict):
            equipment = CapturedEquipmentState(**equipment)
        member.inventory.extend(equipment.inventory)
        member.default_melee_weapon = equipment.default_melee_weapon
        member.default_melee_weapon_secondary = equipment.default_melee_weapon_secondary
        member.default_missile_weapon = equipment.default_missile_weapon
        return bool(
            equipment.inventory
            or equipment.default_melee_weapon
            or equipment.default_melee_weapon_secondary
            or equipment.default_missile_weapon
        )

    def _cast_spell(
        self,
        session: SessionState,
        character_id: str | None,
        spell_name: str | None,
        *,
        exit_id: str | None = None,
        target_character_id: str | None = None,
        target_foe_id: str | None = None,
        secondary_foe_id: str | None = None,
        spell_target_mode: str | None = None,
        life_transfer_amount: int | None = None,
        teleport_tile_id: str | None = None,
        teleport_character_ids: list[str] | None = None,
        mass_blessing_target_ids: list[str] | None = None,
        mass_blessing_condition_choices: dict[str, list[str]] | None = None,
        courtship_choice: str | None = None,
        from_scroll: bool = False,
        scroll_item: str | None = None,
        from_magic_item: bool = False,
        magic_item: str | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
        echo_repeat: bool = False,
        wand_power_charges: int | None = None,
        use_prayer_bead: bool = False,
        item_name: str | None = None,
    ) -> None:
        if not spell_name:
            session.log.append("Choose a spell to cast.")
            return
        tile = self._current_tile(session)
        fighters = combat_party(session, tile.id)
        fighter_ids = {member.character_id for member in fighters}
        caster = next((member for member in session.party if member.character_id == character_id), None)
        if caster is None:
            caster = next(
                (member for member in sorted(fighters, key=lambda item: item.marching_order) if member.current_life > 0),
                None,
            )
        if caster is None or caster.current_life <= 0:
            session.log.append("That hero cannot cast.")
            return
        from_item = from_scroll or from_magic_item
        if caster.class_id.lower() == "conservationist":
            from .courtship_classes import conservationist_forbidden_spell_attempt

            allowed, reason = conservationist_forbidden_spell_attempt(
                session,
                caster,
                spell_name,
                engine=self,
                show_rolls=show_rolls,
            )
            if not allowed:
                session.log.append(reason or f"{caster.name} cannot cast {spell_name}.")
                return
        from .courtship_blossoms_spells import cast_blossoms_spell, is_blossoms_spell
        from .courtship_classes import is_satyr, satyr_blossoms_casts_remaining

        if (
            is_satyr(caster)
            and is_blossoms_spell(spell_name or "")
            and not from_item
            and not echo_repeat
        ):
            remaining = satyr_blossoms_casts_remaining(session, caster)
            if remaining is not None and remaining <= 0:
                session.log.append(
                    f"{caster.name} has already cast an innate Blossoms spell this adventure "
                    f"({caster.level} time(s) per level, TCOTFD p.11)."
                )
                return
            tile = self._current_tile(session)
            if tile is None:
                session.log.append("No map tile for the Blossoms spell.")
                return
            pending_before = session.courtship_pending_choice
            if cast_blossoms_spell(
                self,
                session,
                caster,
                spell_name or "",
                tile,
                target_character_id=target_character_id,
                courtship_choice=courtship_choice,
                show_rolls=show_rolls,
                from_scroll=False,
            ):
                if session.courtship_pending_choice == pending_before:
                    from .courtship_classes import note_satyr_blossoms_cast

                    note_satyr_blossoms_cast(session, caster)
                return
            return
        if caster.character_id not in fighter_ids:
            session.log.append(f"{caster.name} is not on the current map element.")
            return
        if barbarian_cannot_use_magic(caster.class_id) and from_item:
            session.log.append("Barbarians cannot use magic items or scrolls.")
            return

        spell_key = normalize_spell_name(spell_name)
        in_combat = session.mode == "combat"
        from_garment_escape = False
        if spell_key == "escape" and not from_item and not echo_repeat and not in_combat:
            from .expert_skill_effects import can_use_phasing_panther_escape, wears_arcane_garment

            if can_use_phasing_panther_escape(caster, session):
                from_garment_escape = True
            elif wears_arcane_garment(caster, phasing=True):
                if caster.class_id.lower() == "barbarian":
                    session.log.append("Barbarians will not use the Phasing Panther Garment.")
                else:
                    session.log.append(
                        f"{caster.name} has already used the Phasing Panther Garment this adventure."
                    )
                return
        if not from_item and not echo_repeat and not from_garment_escape:
            if not knows_spell(caster, spell_name):
                session.log.append(f"{caster.name} does not know {spell_name}.")
                return
            if not can_cast_spell(
                caster,
                spell_name,
                expended_spells=session.expended_spells.get(caster.character_id, []),
                healing_prayer_uses=session.healing_prayer_uses.get(caster.character_id, 0),
            ):
                session.log.append(f"{caster.name} cannot cast {spell_name} again this adventure.")
                return
        elif not from_item and not from_garment_escape and not knows_spell(caster, spell_name):
            session.log.append(f"{caster.name} does not know {spell_name}.")
            return
        elif from_scroll and scroll_item and scroll_item not in caster.inventory:
            session.log.append(f"{caster.name} does not have that scroll.")
            return
        elif from_magic_item and magic_item and magic_item not in caster.inventory:
            session.log.append(f"{caster.name} does not have that magic item.")
            return

        from .forsaken_depths_heroic_spells import clear_eldritch_fist_on_cast

        if spell_key != "eldritch_fist":
            session.log.extend(clear_eldritch_fist_on_cast(session, caster.character_id))

        no_foe_ok = spell_key in EXPLORATION_SPELLS or from_item or from_garment_escape
        if in_combat and not from_item and not echo_repeat:
            if caster.character_id in session.spell_used_character_ids:
                session.log.append(f"{caster.name} has already cast a spell this combat round.")
                return
        if in_combat and not no_foe_ok and not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("There are no foes to target.")
            return
        if in_combat and self._reactions_unresolved(session):
            if not self._commit_immediate_attack(session):
                return
        if not in_combat:
            exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
            door_type = exit_state.door_type if exit_state and exit_state.kind == "door" else None
            from .courtship_blossoms_spells import is_blossoms_spell

            allowed = spell_key in EXPLORATION_SPELLS or from_garment_escape
            allowed = allowed or (from_scroll and is_blossoms_spell(spell_name or ""))
            allowed = allowed or (
                is_satyr(caster) and is_blossoms_spell(spell_name or "") and not from_item
            )
            allowed = allowed or (spell_key in {"fireball", "lightning"} and door_type == "iron")
            allowed = allowed or (spell_key == "warp_wood" and door_type in {"locked", "lever", "unlocked", "trap_door"})
            from .forsaken_depths_heroic_spells import heroic_spell_id, is_fd_heroic_spell

            if is_fd_heroic_spell(spell_name or ""):
                heroic_key = heroic_spell_id(spell_name or "")
                if heroic_key in {"mass_blessing", "boatmans_luck"}:
                    allowed = True
                if heroic_key == "eldritch_fist" and door_type:
                    allowed = True
            allowed = allowed or (from_scroll and is_fd_heroic_spell(spell_name or ""))
            if spell_key == "mass_teleport" and not teleport_tile_id:
                session.log.append("Choose a visited room for Mass Teleport.")
                return
            if spell_key == "lifeforce_control" and not life_transfer_amount:
                session.log.append("Choose how much Life to transfer with Lifeforce Control.")
                return
            if not allowed:
                session.log.append("Cast that spell during combat, or use exploration spells (Escape, Blessing, Healing prayer, Protection).")
                return
            if spell_key == "mass_teleport":
                visited = {tile.id for tile in session.map_state.tiles}
                if teleport_tile_id not in visited:
                    session.log.append("Mass Teleport can only reach rooms the party has already visited.")
                    return

        exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
        door_type = exit_state.door_type if exit_state and exit_state.kind == "door" else None
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {member.character_id for member in session.party if member.current_life > 0}
        enemies_before_spell = [enemy.model_copy(deep=True) for enemy in tile.enemies]
        wand_item: str | None = None
        if wand_power_charges and wand_power_charges > 0:
            if caster.class_id.lower() != "wizard":
                session.log.append("Only wizards can channel a Wand of Power.")
                return
            wand_item = next((item for item in caster.inventory if is_wand_of_power(item)), None)
            if wand_item is None:
                session.log.append(f"{caster.name} has no Wand of Power.")
                return
            available = parse_wand_of_power_charges(wand_item)
            if available is None or wand_power_charges > available:
                session.log.append("Not enough charges remain on the Wand of Power.")
                return
            apply_wand_cast_bonus(caster, wand_power_charges)
            if show_rolls:
                session.log.append(
                    f"{caster.name} channels {wand_power_charges} Wand of Power charge(s) into this casting (+{wand_power_charges})."
                )
        from .terrain import resolve_play_context

        play_ctx = resolve_play_context(tile, session)
        if from_garment_escape:
            session.log.append(
                f"{caster.name} casts Escape through the Phasing Panther Garment (as a level 6 wizard)."
            )
        if from_scroll and scroll_item:
            from .courtship_lex import apply_lex_soul_tax_if_needed

            if not apply_lex_soul_tax_if_needed(session, caster, scroll_item, show_rolls=show_rolls):
                return
        elif from_magic_item and magic_item:
            from .courtship_lex import apply_lex_soul_tax_if_needed

            if not apply_lex_soul_tax_if_needed(session, caster, magic_item, show_rolls=show_rolls):
                return
        outcome = resolve_spell_cast(
            spell_name,
            caster,
            session.party,
            tile.enemies,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            secondary_foe_id=secondary_foe_id,
            spell_target_mode=spell_target_mode,
            show_rolls=show_rolls,
            terrain=play_ctx.terrain,
            door_type=door_type,
            from_scroll=from_scroll,
            from_magic_item=from_magic_item,
            life_transfer_amount=life_transfer_amount,
            teleport_tile_id=teleport_tile_id,
            teleport_character_ids=teleport_character_ids,
            mass_blessing_target_ids=mass_blessing_target_ids,
            mass_blessing_condition_choices=mass_blessing_condition_choices,
            final_boss=tile.final_boss_treasure,
            session=session,
            item_name=item_name,
        )
        session.log.extend(outcome.log)
        from .forsaken_depths_river import apply_fd_oblivion_spell_forget_from_cast

        apply_fd_oblivion_spell_forget_from_cast(
            session,
            caster,
            spell_name or "",
            outcome.log,
            show_rolls=show_rolls,
        )
        consume_wand_cast_bonus(caster)
        if wand_item and wand_power_charges and wand_power_charges > 0:
            updated_wand = consume_wand_power_charges(wand_item, wand_power_charges)
            if updated_wand is None:
                caster.inventory = [item for item in caster.inventory if item != wand_item]
                session.log.append("The Wand of Power is spent.")
            else:
                caster.inventory = [updated_wand if item == wand_item else item for item in caster.inventory]
                session.log.append(f"The wand now holds {parse_wand_of_power_charges(updated_wand)} charge(s).")
        if outcome.spell_consumed:
            consume_clarity_bonus(caster)
        if in_combat and not from_item and not echo_repeat:
            if caster.character_id not in session.spell_used_character_ids:
                session.spell_used_character_ids.append(caster.character_id)
        if explain_math:
            session.log.append("Spellcasting: exploding d6 + caster level vs. target level when required.")

        if from_scroll and scroll_item:
            updated_book = consume_skalitos_page(scroll_item)
            if updated_book is not None or "book of skalitos" in scroll_item.lower():
                caster.inventory = [updated_book if item == scroll_item and updated_book else item for item in caster.inventory if item != scroll_item or updated_book]
                if updated_book:
                    session.log.append(f"Book of Skalitos has {updated_book.split('(', 1)[1].rstrip(')')} remaining.")
                else:
                    session.log.append("The last page of the Book of Skalitos turns to ash.")
            else:
                caster.inventory = [item for item in caster.inventory if item != scroll_item]
                session.log.append("The scroll is destroyed.")
        elif from_magic_item and magic_item:
            updated = consume_magic_item_charge(magic_item)
            if updated is None:
                caster.inventory = [item for item in caster.inventory if item != magic_item]
                session.log.append(f"{magic_item} is spent.")
            else:
                caster.inventory = [updated if item == magic_item else item for item in caster.inventory]
                parsed = parse_charged_magic_item(updated)
                remaining = parsed.charges if parsed else 0
                label = parsed.base_label if parsed else magic_item
                session.log.append(f"{label} now has {remaining} charge(s) remaining.")
        elif outcome.spell_consumed and not from_item and not from_garment_escape:
            expended = list(session.expended_spells.get(caster.character_id, []))
            prayer_uses = session.healing_prayer_uses.get(caster.character_id, 0)
            bead_used, bead_saved, bead_log = (False, False, [])
            if use_prayer_bead:
                if not member_has_prayer_bead_necklace(caster):
                    session.log.append(f"{caster.name} has no prayer beads to use.")
                elif caster.class_id.lower() != "cleric":
                    session.log.append("Only a cleric may roll prayer beads.")
                else:
                    bead_used, bead_saved, bead_log = consume_prayer_bead(caster)
            if bead_log:
                session.log.extend(bead_log)
            if not (bead_used and bead_saved):
                expended, prayer_uses, expend_log = mark_spell_expended(
                    spell_name,
                    expended_spells=expended,
                    healing_prayer_uses=prayer_uses,
                    prayer_limit=3 + magical_power_bonus_uses(caster, spell_name),
                )
                session.expended_spells[caster.character_id] = expended
                session.healing_prayer_uses[caster.character_id] = prayer_uses
                session.log.extend(expend_log)
                if spell_name and spell_name.strip().lower().startswith("bless"):
                    from .hirelings import acolyte_for_blessing_preservation, offer_acolyte_blessing_preservation

                    acolyte = acolyte_for_blessing_preservation(session, caster)
                    if acolyte is not None:
                        session.log.extend(offer_acolyte_blessing_preservation(session, caster, acolyte))
        if from_garment_escape and outcome.spell_consumed:
            from .expert_skill_effects import mark_phasing_panther_escape_used

            mark_phasing_panther_escape_used(session, caster)

        if outcome.teleport_to_entrance:
            entrance = self._entrance_tile(session)
            session.map_state.current_tile_id = entrance.id
            session.current_tile_entry_exit_id = None
            session.log.append("The party regroups at the adventure entrance.")
            if session.mode == "combat":
                session.mode = "exploration"
                session.combat_round = 0
                tile.enemies = []
        if outcome.teleport_to_tile_id:
            session.map_state.current_tile_id = outcome.teleport_to_tile_id
            session.current_tile_entry_exit_id = None
            session.log.append("The party appears in the chosen room.")
            if session.courtship_demesne_active:
                from .courtship_combat import courtship_clear_entangle_on_escape

                session.log.extend(courtship_clear_entangle_on_escape(session, session.party))
            if session.mode == "combat":
                session.mode = "exploration"
                session.combat_round = 0
                tile.enemies = []
        if outcome.summon_beast:
            session.summoned_beast_life = 5
            session.summoned_beast_owner_id = caster.character_id
            session.log.append(
                "A large animal ally (boar, large cat, bear) joins the fight "
                "(L3, 5 Life, 1 damage per round)."
            )
        if outcome.bear_form:
            session.bear_form_owner_id = caster.character_id
            session.bear_form_start_life = 8
            session.bear_form_pre_life = outcome.bear_form_pre_life
        if outcome.subdual_penalty_ignored:
            session.subdual_penalty_ignored = True
        if outcome.illusionary_fog:
            session.illusionary_fog_active = True
        if outcome.alter_weather_active:
            session.alter_weather_active = True
        if outcome.forest_pathway_active:
            session.forest_pathway_active = True
        if outcome.glamour_mask_reroll_available and outcome.glamour_mask_character_id:
            session.glamour_mask_character_id = outcome.glamour_mask_character_id
            session.glamour_mask_reroll_available = True
        if outcome.banquet_rations > 0:
            for _ in range(outcome.banquet_rations):
                caster.inventory.append("Food ration")
            session.log.append(
                f"{caster.name} gains {outcome.banquet_rations} illusionary food ration(s)."
            )
        if outcome.flee_bonus:
            session.skip_parting_flee = True
        if outcome.illusionary_servant:
            session.illusionary_servant_active = True
            session.illusionary_servant_owner_id = caster.character_id
            session.log.append(
                f"{caster.name}'s illusionary servant can carry an extra 200gp and weapon slots until slain or trapped."
            )
        if (
            outcome.curse_break_target_id
            and session.cursed_character_id == outcome.curse_break_target_id
        ):
            session.cursed_character_id = None
        if outcome.destroy_door and exit_state and exit_state.kind == "door":
            exit_state.door_open = True
            exit_state.status = "open"
            exit_state.door_destroyed = True
            self._sync_linked_door(session, tile, exit_state)
            session.log.append(f"The {exit_state.direction} door is destroyed and open.")
        if outcome.peaceful_bribe:
            self._record_peaceful_quest_progress(session)
            session.mode = "exploration"
            session.combat_round = 0
            tile.enemies = []

        if in_combat and session.mode == "combat":
            from .monster_combat_modifiers import mark_spider_webs_burned, orc_looter_spell_morale_check

            if spell_key in {"fireball", "fire_ball"} and mark_spider_webs_burned(tile, outcome.enemies):
                session.log.append("The Fireball burns through the fiendish spider webs.")
            morale_log: list[str] = []
            initial_orcs = sum(1 for enemy in enemies_before_spell if enemy.name == "Orc Looters")
            orc_fled = orc_looter_spell_morale_check(
                enemies_before_spell,
                outcome.enemies,
                initial_orc_count=initial_orcs,
                session=session,
                party=outcome.party,
                log=morale_log,
                show_rolls=show_rolls,
            )
            session.log.extend(morale_log)
            if orc_fled and not any(enemy.life > 0 for enemy in outcome.enemies):
                outcome.combat_over = True

        if outcome.combat_over and session.mode == "combat":
            if spell_key == "sleep":
                self._record_peaceful_quest_progress(session)
            result = CombatRound(
                party=outcome.party,
                enemies=outcome.enemies,
                log=[],
                combat_over=True,
            )
            self._apply_combat_result(
                session,
                tile,
                result,
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )
        else:
            session.party = self._merge_party_outcome(session.party, outcome.party)
            tile.enemies = outcome.enemies
            if session.mode == "combat":
                remaining = sum(1 for enemy in tile.enemies if enemy.life > 0)
                if remaining:
                    if session.combat_round == 0 and session.reaction_checked and not session.party_attacked_immediately:
                        session.log.append(
                            f"{remaining} foe(s) remain after the spell — use Resolve Round to continue. "
                            "No opening bow volley this fight (Reactions were checked first; p.146)."
                        )
                    else:
                        session.log.append(
                            f"{remaining} foe(s) remain after the spell — use Resolve Round to continue."
                        )

        if (
            not echo_repeat
            and not from_item
            and outcome.spell_consumed
            and caster.current_life > 0
        ):
            repeat, echo_roll = echo_spell_repeats(tile.cavern_feature_key, echo_repeat=False)
            if show_rolls and tile.cavern_feature_key == "echo":
                session.log.append(f"Echo roll: d6 = {echo_roll}.")
            if repeat:
                session.pending_echo_spell = PendingEchoSpellState(
                    caster_id=caster.character_id,
                    spell_name=spell_name,
                    tile_id=tile.id,
                    exit_id=exit_id,
                    target_character_id=target_character_id,
                    target_foe_id=target_foe_id,
                    secondary_foe_id=secondary_foe_id,
                    spell_target_mode=spell_target_mode,
                    life_transfer_amount=life_transfer_amount,
                    teleport_tile_id=teleport_tile_id,
                    teleport_character_ids=teleport_character_ids,
                )
                session.log.append(
                    f"Echo: {caster.name} may immediately cast {spell_name} again for free — choose targets."
                )

    def _resolve_echo_spell(
        self,
        session: SessionState,
        *,
        target_character_id: str | None = None,
        foe_id: str | None = None,
        secondary_foe_id: str | None = None,
        spell_target_mode: str | None = None,
        life_transfer_amount: int | None = None,
        teleport_tile_id: str | None = None,
        teleport_character_ids: list[str] | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        pending = session.pending_echo_spell
        if pending is None:
            session.log.append("No echo spell is pending.")
            return
        caster = next((member for member in session.party if member.character_id == pending.caster_id), None)
        if caster is None or caster.current_life <= 0:
            session.pending_echo_spell = None
            session.log.append("The echo spell fades — the caster cannot act.")
            return
        session.pending_echo_spell = None
        self._cast_spell(
            session,
            pending.caster_id,
            pending.spell_name,
            exit_id=pending.exit_id,
            target_character_id=target_character_id or pending.target_character_id,
            target_foe_id=foe_id or pending.target_foe_id,
            secondary_foe_id=secondary_foe_id or pending.secondary_foe_id,
            spell_target_mode=spell_target_mode or pending.spell_target_mode,
            life_transfer_amount=life_transfer_amount or pending.life_transfer_amount,
            teleport_tile_id=teleport_tile_id or pending.teleport_tile_id,
            teleport_character_ids=teleport_character_ids or pending.teleport_character_ids,
            show_rolls=show_rolls,
            explain_math=explain_math,
            echo_repeat=True,
        )

    def _burn_scroll(
        self,
        session: SessionState,
        character_id: str | None,
        spell_name: str | None,
        *,
        exit_id: str | None = None,
        target_character_id: str | None = None,
        target_foe_id: str | None = None,
        spell_target_mode: str | None = None,
        mass_blessing_target_ids: list[str] | None = None,
        mass_blessing_condition_choices: dict[str, list[str]] | None = None,
        courtship_choice: str | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return
        caster = next((member for member in session.party if member.character_id == character_id), None)
        if caster is None or caster.current_life <= 0:
            session.log.append("That hero cannot use a scroll.")
            return
        if barbarian_cannot_use_scrolls(caster.class_id):
            session.log.append("Barbarians cannot use scrolls.")
            return
        if not spell_name:
            session.log.append("Choose a scroll spell to cast.")
            return
        scroll_item = find_scroll_item(caster.inventory, spell_name)
        if scroll_item is None:
            scroll_item = find_skalitos_book(caster.inventory, spell_name)
        if scroll_item is None:
            session.log.append(f"{caster.name} has no scroll of {spell_name}.")
            return
        from .courtship_blossoms_spells import is_blossoms_spell, try_cast_blossoms_scroll

        if is_blossoms_spell(spell_name):
            if try_cast_blossoms_scroll(
                self,
                session,
                caster,
                spell_name,
                scroll_item,
                target_character_id=target_character_id,
                courtship_choice=courtship_choice,
                show_rolls=show_rolls,
            ):
                return
        self._cast_spell(
            session,
            caster.character_id,
            spell_name,
            exit_id=exit_id,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            mass_blessing_target_ids=mass_blessing_target_ids,
            mass_blessing_condition_choices=mass_blessing_condition_choices,
            from_scroll=True,
            scroll_item=scroll_item,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )

    def _surgeon_burn_scroll(
        self,
        session: SessionState,
        hireling_id: str | None,
        character_id: str | None,
        spell_name: str | None,
        *,
        professional_provider_id: str | None = None,
        exit_id: str | None = None,
        target_character_id: str | None = None,
        target_foe_id: str | None = None,
        spell_target_mode: str | None = None,
        mass_blessing_target_ids: list[str] | None = None,
        mass_blessing_condition_choices: dict[str, list[str]] | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return
        from .courtship_professional_skills import member_has_trained_surgeon
        from .hirelings import _hireling_by_id

        hireling = _hireling_by_id(session, hireling_id)
        provider = next(
            (member for member in session.party if member.character_id == professional_provider_id),
            None,
        )
        if hireling is not None and hireling.life > 0 and hireling.retainer_type == "surgeon":
            reader_label = hireling.name
        elif provider is not None and provider.current_life > 0 and member_has_trained_surgeon(provider):
            reader_label = provider.name
        else:
            session.log.append("Choose a living surgeon retainer or a hero trained as a surgeon.")
            return
        owner = next((member for member in session.party if member.character_id == character_id), None)
        if owner is None or owner.current_life <= 0:
            session.log.append("Choose a living hero who carries the scroll.")
            return
        if barbarian_cannot_use_scrolls(owner.class_id):
            session.log.append("Barbarians cannot use scrolls, even when read by the surgeon.")
            return
        if not spell_name:
            session.log.append("Choose a scroll spell to read.")
            return
        scroll_item = find_scroll_item(owner.inventory, spell_name)
        if scroll_item is None:
            scroll_item = find_skalitos_book(owner.inventory, spell_name)
        if scroll_item is None:
            session.log.append(f"{owner.name} has no scroll of {spell_name}.")
            return
        session.log.append(f"{reader_label} reads {scroll_item} for {owner.name}.")
        self._cast_spell(
            session,
            owner.character_id,
            spell_name,
            exit_id=exit_id,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            from_scroll=True,
            scroll_item=scroll_item,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )

    def _use_magic_item(
        self,
        session: SessionState,
        character_id: str | None,
        spell_name: str | None,
        *,
        item_name: str | None = None,
        exit_id: str | None = None,
        target_character_id: str | None = None,
        target_foe_id: str | None = None,
        spell_target_mode: str | None = None,
        mass_blessing_target_ids: list[str] | None = None,
        mass_blessing_condition_choices: dict[str, list[str]] | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return
        caster = next((member for member in session.party if member.character_id == character_id), None)
        if caster is None or caster.current_life <= 0:
            session.log.append("That hero cannot use a magic item.")
            return
        if barbarian_cannot_use_magic(caster.class_id):
            session.log.append("Barbarians cannot use magic items.")
            return
        magic_item = find_magic_item_by_name(caster.inventory, item_name) if item_name else None
        if magic_item is None and spell_name:
            magic_item = find_magic_item(caster.inventory, spell_name)
        if magic_item is None:
            session.log.append(f"{caster.name} has no usable charged wand or staff for that spell.")
            return
        parsed = parse_charged_magic_item(magic_item)
        if parsed is None:
            session.log.append(f"{magic_item} cannot be used to cast spells.")
            return
        use_error = charged_magic_item_use_error(magic_item, caster.class_id)
        if use_error:
            session.log.append(use_error)
            return
        resolved_spell = spell_name or parsed.spell_name
        self._cast_spell(
            session,
            caster.character_id,
            resolved_spell,
            exit_id=exit_id,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            mass_blessing_target_ids=mass_blessing_target_ids,
            mass_blessing_condition_choices=mass_blessing_condition_choices,
            from_magic_item=True,
            magic_item=magic_item,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )

    def _use_blossoms_item(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None,
        mode: str | None,
        *,
        show_rolls: bool = True,
    ) -> None:
        if not session.courtship_demesne_active:
            session.log.append("Blossoms magic items can only be used in the Demesne (TCOTFD).")
            return
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to use the Blossoms item.")
            return
        if not item_name:
            session.log.append("Choose which Blossoms magic item to use.")
            return
        if barbarian_cannot_use_magic(member.class_id):
            session.log.append("Barbarians cannot use magic items.")
            return
        from .courtship_blossoms_items import use_blossoms_item

        use_blossoms_item(
            self,
            session,
            member,
            item_name,
            mode,
            show_rolls=show_rolls,
        )

    def _use_abyss_item(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None,
        *,
        mode: str | None = None,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode == "complete":
            session.log.append("This adventure is complete.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to use the Abyss item.")
            return
        tile = self._current_tile(session)
        if member.character_id not in {pc.character_id for pc in combat_party(session, tile.id)}:
            session.log.append(f"{member.name} is not on the current map element.")
            return

        from .abyss_items import (
            consume_inventory_item,
            has_fire_breath_status,
            is_blessed_horseshoe,
            is_elven_bread,
            is_medallion_of_snake_charming,
            is_parchment_of_banishing,
            is_philter_of_fire_breathing,
            is_ring_of_three_wishes,
            target_is_snake_or_lizardman_minion,
            target_is_undead_or_demon,
            use_blessed_horseshoe,
            use_elven_bread,
            use_philter_of_fire_breathing,
        )

        selected = item_name if item_name and item_name in member.inventory else None
        lower = selected.lower() if selected else ""
        mode_key = (mode or "").strip().lower()

        if selected and is_elven_bread(selected):
            session.log.extend(use_elven_bread(member, selected))
            return
        if selected and is_blessed_horseshoe(selected):
            session.log.extend(use_blessed_horseshoe(member, selected))
            return
        if selected and is_philter_of_fire_breathing(selected):
            if member.class_id.lower() == "barbarian":
                session.log.append("Barbarians cannot use the Philter of Fire Breathing.")
                return
            session.log.extend(use_philter_of_fire_breathing(member, selected))
            return
        if mode_key == "fire_breath":
            self._abyss_fire_breath(
                session,
                tile,
                member,
                target_enemy_id=target_enemy_id,
                show_rolls=show_rolls,
            )
            return
        if selected and is_parchment_of_banishing(selected):
            if member.class_id.lower() not in {"wizard", "cleric"}:
                session.log.append("Parchment of Banishing may be used only by wizards and clerics.")
                return
            if session.mode != "combat":
                session.log.append("Parchment of Banishing requires an undead or demon foe in combat.")
                return
            living = [enemy for enemy in tile.enemies if enemy.life > 0]
            targets = [enemy for enemy in living if target_is_undead_or_demon(enemy)]
            target = next((enemy for enemy in targets if enemy.id == target_enemy_id), None) or (targets[0] if targets else None)
            if target is None:
                session.log.append("There is no undead or demon foe to banish.")
                return
            if not self._commit_immediate_attack(session):
                return
            active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
            standing_before = {pc.character_id for pc in combat_party(session, tile.id) if pc.current_life > 0}
            consume_inventory_item(member, selected)
            apply_enemy_damage(target, 2, damage_kind="holy")
            session.log.append(f"{member.name} reads {selected}; {target.name} suffers 2 wounds and the parchment turns to dust.")
            self._abyss_finish_item_attack(session, tile, active_enemy_ids, standing_before, show_rolls=show_rolls)
            return
        if selected and is_medallion_of_snake_charming(selected):
            if session.mode != "combat":
                session.log.append("Medallion of Snake Charming requires snake or lizardman minions in combat.")
                return
            living = [enemy for enemy in tile.enemies if enemy.life > 0]
            targets = [enemy for enemy in living if target_is_snake_or_lizardman_minion(enemy)]
            target = next((enemy for enemy in targets if enemy.id == target_enemy_id), None) or (targets[0] if targets else None)
            if target is None:
                session.log.append("There are no snake or lizardman minions to charm.")
                return
            if not self._commit_immediate_attack(session):
                return
            total = roll_die(8) + member.level
            if show_rolls:
                session.log.append(f"Medallion of Snake Charming: {member.name} rolls d8+L = {total} vs L{target.level}.")
            if total >= target.level:
                target.life = 0
                session.log.append(f"{target.name} become friendly and ignore the party while the medallion remains with them.")
                if not any(enemy.life > 0 for enemy in tile.enemies):
                    self._clear_combat_statuses(session)
                    session.combat_round = 0
                    session.mode = "exploration"
                    session.log.append("Combat ends peacefully.")
            else:
                session.log.append(f"{target.name} resist the medallion.")
            return
        if selected and is_ring_of_three_wishes(selected):
            if member.class_id.lower() == "barbarian":
                session.log.append("Barbarians cannot use the Ring of Three Wishes.")
                return
            self._abyss_ring_wish(
                session,
                tile,
                member,
                selected,
                mode_key,
                target_enemy_id=target_enemy_id,
                show_rolls=show_rolls,
            )
            return
        if has_fire_breath_status(member):
            self._abyss_fire_breath(
                session,
                tile,
                member,
                target_enemy_id=target_enemy_id,
                show_rolls=show_rolls,
            )
            return
        item_label = selected or lower or "that item"
        session.log.append(f"{item_label} has no Abyss use action here.")

    def _abyss_fire_breath(
        self,
        session: SessionState,
        tile: TileState,
        member: PartyMemberState,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Fire breath can be used only during combat.")
            return
        from .abyss_items import consume_fire_breath_status, has_fire_breath_status

        if not has_fire_breath_status(member):
            session.log.append(f"{member.name} has no unused Philter fire breath.")
            return
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        targets = [enemy for enemy in living if "dragon" not in enemy.name.lower() and "dragon" not in {tag.lower() for tag in enemy.tags}]
        target = next((enemy for enemy in targets if enemy.id == target_enemy_id), None) or (targets[0] if targets else None)
        if target is None:
            session.log.append("Fire breath has no effect on dragons, and no other living foe is present.")
            return
        if not self._commit_immediate_attack(session):
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in combat_party(session, tile.id) if pc.current_life > 0}
        consume_fire_breath_status(member)
        if target.category in {"vermin", "minions"}:
            slain = min(2, target.life)
            target.life -= slain
            session.log.append(f"{member.name} breathes fire, killing {slain} {target.name}.")
        else:
            apply_enemy_damage(target, 2, damage_kind="fire")
            session.log.append(f"{member.name} breathes fire; {target.name} suffers 2 wounds.")
        self._abyss_finish_item_attack(session, tile, active_enemy_ids, standing_before, show_rolls=show_rolls)

    def _abyss_ring_wish(
        self,
        session: SessionState,
        tile: TileState,
        member: PartyMemberState,
        ring: str,
        mode: str,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        from .abyss_items import consume_ring_wish, ring_wish_count

        if ring not in member.inventory or ring_wish_count(ring) <= 0:
            session.log.append(f"{member.name}'s Ring of Three Wishes has no wishes left.")
            return

        if mode in {"", "heal"}:
            consume_ring_wish(member, ring)
            member.current_life = member.max_life
            member.madness = 0
            session.log.append(f"{member.name} spends a ring wish to heal all Life damage and Madness.")
            return
        if mode == "reroll":
            consume_ring_wish(member, ring)
            member.statuses.append("Ring of Three Wishes reroll")
            session.log.append(f"{member.name} spends a ring wish; mark the next failed die roll as rerolled.")
            return
        if mode in {"equipment", "treasure"}:
            consume_ring_wish(member, ring)
            member.inventory.append("Wish-created non-magical treasure/equipment (<=300gp)")
            session.log.append(f"{member.name} spends a ring wish to create one non-magical treasure or equipment item worth 300gp or less.")
            return
        if mode == "basic_spell":
            consume_ring_wish(member, ring)
            member.statuses.append("Ring of Three Wishes basic spell")
            session.log.append(f"{member.name} spends a ring wish; cast one spell from the basic spell list.")
            return
        if mode == "wound_foe":
            if session.mode != "combat":
                session.log.append("Ring damage wishes require a combat target.")
                return
            living = [enemy for enemy in tile.enemies if enemy.life > 0]
            target = next((enemy for enemy in living if enemy.id == target_enemy_id), None) or (living[0] if living else None)
            if target is None:
                session.log.append("There are no foes to target with the wish.")
                return
            if not self._commit_immediate_attack(session):
                return
            active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
            standing_before = {pc.character_id for pc in combat_party(session, tile.id) if pc.current_life > 0}
            consume_ring_wish(member, ring)
            if target.category in {"vermin", "minions"}:
                slain = min(2, target.life)
                target.life -= slain
                session.log.append(f"{member.name} spends a ring wish, killing {slain} {target.name}.")
            else:
                apply_enemy_damage(target, 2, damage_kind="magic")
                session.log.append(f"{member.name} spends a ring wish; {target.name} suffers 2 wounds.")
            self._abyss_finish_item_attack(session, tile, active_enemy_ids, standing_before, show_rolls=show_rolls)
            return
        session.log.append("Choose a Ring of Three Wishes effect: heal, reroll, wound foe, equipment, or basic spell.")

    def _abyss_finish_item_attack(
        self,
        session: SessionState,
        tile: TileState,
        active_enemy_ids: set[str],
        standing_before: set[str],
        *,
        show_rolls: bool,
    ) -> None:
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._apply_combat_result(
                session,
                tile,
                CombatRound(
                    party=session.party,
                    enemies=tile.enemies,
                    log=[],
                    combat_over=True,
                ),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )
            return
        remaining = sum(1 for enemy in tile.enemies if enemy.life > 0)
        session.log.append(f"{remaining} foe(s) remain after the Abyss item action — use Resolve Round to continue.")

    def _use_apothecary_brew(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None,
        *,
        show_rolls: bool = True,
    ) -> None:
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to use the Apothecary brew.")
            return
        if not item_name:
            session.log.append("Choose which Apothecary brew to use.")
            return
        if item_name not in member.inventory:
            session.log.append(f"{member.name} is not carrying {item_name}.")
            return
        if barbarian_cannot_use_magic(member.class_id):
            session.log.append("Barbarians cannot use magic items or potions.")
            return
        from .courtship_apothecary_brew import use_apothecary_brew

        use_apothecary_brew(session, member, item_name, show_rolls=show_rolls)

    def _copy_scroll(self, session: SessionState, character_id: str | None, spell_name: str | None) -> None:
        if session.mode != "exploration":
            session.log.append("Copy scrolls to a spellbook during exploration.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.class_id.lower() != "wizard":
            session.log.append("Only wizards can copy spells from scrolls.")
            return
        if not spell_name:
            session.log.append("Choose a scroll to copy.")
            return
        scroll_item = find_scroll_item(member.inventory, spell_name)
        if scroll_item is None:
            session.log.append(f"{member.name} does not have that scroll.")
            return
        if any(normalize_spell_name(item) == normalize_spell_name(spell_name) for item in member.spells):
            session.log.append(f"{spell_name} is already in {member.name}'s spellbook.")
            return
        from .courtship_blossoms_spells import is_blossoms_spell

        if is_blossoms_spell(spell_name) and member.class_id.lower() not in {"wizard", "conservationist"}:
            session.log.append("Only wizards and Conservationists may copy Blossoms spells (TCOTFD p.27).")
            return
        member.spells.append(spell_name.strip())
        member.inventory = [item for item in member.inventory if item != scroll_item]
        session.log.append(f"{member.name} copies {spell_name} into the spellbook (scroll destroyed).")

    def _spellcast_door(
        self,
        session: SessionState,
        exit_id: str | None,
        character_id: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Work doors during exploration.")
            return
        tile = self._active_tile(session)
        exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door" or exit_state.door_open:
            session.log.append("Choose a closed door.")
            return
        if exit_state.door_type is None:
            hcl = self._highest_character_level(session.party)
            outcome = self.table_roller.roll_door(hcl)
            exit_state.door_type = outcome.door_type
            exit_state.door_level = outcome.door_level
            exit_state.door_result = outcome.summary
            exit_state.door_treasure_bonus = outcome.treasure_bonus
            session.log.extend(door_discovery_log(outcome, hcl=hcl, show_rolls=show_rolls))

        member = next((item for item in session.party if item.character_id == character_id), None) if character_id else None
        if member is None:
            member = self._member_by_marching_order(session, 1)
        if member is None:
            session.log.append("No hero available.")
            return

        hcl = self._highest_character_level(session.party)
        door_type = exit_state.door_type or "unlocked"
        if door_type == "sealed":
            if not is_spellcaster(member):
                session.log.append("Only a spellcaster can open a magically sealed door.")
                return
            if exit_state.door_sealed_attempted:
                session.log.append("The sealed door already resisted a spellcasting attempt.")
                return
            exit_state.door_sealed_attempted = True
            level = exit_state.door_level or hcl
            total, rolls = roll_exploding_for_level(member)
            modifier = spellcasting_modifier(member)
            final_total = total + modifier
            if show_rolls:
                session.log.append(
                    f"Sealed door: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{level}."
                )
            if rolls[0] == 1:
                member.current_life = max(0, member.current_life - 2)
                session.log.append("Magic feedback! The caster takes 2 damage.")
            success = final_total >= level
            if success:
                exit_state.door_open = True
                exit_state.status = "open"
                self._sync_linked_door(session, tile, exit_state)
                session.log.append(f"The {exit_state.direction} sealed door opens.")
            else:
                session.log.append("The sealed door holds.")
            return

        if door_type == "illusion":
            if member.class_id.lower() != "illusionist":
                session.log.append("An illusionist must dispel this door's magic.")
                return
            if member.character_id in exit_state.door_illusion_attempted_ids:
                session.log.append(f"{member.name} already tried to open this illusionary door.")
                return
            exit_state.door_illusion_attempted_ids.append(member.character_id)
            success, roll_log = spellcasting_roll_vs_level(
                member,
                hcl,
                show_rolls=show_rolls,
                label="Illusionary door",
            )
            session.log.extend(roll_log)
            if success:
                exit_state.door_open = True
                exit_state.status = "open"
                self._sync_linked_door(session, tile, exit_state)
                session.log.append(f"The illusion fades; the {exit_state.direction} door opens.")
            else:
                session.log.append("The illusion persists.")
            return

        session.log.append("This door does not respond to spellcasting.")

    def _spend_clues_on_door(self, session: SessionState, exit_id: str | None, *, show_rolls: bool = True) -> None:
        if session.mode != "exploration":
            session.log.append("Work doors during exploration.")
            return
        tile = self._active_tile(session)
        exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door" or exit_state.door_open:
            session.log.append("Choose a closed door.")
            return
        if exit_state.door_type is None:
            hcl = self._highest_character_level(session.party)
            outcome = self.table_roller.roll_door(hcl)
            exit_state.door_type = outcome.door_type
            exit_state.door_level = outcome.door_level
            exit_state.door_result = outcome.summary
            exit_state.door_treasure_bonus = outcome.treasure_bonus
            session.log.extend(door_discovery_log(outcome, hcl=hcl, show_rolls=show_rolls))
        if exit_state.door_type != "illusion" and exit_state.door_type != "lever":
            session.log.append("Spending Clues works on illusionary or lever doors only.")
            return
        required = 3 if exit_state.door_type == "illusion" else 1
        self._ensure_individual_clues(session)
        if session.clues_found < required:
            session.log.append(f"Need {required} Clue(s) to open this door (party has {session.clues_found}).")
            return
        if not self._spend_clues(session, required):
            session.log.append(f"Need {required} Clue(s) to open this door (party has {session.clues_found}).")
            return
        exit_state.door_open = True
        exit_state.status = "open"
        self._sync_linked_door(session, tile, exit_state)
        session.log.append(
            f"The party spends {required} Clue(s); the {exit_state.direction} {exit_state.door_type} door opens."
        )

    def _reveal_secret_with_clues(
        self,
        session: SessionState,
        character_id: str | None = None,
        *,
        secret_id: str | None = None,
        spell_id: str | None = None,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Reveal Secrets after combat.")
            return
        self._ensure_individual_clues(session)
        if session.clues_found < CLUES_FOR_SECRET_XP:
            session.log.append(
                f"Need {CLUES_FOR_SECRET_XP} Clues to reveal a Secret (party has {session.clues_found})."
            )
            return
        discoverer = None
        if character_id:
            discoverer = next((member for member in session.party if member.character_id == character_id), None)
        if discoverer is None:
            discoverer = next(
                (
                    member
                    for member in sorted(session.party, key=lambda item: item.marching_order)
                    if member.current_life > 0
                ),
                None,
            )
        if discoverer is None:
            session.log.append("Choose a living hero to discover the Secret.")
            return
        secret = secret_by_id(secret_id)
        if secret is None:
            session.log.append("Choose which Secret to reveal from the p.123 Secrets list.")
            return
        blocked = self._secret_reveal_blocker(session, discoverer, secret.id, spell_id=spell_id)
        if blocked:
            session.log.append(blocked)
            return
        if not self._spend_clues(session, CLUES_FOR_SECRET_XP, preferred_character_id=discoverer.character_id):
            session.log.append(
                f"Need {CLUES_FOR_SECRET_XP} Clues to reveal a Secret (party has {session.clues_found})."
            )
            return
        extra_log = self._apply_revealed_secret(session, discoverer, secret.id, spell_id=spell_id)
        session.log.append(
            f"The party spends {CLUES_FOR_SECRET_XP} Clues; {discoverer.name} reveals {secret.label}."
        )
        if session.xp_system == "slow_and_sure":
            session.log.append(
                "Slow and Sure mode does not award XP rolls for Secrets."
            )
        else:
            self._grant_xp_credit(session, 1, f"{discoverer.name} reveals {secret.label}:")
        session.log.extend(extra_log)

    def _find_captive_hideout(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool = True,
    ) -> None:
        """Spend 3 Clues on 'Someone Has Been Imprisoned' to locate the captive hideout.

        Creates a new tile adjacent to the current tile, populated with the capturing
        foe type at doubled count. Captured heroes will be found there with d3 Life.
        """
        if not session.captured_character_ids:
            session.log.append("No heroes are currently held captive.")
            return
        if session.capture_hideout_tile_id:
            existing = next(
                (t for t in session.map_state.tiles if t.id == session.capture_hideout_tile_id), None
            )
            if existing:
                session.log.append(
                    f"The captive hideout is already known: {existing.title}. Head there to rescue your comrades."
                )
                return
        self._ensure_individual_clues(session)
        if session.clues_found < CLUES_FOR_SECRET_XP:
            session.log.append(
                f"Need {CLUES_FOR_SECRET_XP} Clues to locate the captive hideout "
                f"(party has {session.clues_found})."
            )
            return
        discoverer = None
        if character_id:
            discoverer = next((m for m in session.party if m.character_id == character_id), None)
        if discoverer is None:
            discoverer = next(
                (m for m in sorted(session.party, key=lambda item: item.marching_order) if m.current_life > 0),
                None,
            )
        if discoverer is None:
            session.log.append("No living hero to discover the hideout location.")
            return
        if not self._can_place_hideout_near_tile(session, self._current_tile(session)):
            session.log.append(
                "Someone Has Been Imprisoned cannot be used here: no open map space is available around this tile."
            )
            return
        if not self._spend_clues(session, CLUES_FOR_SECRET_XP, preferred_character_id=discoverer.character_id):
            session.log.append(
                f"Need {CLUES_FOR_SECRET_XP} Clues to locate the captive hideout "
                f"(party has {session.clues_found})."
            )
            return
        record_secret(discoverer, "someone_imprisoned")
        if session.xp_system != "slow_and_sure":
            self._grant_xp_credit(session, 1, f"{discoverer.name} reveals 'Someone Has Been Imprisoned':")
        captive_names = ", ".join(
            m.name
            for m in session.party
            if m.character_id in session.captured_character_ids
        ) or "unknown captive(s)"
        foe_name = session.capture_foe_name or "Unknown Foe"
        hideout_tile = self._build_hideout_tile(session, foe_name, show_rolls=show_rolls)
        if hideout_tile is None:
            session.log.append(
                "Someone Has Been Imprisoned cannot be used here: no open map space is available around this tile."
            )
            return
        session.map_state.tiles.append(hideout_tile)
        session.capture_hideout_tile_id = hideout_tile.id
        origin = self._current_tile(session)
        hideout_exit = self._add_hideout_exit(origin, hideout_tile)
        self._add_hideout_return_exit(hideout_tile, origin, hideout_exit)
        from .heroic_skill_effects import mark_tile_visited
        mark_tile_visited(session, hideout_tile.id)
        session.log.append(
            f"The party's clues point to a cave nearby: {hideout_tile.title}. "
            f"A new passage leads to it. "
            f"{captive_names} will be found there guarded by {foe_name}s."
        )

    def _build_hideout_tile(
        self,
        session: SessionState,
        foe_name: str,
        *,
        show_rolls: bool = True,
    ) -> TileState | None:
        """Construct the captive hideout TileState with doubled foes."""
        hcl = self._highest_character_level(session.party)
        origin = self._current_tile(session)
        width = roll_d6() * 2
        height = roll_d6() * 2
        if show_rolls:
            session.log.append(f"Hideout size roll: {width // 2}d6 × {height // 2}d6 = {width}×{height} cave.")
        placement = self._find_hideout_anchor(session, origin, width=width, height=height)
        if placement is None:
            return None
        hx, hy = placement
        walkable = ["1" * width] * height
        visible = [f"{'1' * width}"] * height
        enemies = self._create_hideout_enemies(session, foe_name, hcl)
        if show_rolls:
            session.log.append(f"Hideout guards: {len(enemies)} {foe_name}(s) (doubled count).")
        return TileState(
            id=uuid4().hex,
            x=hx,
            y=hy,
            tile_key="11",
            tile_type="room",
            rotation=0,
            footprint_width=width,
            footprint_height=height,
            editor_cell_size=80,
            image_scale=1.0,
            image_offset_x=0,
            image_offset_y=0,
            walkable=walkable,
            cell_shapes=walkable,
            visible=visible,
            image=None,
            title="Captive Hideout",
            description=(
                "A dank cave serving as a foe hideout. "
                "Your captured comrades are here, stripped of their gold and equipment and guarded by doubled foes."
            ),
            content_key="encounter",
            enemies=enemies,
            initial_enemy_count=len(enemies),
            exits=[],
            environment=session.environment,
            terrain="indoor",
        )

    def _find_hideout_anchor(
        self,
        session: SessionState,
        origin: TileState,
        *,
        width: int,
        height: int,
    ) -> tuple[int, int] | None:
        occupied = {(tile.x, tile.y) for tile in session.map_state.tiles}
        candidates = [
            (origin.x + origin.footprint_width + 1, origin.y),
            (origin.x, origin.y + origin.footprint_height + 1),
            (origin.x - width - 1, origin.y),
            (origin.x, origin.y - height - 1),
        ]
        for cx, cy in candidates:
            if cx < 0 or cy < 0:
                continue
            if (cx, cy) in occupied:
                continue
            return cx, cy
        return None

    def _can_place_hideout_near_tile(self, session: SessionState, origin: TileState) -> bool:
        # Hideouts are at least 2x2, so a 2x2 probe is enough for availability checks.
        return self._find_hideout_anchor(session, origin, width=2, height=2) is not None

    def _create_hideout_enemies(
        self,
        session: SessionState,
        foe_name: str,
        hcl: int,
    ) -> list[EnemyState]:
        """Create doubled-count enemies for the hideout from any existing tile with this foe."""
        template_enemy: EnemyState | None = None
        for tile in session.map_state.tiles:
            for enemy in tile.enemies + tile.defeated_enemies:
                if enemy.name == foe_name:
                    template_enemy = enemy
                    break
            if template_enemy:
                break
        if template_enemy is None:
            level = max(1, hcl)
            template_enemy = EnemyState(
                id=uuid4().hex,
                name=foe_name,
                category="minion",
                level=level,
                life=1,
                max_life=1,
                attacks=1,
            )
        count = max(2, len([
            enemy
            for tile in session.map_state.tiles
            for enemy in tile.enemies
            if enemy.name == foe_name and enemy.life > 0
        ])) * 2
        count = max(count, 4)
        enemies: list[EnemyState] = []
        for _ in range(count):
            enemies.append(
                EnemyState(
                    id=uuid4().hex,
                    name=template_enemy.name,
                    category=template_enemy.category,
                    level=template_enemy.level,
                    life=template_enemy.max_life,
                    max_life=template_enemy.max_life,
                    attacks=template_enemy.attacks,
                    tags=list(template_enemy.tags),
                )
            )
        return enemies

    def _add_hideout_exit(self, origin: TileState, hideout: TileState) -> ExitState:
        """Add a passage exit on origin pointing to the hideout; return the created exit."""
        exit_id = uuid4().hex
        hideout_exit = ExitState(
            id=exit_id,
            label="Passage to Captive Hideout",
            direction="east",
            kind="passage",
            x=max(0, origin.footprint_width - 1),
            y=max(0, origin.footprint_height // 2),
            span=1,
            offset=0,
            position=0.5,
            status="open",
            destination_tile_id=hideout.id,
        )
        origin.exits.append(hideout_exit)
        return hideout_exit

    def _add_hideout_return_exit(
        self,
        hideout: TileState,
        origin: TileState,
        origin_exit: ExitState,
    ) -> None:
        """Add a return passage on the hideout pointing back to origin."""
        hideout.exits.append(
            ExitState(
                id=uuid4().hex,
                label="Passage back to dungeon",
                direction="west",
                kind="passage",
                x=0,
                y=max(0, hideout.footprint_height // 2),
                span=1,
                offset=0,
                position=0.5,
                status="open",
                destination_tile_id=origin.id,
            )
        )

    def _hideout_skips_auto_combat(self, session: SessionState, tile: TileState) -> bool:
        if tile.id != session.capture_hideout_tile_id or not session.captured_character_ids:
            return False
        if not session.capture_hideout_reaction_checked:
            return False
        if not is_bribe_reaction(session.capture_hideout_reaction_key):
            return False
        fighters = [member for member in session.party if member.current_life > 0]
        return not dwarf_miser_blocks_bribe(fighters)

    def _ensure_capture_hideout_reaction(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        if tile.id != session.capture_hideout_tile_id or not session.captured_character_ids:
            return
        if session.capture_hideout_reaction_checked:
            return
        if not any(enemy.life > 0 for enemy in tile.enemies):
            return
        self._roll_capture_hideout_reaction(session, tile, show_rolls=show_rolls)

    def _roll_capture_hideout_reaction(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            return
        reaction_tables = self.rules.monsters().get("reaction_tables", {})
        if not isinstance(reaction_tables, dict):
            reaction_tables = {}
        source = resolve_reaction_source(living_enemies, reaction_tables)
        roll = roll_d6()
        fighters = [member for member in session.party if member.current_life > 0]
        roll, negotiator_log = adjust_reaction_roll(fighters, roll, 0)
        session.log.extend(negotiator_log)
        from .heroic_skill_effects import apply_song_of_elidra, beast_leadership_reaction_bonus

        song_party = self._song_of_elidra_party(session, tile.id)
        song_bonus, song_log = apply_song_of_elidra(session, song_party)
        if song_bonus:
            roll = max(1, min(6, roll + song_bonus))
            session.log.extend(song_log)
        beast_bonus, beast_log = beast_leadership_reaction_bonus(fighters, living_enemies)
        if beast_bonus:
            roll = max(1, min(6, roll + beast_bonus))
            session.log.extend(beast_log)
        if source.inline_rows:
            row = lookup_reaction_row(source.inline_rows, roll)
            table_label = f"{source.label} reaction table"
        else:
            table_name = source.table_name or "default_reaction_table"
            row = self.table_roller.roll_reaction(table_name, roll)
            table_label = table_name
        if row is None:
            row = self.table_roller.roll_reaction("default_reaction_table", roll)
            table_label = "default_reaction_table"
        if row is None:
            row = {"key": "fight", "result": "The foes attack!", "foes_first": True}
        row = apply_reaction_overlays(row, living_enemies, roll)
        row = normalize_reaction_row(row)
        if show_rolls:
            session.log.append(
                f"Hideout guard reaction roll: d6 = {roll} on {table_label}."
            )
        outcome = build_reaction_outcome(
            row,
            hcl=self._highest_character_level(fighters),
            foe_count=len(living_enemies),
        )
        session.capture_hideout_reaction_checked = True
        session.capture_hideout_reaction_key = outcome.key
        session.log.append(outcome.result)
        if is_bribe_reaction(outcome.key):
            if dwarf_miser_blocks_bribe(fighters):
                session.log.append(
                    "Reaction outcome: the dwarves refuse to pay ransom (Miser trait with 2+ dwarves). "
                    "Fight the guards to rescue your comrades."
                )
            else:
                session.log.append(
                    "Reaction outcome: the guards may accept ransom (Level×10 gp per captive) instead of fighting."
                )
        else:
            session.log.append(
                "Reaction outcome: the guards will not accept ransom. Defeat them in combat to rescue your comrades."
            )

    def _clear_capture_hideout_state(self, session: SessionState) -> None:
        session.capture_foe_name = None
        session.capture_origin_tile_id = None
        session.capture_hideout_tile_id = None
        session.capture_hideout_reaction_checked = False
        session.capture_hideout_reaction_key = None

    def _pay_captive_ransom(self, session: SessionState, *, show_rolls: bool = True) -> None:
        """Pay Level×10 gp per captive hero to free them from the hideout.

        Only available when the party is at the hideout tile and the hideout reaction
        allows a bribe-like peaceful resolution.
        """
        if session.map_state.current_tile_id != session.capture_hideout_tile_id:
            session.log.append("You must be at the captive hideout to pay a ransom.")
            return
        if not session.captured_character_ids:
            session.log.append("No captives to ransom.")
            return
        tile = self._current_tile(session)
        self._ensure_capture_hideout_reaction(session, tile, show_rolls=show_rolls)
        if not session.capture_hideout_reaction_checked:
            session.log.append("The hideout guards must be approached before paying ransom.")
            return
        if not is_bribe_reaction(session.capture_hideout_reaction_key):
            session.log.append(
                "The hideout guards will not accept ransom. Defeat them in combat to rescue your comrades."
            )
            return
        fighters = [member for member in session.party if member.current_life > 0]
        if dwarf_miser_blocks_bribe(fighters):
            session.log.append(
                "The dwarves refuse to pay ransom (Miser trait with 2+ dwarves). Fight the guards instead."
            )
            return
        captives = [m for m in session.party if m.character_id in session.captured_character_ids]
        if not captives:
            session.log.append("No captive heroes found in the party.")
            return
        ransom_total = sum(max(1, m.level) * 10 for m in captives)
        living = [m for m in session.party if m.current_life > 0]
        party_gold = sum(m.gold for m in living)
        if party_gold < ransom_total:
            session.log.append(
                f"Ransom required: {ransom_total}gp total "
                f"({' + '.join(f'{max(1,m.level)*10}gp for {m.name}' for m in captives)}). "
                f"Party has only {party_gold}gp."
            )
            return
        remaining = ransom_total
        for member in sorted(living, key=lambda item: item.marching_order):
            if remaining <= 0:
                break
            take = min(member.gold, remaining)
            member.gold -= take
            remaining -= take
        tile = self._current_tile(session)
        for captive in captives:
            rescued_life = roll_d3()
            captive.current_life = rescued_life
            restored_equipment = self._restore_captive_equipment(session, captive)
            session.log.append(
                f"{captive.name} is ransomed and freed! They recover d3 = {rescued_life} Life."
            )
            if restored_equipment:
                session.log.append(f"{captive.name}'s stripped equipment is returned.")
        session.log.append(f"Ransom paid: {ransom_total}gp.")
        session.captured_character_ids = []
        session.captured_stripped_equipment = {}
        self._clear_capture_hideout_state(session)
        tile.resolved = True
        tile.enemies = []
        session.mode = "exploration"

    def _rescue_captives(self, session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
        """Restore captured heroes when their hideout is cleared in combat."""
        captives = [m for m in session.party if m.character_id in session.captured_character_ids]
        if not captives:
            session.captured_character_ids = []
            session.captured_stripped_equipment = {}
            return
        for captive in captives:
            rescued_life = roll_d3()
            captive.current_life = rescued_life
            restored_equipment = self._restore_captive_equipment(session, captive)
            if show_rolls:
                session.log.append(
                    f"{captive.name} is freed from captivity! They recover d3 = {rescued_life} Life."
                )
            if restored_equipment:
                session.log.append(f"{captive.name} recovers their stripped equipment.")
        session.log.append(
            "The captive heroes recover their equipment. Loot any stripped gold left as treasure."
        )
        session.captured_character_ids = []
        session.captured_stripped_equipment = {}
        self._clear_capture_hideout_state(session)

    def _secret_reveal_blocker(
        self,
        session: SessionState,
        discoverer: PartyMemberState,
        secret_id: str,
        *,
        spell_id: str | None = None,
    ) -> str | None:
        if discoverer.current_life <= 0:
            return "Choose a living hero to discover the Secret."
        if secret_id != "magical_power_increase" and has_secret(discoverer, secret_id):
            return f"{discoverer.name} has already discovered {secret_label(secret_id)}."
        if secret_id == "hidden_treasure_location" and not self._tile_accepts_hidden_treasure_secret(
            self._current_tile(session)
        ):
            return "Location of a Hidden Treasure can be automated in an empty non-entrance room with no unresolved trap or treasure."
        if secret_id in {"magic_item_location", "scroll_location"}:
            tile = self._current_tile(session)
            if tile.tile_type != "room" or tile.content_key == "entrance":
                return f"{secret_label(secret_id)} can be automated in a non-entrance room."
        if secret_id == "someone_imprisoned" and not session.captured_character_ids:
            return "Someone Has Been Imprisoned can only be revealed when a hero is currently held captive by foes."
        if secret_id == "someone_imprisoned" and not self._can_place_hideout_near_tile(session, self._current_tile(session)):
            return "Someone Has Been Imprisoned needs free map space around the current tile to place a hideout."
        class_id = discoverer.class_id.strip().lower()
        if secret_id == "new_spell" and class_id not in SPELLCASTER_CLASSES:
            return "Only a spellcaster can reveal the New Spell Secret."
        if secret_id == "magical_power_increase" and class_id not in SPELLCASTER_CLASSES | {"cleric"}:
            return "Only a cleric or spellcaster can reveal the magical/spiritual power Secret."
        if secret_id == "new_spell":
            spell_name = self._secret_spell_name(spell_id)
            if not spell_name:
                return "Choose a spell for New Spell."
        if secret_id == "magical_power_increase":
            spell_name = self._secret_spell_name(spell_id, include_prayers=True)
            if not spell_name:
                return "Choose a spell or Healing prayer for the power increase."
            if class_id == "cleric" and normalize_spell_name(spell_name) not in {"healing_prayer", "healing", "blessing"}:
                return "Clerics can apply this Secret to Blessing or Healing prayer."
            tag = f"magical_power_increase:{spell_name}".lower()
            if any(str(item).strip().lower() == tag for item in discoverer.secrets or []):
                return f"{discoverer.name} already has an extra use of {spell_name} per adventure."
        if secret_id == "dragonslayer_bloodline" and class_id not in {"barbarian", "dwarf"}:
            return "Only a barbarian or dwarf can reveal the dragon-slayer bloodline Secret."
        if secret_id == "yummy_meal" and not any(
            member.class_id.strip().lower() == "halfling" and member.current_life > 0 for member in session.party
        ):
            return "You need at least one halfling in the party to discover this Secret."
        if secret_id == "potion_recipe":
            defeated_majors = session.major_foes_defeated_this_adventure
            if defeated_majors < 2:
                return (
                    f"Recipe for a Potion requires 2 Major Foes defeated this adventure "
                    f"(party has {defeated_majors})."
                )
            if self._outside_party_gold(session) < 50:
                return "Recipe for a Potion requires 50gp for components."
        return None

    def _apply_revealed_secret(
        self,
        session: SessionState,
        discoverer: PartyMemberState,
        secret_id: str,
        *,
        spell_id: str | None = None,
    ) -> list[str]:
        log: list[str] = []
        if secret_id == "potion_recipe":
            paid, payment_log = self._spend_outside_party_gold(session, 50, label="potion recipe components")
            if paid:
                log.extend(payment_log)
        if secret_id == "magical_power_increase":
            log.extend(self._apply_magical_power_secret(discoverer, spell_id))
        elif secret_id == "new_spell":
            log.extend(self._apply_new_spell_secret(session, discoverer, spell_id))
        else:
            record_secret(discoverer, secret_id)
            if secret_id == "hidden_treasure_location":
                log.extend(self._apply_hidden_treasure_secret(session))
            elif secret_id == "magic_item_location":
                log.extend(self._apply_magic_item_location_secret(session))
                consume_secret(discoverer, secret_id)
            elif secret_id == "scroll_location":
                log.extend(self._apply_scroll_location_secret(session, discoverer))
                consume_secret(discoverer, secret_id)
            elif secret_id == "potion_recipe":
                log.append(
                    f"{discoverer.name} records a potion recipe. Between adventures, the party may buy a Potion of Healing for 50gp."
                )
            elif secret_id == "dragonslayer_bloodline":
                log.append(f"{discoverer.name} gains the Dragonslayer trait (+1 Attack and Defense vs dragons).")
            elif secret_id == "someone_imprisoned":
                log.extend(self._apply_someone_imprisoned_secret(session, discoverer))
            elif secret_id == "yummy_meal":
                log.append(
                    f"{discoverer.name} records {secret_label(secret_id)} for use when the party is ready to cook."
                )
            else:
                log.append(
                    f"{discoverer.name} records {secret_label(secret_id)} for the moment when its timing condition applies."
                )
        return log

    def _all_secret_spell_names(self, *, include_prayers: bool = False) -> list[str]:
        names = [
            *WIZARD_BASIC_SPELLS,
            *ELF_BASIC_SPELLS,
            *DRUID_SPELLS,
            *ILLUSIONIST_SPELLS,
        ]
        expert_rows = self.rules.expert_skills().get("expert_spells", [])
        if isinstance(expert_rows, list):
            for row in expert_rows:
                if isinstance(row, dict) and row.get("name"):
                    names.append(str(row["name"]))
        if include_prayers:
            names.extend(["Blessing", "Healing prayer"])
        deduped: list[str] = []
        seen: set[str] = set()
        for name in names:
            key = normalize_spell_name(name)
            if key not in seen:
                seen.add(key)
                deduped.append(name)
        return deduped

    def _secret_spell_name(self, spell_id: str | None, *, include_prayers: bool = False) -> str | None:
        normalized = normalize_spell_name(spell_id or "")
        if not normalized:
            return None
        for spell in self._all_secret_spell_names(include_prayers=include_prayers):
            if normalize_spell_name(spell) == normalized:
                return spell
        return None

    def _apply_new_spell_secret(
        self,
        session: SessionState,
        discoverer: PartyMemberState,
        spell_id: str | None,
    ) -> list[str]:
        spell_name = self._secret_spell_name(spell_id)
        if not spell_name:
            return ["Choose a spell for New Spell."]
        discoverer.spells.append(spell_name)
        temporary = list(session.secret_temporary_spells.get(discoverer.character_id, []))
        temporary.append(spell_name)
        session.secret_temporary_spells[discoverer.character_id] = temporary
        consume_secret(discoverer, "new_spell")
        return [
            f"{discoverer.name} learns {spell_name} from the Secret and gains one temporary spell slot for this adventure."
        ]

    def _apply_magical_power_secret(
        self,
        discoverer: PartyMemberState,
        spell_id: str | None,
    ) -> list[str]:
        spell_name = self._secret_spell_name(spell_id, include_prayers=True)
        if not spell_name:
            return ["Choose a spell or Healing prayer for the power increase."]
        normalized = normalize_spell_name(spell_name)
        tag = f"magical_power_increase:{spell_name}"
        if any(str(item).strip().lower() == tag.lower() for item in discoverer.secrets or []):
            return [f"{discoverer.name} already has an extra use of {spell_name} per adventure."]
        discoverer.secrets.append(tag)
        if normalized in {"healing_prayer", "healing"}:
            return [f"{discoverer.name} gains one permanent extra use of Healing prayer per adventure."]
        if not any(normalize_spell_name(item) == normalized for item in discoverer.spells):
            discoverer.spells.append(spell_name)
        return [f"{discoverer.name} gains one permanent extra use of {spell_name} per adventure."]

    def _apply_magic_item_location_secret(self, session: SessionState) -> list[str]:
        tile = self._current_tile(session)
        outcome = self.table_roller.roll_magic_treasure(environment=session.environment)
        log = list(outcome.log)
        items, item_log = resolve_treasure_item_list(list(outcome.items))
        log.extend(item_log)
        tile.treasure_items.extend(items)
        tile.treasure_claimed = False
        summary = outcome.summary or "Magic treasure"
        if tile.treasure_summary:
            tile.treasure_summary = f"{tile.treasure_summary}; Secret magic item: {summary}"
        else:
            tile.treasure_summary = f"Secret magic item: {summary}"
        if "Secret Magic Item" not in tile.objects:
            tile.objects.append("Secret Magic Item")
        if items:
            log.append(
                "You recognize this location as a hidden magic item cache. "
                f"It can be revealed by speaking the correct password: {', '.join(items)}. Use Claim Treasure."
            )
        else:
            log.append(
                "You recognize this location as a hidden magic item cache. "
                "It can be revealed by speaking the correct password. Use Claim Treasure."
            )
        return log

    def _apply_scroll_location_secret(
        self,
        session: SessionState,
        discoverer: PartyMemberState,
        spell_id: str | None = None,
        scroll_form: str | None = None,
    ) -> list[str]:
        scroll_item = self._scroll_location_item(spell_id, scroll_form)
        ok, message = can_add_item(discoverer, scroll_item)
        if not ok:
            tile = self._current_tile(session)
            tile.treasure_items.append(scroll_item)
            tile.treasure_claimed = False
            if tile.treasure_summary:
                tile.treasure_summary = f"{tile.treasure_summary}; Secret scroll: {scroll_item}"
            else:
                tile.treasure_summary = f"Secret scroll: {scroll_item}"
            if "Secret Scroll" not in tile.objects:
                tile.objects.append("Secret Scroll")
            return [
                "Hidden in a niche, you find a scroll, piece of bark or prism with a spell of your choice. "
                f"It is {scroll_item}, but {discoverer.name} cannot carry it now ({message}). "
                "Use Claim Treasure after making room."
            ]
        discoverer.inventory.append(scroll_item)
        return [
            "Hidden in a niche, you find a scroll, piece of bark or prism with a spell of your choice. "
            f"{discoverer.name} adds {scroll_item} to inventory; it can be burned, or copied by a wizard if eligible."
        ]

    def _scroll_location_item(self, spell_id: str | None = None, scroll_form: str | None = None) -> str:
        form = (scroll_form or "scroll").strip().lower()
        if form in {"prism", "illusionist_prism", "illusionist prism"}:
            return f"Prism of {self._illusionist_prism_spell_name(spell_id)}"
        if form in {"bark", "druid_bark", "druid bark"}:
            return f"Bark of {self._druid_bark_spell_name(spell_id)}"
        return f"Scroll of {self._basic_scroll_spell_name(spell_id)}"

    def _basic_scroll_spell_name(self, spell_id: str | None = None) -> str:
        if spell_id:
            normalized = normalize_spell_name(spell_id)
            for spell in WIZARD_BASIC_SPELLS:
                if normalize_spell_name(spell) == normalized:
                    return spell
        row = self.table_roller.roll_random_basic_spell()
        if row and row.get("spell"):
            return str(row["spell"])
        return WIZARD_BASIC_SPELLS[0]

    def _illusionist_prism_spell_name(self, spell_id: str | None = None) -> str:
        if spell_id:
            normalized = normalize_spell_name(spell_id)
            for row in self.table_roller.tables.get("illusionist_spells_table", []):
                spell = str(row.get("spell", ""))
                if normalize_spell_name(spell) == normalized:
                    return spell
        item, _ = self.table_roller.roll_random_spell_loot("caverns")
        return item.replace("Prism of ", "", 1)

    def _druid_bark_spell_name(self, spell_id: str | None = None) -> str:
        if spell_id:
            normalized = normalize_spell_name(spell_id)
            for row in self.table_roller.tables.get("druid_spells_table", []):
                spell = str(row.get("spell", ""))
                if normalize_spell_name(spell) == normalized:
                    return spell
        item, _ = self.table_roller.roll_random_spell_loot("fungal_grottoes")
        return item.replace("Bark of ", "", 1)


    def _apply_hidden_treasure_secret(self, session: SessionState) -> list[str]:
        tile = self._current_tile(session)
        gold = sum(roll_d6() for _ in range(3)) * 10
        living = [member for member in session.party if member.current_life > 0]
        leftover, payouts = distribute_gold_among(
            sorted(living, key=lambda item: item.marching_order),
            gold,
            servant_owner_ids=self._servant_owner_ids(session),
        )
        if "Secret Hidden Treasure" not in tile.objects:
            tile.objects.append("Secret Hidden Treasure")
        log = [
            "Here a hidden treasure can be revealed by speaking a secret password. "
            f"A niche opens in a wall, and you find {gold}gp."
        ]
        if payouts:
            log.append(f"Gold carried: {', '.join(payouts)}.")
        if leftover:
            log.append(f"{leftover}gp cannot be carried and remains behind.")
        return log

    def _apply_someone_imprisoned_secret(
        self,
        session: SessionState,
        discoverer: PartyMemberState,
    ) -> list[str]:
        """Generate the captive hideout when 'Someone Has Been Imprisoned' is revealed via Reveal Secret.

        Clues were already spent by _reveal_secret_with_clues; record_secret was already called.
        Reuses _build_hideout_tile to create the tile and wires exits exactly as _find_captive_hideout does.
        """
        if session.capture_hideout_tile_id:
            existing = next(
                (t for t in session.map_state.tiles if t.id == session.capture_hideout_tile_id), None
            )
            if existing:
                return [f"The captive hideout is already known: {existing.title}."]
        if session.xp_system != "slow_and_sure":
            self._grant_xp_credit(session, 1, f"{discoverer.name} reveals 'Someone Has Been Imprisoned':")
        captive_names = ", ".join(
            m.name for m in session.party if m.character_id in session.captured_character_ids
        ) or "unknown captive(s)"
        foe_name = session.capture_foe_name or "Unknown Foe"
        hideout_tile = self._build_hideout_tile(session, foe_name, show_rolls=True)
        if hideout_tile is None:
            return [
                "Someone Has Been Imprisoned cannot be used here: no open map space is available around this tile."
            ]
        session.map_state.tiles.append(hideout_tile)
        session.capture_hideout_tile_id = hideout_tile.id
        origin = self._current_tile(session)
        hideout_exit = self._add_hideout_exit(origin, hideout_tile)
        self._add_hideout_return_exit(hideout_tile, origin, hideout_exit)
        from .heroic_skill_effects import mark_tile_visited
        mark_tile_visited(session, hideout_tile.id)
        return [
            f"The party's clues point to a cave nearby: {hideout_tile.title}. "
            f"A new passage leads to it. "
            f"{captive_names} will be found there guarded by {foe_name}s."
        ]

    def _tile_accepts_hidden_treasure_secret(self, tile: TileState) -> bool:
        if tile.tile_type != "room" or tile.content_key == "entrance":
            return False
        if any(enemy.life > 0 for enemy in tile.enemies):
            return False
        if tile.trap_key and not tile.trap_resolved:
            return False
        if tile.treasure_gold or tile.treasure_items:
            return False
        return True

    def _secret_holder(
        self,
        session: SessionState,
        character_id: str | None,
        secret_id: str,
    ) -> PartyMemberState | None:
        if character_id:
            member = next((item for item in session.party if item.character_id == character_id), None)
            if member is None or member.current_life <= 0:
                return None
            return member if has_secret(member, secret_id) else None
        return next(
            (
                member
                for member in sorted(session.party, key=lambda item: item.marching_order)
                if member.current_life > 0 and has_secret(member, secret_id)
            ),
            None,
        )

    def _use_secret(
        self,
        session: SessionState,
        character_id: str | None,
        secret_id: str | None,
        foe_id: str | None = None,
        spell_id: str | None = None,
        scroll_form: str | None = None,
        target_character_id: str | None = None,
    ) -> None:
        secret = secret_by_id(secret_id)
        if secret is None:
            session.log.append("Choose which recorded Secret to use.")
            return
        holder = self._secret_holder(session, character_id, secret.id)
        if holder is None:
            session.log.append(f"Choose a living hero who has {secret.label}.")
            return
        if secret.id == "weakness_of_a_foe":
            self._use_secret_weakness(session, holder, foe_id)
        elif secret.id == "deal_with_a_foe":
            self._use_secret_deal(session, holder, foe_id)
        elif secret.id == "terrifying_secret":
            self._use_terrifying_secret(session, holder)
        elif secret.id == "secret_diet":
            self._use_secret_diet(session, holder)
        elif secret.id == "magic_item_location":
            self._use_secret_magic_item_location(session, holder)
        elif secret.id == "scroll_location":
            self._use_secret_scroll_location(session, holder, spell_id, scroll_form=scroll_form)
        elif secret.id == "enemy_in_dungeon":
            self._use_secret_enemy_in_dungeon(session, holder, foe_id)
        elif secret.id == "prisoner":
            session.log.append(
                "The Prisoner is freed with Break chains during combat, then escorted to the dungeon exit."
            )
        elif secret.id == "true_name_spiritual_entity":
            self._use_secret_true_name(session, holder, spell_id, foe_id, target_character_id)
        elif secret.id == "chaos_fanatics":
            self._use_secret_chaos_fanatics(session, holder)
        elif secret.id == "corridor_leads":
            self._use_secret_corridor_leads(session, holder)
        elif secret.id == "yummy_meal":
            self._use_secret_yummy_meal(session, holder)
        else:
            session.log.append(f"{secret.label} is recorded for manual use when its timing condition applies.")

    def _use_secret_magic_item_location(self, session: SessionState, holder: PartyMemberState) -> None:
        if session.mode != "exploration":
            session.log.append("Location of a Magic Item is used during exploration.")
            return
        tile = self._current_tile(session)
        if tile.tile_type != "room" or tile.content_key == "entrance":
            session.log.append("Location of a Magic Item can be used in a non-entrance room.")
            return
        if not consume_secret(holder, "magic_item_location"):
            session.log.append(f"{holder.name} no longer has Location of a Magic Item.")
            return
        session.log.extend(self._apply_magic_item_location_secret(session))

    def _use_secret_scroll_location(
        self,
        session: SessionState,
        holder: PartyMemberState,
        spell_id: str | None = None,
        scroll_form: str | None = None,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Location of a Scroll is used during exploration.")
            return
        tile = self._current_tile(session)
        if tile.tile_type != "room" or tile.content_key == "entrance":
            session.log.append("Location of a Scroll can be used in a non-entrance room.")
            return
        if not consume_secret(holder, "scroll_location"):
            session.log.append(f"{holder.name} no longer has Location of a Scroll.")
            return
        session.log.extend(self._apply_scroll_location_secret(session, holder, spell_id, scroll_form=scroll_form))

    def _use_secret_enemy_in_dungeon(
        self,
        session: SessionState,
        holder: PartyMemberState,
        foe_id: str | None,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Your Enemy Is in the Dungeon is declared when a Major Foe is met.")
            return
        if session.secret_enemy_foe_id:
            session.log.append("Your Enemy Is in the Dungeon is already active for this combat.")
            return
        tile = self._current_tile(session)
        majors = [enemy for enemy in tile.enemies if enemy.life > 0 and enemy.category in {"weird", "boss"}]
        if not majors:
            session.log.append("Your Enemy Is in the Dungeon requires a living Major Foe target.")
            return
        target = next((enemy for enemy in majors if enemy.id == foe_id), None) if foe_id else majors[0]
        if target is None:
            session.log.append("Choose a living Major Foe for Your Enemy Is in the Dungeon.")
            return
        if not consume_secret(holder, "enemy_in_dungeon"):
            session.log.append(f"{holder.name} no longer has Your Enemy Is in the Dungeon.")
            return
        self._transform_foe_into_chaos_lord(session, target)
        session.secret_enemy_foe_id = target.id
        session.secret_enemy_character_id = holder.character_id
        session.log.append(
            f"{holder.name} uses Your Enemy Is in the Dungeon: the Major Foe is revealed as a Chaos Lord. "
            "Party attacks against it get +1 this combat."
        )

    def _transform_foe_into_chaos_lord(self, session: SessionState, target: EnemyState) -> None:
        hcl = self._highest_character_level(session.party)
        monsters = self.rules.monsters()
        template = next((entry for entry in monsters.get("boss", []) if entry.get("name") == "Chaos Lord"), None)
        if template is None:
            target.name = "Chaos Lord"
            target.category = "boss"
            target.level = max(target.level, hcl + 5)
            target.max_life = max(target.max_life, 6)
            target.life = target.max_life
            target.attacks = max(target.attacks, 3)
            tags = {tag.lower() for tag in target.tags}
            for tag in ("boss", "chaos"):
                if tag not in tags:
                    target.tags.append(tag)
            return
        level = max(1, hcl + int(template.get("level_delta", 0)))
        life = _parse_monster_life(template.get("life", 1), hcl)
        attacks = _parse_monster_attacks(template.get("attacks", 1), hcl)
        tags = template_surprise_tags(template) + template_weapon_allow_tags(template) + template_combat_tags(template)
        power_tag = roll_random_power_tag(template)
        if power_tag:
            tags.append(power_tag)
        target.name = str(template["name"])
        target.category = "boss"
        target.level = level
        target.life = life
        target.max_life = life
        target.attacks = attacks
        target.tags = tags
        target.on_hit_effects = template_on_hit_effects(template)
        target.encounter_start_effects = template_encounter_start_effects(template)
        target.per_turn_effects = template_per_turn_effects(template)
        target.special_attacks = template_special_attacks(template)

    def _party_member_by_id(self, session: SessionState, character_id: str | None) -> PartyMemberState | None:
        if not character_id:
            return None
        return next((member for member in session.party if member.character_id == character_id), None)

    def _maybe_discover_prisoner(self, session: SessionState, tile: TileState) -> None:
        if tile.prisoner_discovered or tile.prisoner_chains_broken or session.rescued_prisoner_active:
            return
        holders = [member for member in session.party if member.current_life > 0 and has_secret(member, "prisoner")]
        if not holders:
            return
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not any(enemy.category in {"minions", "boss"} for enemy in living):
            return
        tile.prisoner_discovered = True
        if "Chained Prisoner" not in tile.objects:
            tile.objects.append("Chained Prisoner")
        discoverer = holders[0]
        session.log.append(
            f"{discoverer.name} recognizes The Prisoner secret: an important NPC is chained to the wall here. "
            "Break the chains with an Attack roll vs L4 (+Level for rogues and barbarians)."
        )

    def _prisoner_holder(self, session: SessionState) -> PartyMemberState | None:
        return next(
            (member for member in session.party if member.current_life > 0 and has_secret(member, "prisoner")),
            None,
        )

    def _prisoner_chain_break_allowed(self, session: SessionState, tile: TileState) -> bool:
        if not tile.prisoner_discovered or tile.prisoner_chains_broken:
            return False
        if session.mode == "combat":
            return True
        if session.mode == "exploration":
            return not any(enemy.life > 0 for enemy in tile.enemies)
        return False

    def _break_prisoner_chains(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool = True,
    ) -> None:
        if session.rescued_prisoner_active:
            session.log.append("The prisoner is already free and traveling with the party.")
            return
        tile = self._current_tile(session)
        if not self._prisoner_chain_break_allowed(session, tile):
            session.log.append(
                "Break chains during combat, or after the room's guards are defeated."
            )
            return
        if not self._prisoner_holder(session):
            session.log.append("A living hero must hold The Prisoner Secret to attempt a rescue.")
            return
        breaker = self._party_member_by_id(session, character_id)
        if breaker is None or breaker.current_life <= 0:
            session.log.append("Choose a living hero to break the prisoner's chains.")
            return
        from .combat import attack_hits
        from .dice import roll_exploding_for_level

        total, rolls = roll_exploding_for_level(breaker)
        modifier = breaker.level + breaker.attack_bonus
        if breaker.class_id.strip().lower() in {"rogue", "barbarian"}:
            modifier += breaker.level
        final_total = total + modifier
        if show_rolls:
            session.log.append(
                f"{breaker.name} tries to break the chains: "
                f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L4."
            )
        if session.mode == "combat":
            session.prisoner_chain_skip_attack[breaker.character_id] = True
        if not attack_hits(final_total, 4):
            session.log.append("The chains hold firm for now.")
            return
        tile.prisoner_chains_broken = True
        session.rescued_prisoner_active = True
        holder = self._prisoner_holder(session)
        session.rescued_prisoner_holder_id = holder.character_id if holder else breaker.character_id
        session.log.append(
            f"{breaker.name} breaks the chains! The rescued NPC joins the party. "
            "Escort them to the dungeon exit to claim the reward."
        )

    def _choose_prisoner_reward(
        self,
        session: SessionState,
        character_id: str | None,
        reward_choice: str | None,
    ) -> None:
        if not session.rescued_prisoner_active:
            session.log.append("No rescued prisoner is traveling with the party.")
            return
        holder = self._party_member_by_id(session, session.rescued_prisoner_holder_id)
        if holder is None:
            session.log.append("The Prisoner Secret holder is no longer available.")
            return
        if character_id and character_id != holder.character_id:
            session.log.append(f"{holder.name} must choose The Prisoner reward.")
            return
        choice = (reward_choice or "").strip().lower()
        if choice in {"gold", "double_gold", "doubled_gold", "gp"}:
            session.prisoner_reward_choice = "gold"
            session.log.append(
                f"{holder.name} will claim double held gp when the party leaves the dungeon with the prisoner."
            )
            return
        if choice in {"magic", "treasure", "item"}:
            session.prisoner_reward_choice = "magic"
            session.log.append(
                f"{holder.name} will claim a random magic item and treasure roll when the party exits with the prisoner."
            )
            return
        session.log.append("Choose magic item + treasure roll, or double held gp.")

    def _apply_prisoner_exit_reward(self, session: SessionState) -> None:
        holder_id = session.rescued_prisoner_holder_id
        holder = self._party_member_by_id(session, holder_id)
        choice = session.prisoner_reward_choice or "magic"
        if holder is not None and has_secret(holder, "prisoner"):
            consume_secret(holder, "prisoner")
        if choice == "gold":
            living = [member for member in session.party if member.current_life > 0]
            doubled: list[str] = []
            for member in living:
                if member.gold <= 0:
                    continue
                before = member.gold
                member.gold *= 2
                doubled.append(f"{member.name} {before}gp → {member.gold}gp")
            if doubled:
                session.log.append(
                    "The rescued prisoner reward doubles held gp: " + "; ".join(doubled) + "."
                )
            else:
                session.log.append("The rescued prisoner reward doubles held gp, but nobody carried any gold.")
        else:
            if holder is None:
                session.log.append("The Prisoner reward could not be delivered — the Secret holder is unavailable.")
            else:
                outcome = self.table_roller.roll_magic_treasure(environment=session.environment)
                magic_items, item_log = resolve_treasure_item_list(list(outcome.items))
                holder.inventory.extend(magic_items)
                treasure = self._roll_treasure(session)
                items = self._finalize_treasure_items(session, list(treasure.items), show_rolls=True)
                holder.inventory.extend(items)
                if treasure.gold:
                    holder.gold += treasure.gold
                session.log.append(
                    f"The rescued prisoner reward: magic item and treasure roll granted to {holder.name}."
                )
                session.log.extend(outcome.log)
                session.log.extend(item_log)
                session.log.extend(treasure.log)
        session.rescued_prisoner_active = False
        session.rescued_prisoner_holder_id = None
        session.prisoner_reward_choice = None
        session.log.append("The prisoner reaches the surface safely.")

    def _true_name_trap_rescue_target(
        self,
        session: SessionState,
        target_character_id: str | None,
    ) -> PartyMemberState | None:
        from .heroic_skill_effects import FALL_TRAP_KEYS

        target = self._party_member_by_id(session, target_character_id)
        if target is None:
            return None
        if target.character_id in session.fallen_outside_character_ids:
            return target
        tile = self._current_tile(session)
        if target.current_life <= 0 and tile.trap_key and tile.trap_key in FALL_TRAP_KEYS:
            return target
        return None

    def _maybe_end_combat_after_true_name(
        self,
        session: SessionState,
        tile: TileState,
        *,
        active_enemy_ids: set[str],
        standing_before: set[str],
    ) -> None:
        if any(enemy.life > 0 for enemy in tile.enemies):
            return
        result = CombatRound(
            party=session.party,
            enemies=tile.enemies,
            log=[],
            combat_over=True,
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=True,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )

    def _use_secret_true_name(
        self,
        session: SessionState,
        holder: PartyMemberState,
        choice: str | None,
        foe_id: str | None,
        target_character_id: str | None = None,
    ) -> None:
        mode = (choice or "").strip().lower()
        family = true_name_mode_family(mode)
        if family is None:
            session.log.append(
                "Choose an angel effect (heal one PC or trap rescue) or a demon effect (major damage or slay minions)."
            )
            return
        locked = true_name_alignment(holder)
        if locked is None:
            set_true_name_alignment(holder, family)
            locked = family
        elif locked != family:
            session.log.append(
                f"{holder.name} is bound to a {locked} True Name and cannot invoke the other."
            )
            return
        if not consume_secret(holder, "true_name_spiritual_entity"):
            session.log.append(f"{holder.name} no longer has True Name of a Spiritual Entity.")
            return

        if family == "angel":
            resolved = mode if mode.startswith("angel_") else "angel_heal_one"
            if resolved in {"angel", "angel_heal"}:
                resolved = "angel_heal_one"
            if resolved == "angel_heal_one":
                target = self._party_member_by_id(session, target_character_id)
                if target is None or target.current_life <= 0:
                    holder.secrets.append("true_name_spiritual_entity")
                    session.log.append("Choose a living PC for the angelic True Name to heal to full Life.")
                    return
                target.current_life = target.max_life
                session.log.append(
                    f"{holder.name} invokes an angelic True Name: {target.name} is healed to full Life "
                    f"({target.current_life}/{target.max_life})."
                )
                return
            if resolved == "angel_trap_rescue":
                target = self._true_name_trap_rescue_target(session, target_character_id)
                if target is None:
                    holder.secrets.append("true_name_spiritual_entity")
                    session.log.append(
                        "Trap rescue requires a PC lost to a trapdoor or fallen on a trap tile."
                    )
                    return
                target.current_life = target.max_life
                if target.character_id in session.fallen_outside_character_ids:
                    session.fallen_outside_character_ids = [
                        item
                        for item in session.fallen_outside_character_ids
                        if item != target.character_id
                    ]
                session.log.append(
                    f"{holder.name} invokes an angelic True Name: {target.name} is rescued from the trap "
                    f"at full Life ({target.current_life}/{target.max_life})."
                )
                return
            holder.secrets.append("true_name_spiritual_entity")
            session.log.append("Choose angel_heal_one or angel_trap_rescue.")
            return

        if session.mode != "combat":
            holder.secrets.append("true_name_spiritual_entity")
            session.log.append("The demonic True Name is used against foes in combat.")
            return
        tile = self._current_tile(session)
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living:
            holder.secrets.append("true_name_spiritual_entity")
            session.log.append("There are no foes for the demonic True Name.")
            return
        active_enemy_ids = {enemy.id for enemy in living}
        standing_before = {
            member.character_id for member in combat_party(session, tile.id) if member.current_life > 0
        }
        resolved = mode if mode.startswith("demon_") else "demon_major"
        if resolved in {"demon", "demon_damage"}:
            resolved = "demon_major"

        if resolved == "demon_major":
            majors = [enemy for enemy in living if enemy.category in {"weird", "boss"}]
            target = next((enemy for enemy in majors if enemy.id == foe_id), None) if foe_id else None
            if target is None and majors:
                target = majors[0]
            if target is None:
                holder.secrets.append("true_name_spiritual_entity")
                session.log.append("Choose a living Major Foe for the demonic True Name.")
                return
            target.life = max(0, target.life - 4)
            session.log.append(
                f"{holder.name} invokes a demonic True Name against {target.name}, dealing 4 Life damage."
            )
            if target.life <= 0:
                session.log.append(f"{target.name} is destroyed by the True Name.")
            self._maybe_end_combat_after_true_name(
                session,
                tile,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )
            return

        if resolved == "demon_minions":
            minors = [enemy for enemy in living if enemy.category in {"vermin", "minions"}]
            if not minors:
                holder.secrets.append("true_name_spiritual_entity")
                session.log.append("There are no vermin or minions for the demonic True Name to destroy.")
                return
            slain = 0
            for enemy in minors:
                if slain >= 6:
                    break
                if enemy.life <= 0:
                    continue
                enemy.life = 0
                slain += 1
                session.log.append(f"{enemy.name} is destroyed by the demonic True Name.")
            session.log.append(
                f"{holder.name}'s demonic True Name destroys {slain} minor foe(s) (up to 6)."
            )
            self._maybe_end_combat_after_true_name(
                session,
                tile,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )
            return

        holder.secrets.append("true_name_spiritual_entity")
        session.log.append("Choose demon_major or demon_minions.")

    def _use_secret_weakness(
        self,
        session: SessionState,
        holder: PartyMemberState,
        foe_id: str | None,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Weakness of a Foe is declared when the Major Foe is encountered.")
            return
        if session.secret_weakness_foe_id:
            session.log.append("Weakness of a Foe is already active for this combat.")
            return
        tile = self._current_tile(session)
        majors = [enemy for enemy in tile.enemies if enemy.life > 0 and enemy.category in {"weird", "boss"}]
        if not majors:
            session.log.append("Weakness of a Foe requires a living Major Foe target.")
            return
        target = next((enemy for enemy in majors if enemy.id == foe_id), None) if foe_id else majors[0]
        if target is None:
            session.log.append("Choose a living Major Foe for Weakness of a Foe.")
            return
        if not consume_secret(holder, "weakness_of_a_foe"):
            session.log.append(f"{holder.name} no longer has Weakness of a Foe.")
            return
        session.secret_weakness_foe_id = target.id
        session.secret_weakness_character_id = holder.character_id
        session.log.append(
            f"{holder.name} uses Weakness of a Foe: party attacks against {target.name} get +2 this combat."
        )

    def _use_secret_deal(
        self,
        session: SessionState,
        holder: PartyMemberState,
        foe_id: str | None = None,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Deal with a Foe is declared when the foe is encountered.")
            return
        tile = self._current_tile(session)
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living:
            session.log.append("There are no active foes for Deal with a Foe.")
            return
        selected = next((enemy for enemy in living if enemy.id == foe_id), None) if foe_id else None
        if foe_id and selected is None:
            session.log.append("Choose a living foe group for Deal with a Foe.")
            return
        considered = [selected] if selected is not None else living
        if any("final_boss" in {tag.lower() for tag in enemy.tags} for enemy in considered):
            session.log.append("Deal with a Foe cannot bypass the Final Boss.")
            return
        if any(enemy.category == "vermin" for enemy in considered):
            session.log.append("Deal with a Foe cannot be used on vermin.")
            return
        target_label = selected.name if selected is not None else "the encountered foes"
        for enemy in considered:
            self._record_deal_with_foe(session, tile, enemy.name)
        session.log.append(
            f"{holder.name} uses Deal with a Foe on {target_label}. "
            "The foes let the party pass; no treasure or XP is gained. The deal persists on this tile."
        )
        self._end_peaceful_encounter(session, tile)

    def _record_deal_with_foe(self, session: SessionState, tile: TileState, foe_name: str) -> None:
        normalized = foe_name.strip()
        if not normalized:
            return
        existing = session.deal_with_foe_entries
        if any(
            deal_entry_matches_foe(entry.tile_id, entry.foe_name, tile.id, normalized)
            for entry in existing
        ):
            return
        session.deal_with_foe_entries.append(DealWithFoeEntry(tile_id=tile.id, foe_name=normalized))
        tile.deal_treasure_forbidden = True

    def _deal_pass_available(self, session: SessionState, tile: TileState) -> bool:
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living:
            return False
        if not any(has_secret(member, "deal_with_a_foe") for member in session.party if member.current_life > 0):
            return False
        for enemy in living:
            if any(
                deal_entry_matches_foe(entry.tile_id, entry.foe_name, tile.id, enemy.name)
                for entry in session.deal_with_foe_entries
            ):
                return True
        return False

    def _pass_using_deal(self, session: SessionState, character_id: str | None) -> None:
        tile = self._current_tile(session)
        holder = self._secret_holder(session, character_id, "deal_with_a_foe")
        if holder is None:
            session.log.append("Choose a living hero who has Deal with a Foe.")
            return
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living:
            session.log.append("There are no foes to pass using Deal with a Foe.")
            return
        matched = [
            enemy
            for enemy in living
            if any(
                deal_entry_matches_foe(entry.tile_id, entry.foe_name, tile.id, enemy.name)
                for entry in session.deal_with_foe_entries
            )
        ]
        if not matched:
            session.log.append("No recorded deal matches the foes here.")
            return
        foe_label = matched[0].name
        session.log.append(
            f"{holder.name} invokes Deal with a Foe with {foe_label}. "
            "The creatures stand aside; the party passes without treasure or XP."
        )
        self._end_peaceful_encounter(session, tile)

    def _use_terrifying_secret(self, session: SessionState, holder: PartyMemberState) -> None:
        if session.mode != "combat":
            session.log.append("Terrifying Secret is declared during combat before a foe tests morale.")
            return
        if session.terrifying_secret_pending_character_id:
            session.log.append("Terrifying Secret is already waiting for the next morale test.")
            return
        tile = self._current_tile(session)
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living:
            session.log.append("Terrifying Secret requires living foes.")
            return
        if all("final_boss" in {tag.lower() for tag in enemy.tags} for enemy in living):
            session.log.append("Terrifying Secret has no effect on Final Bosses.")
            return
        if not consume_secret(holder, "terrifying_secret"):
            session.log.append(f"{holder.name} no longer has Terrifying Secret.")
            return
        session.terrifying_secret_pending_character_id = holder.character_id
        session.log.append(
            f"{holder.name} uses Terrifying Secret. The next morale test in this combat will fail automatically."
        )

    SECRET_DIET_COST_GP = 100
    SECRET_DIET_HALFLING_COST_GP = 50

    def _use_secret_chaos_fanatics(self, session: SessionState, holder: PartyMemberState) -> None:
        if session.mode != "combat":
            session.log.append("Chaos Fanatics is declared when chaos fanatics are met.")
            return
        if session.secret_chaos_fanatics_active:
            session.log.append("Chaos Fanatics is already active for this combat.")
            return
        tile = self._current_tile(session)
        fanatics = [enemy for enemy in tile.enemies if enemy.life > 0 and is_chaos_fanatic(enemy)]
        if not fanatics:
            session.log.append("Chaos Fanatics requires living chaos fanatics in this encounter.")
            return
        if not consume_secret(holder, "chaos_fanatics"):
            session.log.append(f"{holder.name} no longer has Chaos Fanatics.")
            return
        session.secret_chaos_fanatics_active = True
        session.log.append(
            f"{holder.name} uses Chaos Fanatics: all heroes defend at +1 against the chaos fanatics this combat."
        )

    def _use_secret_corridor_leads(self, session: SessionState, holder: PartyMemberState) -> None:
        if session.mode != "exploration":
            session.log.append("I Know Where This Corridor Leads is used during exploration.")
            return
        tile = self._current_tile(session)
        if tile.content_key == "entrance":
            session.log.append("I Know Where This Corridor Leads cannot be used on the entrance tile.")
            return
        if tile.resolved:
            session.log.append("This tile is already resolved; the room content cannot be rerolled.")
            return
        if any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("I Know Where This Corridor Leads must be used before combat begins on this tile.")
            return
        if tile.defeated_enemies:
            session.log.append("I Know Where This Corridor Leads must be used before foes are defeated here.")
            return
        if not consume_secret(holder, "corridor_leads"):
            session.log.append(f"{holder.name} no longer has I Know Where This Corridor Leads.")
            return
        hcl = self._highest_character_level(session.party)
        content = self._roll_content(session, tile.tile_type, hcl)
        tile.content_key = content["key"]
        tile.description = content["description"]
        tile.objects = list(content["objects"])
        tile.enemies = list(content["enemies"])
        tile.initial_enemy_count = len(content["enemies"])
        tile.resolved = False
        tile.searched = False
        tile.trap_key = None
        tile.trap_level = None
        tile.trap_resolved = False
        tile.trap_probed = False
        tile.treasure_summary = None
        tile.treasure_gold = 0
        tile.treasure_items = []
        tile.treasure_claimed = False
        tile.special_event_key = None
        tile.special_event_summary = None
        if content.get("choices"):
            session.pending_tile_content_choice_tile_id = tile.id
        else:
            session.pending_tile_content_choice_tile_id = None
        self._seed_tile_features(tile, hcl, show_rolls=True, session=session)
        self._resolve_event_foes(session, tile, show_rolls=True)
        if content.get("auto_secret_passage"):
            self._offer_secret_passage(session, tile, show_rolls=True)
        session.log.append(
            f"{holder.name} rerolls the room content table for this tile. The new result is final."
        )

    def _use_secret_yummy_meal(self, session: SessionState, holder: PartyMemberState) -> None:
        if holder.class_id.strip().lower() != "halfling":
            session.log.append("Only a halfling can use I Can Cook This, and It's Yummy.")
            return
        if session.secret_yummy_meal_active:
            session.log.append("The party is already enjoying the yummy meal bonus this dungeon.")
            return
        if not consume_secret(holder, "yummy_meal"):
            session.log.append(f"{holder.name} no longer has I Can Cook This, and It's Yummy.")
            return
        session.secret_yummy_meal_active = True
        session.log.append(
            f"{holder.name} cooks rare ingredients for the party. Until the dungeon ends, "
            "all heroes gain +1 to Save rolls vs Madness, fear, and disease."
        )

    def _secret_diet_cost(self, member: PartyMemberState) -> int:
        if member.class_id.strip().lower() == "halfling":
            return self.SECRET_DIET_HALFLING_COST_GP
        return self.SECRET_DIET_COST_GP

    def _use_secret_diet(self, session: SessionState, holder: PartyMemberState) -> None:
        if session.mode != "exploration" or not session.camped_outside:
            session.log.append("Secret Diet is used while camped outside before re-entering the adventure.")
            return
        if holder.character_id in session.secret_diet_character_ids:
            session.log.append(f"{holder.name} already has Secret Diet active for this adventure.")
            return
        cost = self._secret_diet_cost(holder)
        if self._outside_party_gold(session) < cost:
            session.log.append(f"Secret Diet requires {cost}gp in party or home-bank funds.")
            return
        if not consume_secret(holder, "secret_diet"):
            session.log.append(f"{holder.name} no longer has Secret Diet.")
            return
        paid, payment_log = self._spend_outside_party_gold(session, cost, label="secret diet provisions")
        if not paid:
            holder.secrets.append("secret_diet")
            session.log.append(f"Secret Diet requires {cost}gp in party or home-bank funds.")
            return
        session.log.extend(payment_log)
        holder.max_life += 1
        holder.current_life += 1
        session.secret_diet_character_ids.append(holder.character_id)
        session.log.append(
            f"{holder.name} uses Secret Diet, spending {cost}gp for +1 Life this adventure "
            f"({holder.current_life}/{holder.max_life})."
        )

    def _learn_spell_with_clues(
        self,
        session: SessionState,
        character_id: str | None,
        spell_id: str | None,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Learn spells from Clues after combat.")
            return
        self._ensure_individual_clues(session)
        if session.clues_found < CLUES_FOR_SECRET_XP:
            session.log.append(
                f"Need {CLUES_FOR_SECRET_XP} Clues to learn a spell (party has {session.clues_found})."
            )
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to learn a spell from Clues.")
            return
        class_id = member.class_id.strip().lower()
        if class_id == "druid":
            self._learn_druid_spell_with_clues(session, member, spell_id)
            return
        if class_id not in {"wizard", "elf"}:
            session.log.append("Only eligible spellcasters may learn expert spells from Clues.")
            return
        if not spell_id:
            session.log.append("Choose a spell to learn from Clues.")
            return
        catalog = self.rules.expert_skills()
        normalized = spell_id.strip().lower()
        eligible_ids = {str(spell.get("id", "")).strip().lower() for spell in eligible_expert_spells(member, catalog)}
        if normalized not in eligible_ids:
            session.log.append(f"{spell_id} is not available for {member.name} to learn from Clues.")
            return
        if not self._spend_clues(session, CLUES_FOR_SECRET_XP, preferred_character_id=member.character_id):
            session.log.append(
                f"Need {CLUES_FOR_SECRET_XP} Clues to learn a spell (party has {session.clues_found})."
            )
            return
        session.log.append(f"The party spends {CLUES_FOR_SECRET_XP} Clues for {member.name}'s spell research.")
        session.log.extend(apply_expert_skill_learn(member, normalized, catalog))

    def _eligible_druid_clue_spells(self, member: PartyMemberState) -> dict[str, str]:
        if member.level < 5 or not member.expert_trained:
            return {}
        known = {normalize_spell_name(spell) for spell in member.spells}
        learned = {entry.strip().lower().split(":", 1)[0] for entry in member.learned_expert_skills}
        rows = self.rules.dungeon_tables().get("druid_spells_table", [])
        options: dict[str, str] = {}
        for row in (rows if isinstance(rows, list) else []):
            spell_name = str(row.get("spell", "")).strip()
            if not spell_name:
                continue
            spell_key = normalize_spell_name(spell_name)
            if spell_key in known or spell_key in learned:
                continue
            options[spell_key] = spell_name
        return options

    def _learn_druid_spell_with_clues(
        self,
        session: SessionState,
        member: PartyMemberState,
        spell_id: str | None,
    ) -> None:
        if member.level < 5:
            session.log.append(f"{member.name} must reach Level 5 before learning druid spells from Clues.")
            return
        if not member.expert_trained:
            session.log.append(f"{member.name} needs Expert training before learning druid spells from Clues.")
            return
        if not spell_id:
            session.log.append("Choose a druid spell to learn from Clues.")
            return
        options = self._eligible_druid_clue_spells(member)
        normalized = normalize_spell_name(spell_id)
        spell_name = options.get(normalized)
        if spell_name is None:
            session.log.append(f"{spell_id} is not available for {member.name} to learn from Clues.")
            return
        if not self._spend_clues(session, CLUES_FOR_SECRET_XP, preferred_character_id=member.character_id):
            session.log.append(
                f"Need {CLUES_FOR_SECRET_XP} Clues to learn a spell (party has {session.clues_found})."
            )
            return
        member.learned_expert_skills.append(normalized)
        member.spells.append(spell_name)
        session.log.append(f"The party spends {CLUES_FOR_SECRET_XP} Clues for {member.name}'s druid spell research.")
        session.log.append(f"{member.name} learns druid spell {spell_name} (added to repertoire).")

    def _combat_context(
        self,
        session: SessionState,
        tile: TileState,
        combat_abilities: dict[str, str] | None = None,
        combat_log: list[str] | None = None,
        guard_targets: dict[str, str] | None = None,
        double_kick_targets: dict[str, list[str]] | None = None,
        protective_incense_targets: dict[str, str] | None = None,
    ) -> CombatContext:
        abilities = combat_abilities or {}
        rage_attackers = {cid for cid, choice in abilities.items() if choice == "rage"}
        for member in session.party:
            if member.current_life > 0 and BERSERKER_MUSHROOM_STATUS in member.statuses:
                rage_attackers.add(member.character_id)
                member.statuses = [status for status in member.statuses if status != BERSERKER_MUSHROOM_STATUS]
                if combat_log is not None:
                    combat_log.append(
                        f"{member.name} flies into a berserker rage from the mushroom (3d6 keep best, double damage on hit)."
                    )
        luck_reroll_attackers = {cid for cid, choice in abilities.items() if choice == "luck_attack"}
        luck_reroll_defenders = {cid for cid, choice in abilities.items() if choice == "luck_defense"}
        panache_attack_bonus = {cid for cid, choice in abilities.items() if choice == "panache_attack"}
        panache_defense_bonus = {cid for cid, choice in abilities.items() if choice == "panache_defense"}
        gnome_gadget_attackers = {cid for cid, choice in abilities.items() if choice == "gnome_gadget"}
        flip_kick_attackers = {cid for cid, choice in abilities.items() if choice == "flip_kick"}
        parrying_character_ids = {cid for cid, choice in abilities.items() if choice == "gladiator_parry"}
        double_kick_attackers = {cid for cid, choice in abilities.items() if choice == "double_kick"}
        deadly_strike_attackers = {cid for cid, choice in abilities.items() if choice == "deadly_strike"}
        dead_shot_attackers = {cid for cid, choice in abilities.items() if choice == "dead_shot"}
        double_attack_attackers = {cid for cid, choice in abilities.items() if choice == "double_attack"}
        double_shot_attackers = {cid for cid, choice in abilities.items() if choice == "double_shot"}
        restore_users = {cid for cid, choice in abilities.items() if choice == "restore"}
        mass_blessing_users = {cid for cid, choice in abilities.items() if choice == "mass_blessing"}
        ward_users = {cid for cid, choice in abilities.items() if choice == "ward_of_protection"}
        restore_targets: dict[str, str] = {}
        ward_targets: dict[str, str] = {}
        guard_map = guard_targets or {}
        for cid in restore_users:
            member = next((item for item in session.party if item.character_id == cid), None)
            if member is None:
                continue
            from .heroic_skill_effects import has_heroic_skill

            if not has_heroic_skill(member, "restore"):
                continue
            ally_id = guard_map.get(cid)
            if ally_id:
                restore_targets[cid] = ally_id
        for cid in ward_users:
            member = next((item for item in session.party if item.character_id == cid), None)
            if member is None:
                continue
            from .heroic_skill_effects import has_heroic_skill, has_legendary_skill

            if not (has_heroic_skill(member, "ward_of_protection") or has_legendary_skill(member, "legendary_ward_of_protection")):
                continue
            ally_id = guard_map.get(cid) or cid
            ward_targets[cid] = ally_id
            if not encounter_spent(session, cid, "ward_of_protection"):
                mark_encounter_spent(session, cid, "ward_of_protection")
        whirlwind_attackers = {cid for cid, choice in abilities.items() if choice == "whirlwind_of_steel"}
        master_strike_attackers = {cid for cid, choice in abilities.items() if choice == "master_strike"}
        aggressive_stance_attackers = {cid for cid, choice in abilities.items() if choice == "aggressive_stance"}
        defensive_stance_attackers = {cid for cid, choice in abilities.items() if choice == "defensive_stance"}
        knife_throw_attackers = {cid for cid, choice in abilities.items() if choice == "knife_throwing"}
        acrobat_knife_throw_attackers = {cid for cid, choice in abilities.items() if choice == "acrobat_knife_throw"}
        illusionist_knife_throw_attackers = {
            cid for cid, choice in abilities.items() if choice == "illusionist_knife_throw"
        }
        flourishing_strike_attackers = {cid for cid, choice in abilities.items() if choice == "flourishing_strike"}
        riposte_attackers = {cid for cid, choice in abilities.items() if choice == "riposte"}
        continual_light_casters = {
            cid
            for cid, choice in abilities.items()
            if choice in {"continual_light", "illusionist_continual_light"}
        }
        protective_incense_users = {cid for cid, choice in abilities.items() if choice == "protective_incense"}
        incense_map = protective_incense_targets or {}
        for cid in protective_incense_users:
            member = next((item for item in session.party if item.character_id == cid), None)
            if member is None or not has_skill(member, "protective_incense"):
                continue
            if encounter_spent(session, cid, "protective_incense"):
                if combat_log is not None:
                    combat_log.append(f"{member.name} has already used Protective Incense this encounter.")
                continue
            session.expert_protective_incense_target = incense_map.get(cid) or cid
            mark_encounter_spent(session, cid, "protective_incense")
        sacrifice_guards: dict[str, str] = {}
        sacrifice_shield_users: set[str] = set()
        for cid, choice in abilities.items():
            if choice == "bulwark_sacrifice":
                member = next((item for item in session.party if item.character_id == cid), None)
                if member is None or not has_skill(member, "sacrifice_defense"):
                    continue
                ally_id = (guard_targets or {}).get(cid)
                if ally_id:
                    sacrifice_guards[cid] = ally_id
            elif choice == "sacrifice_shield":
                member = next((item for item in session.party if item.character_id == cid), None)
                if (
                    member is not None
                    and has_skill(member, "sacrifice_shield")
                    and member_carries_shield(member, session)
                ):
                    sacrifice_shield_users.add(cid)

        def spend_rage(member: PartyMemberState) -> bool:
            return spend_rage_use(session, member)

        def spend_luck(member: PartyMemberState) -> bool:
            return spend_luck_point(session, member)

        def spend_panache(member: PartyMemberState) -> bool:
            return spend_panache_point(session, member)

        def spend_gnome_gadget(member: PartyMemberState) -> bool:
            return spend_gnome_gadgets(session, member, 1)

        def spend_acrobat_trick_point(member: PartyMemberState) -> bool:
            return spend_acrobat_trick(session, member)

        def spend_spell_slot(member: PartyMemberState) -> bool:
            return spend_caster_spell_slot(session, member, label="Illusionary knife throw")

        def on_assassin_strike_used() -> None:
            clear_assassin_mark(session)

        from .terrain import resolve_play_context

        play_ctx = resolve_play_context(tile, session)
        round_party_attack_bonus = self._consume_sleeping_foe_attack_bonus(session, tile)
        foe_penalties = dict(session.foe_level_penalties)
        for foe_id, tier in (session.foe_taunt_active or {}).items():
            foe_penalties[foe_id] = foe_penalties.get(foe_id, 0) + int(tier)

        combat_context = CombatContext(
            tile_type=tile.tile_type,
            wandering_ambush=tile.wandering_ambush and session.combat_round == 0,
            combat_round=session.combat_round + 1,
            outdoors=play_ctx.outdoors,
            alter_weather_active=play_ctx.weather_active,
            cursed_character_id=session.cursed_character_id,
            wielded_melee=session.wielded_melee_weapons,
            illusionary_fog_active=session.illusionary_fog_active,
            subdual_penalty_ignored=session.subdual_penalty_ignored,
            suppress_morale=session.reaction_key == "fight_to_death",
            body_carrier_id=session.body_carrier_id,
            lookup_monster_template=self._monster_template_for_enemy,
            on_rattleblade_summon=lambda enemy: self._try_rattleblade_summon(
                enemy,
                session=session,
                tile=tile,
                show_rolls=True,
            ),
            rage_attackers=rage_attackers,
            luck_reroll_attackers=luck_reroll_attackers,
            luck_reroll_defenders=luck_reroll_defenders,
            panache_attack_bonus=panache_attack_bonus,
            panache_defense_bonus=panache_defense_bonus,
            gnome_gadget_attackers=gnome_gadget_attackers,
            flip_kick_attackers=flip_kick_attackers,
            parrying_character_ids=parrying_character_ids,
            double_kick_attackers=double_kick_attackers,
            double_kick_targets=double_kick_targets or {},
            sacrifice_guards=sacrifice_guards,
            sacrifice_used=set(),
            evading_character_ids=set(session.evasion_character_ids),
            gladiator_counter_pending=session.gladiator_counter_pending,
            gladiator_counter_used=set(session.gladiator_counter_used),
            foe_level_penalties=foe_penalties,
            flourishing_strike_attackers=flourishing_strike_attackers,
            riposte_attackers=riposte_attackers,
            assassin_striker_id=session.assassin_hidden_id,
            assassin_mark_enemy_id=session.assassin_mark_enemy_id,
            prisoner_chain_skip_attack=session.prisoner_chain_skip_attack,
            acrobat_skip_attack=session.acrobat_skip_attack,
            on_foe_kill=make_kill_callback(session, combat_log),
            on_assassin_strike_used=on_assassin_strike_used,
            spend_rage=spend_rage,
            spend_luck=spend_luck,
            spend_panache=spend_panache,
            spend_gnome_gadget=spend_gnome_gadget,
            session=session,
            deadly_strike_attackers=deadly_strike_attackers,
            dead_shot_attackers=dead_shot_attackers,
            divine_smite_attackers={cid for cid, choice in abilities.items() if choice == "divine_smite"},
            sacrifice_shield_users=sacrifice_shield_users,
            sacrifice_shield_used=set(session.sacrifice_shield_used),
            double_attack_attackers=double_attack_attackers,
            double_shot_attackers=double_shot_attackers,
            restore_users=restore_users,
            restore_targets=restore_targets,
            ward_targets=ward_targets,
            mass_blessing_users=mass_blessing_users,
            whirlwind_attackers=whirlwind_attackers,
            master_strike_attackers=master_strike_attackers,
            aggressive_stance_attackers=aggressive_stance_attackers,
            defensive_stance_attackers=defensive_stance_attackers,
            knife_throw_attackers=knife_throw_attackers,
            acrobat_knife_throw_attackers=acrobat_knife_throw_attackers,
            illusionist_knife_throw_attackers=illusionist_knife_throw_attackers,
            continual_light_casters=continual_light_casters,
            spend_acrobat_trick=spend_acrobat_trick_point,
            spend_caster_spell_slot=spend_spell_slot,
            round_party_attack_bonus=round_party_attack_bonus,
            cavern_feature_key=tile.cavern_feature_key,
        )
        self._active_combat_context = combat_context
        return combat_context

    def _try_rattleblade_summon(
        self,
        enemy: EnemyState,
        *,
        session: SessionState,
        tile: TileState,
        show_rolls: bool,
    ) -> list[str]:
        from .monster_combat_hooks import try_rattleblade_summon
        from .monster_template_effects import party_hcl

        return try_rattleblade_summon(
            enemy,
            engine=self,
            session=session,
            tile=tile,
            hcl=party_hcl(session.party),
            show_rolls=show_rolls,
        )

    def _consume_sleeping_foe_attack_bonus(self, session: SessionState, tile: TileState) -> int:
        fighters = combat_party(session, tile.id)
        bonus = session.reaction_sleep_attack_bonus or 2
        prefix = "Sleeping foe +"
        affected = [
            member
            for member in fighters
            if member.current_life > 0 and any(entry.startswith(prefix) for entry in member.statuses)
        ]
        if not affected:
            return 0
        for member in affected:
            member.statuses = [entry for entry in member.statuses if not entry.startswith(prefix)]
        session.reaction_sleep_attack_bonus = 0
        session.log.append(
            f"Effect: Sleeping foe reaction grants +{bonus} Attack for this first combat round."
        )
        return bonus

    def _apply_combat_result(
        self,
        session: SessionState,
        tile: TileState,
        result,
        *,
        show_rolls: bool,
        fled: bool = False,
        active_enemy_ids: set[str] | None = None,
        standing_before: set[str] | None = None,
    ) -> None:
        if standing_before is None:
            standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
        if active_enemy_ids is None:
            active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        session.party = self._merge_party_outcome(session.party, result.party)
        tile.enemies = result.enemies
        session.log.extend(result.log)
        if getattr(result, "combat_paused", False):
            return
        known_defeated_ids = {enemy.id for enemy in tile.defeated_enemies}
        for enemy in result.enemies:
            if enemy.id in active_enemy_ids and enemy.life <= 0 and enemy.id not in known_defeated_ids:
                tile.defeated_enemies.append(enemy.model_copy(deep=True))
                known_defeated_ids.add(enemy.id)
                if is_fd_ruleset(session):
                    from .forsaken_depths_secret_passage import note_fd_secret_passage_weird_defeated

                    note_fd_secret_passage_weird_defeated(session, enemy, show_rolls=show_rolls)
        fallen_now = [
            pc.character_id
            for pc in session.party
            if pc.character_id in standing_before and pc.current_life <= 0
        ]
        if session.capture_mode:
            fallen_now = self._resolve_captures(session, tile, fallen_now)
        if fallen_now:
            from .hirelings import check_hireling_morale_after_casualty

            session.log.extend(
                check_hireling_morale_after_casualty(
                    session,
                    reason="a party casualty",
                    show_rolls=show_rolls,
                )
            )
        for character_id in fallen_now:
            if character_id not in tile.fallen_character_ids:
                tile.fallen_character_ids.append(character_id)
        apply_fd_tears_death_madness_spread(session, fallen_now, show_rolls=show_rolls)
        if session.summoned_beast_owner_id and session.summoned_beast_owner_id in fallen_now:
            session.summoned_beast_life = 0
            session.summoned_beast_owner_id = None
            session.log.append("The summoned beast fades as its master falls.")
        if session.druid_companion_owner_id and session.druid_companion_owner_id in fallen_now:
            session.druid_companion_life = 0
            session.druid_companion_owner_id = None
            session.druid_companion_kind = None
            session.log.append("The animal companion flees as its druid falls.")
        if session.body_carrier_id and session.body_carrier_id in fallen_now:
            if session.carried_body_id and session.carried_body_id not in tile.fallen_character_ids:
                tile.fallen_character_ids.append(session.carried_body_id)
            session.log.append("The carrier falls; the fallen comrade's body is dropped here.")
            session.body_carrier_id = None
            session.carried_body_id = None

        session.combat_round += 1
        session.spell_used_character_ids = []
        session.combat_bodyguard_pause = None
        if session.combat_round == 1:
            session.party_surprised = False
            session.reaction_pending = False
        if session.combat_round > 1:
            tile.wandering_ambush = False
            session.reaction_pending = False

        if not result.combat_over:
            session.foe_taunt_active = {}
            return

        from .hirelings import consume_bladesmith_buff

        consume_bladesmith_buff(session)

        from .monster_combat_modifiers import apply_end_of_combat_poison

        apply_end_of_combat_poison(
            session,
            session.party,
            session.log,
            show_rolls=show_rolls,
        )
        from .abyss_afflictions import resolve_lycanthropy_exposures

        session.log.extend(resolve_lycanthropy_exposures(session, tile, show_rolls=show_rolls))

        from .swashbuckler_traits import apply_lucky_hat_blocked_damage, clear_blade_dance_on_combat_end

        if session.pending_defense_reroll_blocked_damage:
            apply_lucky_hat_blocked_damage(session, session.log)
        session.pending_defense_reroll = None
        session.log.extend(clear_blade_dance_on_combat_end(session))
        session.foe_taunt_active = {}
        session.foe_taunt_pending = {}
        session.fd_illusionary_distraction_active = False
        if session.courtship_demesne_active:
            from .courtship_combat import clear_courtship_combat_statuses

            session.log.extend(clear_courtship_combat_statuses(session, session.party))

        self._clear_combat_statuses(session)
        session.capture_mode = False
        session.combat_round = 0
        tile.wandering_ambush = False

        if not any(pc.current_life > 0 for pc in session.party):
            session.mode = "complete"
            session.log.append("The party has fallen.")
            return

        if fled:
            from .abyss_campaign import queue_vampire_sire

            for enemy in tile.enemies:
                if enemy.id in active_enemy_ids and enemy.life > 0:
                    queued = queue_vampire_sire(session, enemy)
                    if queued:
                        session.log.extend(queued)
                        break
            session.mode = "exploration"
            session.log.append("Combat ends in retreat.")
            self._clear_combat_statuses(session)
            if tile.hidden_treasure_alarm_pending and any(enemy.life > 0 for enemy in tile.enemies):
                session.log.append(
                    f"The hidden treasure ({self._treasure_value_label(tile)}) is still here, "
                    "but wandering monsters must be defeated before you can claim it."
                )
            return

        tile.enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        tile.resolved = True
        session.mode = "exploration"
        session.log.append("Combat ends.")
        if any("former_party_member" in {tag.lower() for tag in enemy.tags} for enemy in tile.enemies):
            session.log.append("A transformed ally is now an active foe.")
            self._announce_encounter(session, tile, show_rolls=show_rolls)
            return
        if result.morale_failed:
            self._award_treasure(session, tile, show_rolls=show_rolls)
        elif not tile.enemies:
            self._award_treasure(session, tile, show_rolls=show_rolls)
        defeated_this_fight = [
            enemy.model_copy(deep=True)
            for enemy in result.enemies
            if enemy.id in active_enemy_ids and enemy.life <= 0
        ]
        if not fled and defeated_this_fight:
            from .abyss_campaign import (
                clear_vampire_sire_if_defeated,
                on_combat_defeated,
                on_final_boss_defeated,
            )

            session.log.extend(clear_vampire_sire_if_defeated(session, defeated_this_fight))
            session.log.extend(on_combat_defeated(session, defeated_this_fight))
            session.log.extend(on_final_boss_defeated(self, session, defeated_this_fight))
            for enemy in defeated_this_fight:
                if enemy.category in {"weird", "boss"}:
                    session.major_foes_defeated_this_adventure += 1
            self._award_encounter_xp(session, defeated_this_fight, show_rolls=show_rolls)
            self._update_quest_on_combat_end(session, defeated_this_fight, show_rolls=show_rolls)
            if session.courtship_demesne_active:
                from .courtship_demesne import update_courtship_on_combat_end

                update_courtship_on_combat_end(
                    self, session, defeated_this_fight, show_rolls=show_rolls
                )
            from .milestones import record_defeated_foes

            session.log.extend(record_defeated_foes(session.party, defeated_this_fight))
            session.log.extend(
                grant_spore_doses_after_combat(session, session.party, defeated_this_fight)
            )
            from .monster_combat_hooks import defeated_has_free_slaves_effect

            if defeated_has_free_slaves_effect(defeated_this_fight):
                session.pending_free_slaves_tile_id = tile.id
                session.log.append(
                    "You may free the Fiendish Chaos Lord's captured slaves for 1 Clue "
                    "(triggers a Wandering Monsters roll). Choose Free Slaves or Decline."
                )
        if session.firearm_fired_this_encounter:
            session.next_wandering_roll_bonus += 1
            session.log.append("Firearm use may attract attention (+1 on the next Wandering Monsters roll).")
            session.firearm_fired_this_encounter = False
        if not fled and session.capture_hideout_tile_id and tile.id == session.capture_hideout_tile_id:
            self._rescue_captives(session, tile, show_rolls=show_rolls)
        self._announce_hidden_treasure_claimable(session, tile)
        if not fled:
            self._log_room_recap_after_combat(session, tile)

    def _merge_party_outcome(
        self,
        current_party: list[PartyMemberState],
        outcome_party: list[PartyMemberState],
    ) -> list[PartyMemberState]:
        outcome_by_id = {member.character_id: member for member in outcome_party}
        merged: list[PartyMemberState] = []
        for member in current_party:
            merged.append(outcome_by_id.pop(member.character_id, member))
        merged.extend(outcome_by_id.values())
        return sorted(merged, key=lambda member: member.marching_order)

    def _resolve_foe_flee_strike(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if not any(enemy.life > 0 for enemy in tile.enemies):
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        fighters = combat_party(session, tile.id)
        standing_before = {pc.character_id for pc in fighters if pc.current_life > 0}
        session.foe_flee_strike_pending = False
        result = resolve_flee_strike(
            fighters,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            context=self._combat_context(session, tile),
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )

    def _resume_bodyguard_paused_combat(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "combat" or session.combat_bodyguard_pause is None:
            return
        if session.pending_bodyguard_intercept is not None:
            return
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.combat_bodyguard_pause = None
            return
        pause = session.combat_bodyguard_pause
        initial_minor_count = tile.initial_enemy_count or len(tile.enemies)
        known_defeated_ids = {enemy.id for enemy in tile.defeated_enemies}
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.id not in known_defeated_ids}
        party_here = combat_party(session, tile.id)
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        missile_used = set(session.missile_used_character_ids)
        combat_context = self._combat_context(session, tile)
        session.log.append("Bodyguard choice resolved; continuing the same paused combat round.")
        result = resolve_combat_round(
            party_here,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            initial_minor_count=initial_minor_count,
            context=combat_context,
            party_surprised=False,
            party_attacked_immediately=False,
            foes_strike_first=False,
            encounter_round=session.combat_round,
            missile_used=missile_used,
            resume_after_bodyguard=pause,
        )
        session.gladiator_counter_used = sorted(combat_context.gladiator_counter_used)
        session.evasion_character_ids = []
        if any(enemy.life > 0 for enemy in tile.enemies):
            from .hirelings import apply_hireling_combat_round

            hireling_log = apply_hireling_combat_round(session, tile.enemies, show_rolls=show_rolls)
            if hireling_log:
                result.log.extend(hireling_log)
            if not any(enemy.life > 0 for enemy in tile.enemies):
                result.combat_over = True
        round_summary = summarize_combat_log(
            result.log,
            party_names=[member.name for member in result.party],
            enemy_names=[enemy.name for enemy in result.enemies],
        )
        if round_summary:
            result.log.append(f"Round summary: {round_summary}")
        if result.missile_used is not None:
            session.missile_used_character_ids = sorted(result.missile_used)
        self._foes_strike_summoned_beast(session, tile, show_rolls=show_rolls)
        self._foes_strike_druid_companion(session, tile, show_rolls=show_rolls)
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )

    def _combat_round(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        subdual: bool = False,
        attack_targets: dict[str, str] | None = None,
        attack_secondary_targets: dict[str, str] | None = None,
        double_kick_targets: dict[str, list[str]] | None = None,
        protective_incense_targets: dict[str, str] | None = None,
        combat_abilities: dict[str, str] | None = None,
        guard_targets: dict[str, str] | None = None,
    ) -> None:
        if session.mode != "combat":
            session.log.append("There are no active enemies here.")
            return
        if session.pending_bodyguard_intercept is not None:
            session.log.append("Choose whether the bodyguard intercepts before resolving the combat round.")
            return
        if not self._commit_immediate_attack(session):
            return
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("There are no active enemies here.")
            return
        initial_minor_count = tile.initial_enemy_count or len(tile.enemies)
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        party_here = combat_party(session, tile.id)
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}

        if session.summoned_beast_life > 0:
            owner = next((m for m in session.party if m.character_id == session.summoned_beast_owner_id), None)
            if owner and owner.current_life > 0:
                target = next((enemy for enemy in tile.enemies if enemy.life > 0), None)
                if target:
                    target.life = max(0, target.life - 1)
                    session.log.append(
                        f"The summoned beast claws {target.name} for 1 damage "
                        f"({session.summoned_beast_life} Life remaining)."
                    )
                    if target.life <= 0:
                        session.log.append(f"{target.name} is defeated.")
            else:
                session.summoned_beast_life = 0
                session.summoned_beast_owner_id = None
                session.log.append("The summoned beast fades as its master falls.")

        if session.druid_companion_life > 0:
            owner = next(
                (m for m in session.party if m.character_id == session.druid_companion_owner_id),
                None,
            )
            if owner and owner.current_life > 0:
                target = next((enemy for enemy in tile.enemies if enemy.life > 0), None)
                if target:
                    target.life = max(0, target.life - 1)
                    session.log.extend(companion_attack_log(session, target.name))
                    if target.life <= 0:
                        session.log.append(f"{target.name} is defeated.")
            else:
                session.druid_companion_life = 0
                session.druid_companion_owner_id = None
                session.druid_companion_kind = None
                session.log.append("The animal companion leaves as its druid falls.")

        if session.kukla_doll_active:
            target = next((enemy for enemy in tile.enemies if enemy.life > 0), None)
            for kukla_id in list(session.kukla_doll_active):
                kukla = next((m for m in session.party if m.character_id == kukla_id), None)
                if kukla is None or kukla.current_life <= 0:
                    continue
                if target is None:
                    break
                session.log.extend(
                    kukla_doll_round_attacks(session, kukla, target, show_rolls=show_rolls)
                )
                if target.life <= 0:
                    session.log.append(f"{target.name} is defeated.")
                    target = next((enemy for enemy in tile.enemies if enemy.life > 0), None)

        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("Combat ends.")
            self._apply_combat_result(
                session,
                tile,
                CombatRound(party=session.party, enemies=tile.enemies, log=[], combat_over=True),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )
            return

        if session.foe_flee_strike_pending:
            self._resolve_foe_flee_strike(
                session,
                tile,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return

        foes_strike_first = session.foes_strike_first and session.combat_round == 0
        if foes_strike_first:
            session.foes_strike_first = False
        if session.foe_taunt_pending:
            active = dict(session.foe_taunt_active or {})
            for foe_id, tier in session.foe_taunt_pending.items():
                active[foe_id] = max(int(active.get(foe_id, 0)), int(tier))
            session.foe_taunt_active = active
            session.foe_taunt_pending = {}
        missile_used = set(session.missile_used_character_ids)
        ability_log: list[str] = []
        from .abyss_tactics import (
            apply_abyss_multiple_boss_defaults,
            coerce_abyss_attack_targets,
        )

        attack_targets, multiple_boss_log = apply_abyss_multiple_boss_defaults(
            party_here,
            tile.enemies,
            tile_type=tile.tile_type,
            attack_targets=attack_targets,
        )
        attack_targets, leader_lock_log = coerce_abyss_attack_targets(
            party_here,
            tile.enemies,
            tile_type=tile.tile_type,
            attack_targets=attack_targets,
        )
        attack_secondary_targets, secondary_leader_lock_log = coerce_abyss_attack_targets(
            party_here,
            tile.enemies,
            tile_type=tile.tile_type,
            attack_targets=attack_secondary_targets,
            label="second target",
        )
        ability_log.extend(multiple_boss_log)
        ability_log.extend(leader_lock_log)
        ability_log.extend(secondary_leader_lock_log)
        combat_context = self._combat_context(
            session,
            tile,
            combat_abilities,
            ability_log,
            guard_targets=guard_targets,
            double_kick_targets=double_kick_targets,
            protective_incense_targets=protective_incense_targets,
        )
        if mixed_encounter(tile.enemies):
            result = resolve_simultaneous_combat_round(
                party_here,
                tile.enemies,
                show_rolls=show_rolls,
                explain_math=explain_math,
                initial_minor_count=initial_minor_count,
                context=combat_context,
                party_surprised=session.party_surprised and session.combat_round == 0,
                party_attacked_immediately=session.party_attacked_immediately and session.combat_round == 0,
                foes_strike_first=foes_strike_first,
                subdual=subdual,
                encounter_round=session.combat_round,
                missile_used=missile_used,
                attack_targets=attack_targets,
                attack_secondary_targets=attack_secondary_targets,
            )
        else:
            result = resolve_combat_round(
                party_here,
                tile.enemies,
                show_rolls=show_rolls,
                explain_math=explain_math,
                initial_minor_count=initial_minor_count,
                context=combat_context,
                party_surprised=session.party_surprised and session.combat_round == 0,
                party_attacked_immediately=session.party_attacked_immediately and session.combat_round == 0,
                foes_strike_first=foes_strike_first,
                subdual=subdual,
                encounter_round=session.combat_round,
                missile_used=missile_used,
                attack_targets=attack_targets,
                attack_secondary_targets=attack_secondary_targets,
            )
        session.gladiator_counter_used = sorted(combat_context.gladiator_counter_used)
        session.evasion_character_ids = []
        if ability_log:
            result.log = ability_log + result.log
        if any(enemy.life > 0 for enemy in tile.enemies):
            from .hirelings import apply_hireling_combat_round

            hireling_log = apply_hireling_combat_round(session, tile.enemies, show_rolls=show_rolls)
            if hireling_log:
                result.log.extend(hireling_log)
            if not any(enemy.life > 0 for enemy in tile.enemies):
                result.combat_over = True
        round_summary = summarize_combat_log(
            result.log,
            party_names=[member.name for member in result.party],
            enemy_names=[enemy.name for enemy in result.enemies],
        )
        if round_summary:
            result.log.append(f"Round summary: {round_summary}")
        if result.missile_used is not None:
            session.missile_used_character_ids = sorted(result.missile_used)
        if combat_context.pending_skeleton_spawns > 0:
            from .monster_combat_hooks import spawn_skeleton_reinforcements

            spawn_log = spawn_skeleton_reinforcements(
                self,
                session,
                tile,
                result.enemies,
                combat_context.pending_skeleton_spawns,
                show_rolls=show_rolls,
            )
            combat_context.pending_skeleton_spawns = 0
            if spawn_log:
                result.log.extend(spawn_log)
        self._foes_strike_summoned_beast(session, tile, show_rolls=show_rolls)
        self._foes_strike_druid_companion(session, tile, show_rolls=show_rolls)
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )
        self._tick_teleport_enemy_returns(session, reason="combat turn")
        from .heroic_skill_effects import rotate_aggressive_stance_penalty

        aggressive = {cid for cid, choice in (combat_abilities or {}).items() if choice == "aggressive_stance"}
        rotate_aggressive_stance_penalty(session, aggressive)

    def _tick_teleport_enemy_returns(self, session: SessionState, *, reason: str) -> None:
        if not session.fd_teleport_enemy_returns:
            return
        from .fd_teleport_enemy import tick_teleport_enemy_returns

        reaction_tables = self.rules.monsters().get("reaction_tables", {})
        if not isinstance(reaction_tables, dict):
            reaction_tables = {}
        tick_teleport_enemy_returns(
            session,
            reason=reason,
            reaction_tables=reaction_tables,
            roll_reaction=self.table_roller.roll_reaction,
        )

    def _flee(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
        use_luck_flee: bool = False,
        use_daring_escape: bool = False,
        character_id: str | None = None,
        target_character_id: str | None = None,
        foe_id: str | None = None,
    ) -> None:
        if session.mode != "combat":
            session.log.append("There is no fight to flee.")
            return
        tile = self._current_tile(session)
        party_here = combat_party(session, tile.id)
        from .monster_combat_hooks import member_cannot_flee

        if any(member_cannot_flee(member) for member in party_here if member.current_life > 0):
            session.log.append("Pinned heroes cannot flee until the lurking mantlebeast is slain.")
            return
        from .courtship_combat import COURTSHIP_CANNOT_FLEE

        if any(
            COURTSHIP_CANNOT_FLEE in member.statuses
            for member in party_here
            if member.current_life > 0
        ):
            session.log.append(
                "Maypole Dancers mesmerize the party — cannot flee this encounter (TCOTFD)."
            )
            return
        if session.courtship_vault_combat_no_flee:
            session.log.append(
                "The queen's court fights to the death — the party cannot flee (BoS entry 3, TCOTFD)."
            )
            return
        if not self._commit_immediate_attack(session):
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        skip_parting_attacks = session.skip_parting_flee or session.gnome_smokescreen_ready
        puffball_flee = session.puffball_flee
        if puffball_flee:
            skip_parting_attacks = False
        if use_daring_escape:
            swash = next((member for member in session.party if member.character_id == character_id), None)
            ally = next(
                (member for member in session.party if member.character_id == target_character_id),
                None,
            )
            foe = next((enemy for enemy in tile.enemies if enemy.id == foe_id and enemy.life > 0), None)
            if swash is None or swash.class_id.lower() != "swashbuckler":
                session.log.append("Choose a swashbuckler to use Daring Escape.")
            elif ally is None or ally.character_id == swash.character_id:
                session.log.append("Choose an ally to grant +1 on their next attack.")
            elif foe is None:
                session.log.append("Choose a foe for the ally's attack bonus.")
            else:
                from .swashbuckler_traits import apply_daring_escape, daring_escape_available

                if not daring_escape_available(session, swash):
                    session.log.append(f"{swash.name} has already used Daring Escape this adventure.")
                else:
                    session.log.extend(apply_daring_escape(session, swash, ally=ally, foe=foe))
                    skip_parting_attacks = True
        if use_luck_flee:
            luck_hero = next((member for member in session.party if member.character_id == character_id), None)
            if luck_hero is None or luck_hero.current_life <= 0:
                session.log.append("Choose a living hero with Luck to spend for a clean escape.")
            elif not spend_luck_point(session, luck_hero):
                session.log.append(f"{luck_hero.name} has no Luck points remaining.")
            else:
                skip_parting_attacks = True
                session.log.append(
                    f"{luck_hero.name} spends 1 Luck; the party flees without parting blows."
                )
        elif skip_parting_attacks:
            session.log.append("The party escapes without parting blows (smokescreen or Serpent Twist).")
        blocked, block_reason = flee_blocked_by_web(tile.enemies, torch_spent=session.torch_spent_this_combat)
        if blocked:
            session.log.append(block_reason)
            return
        result = resolve_flee(
            party_here,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            context=self._combat_context(session, tile),
            skip_parting_attacks=skip_parting_attacks,
            parting_foe_filter=puffball_parting_foe if puffball_flee else None,
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            fled=result.fled,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )
        if result.fled:
            session.skip_parting_flee = False
            session.puffball_flee = False
            session.gnome_smokescreen_ready = False
            if show_rolls:
                roll = roll_d6()
                session.log.append(f"Flee wandering check: d6 = {roll}.")
                if roll == 1:
                    session.log.append("Something pursues the fleeing party (Wandering Monsters on 1).")

    def _withdraw(
        self,
        session: SessionState,
        exit_id: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "combat":
            session.log.append("There is no fight to withdraw from.")
            return
        if not self._commit_immediate_attack(session):
            return
        tile = self._current_tile(session)
        from .monster_combat_modifiers import withdraw_blocked_by_webs

        if withdraw_blocked_by_webs(tile.enemies, webs_burned=tile.spider_webs_burned):
            session.log.append(
                "Fiendish spider webs block withdrawal. Cast Fireball to burn the webs, then withdraw."
            )
            return
        exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door" or not exit_state.destination_tile_id:
            session.log.append("Withdraw requires an open door back to a visited tile.")
            return
        destination = self._tile_by_id(session, exit_state.destination_tile_id)
        if destination is None:
            session.log.append("That door does not lead anywhere known.")
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        party_here = combat_party(session, tile.id)
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        result = resolve_withdraw(
            party_here,
            tile.enemies,
            show_rolls=show_rolls,
            explain_math=explain_math,
            context=self._combat_context(session, tile),
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            fled=result.fled,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )
        if not result.fled:
            return
        exit_state.door_open = False
        reciprocal = next(
            (item for item in destination.exits if item.destination_tile_id == tile.id),
            None,
        )
        if reciprocal is not None:
            reciprocal.door_open = False
            reciprocal.status = "open"
        session.map_state.current_tile_id = destination.id
        session.current_tile_entry_exit_id = reciprocal.id if reciprocal else None
        self._sync_session_environment_from_tile(session, destination)
        session.log.append(f"The party withdraws to {destination.title}. The foes remain behind.")
        if show_rolls:
            roll = roll_d6()
            session.log.append(f"Withdraw wandering check: d6 = {roll}.")
            if roll == 1:
                self._spawn_wandering_monsters(session, destination, show_rolls=show_rolls)

    def _set_marching_order(
        self,
        session: SessionState,
        character_id: str | None,
        position: int | None,
    ) -> None:
        from .hirelings import set_party_member_marching_order

        session.log.extend(set_party_member_marching_order(session, character_id, position))

    def _set_default_weapon(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None,
        *,
        weapon_kind: str | None,
    ) -> None:
        if session.mode == "combat":
            session.log.append(
                "Use Swap Weapon during combat (costs 1 turn). To change sheet defaults, wait until exploration."
            )
            return
        if session.mode != "exploration":
            session.log.append("Set default weapons during exploration.")
            return
        if not character_id or not item_name:
            session.log.append("Choose a hero and weapon to set as default.")
            return
        if weapon_kind not in {"melee", "missile"}:
            session.log.append("Choose whether this is a melee or missile default weapon.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero.")
            return
        if item_name not in member.inventory:
            session.log.append(f"{member.name} does not carry {item_name}.")
            return
        ok, note = set_weapon_default(member, item_name=item_name, weapon_kind=weapon_kind)
        if not ok:
            session.log.append(note)
            return
        tile = self._current_tile(session)
        if tile.content_key == "armory" or any("armory" in obj.lower() for obj in tile.objects):
            note += " (Armory: changed within carried gear.)"
        session.log.append(note)

    def _ready_spear_shield(self, session: SessionState, character_id: str | None) -> None:
        if session.mode != "combat":
            session.log.append("Ready a spear-carried shield during combat only.")
            return
        if not character_id:
            session.log.append("Choose a hero to ready a shield.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to ready a shield.")
            return
        from .hirelings import can_ready_spear_shield, spear_carrier_for_owner

        if not can_ready_spear_shield(session, member.character_id):
            session.log.append(f"{member.name} cannot ready a shield from the spear carrier now.")
            return
        carrier = spear_carrier_for_owner(session, member.character_id)
        ready = list(session.spear_shield_readied or [])
        ready.append(member.character_id)
        session.spear_shield_readied = ready
        session.log.append(
            f"{member.name} readies {carrier.carried_gear} from {carrier.name} without forfeiting an attack."
        )

    def _swap_weapon(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Swap weapons during combat only.")
            return
        if not character_id or not item_name:
            session.log.append("Choose a hero and melee weapon to draw.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to swap weapons.")
            return
        from .hirelings import spear_carrier_for_owner

        spear_carrier = spear_carrier_for_owner(session, member.character_id)
        spear_swap = spear_carrier is not None and spear_carrier.carried_gear == item_name
        if not spear_swap and item_name not in member.inventory:
            session.log.append(f"{member.name} does not carry {item_name}.")
            return
        profile = _parse_weapon_item(item_name)
        if profile is None or profile.kind != "melee":
            session.log.append(f"{item_name} is not a melee weapon.")
            return
        current = session.wielded_melee_weapons.get(member.character_id) or member.default_melee_weapon
        if current == item_name:
            session.log.append(f"{member.name} already wields {item_name}.")
            return
        if spear_swap:
            session.wielded_melee_weapons[member.character_id] = item_name
            session.log.append(
                f"{member.name} takes {item_name} from {spear_carrier.name} without forfeiting an attack."
            )
            return
        if not self._commit_immediate_attack(session):
            return
        session.wielded_melee_weapons[member.character_id] = item_name
        session.log.append(f"{member.name} spends the turn drawing {item_name}.")
        tile = self._current_tile(session)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("There are no active enemies here.")
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        party_here = combat_party(session, tile.id)
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        result = resolve_combat_round(
            party_here,
            tile.enemies,
            show_rolls=show_rolls,
            context=self._combat_context(session, tile),
            encounter_round=session.combat_round,
            missile_used=set(session.missile_used_character_ids),
            foe_phase_only=True,
        )
        self._apply_combat_result(
            session,
            tile,
            result,
            show_rolls=show_rolls,
            active_enemy_ids=active_enemy_ids,
            standing_before=standing_before,
        )

    def _transfer_item(
        self,
        session: SessionState,
        from_character_id: str | None,
        to_character_id: str | None,
        item_name: str | None,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Exchange gear during exploration, not in combat.")
            return
        if not from_character_id or not to_character_id:
            session.log.append("Choose who gives and who receives the item.")
            return
        source = next((member for member in session.party if member.character_id == from_character_id), None)
        target = next((member for member in session.party if member.character_id == to_character_id), None)
        if source and is_paranoid(source):
            session.log.append(f"{source.name} is too paranoid to exchange equipment.")
            return
        if target and is_paranoid(target):
            session.log.append(f"{target.name} is too paranoid to exchange equipment.")
            return
        _ok, message = transfer_inventory_item(
            session.party,
            from_character_id=from_character_id,
            to_character_id=to_character_id,
            item_name=item_name or "",
        )
        session.log.append(message)
        session.log.extend(enforce_single_pole_carrier(session.party, session=session))

    def _transfer_gold(
        self,
        session: SessionState,
        from_character_id: str | None,
        to_character_id: str | None,
        amount: int | None,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Exchange gold during exploration, not in combat.")
            return
        if not from_character_id or not to_character_id:
            session.log.append("Choose who gives and who receives the gold.")
            return
        _ok, message = transfer_gold(
            session.party,
            from_character_id=from_character_id,
            to_character_id=to_character_id,
            amount=amount or 0,
        )
        session.log.append(message)

    def _bank_access_member(
        self,
        session: SessionState,
        character_id: str | None,
    ) -> PartyMemberState | None:
        if session.mode != "exploration" or not session.camped_outside:
            session.log.append("The home bank is available only while camped outside the dungeon.")
            return None
        if not character_id:
            session.log.append("Choose a hero for the bank transaction.")
            return None
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("Choose a hero in the active party.")
            return None
        if member.current_life <= 0:
            session.log.append(f"{member.name} cannot use the bank while fallen.")
            return None
        return member

    def _deposit_bank_gold(
        self,
        session: SessionState,
        character_id: str | None,
        amount: int | None,
    ) -> None:
        member = self._bank_access_member(session, character_id)
        if member is None:
            return
        deposit = min(member.gold, amount or member.gold)
        if deposit <= 0:
            session.log.append(f"{member.name} has no carried gold to deposit.")
            return
        member.gold -= deposit
        member.bank_gold += deposit
        session.log.append(f"{member.name} deposits {deposit}gp in the home bank.")

    def _withdraw_bank_gold(
        self,
        session: SessionState,
        character_id: str | None,
        amount: int | None,
    ) -> None:
        member = self._bank_access_member(session, character_id)
        if member is None:
            return
        free_capacity = max(0, MAX_CARRIED_GOLD - member.gold)
        withdraw = min(member.bank_gold, amount or free_capacity, free_capacity)
        if withdraw <= 0:
            if member.bank_gold <= 0:
                session.log.append(f"{member.name} has no banked gold to withdraw.")
            else:
                session.log.append(f"{member.name} cannot carry more than {MAX_CARRIED_GOLD}gp in the dungeon.")
            return
        member.bank_gold -= withdraw
        member.gold += withdraw
        session.log.append(f"{member.name} withdraws {withdraw}gp from the home bank.")

    def _deposit_party_bank_gold(self, session: SessionState) -> None:
        if session.mode != "exploration" or not session.camped_outside:
            session.log.append("The home bank is available only while camped outside the dungeon.")
            return
        deposits: list[str] = []
        for member in sorted(session.party, key=lambda item: item.marching_order):
            if member.current_life <= 0 or member.gold <= 0:
                continue
            deposit = member.gold
            member.gold = 0
            member.bank_gold += deposit
            deposits.append(f"{member.name} {deposit}gp")
        if not deposits:
            session.log.append("No living party member has carried gold to deposit.")
            return
        session.log.append(f"Party deposits carried gold in the home bank: {', '.join(deposits)}.")

    def _grant_clue(
        self,
        session: SessionState,
        tile: TileState,
        *,
        character_id: str | None = None,
        add_object: bool = True,
        source: str = "finds",
    ) -> PartyMemberState | None:
        if add_object and "Clue" not in tile.objects:
            tile.objects.append("Clue")
        holder = self._default_clue_holder(session, character_id)
        if holder is None:
            session.log.append("No hero is available to hold the Clue.")
            return None
        holder.clues += 1
        self._sync_clue_total(session)
        if source == "buys":
            session.log.append(
                f"{holder.name} buys 1 Clue ({holder.clues} carried; {session.clues_found} party total)."
            )
        else:
            session.log.append(
                f"{holder.name} finds 1 Clue ({holder.clues} carried; {session.clues_found} party total)."
            )
        if session.clues_found >= CLUES_FOR_SECRET_XP:
            session.log.append(
                f"{CLUES_FOR_SECRET_XP} Clues are available. Spend them deliberately on a Secret, "
                "an eligible spell, or a special clue use."
            )
        return holder

    def _grant_xp_credit(self, session: SessionState, amount: int, reason: str) -> None:
        if amount <= 0 or session.xp_system == "slow_and_sure":
            return
        if session.xp_system == "old_school":
            tier = tier_for_level(self._highest_character_level(session.party))
            points = tier * 100 * amount
            session.old_school_xp_tally += points
            session.log.append(f"{reason} Old School XP +{points} (tally {session.old_school_xp_tally}).")
            return
        if session.xp_system == "slower_advancement":
            session.slower_xp_bank += amount
            session.log.append(f"{reason} Banked {amount} XP ({session.slower_xp_bank} total).")
            return
        session.xp_rolls_pending += amount
        session.log.append(f"{reason} Earned {amount} XP roll(s). Assign from party sheets.")

    def _can_assign_level_up(self, session: SessionState, character_id: str) -> bool:
        survivors = [member for member in session.party if member.current_life > 0]
        if len(survivors) <= 1:
            return True
        return session.last_leveled_character_id != character_id

    def _award_encounter_xp(
        self,
        session: SessionState,
        defeated: list[EnemyState],
        *,
        show_rolls: bool,
    ) -> None:
        if not defeated or session.xp_system == "slow_and_sure":
            return
        if session.xp_system == "old_school":
            points = old_school_xp_for_defeated(defeated)
            if points:
                session.old_school_xp_tally += points
                session.log.append(f"Old School XP +{points} (tally {session.old_school_xp_tally}).")
            return

        majors = major_foes_defeated(defeated)
        if majors and defeated_mixed_major_minor(defeated):
            names = ", ".join(enemy.name for enemy in majors)
            self._grant_xp_credit(
                session,
                2,
                f"Mixed major+minions encounter ({names}; EE p.180):",
            )
            if any("final_boss" in enemy.tags for enemy in majors):
                session.final_boss_defeated = True
                self._grant_xp_credit(session, 1, "Final Boss slain:")
        else:
            for enemy in majors:
                self._grant_xp_credit(session, 1, f"Defeated {enemy.name} (Major Foe):")
                if "final_boss" in enemy.tags:
                    session.final_boss_defeated = True
                    self._grant_xp_credit(session, 1, "Final Boss slain:")
        if majors:
            return
        if not is_minor_encounter(defeated):
            return
        session.minor_encounters_defeated += 1
        if show_rolls:
            session.log.append(
                f"Minor encounter cleared ({session.minor_encounters_defeated}/"
                f"{MINOR_ENCOUNTERS_FOR_XP} toward next XP credit)."
            )
        if session.minor_encounters_defeated >= MINOR_ENCOUNTERS_FOR_XP:
            session.minor_encounters_defeated -= MINOR_ENCOUNTERS_FOR_XP
            self._grant_xp_credit(session, 1, f"{MINOR_ENCOUNTERS_FOR_XP} minor encounters:")

    def _complete_level_up(
        self,
        session: SessionState,
        member: PartyMemberState,
        *,
        new_spell: str | None = None,
    ) -> None:
        result = apply_level_up(member, new_spell=new_spell)
        session.log.extend(result.log)
        if member.class_id == "light_gladiator" and member.level >= 3 and "gladiator" not in learned_skill_ids(member):
            session.log.extend(
                apply_expert_skill_learn(member, "gladiator", self.rules.expert_skills())
            )
        session.last_leveled_character_id = member.character_id
        if result.spell_pick_pending:
            session.level_up_spell_pending_character_id = member.character_id
        else:
            session.level_up_spell_pending_character_id = None

    def _validate_advancement_fork(
        self,
        member: PartyMemberState,
        fork: str,
        *,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
        heroic_skill_id: str | None = None,
        legendary_skill_id: str | None = None,
        heroic_skill_target: str | None = None,
    ) -> str | None:
        allowed = available_advancement_forks(member)
        if fork not in allowed:
            if fork == "learn_expert_skill" and member.level >= 5 and not member.expert_trained:
                from .courtship_classes import is_wandering_alchemist

                if not is_wandering_alchemist(member):
                    return f"{member.name} needs Expert training before learning expert skills or spells."
            if fork == "learn_heroic_skill" and member.level >= 10 and not member.heroic_trained:
                return f"{member.name} needs Heroic training before learning heroic skills."
            if fork == "learn_legendary_skill" and member.level >= 15 and not member.legendary_trained:
                return f"{member.name} needs Legendary training before learning legendary skills."
            labels = ", ".join(advancement_fork_label(item) for item in allowed)
            return f"Choose {labels}."
        if fork == "level_up":
            return level_up_gate_reason(member, member.level + 1)
        if fork == "learn_expert_skill":
            if not expert_skill_id:
                return "Choose an expert skill or spell to learn."
            return validate_expert_skill_choice(member, expert_skill_id, self.rules.expert_skills())
        if fork == "learn_heroic_skill":
            if not heroic_skill_id:
                return "Choose a heroic skill to learn."
            blocked = validate_tier_skill_choice(member, heroic_skill_id, self.rules.heroic_skills(), "heroic")
            if blocked:
                return blocked
            from .heroic_skill_effects import HEROIC_TARGET_SKILLS

            if heroic_skill_id.strip().lower() in HEROIC_TARGET_SKILLS and not (heroic_skill_target or "").strip():
                return "Choose a weapon type for Heroic Accuracy (e.g. bow, sword, dagger)."
            return None
        if fork == "learn_legendary_skill":
            if not legendary_skill_id:
                return "Choose a legendary skill to learn."
            return validate_tier_skill_choice(member, legendary_skill_id, self.rules.legendary_skills(), "legendary")
        return None

    def _apply_advancement_success(
        self,
        session: SessionState,
        member: PartyMemberState,
        fork: str,
        *,
        new_spell: str | None = None,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
        heroic_skill_id: str | None = None,
        legendary_skill_id: str | None = None,
        heroic_skill_target: str | None = None,
    ) -> None:
        if fork == "level_up":
            self._complete_level_up(session, member, new_spell=new_spell)
            return
        if fork == "learn_expert_skill":
            session.log.extend(
                apply_expert_skill_learn(
                    member,
                    expert_skill_id or "",
                    self.rules.expert_skills(),
                    target=expert_skill_target,
                )
            )
            return
        if fork == "learn_heroic_skill":
            session.log.extend(
                apply_tier_skill_learn(
                    member,
                    heroic_skill_id or "",
                    self.rules.heroic_skills(),
                    "heroic",
                    target=heroic_skill_target,
                )
            )
            return
        if fork == "learn_legendary_skill":
            session.log.extend(
                apply_tier_skill_learn(
                    member, legendary_skill_id or "", self.rules.legendary_skills(), "legendary"
                )
            )

    def _pick_level_up_spell(
        self,
        session: SessionState,
        character_id: str | None,
        spell_name: str | None,
    ) -> None:
        if not session.level_up_spell_pending_character_id:
            session.log.append("No spell choice is pending.")
            return
        if character_id != session.level_up_spell_pending_character_id:
            session.log.append("Choose a spell for the hero who just leveled up.")
            return
        if not spell_name:
            session.log.append("Select a spell to prepare.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("Hero not found.")
            return
        session.log.extend(assign_level_up_spell(member, spell_name))
        session.level_up_spell_pending_character_id = None

    def _xp_roll(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
        explain_math: bool,
        new_spell: str | None = None,
        advancement_fork: str | None = None,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
        heroic_skill_id: str | None = None,
        legendary_skill_id: str | None = None,
        heroic_skill_target: str | None = None,
    ) -> None:
        if session.level_up_spell_pending_character_id:
            pending = next(
                (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
                None,
            )
            name = pending.name if pending else "the hero"
            session.log.append(f"Choose a spell for {name} before spending another XP roll.")
            return
        if session.mode == "combat":
            session.log.append("XP rolls wait until combat ends.")
            return
        if session.xp_system != "classical":
            session.log.append(f"Use the {campaign_mode_label(session.xp_system)} advancement action instead.")
            return
        if session.xp_rolls_pending <= 0:
            session.log.append("No XP rolls are available.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero for the XP roll.")
            return
        if not self._can_assign_level_up(session, character_id or ""):
            session.log.append("Another hero must take the next level (same PC cannot level twice in a row).")
            return

        allowed = available_advancement_forks(member)
        fork = advancement_fork or (allowed[0] if len(allowed) == 1 else None)
        blocked = self._validate_advancement_fork(
            member,
            fork or "",
            expert_skill_id=expert_skill_id,
            expert_skill_target=expert_skill_target,
            heroic_skill_id=heroic_skill_id,
            legendary_skill_id=legendary_skill_id,
            heroic_skill_target=heroic_skill_target,
        )
        if fork is None or blocked:
            session.log.append(blocked or f"Choose {', '.join(advancement_fork_label(item) for item in allowed)}.")
            return

        purpose = {
            "level_up": "level_up",
            "learn_expert_skill": "learn_expert_skill",
            "learn_heroic_skill": "learn_heroic_skill",
            "learn_legendary_skill": "learn_legendary_skill",
        }[fork]
        session.xp_rolls_pending -= 1
        from .heroic_skill_effects import consume_training_focus_bonus

        focus_bonus = consume_training_focus_bonus(session, member.character_id)
        result = perform_advancement_roll(member, purpose=purpose, bonus=focus_bonus)
        if focus_bonus:
            session.log.append(f"{member.name} applies Training Focus (+{focus_bonus}).")
        if show_rolls:
            session.log.append(
                f"{advancement_fork_label(fork)} roll for {member.name}: {result.die_label} = {result.natural}"
                + (f" + {result.modifier} = {result.total}" if result.modifier else "")
                + f" vs Level {member.level}."
            )
        if explain_math:
            session.log.append(advancement_roll_explain(member))
        if advancement_succeeds(result, member.level):
            self._apply_advancement_success(
                session,
                member,
                fork,
                new_spell=new_spell,
                expert_skill_id=expert_skill_id,
                expert_skill_target=expert_skill_target,
                heroic_skill_id=heroic_skill_id,
                legendary_skill_id=legendary_skill_id,
                heroic_skill_target=heroic_skill_target,
            )
        elif fork == "level_up":
            session.log.append(f"{member.name} fails to advance (needs > {member.level}).")
        else:
            session.log.append(
                f"{member.name} fails to learn the {advancement_fork_label(fork).lower()} (needs > {member.level})."
            )

    def _bank_xp_roll(self, session: SessionState, character_id: str | None) -> None:
        if session.level_up_spell_pending_character_id:
            pending = next(
                (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
                None,
            )
            name = pending.name if pending else "the hero"
            session.log.append(f"Choose a spell for {name} before banking another XP roll.")
            return
        if session.mode == "combat":
            session.log.append("XP rolls wait until combat ends.")
            return
        if session.xp_system != "classical":
            session.log.append(f"Use the {campaign_mode_label(session.xp_system)} advancement action instead.")
            return
        if session.xp_rolls_pending <= 0:
            session.log.append("No pending XP rolls are available to bank.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to bank the XP roll.")
            return
        session.xp_rolls_pending -= 1
        member.xp += 1
        session.log.append(f"{member.name} banks 1 XP roll for later advancement ({member.xp} banked).")

    def _spend_banked_xp(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
        explain_math: bool,
        new_spell: str | None = None,
        advancement_fork: str | None = None,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
        heroic_skill_id: str | None = None,
        legendary_skill_id: str | None = None,
        heroic_skill_target: str | None = None,
    ) -> None:
        if session.level_up_spell_pending_character_id:
            pending = next(
                (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
                None,
            )
            name = pending.name if pending else "the hero"
            session.log.append(f"Choose a spell for {name} before spending banked XP.")
            return
        if session.mode == "combat":
            session.log.append("Banked XP spending waits until combat ends.")
            return
        if session.xp_system != "classical":
            session.log.append(f"Use the {campaign_mode_label(session.xp_system)} advancement action instead.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to spend banked XP.")
            return
        if member.xp <= 0:
            session.log.append(f"{member.name} has no banked XP rolls.")
            return

        allowed = available_advancement_forks(member)
        fork = advancement_fork or (allowed[0] if len(allowed) == 1 else None)
        blocked = self._validate_advancement_fork(
            member,
            fork or "",
            expert_skill_id=expert_skill_id,
            expert_skill_target=expert_skill_target,
            heroic_skill_id=heroic_skill_id,
            legendary_skill_id=legendary_skill_id,
            heroic_skill_target=heroic_skill_target,
        )
        if fork is None or blocked:
            session.log.append(blocked or f"Choose {', '.join(advancement_fork_label(item) for item in allowed)}.")
            return
        if fork == "level_up" and not self._can_assign_level_up(session, character_id or ""):
            session.log.append("Another hero must take the next level (same PC cannot level twice in a row).")
            return

        purpose = {
            "level_up": "level_up",
            "learn_expert_skill": "learn_expert_skill",
            "learn_heroic_skill": "learn_heroic_skill",
            "learn_legendary_skill": "learn_legendary_skill",
        }[fork]
        member.xp -= 1
        from .heroic_skill_effects import consume_training_focus_bonus

        focus_bonus = consume_training_focus_bonus(session, member.character_id)
        result = perform_advancement_roll(member, purpose=purpose, bonus=focus_bonus)
        if focus_bonus:
            session.log.append(f"{member.name} applies Training Focus (+{focus_bonus}).")
        if show_rolls:
            session.log.append(
                f"Banked {advancement_fork_label(fork).lower()} roll for {member.name}: {result.die_label} = {result.natural}"
                + (f" + {result.modifier} = {result.total}" if result.modifier else "")
                + f" vs Level {member.level}."
            )
        if explain_math:
            session.log.append(advancement_roll_explain(member))
        if advancement_succeeds(result, member.level):
            self._apply_advancement_success(
                session,
                member,
                fork,
                new_spell=new_spell,
                expert_skill_id=expert_skill_id,
                expert_skill_target=expert_skill_target,
                heroic_skill_id=heroic_skill_id,
                legendary_skill_id=legendary_skill_id,
                heroic_skill_target=heroic_skill_target,
            )
        elif fork == "level_up":
            session.log.append(f"{member.name} fails to advance (needs > {member.level}).")
        else:
            session.log.append(
                f"{member.name} fails to learn the {advancement_fork_label(fork).lower()} (needs > {member.level})."
            )

    def _bank_training_focus(self, session: SessionState, character_id: str | None) -> None:
        if session.mode == "combat":
            session.log.append("Training Focus waits until combat ends.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to focus for training.")
            return
        from .heroic_skill_effects import bank_training_focus

        session.log.extend(bank_training_focus(session, member))

    def _envenom_weapon(
        self,
        session: SessionState,
        character_id: str | None,
        weapon_kind: str | None,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Envenom a weapon before combat begins.")
            return
        member = next((hero for hero in session.party if hero.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to envenom a weapon.")
            return
        session.log.extend(apply_envenom_weapon(session, member, weapon_kind or ""))

    def _maybe_trigger_alchemist_revisit_trap(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if not session.wandering_alchemist_met:
            return
        if tile.id not in session.alchemist_event_tile_ids:
            return
        if tile.trap_key and not tile.trap_resolved:
            return
        hcl = self._highest_character_level(session.party)
        trap = self.table_roller.roll_trap(
            hcl,
            show_rolls=show_rolls,
            explain_math=explain_math,
            environment=session.environment,
        )
        tile.trap_key = trap.trap_key
        tile.trap_level = trap.trap_level
        if trap.summary not in tile.objects:
            tile.objects.append(trap.summary)
        tile.alchemist_available = False
        session.log.append("Event: Returning to the alchemist's room triggers a trap instead.")
        session.log.append(f"Event: Trap triggered: {trap.summary}")

    def _buy_healing(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Buy healing between encounters.")
            return
        tile = self._current_tile(session)
        if not tile.healer_available:
            session.log.append("No wandering healer is here.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to heal.")
            return
        if member.current_life >= member.max_life:
            session.log.append(f"{member.name} is already at full Life.")
            return
        payer = next((item for item in session.party if item.gold >= 10), None)
        if payer is None:
            session.log.append("The party needs 10gp for the healer.")
            return
        payer.gold -= 10
        member.current_life += 1
        if show_rolls:
            session.log.append(
                f"{payer.name} pays 10gp; the healer restores 1 Life to {member.name} "
                f"({member.current_life}/{member.max_life})."
            )

    def _buy_alchemist(
        self,
        session: SessionState,
        character_id: str | None,
        item_key: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Buy from the alchemist between encounters.")
            return
        tile = self._current_tile(session)
        if not tile.alchemist_available:
            session.log.append("No wandering alchemist is here.")
            return
        if item_key not in {"potion", "poison"}:
            session.log.append("Choose Potion of Healing (50gp) or blade poison (30gp).")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero for the purchase.")
            return
        if item_key == "potion":
            if member.character_id in session.alchemist_potion_bought:
                session.log.append(f"{member.name} already bought a potion this adventure.")
                return
            cost = 50
            item_name = "Potion of Healing"
        else:
            if member.character_id in session.alchemist_poison_bought:
                session.log.append(f"{member.name} already bought poison this adventure.")
                return
            cost = 30
            item_name = "Blade poison"
        payer = next((item for item in session.party if item.gold >= cost), None)
        if payer is None:
            session.log.append(f"The party needs {cost}gp for {item_name}.")
            return
        payer.gold -= cost
        ok, message = can_add_item(member, item_name)
        if not ok:
            payer.gold += cost
            session.log.append(message)
            return
        member.inventory.append(item_name)
        if item_key == "potion":
            session.alchemist_potion_bought.append(member.character_id)
        else:
            session.alchemist_poison_bought.append(member.character_id)
        if show_rolls:
            session.log.append(f"{payer.name} pays {cost}gp; {member.name} receives {item_name}.")

    def _use_class_ability(
        self,
        session: SessionState,
        character_id: str | None,
        class_ability: str | None,
        *,
        target_character_id: str | None = None,
        foe_id: str | None = None,
        show_rolls: bool = True,
        explain_math: bool = False,
        exit_id: str | None = None,
        gadget_points: int | None = None,
        panache_spend: int | None = None,
        search_choice: str | None = None,
        item_name: str | None = None,
        gold_amount: int | None = None,
    ) -> None:
        if not class_ability:
            session.log.append("No class ability specified.")
            return
        actor = next((member for member in session.party if member.character_id == character_id), None)
        if actor is None:
            session.log.append("Choose a hero for this ability.")
            return
        tile = self._current_tile(session)
        heroes_here = combat_party(session, tile.id)
        hero_ids_here = {member.character_id for member in heroes_here}
        if actor.current_life > 0 and actor.character_id not in hero_ids_here:
            session.log.append(f"{actor.name} is not on the current map element.")
            return
        living_foes = [enemy for enemy in tile.enemies if enemy.life > 0]

        if class_ability == "combat_acrobatics":
            if session.mode != "combat":
                session.log.append("Combat Acrobatics is used during combat.")
                return
            if not has_skill(actor, "combat_acrobatics"):
                session.log.append(f"{actor.name} has not learned Combat Acrobatics.")
                return
            ally = next(
                (member for member in heroes_here if member.character_id == target_character_id),
                None,
            )
            if ally is None or ally.character_id == actor.character_id:
                session.log.append("Choose another hero to swap marching order with.")
                return
            actor_order = actor.marching_order
            actor.marching_order = ally.marching_order
            ally.marching_order = actor_order
            session.acrobat_skip_attack[actor.character_id] = True
            session.log.append(
                f"{actor.name} swaps position with {ally.name} (Combat Acrobatics; no attack this round)."
            )
            return

        if class_ability == "lesser_necromancy":
            if session.mode != "exploration":
                session.log.append("Lesser Necromancy is used during exploration.")
                return
            if not has_skill(actor, "lesser_necromancy"):
                session.log.append(f"{actor.name} has not learned Lesser Necromancy.")
                return
            target = next(
                (member for member in session.party if member.character_id == target_character_id),
                None,
            )
            if target is None or target.current_life > 0:
                session.log.append("Choose a fallen hero on this tile.")
                return
            if target.character_id not in tile.fallen_character_ids:
                session.log.append("The ritual requires a fallen comrade here.")
                return
            total = roll_die(8) + actor.level
            if show_rolls:
                session.log.append(
                    f"Lesser Necromancy: {actor.name} rolls d8+L = {total} vs L{target.level} ({target.name})."
                )
            if total <= target.level:
                session.log.append("The necromantic ritual fails.")
                return
            target.current_life = max(1, target.max_life // 2)
            target.abilities = []
            target.spells = []
            target.learned_expert_skills = []
            target.learned_heroic_skills = []
            target.learned_legendary_skills = []
            target.expert_skill_targets = {}
            target.statuses = [status for status in target.statuses if status.lower() != "fallen"]
            if "Undead" not in target.statuses:
                target.statuses.append("Undead")
            tile.fallen_character_ids = [
                cid for cid in tile.fallen_character_ids if cid != target.character_id
            ]
            session.log.append(
                f"{target.name} rises as undead with {target.current_life} Life (no class abilities)."
            )
            return

        if class_ability == "throw_spore":
            if session.mode != "combat":
                session.log.append("Sleep spores are thrown during combat.")
                return
            if not has_skill(actor, "spore_alchemy"):
                session.log.append(f"{actor.name} has not learned Spore Alchemy.")
                return
            doses = dict(session.expert_spore_doses or {})
            if doses.get(actor.character_id, 0) <= 0:
                session.log.append("No sleep spores remain.")
                return
            from .spells import cast_sleep_effect

            doses[actor.character_id] = doses.get(actor.character_id, 0) - 1
            session.expert_spore_doses = doses
            session.log.append(f"{actor.name} throws a sleep spore.")
            outcome = cast_sleep_effect(
                actor, session.party, tile.enemies, show_rolls=show_rolls
            )
            session.log.extend(outcome.log)
            tile.enemies = outcome.enemies
            return

        if class_ability == "turn_undead":
            from .expert_skill_effects import _is_undead, encounter_spent, mark_encounter_spent

            if session.mode != "combat":
                session.log.append("Turn Undead is used during combat.")
                return
            if not has_skill(actor, "turn_undead"):
                session.log.append(f"{actor.name} has not learned Turn Undead.")
                return
            if encounter_spent(session, actor.character_id, "turn_undead"):
                session.log.append(f"{actor.name} has already used Turn Undead this encounter.")
                return
            undead = [enemy for enemy in living_foes if _is_undead(enemy)]
            if not undead:
                session.log.append("Turn Undead has no eligible undead foes in this encounter.")
                return
            mark_encounter_spent(session, actor.character_id, "turn_undead")
            active_enemy_ids = {enemy.id for enemy in living_foes}
            standing_before = {member.character_id for member in heroes_here if member.current_life > 0}
            session.log.append(
                f"{actor.name} invokes Turn Undead against {len(undead)} undead foe"
                f"{'' if len(undead) == 1 else 's'}."
            )
            for enemy in undead:
                total = roll_d6() + actor.level // 2
                if show_rolls:
                    session.log.append(
                        f"Turn Undead: {actor.name} rolls d6+½L = {total} vs L{enemy.level} ({enemy.name})."
                    )
                if total >= enemy.level:
                    flee = roll_d6()
                    enemy.life = max(0, enemy.life - flee)
                    if enemy.life <= 0:
                        session.log.append(f"Turn Undead succeeds against {enemy.name}; it loses {flee} Life and is destroyed.")
                    else:
                        session.log.append(f"Turn Undead succeeds against {enemy.name}; it loses {flee} Life.")
                else:
                    session.log.append(f"Turn Undead fails against {enemy.name}.")
            if not any(enemy.life > 0 for enemy in tile.enemies):
                self._apply_combat_result(
                    session,
                    tile,
                    CombatRound(
                        party=session.party,
                        enemies=tile.enemies,
                        log=[],
                        combat_over=True,
                    ),
                    show_rolls=show_rolls,
                    active_enemy_ids=active_enemy_ids,
                    standing_before=standing_before,
                )
            return

        if class_ability == "paladin_heal":
            target_id = target_character_id or character_id
            target = next((member for member in heroes_here if member.character_id == target_id), None)
            if target is None:
                session.log.append("Choose a target on this map element to heal.")
                return
            session.log.extend(paladin_heal(session, actor, target))
            return

        if class_ability in {"paladin_reroll_save", "halfling_reroll_save"}:
            pending = session.pending_save_reroll
            if class_ability == "halfling_reroll_save" and luck_points_remaining(session, actor) <= 0:
                session.log.append(f"{actor.name} has no Luck points remaining.")
                return
            log, succeeded = reroll_failed_save_with_luck(session, actor, show_rolls=show_rolls)
            session.log.extend(log)
            if pending and pending.get("context") in {"puzzle", "magic_challenge"}:
                if succeeded:
                    if pending.get("context") == "magic_challenge":
                        session.log.append("The magical challenge is answered; the foes let you pass.")
                    else:
                        session.log.append("The puzzle is solved; the foes let you pass.")
                    self._end_peaceful_encounter(session, tile)
                else:
                    session.foes_strike_first = True
                    session.reaction_pending = False
            return

        if class_ability == "paladin_summon_steed":
            session.log.extend(paladin_summon_steed(session, actor))
            return

        if class_ability == "acrobat_shift_position":
            if session.mode != "exploration":
                session.log.append("Shift Position is used in exploration.")
                return
            ally = next(
                (member for member in heroes_here if member.character_id == target_character_id),
                None,
            )
            if ally is None or ally.character_id == actor.character_id:
                session.log.append("Choose another hero to swap marching order with.")
                return
            session.log.extend(acrobat_shift_position(session, actor, ally))
            return

        if class_ability == "acrobat_distract":
            enemy = next((item for item in living_foes if item.id == foe_id), None)
            if enemy is None:
                session.log.append("Choose a foe to distract.")
                return
            session.log.extend(acrobat_distract(session, actor, enemy))
            return

        if class_ability == "illusionist_distract":
            enemy = next((item for item in living_foes if item.id == foe_id), None)
            if enemy is None:
                session.log.append("Choose a foe to distract with lights.")
                return
            session.log.extend(illusionist_distract(session, actor, enemy, all_enemies=tile.enemies))
            return

        if class_ability == "acrobat_leap_harm":
            session.log.extend(acrobat_leap_out_of_harm(session, actor))
            return

        if class_ability == "acrobat_serpent_twist":
            session.log.extend(acrobat_serpent_twist(session, actor))
            return

        if class_ability == "acrobat_evade":
            if session.mode != "combat":
                session.log.append("Evade is used during combat.")
                return
            session.log.extend(acrobat_evade(session, actor))
            return

        if class_ability == "gnome_smokescreen":
            session.log.extend(gnome_smokescreen(session, actor))
            return

        if class_ability == "mushroom_spore_cloud":
            if session.mode == "combat" and session.combat_round > 0:
                session.log.append("Spore cloud must be used before or at the start of a fight.")
                return
            session.log.extend(mushroom_spore_cloud(session, actor, tile.enemies))
            return

        if class_ability == "assassin_hide":
            if session.mode != "combat":
                session.log.append("Hide in Shadows is used when foes are present.")
                return
            session.log.extend(
                assassin_hide(
                    session,
                    actor,
                    tile.enemies,
                    show_rolls=show_rolls,
                    target_foe_id=foe_id,
                )
            )
            return

        if class_ability == "gnome_gadget_trap":
            if session.mode == "combat":
                session.log.append("Disarm traps during exploration.")
                return
            if not tile.trap_key or tile.trap_resolved:
                session.log.append("There is no active trap here.")
                return
            points = gadget_points or 1
            trap_level = tile.trap_level or self._highest_character_level(session.party)
            ok, log = attempt_gnome_trap_disarm(
                session, actor, trap_level, gadget_points=points, show_rolls=show_rolls
            )
            session.log.extend(log)
            if ok:
                tile.trap_resolved = True
                self._after_trap_resolved(session, tile, show_rolls=show_rolls)
            else:
                trap_result = self.table_roller.resolve_trap(
                    tile.trap_key,
                    trap_level,
                    session.party,
                    self._marching_order_ids(session),
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
                if trap_result.pending_mycelium_snare_character_id:
                    from ..schemas import PendingMyceliumSnareState

                    session.pending_mycelium_snare = PendingMyceliumSnareState(
                        tile_id=tile.id,
                        character_id=trap_result.pending_mycelium_snare_character_id,
                    )
                    session.log.extend(trap_result.log)
                else:
                    self._finalize_trap_resolution(
                        session,
                        tile,
                        trap_log=trap_result.log,
                        show_rolls=show_rolls,
                    )
                    tile.objects = [item for item in tile.objects if "trap" not in item.lower()]
            return

        if class_ability == "gnome_gadget_door":
            if session.mode != "exploration":
                session.log.append("Gadget doors are worked during exploration.")
                return
            exit_state = next((item for item in tile.exits if item.id == exit_id), None) if exit_id else None
            if exit_state is None or exit_state.kind != "door" or exit_state.door_open:
                session.log.append("Choose a closed door.")
                return
            if exit_state.door_type is None:
                hcl = self._highest_character_level(session.party)
                outcome = self.table_roller.roll_door(hcl)
                exit_state.door_type = outcome.door_type
                exit_state.door_level = outcome.door_level
                exit_state.door_result = outcome.summary
                exit_state.door_treasure_bonus = outcome.treasure_bonus
                session.log.extend(door_discovery_log(outcome, hcl=hcl, show_rolls=show_rolls))
            door_type = exit_state.door_type or "unlocked"
            if door_type == "lever":
                session.log.extend(open_lever_door_with_gnome_gadget(session, actor))
                exit_state.door_open = True
                exit_state.status = "open"
                self._sync_linked_door(session, tile, exit_state)
                session.log.append(f"The {exit_state.direction} lever door opens.")
                return
            points = gadget_points or 1
            ok, log = attempt_gnome_gadget_door(
                session,
                actor,
                exit_state.door_level or 6,
                gadget_points=points,
                show_rolls=show_rolls,
            )
            session.log.extend(log)
            if ok:
                exit_state.door_open = True
                exit_state.status = "open"
                self._sync_linked_door(session, tile, exit_state)
                session.log.append(f"The {exit_state.direction} door is now open.")
            return

        if class_ability == "halfling_luck_treasure":
            if session.pending_treasure_reroll_tile_id != tile.id:
                session.log.append("No fresh treasure roll is available to reroll on this tile.")
                return
            if not spend_luck_point(session, actor):
                session.log.append(f"{actor.name} has no Luck points remaining.")
                return
            tile.treasure_summary = ""
            tile.treasure_gold = 0
            tile.treasure_items = []
            outcome = self._roll_treasure(session)
            if show_rolls:
                session.log.extend(outcome.log)
            session.log.append(f"{actor.name} spends 1 Luck point to reroll the treasure table.")
            if outcome.gold or outcome.items:
                tile.treasure_summary = outcome.summary
                tile.treasure_gold = outcome.gold
                tile.treasure_items = self._finalize_treasure_items(
                    session, list(outcome.items), show_rolls=show_rolls
                )
                self._apply_treasure_doubling(tile)
                session.log.append("Treasure is available to claim.")
            else:
                tile.treasure_summary = outcome.summary
                session.log.append(outcome.summary or "No treasure found.")
            session.pending_treasure_reroll_tile_id = None
            return

        if class_ability == "halfling_luck_hidden_complication":
            if session.pending_hidden_complication_reroll_tile_id != tile.id:
                session.log.append("No hidden treasure complication is available to reroll on this tile.")
                return
            effect = tile.hidden_treasure_complication_effect_pending
            if not effect:
                session.log.append("No hidden treasure complication is pending on this tile.")
                return
            if not spend_luck_point(session, actor):
                session.log.append(f"{actor.name} has no Luck points remaining.")
                return
            complication = roll_d6()
            session.log.append(f"{actor.name} spends 1 Luck point to reroll the hidden treasure complication.")
            session.log.append(f"Hidden treasure complication reroll: d6 = {complication}.")
            new_effect, result_text, _ = self.table_roller.lookup_hidden_treasure_complication(complication)
            if result_text:
                session.log.append(result_text)
            hcl = self._highest_character_level(session.party)
            self._apply_hidden_treasure_complication(
                session,
                tile,
                new_effect or effect,
                hcl=hcl,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return

        if class_ability == "halfling_luck_search":
            if session.pending_search_reroll_tile_id != tile.id:
                session.log.append("No search roll is available to reroll on this tile.")
                return
            if not spend_luck_point(session, actor):
                session.log.append(f"{actor.name} has no Luck points remaining.")
                return
            session.pending_search_reroll_tile_id = None
            session.pending_search_reward_tile_id = None
            tile.searched = False
            session.log.append(f"{actor.name} spends 1 Luck point to reroll the search table.")
            self._search(
                session,
                search_choice=search_choice,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return

        if class_ability == "pole_search_reroll":
            carrier = pole_carrier(session.party)
            if carrier is None or actor.character_id != carrier.character_id:
                session.log.append("Only the hero carrying the 10' pole may reroll search.")
                return
            if session.pending_pole_search_reroll_tile_id != tile.id:
                session.log.append("No pole search reroll is available on this tile.")
                return
            session.pending_pole_search_reroll_tile_id = None
            session.pending_search_reward_tile_id = None
            tile.searched = False
            session.log.append(f"{actor.name} uses the 10' pole to reroll the search table.")
            self._search(
                session,
                search_choice=search_choice,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return

        if class_ability == "arm_talisman_save":
            from .equipment_effects import arm_talisman_save

            ok, message = arm_talisman_save(actor)
            session.log.append(message)
            return

        if class_ability == "gnome_repair_firearm":
            target = next(
                (member for member in session.party if member.character_id == target_character_id),
                actor,
            )
            session.log.extend(gnome_repair_firearm(session, actor, target))
            return

        if class_ability == "acrobat_graceful_move":
            session.log.extend(acrobat_graceful_move(session, actor))
            return

        if class_ability == "illusionist_continual_light":
            session.log.extend(illusionist_continual_light(session, actor))
            return

        if class_ability == "gnome_gadget_free":
            target = next(
                (member for member in session.party if member.character_id == target_character_id),
                None,
            )
            if target is None:
                session.log.append("Choose an ally to free from restraints.")
                return
            session.log.extend(
                gnome_gadget_free_prisoner(session, actor, target, show_rolls=show_rolls)
            )
            return

        if class_ability == "mushroom_hyphae":
            from .terrain import resolve_play_context

            play_ctx = resolve_play_context(tile, session)
            env = "wilderness" if play_ctx.outdoors else play_ctx.environment
            log, follow_up = mushroom_hyphae_communion(
                session,
                actor,
                environment=env,
                choice=search_choice or "search",
            )
            session.log.extend(log)
            if follow_up == "secret_door":
                self._reveal_secret_door(session, tile, show_rolls=show_rolls, explain_math=explain_math)
            elif follow_up == "secret_passage":
                self._reveal_secret_passage(session, tile, show_rolls=show_rolls)
            return

        if class_ability == "kukla_army_of_dolls":
            session.log.extend(kukla_deploy_dolls(session, actor))
            return

        if class_ability == "kukla_green_ring_revive":
            if session.mode != "exploration":
                session.log.append("Use the green ring during exploration.")
                return
            target = next(
                (member for member in session.party if member.character_id == target_character_id),
                None,
            )
            if target is None:
                session.log.append("Choose a fallen kukla on this tile.")
                return
            session.log.extend(kukla_green_ring_revive(session, actor, target, tile, show_rolls=show_rolls))
            return

        if class_ability == "kukla_red_ring_poison":
            if session.mode not in {"exploration", "combat"}:
                session.log.append("The red ring is used when foes are present.")
                return
            enemy = next((item for item in living_foes if item.id == foe_id), None)
            if enemy is None and living_foes:
                enemy = living_foes[0]
            session.log.extend(kukla_red_ring_poison(session, actor, enemy, show_rolls=show_rolls))
            return

        if class_ability == "kukla_compartment_stash":
            if session.mode != "exploration":
                session.log.append("Use the secret compartment during exploration.")
                return
            session.log.extend(
                kukla_compartment_stash(actor, item_name or "", gold_amount=gold_amount)
            )
            return

        if class_ability == "kukla_compartment_retrieve":
            if session.mode != "exploration":
                session.log.append("Use the secret compartment during exploration.")
                return
            if gold_amount:
                session.log.extend(kukla_compartment_retrieve_gold(actor, gold_amount))
            else:
                session.log.extend(kukla_compartment_retrieve(actor, item_name or ""))
            return

        if class_ability == "restore_mental_capacity":
            from .heroic_skill_effects import restore_mental_capacity

            target = next(
                (item for item in session.party if item.character_id == (target_character_id or actor.character_id)),
                actor,
            )
            session.log.extend(restore_mental_capacity(session, actor, target))
            return

        if class_ability == "swashbuckler_taunt":
            if session.mode != "combat":
                session.log.append("Taunt is used during combat.")
                return
            enemy = next((item for item in tile.enemies if item.id == foe_id and item.life > 0), None)
            if enemy is None:
                session.log.append("Choose a living foe to Taunt.")
                return
            from .swashbuckler_traits import apply_swashbuckler_taunt

            session.log.extend(apply_swashbuckler_taunt(session, actor, enemy))
            return

        if class_ability == "lucky_hat":
            from .swashbuckler_traits import lucky_hat_reroll_defense

            log, _succeeded = lucky_hat_reroll_defense(session, actor, show_rolls=show_rolls)
            session.log.extend(log)
            return

        if class_ability == "blade_dance":
            from .swashbuckler_traits import activate_blade_dance

            points = gadget_points or panache_spend or 1
            session.log.extend(activate_blade_dance(session, actor, panache_points=points))
            return

        session.log.append(f"Unknown class ability: {class_ability}.")

    def _rest(
        self,
        session: SessionState,
        *,
        nail_doors: bool = False,
        rest_choices: dict[str, str] | None = None,
        show_rolls: bool = True,
        nourishing_meal: bool = False,
        nourishing_meal_eaters: list[str] | None = None,
        everyone_eats: bool = False,
    ) -> None:
        tile = self._current_tile(session)
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
            session.log.append(reason)
            return

        doors = nailable_doors(tile)
        session.log.append("The party rests (once per adventure, rulebook p.114).")
        if nail_doors:
            if not consume_nail_bags(session.party, len(doors)):
                session.log.append("Not enough bags of nails to seal the doors.")
                return
            for exit_state in doors:
                exit_state.nailed_shut = True
                exit_state.door_open = False
                exit_state.status = "blocked"
                self._sync_linked_door(session, tile, exit_state)
            session.log.append(
                f"The party nails {len(doors)} door(s) shut ({len(doors)} bag(s) of nails used)."
            )
        else:
            session.log.append("The party does not nail the doors shut.")

        session.rest_used = True
        session.alter_weather_active = False
        session.forest_pathway_active = False
        session.glamour_mask_character_id = None
        session.glamour_mask_reroll_available = False
        session.log.extend(apply_rest_recovery(session, session.party, choices, tile=tile))
        for member in living:
            trick_note = recover_acrobat_tricks_on_rest(session, member)
            if trick_note:
                session.log.append(trick_note)
        if everyone_eats:
            session.log.extend(feed_all_living_heroes(session, session.party))
        if nourishing_meal:
            eaters = nourishing_meal_eaters or [
                member.character_id for member in living if member.current_life > 0
            ]
            session.log.extend(apply_nourishing_meal(session, session.party, eaters))

        triggered, roll = wandering_roll_triggers(
            tile.cavern_feature_key,
            roll_bonus=session.next_wandering_roll_bonus,
        )
        if session.next_wandering_roll_bonus:
            if show_rolls:
                session.log.append(
                    f"Firearm noise increases wandering risk (+{session.next_wandering_roll_bonus} on d6)."
                )
            session.next_wandering_roll_bonus = 0
        if show_rolls:
            session.log.append(f"Rest wandering-monster roll: d6 = {roll}.")
        if not triggered:
            session.log.append("The rest is undisturbed.")
            return

        door = pick_wandering_door(doors)
        if door is not None:
            if nail_doors:
                session.log.append(
                    f"Wandering Monsters force open the nailed {door.direction} door!"
                )
            else:
                session.log.append(
                    f"Wandering Monsters burst through the unnailed {door.direction} door!"
                )
        else:
            session.log.append("Wandering Monsters arrive!")
        tile.wandering_ambush = False
        self._spawn_wandering_monsters(
            session,
            tile,
            show_rolls=show_rolls,
            combat_message="Wandering Monsters disturb the rest!",
            party_strikes_first=nail_doors,
            foes_strike_first=not nail_doors,
        )
        self._check_detached_wandering(session, show_rolls=show_rolls, exclude_tile_id=tile.id)
        if nail_doors:
            session.log.append(
                "The nailed doors gave warning — the party may attack first even if the foes would normally surprise you."
            )
        else:
            session.log.append("The unnailed doors gave no warning — Wandering Monsters attack first.")

    def _generate_tile(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
        hcl: int,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> TileState | None:
        failed_keys: list[str] = []
        for attempt_index, tile_key in enumerate(self._generated_placement_attempt_keys(session), start=1):
            tile_def = self._tiles_for_session(session).get(tile_key)
            tile_type = self._tile_type(tile_def.tile_type if tile_def else "unknown")
            placement = self._select_placement(session, origin, origin_exit, tile_type, tile_def)
            if placement is None:
                failed_keys.append(tile_key)
                if show_rolls:
                    session.log.append(f"Map element roll: d66 = {tile_key}; no legal placement, rerolling.")
                elif explain_math:
                    session.log.append(f"Map element {tile_key} could not be placed; trying another candidate.")
                continue
            if "tile_def" in inspect.signature(self._roll_content).parameters:
                content = self._roll_content(session, tile_type, hcl, tile_def=tile_def)
            else:
                content = self._roll_content(session, tile_type, hcl)
            return self._tile_from_placement(
                tile_key=tile_key,
                tile_type=tile_type,
                tile_def=tile_def,
                placement=placement,
                content=content,
                hcl=hcl,
                session=session,
                show_rolls=show_rolls,
                explain_math=explain_math,
                attempt_index=attempt_index,
            )

        placement = self._fallback_dead_end_placement(session, origin, origin_exit)
        if placement is None:
            return None
        if failed_keys:
            session.log.append(
                f"No generated map element could be placed after {len(failed_keys)} attempt"
                f"{'s' if len(failed_keys) != 1 else ''}; drawing a 1x1 dead end."
            )
        content = self._content("empty", "The cramped dead end is quiet.", [], [])
        return self._tile_from_placement(
            tile_key=FALLBACK_MAP_ELEMENT_KEY,
            tile_type="corridor",
            tile_def=None,
            placement=placement,
            content=content,
            hcl=hcl,
            session=session,
            show_rolls=show_rolls,
            explain_math=explain_math,
            attempt_index=len(failed_keys) + 1,
        )

    def _tile_from_placement(
        self,
        *,
        tile_key: str,
        tile_type: str,
        tile_def: TileDefinition | None,
        placement: Placement,
        content: dict,
        hcl: int,
        session: SessionState,
        show_rolls: bool,
        explain_math: bool,
        attempt_index: int,
    ) -> TileState:
        if show_rolls and tile_key == FALLBACK_MAP_ELEMENT_KEY:
            session.log.append("Emergency placement fallback: 1x1 dead-end map element.")
        elif show_rolls:
            session.log.append(f"Map element roll: d66 = {tile_key}.")
            if attempt_index > 1 and tile_key != FALLBACK_MAP_ELEMENT_KEY:
                session.log.append(f"Placed the map element after {attempt_index} placement attempts.")
        if explain_math:
            session.log.append(f"Map element lookup for {tile_key}: {tile_def.name if tile_def else 'metadata missing'}.")
        if show_rolls:
            if "roll" in content:
                session.log.append(f"Room content roll: 2d6 = {content['roll']}.")
            elif tile_key == FALLBACK_MAP_ELEMENT_KEY:
                session.log.append("Emergency dead-end fallback: no room content roll.")
        if explain_math and "roll" in content:
            session.log.append(f"{tile_type.title()} content lookup for {content['roll']}: {content['description']}")
        if placement.truncated:
            session.log.append("The map element was truncated to avoid overlapping explored space or open exits.")
        tile = TileState(
            id=uuid4().hex,
            x=placement.x,
            y=placement.y,
            tile_key=tile_key,
            tile_type=tile_type,
            rotation=placement.rotation,
            footprint_width=tile_def.footprint_width if tile_def else 1,
            footprint_height=tile_def.footprint_height if tile_def else 1,
            editor_cell_size=tile_def.editor_cell_size if tile_def else 80,
            image_scale=tile_def.image_scale if tile_def else 1.0,
            image_offset_x=tile_def.image_offset_x if tile_def else 0,
            image_offset_y=tile_def.image_offset_y if tile_def else 0,
            walkable=placement.walkable,
            cell_shapes=placement.cell_shapes,
            visible=placement.visible,
            image=self._tile_image(tile_key, tile_def.image if tile_def else None),
            title=tile_def.name if tile_def else f"{tile_type.title()} {tile_key}",
            description=self._tile_description(tile_def.description if tile_def else "", content["description"]),
            content_key=content["key"],
            objects=content["objects"],
            enemies=content["enemies"],
            exits=placement.exits,
            initial_enemy_count=len(content["enemies"]),
            environment=session.environment,
            terrain=tile_def.terrain if tile_def else "indoor",
            tile_catalog=session_tile_catalog(session),
            room_codes=list(tile_def.room_codes) if tile_def else [],
        )
        if content.get("treasure_summary"):
            tile.treasure_summary = str(content["treasure_summary"])
            tile.treasure_gold = int(content.get("treasure_gold") or 0)
            tile.treasure_items = list(content.get("treasure_items") or [])
            tile.pending_treasure_choice = content.get("pending_treasure_choice")
            tile.treasure_claimed = False
        if content.get("trap_key"):
            tile.trap_key = str(content["trap_key"])
            tile.trap_level = int(content.get("trap_level") or hcl)
        if content.get("special_event_key"):
            tile.special_event_key = content["special_event_key"]
        if content.get("special_event_summary"):
            tile.special_event_summary = content["special_event_summary"]
        if content.get("choices"):
            session.pending_tile_content_choice_tile_id = tile.id
        self._seed_tile_features(tile, hcl, show_rolls=show_rolls, session=session)
        self._resolve_event_foes(session, tile, show_rolls=show_rolls)
        if content.get("auto_secret_passage"):
            self._offer_secret_passage(session, tile, show_rolls=show_rolls)
        return tile

    def _generated_placement_attempt_keys(self, session: SessionState) -> list[str]:
        valid_generated = self._valid_generated_tile_keys(session)
        if not valid_generated:
            return []
        oversized_only = (
            session.fd_side_sheet_active
            and session.fd_side_sheet_kind == "citadel"
            and session.fd_citadel_type == "ghost_citadel"
        )
        if oversized_only:
            tiles = self._tiles_for_session(session)
            large_keys = sorted(
                valid_generated,
                key=lambda key: (
                    -(tiles[key].footprint_width * tiles[key].footprint_height)
                    if tiles.get(key)
                    else -1
                ),
            )
            threshold = 40
            preferred = [
                key
                for key in large_keys
                if tiles.get(key)
                and tiles[key].footprint_width * tiles[key].footprint_height >= threshold
            ]
            pool = preferred or large_keys
            first = pool[0]
            attempts = [first]
            remaining = [key for key in pool if key != first]
            if len(remaining) < len(valid_generated) - 1:
                remaining.extend(key for key in valid_generated if key not in attempts and key not in remaining)
            random.shuffle(remaining)
            attempts.extend(remaining)
            return attempts[: len(valid_generated)]
        first = self._roll_generated_tile_key(session)
        attempts = [first]
        remaining = [key for key in valid_generated if key != first]
        random.shuffle(remaining)
        attempts.extend(remaining)
        return attempts[: len(valid_generated)]

    def _valid_generated_tile_keys(self, session: SessionState) -> list[str]:
        tiles = self._tiles_for_session(session)
        return sorted(key for key in tiles if len(key) == 2 and key[0] in "123456" and key[1] in "123456")

    def _fallback_dead_end_placement(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
    ) -> Placement | None:
        entered_from = OPPOSITE[origin_exit.direction]
        tile_def = TileDefinition(
            key="11",
            name="Emergency Dead End",
            tile_type="corridor",
            footprint_width=1,
            footprint_height=1,
            walkable=["1"],
            cell_shapes=["F"],
            exits=[
                {
                    "id": "fallback-entry",
                    "direction": entered_from,
                    "kind": origin_exit.kind,
                    "x": 0,
                    "y": 0,
                    "span": 1,
                }
            ],
            implementation_status="engine-fallback",
        )
        exits = self._rotated_exits(tile_def, 0)
        matching = exits[0]
        matching.status = "open"
        x, y = self._aligned_origin(origin, origin_exit, matching, 1, 1)
        if not self._placement_blocked(session, x, y, 1, 1, tile_def, 0, origin, origin_exit):
            placement = Placement(
                x=x,
                y=y,
                rotation=0,
                exits=exits,
                walkable=["1"],
                cell_shapes=["F"],
                visible=["1"],
                truncated=True,
            )
            return placement if self._placement_displayed_exit_count(session, placement) > 0 else None
        placement = self._truncated_placement(session, x, y, 1, 1, tile_def, 0, origin, origin_exit, exits, matching)
        if placement is None:
            return None
        return placement if self._placement_displayed_exit_count(session, placement) > 0 else None

    def _roll_content(
        self,
        session: SessionState,
        tile_type: str,
        hcl: int,
        *,
        tile_def: TileDefinition | None = None,
    ) -> dict:
        if is_fd_ruleset(session) and session.fd_side_sheet_active:
            kind = session.fd_side_sheet_kind or "ruins"
            return self._content(
                "fd_side_sheet",
                f"{kind.title()} side-sheet room.",
                ["Side dungeon"],
                [],
            )
        if is_fd_ruleset(session):
            return self._roll_fd_content(session, tile_type, hcl)
        from .abyss_tables import is_abyss_profile

        if is_abyss_profile(session):
            return self._roll_abyss_content(session, tile_type, hcl, tile_def=tile_def)
        roll = roll_2d6()
        outcome = self.table_roller.lookup_room_content(roll, tile_type)
        if outcome is None:
            return self._content("empty", "The area is quiet.", [], [], roll=roll)
        if roll == 5 and tile_type == "room":
            if session.environment == "fungal_grottoes":
                return self._content(
                    "searchable",
                    "This tile is empty and may be searched. You find a secret passage.",
                    ["Searchable", "Secret Passage"],
                    [],
                    roll=roll,
                    auto_secret_passage=True,
                )
            description = "This tile is empty and may be searched."
            if session.environment == "caverns":
                description += " Roll on the Caverns Special Feature Table."
            else:
                description += " Roll on the Special Feature Table."
            return self._content(
                "special_feature",
                description,
                ["Searchable", "Special Feature"],
                [],
                roll=roll,
            )
        enemies: list[EnemyState] = []
        if outcome.enemy_category:
            enemies = self._roll_enemy(session, outcome.enemy_category, hcl, required_tags=outcome.enemy_tags or None)
        return self._content(
            outcome.key,
            outcome.description,
            list(outcome.objects),
            enemies,
            roll=roll,
            choices=list(outcome.choices),
        )

    def _roll_abyss_content(
        self,
        session: SessionState,
        tile_type: str,
        hcl: int,
        *,
        tile_def: TileDefinition | None = None,
    ) -> dict:
        from .abyss_tables import lookup_abyss_table_row

        roll = roll_2d6()
        row = lookup_abyss_table_row("abyss_room_content_table", roll)
        if row is None:
            return self._content("abyss_empty", "The Abyss chamber is quiet and searchable.", ["Searchable"], [], roll=roll)
        effect = str(row.get("effect") or "")
        name = str(row.get("name") or row.get("key") or "Abyss content")
        summary = str(row.get("summary") or "")
        description = f"Abyss room content: {name} (2d6={roll}). {summary}".strip()
        if effect == "spawn" or (effect == "spawn_room_only" and tile_type == "room"):
            enemies, subdesc = self._roll_abyss_monster_row(
                session,
                str(row.get("monster_table") or ""),
                str(row.get("category") or "minions"),
            )
            if subdesc:
                description = f"{description} {subdesc}"
            from .abyss_campaign import check_kidnap_minions

            kidnap_log = check_kidnap_minions(session, tile_type, enemies, show_rolls=True)
            if kidnap_log:
                description = f"{description} {' '.join(kidnap_log)}"
            return self._content(str(row.get("key") or "abyss_encounter"), description, ["Abyss encounter"], enemies, roll=roll)
        if effect == "spawn_room_only":
            return self._content("abyss_empty", f"{description} Corridor result: empty and searchable.", ["Searchable"], [], roll=roll)
        if effect == "trap_corridor_weird_room":
            if tile_type == "room":
                enemies, subdesc = self._roll_abyss_monster_row(session, "abyss_weird_table", "weird")
                if subdesc:
                    description = f"{description} {subdesc}"
                return self._content("abyss_weird", description, ["Abyss weird monster"], enemies, roll=roll)
            trap = self._roll_abyss_subtable("abyss_trap_table")
            if trap:
                description = f"{description} Trap: {trap.get('name')} - {trap.get('summary')}"
            return self._content(
                "abyss_trap",
                description,
                ["Abyss Trap"],
                [],
                roll=roll,
                extra=self._abyss_trap_extra(trap, tile_type, hcl),
            )
        if effect in {"boss", "boss_or_dragon"}:
            table_name = "abyss_boss_table"
            key = "abyss_boss"
            if effect == "boss_or_dragon" and tile_type == "room" and self._is_large_abyss_room(session, tile_def):
                table_name = "abyss_dragon_table"
                key = "abyss_dragon"
            from .abyss_campaign import should_force_enchantment_dragon_final

            if table_name == "abyss_boss_table" and should_force_enchantment_dragon_final(session):
                table_name = "abyss_dragon_table"
                key = "abyss_dragon"
            enemies, subdesc = self._roll_abyss_monster_row(session, table_name, "boss")
            if subdesc:
                description = f"{description} {subdesc}"
            if table_name == "abyss_boss_table":
                final_roll = roll_d6() + session.major_foes_defeated_this_adventure
                description = f"{description} Final Boss check: d6 + defeated bosses = {final_roll}."
                if final_roll >= 6 and not dungeon_has_final_boss(session):
                    for enemy in enemies:
                        if enemy.category == "boss":
                            enemy.tags.append("final_boss")
                    session.final_boss_designated = True
                    description = f"{description} This is the Final Boss."
                elif dungeon_has_final_boss(session):
                    description = f"{description} A Final Boss is already designated."
            return self._content(key, description, ["Abyss boss"], enemies, roll=roll)
        if effect in {"treasure", "trap_treasure"}:
            extra = self._roll_abyss_treasure_extra()
            objects = ["Abyss Treasure"]
            if effect == "trap_treasure":
                trap = self._roll_abyss_subtable("abyss_trap_table")
                trap_text = f" Trap: {trap.get('name')} - {trap.get('summary')}" if trap else ""
                description = f"{description}{trap_text}"
                objects.insert(0, "Abyss Trap")
                extra.update(self._abyss_trap_extra(trap, tile_type, hcl))
            if effect == "treasure" and roll_d6() == 6:
                enemies, subdesc = self._roll_abyss_monster_row(session, "abyss_boss_table", "boss")
                if subdesc:
                    description = f"{description} Guarded treasure: {subdesc}"
                return self._content("abyss_guarded_treasure", description, objects, enemies, roll=roll, extra=extra)
            return self._content(str(row.get("key") or "abyss_treasure"), description, objects, [], roll=roll, extra=extra)
        if effect == "special_feature":
            if tile_type != "room":
                return self._content("abyss_empty", f"{description} Corridor result: empty and searchable.", ["Searchable"], [], roll=roll)
            feature = self._roll_abyss_subtable("abyss_special_feature_table")
            extra_text = f" Feature: {feature.get('name')} - {feature.get('summary')}" if feature else ""
            return self._content(
                "abyss_special_feature",
                f"{description}{extra_text}",
                ["Abyss Special Feature"],
                [],
                roll=roll,
                extra={"special_event_key": feature.get("key"), "special_event_summary": feature.get("summary")} if feature else None,
            )
        if effect in {"unique_event", "empty_unique"}:
            if effect == "empty_unique" and roll_d6() < 5:
                return self._content("abyss_empty", f"{description} No unique event appears; the area is searchable.", ["Searchable"], [], roll=roll)
            event = self._roll_abyss_subtable("abyss_unique_event_table")
            if event:
                description = f"{description} Event: {event.get('name')} - {event.get('summary')}"
                return self._content(
                    "abyss_unique_event",
                    description,
                    ["Abyss Unique Event"],
                    [],
                    roll=roll,
                    extra={"special_event_key": event.get("key"), "special_event_summary": event.get("summary")},
                )
        return self._content(str(row.get("key") or "abyss_empty"), description, ["Searchable"], [], roll=roll)

    def _abyss_trap_extra(self, trap: dict | None, tile_type: str, hcl: int) -> dict:
        if not trap:
            return {}
        key = f"abyss_{trap.get('key')}"
        if key == "abyss_dart_shooting_mechanism":
            level = roll_die(8) + 3
        elif key == "abyss_giant_metal_ball":
            level = 7 if tile_type == "room" else 9
        elif key == "abyss_crocodile_pit":
            level = 6
        elif key == "abyss_guillotine":
            level = roll_d6() + 2
        elif key in {"abyss_electrical_blast", "abyss_steel_spear"}:
            level = 7
        else:
            level = max(1, hcl)
        return {"trap_key": key, "trap_level": level}

    def _roll_abyss_subtable(self, table_name: str) -> dict | None:
        from .abyss_tables import lookup_abyss_table_row

        return lookup_abyss_table_row(table_name, roll_d6())

    def _is_large_abyss_room(self, session: SessionState, tile_def: TileDefinition | None) -> bool:
        if tile_def is None or tile_def.tile_type != "room":
            return False
        walkable = sum(row.count("1") for row in tile_def.walkable or [])
        area = max(1, tile_def.footprint_width) * max(1, tile_def.footprint_height)
        return walkable >= 16 or area >= 36

    def _roll_abyss_treasure_extra(self) -> dict:
        from .abyss_tables import lookup_abyss_table_row

        roll = roll_die(8)
        row = lookup_abyss_table_row("abyss_treasure_table", roll)
        if row is None:
            row = lookup_abyss_table_row("abyss_treasure_table", 0) or {}
        gold = 0
        formula = row.get("gold_formula")
        if formula:
            gold = self._resolve_abyss_formula(str(formula))
        items = list(row.get("items") or [])
        summary = f"Abyss Treasure d8={roll}: {row.get('summary', 'No treasure found.')}"
        if gold:
            summary = f"{summary} ({gold}gp)"
        choice = None
        if roll == 1:
            choice = "abyss_gold_or_weapon"
        elif roll == 2:
            choice = "abyss_gold_or_useful"
        elif roll == 5:
            choice = "abyss_jewelry_or_useful"
        elif roll == 8:
            choice = "abyss_defense_or_gold"
        if roll in {6, 7, 8}:
            items = [self._roll_abyss_magic_or_defense_item(defense=roll in {7, 8})]
        return {"treasure_summary": summary, "treasure_gold": gold, "treasure_items": items, "pending_treasure_choice": choice}

    def _roll_abyss_useful_item(self) -> str:
        roll = roll_d6()
        if roll == 1:
            return "Abyss Useful Stuff: rope, lantern, or hand weapon"
        if roll == 2:
            return f"{roll_d6()} blessed stakes"
        if roll == 3:
            return "Wolvesbane"
        if roll == 4:
            return "Silver weapon"
        if roll == 5:
            return "Blessed horseshoe"
        return f"{roll_d3()} loaves of elven bread"

    def _roll_abyss_magic_or_defense_item(self, *, defense: bool) -> str:
        if defense:
            roll = roll_d6()
            names = {
                1: "Ring of Defense",
                2: "Cross against Vampires",
                3: "Brownie Ward",
                4: "Magic Shield",
                5: "Elfin Chain Mail",
                6: "Suit of Enchanted Armor",
            }
            return names.get(roll, "Abyss magical defense")
        roll = roll_d6()
        names = {
            1: "Amulet of Protection versus Undead",
            2: "Medallion of Snake Charming",
            3: "Parchment of Banishing",
            4: "Baton of Righteousness",
            5: "Philter of Fire Breathing",
            6: f"Ring of Three Wishes ({roll_d3()} wishes)",
        }
        return names.get(roll, "Abyss magic treasure")

    def _roll_abyss_monster_row(
        self,
        session: SessionState,
        table_name: str,
        category: str,
        *,
        fixed_roll: int | None = None,
    ) -> tuple[list[EnemyState], str]:
        from .abyss_tables import lookup_abyss_table_row

        roll = fixed_roll if fixed_roll is not None else roll_d6()
        row = lookup_abyss_table_row(table_name, roll)
        if row is None:
            return [], f"Abyss {category} roll d6={roll}: no row found."
        enemies = self._abyss_spawn_from_row(session, row, category)
        return enemies, f"Abyss {category} roll d6={roll}: {row.get('name')} - {row.get('summary', '')}"

    def _abyss_spawn_from_row(self, session: SessionState, row: dict, category: str) -> list[EnemyState]:
        enemies: list[EnemyState] = []
        count = max(1, self._resolve_abyss_formula(str(row.get("count", "1"))))
        reaction_table = str(row.get("reaction_table") or "").strip()
        for _ in range(count):
            enemies.append(self._abyss_enemy_from_row(row, category, reaction_table=reaction_table or None))
        leader = row.get("leader")
        leader_chance = int(row.get("leader_chance") or 0)
        if isinstance(leader, dict) and (not leader_chance or roll_d6() <= leader_chance):
            enemies.append(
                self._abyss_enemy_from_row(
                    leader,
                    str(leader.get("category") or "boss"),
                    reaction_table=reaction_table or None,
                    extra_tags=["abyss_leader", "minion_leader"],
                )
            )
        leader_table = row.get("leader_table")
        leader_roll = row.get("leader_roll")
        if leader_table and leader_roll and (not leader_chance or roll_d6() <= leader_chance):
            leader_enemies, _ = self._roll_abyss_monster_row(
                session,
                str(leader_table),
                "boss",
                fixed_roll=int(leader_roll),
            )
            for leader_enemy in leader_enemies[:1]:
                if reaction_table:
                    tag = f"reaction_table:{reaction_table}"
                    if tag not in leader_enemy.tags:
                        leader_enemy.tags.append(tag)
                for tag in ("abyss_leader", "minion_leader"):
                    if tag not in leader_enemy.tags:
                        leader_enemy.tags.append(tag)
                enemies.append(leader_enemy)
        return enemies

    def _abyss_enemy_from_row(
        self,
        row: dict,
        category: str,
        *,
        reaction_table: str | None = None,
        extra_tags: list[str] | None = None,
    ) -> EnemyState:
        level_value = row.get("level", 1)
        level = self._resolve_abyss_formula(str(level_value)) if isinstance(level_value, str) else int(level_value)
        life_value = row.get("life", 1)
        life = self._resolve_abyss_formula(str(life_value)) if isinstance(life_value, str) else int(life_value)
        attacks_value = row.get("attacks", 1)
        attacks = self._resolve_abyss_formula(str(attacks_value)) if isinstance(attacks_value, str) else int(attacks_value)
        tags = [str(tag) for tag in row.get("tags", [])]
        tags.append("abyss")
        if reaction_table:
            tags.append(f"reaction_table:{reaction_table}")
        if extra_tags:
            tags.extend(extra_tags)
        treasure_rolls = int(row.get("treasure_rolls") or 0)
        if treasure_rolls <= 0:
            tags.append("no_treasure")
        else:
            tags.append(f"abyss_treasure_rolls:{treasure_rolls}")
        return EnemyState(
            id=uuid4().hex,
            name=str(row.get("name") or "Abyss Foe"),
            category=category,
            level=max(1, level),
            life=max(1, life),
            max_life=max(1, life),
            attacks=max(0, attacks),
            tags=tags,
            on_hit_effects=list(row.get("on_hit_effects") or []),
            encounter_start_effects=list(row.get("encounter_start_effects") or []),
            per_turn_effects=list(row.get("per_turn_effects") or []),
            special_attacks=list(row.get("special_attacks") or []),
        )

    def _resolve_abyss_formula(self, formula: str) -> int:
        formula = formula.strip().lower().replace(" ", "")
        if "*" in formula:
            total = 1
            for part in formula.split("*"):
                total *= self._resolve_abyss_formula(part)
            return total
        return roll_formula(formula)

    def _roll_fd_content(self, session: SessionState, tile_type: str, hcl: int) -> dict:
        roll = roll_2d6()
        outcome = self.table_roller.lookup_fd_room_content(roll, tile_type)
        if outcome is None:
            return self._content("fd_empty", "The forsaken tunnels are quiet.", [], [], roll=roll)
        if outcome.key == "fd_hallucination" and session.fd_hallucination_content_rolls >= 2:
            session.log.append(
                "Forsaken Depths: third hallucination result — use Event instead (FD p.59)."
            )
            outcome = self.table_roller.lookup_fd_room_content(11, tile_type) or outcome
        if outcome.key == "fd_hallucination":
            session.fd_hallucination_content_rolls += 1
        description = outcome.description
        spawn_row: dict | None = None
        extra: dict = {}
        if outcome.key == "fd_event":
            event_roll = roll_d10()
            event_row = self.table_roller.lookup("fd_event_table", event_roll)
            if event_row:
                name = event_row.get("name") or "Event"
                summary = event_row.get("summary") or event_row.get("result") or ""
                description = f"{description} ({name}; d10={event_roll}). {summary}".strip()
                extra["special_event_key"] = event_row.get("key")
                extra["special_event_summary"] = summary
        elif outcome.subtable:
            sub_roll = roll_d6()
            sub_row = self.table_roller.lookup_fd_subtable_row(outcome.subtable, sub_roll)
            if sub_row:
                spawn_row = sub_row
                name = sub_row.get("name") or sub_row.get("key") or outcome.subtable
                summary = sub_row.get("summary") or sub_row.get("result") or ""
                description = f"{description} ({name}; d6={sub_roll}). {summary}".strip()
        elif outcome.key == "fd_weird":
            table_pick = roll_d6()
            table_name = "fd_citadel_weird_table" if table_pick >= 4 else "fd_weird_table"
            sub_roll = roll_d6()
            sub_row = self.table_roller.lookup_fd_subtable_row(table_name, sub_roll)
            if sub_row:
                spawn_row = sub_row
                name = sub_row.get("name") or "Weird monster"
                summary = sub_row.get("summary") or ""
                table_label = "Citadel Weird" if table_name == "fd_citadel_weird_table" else "Weird"
                description = (
                    f"{description} ({table_label} d6={table_pick}, {name}; d6={sub_roll}). {summary}"
                ).strip()
        elif outcome.key == "fd_boss":
            sub_roll = roll_d6()
            sub_row = self.table_roller.lookup_fd_subtable_row("fd_boss_table", sub_roll)
            if sub_row:
                spawn_row = sub_row
                name = sub_row.get("name") or "Boss"
                summary = sub_row.get("summary") or ""
                description = f"{description} ({name}; d6={sub_roll}). {summary}".strip()
        if outcome.key == "fd_trap" and tile_type == "room" and roll_d6() <= 2:
            description += " A 2-in-6 chance indicates treasure here after the trap is resolved."
        enemies: list[EnemyState] = []
        if spawn_row:
            enemies = self._fd_spawn_from_table_row(session, spawn_row, hcl)
        elif outcome.enemy_category:
            enemies = self._roll_enemy(session, outcome.enemy_category, hcl, required_tags=outcome.enemy_tags or None)
        content = self._content(
            outcome.key,
            description,
            list(outcome.objects),
            enemies,
            roll=roll,
            choices=list(outcome.choices),
        )
        content.update(extra)
        return content

    def _fd_ensure_river_type(self, session: SessionState, *, show_rolls: bool = True) -> None:
        if session.fd_river_type:
            return
        roll = roll_d6()
        row = self.table_roller.lookup_fd_river_type(roll)
        key = row.get("key") if row else "oblivion"
        session.fd_river_type = key  # type: ignore[assignment]
        label = row.get("name") if row else fd_river_type_label(key)
        if show_rolls:
            session.log.append(
                f"River type roll: d6 = {roll} → {label} (FD p.32). All stretches on this river use this type."
            )

    def _fd_on_river_stretch_entered(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        if tile.id in session.fd_river_processed_tile_ids:
            return
        self._fd_ensure_river_type(session, show_rolls=show_rolls)
        apply_river_type_on_stretch_entry(session, show_rolls=show_rolls)
        hcl = self._highest_character_level(session.party)
        apply_flame_river_entry(session, hcl=hcl, show_rolls=show_rolls)
        apply_room_codes_on_stretch_entry(self, session, tile, show_rolls=show_rolls)
        if session.fd_boat_status == "destroyed" or session.fd_travel_mode == "foot":
            if show_rolls:
                session.log.append("The party travels on foot along the river banks (FD p.28).")
        if session.fd_waste_of_time_skip_hazard_stretches > 0:
            session.fd_waste_of_time_skip_hazard_stretches -= 1
            if show_rolls:
                session.log.append(
                    "Waste of Time after-effect — hazard check skipped on this stretch "
                    f"({session.fd_waste_of_time_skip_hazard_stretches} stretch(es) remain, FD p.30)."
                )
            session.fd_river_processed_tile_ids.append(tile.id)
            return
        if session.fd_boatman_luck_active:
            session.fd_boatman_luck_active = False
            if show_rolls:
                session.log.append("Boatman's Luck avoids the first river hazard on this stretch (FD p.19).")
            session.fd_river_processed_tile_ids.append(tile.id)
            return
        chance_roll = roll_d6()
        if chance_roll > 2:
            if show_rolls:
                session.log.append(f"River hazard check: d6 = {chance_roll} — no hazard this stretch (2-in-6).")
            session.fd_river_processed_tile_ids.append(tile.id)
            return
        hazard_roll = roll_d6()
        row = self.table_roller.lookup_fd_river_hazard(hazard_roll)
        if row is None:
            session.fd_river_processed_tile_ids.append(tile.id)
            return
        result = row.get("result") or row.get("key") or "River hazard."
        if show_rolls:
            session.log.append(f"River hazard: 2-in-6 triggered; d6 = {hazard_roll}. {result}")
        key = row.get("key")
        if key == "damaged_boat":
            if session.fd_travel_mode == "foot" or session.fd_boat_status == "destroyed":
                if show_rolls:
                    session.log.append("Damaged Boat hazard — no effect while traveling on foot (FD p.30).")
            else:
                self._fd_apply_damaged_boat(session)
        elif key == "ambush" and row.get("subtable"):
            sub_roll = roll_d6()
            sub_row = self.table_roller.lookup_fd_subtable_row(row["subtable"], sub_roll)
            if sub_row:
                if show_rolls:
                    session.log.append(
                        f"River Encounter roll d6={sub_roll}: {sub_row.get('name', 'Encounter')}. "
                        f"{sub_row.get('summary', '')}"
                    )
                spawned = self._fd_spawn_from_table_row(session, sub_row, hcl)
                if spawned:
                    tile.enemies.extend(spawned)
                    session.log.append(
                        f"River ambush — {len(spawned)} foe group(s) attack with surprise (FD p.30)."
                    )
                    for enemy in spawned:
                        if "surprise" not in enemy.tags:
                            enemy.tags.append("surprise")
                    if session.mode == "exploration":
                        self._announce_encounter(session, tile, show_rolls=show_rolls)
        elif key == "waste_of_time":
            fd_on_waste_of_time_hazard(session, show_rolls=show_rolls)
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)
        elif key == "ghosts_of_the_river":
            resolve_ghosts_of_the_river(session, hcl=hcl, show_rolls=show_rolls)
        elif key == "teleport":
            resolve_river_teleport(self, session, tile, show_rolls=show_rolls)
        elif key == "special_feature":
            apply_special_feature_hazard(session, tile, show_rolls=show_rolls)
            apply_room_codes_on_stretch_entry(self, session, tile, show_rolls=show_rolls)
        session.fd_river_processed_tile_ids.append(tile.id)

    def _fd_spawn_from_table_row(
        self,
        session: SessionState,
        row: dict,
        hcl: int,
    ) -> list[EnemyState]:
        name = row.get("name")
        table_category = row.get("enemy_category")
        if not name or not table_category:
            return []
        table_key = self._resolve_monster_table_key(session, table_category, log_mixed_roll=False)
        monsters = self.rules.monsters()
        table = monsters.get(table_key) or []
        template = next((entry for entry in table if entry.get("name") == name), None)
        if template is None:
            session.log.append(f"Forsaken Depths bestiary missing: {name} ({table_key}).")
            return []
        count_formula = row.get("count") or template.get("count", "1")
        count = max(1, roll_formula(str(count_formula)))
        spawn_category = "boss" if table_category == "horde" else table_category
        serpent_bonus = 0
        if (
            spawn_category == "boss"
            and is_fd_ruleset(session)
            and session.fd_river_type == "serpent"
            and session_tile_catalog(session) == "forsaken_depths_rivers"
        ):
            serpent_bonus = 1
        return self._spawn_from_template_name(
            session,
            table_key=table_key,
            template_name=name,
            count=count,
            hcl=hcl,
            category=spawn_category,
            level_delta_bonus=serpent_bonus,
        )

    def _fd_apply_damaged_boat(self, session: SessionState) -> None:
        if session.fd_boat_status == "ok":
            session.fd_boat_status = "damaged"
            session.log.append("The boat is slightly damaged (FD p.30).")
            return
        session.fd_boat_status = "destroyed"
        session.fd_travel_mode = "foot"
        session.log.append("The boat is destroyed — disembark and continue on foot (FD p.30).")

    def _content(
        self,
        key: str,
        description: str,
        objects: list[str],
        enemies: list[EnemyState],
        roll: int | None = None,
        *,
        choices: list[str] | None = None,
        auto_secret_passage: bool = False,
        extra: dict | None = None,
    ) -> dict:
        content = {"key": key, "description": description, "objects": objects, "enemies": enemies}
        if roll is not None:
            content["roll"] = roll
        if choices:
            content["choices"] = choices
        if auto_secret_passage:
            content["auto_secret_passage"] = True
        if extra:
            content.update(extra)
        return content

    def _select_placement(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
        tile_type: str,
        tile_def: TileDefinition | None,
    ) -> Placement | None:
        entered_from = OPPOSITE[origin_exit.direction]
        footprint_width = tile_def.footprint_width if tile_def else 1
        footprint_height = tile_def.footprint_height if tile_def else 1
        truncation_candidate: Placement | None = None
        truncation_conflicts: set[str] = set()

        if tile_def and tile_def.exits:
            rotations = ROTATIONS[:]
            random.shuffle(rotations)
            for rotation in rotations:
                exits = self._rotated_exits(tile_def, rotation)
                matching_exits = [exit_state for exit_state in exits if exit_state.direction == entered_from]
                random.shuffle(matching_exits)
                width, height = self._rotated_size(footprint_width, footprint_height, rotation)
                for matching in matching_exits:
                    matching.status = "open"
                    x, y = self._aligned_origin(origin, origin_exit, matching, width, height)
                    if not self._placement_blocked(session, x, y, width, height, tile_def, rotation, origin, origin_exit):
                        candidate = Placement(
                            x=x,
                            y=y,
                            rotation=rotation,
                            exits=exits,
                            walkable=self._rotated_walkable(tile_def, rotation),
                            cell_shapes=self._rotated_cell_shapes(tile_def, rotation),
                            visible=self._visible_rows(width, height),
                        )
                        conflicts = self._placement_exit_conflicts(session, candidate, origin, origin_exit, matching.id)
                        if not conflicts and self._placement_displayed_exit_count(session, candidate) > 0:
                            return candidate
                        if self._placement_displayed_exit_count(session, candidate, conflicts) == 0:
                            matching.status = "unexplored"
                            continue
                        if (
                            truncation_candidate is None
                            or self._placement_choice_score(session, candidate, conflicts)
                            > self._placement_choice_score(session, truncation_candidate, truncation_conflicts)
                        ):
                            truncation_candidate = candidate
                            truncation_conflicts = conflicts
                    candidate = self._truncated_placement(
                        session,
                        x,
                        y,
                        width,
                        height,
                        tile_def,
                        rotation,
                        origin,
                        origin_exit,
                        exits,
                        matching,
                    )
                    if candidate is not None:
                        conflicts = self._placement_exit_conflicts(session, candidate, origin, origin_exit, matching.id)
                        if self._placement_displayed_exit_count(session, candidate, conflicts) == 0:
                            matching.status = "unexplored"
                            continue
                        if (
                            truncation_candidate is None
                            or self._placement_choice_score(session, candidate, conflicts)
                            > self._placement_choice_score(session, truncation_candidate, truncation_conflicts)
                        ):
                            truncation_candidate = candidate
                            truncation_conflicts = conflicts
                    matching.status = "unexplored"
            if truncation_candidate is not None:
                self._block_placement_exits(truncation_candidate, truncation_conflicts)
            return truncation_candidate

        rotation = 0
        width, height = self._rotated_size(footprint_width, footprint_height, rotation)
        exits = self._fallback_exits(tile_type, entered_from, width, height)
        matching = next(exit_state for exit_state in exits if exit_state.direction == entered_from)
        x, y = self._aligned_origin(origin, origin_exit, matching, width, height)
        if self._placement_blocked(session, x, y, width, height, tile_def, rotation, origin, origin_exit):
            return self._truncated_placement(
                session,
                x,
                y,
                width,
                height,
                tile_def,
                rotation,
                origin,
                origin_exit,
                exits,
                matching,
            )
        placement = Placement(
            x=x,
            y=y,
            rotation=rotation,
            exits=exits,
            walkable=self._rotated_walkable(tile_def, rotation),
            cell_shapes=self._rotated_cell_shapes(tile_def, rotation),
            visible=self._visible_rows(width, height),
        )
        conflicts = self._placement_exit_conflicts(session, placement, origin, origin_exit, matching.id)
        self._block_placement_exits(placement, conflicts)
        return placement

    def _placement_choice_score(
        self,
        session: SessionState,
        placement: Placement,
        conflict_ids: set[str],
    ) -> tuple[int, int, int, int, int]:
        walkable_count, visible_count, usable_exits = self._placement_score(placement)
        displayed_exits = self._placement_displayed_exit_count(session, placement, conflict_ids)
        return -len(conflict_ids), displayed_exits, walkable_count, visible_count, usable_exits

    def _placement_score(self, placement: Placement) -> tuple[int, int, int]:
        walkable_count = sum(1 for row in placement.walkable for char in row if char != "0")
        visible_count = sum(1 for row in placement.visible for char in row if char != "0")
        usable_exits = sum(1 for exit_state in placement.exits if exit_state.status != "blocked")
        return walkable_count, visible_count, usable_exits

    def _roll_generated_tile_key(self, session: SessionState) -> str:
        tiles = self._tiles_for_session(session)
        for _ in range(20):
            tile_key = roll_tile_key()
            if tile_key in tiles and tile_key[0] in "123456" and tile_key[1] in "123456":
                return tile_key
        valid_generated = [key for key in tiles if key[0] in "123456" and key[1] in "123456"]
        return random.choice(valid_generated)

    def _fallen_in_dungeon(self, session: SessionState) -> list[str]:
        fallen: list[str] = []
        for tile in session.map_state.tiles:
            for character_id in tile.fallen_character_ids:
                if character_id not in fallen:
                    fallen.append(character_id)
        return fallen

    def _entrance_tile(self, session: SessionState) -> TileState:
        for tile in session.map_state.tiles:
            if tile.content_key == "entrance":
                return tile
        return min(session.map_state.tiles, key=lambda item: (item.y, item.x))

    def _heal_living_party(self, session: SessionState) -> list[str]:
        healed_names: list[str] = []
        for member in session.party:
            if member.current_life <= 0:
                continue
            if member.current_life < member.max_life:
                healed_names.append(member.name)
            member.current_life = member.max_life
        return healed_names

    def _log_between_foray_refresh(self, session: SessionState, healed_names: list[str]) -> None:
        if healed_names:
            session.log.append(f"Living heroes recover to full Life: {', '.join(healed_names)}.")
        else:
            session.log.append("Living heroes are ready to return when preparations are done.")
        session.log.append("Spells, prayers, rest, and per-foray class resources refresh at camp.")

    def _retreat_from_dungeon(
        self,
        session: SessionState,
        fallen_ids: list[str],
        *,
        show_rolls: bool,
    ) -> None:
        entrance = self._entrance_tile(session)
        session.map_state.current_tile_id = entrance.id
        session.current_tile_entry_exit_id = None
        self._refresh_tile_connections(session, entrance)
        self._initialize_outside_entrance(entrance)
        session.camped_outside = True
        session.summary = []
        self._reset_between_foray_resources(session)
        healed_names = self._heal_living_party(session)
        names = [
            member.name
            for member in session.party
            if member.character_id in fallen_ids
        ]
        label = ", ".join(names) if names else f"{len(fallen_ids)} hero(es)"
        session.log.append(
            f"The party retreats to camp outside the dungeon. Fallen comrades remain inside: {label}."
        )
        session.log.append(
            "The explored dungeon persists. Regroup and re-enter to recover them. "
            "Items left on unattended bodies may be stolen (5-in-6)."
        )
        self._log_between_foray_refresh(session, healed_names)
        self._steal_from_unattended_bodies(session, show_rolls=show_rolls)

    def _camp_outside_with_recovery(self, session: SessionState) -> None:
        entrance = self._entrance_tile(session)
        session.map_state.current_tile_id = entrance.id
        session.current_tile_entry_exit_id = None
        self._refresh_tile_connections(session, entrance)
        self._initialize_outside_entrance(entrance)
        session.mode = "exploration"
        session.camped_outside = True
        session.summary = []
        self._reset_between_foray_resources(session)
        healed_names = self._heal_living_party(session)
        names = [
            member.name
            for member in session.party
            if member.character_id in session.fallen_outside_character_ids
        ]
        label = ", ".join(names) if names else f"{len(session.fallen_outside_character_ids)} hero(es)"
        session.log.append(f"The party is camped outside with fallen comrades awaiting recovery: {label}.")
        session.log.append(
            "A Resurrection Ritual costs 1000gp and restores full Life on success "
            "(d6 <= Level; L6+ automatic). The party may re-enter the dungeon or lay a body to rest."
        )
        self._log_between_foray_refresh(session, healed_names)

    def _reset_between_foray_resources(self, session: SessionState) -> None:
        self._clear_combat_statuses(session)
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

    def _camp_outside_to_return(self, session: SessionState) -> None:
        entrance = self._entrance_tile(session)
        session.map_state.current_tile_id = entrance.id
        session.current_tile_entry_exit_id = None
        self._refresh_tile_connections(session, entrance)
        self._initialize_outside_entrance(entrance)
        session.mode = "exploration"
        session.camped_outside = True
        session.summary = []
        self._reset_between_foray_resources(session)
        healed_names = self._heal_living_party(session)
        explored = len(session.map_state.tiles)
        session.log.append(
            f"The party leaves the dungeon and makes camp outside. The explored {explored} "
            f"map element{'s' if explored != 1 else ''} remain ready for return."
        )
        self._log_between_foray_refresh(session, healed_names)
        session.log.append("Buy gear, train, regroup, or use the home bank before re-entering the dungeon.")

    def _return_to_dungeon_from_camp(self, session: SessionState) -> None:
        if session.mode != "exploration":
            session.log.append("Resolve the current encounter before returning to the dungeon.")
            return
        entrance = self._entrance_tile(session)
        session.map_state.current_tile_id = entrance.id
        session.current_tile_entry_exit_id = None
        self._refresh_tile_connections(session, entrance)
        self._initialize_outside_entrance(entrance)
        if not session.camped_outside:
            session.log.append("The party is already inside the dungeon.")
            return
        session.camped_outside = False
        from .courtship_apothecary_brew import unlock_apothecary_brew_after_encounter

        unlock_apothecary_brew_after_encounter(session)
        session.summary = []
        from .hirelings import reset_hirelings_for_new_foray

        reset_hirelings_for_new_foray(session)
        from .abyss_campaign import on_new_foray

        session.log.extend(on_new_foray(session))
        if session.imported_entrance_pending:
            session.imported_entrance_pending = False
            from .adventure_session import enter_imported_entrance_tile

            enter_imported_entrance_tile(self, session, entrance, show_rolls=True)
        session.log.append("The party enters the dungeon at the entrance.")

    def _steal_from_unattended_bodies(self, session: SessionState, *, show_rolls: bool) -> None:
        for character_id in self._fallen_in_dungeon(session):
            member = next((item for item in session.party if item.character_id == character_id), None)
            if member is None or not member.inventory:
                continue
            roll = roll_d6()
            if roll >= 6:
                if show_rolls:
                    session.log.append(f"No theft from {member.name}'s body (d6 = {roll}).")
                continue
            stolen = member.inventory.pop(0)
            if show_rolls:
                session.log.append(
                    f"Loot stolen from {member.name}'s unattended body: {stolen} (d6 = {roll}, need 6 to avoid)."
                )
            else:
                session.log.append(f"Loot stolen from {member.name}'s unattended body: {stolen}.")

    def _complete_dungeon(self, session: SessionState) -> None:
        if session.level_up_spell_pending_character_id:
            pending = next(
                (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
                None,
            )
            name = pending.name if pending else "the hero"
            session.log.append(f"Choose a spell for {name} before completing or abandoning the adventure.")
            return
        if session.xp_rolls_pending > 0 and session.xp_system == "classical":
            session.log.append(
                f"{session.xp_rolls_pending} unassigned XP roll(s) remain. Bank them to a hero "
                "or spend them before completing or abandoning the adventure."
            )
            return
        if session.rescued_prisoner_active and session.prisoner_reward_choice is None:
            session.log.append(
                "The rescued prisoner must reach the surface. Choose their reward "
                "(magic item + treasure roll, or double held gp) before leaving the dungeon."
            )
            return
        if session.rescued_prisoner_active:
            self._apply_prisoner_exit_reward(session)
        from .forsaken_depths_quest import resolve_fd_lady_in_black_oracle_on_exit

        resolve_fd_lady_in_black_oracle_on_exit(session, show_rolls=True)
        from .abyss_campaign import maybe_trigger_exit_ambush

        if maybe_trigger_exit_ambush(self, session, self._current_tile(session)):
            return
        session.mode = "complete"
        session.camped_outside = False
        explored = len(session.map_state.tiles)
        survivors = [member for member in session.party if member.current_life > 0]
        if session.xp_system == "slow_and_sure" and survivors:
            target = survivors[0]
            self._complete_level_up(session, target)
            session.log.append(f"Slow and Sure: {target.name} gains 1 Level for completing the adventure.")
        self._reset_between_foray_resources(session)
        from .hirelings import clear_hirelings_on_dungeon_exit

        clear_hirelings_on_dungeon_exit(session)
        for member in session.party:
            if member.current_life > 0:
                member.current_life = member.max_life
        boss_note = " Final Boss slain." if session.final_boss_defeated else ""
        session.summary = [
            f"Explored {explored} map element{'s' if explored != 1 else ''}.{boss_note}",
            f"{len(survivors)} of {len(session.party)} party members left the dungeon.",
            "Between adventures, surviving heroes fully heal and keep treasure already recorded on their sheets.",
        ]
        if session.adventure_type == "imported":
            quest = session.active_quest
            if quest and not quest.completed:
                session.summary.insert(0, "Quest left incomplete.")
            elif quest and quest.completed:
                session.summary.insert(0, "Quest objective complete.")
            log_imported_departure_narrative(session)
        from .weapon_finishes import tick_leafsteel_after_adventure

        for member in session.party:
            for line in tick_leafsteel_after_adventure(member):
                session.log.append(line)
        from .fungal_rare_items import expire_unused_healers_chanterelle, expire_white_angel_mushrooms

        session.log.extend(expire_white_angel_mushrooms(session.party))
        session.log.extend(expire_unused_healers_chanterelle(session.party))
        session.log.append("The party leaves the dungeon. Surviving heroes fully heal between adventures.")
        session.secret_yummy_meal_active = False
        session.log.extend(heal_madness_on_dungeon_exit(session))
        session.log.append("Spells, prayers, rest, and per-adventure class resources refresh between adventures.")

    def _resolve_monster_table_key(
        self,
        session: SessionState,
        category: str,
        *,
        log_mixed_roll: bool = True,
    ) -> str:
        monsters = self.rules.monsters()
        if is_fd_ruleset(session):
            fd_key = f"fd_{category}"
            if fd_key in monsters:
                return fd_key
        use_fiendish, mixed_roll = resolve_use_fiendish_foes_table(
            session.fiendish_foes_enabled,
            eligible=party_fiendish_foes_eligible(session.party),
        )
        if log_mixed_roll and session.fiendish_foes_enabled and mixed_roll is not None:
            label = "Fiendish Foes" if use_fiendish else "standard"
            session.log.append(
                f"Fiendish Foes mixed roll: d6 = {mixed_roll} -> {label} {category} table (EE p.180)."
            )
        return resolve_monster_table_key(
            self.rules.monsters(),
            session,
            category,
            use_fiendish=use_fiendish,
        )

    def _roll_enemy(
        self,
        session: SessionState,
        category: str,
        hcl: int,
        *,
        required_tags: list[str] | None = None,
        wandering: bool = False,
    ) -> list[EnemyState]:
        monsters = self.rules.monsters() if self.rules is not None else {}
        table_key = self._resolve_monster_table_key(session, category)
        table = monsters.get(table_key) or monsters.get(category) or monsters["vermin"]
        if wandering:
            eligible = [template for template in table if not template_never_wandering(template)]
            if eligible:
                table = eligible
            else:
                return []
        if required_tags:
            filtered = [
                template
                for template in table
                if all(tag in template.get("tags", []) for tag in required_tags)
            ]
            if filtered:
                table = filtered
        quest = session.active_quest
        quest_target = getattr(quest, "boss_target_name", None)
        if (
            category == "boss"
            and quest is not None
            and quest.key == "bring_head"
            and quest.boss_slay_pending
            and quest_target
        ):
            target_matches = [template for template in table if template.get("name") == quest_target]
            if target_matches:
                table = target_matches
        template = random.choice(table)
        count = max(1, roll_formula(str(template.get("count", "1"))))
        level = max(1, hcl + int(template.get("level_delta", 0)))
        fiendish_spawn = table_key.startswith("fiendish_foes")
        enemies: list[EnemyState] = []
        for _ in range(count):
            life = _parse_monster_life(template.get("life", 1), hcl)
            attacks = _parse_monster_attacks(template.get("attacks", 1), hcl)
            tags = template_surprise_tags(template) + template_weapon_allow_tags(template) + template_combat_tags(template)
            if wandering:
                tags.append("wandering_spawn")
            if fiendish_spawn:
                tags.append("fiendish")
            power_tag = roll_random_power_tag(template)
            if power_tag:
                tags.append(power_tag)
            enemies.append(
                EnemyState(
                    id=uuid4().hex,
                    name=template["name"],
                    category=category,
                    level=level,
                    life=life,
                    max_life=life,
                    attacks=attacks,
                    tags=tags,
                    on_hit_effects=template_on_hit_effects(template),
                    encounter_start_effects=template_encounter_start_effects(template),
                    per_turn_effects=template_per_turn_effects(template),
                    special_attacks=template_special_attacks(template),
                )
            )
        return enemies

    def _spawn_from_template_name(
        self,
        session: SessionState,
        *,
        table_key: str,
        template_name: str,
        count: int,
        hcl: int,
        category: str,
        level_delta_bonus: int = 0,
    ) -> list[EnemyState]:
        monsters = self.rules.monsters()
        table = monsters.get(table_key) or monsters.get(category) or []
        template = next((entry for entry in table if entry.get("name") == template_name), None)
        if template is None:
            return []
        level = max(1, hcl + int(template.get("level_delta", 0)) + level_delta_bonus)
        fiendish_spawn = table_key.startswith("fiendish_foes")
        enemies: list[EnemyState] = []
        for _ in range(max(1, count)):
            life = _parse_monster_life(template.get("life", 1), hcl)
            attacks = _parse_monster_attacks(template.get("attacks", 1), hcl)
            tags = template_surprise_tags(template) + template_weapon_allow_tags(template) + template_combat_tags(template)
            if fiendish_spawn:
                tags.append("fiendish")
            power_tag = roll_random_power_tag(template)
            if power_tag:
                tags.append(power_tag)
            enemies.append(
                EnemyState(
                    id=uuid4().hex,
                    name=template["name"],
                    category=category,
                    level=level,
                    life=life,
                    max_life=life,
                    attacks=attacks,
                    tags=tags,
                    on_hit_effects=template_on_hit_effects(template),
                    encounter_start_effects=template_encounter_start_effects(template),
                    per_turn_effects=template_per_turn_effects(template),
                    special_attacks=template_special_attacks(template),
                )
            )
        return enemies

    def _rotated_exits(self, tile_def: TileDefinition, rotation: int) -> list[ExitState]:
        width, height = self._rotated_size(tile_def.footprint_width, tile_def.footprint_height, rotation)
        exits: list[ExitState] = []
        for exit_def in tile_def.exits:
            direction = self._rotate_direction(exit_def.direction, rotation)
            cells = [
                self._rotate_cell(x, y, tile_def.footprint_width, tile_def.footprint_height, rotation)
                for x, y in self._exit_cells(
                    exit_def.x,
                    exit_def.y,
                    exit_def.direction,
                    exit_def.span,
                    tile_def.footprint_width,
                    tile_def.footprint_height,
                )
            ]
            x, y, span = self._exit_geometry_from_cells(cells, direction)
            offset = self._exit_offset(direction, x, y)
            exits.append(
                ExitState(
                    id=exit_def.id,
                    label=exit_def.label,
                    direction=direction,
                    kind=exit_def.kind,
                    x=x,
                    y=y,
                    span=span,
                    offset=offset,
                    position=self._position_from_offset(offset, direction, width, height),
                    dungeon_exit=exit_def.dungeon_exit,
                    status="unexplored",
                )
            )
        return exits

    def _starting_exits(
        self,
        tile_key: str,
        tile_def: TileDefinition | None,
        width: int,
        height: int,
        *,
        ensure_dungeon_exit: bool = False,
    ) -> list[ExitState]:
        if tile_def and tile_def.exits:
            exits = self._rotated_exits(tile_def, 0)
            if ensure_dungeon_exit and not any(exit_state.dungeon_exit for exit_state in exits):
                exits.append(
                    self._new_synthetic_dungeon_exit(
                        tile_key,
                        exits,
                        width,
                        height,
                    )
                )
            return exits

        return [
            self._new_exit(direction="north", kind="passage", width=width, height=height),
            self._new_exit(direction="east", kind="door", width=width, height=height),
            self._new_exit(direction="west", kind="door", width=width, height=height),
            self._new_exit(
                direction="south",
                kind="passage",
                width=width,
                height=height,
                dungeon_exit=True,
                exit_id=f"{tile_key}-dungeon-exit",
            ),
        ]

    def _new_synthetic_dungeon_exit(
        self,
        tile_key: str,
        exits: list[ExitState],
        width: int,
        height: int,
    ) -> ExitState:
        """Add an outside exit to authored start tiles that do not include one."""
        used_directions = {exit_state.direction for exit_state in exits}
        direction = next(
            (item for item in ("south", "north", "west", "east") if item not in used_directions),
            "south",
        )
        existing_ids = {exit_state.id for exit_state in exits}
        exit_id = f"{tile_key}-dungeon-exit"
        if exit_id in existing_ids:
            exit_id = uuid4().hex
        return self._new_exit(
            direction=direction,
            kind="passage",
            width=width,
            height=height,
            dungeon_exit=True,
            exit_id=exit_id,
            label="Dungeon Exit",
        )

    def _ensure_entrance_dungeon_exit(self, entrance: TileState) -> bool:
        if entrance.content_key != "entrance":
            return False
        if any(exit_state.dungeon_exit for exit_state in entrance.exits):
            return False
        width, height = self._rotated_size(
            entrance.footprint_width,
            entrance.footprint_height,
            entrance.rotation,
        )
        entrance.exits.append(
            self._new_synthetic_dungeon_exit(
                entrance.tile_key,
                entrance.exits,
                width,
                height,
            )
        )
        return True

    def _fallback_exits(self, tile_type: str, entered_from: str, width: int, height: int) -> list[ExitState]:
        directions = CARDINAL_DIRECTION_ORDER[:]
        random.shuffle(directions)
        exits = [
            self._new_exit(
                direction=entered_from,
                kind="passage",
                width=width,
                height=height,
                status="open",
            )
        ]
        extra_count = roll_d6() // (2 if tile_type == "room" else 3)
        for direction in directions:
            if direction == entered_from:
                continue
            if len(exits) >= extra_count + 1:
                break
            kind = "door" if roll_d6() >= 4 else "passage"
            exits.append(self._new_exit(direction=direction, kind=kind, width=width, height=height))
        return exits

    def _new_exit(
        self,
        direction: str,
        kind: str,
        width: int,
        height: int,
        status: str = "unexplored",
        dungeon_exit: bool = False,
        exit_id: str | None = None,
        label: str = "",
        span: int = 1,
    ) -> ExitState:
        x, y = self._default_entry_cell(direction, width, height)
        offset = self._exit_offset(direction, x, y)
        return ExitState(
            id=exit_id or uuid4().hex,
            label=label,
            direction=direction,
            kind=kind,
            x=x,
            y=y,
            span=max(1, min(span, self._max_exit_span(direction, x, y, width, height))),
            offset=offset,
            position=self._position_from_offset(offset, direction, width, height),
            dungeon_exit=dungeon_exit,
            status=status,
        )

    def _default_entry_cell(self, direction: str, width: int, height: int) -> tuple[int, int]:
        if direction == "northeast":
            return width - 1, 0
        if direction == "southeast":
            return width - 1, height - 1
        if direction == "southwest":
            return 0, height - 1
        if direction == "northwest":
            return 0, 0
        offset = max(0, self._side_length(direction, width, height) // 2)
        if direction in {"north", "south"}:
            return min(offset, width - 1), 0 if direction == "north" else height - 1
        return 0 if direction == "west" else width - 1, min(offset, height - 1)

    def _exit_geometry_from_cells(
        self,
        cells: list[tuple[int, int]],
        direction: str,
    ) -> tuple[int, int, int]:
        if not cells:
            return 0, 0, 1
        cell_set = set(cells)
        step_x, step_y = EXIT_SPAN_STEPS[direction]
        for start_x, start_y in cells:
            generated = {
                (start_x + index * step_x, start_y + index * step_y)
                for index in range(len(cells))
            }
            if generated == cell_set:
                return start_x, start_y, len(cells)
        return cells[0][0], cells[0][1], 1

    def _rotate_cell(self, x: int, y: int, width: int, height: int, rotation: int) -> tuple[int, int]:
        turns = (rotation // 90) % 4
        if turns == 1:
            return height - 1 - y, x
        if turns == 2:
            return width - 1 - x, height - 1 - y
        if turns == 3:
            return y, width - 1 - x
        return x, y

    def _aligned_origin(
        self,
        origin: TileState,
        origin_exit: ExitState,
        entry_exit: ExitState,
        width: int,
        height: int,
    ) -> tuple[int, int]:
        _, outside = self._exit_edge(origin, origin_exit)
        x = max(0, min(entry_exit.x, width - 1))
        y = max(0, min(entry_exit.y, height - 1))
        return outside[0] - x, outside[1] - y

    def _exit_edge(self, tile: TileState, exit_state: ExitState) -> tuple[tuple[int, int], tuple[int, int]]:
        if self._uses_authored_exit_portal(tile, exit_state):
            return self._authored_exit_edge(tile, exit_state)
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        walkable = self._state_rows(tile.walkable, width, height, "1")
        visible = self._state_rows(tile.visible, width, height, "1")
        local_x, local_y = self._exit_cells(
            exit_state.x,
            exit_state.y,
            exit_state.direction,
            exit_state.span,
            width,
            height,
        )[0]
        inside, outside, _ = self._trace_exit_portal(
            local_x,
            local_y,
            exit_state.direction,
            width,
            height,
            walkable,
            visible,
        )
        return (tile.x + inside[0], tile.y + inside[1]), (tile.x + outside[0], tile.y + outside[1])

    def _uses_authored_exit_portal(self, tile: TileState, exit_state: ExitState) -> bool:
        if exit_state.dungeon_exit:
            return False
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        walkable = self._state_rows(tile.walkable, width, height, "1")
        dx, dy = DIRECTIONS[exit_state.direction]
        for local_x, local_y in self._exit_cells(
            exit_state.x,
            exit_state.y,
            exit_state.direction,
            exit_state.span,
            width,
            height,
        ):
            if walkable[local_y][local_x] == "0":
                inside_x = local_x - dx
                inside_y = local_y - dy
                if (
                    0 <= inside_x < width
                    and 0 <= inside_y < height
                    and walkable[inside_y][inside_x] != "0"
                ):
                    return True
            target_x = local_x + dx
            target_y = local_y + dy
            if 0 <= target_x < width and 0 <= target_y < height and walkable[target_y][target_x] == "0":
                if self._is_entrance_tile(tile):
                    return True
                next_x = target_x + dx
                next_y = target_y + dy
                if not (0 <= next_x < width and 0 <= next_y < height):
                    return True
        return False

    def _authored_exit_edge(self, tile: TileState, exit_state: ExitState) -> tuple[tuple[int, int], tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        local_x, local_y = self._exit_cells(
            exit_state.x,
            exit_state.y,
            exit_state.direction,
            exit_state.span,
            width,
            height,
        )[0]
        dx, dy = DIRECTIONS[exit_state.direction]
        walkable = self._state_rows(tile.walkable, width, height, "1")
        if walkable[local_y][local_x] == "0":
            inside_local = (local_x - dx, local_y - dy)
            outside_local = (local_x, local_y)
        else:
            inside_local = (local_x, local_y)
            outside_local = (local_x + dx, local_y + dy)
        inside = (tile.x + inside_local[0], tile.y + inside_local[1])
        outside = (tile.x + outside_local[0], tile.y + outside_local[1])
        return inside, outside

    def _trace_exit_portal(
        self,
        local_x: int,
        local_y: int,
        direction: str,
        width: int,
        height: int,
        walkable: list[str],
        visible: list[str],
    ) -> tuple[tuple[int, int], tuple[int, int], set[tuple[int, int]]]:
        dx, dy = DIRECTIONS[direction]
        inside = (max(0, min(local_x, width - 1)), max(0, min(local_y, height - 1)))
        if walkable[inside[1]][inside[0]] == "0":
            prior_x = inside[0] - dx
            prior_y = inside[1] - dy
            if 0 <= prior_x < width and 0 <= prior_y < height and walkable[prior_y][prior_x] != "0":
                inside = (prior_x, prior_y)
        probe_x = inside[0] + dx
        probe_y = inside[1] + dy
        throat_cells: set[tuple[int, int]] = set()
        while 0 <= probe_x < width and 0 <= probe_y < height:
            if visible[probe_y][probe_x] == "0":
                return inside, (probe_x, probe_y), throat_cells
            if walkable[probe_y][probe_x] != "0":
                inside = (probe_x, probe_y)
            else:
                throat_cells.add((probe_x, probe_y))
            probe_x += dx
            probe_y += dy
        return inside, (probe_x, probe_y), throat_cells

    def _position_from_offset(self, offset: int, direction: str, width: int, height: int) -> float:
        side_length = self._side_length(direction, width, height)
        if side_length <= 1:
            return 0.5
        return max(0.0, min(1.0, offset / (side_length - 1)))

    def _side_length(self, direction: str, width: int, height: int) -> int:
        if direction not in {"north", "south", "east", "west"}:
            return min(width, height)
        return width if direction in {"north", "south"} else height

    def _exit_offset(self, direction: str, x: int, y: int) -> int:
        if direction not in {"north", "south", "east", "west"}:
            return min(x, y)
        return x if direction in {"north", "south"} else y

    def _exit_cells(
        self,
        x: int,
        y: int,
        direction: str,
        span: int,
        width: int,
        height: int,
    ) -> list[tuple[int, int]]:
        max_span = self._max_exit_span(direction, x, y, width, height)
        clamped_span = max(1, min(span, max_span))
        step_x, step_y = EXIT_SPAN_STEPS[direction]
        return [(x + index * step_x, y + index * step_y) for index in range(clamped_span)]

    def _max_exit_span(self, direction: str, x: int, y: int, width: int, height: int) -> int:
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        step_x, step_y = EXIT_SPAN_STEPS[direction]
        unlimited = width + height
        x_room = width - x if step_x > 0 else x + 1 if step_x < 0 else unlimited
        y_room = height - y if step_y > 0 else y + 1 if step_y < 0 else unlimited
        return max(1, min(x_room, y_room))

    def _add_emergency_exit(self, session: SessionState, current: TileState) -> ExitState | None:
        occupied = set().union(*(self._occupied_cells(tile) for tile in session.map_state.tiles))
        width, height = self._rotated_size(current.footprint_width, current.footprint_height, current.rotation)
        for direction in DIRECTIONS:
            probe = self._new_exit(direction=direction, kind="passage", width=width, height=height)
            _, outside = self._exit_edge(current, probe)
            if outside not in occupied:
                current.exits.append(probe)
                return probe
        return None

    def _set_reciprocal_exit(self, destination: TileState, origin: TileState, origin_exit: ExitState) -> ExitState:
        reciprocal_direction = OPPOSITE[origin_exit.direction]
        origin_inside, _ = self._exit_edge(origin, origin_exit)
        reciprocal = next(
            (
                exit_state
                for exit_state in destination.exits
                if exit_state.direction == reciprocal_direction and exit_state.destination_tile_id in (None, origin.id)
                and self._exit_edge(destination, exit_state)[1] == origin_inside
            ),
            None,
        ) or next((exit_state for exit_state in destination.exits if exit_state.direction == reciprocal_direction), None)
        if reciprocal is None:
            width, height = self._rotated_size(destination.footprint_width, destination.footprint_height, destination.rotation)
            reciprocal = self._new_exit(
                direction=reciprocal_direction,
                kind=origin_exit.kind,
                width=width,
                height=height,
                status="open",
                span=origin_exit.span,
            )
            destination.exits.append(reciprocal)
        reciprocal.status = "open"
        reciprocal.destination_tile_id = origin.id
        self._sync_connection_state(origin_exit, reciprocal, passed_through=True)
        return reciprocal

    def _clear_door_state(self, exit_state: ExitState) -> None:
        exit_state.door_type = None
        exit_state.door_level = None
        exit_state.door_result = None
        exit_state.door_open = False
        exit_state.door_treasure_bonus = 0

    def _sync_connection_state(
        self,
        source: ExitState,
        target: ExitState,
        *,
        passed_through: bool = False,
    ) -> None:
        target.kind = source.kind
        target.span = max(source.span, target.span)
        target.door_destroyed = source.door_destroyed
        target.nailed_shut = source.nailed_shut
        if source.kind == "door":
            target.door_type = source.door_type
            target.door_level = source.door_level
            target.door_result = source.door_result
            target.door_treasure_bonus = source.door_treasure_bonus
            if source.nailed_shut:
                target.status = "blocked"
                target.door_open = False
            else:
                target.status = "open"
                target.door_open = True if passed_through else source.door_open
            return
        target.status = "open"
        self._clear_door_state(target)

    def _copy_door_state(self, source: ExitState, target: ExitState) -> None:
        if source.kind != "door":
            return
        self._sync_connection_state(source, target, passed_through=source.door_open)

    def _reciprocal_exit_on_tile(
        self,
        tile: TileState,
        other_tile_id: str,
        *,
        direction: str | None = None,
    ) -> ExitState | None:
        matches = [exit_state for exit_state in tile.exits if exit_state.destination_tile_id == other_tile_id]
        if not matches:
            return None
        if direction:
            directional = [exit_state for exit_state in matches if exit_state.direction == direction]
            if directional:
                return directional[0]
        return matches[0]

    def _persist_open_connection(self, session: SessionState, origin: TileState, origin_exit: ExitState) -> None:
        origin_exit.status = "open"
        if origin_exit.kind == "door":
            origin_exit.door_open = True
        if not origin_exit.destination_tile_id:
            return
        destination = self._tile_by_id(session, origin_exit.destination_tile_id)
        if destination is None:
            return
        reciprocal = self._reciprocal_exit_on_tile(
            destination,
            origin.id,
            direction=OPPOSITE[origin_exit.direction],
        )
        if reciprocal is None:
            return
        self._sync_connection_state(origin_exit, reciprocal, passed_through=True)

    def _inherit_connection_from_reciprocal(
        self,
        session: SessionState,
        current: TileState,
        exit_state: ExitState,
    ) -> None:
        if exit_state.door_open or not exit_state.destination_tile_id:
            return
        other_tile = self._tile_by_id(session, exit_state.destination_tile_id)
        if other_tile is None:
            return
        reciprocal = self._reciprocal_exit_on_tile(
            other_tile,
            current.id,
            direction=OPPOSITE[exit_state.direction],
        )
        if reciprocal is None:
            return
        if reciprocal.kind == "passage" and reciprocal.status == "open":
            self._sync_connection_state(reciprocal, exit_state, passed_through=True)
            return
        if reciprocal.kind == "door" and reciprocal.door_open:
            self._sync_connection_state(reciprocal, exit_state, passed_through=True)
            return

    def _refresh_tile_connections(self, session: SessionState, tile: TileState) -> None:
        for exit_state in tile.exits:
            if not exit_state.destination_tile_id:
                continue
            self._inherit_connection_from_reciprocal(session, tile, exit_state)
            if exit_state.kind == "door" and exit_state.door_open:
                self._sync_linked_door(session, tile, exit_state)

    def _initialize_outside_entrance(
        self,
        entrance: TileState,
        *,
        log: list[str] | None = None,
    ) -> bool:
        """Rulebook p.25: the party enters through the outside door; it stands open behind them."""
        changed = False
        for exit_state in entrance.exits:
            if not exit_state.dungeon_exit or exit_state.nailed_shut or exit_state.door_destroyed:
                continue
            if exit_state.status == "open" and (
                exit_state.kind != "door" or exit_state.door_open
            ):
                continue
            exit_state.status = "open"
            if exit_state.kind == "door":
                exit_state.door_open = True
                exit_state.door_type = exit_state.door_type or "unlocked"
            changed = True
            if log is not None:
                exit_label = "door" if exit_state.kind == "door" else "opening"
                log.append(
                    f"The party entered through the {exit_state.direction} {exit_label}; it remains open behind them."
                )
        return changed

    def _open_entrance_threshold(
        self,
        session: SessionState,
        exit_state: ExitState,
        *,
        show_rolls: bool,
    ) -> None:
        """Rulebook p.25: the party chooses an entrance door into the dungeon (no separate open step)."""
        exit_state.door_open = True
        exit_state.status = "open"
        if show_rolls:
            session.log.append(
                f"The party passes through the {exit_state.direction} entrance into the dungeon."
            )

    def _sync_linked_door(self, session: SessionState, current: TileState, exit_state: ExitState) -> None:
        if exit_state.kind != "door" or not exit_state.destination_tile_id:
            return
        other_tile = self._tile_by_id(session, exit_state.destination_tile_id)
        if other_tile is None:
            return
        reciprocal = self._reciprocal_exit_on_tile(
            other_tile,
            current.id,
            direction=OPPOSITE[exit_state.direction],
        )
        if reciprocal:
            self._sync_connection_state(exit_state, reciprocal, passed_through=exit_state.door_open)
            if not exit_state.nailed_shut:
                reciprocal.status = "open"

    def _overlaps_existing(self, session: SessionState, candidate: TileState) -> bool:
        candidate_cells = self._occupied_cells(candidate)
        for tile in session.map_state.tiles:
            if candidate_cells.intersection(self._occupied_cells(tile)):
                return True
        return False

    def _occupied_cells(self, tile: TileState) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        if len(tile.walkable) == height and all(len(row) == width for row in tile.walkable):
            return {
                (tile.x + local_x, tile.y + local_y)
                for local_y, row in enumerate(tile.walkable)
                for local_x, value in enumerate(row)
                if value != "0"
            }
        return self._footprint_cells(tile.x, tile.y, width, height)

    def _visible_cells(self, tile: TileState) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        if len(tile.visible) == height and all(len(row) == width for row in tile.visible):
            return {
                (tile.x + local_x, tile.y + local_y)
                for local_y, row in enumerate(tile.visible)
                for local_x, value in enumerate(row)
                if value != "0"
            }
        return self._footprint_cells(tile.x, tile.y, width, height)

    def _normalized_walkable(
        self,
        tile_def: TileDefinition | None,
        width: int,
        height: int,
        *,
        catalog: TileCatalogId = "ee",
    ) -> list[str]:
        if tile_def and len(tile_def.walkable) == height and all(len(row) == width for row in tile_def.walkable):
            active_catalog = tile_def.catalog if tile_def.catalog else catalog
            if active_catalog == "forsaken_depths_rivers":
                return [
                    "".join(
                        "2" if char == "2" else "1" if char in {"1", "w", "W", "."} else "0"
                        for char in row
                    )
                    for row in tile_def.walkable
                ]
            return ["".join("1" if char in {"1", "w", "W", "."} else "0" for char in row) for row in tile_def.walkable]
        return ["1" * width for _ in range(height)]

    def _normalized_cell_shapes(self, tile_def: TileDefinition | None, width: int, height: int) -> list[str]:
        allowed = {
            "F",
            "A",
            "B",
            "C",
            "D",
            "E",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
            "Q",
            "R",
            "S",
            "T",
            "U",
            "V",
            "W",
            "X",
            "Y",
            "a",
            "b",
            "c",
            "d",
            "e",
            "g",
            "h",
            "i",
            "f",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "z",
            "Z",
            "y",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "0",
        }
        if tile_def and len(tile_def.cell_shapes) == height and all(len(row) == width for row in tile_def.cell_shapes):
            return ["".join(char if char in allowed else "F" for char in row) for row in tile_def.cell_shapes]
        return ["F" * width for _ in range(height)]

    def _visible_rows(self, width: int, height: int) -> list[str]:
        return ["1" * width for _ in range(height)]

    def _rotated_walkable(self, tile_def: TileDefinition | None, rotation: int, *, catalog: TileCatalogId = "ee") -> list[str]:
        width = tile_def.footprint_width if tile_def else 1
        height = tile_def.footprint_height if tile_def else 1
        active_catalog = tile_def.catalog if tile_def and tile_def.catalog else catalog
        source = self._normalized_walkable(tile_def, width, height, catalog=active_catalog)
        return self._rotate_rows(source, width, height, rotation)

    def _rotated_cell_shapes(self, tile_def: TileDefinition | None, rotation: int) -> list[str]:
        width = tile_def.footprint_width if tile_def else 1
        height = tile_def.footprint_height if tile_def else 1
        source = self._normalized_cell_shapes(tile_def, width, height)
        return self._rotate_rows(source, width, height, rotation, self._rotate_cell_shape)

    def _rotate_rows(
        self,
        source: list[str],
        width: int,
        height: int,
        rotation: int,
        transform_value=None,
    ) -> list[str]:
        rotated_width, rotated_height = self._rotated_size(width, height, rotation)
        rows = [["0" for _ in range(rotated_width)] for _ in range(rotated_height)]
        transform_value = transform_value or (lambda value, _rotation: value)
        for y, row in enumerate(source):
            for x, value in enumerate(row):
                rotated_x, rotated_y = self._rotate_cell(x, y, width, height, rotation)
                rows[rotated_y][rotated_x] = transform_value(value, rotation)
        return ["".join(row) for row in rows]

    def _rotate_cell_shape(self, value: str, rotation: int) -> str:
        turns = (rotation // 90) % 4
        maps = [
            {},
            {
                "A": "C",
                "C": "D",
                "D": "B",
                "B": "A",
                "E": "H",
                "H": "I",
                "I": "G",
                "G": "E",
                "J": "L",
                "L": "M",
                "M": "K",
                "K": "J",
                "N": "T",
                "O": "U",
                "P": "R",
                "Q": "S",
                "R": "N",
                "S": "O",
                "T": "P",
                "U": "Q",
                "V": "Y",
                "W": "X",
                "X": "V",
                "Y": "W",
                "a": "c",
                "c": "d",
                "d": "b",
                "b": "a",
                "e": "h",
                "h": "i",
                "i": "g",
                "g": "e",
                "f": "u",
                "j": "v",
                "k": "w",
                "l": "x",
                "z": "4",
                "2": "5",
                "3": "6",
                "m": "q",
                "n": "r",
                "o": "s",
                "p": "t",
                "Z": "9",
                "7": "0",
                "8": "y",
                "q": "m",
                "r": "n",
                "s": "o",
                "t": "p",
                "9": "Z",
                "0": "7",
                "y": "8",
                "u": "f",
                "v": "j",
                "w": "k",
                "x": "l",
                "4": "z",
                "5": "2",
                "6": "3",
                "1": "z",
            },
            {
                "A": "D",
                "D": "A",
                "B": "C",
                "C": "B",
                "E": "I",
                "I": "E",
                "G": "H",
                "H": "G",
                "J": "M",
                "M": "J",
                "K": "L",
                "L": "K",
                "N": "Q",
                "O": "P",
                "P": "O",
                "Q": "N",
                "R": "U",
                "S": "T",
                "T": "S",
                "U": "R",
                "V": "W",
                "W": "V",
                "X": "Y",
                "Y": "X",
                "a": "d",
                "d": "a",
                "b": "c",
                "c": "b",
                "e": "i",
                "i": "e",
                "g": "h",
                "h": "g",
                "f": "m",
                "j": "p",
                "k": "o",
                "l": "n",
                "z": "Z",
                "2": "7",
                "3": "8",
                "m": "f",
                "n": "l",
                "o": "k",
                "p": "j",
                "Z": "z",
                "7": "2",
                "8": "3",
                "q": "u",
                "r": "x",
                "s": "w",
                "t": "v",
                "9": "6",
                "0": "5",
                "y": "4",
                "u": "q",
                "v": "t",
                "w": "s",
                "x": "r",
                "4": "y",
                "5": "0",
                "6": "9",
                "1": "8",
            },
            {
                "A": "B",
                "B": "D",
                "D": "C",
                "C": "A",
                "E": "G",
                "G": "I",
                "I": "H",
                "H": "E",
                "J": "K",
                "K": "M",
                "M": "L",
                "L": "J",
                "N": "R",
                "O": "S",
                "P": "T",
                "Q": "U",
                "R": "P",
                "S": "Q",
                "T": "N",
                "U": "O",
                "V": "X",
                "W": "Y",
                "X": "W",
                "Y": "V",
                "a": "b",
                "b": "d",
                "d": "c",
                "c": "a",
                "e": "g",
                "g": "i",
                "i": "h",
                "h": "e",
                "f": "q",
                "j": "9",
                "k": "0",
                "l": "y",
                "z": "r",
                "2": "s",
                "3": "t",
                "m": "u",
                "n": "4",
                "o": "5",
                "p": "6",
                "Z": "v",
                "7": "w",
                "8": "x",
                "q": "f",
                "r": "j",
                "s": "k",
                "t": "l",
                "9": "z",
                "0": "2",
                "y": "3",
                "u": "m",
                "v": "n",
                "w": "o",
                "x": "p",
                "4": "Z",
                "5": "7",
                "6": "8",
                "1": "3",
            },
        ]
        return maps[turns].get(value, value)

    def _placement_blocked(
        self,
        session: SessionState,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_def: TileDefinition | None,
        rotation: int,
        origin: TileState,
        origin_exit: ExitState,
    ) -> bool:
        candidate_cells = self._candidate_footprint_cells(x, y, width, height)
        if self._outside_paper_bounds(session, candidate_cells):
            return True
        if any(candidate_cells.intersection(self._visible_walkable_cells(tile)) for tile in session.map_state.tiles):
            return True
        if candidate_cells.intersection(self._protected_dungeon_exit_cells(session, origin, origin_exit)):
            return True
        reserved_exit_cells = self._reserved_exit_cells(session, origin, origin_exit)
        return bool(candidate_cells.intersection(reserved_exit_cells))

    def _outside_paper_bounds(self, session: SessionState, cells: set[tuple[int, int]]) -> bool:
        if session.map_bounds_mode != "paper":
            return False
        width = session.map_state.width
        height = session.map_state.height
        return any(cell_x < 0 or cell_y < 0 or cell_x >= width or cell_y >= height for cell_x, cell_y in cells)

    def _truncated_placement(
        self,
        session: SessionState,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_def: TileDefinition | None,
        rotation: int,
        origin: TileState,
        origin_exit: ExitState,
        exits: list[ExitState],
        matching: ExitState,
    ) -> Placement | None:
        candidate_exits = [exit_state.model_copy(deep=True) for exit_state in exits]
        candidate_matching = next((exit_state for exit_state in candidate_exits if exit_state.id == matching.id), None)
        if candidate_matching is None:
            return None
        base_walkable = self._rotated_walkable(tile_def, rotation)
        base_shapes = self._rotated_cell_shapes(tile_def, rotation)
        visible_walkable_blockers = set().union(
            *(self._visible_walkable_cells(tile) for tile in session.map_state.tiles)
        )
        origin_walkable_cells = self._visible_walkable_cells(origin)
        reserved_records = self._reserved_exit_records(session, origin, origin_exit)
        protected_exit_cells = self._protected_dungeon_exit_cells(session, origin, origin_exit)
        connectable_reserved_allowance: set[tuple[int, int]] = set()
        blocked_reserved_cells: set[tuple[int, int]] = set(protected_exit_cells)
        for record in reserved_records:
            reserved_target_cells = record["target_cells"]
            if self._candidate_has_matching_exit_for_record(
                x,
                y,
                width,
                height,
                base_walkable,
                self._visible_rows(width, height),
                candidate_exits,
                record,
            ):
                connectable_reserved_allowance.update(reserved_target_cells)
                connectable_reserved_allowance.update(record["throat_cells"])
            else:
                blocked_reserved_cells.update(reserved_target_cells)
        hard_blockers = (visible_walkable_blockers | blocked_reserved_cells) - connectable_reserved_allowance
        matching_cells = {
            (x + local_x, y + local_y)
            for local_x, local_y in self._exit_cells(
                candidate_matching.x,
                candidate_matching.y,
                candidate_matching.direction,
                candidate_matching.span,
                width,
                height,
            )
        }
        matching_local_cells = {
            (local_x, local_y)
            for local_x, local_y in self._exit_cells(
                candidate_matching.x,
                candidate_matching.y,
                candidate_matching.direction,
                candidate_matching.span,
                width,
                height,
            )
        }

        if matching_cells.intersection(hard_blockers):
            return None

        blockers = hard_blockers
        local_blockers = {
            (global_x - x, global_y - y)
            for global_x, global_y in blockers
            if x <= global_x < x + width and y <= global_y < y + height
        }
        removed_cells = self._directional_truncation_cells(
            local_blockers,
            width,
            height,
            OPPOSITE[origin_exit.direction],
        )
        removed_cells.update(
            self._origin_overlap_local_cells(
                x,
                y,
                width,
                height,
                origin,
                origin_exit=origin_exit,
                origin_visible_cells=origin_walkable_cells,
                entry_cells=matching_cells,
            )
        )
        if matching_local_cells.intersection(removed_cells):
            return None

        connected_cells = self._connected_local_walkable_cells(
            base_walkable,
            matching_local_cells,
            removed_cells,
            width,
            height,
        )
        if not connected_cells:
            return None
        walkable_local_cells = {
            (local_x, local_y)
            for local_y, row in enumerate(base_walkable)
            for local_x, value in enumerate(row)
            if value != "0" and (local_x, local_y) not in removed_cells
        }
        removed_cells.update(walkable_local_cells - connected_cells)

        truncated = False
        walkable_rows: list[str] = []
        shape_rows: list[str] = []
        visible_rows: list[str] = []
        for local_y in range(height):
            walkable_row = []
            shape_row = []
            visible_row = []
            for local_x in range(width):
                if (local_x, local_y) in removed_cells:
                    walkable_row.append("0")
                    shape_row.append("F")
                    visible_row.append("0")
                    truncated = True
                else:
                    walkable_row.append(base_walkable[local_y][local_x])
                    shape_row.append(base_shapes[local_y][local_x])
                    visible_row.append("1")
            walkable_rows.append("".join(walkable_row))
            shape_rows.append("".join(shape_row))
            visible_rows.append("".join(visible_row))

        if not any(char != "0" for row in walkable_rows for char in row):
            return None
        if any(walkable_rows[local_y][local_x] == "0" for local_x, local_y in matching_local_cells):
            return None

        for exit_state in candidate_exits:
            exit_cells = self._exit_cells(exit_state.x, exit_state.y, exit_state.direction, exit_state.span, width, height)
            if exit_state.id == candidate_matching.id:
                exit_state.status = "open"
                continue
            if any((local_x, local_y) in removed_cells for local_x, local_y in exit_cells):
                exit_state.status = "blocked"
                truncated = True
                continue
            if any(walkable_rows[local_y][local_x] == "0" for local_x, local_y in exit_cells):
                exit_state.status = "blocked"
                truncated = True
                continue
            outside_cells = self._candidate_exit_outside_cells(
                x,
                y,
                exit_state,
                width,
                height,
                walkable_rows,
                visible_rows,
            )
            if outside_cells.intersection(blockers):
                if any(
                    self._candidate_exit_matches_record(
                        x,
                        y,
                        exit_state,
                        width,
                        height,
                        walkable_rows,
                        visible_rows,
                        record,
                    )
                    for record in reserved_records
                ):
                    continue
                exit_state.status = "blocked"
                truncated = True

        return Placement(
            x=x,
            y=y,
            rotation=rotation,
            exits=candidate_exits,
            walkable=walkable_rows,
            cell_shapes=shape_rows,
            visible=visible_rows,
            truncated=truncated,
        )

    def _connected_local_walkable_cells(
        self,
        walkable: list[str],
        seed_cells: set[tuple[int, int]],
        removed_cells: set[tuple[int, int]],
        width: int,
        height: int,
    ) -> set[tuple[int, int]]:
        seeds = [
            cell
            for cell in seed_cells
            if 0 <= cell[0] < width
            and 0 <= cell[1] < height
            and cell not in removed_cells
            and walkable[cell[1]][cell[0]] != "0"
        ]
        if not seeds:
            return set()
        connected: set[tuple[int, int]] = set(seeds)
        frontier = list(seeds)
        while frontier:
            local_x, local_y = frontier.pop()
            for dx, dy in CARDINAL_DIRECTIONS.values():
                next_x = local_x + dx
                next_y = local_y + dy
                candidate = (next_x, next_y)
                if (
                    candidate in connected
                    or candidate in removed_cells
                    or next_x < 0
                    or next_y < 0
                    or next_x >= width
                    or next_y >= height
                    or walkable[next_y][next_x] == "0"
                ):
                    continue
                connected.add(candidate)
                frontier.append(candidate)
        return connected

    def _candidate_footprint_cells(self, x: int, y: int, width: int, height: int) -> set[tuple[int, int]]:
        return self._footprint_cells(x, y, width, height)

    def _clip_origin_visible_for_neighbor(self, origin: TileState, neighbor: TileState) -> None:
        if self._is_entrance_tile(origin):
            return
        neighbor_width, neighbor_height = self._rotated_size(
            neighbor.footprint_width,
            neighbor.footprint_height,
            neighbor.rotation,
        )
        neighbor_visible = self._visible_cells(neighbor)
        if not neighbor_visible:
            return
        width, height = self._rotated_size(origin.footprint_width, origin.footprint_height, origin.rotation)
        if len(origin.visible) != height or not all(len(row) == width for row in origin.visible):
            origin.visible = self._visible_rows(width, height)
        updated: list[str] = []
        changed = False
        for local_y in range(height):
            row_chars: list[str] = []
            for local_x in range(width):
                global_pos = (origin.x + local_x, origin.y + local_y)
                if global_pos in neighbor_visible and origin.visible[local_y][local_x] != "0":
                    row_chars.append("0")
                    changed = True
                else:
                    row_chars.append(origin.visible[local_y][local_x])
            updated.append("".join(row_chars))
        if changed:
            origin.visible = updated

    def _origin_exit_interior_cells(self, tile: TileState, exit_state: ExitState) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        walkable = self._state_rows(tile.walkable, width, height, "1")
        visible = self._state_rows(tile.visible, width, height, "1")
        return {
            (tile.x + inside_x, tile.y + inside_y)
            for local_x, local_y in self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            )
            for (inside_x, inside_y), _, _ in [
                self._trace_exit_portal(
                    local_x,
                    local_y,
                    exit_state.direction,
                    width,
                    height,
                    walkable,
                    visible,
                )
            ]
        }

    def _origin_overlap_local_cells(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        origin: TileState,
        *,
        origin_exit: ExitState | None = None,
        origin_visible_cells: set[tuple[int, int]] | None = None,
        entry_cells: set[tuple[int, int]] | None = None,
    ) -> set[tuple[int, int]]:
        """Local cells of a candidate tile that overlap the origin over an exit (not throat-only overlap)."""
        origin_visible = origin_visible_cells if origin_visible_cells is not None else self._visible_cells(origin)
        candidate_footprint = self._footprint_cells(x, y, width, height)
        overlap = candidate_footprint.intersection(origin_visible)
        if entry_cells:
            overlap -= entry_cells
        if not overlap:
            return set()

        origin_exit_cells = set().union(
            *(self._origin_exit_interior_cells(origin, exit_state) for exit_state in origin.exits)
        )
        if not overlap.intersection(origin_exit_cells):
            return set()

        return {
            (global_x - x, global_y - y)
            for global_x, global_y in overlap
            if x <= global_x < x + width and y <= global_y < y + height
        }

    def _strip_neighbor_origin_overlap(
        self,
        origin: TileState,
        neighbor: TileState,
        origin_exit: ExitState,
    ) -> None:
        """Remove neighbor squares that overlap explored origin exits, keeping throat-only overlap."""
        neighbor_width, neighbor_height = self._rotated_size(
            neighbor.footprint_width,
            neighbor.footprint_height,
            neighbor.rotation,
        )
        entered_from = OPPOSITE[origin_exit.direction]
        entry_cells: set[tuple[int, int]] = set()
        for exit_state in neighbor.exits:
            if exit_state.direction != entered_from:
                continue
            entry_cells.update(
                (neighbor.x + local_x, neighbor.y + local_y)
                for local_x, local_y in self._exit_cells(
                    exit_state.x,
                    exit_state.y,
                    exit_state.direction,
                    exit_state.span,
                    neighbor_width,
                    neighbor_height,
                )
            )
        removed = self._origin_overlap_local_cells(
            neighbor.x,
            neighbor.y,
            neighbor_width,
            neighbor_height,
            origin,
            origin_exit=origin_exit,
            entry_cells=entry_cells,
        )
        if not removed:
            return
        if len(neighbor.walkable) != neighbor_height or not all(len(row) == neighbor_width for row in neighbor.walkable):
            neighbor.walkable = self._normalized_walkable(None, neighbor_width, neighbor_height)
        if len(neighbor.visible) != neighbor_height or not all(len(row) == neighbor_width for row in neighbor.visible):
            neighbor.visible = self._visible_rows(neighbor_width, neighbor_height)
        if len(neighbor.cell_shapes) != neighbor_height or not all(len(row) == neighbor_width for row in neighbor.cell_shapes):
            neighbor.cell_shapes = ["F" * neighbor_width for _ in range(neighbor_height)]

        walkable_rows: list[str] = []
        shape_rows: list[str] = []
        visible_rows: list[str] = []
        for local_y in range(neighbor_height):
            walkable_row: list[str] = []
            shape_row: list[str] = []
            visible_row: list[str] = []
            for local_x in range(neighbor_width):
                if (local_x, local_y) in removed:
                    walkable_row.append("0")
                    shape_row.append("F")
                    visible_row.append("0")
                else:
                    walkable_row.append(neighbor.walkable[local_y][local_x])
                    shape_row.append(neighbor.cell_shapes[local_y][local_x])
                    visible_row.append(neighbor.visible[local_y][local_x])
            walkable_rows.append("".join(walkable_row))
            shape_rows.append("".join(shape_row))
            visible_rows.append("".join(visible_row))
        neighbor.walkable = walkable_rows
        neighbor.cell_shapes = shape_rows
        neighbor.visible = visible_rows

        for exit_state in neighbor.exits:
            exit_cells = self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                neighbor_width,
                neighbor_height,
            )
            if any(neighbor.walkable[local_y][local_x] == "0" for local_x, local_y in exit_cells):
                exit_state.status = "blocked"

    def _apply_truncated_cells_to_tile(self, tile: TileState, removed: set[tuple[int, int]]) -> None:
        if not removed:
            return
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        if len(tile.walkable) != height or not all(len(row) == width for row in tile.walkable):
            tile.walkable = self._normalized_walkable(None, width, height)
        if len(tile.visible) != height or not all(len(row) == width for row in tile.visible):
            tile.visible = self._visible_rows(width, height)
        if len(tile.cell_shapes) != height or not all(len(row) == width for row in tile.cell_shapes):
            tile.cell_shapes = ["F" * width for _ in range(height)]

        walkable_rows: list[str] = []
        shape_rows: list[str] = []
        visible_rows: list[str] = []
        for local_y in range(height):
            walkable_row: list[str] = []
            shape_row: list[str] = []
            visible_row: list[str] = []
            for local_x in range(width):
                if (local_x, local_y) in removed:
                    walkable_row.append("0")
                    shape_row.append("F")
                    visible_row.append("0")
                else:
                    walkable_row.append(tile.walkable[local_y][local_x])
                    shape_row.append(tile.cell_shapes[local_y][local_x])
                    visible_row.append(tile.visible[local_y][local_x])
            walkable_rows.append("".join(walkable_row))
            shape_rows.append("".join(shape_row))
            visible_rows.append("".join(visible_row))
        tile.walkable = walkable_rows
        tile.cell_shapes = shape_rows
        tile.visible = visible_rows

        for exit_state in tile.exits:
            exit_cells = self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            )
            if any(tile.walkable[local_y][local_x] == "0" for local_x, local_y in exit_cells):
                exit_state.status = "blocked"

    def carve_imported_neighbor_connection(
        self,
        origin: TileState,
        neighbor: TileState,
        origin_exit: ExitState,
        neighbor_entry_exit: ExitState,
    ) -> None:
        """Carve neighbor walkable grids at an imported link (same rules as procedural placement)."""
        self._strip_neighbor_origin_overlap(origin, neighbor, origin_exit)

        neighbor_width, neighbor_height = self._rotated_size(
            neighbor.footprint_width,
            neighbor.footprint_height,
            neighbor.rotation,
        )
        origin_walkable_cells = self._visible_walkable_cells(origin)
        matching_local_cells = set(
            self._exit_cells(
                neighbor_entry_exit.x,
                neighbor_entry_exit.y,
                neighbor_entry_exit.direction,
                neighbor_entry_exit.span,
                neighbor_width,
                neighbor_height,
            )
        )
        entry_cells_global = {
            (neighbor.x + local_x, neighbor.y + local_y) for local_x, local_y in matching_local_cells
        }
        entered_from = OPPOSITE[origin_exit.direction]
        blockers = origin_walkable_cells - entry_cells_global
        local_blockers = {
            (global_x - neighbor.x, global_y - neighbor.y)
            for global_x, global_y in blockers
            if neighbor.x <= global_x < neighbor.x + neighbor_width
            and neighbor.y <= global_y < neighbor.y + neighbor_height
        }
        removed_cells = self._directional_truncation_cells(
            local_blockers,
            neighbor_width,
            neighbor_height,
            entered_from,
        )
        removed_cells.update(
            self._origin_overlap_local_cells(
                neighbor.x,
                neighbor.y,
                neighbor_width,
                neighbor_height,
                origin,
                origin_exit=origin_exit,
                origin_visible_cells=origin_walkable_cells,
                entry_cells=entry_cells_global,
            )
        )
        if matching_local_cells.intersection(removed_cells):
            return

        base_walkable = self._state_rows(neighbor.walkable, neighbor_width, neighbor_height, "1")
        connected_cells = self._connected_local_walkable_cells(
            base_walkable,
            matching_local_cells,
            removed_cells,
            neighbor_width,
            neighbor_height,
        )
        if not connected_cells:
            return
        walkable_local_cells = {
            (local_x, local_y)
            for local_y, row in enumerate(base_walkable)
            for local_x, value in enumerate(row)
            if value != "0" and (local_x, local_y) not in removed_cells
        }
        removed_cells.update(walkable_local_cells - connected_cells)
        already_removed = {
            (local_x, local_y)
            for local_y, row in enumerate(neighbor.walkable)
            for local_x, value in enumerate(row)
            if value == "0"
        }
        removed_cells -= already_removed
        self._apply_truncated_cells_to_tile(neighbor, removed_cells)

    def _visible_walkable_cells(self, tile: TileState) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        walkable = self._state_rows(tile.walkable, width, height, "1")
        visible = self._state_rows(tile.visible, width, height, "1")
        return {
            (tile.x + local_x, tile.y + local_y)
            for local_y, row in enumerate(walkable)
            for local_x, value in enumerate(row)
            if value != "0" and visible[local_y][local_x] != "0"
        }

    def _connect_reserved_exits_to_neighbor(
        self,
        session: SessionState,
        neighbor: TileState,
        origin: TileState,
        origin_exit: ExitState,
    ) -> None:
        neighbor_width, neighbor_height = self._rotated_size(
            neighbor.footprint_width,
            neighbor.footprint_height,
            neighbor.rotation,
        )
        neighbor_walkable = self._visible_walkable_cells(neighbor)
        if not neighbor_walkable:
            return

        for record in self._reserved_exit_records(session, origin, origin_exit):
            source_tile: TileState = record["tile"]
            source_exit: ExitState = record["exit"]
            reciprocal_direction = OPPOSITE[source_exit.direction]
            reciprocal = next(
                (
                    exit_state
                    for exit_state in neighbor.exits
                    if exit_state.direction == reciprocal_direction
                    and exit_state.status != "blocked"
                    and self._candidate_exit_matches_record(
                        neighbor.x,
                        neighbor.y,
                        exit_state,
                        neighbor_width,
                        neighbor_height,
                        neighbor.walkable,
                        neighbor.visible,
                        record,
                    )
                ),
                None,
            )
            if reciprocal is None:
                continue

            source_exit.destination_tile_id = neighbor.id
            reciprocal.destination_tile_id = source_tile.id
            self._sync_connection_state(source_exit, reciprocal, passed_through=source_exit.door_open)
            if source_exit.kind == "passage" or source_exit.door_open:
                source_exit.status = "open"

    def _directional_truncation_cells(
        self,
        blockers: set[tuple[int, int]],
        width: int,
        height: int,
        direction: str,
    ) -> set[tuple[int, int]]:
        dx, dy = DIRECTIONS[direction]
        blocker_by_line: dict[int, list[int]] = {}
        for blocker_x, blocker_y in blockers:
            line = blocker_x * dy - blocker_y * dx
            projection = blocker_x * dx + blocker_y * dy
            blocker_by_line.setdefault(line, []).append(projection)
        removed: set[tuple[int, int]] = set()
        for local_y in range(height):
            for local_x in range(width):
                line = local_x * dy - local_y * dx
                projections = blocker_by_line.get(line)
                if not projections:
                    continue
                projection = local_x * dx + local_y * dy
                if projection >= min(projections):
                    removed.add((local_x, local_y))
        return removed

    def _candidate_occupied_cells(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        tile_def: TileDefinition | None,
        rotation: int,
    ) -> set[tuple[int, int]]:
        if tile_def is None:
            return self._footprint_cells(x, y, width, height)
        rows = self._rotated_walkable(tile_def, rotation)
        cells = {
            (x + local_x, y + local_y)
            for local_y, row in enumerate(rows)
            for local_x, value in enumerate(row)
            if value != "0"
        }
        return cells or self._footprint_cells(x, y, width, height)

    def _reserved_exit_cells(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
    ) -> set[tuple[int, int]]:
        return set().union(*(record["target_cells"] for record in self._reserved_exit_records(session, origin, origin_exit)))

    def _reserved_exit_records(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
    ) -> list[dict]:
        records: list[dict] = []
        for tile in session.map_state.tiles:
            for exit_state in tile.exits:
                if tile.id == origin.id and exit_state.id == origin_exit.id:
                    continue
                if exit_state.dungeon_exit or exit_state.status == "blocked" or exit_state.destination_tile_id:
                    continue
                inside_cells = self._exit_portal_inside_cells(tile, exit_state)
                target_cells, throat_cells = self._exit_portal_cells(tile, exit_state)
                if not target_cells:
                    continue
                records.append(
                    {
                        "tile": tile,
                        "exit": exit_state,
                        "inside_cells": inside_cells,
                        "target_cells": target_cells,
                        "throat_cells": throat_cells,
                    }
                )
        return records

    def _placement_exit_conflicts(
        self,
        session: SessionState,
        placement: Placement,
        origin: TileState,
        origin_exit: ExitState,
        matching_exit_id: str,
    ) -> set[str]:
        if not placement.walkable:
            return set()
        width = len(placement.walkable[0])
        height = len(placement.walkable)
        records = self._reserved_exit_records(session, origin, origin_exit)
        conflicts: set[str] = set()
        for exit_state in placement.exits:
            if exit_state.id == matching_exit_id or exit_state.status == "blocked":
                continue
            outside_cells = self._candidate_exit_outside_cells(
                placement.x,
                placement.y,
                exit_state,
                width,
                height,
                placement.walkable,
                placement.visible,
            )
            if not outside_cells:
                continue
            touches_existing = any(
                outside_cells.intersection(self._visible_cells(tile))
                for tile in session.map_state.tiles
            )
            if not touches_existing:
                continue
            if any(
                self._candidate_exit_matches_record(
                    placement.x,
                    placement.y,
                    exit_state,
                    width,
                    height,
                    placement.walkable,
                    placement.visible,
                    record,
                )
                for record in records
            ):
                continue
            conflicts.add(exit_state.id)
        return conflicts

    def _placement_displayed_exit_count(
        self,
        session: SessionState,
        placement: Placement,
        blocked_exit_ids: set[str] | None = None,
    ) -> int:
        if not placement.walkable:
            return 0
        width = len(placement.walkable[0])
        height = len(placement.walkable)
        visible = self._state_rows(placement.visible, width, height, "1")
        walkable = self._state_rows(placement.walkable, width, height, "1")
        older_hard_cells = set().union(*(self._visible_walkable_cells(tile) for tile in session.map_state.tiles))
        blocked = blocked_exit_ids or set()
        count = 0
        for exit_state in placement.exits:
            if exit_state.status == "blocked" or exit_state.id in blocked:
                continue
            for local_x, local_y in self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            ):
                if walkable[local_y][local_x] == "0" or visible[local_y][local_x] == "0":
                    continue
                if (placement.x + local_x, placement.y + local_y) in older_hard_cells:
                    continue
                count += 1
                break
        return count

    def _block_placement_exits(self, placement: Placement, exit_ids: set[str]) -> None:
        if not exit_ids:
            return
        for exit_state in placement.exits:
            if exit_state.id in exit_ids:
                exit_state.status = "blocked"
        placement.truncated = True

    def _candidate_has_matching_exit_for_record(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        walkable: list[str],
        visible: list[str],
        exits: list[ExitState],
        record: dict,
    ) -> bool:
        return any(
            exit_state.status != "blocked"
            and self._candidate_exit_matches_record(x, y, exit_state, width, height, walkable, visible, record)
            for exit_state in exits
        )

    def _candidate_exit_matches_record(
        self,
        x: int,
        y: int,
        exit_state: ExitState,
        width: int,
        height: int,
        walkable: list[str],
        visible: list[str],
        record: dict,
    ) -> bool:
        source_exit: ExitState = record["exit"]
        if exit_state.direction != OPPOSITE[source_exit.direction]:
            return False
        candidate_inside = self._candidate_exit_inside_cells(x, y, exit_state, width, height, walkable, visible)
        candidate_outside = self._candidate_exit_outside_cells(x, y, exit_state, width, height, walkable, visible)
        return bool(candidate_inside.intersection(record["target_cells"])) and bool(
            candidate_outside.intersection(record["inside_cells"])
        )

    def _protected_dungeon_exit_cells(
        self,
        session: SessionState,
        origin: TileState,
        origin_exit: ExitState,
    ) -> set[tuple[int, int]]:
        protected: set[tuple[int, int]] = set()
        for tile in session.map_state.tiles:
            for exit_state in tile.exits:
                if tile.id == origin.id and exit_state.id == origin_exit.id:
                    continue
                if not exit_state.dungeon_exit:
                    continue
                target_cells, throat_cells = self._exit_portal_cells(tile, exit_state)
                protected.update(target_cells)
                protected.update(throat_cells)
        return protected

    def _exit_outside_cells(self, tile: TileState, exit_state: ExitState) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        dx, dy = DIRECTIONS[exit_state.direction]
        return {
            (tile.x + local_x + dx, tile.y + local_y + dy)
            for local_x, local_y in self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            )
        }

    def _state_rows(self, rows: list[str], width: int, height: int, default: str) -> list[str]:
        if len(rows) == height and all(len(row) == width for row in rows):
            return rows
        return [default * width for _ in range(height)]

    def _exit_portal_cells(
        self,
        tile: TileState,
        exit_state: ExitState,
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        if self._uses_authored_exit_portal(tile, exit_state):
            dx, dy = DIRECTIONS[exit_state.direction]
            walkable = self._state_rows(tile.walkable, width, height, "1")
            target_cells: set[tuple[int, int]] = set()
            throat_cells: set[tuple[int, int]] = set()
            for local_x, local_y in self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            ):
                if walkable[local_y][local_x] == "0":
                    target_cells.add((tile.x + local_x, tile.y + local_y))
                    throat_cells.add((tile.x + local_x, tile.y + local_y))
                else:
                    target_cells.add((tile.x + local_x + dx, tile.y + local_y + dy))
            return target_cells, throat_cells
        walkable = self._state_rows(tile.walkable, width, height, "1")
        visible = self._state_rows(tile.visible, width, height, "1")
        target_cells: set[tuple[int, int]] = set()
        throat_cells: set[tuple[int, int]] = set()
        for local_x, local_y in self._exit_cells(
            exit_state.x,
            exit_state.y,
            exit_state.direction,
            exit_state.span,
            width,
            height,
        ):
            _, target, throat = self._trace_exit_portal(
                local_x,
                local_y,
                exit_state.direction,
                width,
                height,
                walkable,
                visible,
            )
            target_cells.add((tile.x + target[0], tile.y + target[1]))
            throat_cells.update((tile.x + throat_x, tile.y + throat_y) for throat_x, throat_y in throat)
        return target_cells, throat_cells

    def _exit_portal_inside_cells(
        self,
        tile: TileState,
        exit_state: ExitState,
    ) -> set[tuple[int, int]]:
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        if self._uses_authored_exit_portal(tile, exit_state):
            return self._origin_exit_interior_cells(tile, exit_state)
        walkable = self._state_rows(tile.walkable, width, height, "1")
        visible = self._state_rows(tile.visible, width, height, "1")
        inside_cells: set[tuple[int, int]] = set()
        for local_x, local_y in self._exit_cells(
            exit_state.x,
            exit_state.y,
            exit_state.direction,
            exit_state.span,
            width,
            height,
        ):
            inside, _, _ = self._trace_exit_portal(
                local_x,
                local_y,
                exit_state.direction,
                width,
                height,
                walkable,
                visible,
            )
            inside_cells.add((tile.x + inside[0], tile.y + inside[1]))
        return inside_cells

    def _candidate_exit_inside_cells(
        self,
        x: int,
        y: int,
        exit_state: ExitState,
        width: int,
        height: int,
        walkable: list[str] | None = None,
        visible: list[str] | None = None,
    ) -> set[tuple[int, int]]:
        walkable_rows = self._state_rows(walkable or [], width, height, "1")
        visible_rows = self._state_rows(visible or [], width, height, "1")
        return {
            (x + inside_x, y + inside_y)
            for local_x, local_y in self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            )
            for (inside_x, inside_y), _, _ in [
                self._trace_exit_portal(
                    local_x,
                    local_y,
                    exit_state.direction,
                    width,
                    height,
                    walkable_rows,
                    visible_rows,
                )
            ]
        }

    def _candidate_exit_outside_cells(
        self,
        x: int,
        y: int,
        exit_state: ExitState,
        width: int,
        height: int,
        walkable: list[str] | None = None,
        visible: list[str] | None = None,
    ) -> set[tuple[int, int]]:
        walkable_rows = self._state_rows(walkable or [], width, height, "1")
        visible_rows = self._state_rows(visible or [], width, height, "1")
        return {
            (x + target_x, y + target_y)
            for local_x, local_y in self._exit_cells(
                exit_state.x,
                exit_state.y,
                exit_state.direction,
                exit_state.span,
                width,
                height,
            )
            for _, (target_x, target_y), _ in [
                self._trace_exit_portal(
                    local_x,
                    local_y,
                    exit_state.direction,
                    width,
                    height,
                    walkable_rows,
                    visible_rows,
                )
            ]
        }

    def _footprint_cells(self, x: int, y: int, width: int, height: int) -> set[tuple[int, int]]:
        return {(x + dx, y + dy) for dx in range(width) for dy in range(height)}

    def _rotated_size(self, width: int, height: int, rotation: int) -> tuple[int, int]:
        return (height, width) if rotation in (90, 270) else (width, height)

    def _current_tile(self, session: SessionState) -> TileState:
        return next(tile for tile in session.map_state.tiles if tile.id == session.map_state.current_tile_id)

    def _active_tile(self, session: SessionState) -> TileState:
        """Return the tile of the active navigation group (detached or main party)."""
        tid = active_tile_id(session)
        tile = self._tile_by_id(session, tid)
        return tile if tile is not None else self._current_tile(session)

    def _tile_by_id(self, session: SessionState, tile_id: str | None) -> TileState | None:
        if tile_id is None:
            return None
        return next((tile for tile in session.map_state.tiles if tile.id == tile_id), None)

    def _tile_occupying(
        self,
        session: SessionState,
        x: int,
        y: int,
        exclude_tile_id: str | None = None,
    ) -> TileState | None:
        return next(
            (
                tile
                for tile in session.map_state.tiles
                if tile.id != exclude_tile_id and (x, y) in self._occupied_cells(tile)
            ),
            None,
        )

    def _highest_character_level(self, party: list[PartyMemberState]) -> int:
        return max((pc.level for pc in party), default=1)

    def _tile_type(self, tile_type: str) -> str:
        if tile_type in {"room", "corridor"}:
            return tile_type
        return "corridor" if roll_d6() <= 2 else "room"

    def _rotate_direction(self, direction: str, rotation: int) -> str:
        turns = (rotation // 90) % 4
        index = DIRECTION_ORDER.index(direction)
        return DIRECTION_ORDER[(index + turns * 2) % len(DIRECTION_ORDER)]

    def _tile_description(self, tile_description: str, content_description: str) -> str:
        if tile_description:
            return f"{tile_description} {content_description}"
        return content_description

    def _tile_image(self, tile_key: str, image: str | None = None) -> str:
        filename = image or f"{tile_key}.gif"
        return f"/assets/tiles/{filename}"

    def _member_by_marching_order(self, session: SessionState, position: int) -> PartyMemberState | None:
        living = [member for member in session.party if member.current_life > 0]
        if not living:
            return None
        return next((member for member in living if member.marching_order == position), living[0])

    def _marching_order_ids(self, session: SessionState) -> list[str]:
        return [
            member.character_id
            for member in sorted(session.party, key=lambda item: item.marching_order)
            if member.current_life > 0
        ]

    def _stage_treasure_outcome(
        self,
        session: SessionState,
        tile: TileState,
        outcome: TreasureOutcome,
        *,
        show_rolls: bool,
    ) -> None:
        if outcome.choice_key:
            tile.pending_treasure_choice = outcome.choice_key
            tile.treasure_summary = outcome.summary
            tile.treasure_gold = outcome.gold
            tile.treasure_items = list(outcome.items)
            tile.treasure_claimed = False
            if outcome.jackpot_wandering_on_claim:
                tile.fd_jackpot_wandering_on_claim = True
            if show_rolls:
                session.log.append(outcome.summary)
            return
        tile.pending_treasure_choice = None
        if outcome.jackpot_wandering_on_claim:
            tile.fd_jackpot_wandering_on_claim = True
        if outcome.gold or outcome.items:
            tile.treasure_summary = outcome.summary
            tile.treasure_gold = outcome.gold
            tile.treasure_items = self._finalize_treasure_items(session, list(outcome.items), show_rolls=show_rolls)
            tile.treasure_claimed = False
            if show_rolls:
                session.log.append("Treasure is available to claim.")
        else:
            tile.treasure_summary = outcome.summary
            tile.objects = [item for item in tile.objects if "treasure" not in item.lower()]
            empty_msg = outcome.summary or "No treasure found."
            self._apply_empty_treasure_description(tile, empty_msg)
            if show_rolls:
                session.log.append(empty_msg)

    def _choose_treasure_outcome(
        self,
        session: SessionState,
        pick: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        tile = self._current_tile(session)
        if session.mode != "exploration":
            session.log.append("Resolve treasure choices during exploration.")
            return
        if not tile.pending_treasure_choice:
            session.log.append("No treasure choice is pending on this tile.")
            return
        if not pick:
            session.log.append("Choose a treasure outcome.")
            return
        choice_key = tile.pending_treasure_choice
        if choice_key.startswith("abyss_"):
            outcome = self._resolve_abyss_treasure_choice(choice_key, pick, tile)
        elif choice_key.startswith("fd_"):
            outcome = self.table_roller.resolve_fd_treasure_choice(
                choice_key,
                pick,
                staged_gold=tile.treasure_gold,
                staged_items=list(tile.treasure_items),
                silk_already_found=session.fd_silk_treasure_used,
                show_rolls=show_rolls,
            )
        else:
            outcome = self.table_roller.resolve_environment_treasure_choice(
                choice_key,
                pick,
                environment=session.environment,
            )
        if show_rolls:
            session.log.extend(outcome.log)
        if outcome.clues_granted > 0:
            for index in range(outcome.clues_granted):
                self._grant_clue(session, tile, add_object=(index == 0))
        if "Precious silk" in outcome.summary or any(
            "silk" in item.lower() for item in outcome.items
        ):
            session.fd_silk_treasure_used = True
        self._stage_treasure_outcome(session, tile, outcome, show_rolls=show_rolls)
        self._apply_treasure_doubling(tile)
        if outcome.gold or outcome.items:
            session.pending_treasure_reroll_tile_id = tile.id

    def _resolve_abyss_treasure_choice(self, choice_key: str, pick: str, tile: TileState) -> TreasureOutcome:
        if choice_key == "abyss_gold_or_weapon":
            if pick == "weapon":
                return TreasureOutcome("Abyss treasure: one non-magical weapon of your choice.", 0, ["Non-magical weapon"], [])
            return TreasureOutcome(tile.treasure_summary or "Abyss gold.", tile.treasure_gold, [], [])
        if choice_key == "abyss_gold_or_useful":
            if pick == "useful":
                item = self._roll_abyss_useful_item()
                return TreasureOutcome(f"Abyss Useful Stuff: {item}.", 0, [item], [])
            return TreasureOutcome(tile.treasure_summary or "Abyss gold.", tile.treasure_gold, [], [])
        if choice_key == "abyss_jewelry_or_useful":
            if pick == "useful":
                item = self._roll_abyss_useful_item()
                return TreasureOutcome(f"Abyss Useful Stuff: {item}.", 0, [item], [])
            return TreasureOutcome(tile.treasure_summary or "Abyss jewelry.", tile.treasure_gold, ["Abyss jewelry"], [])
        if choice_key == "abyss_defense_or_gold":
            if pick == "gold":
                return TreasureOutcome(tile.treasure_summary or "Abyss gold.", tile.treasure_gold, [], [])
            item = tile.treasure_items[0] if tile.treasure_items else self._roll_abyss_magic_or_defense_item(defense=True)
            return TreasureOutcome(f"Abyss magical defense: {item}.", 0, [item], [])
        return TreasureOutcome(tile.treasure_summary or "Abyss treasure.", tile.treasure_gold, list(tile.treasure_items), [])

    def _fd_oblivion_redeem_madness(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Oblivion redemption is available during exploration.")
            return
        if not character_id:
            session.log.append("Choose a hero to remove 1 Madness.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("That hero is not in the party.")
            return
        from .forsaken_depths_river import redeem_fd_oblivion_madness

        if not redeem_fd_oblivion_madness(session, member, show_rolls=show_rolls):
            session.log.append(
                "Oblivion redemption is unavailable — need the River of Oblivion, a pending one-time offer, "
                "and a living hero with Madness."
            )

    def _fd_spend_hallucination_revelation(
        self,
        session: SessionState,
        choice: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Spend a Hallucination Revelation during exploration.")
            return
        if not choice:
            session.log.append("Choose a Revelation benefit.")
            return
        from .forsaken_depths_content import spend_fd_hallucination_revelation

        if not spend_fd_hallucination_revelation(session, choice, show_rolls=show_rolls):
            session.log.append("Hallucination Revelation is not available.")

    def _fd_prisoners_escape(self, session: SessionState, *, show_rolls: bool) -> None:
        if session.mode != "exploration":
            session.log.append("Escape the citadel during exploration.")
            return
        from .forsaken_depths_citadel import escape_fd_prisoners_citadel

        if not escape_fd_prisoners_citadel(self, session, show_rolls=show_rolls):
            session.log.append("Prisoners escape failed.")

    def _fd_secret_passage_unlock_clues(self, session: SessionState, *, show_rolls: bool) -> None:
        if session.mode != "exploration":
            session.log.append("Unlock the Forsaken secret passage during exploration.")
            return
        from .forsaken_depths_secret_passage import unlock_fd_secret_passage_with_clues

        unlock_fd_secret_passage_with_clues(self, session, show_rolls=show_rolls)

    def _ensure_side_sheet_exit(self, session: SessionState, origin: TileState) -> ExitState | None:
        for exit_state in origin.exits:
            if exit_state.status != "blocked" and not exit_state.destination_tile_id:
                return exit_state
        width, height = self._rotated_size(
            origin.footprint_width, origin.footprint_height, origin.rotation
        )
        used = {exit_state.direction for exit_state in origin.exits}
        direction = next(
            (item for item in CARDINAL_DIRECTION_ORDER if item not in used),
            "north",
        )
        exit_state = self._new_exit(
            direction=direction,
            kind="passage",
            width=width,
            height=height,
            label="Side sheet",
        )
        origin.exits.append(exit_state)
        return exit_state

    def _find_fd_side_sheet_expansion_exit(
        self,
        session: SessionState,
    ) -> tuple[TileState, ExitState] | None:
        side_tiles = [tile for tile in session.map_state.tiles if tile.fd_side_sheet]
        for tile in reversed(side_tiles):
            for exit_state in tile.exits:
                if exit_state.status != "blocked" and not exit_state.destination_tile_id:
                    return tile, exit_state
        return None

    def _place_fd_side_sheet_room(
        self,
        session: SessionState,
        origin: TileState,
        exit_state: ExitState,
        *,
        show_rolls: bool,
        explain_math: bool = False,
    ) -> TileState | None:
        from .experience import unlimited_map_element_cap
        from .forsaken_depths_map import is_fd_ruleset
        from .heroic_skill_effects import mark_tile_visited

        cap = unlimited_map_element_cap(session)
        if cap is not None and len(session.map_state.tiles) >= cap:
            return None
        new_tile = self._generate_tile(
            session=session,
            origin=origin,
            origin_exit=exit_state,
            hcl=self._highest_character_level(session.party),
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if new_tile is None:
            exit_state.status = "unexplored"
            exit_state.destination_tile_id = None
            return None
        if session.fd_side_sheet_active:
            new_tile.fd_side_sheet = True
        exit_state.destination_tile_id = new_tile.id
        session.map_state.tiles.append(new_tile)
        self._strip_neighbor_origin_overlap(origin, new_tile, exit_state)
        self._set_reciprocal_exit(new_tile, origin, exit_state)
        self._connect_reserved_exits_to_neighbor(session, new_tile, origin, exit_state)
        for tile in session.map_state.tiles:
            if tile.id != new_tile.id:
                self._clip_origin_visible_for_neighbor(tile, new_tile)
        self._persist_open_connection(session, origin, exit_state)
        mark_tile_visited(session, new_tile.id)
        self._maybe_fd_revelation_preview_room(session, new_tile, show_rolls=show_rolls)
        if is_fd_ruleset(session) and session_tile_catalog(session) == "forsaken_depths_rivers":
            self._fd_on_river_stretch_entered(session, new_tile, show_rolls=show_rolls)
        self._fd_on_area_entered(session, new_tile, show_rolls=show_rolls)
        return new_tile

    def pregenerate_fd_citadel_side_sheet_rooms(
        self,
        session: SessionState,
        *,
        show_rolls: bool = True,
    ) -> int:
        """Place remaining citadel side-sheet tiles without moving the party (FD p.60)."""
        if not session.fd_side_sheet_active or session.fd_side_sheet_kind != "citadel":
            return 0
        placed = 0
        target = max(0, session.fd_side_sheet_rooms_total)
        while len([tile for tile in session.map_state.tiles if tile.fd_side_sheet]) < target:
            expansion = self._find_fd_side_sheet_expansion_exit(session)
            if expansion is None:
                break
            origin, exit_state = expansion
            if self._place_fd_side_sheet_room(
                session,
                origin,
                exit_state,
                show_rolls=show_rolls,
            ) is None:
                break
            placed += 1
        if placed and show_rolls:
            total = len([tile for tile in session.map_state.tiles if tile.fd_side_sheet])
            session.log.append(
                f"Citadel side sheet: {total} rooms placed on the map "
                f"({session.fd_side_sheet_rooms_total} room budget, FD p.60)."
            )
        return placed

    def _enter_fd_side_sheet(self, session: SessionState, *, show_rolls: bool) -> None:
        if session.mode != "exploration":
            session.log.append("Enter a side dungeon during exploration.")
            return
        tile = self._current_tile(session)
        from .forsaken_depths_side_sheet import enter_fd_side_sheet

        enter_fd_side_sheet(self, session, tile, show_rolls=show_rolls)

    def _exit_fd_side_sheet(self, session: SessionState, *, show_rolls: bool) -> None:
        if session.mode != "exploration":
            session.log.append("Return from a side dungeon during exploration.")
            return
        from .forsaken_depths_side_sheet import exit_fd_side_sheet

        exit_fd_side_sheet(self, session, show_rolls=show_rolls)

    def _seed_tile_features(
        self,
        tile: TileState,
        hcl: int,
        *,
        show_rolls: bool,
        session: SessionState | None = None,
    ) -> None:
        if (tile.content_key in {"treasure", "trap_treasure"} or any("treasure" in item.lower() for item in tile.objects)) and not tile.treasure_summary:
            outcome = self._roll_treasure(session)
            if show_rolls and session is not None:
                session.log.extend(outcome.log)
            if session is not None:
                self._stage_treasure_outcome(session, tile, outcome, show_rolls=show_rolls)
            elif outcome.gold or outcome.items:
                tile.treasure_summary = outcome.summary
                tile.treasure_gold = outcome.gold
                tile.treasure_items = list(outcome.items)
        if (tile.content_key == "trap_treasure" or any("trap" in item.lower() for item in tile.objects)) and not tile.trap_key:
            if session is not None and is_fd_ruleset(session):
                trap = self.table_roller.roll_fd_trap(
                    hcl,
                    show_rolls=show_rolls,
                    explain_math=False,
                )
            else:
                trap = self.table_roller.roll_trap(
                    hcl,
                    show_rolls=show_rolls,
                    explain_math=False,
                    environment=session.environment if session else "dungeon",
                )
            tile.trap_key = trap.trap_key
            tile.trap_level = trap.trap_level
            tile.objects = [item for item in tile.objects if item.lower() != "trap"] + [trap.summary]
        self._apply_treasure_doubling(tile)

    def _apply_empty_treasure_description(self, tile: TileState, empty_msg: str) -> None:
        if tile.content_key == "trap_treasure":
            tile.description = tile.description.replace(
                "Treasure is protected by a trap.",
                f"{empty_msg} A trap remains.",
            )
        elif tile.content_key == "treasure":
            tile.description = tile.description.replace("There is treasure here.", empty_msg)
            tile.content_key = "empty"
        elif "There is treasure here." in tile.description:
            tile.description = tile.description.replace("There is treasure here.", empty_msg)

    def _apply_treasure_doubling(self, tile: TileState) -> None:
        if not tile.treasure_doubled or not tile.treasure_gold:
            return
        tile.treasure_gold *= 2
        if tile.treasure_summary:
            tile.treasure_summary = f"{tile.treasure_summary} (doubled behind secret door: {tile.treasure_gold}gp)."

    def _final_boss_summary_gold_cap(self, tile: TileState) -> int | None:
        if not tile.final_boss_treasure or not tile.treasure_summary:
            return None
        amounts = [int(match) for match in re.findall(r"(\d+)\s*gp", tile.treasure_summary, flags=re.IGNORECASE)]
        return max(amounts) if amounts else None

    def _prepare_tile_features(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if tile.trap_key and not tile.trap_resolved and not tile.enemies:
            if self._consume_mycelial_warning(session, tile, "Trap"):
                tile.trap_resolved = True
                tile.objects = [item for item in tile.objects if "trap" not in item.lower()]
                return
            session.log.append("A trap waits in this area. Resolve it before claiming treasure.")
        if tile.content_key == "special_event" and tile.special_event_key is None:
            self._apply_special_event(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        elif tile.content_key == "special_feature" and tile.special_event_key is None and not tile.resolved:
            self._apply_special_feature(session, tile, show_rolls=show_rolls, explain_math=explain_math)
        elif is_fd_ruleset(session) and tile.content_key == "fd_hallucination" and not tile.resolved:
            from .forsaken_depths_content import apply_fd_hallucination

            apply_fd_hallucination(
                self,
                session,
                tile,
                hcl=self._highest_character_level(session.party),
                show_rolls=show_rolls,
            )
        elif is_fd_ruleset(session) and tile.content_key == "fd_event" and tile.special_event_key and not tile.environment_event_resolved:
            from .forsaken_depths_content import apply_fd_event

            apply_fd_event(
                self,
                session,
                tile,
                hcl=self._highest_character_level(session.party),
                show_rolls=show_rolls,
            )
        elif is_fd_ruleset(session) and tile.fd_side_sheet and not tile.resolved:
            from .forsaken_depths_side_sheet import apply_fd_side_sheet_room

            apply_fd_side_sheet_room(self, session, tile, show_rolls=show_rolls)
        elif tile.content_key in {"abyss_special_feature", "abyss_unique_event"} and tile.special_event_key and not tile.resolved:
            self._apply_abyss_pending_feature_or_event(
                session,
                tile,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
        elif is_fd_ruleset(session):
            from .forsaken_depths_content import maybe_fd_stirs_on_tile_enter

            maybe_fd_stirs_on_tile_enter(
                self,
                session,
                tile,
                hcl=self._highest_character_level(session.party),
                show_rolls=show_rolls,
            )
        if session.pending_tile_content_choice_tile_id == tile.id:
            session.log.append(
                "Event: This area is empty and searchable, or you may spend 2 Clues to find a secret passage."
            )

    def _apply_abyss_pending_feature_or_event(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        key = tile.special_event_key or ""
        if key == "room_of_horrors":
            self._resolve_abyss_room_of_horrors(session, tile, show_rolls=show_rolls)
            return
        if key == "dark_plague":
            self._resolve_abyss_dark_plague(session, tile, show_rolls=show_rolls)
            return
        if key == "mana_sink":
            self._resolve_abyss_mana_sink(session, tile, show_rolls=show_rolls)
            return
        choice_labels = {
            "enchanted_banquet": "eat from the Enchanted Banquet or leave it alone",
            "lava_river": "choose a hero to leap the Lava River or leave the item",
            "chained_monster": "free, kill, or leave the chained Abyss boss",
            "repository_secret_knowledge": "research the repository or leave it alone",
            "puzzle_room": "choose a hero to solve the Abyss puzzle box or leave it alone",
            "book_of_secrets": "choose a reader for the Book of Secrets or leave it alone",
            "swarm_of_critters": "cast Fireball or endure the swarm",
            "secret_stairs": "take the secret stairs or leave them alone",
            "gold_ghost": "pay 100gp or refuse the Gold Ghost",
        }
        if key in choice_labels:
            session.log.append(f"Abyss event: {choice_labels[key]}.")

    def _mark_environment_event_resolved(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        tile.environment_event_resolved = True
        session.dwarf_miner_gems_available = 0
        session.dwarf_miner_trade_preview_done = False
        fire_imported_triggers(self, session, tile, "on_feature", show_rolls=show_rolls)

    def _mark_special_feature_resolved(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
    ) -> None:
        tile.resolved = True
        fire_imported_triggers(self, session, tile, "on_feature", show_rolls=show_rolls)

    def _apply_special_event(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        hcl = self._highest_character_level(session.party)
        outcome = self.table_roller.roll_special_event(
            healer_met=session.wandering_healer_met,
            alchemist_met=session.wandering_alchemist_met,
            lady_in_white_refused=session.lady_in_white_refused,
            environment=session.environment,
        )
        tile.special_event_key = outcome.key
        tile.special_event_summary = outcome.result
        session.log.append(f"Event: {outcome.result}")
        if outcome.key == "ghost":
            self._resolve_ghost_event(session, show_rolls=show_rolls)
        elif outcome.key == "wandering_monsters":
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls, special_event=True)
        elif outcome.key == "lady_in_white":
            if session.active_quest is not None:
                session.log.append("The Lady in White waits while your current Quest is unfinished.")
            elif session.lady_in_white_refused:
                session.log.append("The Lady in White will not appear again this adventure.")
            else:
                tile.lady_in_white_available = True
                session.log.append(
                    "Event: The Lady in White offers a Quest. Accept to roll on the Quest Table; "
                    "refuse and she will not appear again this adventure."
                )
        elif outcome.key == "trap":
            trap = self.table_roller.roll_trap(
                hcl,
                show_rolls=show_rolls,
                explain_math=explain_math,
                environment=session.environment,
            )
            tile.trap_key = trap.trap_key
            tile.trap_level = trap.trap_level
            tile.objects.append(trap.summary)
            session.log.append(f"Event: Trap triggered: {trap.summary}")
        elif outcome.key == "trap_rare_item":
            trap = self.table_roller.roll_trap(
                hcl,
                show_rolls=show_rolls,
                explain_math=explain_math,
                environment=session.environment,
            )
            item = self.table_roller.roll_magic_treasure(environment=session.environment)
            tile.trap_key = trap.trap_key
            tile.trap_level = trap.trap_level
            tile.objects.append(trap.summary)
            tile.treasure_summary = item.summary
            tile.treasure_items = self._finalize_treasure_items(session, list(item.items), show_rolls=show_rolls)
            session.log.append(f"Event: Trap triggered: {trap.summary}")
            session.log.append(f"Event: Rare item found: {item.summary}")
            self._mark_environment_event_resolved(session, tile)
        elif outcome.key == "healer":
            session.wandering_healer_met = True
            tile.healer_available = True
            session.log.append(
                "Event: A wandering healer is here: 10gp restores 1 Life (use Buy Healing on party sheets)."
            )
        elif outcome.key == "alchemist":
            session.wandering_alchemist_met = True
            if tile.id not in session.alchemist_event_tile_ids:
                session.alchemist_event_tile_ids.append(tile.id)
            tile.alchemist_available = True
            session.log.append(
                "Event: A wandering alchemist is here: Potion of Healing 50gp or blade poison 30gp, once per hero."
            )
        elif outcome.key == "spore_cloud":
            self._resolve_fungal_spore_cloud_event(session, hcl, show_rolls=show_rolls)
            self._mark_environment_event_resolved(session, tile)
        elif outcome.key in ENVIRONMENT_EVENT_KEYS:
            self._announce_environment_event_choice(session, tile)
        tile.objects = [item for item in tile.objects if item != "Special Event"]

    def _announce_environment_event_choice(self, session: SessionState, tile: TileState) -> None:
        key = tile.special_event_key or ""
        if key == "dwarf_party_gem" and not self._has_living_class(session, "dwarf"):
            self._mark_environment_event_resolved(session, tile)
            session.log.append("Event: No dwarf is in the party, so the gem seam is ignored.")
            return
        if key == "mycelial_warning" and not self._has_living_class(session, "mushroom_monk"):
            self._mark_environment_event_resolved(session, tile)
            session.log.append("Event: No mushroom monk senses the mycelial warning.")
            return
        if key == "fungal_merchant" and session.fungal_merchant_met:
            tile.special_event_key = "halfling_scout"
            tile.special_event_summary = "Repeat fungal merchant counts as the halfling scout event."
            session.log.append("Event: This merchant was already met; count this as the halfling scout result (roll 1).")
        if key == "dwarf_miner":
            gems = roll_d6()
            session.dwarf_miner_gems_available = gems
            session.log.append(f"Event: The dwarf miner offers up to {gems} gem(s) for 25gp each.")
        session.log.append("Event: Choose how to resolve this PDF special event from the map marker.")

    def _resolve_environment_event(
        self,
        session: SessionState,
        choice: str | None,
        *,
        character_id: str | None = None,
        item_name: str | None = None,
        target_weapon: str | None = None,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Resolve special events during exploration.")
            return
        tile = self._active_tile(session)
        key = tile.special_event_key or ""
        if tile.content_key != "special_event" or key not in ENVIRONMENT_EVENT_KEYS or tile.environment_event_resolved:
            if not (
                session.adventure_type == "imported"
                and tile.content_key.startswith(IMPORTED_ROOM_PREFIX)
                and key in ENVIRONMENT_EVENT_KEYS
                and not tile.environment_event_resolved
            ):
                session.log.append("No pending caverns or fungal special-event choice here.")
                return
        if any(enemy.life > 0 for enemy in tile.enemies):
            session.log.append("Resolve the encounter before handling the special event.")
            return
        if key == "cavemen_explorers":
            self._resolve_cavemen_event(session, tile, choice, food_required=2, count=roll_d6(), label="Cavemen explorers")
            return
        if key == "fungal_cavemen":
            count = roll_d6() + 2
            if choice == "feed_mushroom":
                if not self._consume_rare_mushroom(session):
                    session.log.append("Fungal cavemen require 1 rare mushroom or 4 Food rations.")
                    return
                self._mark_environment_event_resolved(session, tile)
                session.log.append("Event: The party gives the fungal cavemen 1 rare mushroom.")
                self._show_fungal_cavemen_passage(
                    session,
                    tile,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
                return
            self._resolve_cavemen_event(
                session,
                tile,
                choice,
                food_required=4,
                count=count,
                label="Fungal cavemen",
                on_feed=lambda: self._show_fungal_cavemen_passage(
                    session,
                    tile,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                ),
            )
            return
        if key == "morlock_spy":
            self._resolve_paid_scout_event(
                session,
                tile,
                choice,
                cost=5,
                flag_name="caverns_morlock_warning",
                status=None,
                paid_log="Event: The morlock spy accepts 5gp; morlocks cannot surprise the party until the caverns are left.",
            )
            return
        if key == "cave_goblin_scout":
            self._resolve_paid_scout_event(
                session,
                tile,
                choice,
                cost=10,
                flag_name="caverns_scout_warning",
                status="Scout Warning +1 Saves (caverns)",
                paid_log="Event: The cave goblin scout accepts 10gp; no foes surprise the party and all Saves get +1 until the caverns are left.",
            )
            return
        if key == "halfling_scout":
            self._resolve_paid_scout_event(
                session,
                tile,
                choice,
                cost=10,
                flag_name="fungal_scout_warning",
                status="Scout Warning +1 Saves (fungal)",
                paid_log="Event: The halfling scout accepts 10gp; no foes surprise the party and all Saves get +1 until the fungal grottoes are left.",
            )
            return
        if key == "dwarf_party_gem":
            self._resolve_dwarf_party_gem(session, tile, choice, show_rolls=show_rolls)
            return
        if key == "dwarf_miner":
            self._resolve_dwarf_miner(session, tile, choice, show_rolls=show_rolls, explain_math=explain_math)
            return
        if key == "fungal_merchant":
            self._resolve_fungal_merchant(
                session,
                tile,
                choice,
                character_id=character_id,
                item_key=item_name,
                target_weapon=target_weapon,
            )
            return
        if key == "mycelial_warning":
            if choice not in {"take_warning", "decline"}:
                session.log.append("Choose whether the mushroom monk keeps the mycelial warning.")
                return
            self._mark_environment_event_resolved(session, tile)
            if choice == "take_warning":
                session.mycelial_warning_ready = True
                session.log.append("Event: Mycelial warning stored; ignore the next Trap or Wandering Monsters encounter in the fungal grottoes.")
            else:
                session.log.append("Event: The party ignores the mycelial warning.")

    def _resolve_cavemen_event(
        self,
        session: SessionState,
        tile: TileState,
        choice: str | None,
        *,
        food_required: int,
        count: int,
        label: str,
        on_feed: object | None = None,
    ) -> None:
        if choice == "feed":
            if count_food_rations(session.party) < food_required or not consume_food_rations(session.party, food_required):
                session.log.append(f"{label} require {food_required} Food rations.")
                return
            self._mark_environment_event_resolved(session, tile)
            session.log.append(f"Event: The party gives {food_required} Food ration(s) to the {label.lower()}.")
            if callable(on_feed):
                on_feed()
            return
        if choice == "fight":
            hcl = self._highest_character_level(session.party)
            level = hcl + 3
            tile.enemies = [
                EnemyState(
                    id=uuid4().hex,
                    name="Caveman",
                    category="minions",
                    level=level,
                    life=1,
                    max_life=1,
                    attacks=1,
                    tags=["minions", "caveman"],
                    initial_count=count,
                )
                for _ in range(max(1, count))
            ]
            tile.initial_enemy_count = len(tile.enemies)
            self._mark_environment_event_resolved(session, tile)
            self._begin_combat(session, f"{label} attack!", show_rolls=True, tile=tile)
            return
        if choice == "decline":
            self._mark_environment_event_resolved(session, tile)
            session.log.append(f"Event: The party refuses the {label.lower()}; they move on.")
            return
        session.log.append(f"Choose whether to feed or fight the {label.lower()}.")

    def _resolve_paid_scout_event(
        self,
        session: SessionState,
        tile: TileState,
        choice: str | None,
        *,
        cost: int,
        flag_name: str,
        status: str | None,
        paid_log: str,
    ) -> None:
        if choice == "decline":
            self._mark_environment_event_resolved(session, tile)
            session.log.append("Event: The scout walks away.")
            return
        if choice != "pay":
            session.log.append(f"Choose whether to pay {cost}gp or let the scout walk away.")
            return
        paid, log = self._spend_party_gold(session, cost)
        if not paid:
            session.log.append(f"The party needs {cost}gp to pay this scout.")
            return
        self._mark_environment_event_resolved(session, tile)
        setattr(session, flag_name, True)
        session.log.extend(log)
        if status:
            for member in session.party:
                if member.current_life > 0 and status not in member.statuses:
                    member.statuses.append(status)
        session.log.append(paid_log)

    def _resolve_dwarf_party_gem(self, session: SessionState, tile: TileState, choice: str | None, *, show_rolls: bool) -> None:
        if not self._has_living_class(session, "dwarf"):
            self._mark_environment_event_resolved(session, tile)
            session.log.append("Event: No dwarf is in the party, so the gem seam is ignored.")
            return
        if choice == "decline":
            self._mark_environment_event_resolved(session, tile)
            session.log.append("Event: The party leaves the dwarf-only gem seam alone.")
            return
        if choice != "claim":
            session.log.append("Choose whether the dwarf claims the gem and risks Wandering Monsters.")
            return
        value_roll = roll_d6()
        risk_roll = roll_d6()
        value = value_roll * 10
        if show_rolls:
            session.log.append(f"Dwarf gem value: d6 = {value_roll} -> {value}gp.")
            session.log.append(f"Dwarf gem wandering roll: d6 = {risk_roll}.")
        tile.treasure_items.append(f"Gem ({value}gp)")
        tile.treasure_summary = f"Dwarf gem worth {value}gp."
        tile.treasure_claimed = False
        self._mark_environment_event_resolved(session, tile)
        session.log.append(f"Event: The dwarf finds a gem worth {value}gp. Use Claim Treasure.")
        if risk_roll == 1:
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)

    def _resolve_dwarf_miner(
        self,
        session: SessionState,
        tile: TileState,
        choice: str | None,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if choice == "decline":
            self._mark_environment_event_resolved(session, tile)
            session.log.append("Event: The party makes no trade with the dwarf miner.")
            return
        if choice == "buy_gem":
            if session.dwarf_miner_gems_available <= 0:
                session.log.append("The dwarf miner has no more gems to sell.")
                return
            paid, log = self._spend_party_gold(session, 25)
            if not paid:
                session.log.append("The party needs 25gp to buy a gem from the dwarf miner.")
                return
            tile.treasure_items.append("Gem (25gp)")
            tile.treasure_summary = "Dwarf miner trade: Gem (25gp)."
            tile.treasure_claimed = False
            session.dwarf_miner_gems_available -= 1
            session.log.extend(log)
            session.log.append("Event: The party buys a 25gp gem from the dwarf miner.")
            if not session.dwarf_miner_trade_preview_done:
                self._reveal_next_tile_from_trade(session, tile, show_rolls=show_rolls, explain_math=explain_math)
                session.dwarf_miner_trade_preview_done = True
            if session.dwarf_miner_gems_available > 0:
                session.log.append("Event: The dwarf miner still has gems for sale.")
                return
            self._mark_environment_event_resolved(session, tile)
            return
        if choice == "sell_gems":
            sold = self._sell_matching_inventory(session, "gem", 25)
            if sold <= 0:
                session.log.append("No carried gems are available to sell to the dwarf miner.")
                return
            session.log.append(f"Event: The party sells {sold} gem(s) to the dwarf miner for {sold * 25}gp.")
            if not session.dwarf_miner_trade_preview_done:
                self._reveal_next_tile_from_trade(session, tile, show_rolls=show_rolls, explain_math=explain_math)
                session.dwarf_miner_trade_preview_done = True
            session.log.append("Event: You may continue trading with the dwarf miner.")
            return
        session.log.append("Choose whether to buy one 25gp gem, sell gems, or make no trade.")

    def _resolve_fungal_merchant(
        self,
        session: SessionState,
        tile: TileState,
        choice: str | None,
        *,
        character_id: str | None,
        item_key: str | None,
        target_weapon: str | None = None,
    ) -> None:
        if choice == "decline":
            self._mark_environment_event_resolved(session, tile)
            session.fungal_merchant_met = True
            session.log.append("Event: The party makes no trade with the fungal merchant.")
            return
        if choice == "sell_gems":
            sold = self._sell_matching_inventory(session, "gem", 25)
            if sold <= 0:
                session.log.append("No carried gems are available to sell to the fungal merchant.")
                return
            self._mark_environment_event_resolved(session, tile)
            session.fungal_merchant_met = True
            session.log.append(f"Event: The party sells {sold} gem(s) to the fungal merchant for {sold * 25}gp.")
            return
        if choice == "sell_mushrooms":
            sold, gold, sale_log = self._sell_rare_mushrooms(session)
            if sold <= 0:
                session.log.append("No carried rare mushrooms are available to sell to the fungal merchant.")
                return
            self._mark_environment_event_resolved(session, tile)
            session.fungal_merchant_met = True
            session.log.extend(sale_log)
            session.log.append(f"Event: The party sells {sold} rare mushroom(s) to the fungal merchant for {gold}gp.")
            return
        if choice == "buy_equipment":
            self._buy_fungal_merchant_equipment(session, tile, character_id, item_key, target_weapon=target_weapon)
            return
        session.log.append("Choose whether to buy equipment, sell gems, sell rare mushrooms, or decline the fungal merchant.")

    def _buy_fungal_merchant_equipment(
        self,
        session: SessionState,
        tile: TileState,
        character_id: str | None,
        item_key: str | None,
        *,
        target_weapon: str | None = None,
    ) -> None:
        if not character_id or not item_key:
            session.log.append("Choose a hero and equipment item for the fungal merchant purchase.")
            return
        buyer = next(
            (member for member in session.party if member.character_id == character_id and member.current_life > 0),
            None,
        )
        if buyer is None:
            session.log.append("Choose a living hero to receive the fungal merchant purchase.")
            return
        shop_item = self._equipment_shop_item(item_key)
        if shop_item is None:
            session.log.append("Unknown fungal merchant equipment item.")
            return
        allowed, message = can_class_use_item(buyer.class_id, shop_item)
        if not allowed:
            session.log.append(message)
            return
        item_key_normalized = str(shop_item.get("key", "")).strip().lower()
        from .weapon_finishes import WEAPON_SERVICE_KEYS, apply_weapon_service_to_member

        if item_key_normalized in WEAPON_SERVICE_KEYS:
            if not target_weapon:
                session.log.append("Choose a weapon from that hero's inventory for this service.")
                return
            if target_weapon not in buyer.inventory:
                session.log.append(f"{buyer.name} does not carry {target_weapon}.")
                return
            base_price = int(shop_item.get("price_gp", 0))
            price = (base_price * 6 + 4) // 5
            paid, log = self._spend_party_gold(session, price)
            if not paid:
                session.log.append(f"The party needs {price}gp to buy {shop_item.get('name', 'service')} from the fungal merchant.")
                return
            ok, service_message = apply_weapon_service_to_member(buyer, item_key_normalized, target_weapon)
            if not ok:
                session.log.append(service_message)
                return
            prune_weapon_defaults(buyer)
            self._mark_environment_event_resolved(session, tile)
            session.fungal_merchant_met = True
            session.log.extend(log)
            session.log.append(
                f"Event: {buyer.name} buys {shop_item.get('name', 'service')} for {target_weapon} from the fungal merchant for {price}gp. {service_message}"
            )
            return
        item_name = str(shop_item.get("name", "")).strip()
        if not item_name:
            session.log.append("Unknown fungal merchant equipment item.")
            return
        can_receive, reason = can_add_item(buyer, item_name, servant_active=buyer.character_id in self._servant_owner_ids(session))
        if not can_receive:
            session.log.append(reason)
            return
        base_price = int(shop_item.get("price_gp", 0))
        price = (base_price * 6 + 4) // 5
        paid, log = self._spend_party_gold(session, price)
        if not paid:
            session.log.append(f"The party needs {price}gp to buy {item_name} from the fungal merchant.")
            return
        buyer.inventory.append(item_name)
        prune_weapon_defaults(buyer)
        self._mark_environment_event_resolved(session, tile)
        session.fungal_merchant_met = True
        session.log.extend(log)
        session.log.append(f"Event: {buyer.name} buys {item_name} from the fungal merchant for {price}gp.")

    def _equipment_shop_item(self, item_key: str) -> dict | None:
        normalized = item_key.strip().lower()
        for item in self.rules.equipment_shop().get("items", []):
            if str(item.get("key", "")).lower() == normalized:
                return item
        return None

    def _show_fungal_cavemen_passage(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if "Secret Passage to caves" not in tile.objects:
            tile.objects.append("Secret Passage to caves")
        previous = session.environment
        self._open_secret_passage_destination(
            session,
            tile,
            "caverns",
            previous_environment=previous,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        session.log.append(
            "Event: The fed cavemen show a secret passage leading from the fungal grottoes to the caves."
        )

    def _spend_party_gold(self, session: SessionState, amount: int) -> tuple[bool, list[str]]:
        living = [member for member in session.party if member.current_life > 0]
        if sum(member.gold for member in living) < amount:
            return False, []
        remaining = amount
        paid: list[str] = []
        for member in living:
            take = min(member.gold, remaining)
            if take <= 0:
                continue
            member.gold -= take
            remaining -= take
            paid.append(f"{member.name} -{take}gp")
            if remaining <= 0:
                break
        return True, [f"Payment: {', '.join(paid)}."]

    def _sell_matching_inventory(self, session: SessionState, needle: str, value: int) -> int:
        sold = 0
        for member in session.party:
            kept: list[str] = []
            for item in member.inventory:
                if needle.lower() in item.lower():
                    sold += 1
                else:
                    kept.append(item)
            member.inventory = kept
        if sold:
            distribute_gold_among(
                [member for member in session.party if member.current_life > 0],
                sold * value,
                servant_owner_ids=self._servant_owner_ids(session),
            )
        return sold

    def _sell_rare_mushrooms(self, session: SessionState) -> tuple[int, int, list[str]]:
        sold = 0
        gold = 0
        log: list[str] = []
        for member in session.party:
            kept: list[str] = []
            for item in member.inventory:
                if not is_mushroom(item):
                    kept.append(item)
                    continue
                value, value_log = mushroom_resale_value(item, member, show_rolls=True)
                log.extend(value_log)
                if value is None:
                    kept.append(item)
                    continue
                sold += 1
                gold += value
                log.append(f"{member.name} sells {item} for {value}gp.")
            member.inventory = kept
        if gold:
            distribute_gold_among(
                [member for member in session.party if member.current_life > 0],
                gold,
                servant_owner_ids=self._servant_owner_ids(session),
            )
        return sold, gold, log

    def _consume_rare_mushroom(self, session: SessionState) -> bool:
        for member in session.party:
            for index, item in enumerate(member.inventory):
                if is_mushroom(item):
                    del member.inventory[index]
                    return True
        return False

    def _has_living_class(self, session: SessionState, class_id: str) -> bool:
        return any(member.current_life > 0 and member.class_id.lower() == class_id for member in session.party)

    def _reveal_next_tile_from_trade(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
        source: str = "Dwarf miner",
    ) -> None:
        exit_state = next((item for item in tile.exits if item.status != "blocked" and item.destination_tile_id is None), None)
        if exit_state is None:
            session.log.append(f"{source} cannot preview the next tile — no unrevealed opening is available here.")
            return
        exit_state.status = "open"
        if exit_state.kind == "door":
            exit_state.door_open = True
        preview = self._generate_tile(
            session=session,
            origin=tile,
            origin_exit=exit_state,
            hcl=self._highest_character_level(session.party),
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if preview is None:
            session.log.append(f"{source} cannot preview the next tile — no legal map placement is available.")
            return
        exit_state.destination_tile_id = preview.id
        session.map_state.tiles.append(preview)
        self._strip_neighbor_origin_overlap(tile, preview, exit_state)
        self._set_reciprocal_exit(preview, tile, exit_state)
        self._persist_open_connection(session, tile, exit_state)
        session.log.append(f"{source} reveals the next tile: {preview.title} — {preview.description}")

    def _consume_mycelial_warning(self, session: SessionState, tile: TileState, reason: str) -> bool:
        if not session.mycelial_warning_ready or session.environment != "fungal_grottoes":
            return False
        session.mycelial_warning_ready = False
        session.log.append(f"Mycelial warning: the party ignores this {reason} encounter in the fungal grottoes.")
        return True

    def _clear_environment_warning_statuses(
        self,
        session: SessionState,
        *,
        previous_environment: str,
        new_environment: str,
    ) -> None:
        if previous_environment == new_environment:
            return
        if previous_environment == "caverns":
            session.caverns_morlock_warning = False
            session.caverns_scout_warning = False
            self._remove_status_from_party(session, "Scout Warning +1 Saves (caverns)")
        if previous_environment == "fungal_grottoes":
            session.fungal_scout_warning = False
            session.mycelial_warning_ready = False
            self._remove_status_from_party(session, "Scout Warning +1 Saves (fungal)")

    def _remove_status_from_party(self, session: SessionState, status: str) -> None:
        for member in session.party:
            member.statuses = [entry for entry in member.statuses if entry != status]

    def _tick_phoenix_mushrooms(self, session: SessionState) -> None:
        for member in session.party:
            updated: list[str] = []
            expired = False
            for status in member.statuses:
                lower = status.lower()
                if not lower.startswith("phoenix mushroom"):
                    updated.append(status)
                    continue
                match = re.search(r"\((\d+)\s+tiles?\)", status, re.IGNORECASE)
                remaining = int(match.group(1)) if match else 3
                remaining -= 1
                if remaining > 0:
                    updated.append(f"Phoenix Mushroom ({remaining} tiles)")
                else:
                    expired = True
            member.statuses = updated
            if expired:
                member.current_life = max(0, member.current_life - 1)
                session.log.append(
                    f"Phoenix Mushroom fades from {member.name}; {member.name} loses 1 Life "
                    f"({member.current_life}/{member.max_life})."
                )

    def _tick_toxic_spores(self, session: SessionState) -> None:
        for member in session.party:
            updated: list[str] = []
            expired = False
            for status in member.statuses:
                lower = status.lower()
                if not lower.startswith("toxic spores"):
                    updated.append(status)
                    continue
                match = re.search(r"(\d+)\s+rooms?", status, re.IGNORECASE)
                remaining = int(match.group(1)) if match else 6
                remaining -= 1
                if remaining > 0:
                    updated.append(f"Toxic Spores (-1 Saves, {remaining} rooms)")
                else:
                    expired = True
            member.statuses = updated
            if expired:
                session.log.append(f"Toxic spores clear from {member.name}; Save penalty removed.")

    def _tick_abyss_room_entry_afflictions(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> None:
        from .abyss_afflictions import tick_dark_plague_on_room_entry

        session.log.extend(tick_dark_plague_on_room_entry(session, tile, show_rolls=show_rolls))

    def _tile_has_morlocks(self, tile: TileState) -> bool:
        return any(
            enemy.life > 0
            and ("morlock" in enemy.name.lower() or "morlock" in {tag.lower() for tag in enemy.tags})
            for enemy in tile.enemies
        )

    def _resolve_ghost_event(self, session: SessionState, *, show_rolls: bool) -> None:
        from .heroic_skill_effects import resolve_fear_save
        from .madness import madness_points

        fear_level = 4
        for member in session.party:
            if member.current_life <= 0:
                continue
            before_madness = madness_points(member)
            before_pending = session.pending_madness_choice
            saved, fear_log = resolve_fear_save(
                session,
                member,
                fear_level,
                party=session.party,
                show_rolls=show_rolls,
                label="fear",
                madness_source="the ghost",
            )
            session.log.extend(fear_log)
            if not saved:
                if session.pending_madness_choice is before_pending and madness_points(member) == before_madness:
                    session.log.extend(
                        apply_madness_gain(
                            session,
                            member,
                            source="the ghost",
                            show_rolls=show_rolls,
                        )
                    )
                session.log.append(f"Event: {member.name} fails the ghost fear save.")

    def _resolve_fungal_spore_cloud_event(self, session: SessionState, hcl: int, *, show_rolls: bool) -> None:
        poison_level = max(1, hcl)
        for member in session.party:
            if member.current_life <= 0:
                continue
            if member.class_id.lower() == "mushroom_monk":
                session.log.append(f"Event: {member.name} is immune to the spore cloud.")
                continue
            modifier = save_modifier(member, poison=True) + encumbrance_penalty(member)
            if member.class_id.lower() in {"halfling", "barbarian"}:
                modifier += member.level
            total, rolls = roll_exploding_for_level(member)
            if show_rolls:
                detail = f" {' + '.join(str(value) for value in rolls)}"
                if modifier:
                    detail += f" + {modifier}"
                session.log.append(f"Spore cloud: {member.name} Save vs L{poison_level}:{detail}.")
            if rolls[0] == 1 or total + modifier < poison_level:
                member.current_life = max(0, member.current_life - 2)
                session.log.append(f"Effect: {member.name} loses 2 Life to the spore cloud.")
            else:
                session.log.append(f"{member.name} resists the spore cloud.")

    def _resolve_abyss_room_of_horrors(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        from .heroic_skill_effects import resolve_fear_save

        for member in session.party:
            if member.current_life <= 0:
                continue
            session.log.extend(apply_madness_gain(session, member, source="Abyss Room of Horrors", show_rolls=show_rolls))
            saved, fear_log = resolve_fear_save(
                session,
                member,
                6,
                party=session.party,
                show_rolls=show_rolls,
                label="Room of Horrors fear",
                madness_source="Room of Horrors",
            )
            session.log.extend(fear_log)
            if not saved and "Abyss Room of Horrors -1 Attack" not in member.statuses:
                member.statuses.append("Abyss Room of Horrors -1 Attack")
                session.log.append(f"Effect: {member.name} suffers -1 Attack until blessed.")
        self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)

    def _resolve_abyss_dark_plague(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        living = [member for member in session.party if member.current_life > 0]
        if not living:
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        target = random.choice(living)
        from .abyss_afflictions import apply_dark_plague_exposure

        apply_dark_plague_exposure(
            target,
            session=session,
            log=session.log,
            show_rolls=show_rolls,
            source="Dark Plague",
        )
        self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)

    def _resolve_abyss_mana_sink(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        for member in session.party:
            if member.current_life <= 0:
                continue
            spells = list(member.spells or [])
            if not spells:
                continue
            kept: list[str] = []
            lost: list[str] = []
            bonus = member.level // 2
            for spell in spells:
                if self._abyss_save(member, 7, show_rolls=show_rolls, log=session.log, label=f"Mana Sink ({spell})", bonus=bonus):
                    kept.append(spell)
                else:
                    lost.append(spell)
            member.spells = kept
            if lost:
                session.log.append(f"Effect: {member.name} loses prepared spell(s): {', '.join(lost)}.")
        self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)

    def _resolve_abyss_special_feature_choice(
        self,
        session: SessionState,
        tile: TileState,
        choice: str | None,
        *,
        target_character_id: str | None,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        key = tile.special_event_key or ""
        if key == "enchanted_banquet":
            if choice == "leave_abyss_banquet":
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                session.log.append("Abyss Banquet: the party leaves the food untouched.")
                return
            if choice != "eat_abyss_banquet":
                session.log.append("Choose whether the party eats from the Enchanted Banquet.")
                return
            for member in [item for item in session.party if item.current_life > 0]:
                self._resolve_abyss_banquet_eater(session, tile, member, show_rolls=show_rolls)
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        if key == "lava_river":
            if choice == "leave_abyss_lava":
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                session.log.append("Abyss Lava River: the party leaves the item across the lava.")
                return
            if choice != "leap_abyss_lava":
                session.log.append("Choose a living hero to leap the Lava River.")
                return
            member = self._chosen_or_lead(session, target_character_id)
            if member is None:
                session.log.append("Choose a living hero to leap the Lava River.")
                return
            bonus = member.level if member.class_id.lower() == "rogue" else 0
            if member.class_id.lower() in {"halfling", "elf"}:
                bonus += 1
            if member.class_id.lower() == "dwarf" or "heavy armor" in " ".join(member.inventory).lower():
                bonus -= 1
            crossed = self._abyss_save(member, 6, show_rolls=show_rolls, log=session.log, label="Lava River leap out", bonus=bonus)
            returned = crossed and self._abyss_save(member, 6, show_rolls=show_rolls, log=session.log, label="Lava River leap back", bonus=bonus)
            if crossed:
                item = self._roll_abyss_magic_or_defense_item(defense=False)
                tile.treasure_items.append(item)
                tile.treasure_summary = f"Lava River prize: {item}."
                tile.treasure_claimed = False
                session.log.append(f"Abyss Lava River: {member.name} recovers {item}.")
            if not crossed or not returned:
                self._damage_member(member, roll_d6(), session.log, "falling into lava")
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        if key == "chained_monster":
            self._resolve_abyss_chained_monster(session, tile, choice, show_rolls=show_rolls)
            return
        if key == "repository_secret_knowledge":
            if choice == "leave_abyss_repository":
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                session.log.append("Abyss Repository: the party leaves the books alone.")
                return
            if choice != "research_abyss_repository":
                session.log.append("Choose whether to research the Repository of Secret Knowledge.")
                return
            self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls, start_combat=False)
            member = self._chosen_or_lead(session, target_character_id)
            if member:
                self._grant_clue_to_member(session, member, tile)
                if roll_die(8) <= 2:
                    session.log.extend(apply_madness_gain(session, member, source="Abyss Repository", show_rolls=show_rolls))
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        if key == "puzzle_room":
            if choice == "leave_abyss_puzzle":
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                session.log.append("Abyss Puzzle Room: the party leaves the puzzle box alone.")
                return
            if choice != "attempt_abyss_puzzle":
                session.log.append("Choose a living hero to attempt the Abyss puzzle box.")
                return
            member = self._chosen_or_lead(session, target_character_id)
            if member is None:
                session.log.append("Choose a living hero to attempt the Abyss puzzle box.")
                return
            level = roll_die(8) + 4
            bonus = member.level if member.class_id.lower() in {"wizard", "rogue"} else 0
            if self._abyss_save(member, level, show_rolls=show_rolls, log=session.log, label="Abyss puzzle box", bonus=bonus):
                outcome = self._roll_abyss_treasure_outcome()
                self._stage_treasure_outcome(session, tile, outcome, show_rolls=show_rolls)
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            else:
                self._damage_member(member, 1, session.log, "failed Abyss puzzle")
            return

    def _resolve_abyss_unique_event_choice(
        self,
        session: SessionState,
        tile: TileState,
        choice: str | None,
        *,
        target_character_id: str | None,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        key = tile.special_event_key or ""
        if key == "book_of_secrets":
            if choice == "leave_abyss_book":
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                session.log.append("Abyss Book of Secrets: the party leaves the book hidden.")
                return
            if choice != "read_abyss_book":
                session.log.append("Choose a living reader for the Book of Secrets.")
                return
            member = self._chosen_or_lead(session, target_character_id)
            if member is None:
                session.log.append("Choose a living reader for the Book of Secrets.")
                return
            clues = roll_d6()
            for _ in range(clues):
                self._grant_clue_to_member(session, member, tile)
            bonus = member.level // 2 if member.class_id.lower() == "wizard" else 0
            if not self._abyss_save(member, clues + 2, show_rolls=show_rolls, log=session.log, label="Book of Secrets madness", bonus=bonus):
                for _ in range(roll_d3()):
                    session.log.extend(apply_madness_gain(session, member, source="Book of Secrets", show_rolls=show_rolls))
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        if key == "swarm_of_critters":
            if choice == "cast_fireball_abyss_swarm":
                caster = self._chosen_or_lead(session, target_character_id)
                if caster and self._spend_prepared_spell(caster, "Fireball"):
                    session.log.append(f"Abyss Swarm: {caster.name} casts Fireball and disperses the critters.")
                    self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                    return
                session.log.append("Choose a living caster with a prepared Fireball, or endure the swarm.")
                return
            if choice != "endure_abyss_swarm":
                session.log.append("Choose Fireball or endure the Swarm of Critters.")
                return
            for member in [item for item in session.party if item.current_life > 0]:
                self._damage_member(member, 1, session.log, "Swarm of Critters")
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        if key == "secret_stairs":
            if choice == "leave_abyss_stairs":
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                session.log.append("Abyss Secret Stairs: the party leaves the passage alone.")
                return
            if choice != "take_abyss_stairs":
                session.log.append("Choose whether to take the Secret Stairs.")
                return
            if roll_d6() == 1:
                self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls, combat_message="Wandering Monsters wait on the Secret Stairs!")
            else:
                session.log.append("Abyss Secret Stairs: no wandering monsters appear.")
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        if key == "gold_ghost":
            if choice == "pay_abyss_gold_ghost":
                paid, log = self._spend_party_gold(session, 100)
                if not paid:
                    session.log.append("The party needs 100gp to appease the Gold Ghost.")
                    return
                session.log.extend(log)
                session.log.append("Abyss Gold Ghost: the spirit accepts 100gp and fades.")
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                return
            if choice != "refuse_abyss_gold_ghost":
                session.log.append("Choose whether to pay 100gp or refuse the Gold Ghost.")
                return
            for member in [item for item in session.party if item.current_life > 0]:
                if "Gold Ghost -1 Defense" not in member.statuses:
                    member.statuses.append("Gold Ghost -1 Defense")
            session.log.append("Abyss Gold Ghost: all living heroes suffer -1 Defense until individually Blessed.")
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)

    def _resolve_abyss_banquet_eater(self, session: SessionState, tile: TileState, member: PartyMemberState, *, show_rolls: bool) -> None:
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Enchanted Banquet: {member.name} rolls d6 = {roll}.")
        if roll == 1:
            healed = min(3, member.max_life - member.current_life)
            member.current_life += healed
            loss = roll_d6() * roll_d6()
            member.gold = max(0, member.gold - loss)
            session.log.append(f"Magical Food: {member.name} heals {healed} Life; a fey steals up to {loss}gp.")
            if loss <= 0 and "Magical Bells" not in member.statuses:
                member.statuses.append("Magical Bells")
        elif roll == 2:
            member.current_life = min(member.max_life, member.current_life + 1)
            session.log.append(f"Nourishing Food: {member.name} heals 1 Life.")
        elif roll == 3:
            bonus = member.level if member.class_id.lower() == "halfling" else (1 if member.class_id.lower() == "barbarian" else 0)
            if not self._abyss_save(member, 7, show_rolls=show_rolls, log=session.log, label="Spoiled lamb poison", bonus=bonus):
                member.statuses.append("Spoiled Banquet -1 Attack (2 encounters)")
        elif roll == 4:
            bonus = member.level // 2 if member.class_id.lower() in {"wizard", "cleric"} else 0
            if not self._abyss_save(member, 6, show_rolls=show_rolls, log=session.log, label="Ghost Food magic", bonus=bonus):
                session.log.extend(apply_madness_gain(session, member, source="Ghost Food", show_rolls=show_rolls))
        elif roll == 5:
            if not any(enemy.name == "Two-Headed Ogre" for enemy in tile.enemies + tile.defeated_enemies):
                tile.enemies.append(
                    EnemyState(
                        id=uuid4().hex,
                        name="Two-Headed Ogre",
                        category="boss",
                        level=7,
                        life=6,
                        max_life=6,
                        attacks=2,
                        tags=["abyss", "surprise", "fight_to_death", "abyss_treasure_rolls:1"],
                    )
                )
                tile.treasure_summary = "Two-Headed Ogre silverware worth 100gp."
                tile.treasure_gold = 100
                tile.treasure_claimed = False
                session.log.append(f"That's My Food: a two-headed ogre attacks {member.name} with surprise.")
        elif roll == 6:
            if member.class_id.lower() == "barbarian":
                session.log.append(f"Fey Food: {member.name} is a barbarian and ignores the spell gift.")
                return
            spell = self.table_roller.roll_random_basic_spell()
            spell_name = str(spell.get("spell", "Fireball")) if spell else "Fireball"
            member.inventory.append(f"One-use Fey Food spell: {spell_name}")
            session.log.append(f"Fey Food: {member.name} gains a one-use {spell_name} spell.")

    def _chosen_or_lead(self, session: SessionState, character_id: str | None) -> PartyMemberState | None:
        if character_id:
            chosen = next((member for member in session.party if member.character_id == character_id), None)
            if chosen is not None and chosen.current_life > 0:
                return chosen
        return self._member_by_marching_order(session, 1)

    def _grant_clue_to_member(self, session: SessionState, member: PartyMemberState, tile: TileState) -> None:
        member.clues += 1
        if "Clue" not in tile.objects:
            tile.objects.append("Clue")
        session.log.append(f"Effect: {member.name} gains 1 Clue (now {member.clues}).")

    def _spend_prepared_spell(self, member: PartyMemberState, spell_name: str) -> bool:
        target = spell_name.lower()
        for index, spell in enumerate(list(member.spells or [])):
            if str(spell).lower() == target:
                del member.spells[index]
                return True
        return False

    def _resolve_abyss_chained_monster(
        self,
        session: SessionState,
        tile: TileState,
        choice: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if choice == "leave_abyss_chained_monster":
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            session.log.append("Abyss Chained Monster: the party leaves the prisoner chained.")
            return
        if choice == "free_abyss_chained_monster":
            gold = roll_d6() * roll_d6()
            tile.treasure_summary = f"Chained monster reward worth {gold}gp."
            tile.treasure_gold = gold
            tile.treasure_claimed = False
            lead = self._member_by_marching_order(session, 1)
            if lead:
                self._grant_clue_to_member(session, lead, tile)
            session.log.append(
                "Abyss Chained Monster: the freed boss pays the party and may return beside the Final Boss (2-in-6; tracked in log)."
            )
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        if choice == "kill_abyss_chained_monster":
            enemies, subdesc = self._roll_abyss_monster_row(session, "abyss_boss_table", "boss")
            for enemy in enemies:
                if "no_treasure" not in enemy.tags:
                    enemy.tags.append("no_treasure")
                if "no_xp" not in enemy.tags:
                    enemy.tags.append("no_xp")
            tile.enemies.extend(enemies)
            tile.initial_enemy_count = max(tile.initial_enemy_count, len(tile.enemies))
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            session.log.append(f"Abyss Chained Monster: the party attacks the prisoner without XP or treasure. {subdesc}")
            if enemies:
                self._begin_combat(session, "The chained Abyss boss fights for its life.", tile=tile, show_rolls=show_rolls)
            return
        session.log.append("Choose whether to free, kill, or leave the chained Abyss boss.")

    def _roll_abyss_treasure_outcome(self) -> TreasureOutcome:
        extra = self._roll_abyss_treasure_extra()
        return TreasureOutcome(
            str(extra.get("treasure_summary") or "Abyss treasure."),
            int(extra.get("treasure_gold") or 0),
            list(extra.get("treasure_items") or []),
            [],
            choice_key=extra.get("pending_treasure_choice"),
        )

    def _resolve_tile_content_choice(
        self,
        session: SessionState,
        choice: str | None,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Resolve tile content choices during exploration.")
            return
        tile_id = session.pending_tile_content_choice_tile_id
        if not tile_id:
            session.log.append("No tile content choice is pending.")
            return
        tile = self._tile_by_id(session, tile_id)
        if tile is None:
            session.pending_tile_content_choice_tile_id = None
            session.log.append("The tile for this choice is no longer on the map.")
            return
        if choice == "searchable":
            session.pending_tile_content_choice_tile_id = None
            session.log.append("Event: The party keeps the area empty and searchable.")
            return
        if choice == "secret_passage_2_clues":
            if not self._spend_clues(session, 2):
                session.log.append("Not enough Clues (need 2).")
                return
            session.pending_tile_content_choice_tile_id = None
            session.log.append("Effect: The party spends 2 Clues to find a secret passage.")
            self._offer_secret_passage(session, tile, show_rolls=show_rolls)
            return
        session.log.append("Choose to keep the area searchable or spend 2 Clues for a secret passage.")

    def _dip_water_pool(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Dip into water pools during exploration.")
            return
        tile = self._active_tile(session)
        if tile.cavern_feature_key != "water_pools":
            session.log.append("No cavern water pool is here.")
            return
        member = next(
            (entry for entry in session.party if entry.character_id == character_id and entry.current_life > 0),
            None,
        )
        if member is None:
            member = next((entry for entry in session.party if entry.current_life > 0), None)
        if member is None:
            session.log.append("No living hero can dip into the pool.")
            return
        outcome = self.table_roller.roll_caverns_water_pool()
        if show_rolls:
            session.log.append(f"Water pool roll: d6 -> {outcome.key}.")
        session.log.append(f"Feature: {outcome.result}")
        if outcome.key == "contaminated":
            if member.character_id not in session.cavern_contaminated_character_ids:
                session.cavern_contaminated_character_ids.append(member.character_id)
            session.log.append(f"Effect: {member.name} suffers -1 to all Saves until cleansed.")
        elif outcome.key == "refreshing":
            if member.character_id in session.cavern_water_pool_healed_character_ids:
                session.log.append(f"Effect: {member.name} has already benefited from this pool this adventure.")
            elif member.current_life < member.max_life:
                member.current_life += 1
                session.cavern_water_pool_healed_character_ids.append(member.character_id)
                session.log.append(f"Effect: {member.name} heals 1 Life from the pool.")
            else:
                session.log.append(f"Effect: {member.name} is already at full Life.")
        else:
            session.log.append(f"Effect: {member.name} feels no change from the water.")

    def _apply_special_feature(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        hcl = self._highest_character_level(session.party)
        outcome = self.table_roller.roll_special_feature(environment=session.environment)
        session.log.append(f"Feature: {outcome.result}")
        if session.environment == "caverns":
            self._apply_cavern_special_feature(
                session,
                tile,
                outcome,
                hcl=hcl,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            tile.objects = [item for item in tile.objects if item != "Special Feature"]
            return
        if outcome.key == "fountain":
            if session.fountain_used:
                session.log.append("The fountain has no further effect this adventure.")
            else:
                session.fountain_used = True
                healed: list[str] = []
                for member in session.party:
                    if member.current_life <= 0:
                        continue
                    if member.character_id not in session.characters_who_lost_life:
                        continue
                    if member.current_life < member.max_life:
                        member.current_life += 1
                        healed.append(member.name)
                if healed:
                    session.log.append(f"Effect: Fountain restores 1 Life to {', '.join(healed)}.")
                else:
                    session.log.append(
                        "Effect: The fountain has no effect on heroes who have not lost Life this adventure."
                    )
            tile.resolved = True
        elif outcome.key == "blessed_temple":
            tile.special_event_key = "blessed_temple"
            tile.special_event_summary = outcome.result
            session.log.append(
                "Event: Blessed Temple — choose which hero receives +1 Attack vs undead or demons."
            )
        elif outcome.key == "armory":
            tile.content_key = "armory"
            session.log.append("Event: The armory allows weapon changes within class limits.")
            tile.resolved = True
        elif outcome.key == "cursed_altar":
            living = [member for member in session.party if member.current_life > 0]
            if living:
                cursed = random.choice(living)
                session.cursed_character_id = cursed.character_id
                session.log.append(
                    f"Effect: Cursed Altar curses {cursed.name} (-1 Defense until broken)."
                )
            tile.resolved = True
        elif outcome.key == "statue":
            tile.special_event_key = "statue"
            tile.special_event_summary = outcome.result
            session.log.append("Event: Statue feature awaits your choice: leave it alone or touch it.")
        elif outcome.key == "puzzle_box":
            tile.special_event_key = "puzzle_box"
            tile.special_event_summary = outcome.result
            session.log.append(
                "Event: Puzzle box awaits your choice: attempt a Save vs d6 Level or leave it alone."
            )
        tile.objects = [item for item in tile.objects if item != "Special Feature"]

    def _apply_cavern_special_feature(
        self,
        session: SessionState,
        tile: TileState,
        outcome: SubtableOutcome,
        *,
        hcl: int,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        tile.cavern_feature_key = outcome.key
        marker_labels = {
            "stalactites": "Stalactites",
            "stalagmites": "Stalagmites",
            "boulders": "Boulders",
            "echo": "Echo",
            "water_pools": "Water Pool",
        }
        marker = marker_labels.get(outcome.key)
        if marker and marker not in tile.objects:
            tile.objects.append(marker)
        if outcome.key == "water_pools":
            session.log.append("Event: Mark the water pool on the tile. Heroes may dip into it.")
        else:
            tile.resolved = True
            session.log.append(f"Event: Mark {marker or outcome.key} on the map element.")

    def _resolve_special_feature_choice(
        self,
        session: SessionState,
        choice: str | None,
        *,
        target_character_id: str | None = None,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Resolve special features during exploration.")
            return
        tile = self._active_tile(session)
        pending_keys = {
            "statue",
            "puzzle_box",
            "blessed_temple",
            "enchanted_banquet",
            "lava_river",
            "chained_monster",
            "repository_secret_knowledge",
            "puzzle_room",
            "book_of_secrets",
            "swarm_of_critters",
            "secret_stairs",
            "gold_ghost",
        }
        abyss_content_keys = {"abyss_special_feature", "abyss_unique_event"}
        if (
            (tile.content_key != "special_feature" and tile.content_key not in abyss_content_keys)
            or tile.special_event_key not in pending_keys
        ):
            if not (
                session.adventure_type == "imported"
                and tile.content_key.startswith(IMPORTED_ROOM_PREFIX)
                and tile.special_event_key in pending_keys
            ):
                session.log.append("No pending special feature choice here.")
                return
        if tile.enemies:
            session.log.append("Resolve the encounter before handling the special feature.")
            return
        hcl = self._highest_character_level(session.party)
        if tile.special_event_key == "blessed_temple":
            if choice != "bless_temple":
                session.log.append("Choose which hero receives the Blessed Temple bonus.")
                return
            chosen = (
                next((member for member in session.party if member.character_id == target_character_id), None)
                if target_character_id
                else None
            )
            if chosen is None or chosen.current_life <= 0:
                session.log.append("Choose a living hero for the blessing.")
                return
            session.blessed_undead_bonus_character_id = chosen.character_id
            session.log.append(
                f"Effect: Blessed Temple grants {chosen.name} +1 Attack vs undead or demons until one is slain."
            )
            if session.cursed_character_id:
                cursed_id = session.cursed_character_id
                session.cursed_character_id = None
                cursed = next((member for member in session.party if member.character_id == cursed_id), None)
                if cursed:
                    session.log.append(f"Effect: The curse on {cursed.name} is broken.")
            self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
            return
        if tile.special_event_key == "statue":
            if choice == "touch_statue":
                self._resolve_statue_feature(session, tile, hcl, show_rolls=show_rolls)
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                return
            if choice == "leave_statue":
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                session.log.append("Event: The party leaves the statue alone.")
                return
            session.log.append("Choose whether to touch the statue or leave it alone.")
            return
        if tile.special_event_key == "puzzle_box":
            if choice == "attempt_puzzle_box":
                chosen = (
                    next((member for member in session.party if member.character_id == target_character_id), None)
                    if target_character_id
                    else self._member_by_marching_order(session, 1)
                )
                if chosen is None or chosen.current_life <= 0:
                    session.log.append("Choose a living hero to attempt the puzzle box.")
                    return
                solved = self._resolve_puzzle_box(
                    session,
                    tile,
                    hcl,
                    member=chosen,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
                if solved:
                    self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                return
            if choice == "leave_puzzle_box":
                self._mark_special_feature_resolved(session, tile, show_rolls=show_rolls)
                session.log.append("Event: The party leaves the puzzle box alone.")
                return
            session.log.append("Choose whether to attempt the puzzle box or leave it alone.")
            return
        if tile.special_event_key in {
            "enchanted_banquet",
            "lava_river",
            "chained_monster",
            "repository_secret_knowledge",
            "puzzle_room",
        }:
            self._resolve_abyss_special_feature_choice(
                session,
                tile,
                choice,
                target_character_id=target_character_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )
            return
        if tile.special_event_key in {"book_of_secrets", "swarm_of_critters", "secret_stairs", "gold_ghost"}:
            self._resolve_abyss_unique_event_choice(
                session,
                tile,
                choice,
                target_character_id=target_character_id,
                show_rolls=show_rolls,
                explain_math=explain_math,
            )

    def _resolve_statue_feature(self, session: SessionState, tile: TileState, hcl: int, *, show_rolls: bool) -> None:
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Statue touch roll: d6 = {roll}.")
        if roll <= 3:
            level = max(1, hcl + 3)
            life = _parse_monster_life("Tier+5", hcl)
            attacks = max(1, _hcl_to_tier(hcl))
            tile.enemies.append(
                EnemyState(
                    id=uuid4().hex,
                    name="Living Statue",
                    category="boss",
                    level=level,
                    life=life,
                    max_life=life,
                    attacks=attacks,
                    tags=["boss", "artificial", "spell_immune", "living_statue"],
                )
            )
            tile.initial_enemy_count = len(tile.enemies)
            self._begin_combat(session, "The statue animates and attacks!")
        else:
            gold = resolve_gold_formula("3d6*10", hcl=0)
            tile.treasure_summary = f"Broken statue yields {gold}gp."
            tile.treasure_gold = gold
            session.log.append(f"Event: The statue breaks open, revealing {gold}gp (no XP).")

    def _resolve_puzzle_box(
        self,
        session: SessionState,
        tile: TileState,
        hcl: int,
        *,
        member: PartyMemberState,
        show_rolls: bool,
        explain_math: bool,
    ) -> bool:
        box_level = roll_d6()
        modifier = member.level if member.class_id.lower() in {"wizard", "rogue"} else 0
        modifier += expert_puzzle_bonus(session.party)
        total, rolls = roll_exploding_for_level(member)
        if show_rolls:
            detail = f" {' + '.join(str(value) for value in rolls)}"
            if modifier:
                detail += f" + {modifier}"
            session.log.append(
                f"Puzzle box (L{box_level}): {member.name} Save{detail}."
            )
        if rolls[0] != 1 and total + modifier >= box_level:
            outcome = self._roll_treasure(session)
            if show_rolls:
                session.log.extend(outcome.log)
            if outcome.choice_key:
                self._stage_treasure_outcome(session, tile, outcome, show_rolls=show_rolls)
            else:
                tile.treasure_summary = outcome.summary
                tile.treasure_gold = outcome.gold
                tile.treasure_items = self._finalize_treasure_items(session, list(outcome.items), show_rolls=show_rolls)
            session.log.append("Event: The puzzle box opens!")
            self._apply_treasure_doubling(tile)
            return True
        else:
            from .forsaken_depths_river import apply_fd_oblivion_forget_on_natural_one
            from .party_life import apply_party_life_loss

            apply_fd_oblivion_forget_on_natural_one(
                session,
                member,
                natural=rolls[0],
                show_rolls=show_rolls,
                source="puzzle Save",
            )
            apply_party_life_loss(session, member, 1)
            session.log.append(f"Effect: {member.name} takes 1 damage from the puzzle box.")
            return False

    def _listen_at_door(
        self,
        session: SessionState,
        exit_id: str | None,
        character_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Listen at a door during exploration.")
            return
        current = self._active_tile(session)
        exit_state = next((item for item in current.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door":
            session.log.append("Choose a door to listen at.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("Choose a hero to listen at the door.")
            return
        if not has_skill(member, "acute_hearing"):
            session.log.append(f"{member.name} has not learned Acute Hearing.")
            return
        if exit_state.door_listened:
            preview = exit_state.listen_preview or "You already listened at this door."
            session.log.append(preview)
            return
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Acute Hearing: {member.name} listens (d6 = {roll}; need 6+).")
        if roll < 6:
            session.log.append("You hear nothing useful.")
            return
        exit_state.door_listened = True
        exit_state.acute_hearing_cleared = True
        destination = (
            self._tile_by_id(session, exit_state.destination_tile_id)
            if exit_state.destination_tile_id
            else None
        )
        if destination and destination.enemies:
            names = sorted({enemy.name for enemy in destination.enemies if enemy.life > 0})
            preview = f"Beyond the door: {', '.join(names)}."
        elif destination:
            preview = f"Beyond the door: {destination.title} — {destination.description}"
        else:
            preview = "You hear movement beyond the door."
        exit_state.listen_preview = preview
        session.log.append(preview)
        session.log.append("Acute Hearing: foes here cannot surprise the party when you enter.")

    def _open_door(
        self,
        session: SessionState,
        exit_id: str | None,
        character_id: str | None,
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Doors can only be worked during exploration.")
            return
        current = self._active_tile(session)
        exit_state = next((item for item in current.exits if item.id == exit_id), None) if exit_id else None
        if exit_state is None or exit_state.kind != "door":
            session.log.append("Choose a door to open.")
            return
        member = (
            next((item for item in session.party if item.character_id == character_id), None)
            if character_id
            else self._member_by_marching_order(session, 1)
        )
        if member is None:
            session.log.append("That hero is not available.")
            return
        session.log.append(f"{member.name} works the {exit_state.direction} door.")
        opened, log = attempt_open_door(
            exit_state,
            member,
            hcl=self._highest_character_level(session.party),
            show_rolls=show_rolls,
            explain_math=explain_math,
            roller=self.table_roller,
            party=session.party,
            marching_order=self._marching_order_ids(session),
            servant_active=has_illusionary_servant(session, member.character_id),
        )
        session.log.extend(log)
        if not log:
            session.log.append("Nothing happens at this door.")
        if opened:
            exit_state.status = "open"
            self._sync_linked_door(session, current, exit_state)
            session.log.append(f"The {exit_state.direction} door is now open.")
        elif exit_state.door_result:
            session.log.append(f"The {exit_state.direction} door remains closed.")

    def _resolve_trap(
        self,
        session: SessionState,
        *,
        show_rolls: bool,
        explain_math: bool,
        boulder_origin: str | None = None,
        boulder_block_exit_id: str | None = None,
        snare_item_name: str | None = None,
    ) -> None:
        tile = self._current_tile(session)
        if not tile.trap_key or tile.trap_resolved:
            session.log.append("There is no active trap here.")
            return
        if session.mode == "combat":
            session.log.append("Handle the fight before disarming traps.")
            return
        pending_snare = session.pending_mycelium_snare
        if pending_snare is not None:
            if pending_snare.tile_id != tile.id:
                session.log.append("The mycelium snare choice belongs to another tile.")
                return
            if not snare_item_name:
                session.log.append("Choose which held object the mycelium snatches.")
                return
            member = next(
                (item for item in session.party if item.character_id == pending_snare.character_id),
                None,
            )
            if member is None or member.current_life <= 0:
                session.pending_mycelium_snare = None
                session.log.append("The snared hero is no longer available.")
                return
            from .fungal_traps import lose_mycelium_snare_object, resolve_mycelium_snare_item_choice, mycelium_snare_held_objects

            choices = mycelium_snare_held_objects(member)
            chosen = resolve_mycelium_snare_item_choice(choices, snare_item_name)
            if chosen is None:
                session.log.append(f"Choose a held object for {member.name}: {', '.join(choices)}.")
                return
            lost = lose_mycelium_snare_object(member, chosen)
            session.pending_mycelium_snare = None
            session.log.append(f"{member.name}'s {lost} is snatched away forever by the mycelium.")
            self._finalize_trap_resolution(session, tile, trap_log=[], show_rolls=show_rolls)
            return
        if (tile.trap_key or "").startswith("abyss_"):
            trap_log = self._resolve_abyss_trap(session, tile, show_rolls=show_rolls)
            self._finalize_trap_resolution(session, tile, trap_log=trap_log, show_rolls=show_rolls)
            return
        lead = next(
            (
                item
                for item in sorted(session.party, key=lambda row: row.marching_order)
                if item.current_life > 0 and item.marching_order == 1
            ),
            None,
        )
        if (
            session.environment == "caverns"
            and not session.miner_amulet_consumed
            and lead is not None
            and any(is_miners_amulet(item) for item in lead.inventory)
        ):
            session.miner_amulet_consumed = True
            tile.trap_resolved = True
            session.log.append(f"{lead.name}'s Miners' Amulet negates the trap.")
            self._after_trap_resolved(session, tile, show_rolls=show_rolls)
            return
        block_exit = None
        if tile.trap_key == "rolling_boulder":
            if boulder_origin not in {"front", "back"}:
                session.log.append("Rolling Boulder: choose whether it comes from the front or back of the party.")
                return
            block_exit = next(
                (
                    exit_state
                    for exit_state in tile.exits
                    if exit_state.id == boulder_block_exit_id and exit_state.status != "blocked"
                ),
                None,
            )
            if block_exit is None:
                session.log.append("Rolling Boulder: choose an accessible opening on this tile for the boulder to block.")
                return
        member = next(
            (
                item
                for item in sorted(session.party, key=lambda row: row.marching_order)
                if item.current_life > 0 and item.class_id.lower() == "rogue" and item.marching_order in {1, 2}
            ),
            None,
        )
        trap_level = tile.trap_level or self._highest_character_level(session.party)
        if member is not None:
            total, rolls = roll_exploding_for_level(member)
            modifier = member.level
            if show_rolls:
                session.log.append(
                    f"Disarm attempt: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}."
                )
            disarm_bonus = 1 if tile.trap_probed else 0
            if disarm_bonus and show_rolls:
                session.log.append("Trap was probed with a 10' pole (+1 disarm).")
            if rolls[0] != 1 and total + modifier + disarm_bonus >= trap_level:
                tile.trap_resolved = True
                session.log.append("The rogue disarms the trap.")
                self._after_trap_resolved(session, tile, show_rolls=show_rolls)
                return
            session.log.append("The rogue fails to disarm the trap.")
        gnome = next(
            (
                item
                for item in sorted(session.party, key=lambda row: row.marching_order)
                if item.current_life > 0 and item.class_id.lower() == "gnome"
            ),
            None,
        )
        if gnome is not None:
            ok, log = attempt_gnome_trap_disarm(session, gnome, trap_level, show_rolls=show_rolls)
            session.log.extend(log)
            if ok:
                tile.trap_resolved = True
                self._after_trap_resolved(session, tile, show_rolls=show_rolls)
                return
            session.log.append("The gnome fails to disarm the trap.")
        trap_log = self.table_roller.resolve_trap(
            tile.trap_key,
            tile.trap_level or self._highest_character_level(session.party),
            session.party,
            self._marching_order_ids(session),
            show_rolls=show_rolls,
            explain_math=explain_math,
            boulder_origin="back" if boulder_origin == "back" else "front",
            snare_item_name=snare_item_name,
            session=session,
        )
        if trap_log.pending_mycelium_snare_character_id:
            from ..schemas import PendingMyceliumSnareState

            session.pending_mycelium_snare = PendingMyceliumSnareState(
                tile_id=tile.id,
                character_id=trap_log.pending_mycelium_snare_character_id,
            )
            session.log.extend(trap_log.log)
            return
        self._finalize_trap_resolution(
            session,
            tile,
            trap_log=trap_log.log,
            show_rolls=show_rolls,
            boulder_block_exit=block_exit,
        )

    def _finalize_trap_resolution(
        self,
        session: SessionState,
        tile: TileState,
        *,
        trap_log: list[str],
        show_rolls: bool,
        boulder_block_exit=None,
    ) -> None:
        session.log.extend(trap_log)
        if tile.trap_key == "rolling_boulder" and boulder_block_exit is not None:
            boulder_block_exit.status = "blocked"
            boulder_block_exit.destination_tile_id = None
            boulder_block_exit.door_open = False
            session.log.append(f"The rolling boulder blocks the {boulder_block_exit.direction} opening.")
        if tile.trap_key == "hidden_pit":
            from .special_items import is_pit_trapped

            if any(is_pit_trapped(member) for member in session.party):
                tile.hidden_pit_secret_passage_available = True
                session.log.append(
                    "Hidden Pit: spend 1 held Clue here to find a Secret Passage from the bottom of the pit."
                )
        if tile.trap_key == "fd_beast_cage" and is_fd_ruleset(session):
            lead_failed = any(
                (" fails " in line.lower() or " takes " in line.lower())
                for line in trap_log
            )
            if lead_failed and not tile.enemies:
                sub_roll = roll_d6()
                sub_row = self.table_roller.lookup_fd_subtable_row("fd_weird_table", sub_roll)
                if sub_row:
                    hcl = self._highest_character_level(session.party)
                    spawned = self._fd_spawn_from_table_row(session, sub_row, hcl)
                    for enemy in spawned:
                        if "surprise" not in enemy.tags:
                            enemy.tags.append("surprise")
                        if "no_treasure" not in enemy.tags:
                            enemy.tags.append("no_treasure")
                    tile.enemies.extend(spawned)
                    session.log.append(
                        f"Beast Cage — {sub_row.get('name', 'Weird monster')} attacks with surprise (FD p.58)."
                    )
                    if spawned and session.mode == "exploration":
                        self._announce_encounter(session, tile, show_rolls=show_rolls)
            elif not lead_failed:
                session.log.append("Trap cleared. Beast Cage avoided before the caged foe breaks loose.")
        self._resolve_environment_trap_wandering_follow_up(
            session,
            tile,
            trap_key=tile.trap_key,
            trap_log=trap_log,
            show_rolls=show_rolls,
        )
        self._resolve_cordyceps_boss_rises(session, tile, show_rolls=show_rolls)
        tile.trap_resolved = True
        if session.illusionary_servant_active:
            self._dismiss_illusionary_servant(session, "trapped by the mechanism")
        self._after_trap_resolved(session, tile, show_rolls=show_rolls)

    def _resolve_abyss_trap(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> list[str]:
        key = tile.trap_key or ""
        level = tile.trap_level or self._highest_character_level(session.party)
        living = [member for member in sorted(session.party, key=lambda row: row.marching_order) if member.current_life > 0]
        log: list[str] = []
        if not living:
            return log
        if key == "abyss_dart_shooting_mechanism":
            target = random.choice(living)
            failed = not self._abyss_save(target, level, show_rolls=show_rolls, log=log, label="Dart trap", bonus=self._abyss_trap_bonus(target, key))
            if failed:
                poison_bonus = 1 if target.class_id.lower() == "barbarian" else 0
                poisoned = not self._abyss_save(target, 4, show_rolls=show_rolls, log=log, label="Dart poison", bonus=poison_bonus)
                if poisoned:
                    self._damage_member(target, 2, log, "poisonous dart")
            return log
        if key == "abyss_giant_metal_ball":
            for member in living:
                failed = not self._abyss_save(member, level, show_rolls=show_rolls, log=log, label="Giant metal ball", bonus=self._abyss_trap_bonus(member, key))
                if failed:
                    self._damage_member(member, 1, log, "giant metal ball")
            return log
        if key == "abyss_crocodile_pit":
            target = random.choice(living)
            failed = not self._abyss_save(target, level, show_rolls=show_rolls, log=log, label="Crocodile pit", bonus=self._abyss_trap_bonus(target, key))
            if failed:
                self._damage_member(target, 1, log, "falling into the crocodile pit")
                crocodile = EnemyState(
                    id=uuid4().hex,
                    name="Spiked Crocodile",
                    category="weird",
                    level=7,
                    life=3,
                    max_life=3,
                    attacks=1,
                    tags=["abyss", "crocodile", "surprise", "no_treasure"],
                )
                tile.enemies.append(crocodile)
                tile.initial_enemy_count = max(tile.initial_enemy_count, len(tile.enemies))
                log.append("A level 7 spiked crocodile attacks from the pit; it strikes first and fights to the death.")
                if roll_d6() <= 2:
                    gold = roll_formula("8d6")
                    tile.treasure_summary = f"Crocodile pit victims' treasure worth {gold}gp."
                    tile.treasure_gold = gold
                    tile.treasure_claimed = False
                    log.append(f"Pit remains: 2-in-6 treasure found, worth {gold}gp after the crocodile is slain.")
            return log
        if key == "abyss_guillotine":
            target = random.choice(living)
            failed = not self._abyss_save(target, level, show_rolls=show_rolls, log=log, label="Guillotine", bonus=self._abyss_trap_bonus(target, key))
            if failed:
                self._damage_member(target, 3, log, "guillotine blade")
            return log
        if key == "abyss_electrical_blast":
            for member in living:
                failed = not self._abyss_save(member, 7, show_rolls=show_rolls, log=log, label="Electrical blast", bonus=0)
                if failed:
                    self._damage_member(member, 1, log, "electrical blast")
            return log
        if key == "abyss_steel_spear":
            spear_level = 7
            for member in living:
                bonus = self._abyss_trap_bonus(member, key)
                failed = not self._abyss_save(member, spear_level, show_rolls=show_rolls, log=log, label="Steel spear dodge", bonus=bonus)
                if failed:
                    damage = roll_d3()
                    self._damage_member(member, damage, log, "steel spear")
                    spear_level = max(1, spear_level - 1)
                    log.append(f"The spear continues; its level drops to {spear_level}.")
                    continue
                log.append(f"{member.name} dodges; the spear continues toward the next hero.")
            return log
        log.append(f"Abyss trap {key} has no exact resolver; no effect applied.")
        return log

    def _abyss_trap_bonus(self, member: PartyMemberState, trap_key: str) -> int:
        class_id = member.class_id.lower()
        if trap_key == "abyss_dart_shooting_mechanism":
            return member.level if class_id in {"halfling", "rogue"} else 0
        if trap_key == "abyss_giant_metal_ball":
            bonus = 0
            if class_id == "rogue":
                bonus += member.level
            elif class_id in {"halfling", "swashbuckler", "elf"}:
                bonus += member.level // 2
            inventory = " ".join(member.inventory).lower()
            if "heavy armor" in inventory:
                bonus += 1
            if "shield" in inventory:
                bonus += 1
            return bonus
        if trap_key == "abyss_guillotine":
            if class_id == "rogue":
                return member.level
            if class_id in {"elf", "swashbuckler", "halfling"}:
                return 1
            return 0
        if trap_key == "abyss_steel_spear":
            if class_id == "rogue":
                return member.level
            if class_id in {"elf", "halfling"}:
                return member.level // 2
            return 0
        return 0

    def _abyss_save(
        self,
        member: PartyMemberState,
        level: int,
        *,
        show_rolls: bool,
        log: list[str],
        label: str,
        bonus: int = 0,
    ) -> bool:
        total, rolls = roll_exploding_for_level(member)
        score = total + bonus + encumbrance_penalty(member)
        if show_rolls:
            detail = f"{' + '.join(str(value) for value in rolls)}"
            if bonus:
                detail += f" + {bonus}"
            log.append(f"{label}: {member.name} rolls {detail} vs L{level}.")
        passed = rolls[0] != 1 and score >= level
        log.append(f"{member.name} {'succeeds' if passed else 'fails'} the {label.lower()} save.")
        return passed

    def _damage_member(self, member: PartyMemberState, amount: int, log: list[str], source: str) -> None:
        member.current_life = max(0, member.current_life - max(0, amount))
        log.append(f"Effect: {member.name} loses {amount} Life from {source} ({member.current_life}/{member.max_life}).")

    def _resolve_environment_trap_wandering_follow_up(
        self,
        session: SessionState,
        tile: TileState,
        *,
        trap_key: str,
        trap_log: list[str],
        show_rolls: bool,
    ) -> None:
        if trap_key in {"spore_cloud", "slime_patch"}:
            if not any("1-in-6 Wandering Monsters check" in line for line in trap_log):
                return
            roll = roll_d6()
            if show_rolls:
                session.log.append(f"{trap_key.replace('_', ' ').title()} wandering-monster roll: d6 = {roll}.")
            if roll == 1:
                if trap_key == "slime_patch":
                    for member in session.party:
                        if member.current_life > 0 and any(
                            "fallen prone (slime patch)" in status.lower() for status in member.statuses
                        ):
                            from .fungal_traps import SLIME_PATCH_SKIP_STATUS

                            if SLIME_PATCH_SKIP_STATUS not in member.statuses:
                                member.statuses.append(SLIME_PATCH_SKIP_STATUS)
                            session.log.append(
                                f"{member.name} will skip 1 turn while struggling back to their feet."
                            )
                self._spawn_wandering_monsters(
                    session,
                    tile,
                    show_rolls=show_rolls,
                    combat_message=f"Wandering Monsters arrive after the {trap_key.replace('_', ' ')}!",
                )
            return
        if trap_key == "shrieking_mushroom" and any("calls Wandering Monsters" in line for line in trap_log):
            self._spawn_wandering_monsters(
                session,
                tile,
                show_rolls=show_rolls,
                combat_message="Wandering Monsters answer the shrieking mushroom!",
            )

    def _resolve_cordyceps_boss_rises(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        from .fungal_traps import CORDYCEPS_VICTIM_STATUS, cordyceps_boss_life

        fallen = [
            member
            for member in session.party
            if member.current_life <= 0 and CORDYCEPS_VICTIM_STATUS in member.statuses
        ]
        if not fallen:
            return
        hcl = self._highest_character_level(session.party)
        boss_life = cordyceps_boss_life(hcl)
        for victim in fallen:
            boss = EnemyState(
                id=f"cordyceps-boss-{victim.character_id}",
                name=f"Undead {victim.name}",
                category="boss",
                level=victim.level,
                life=boss_life,
                max_life=boss_life,
                tags=["undead", "boss", "cordyceps_risen"],
            )
            tile.enemies.append(boss)
            session.log.append(
                f"{victim.name} rises as an undead boss (L{victim.level}, {boss_life} Life) and attacks!"
            )
        living = [member for member in session.party if member.current_life > 0]
        if not living or not tile.enemies:
            return
        self._begin_combat(
            session,
            "The cordyceps victim rises to attack the party!",
            show_rolls=show_rolls,
            allow_final_boss_check=False,
            foes_strike_first=True,
            tile=tile,
        )

    def _use_hidden_pit_clue(self, session: SessionState, *, show_rolls: bool) -> None:
        tile = self._current_tile(session)
        if not tile.hidden_pit_secret_passage_available:
            session.log.append("There is no hidden pit clue option here.")
            return
        if session.mode != "exploration":
            session.log.append("Use the hidden pit clue option during exploration.")
            return
        self._ensure_individual_clues(session)
        if session.clues_found < 1:
            session.log.append("Hidden Pit secret passage requires 1 held Clue.")
            return
        if not self._spend_clues(session, 1):
            session.log.append("Hidden Pit secret passage requires 1 held Clue.")
            return
        tile.hidden_pit_secret_passage_available = False
        session.pending_secret_passage_hidden_pit = True
        session.log.append("The party spends 1 Clue at the bottom of the hidden pit.")
        self._reveal_secret_passage(session, tile, show_rolls=show_rolls)

    def _servant_owner_ids(self, session: SessionState) -> set[str]:
        if session.illusionary_servant_active and session.illusionary_servant_owner_id:
            return {session.illusionary_servant_owner_id}
        return set()

    def _dismiss_illusionary_servant(self, session: SessionState, reason: str) -> None:
        if not session.illusionary_servant_active:
            return
        session.illusionary_servant_active = False
        session.illusionary_servant_owner_id = None
        session.log.append(f"The illusionary servant is lost ({reason}).")

    def _monster_template_for_enemy(self, enemy: EnemyState) -> dict | None:
        if self.rules is None:
            return None
        from .monster_combat_hooks import MONSTER_TEMPLATE_ALIASES

        monsters = self.rules.monsters()
        names_to_try = [enemy.name]
        alias = MONSTER_TEMPLATE_ALIASES.get(enemy.name)
        if alias:
            names_to_try.append(alias)
        candidates: list[dict] = []
        for name in names_to_try:
            for table in monsters.values():
                if not isinstance(table, list):
                    continue
                for template in table:
                    if template.get("name") == name:
                        candidates.append(template)
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        def template_richness(template: dict) -> int:
            score = 0
            if template.get("treasure_rolls"):
                score += 20 + int(template.get("treasure_rolls", 0))
            if template.get("no_treasure"):
                score += 20
            score += len(template.get("reactions", []) or [])
            score += len(template.get("special_attacks", []) or [])
            score += len(template.get("on_hit_effects", []) or [])
            score += len(template.get("special_rules", []) or [])
            return score

        return max(candidates, key=template_richness)

    def _treasure_roll_count_for_tile(self, session: SessionState, tile: TileState) -> int:
        from .forsaken_depths_map import is_fd_ruleset
        from .monster_combat_hooks import treasure_roll_count_from_defeated

        defeated = list(tile.defeated_enemies)
        if not defeated or self.rules is None:
            return 1
        abyss_rolls = 0
        for enemy in defeated:
            for tag in enemy.tags:
                if tag.startswith("abyss_treasure_rolls:"):
                    try:
                        abyss_rolls += max(0, int(tag.split(":", 1)[1]))
                    except ValueError:
                        pass
        if abyss_rolls:
            return abyss_rolls
        return treasure_roll_count_from_defeated(
            defeated,
            lookup_template=self._monster_template_for_enemy,
            log=session.log,
            fd_ruleset=is_fd_ruleset(session),
        )

    def _award_fd_defeated_foe_treasure(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> None:
        from .monster_combat_hooks import fd_treasure_roll_bonuses_from_defeated

        defeated = list(tile.defeated_enemies)
        door_bonus = self._entry_treasure_bonus(session)
        bonuses = fd_treasure_roll_bonuses_from_defeated(
            defeated,
            lookup_template=self._monster_template_for_enemy,
            log=session.log,
        )
        if door_bonus:
            bonuses = [bonus + door_bonus for bonus in bonuses]
        if not bonuses:
            if tile.final_boss_treasure:
                tile.treasure_gold = apply_final_boss_treasure_bonus(0)
                tile.treasure_summary = f"Final Boss treasure: {tile.treasure_gold}gp"
                tile.treasure_claimed = False
                session.pending_treasure_reroll_tile_id = tile.id
                session.log.append(
                    f"Final Boss bounty: {tile.treasure_gold}gp "
                    "(foe template has no treasure rolls; minimum bounty applied)."
                )
            else:
                session.log.append(
                    "No treasure rolls for defeated foes (no_treasure or no treasure_rolls on template)."
                )
            return
        outcome = self.table_roller.roll_fd_treasure_batch_with_bonuses(
            bonuses,
            show_rolls=show_rolls,
            silk_already_found=session.fd_silk_treasure_used,
        )
        if "Precious silk worth" in outcome.summary or any(
            "silk" in item.lower() for item in outcome.items
        ):
            session.fd_silk_treasure_used = True
        if show_rolls:
            session.log.extend(outcome.log)
        self._stage_treasure_outcome(session, tile, outcome, show_rolls=show_rolls)
        if tile.final_boss_treasure and (tile.treasure_gold or tile.treasure_items):
            tile.treasure_gold = apply_final_boss_treasure_bonus(tile.treasure_gold)
            if len(tile.treasure_items) == 1:
                tile.treasure_items.append(tile.treasure_items[0])
            tile.treasure_summary = (
                f"Final Boss treasure: {tile.treasure_gold}gp"
                + (f", {', '.join(tile.treasure_items)}" if tile.treasure_items else "")
            )
        if tile.treasure_gold or tile.treasure_items or tile.pending_treasure_choice:
            self._apply_treasure_doubling(tile)
            session.pending_treasure_reroll_tile_id = tile.id

    def _merge_treasure_outcomes(self, outcomes: list[TreasureOutcome]) -> TreasureOutcome:
        if not outcomes:
            return TreasureOutcome("", 0, [], [])
        gold = sum(outcome.gold for outcome in outcomes)
        items: list[str] = []
        for outcome in outcomes:
            items.extend(outcome.items)
        log: list[str] = []
        for outcome in outcomes:
            log.extend(outcome.log)
        summaries = [outcome.summary for outcome in outcomes if outcome.summary]
        summary = "; ".join(summaries) if summaries else "Treasure"
        return TreasureOutcome(summary, gold, items, log)

    def _maybe_award_living_statue_treasure(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> bool:
        if not any("living_statue" in enemy.tags for enemy in tile.defeated_enemies):
            return False
        if tile.treasure_gold or tile.treasure_items:
            return False
        gold = resolve_gold_formula("3d6*10", hcl=0)
        if tile.final_boss_treasure:
            gold = apply_final_boss_treasure_bonus(gold)
        tile.treasure_gold = gold
        tile.treasure_summary = f"Defeated Living Statue yields {gold}gp."
        tile.treasure_claimed = False
        session.pending_treasure_reroll_tile_id = tile.id
        session.log.append(f"Living Statue treasure: {gold}gp inside the broken statue.")
        self._apply_treasure_doubling(tile)
        return True

    def _award_treasure(self, session: SessionState, tile: TileState, *, show_rolls: bool) -> None:
        if session.adventure_type == "imported":
            return
        if tile.treasure_gold or tile.treasure_items:
            return
        if tile.treasure_summary and not tile.treasure_claimed:
            return
        if tile.content_key in {"treasure", "trap_treasure"} or tile.resolved:
            if is_fd_ruleset(session):
                self._award_fd_defeated_foe_treasure(session, tile, show_rolls=show_rolls)
                self._append_arcane_tanner_hides(session, tile, show_rolls=show_rolls)
                return
            if self._maybe_award_living_statue_treasure(session, tile, show_rolls=show_rolls):
                self._append_arcane_tanner_hides(session, tile, show_rolls=show_rolls)
                return
            roll_count = self._treasure_roll_count_for_tile(session, tile)
            if roll_count <= 0:
                if tile.final_boss_treasure:
                    tile.treasure_gold = apply_final_boss_treasure_bonus(0)
                    tile.treasure_summary = f"Final Boss treasure: {tile.treasure_gold}gp"
                    tile.treasure_claimed = False
                    session.pending_treasure_reroll_tile_id = tile.id
                    session.log.append(
                        f"Final Boss bounty: {tile.treasure_gold}gp "
                        "(foe template has no treasure rolls; minimum bounty applied)."
                    )
                else:
                    session.log.append(
                        "No treasure rolls for defeated foes (no_treasure or no treasure_rolls on template)."
                    )
            else:
                outcomes = [self._roll_treasure(session) for _ in range(roll_count)]
                outcome = self._merge_treasure_outcomes(outcomes)
                if show_rolls:
                    session.log.extend(outcome.log)
                if outcome.gold or outcome.items:
                    tile.treasure_summary = outcome.summary
                    tile.treasure_gold = outcome.gold
                    tile.treasure_items = self._finalize_treasure_items(
                        session, list(outcome.items), show_rolls=show_rolls
                    )
                    tile.treasure_claimed = False
                    if tile.final_boss_treasure:
                        tile.treasure_gold = apply_final_boss_treasure_bonus(tile.treasure_gold)
                        if len(tile.treasure_items) == 1:
                            tile.treasure_items.append(tile.treasure_items[0])
                        tile.treasure_summary = (
                            f"Final Boss treasure: {tile.treasure_gold}gp"
                            + (f", {', '.join(tile.treasure_items)}" if tile.treasure_items else "")
                        )
                    self._apply_treasure_doubling(tile)
                    session.pending_treasure_reroll_tile_id = tile.id
                    session.log.append("Treasure is available to claim.")
                else:
                    tile.treasure_summary = outcome.summary
                    session.log.append(outcome.summary or "No treasure found.")
            self._append_arcane_tanner_hides(session, tile, show_rolls=show_rolls)

    def _append_arcane_tanner_hides(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> None:
        from .expert_skill_effects import arcane_tanner_hides_from_defeated

        defeated = list(tile.defeated_enemies)
        if not defeated:
            defeated = [enemy for enemy in tile.enemies if enemy.life <= 0]
        hide_items, hide_log = arcane_tanner_hides_from_defeated(defeated)
        if not hide_items:
            return
        if show_rolls:
            session.log.extend(hide_log)
        tile.treasure_items.extend(hide_items)
        tile.treasure_claimed = False
        hide_summary = ", ".join(hide_items)
        if tile.treasure_summary:
            tile.treasure_summary = f"{tile.treasure_summary}; {hide_summary}"
        else:
            tile.treasure_summary = hide_summary
        session.log.append("Beast hides are available to claim with the treasure.")

    def _claim_treasure(self, session: SessionState) -> None:
        tile = self._current_tile(session)
        if tile.pending_treasure_choice:
            session.log.append("Choose the treasure outcome before claiming.")
            return
        if tile.fd_jackpot_wandering_on_claim:
            tile.fd_jackpot_wandering_on_claim = False
            wander_roll = roll_d6()
            session.log.append(
                f"Jackpot looting: d6 = {wander_roll} — 4-in-6 wandering monsters while looting (FD p.62)."
            )
            if wander_roll >= 4:
                self._spawn_wandering_monsters(session, tile, show_rolls=True)
                if session.mode != "exploration":
                    return
        if tile.hidden_treasure_complication_effect_pending:
            effect = tile.hidden_treasure_complication_effect_pending
            hcl = self._highest_character_level(session.party)
            self._apply_hidden_treasure_complication(
                session,
                tile,
                effect,
                hcl=hcl,
                show_rolls=True,
                explain_math=False,
            )
            if tile.hidden_treasure_alarm_pending or any(enemy.life > 0 for enemy in tile.enemies):
                return
        if tile.trap_key and not tile.trap_resolved:
            session.log.append("Resolve the trap before claiming treasure.")
            return
        if tile.treasure_claimed:
            session.log.append("Treasure has already been claimed here.")
            return
        if tile.deal_treasure_forbidden:
            session.log.append("Treasure here is forbidden by Deal with a Foe.")
            return
        if not tile.treasure_gold and not tile.treasure_items:
            if tile.treasure_summary:
                session.log.append(tile.treasure_summary)
            else:
                session.log.append("There is no treasure here.")
            return
        survivors = sorted(
            [member for member in session.party if member.current_life > 0],
            key=lambda member: member.marching_order,
        )
        if not survivors:
            session.log.append("There is no one left to carry treasure.")
            return
        gold_total = tile.treasure_gold
        gold_cap = self._final_boss_summary_gold_cap(tile)
        if gold_cap is not None and gold_total > gold_cap:
            session.log.append(
                f"Final Boss treasure corrected from {gold_total}gp to {gold_cap}gp to match the recorded treasure."
            )
            gold_total = gold_cap
            tile.treasure_gold = gold_cap
        remaining_gold, payouts = distribute_gold_among(
            survivors,
            gold_total,
            servant_owner_ids=self._servant_owner_ids(session),
        )
        items = list(tile.treasure_items)
        inventory_lengths = {member.character_id: len(member.inventory) for member in survivors}
        uncarried_items, placed_items = distribute_items_among(survivors, items)
        item_recipients: list[str] = []
        for member in survivors:
            before_count = inventory_lengths.get(member.character_id, len(member.inventory))
            for item in member.inventory[before_count:]:
                item_recipients.append(f"{member.name} receives {item}")
                from .milestones import record_inventory_item_acquired

                session.log.extend(record_inventory_item_acquired(member, item))
        if session.xp_system == "old_school" and gold_total:
            session.old_school_xp_tally += gold_total
            session.log.append(f"Old School XP +{gold_total} from treasure (tally {session.old_school_xp_tally}).")
        tile.treasure_gold = remaining_gold
        tile.treasure_items = uncarried_items
        tile.treasure_claimed = remaining_gold <= 0 and not uncarried_items
        summary = tile.treasure_summary or "Treasure"
        if tile.treasure_claimed:
            session.log.append(f"Treasure claimed: {summary}")
        else:
            session.log.append(f"Treasure partially claimed: {summary}")
        if payouts:
            session.log.append(f"Gold split: {', '.join(payouts)}.")
        if remaining_gold:
            session.log.append(
                f"{remaining_gold}gp left behind (each hero carries at most 200gp)."
            )
        if placed_items:
            item_list = "; ".join(item_recipients) if item_recipients else ", ".join(placed_items)
            session.log.append(f"Items assigned: {item_list}.")
        for member in survivors:
            if any(is_glittering_crystal(item) for item in member.inventory):
                if "Glittering Crystal" not in member.statuses:
                    session.log.extend(equip_glittering_crystal(member))
        if uncarried_items:
            item_list = ", ".join(uncarried_items)
            session.log.append(
                f"Could not carry: {item_list} (weapon/shield limits or no free carrier)."
            )
        session.log.extend(enforce_single_pole_carrier(session.party, session=session))
        if tile.treasure_claimed:
            tile.objects = [item for item in tile.objects if "treasure" not in item.lower()]
        if session.adventure_type == "imported":
            fire_imported_triggers(self, session, tile, "on_treasure", show_rolls=True)

    def _carry_body(
        self,
        session: SessionState,
        carrier_id: str | None,
        fallen_id: str | None,
    ) -> None:
        tile = self._current_tile(session)
        if not carrier_id or not fallen_id:
            session.log.append("Choose who carries which fallen hero.")
            return
        session.log.extend(start_carrying_body(session, tile, carrier_id, fallen_id))

    def _drop_body(self, session: SessionState) -> None:
        tile = self._current_tile(session)
        session.log.extend(drop_carried_body(session, tile))

    def _attempt_resurrection(
        self,
        session: SessionState,
        fallen_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        session.log.extend(attempt_resurrection(session, fallen_id, show_rolls=show_rolls))

    def _treat_lycanthropy(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        member = next((item for item in session.party if item.character_id == character_id), None)
        from .abyss_afflictions import treat_lycanthropy_at_monastery

        session.log.extend(treat_lycanthropy_at_monastery(session, member, show_rolls=show_rolls))

    def _start_abyss_campaign_plot(
        self,
        session: SessionState,
        plot_choice: str | None,
        character_id: str | None,
        *,
        show_rolls: bool,
    ) -> None:
        holder = next((item for item in session.party if item.character_id == character_id), None)
        from .abyss_campaign import start_abyss_campaign_plot

        session.log.extend(
            start_abyss_campaign_plot(
                session,
                plot_choice=plot_choice,
                holder=holder,
                show_rolls=show_rolls,
            )
        )

    def _abyss_plot_contribute_gold(self, session: SessionState, amount: int | None) -> None:
        from .abyss_campaign import contribute_rebellion_gold

        session.log.extend(contribute_rebellion_gold(session, amount))

    def _abyss_plot_take_artifact_piece(self, session: SessionState) -> None:
        from .abyss_campaign import take_entity_artifact_piece

        session.log.extend(take_entity_artifact_piece(session, self._current_tile(session)))

    def _abyss_plot_spend_clues(self, session: SessionState) -> None:
        from .abyss_campaign import spend_invasion_clues

        session.log.extend(spend_invasion_clues(session))

    def _abyss_plot_transfer_artifact(self, session: SessionState, character_id: str | None) -> None:
        holder = next((item for item in session.party if item.character_id == character_id), None)
        from .abyss_campaign import transfer_invasion_artifact

        session.log.extend(transfer_invasion_artifact(session, holder))

    def _abyss_plot_resolve_finale(self, session: SessionState) -> None:
        from .abyss_campaign import resolve_plot_finale

        session.log.extend(resolve_plot_finale(session))

    def _hunt_vampire_sire(self, session: SessionState) -> None:
        if session.mode != "exploration":
            session.log.append("Hunt the vampire sire during exploration.")
            return
        from .abyss_campaign import hunt_vampire_sire

        session.log.extend(hunt_vampire_sire(session, self._current_tile(session)))

    def _accept_fallen_loss(self, session: SessionState, fallen_id: str | None) -> None:
        session.log.extend(accept_fallen_loss(session, fallen_id))

    def _use_map_fragment(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool = True,
        explain_math: bool = False,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Use a map fragment during exploration.")
            return
        if session.environment != "caverns":
            session.log.append("Map fragments only work in caverns.")
            return
        if session.map_fragment_used:
            session.log.append("The party has already used a map fragment this adventure.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to read the map fragment.")
            return
        fragment = next((item for item in member.inventory if is_map_fragment(item)), None)
        if fragment is None:
            session.log.append(f"{member.name} has no map fragment.")
            return
        tile = self._current_tile(session)
        member.inventory = [item for item in member.inventory if item != fragment]
        session.map_fragment_used = True
        session.log.append(f"{member.name} studies the map fragment (once per adventure).")
        self._reveal_next_tile_from_trade(
            session,
            tile,
            show_rolls=show_rolls,
            explain_math=explain_math,
            source="The map fragment",
        )

    def _use_enchanted_paint(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        paint_choice: str | None = None,
        paint_direction: str | None = None,
        paint_quantity: int | None = None,
        paint_item_key: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Enchanted Paint can only be used during exploration.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to use Enchanted Paint.")
            return
        if not any(is_enchanted_paint(item) for item in member.inventory):
            session.log.append(f"{member.name} has no Enchanted Paint.")
            return
        if not paint_choice:
            session.log.append("Choose what the Enchanted Paint should become.")
            return
        direction = (paint_direction or "").strip().lower() or None
        catalog = self.rules.equipment_shop()
        log_lines, used, _depleted = apply_enchanted_paint(
            member,
            choice=paint_choice,
            quantity=paint_quantity or 1,
            direction=direction,
            item_key=paint_item_key,
            shop_catalog=catalog,
            show_rolls=show_rolls,
        )
        session.log.extend(log_lines)
        if used and paint_choice == "paint_door" and direction in {"north", "south", "east", "west"}:
            session.log.extend(self._open_painted_door(session, direction))

    def _open_painted_door(self, session: SessionState, direction: str) -> list[str]:
        tile = self._current_tile(session)
        width, height = self._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        exit_state = next((item for item in tile.exits if item.direction == direction), None)
        if exit_state is None:
            exit_state = self._new_exit(direction=direction, kind="door", width=width, height=height, status="open")
            tile.exits.append(exit_state)
        exit_state.kind = "door"
        exit_state.door_type = "unlocked"
        exit_state.status = "open"
        exit_state.door_open = True
        exit_state.door_result = "open"
        _, destination = self._exit_edge(tile, exit_state)
        existing = (
            self._tile_by_id(session, exit_state.destination_tile_id)
            if exit_state.destination_tile_id
            else self._tile_occupying(session, *destination, exclude_tile_id=tile.id)
        )
        if existing and existing.id != tile.id:
            exit_state.destination_tile_id = existing.id
            self._set_reciprocal_exit(existing, tile, exit_state)
            reciprocal = self._reciprocal_exit_on_tile(
                existing,
                tile.id,
                direction=OPPOSITE[direction],
            )
            if reciprocal is not None:
                reciprocal.status = "open"
                reciprocal.door_open = True
            self._sync_connection_state(exit_state, reciprocal, passed_through=False)
            self._persist_open_connection(session, tile, exit_state)
            return [
                f"The painted door connects to {existing.title} (EE p.186). "
                "Move through it as usual, or explore elsewhere."
            ]
        return [
            f"The painted door opens on the {direction} wall (EE p.186). "
            "Move through it to roll a new map element, or connect later when tiles align."
        ]

    def _probe_trap(self, session: SessionState, *, show_rolls: bool) -> None:
        if session.mode != "exploration":
            session.log.append("Probe traps during exploration.")
            return
        tile = self._current_tile(session)
        if not tile.trap_key or tile.trap_resolved:
            session.log.append("There is no active trap to probe here.")
            return
        carrier = pole_carrier(session.party)
        if carrier is None:
            session.log.append("The party needs a 10' pole to probe traps.")
            return
        trap_label = (tile.trap_key or "trap").replace("_", " ")
        tile.trap_probed = True
        session.log.append(
            f"{carrier.name} probes with the 10' pole and finds a {trap_label} "
            f"(trap level {tile.trap_level or self._highest_character_level(session.party)})."
        )
        if show_rolls:
            session.log.append("Rogues gain +1 on the next disarm attempt here.")

    def _use_miners_ointment(self, session: SessionState, character_id: str | None) -> None:
        if session.mode != "exploration":
            session.log.append("Use Miners' Ointment during exploration.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to use Miners' Ointment.")
            return
        ointment = next((item for item in member.inventory if is_miners_ointment(item)), None)
        if ointment is None:
            session.log.append(f"{member.name} has no Miners' Ointment.")
            return
        log, _ = use_miners_ointment(member, ointment)
        session.gremlin_wm_protection_pending = True
        session.log.extend(log)

    def _use_herbal_tonic(self, session: SessionState, character_id: str | None) -> None:
        if session.mode == "combat":
            session.log.append("Herbal tonic cannot be drunk during combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to drink herbal tonic.")
            return
        if member.character_id in session.herbal_tonic_used_character_ids:
            session.log.append(f"{member.name} already drank herbal tonic this adventure.")
            return
        tonic = next((item for item in member.inventory if is_herbal_tonic(item)), None)
        if tonic is None:
            session.log.append(f"{member.name} has no herbal tonic.")
            return
        if member.current_life >= member.max_life:
            session.log.append(f"{member.name} is already at full Life.")
            return
        session.log.extend(use_herbal_tonic(member, tonic))
        session.herbal_tonic_used_character_ids.append(member.character_id)

    def _apply_gremlin_repellant(self, session: SessionState, character_id: str | None) -> None:
        if session.mode != "exploration":
            session.log.append("Apply gremlin repellant during exploration.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to apply gremlin repellant.")
            return
        repellant = next((item for item in member.inventory if "gremlin repellant" in item.lower()), None)
        if repellant is None:
            session.log.append(f"{member.name} has no gremlin repellant.")
            return
        member.inventory = [item for item in member.inventory if item != repellant]
        session.gremlin_wm_protection_pending = True
        session.log.append(
            f"{member.name} applies {repellant}; the next Wandering Monsters or gremlin event is ignored."
        )

    def _use_berserkers_mushroom(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        item_name: str | None = None,
    ) -> None:
        if session.mode != "exploration":
            session.log.append("Eat the Berserker's Mushroom during exploration before combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to eat the mushroom.")
            return
        mushroom = item_name if item_name and item_name in member.inventory and is_berserkers_mushroom(item_name) else None
        if mushroom is None:
            mushroom = next((item for item in member.inventory if is_berserkers_mushroom(item)), None)
        if mushroom is None:
            session.log.append(f"{member.name} has no Berserker's Mushroom.")
            return
        session.log.extend(eat_berserkers_mushroom(member, mushroom))

    def _climb_from_pit(
        self,
        session: SessionState,
        helper_id: str | None,
        trapped_id: str | None,
    ) -> None:
        helper = next((item for item in session.party if item.character_id == helper_id), None)
        trapped = next((item for item in session.party if item.character_id == trapped_id), None)
        if helper is None or helper.current_life <= 0:
            session.log.append("Choose a living hero to help climb out of the pit.")
            return
        if trapped is None:
            session.log.append("Choose which trapped hero to rescue.")
            return
        session.log.extend(climb_from_pit(session, helper, trapped, session.party))

    def _spend_torch(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Spend a torch during combat to burn through webs.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to spend a torch.")
            return
        ok, torch_name = consume_torch(member)
        if not ok:
            session.log.append(f"{member.name} has no torch to spend.")
            return
        session.torch_spent_this_combat = True
        if show_rolls:
            session.log.append(f"{member.name} spends {torch_name} to burn through spider webs; the party may flee.")

    def _use_wolfsbane(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Wolfsbane can only be thrown during combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to throw wolfsbane.")
            return
        available = [item for item in member.inventory if is_wolfsbane(item)]
        if not available:
            session.log.append(f"{member.name} has no wolfsbane.")
            return
        bundle = item_name if item_name and item_name in member.inventory and is_wolfsbane(item_name) else None
        if bundle is None:
            bundle = available[0] if len(available) == 1 else None
        if bundle is None:
            session.log.append("Choose which wolfsbane bundle to throw.")
            return
        tile = self._current_tile(session)
        party_here = combat_party(session, tile.id)
        if member.character_id not in {pc.character_id for pc in party_here}:
            session.log.append(f"{member.name} is not on the current map element.")
            return
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            session.log.append("There are no foes to target.")
            return
        from .equipment_effects import is_werecreature

        were_foes = [enemy for enemy in living_enemies if is_werecreature(enemy)]
        if not were_foes:
            session.log.append("There are no lycanthropes to target with wolfsbane.")
            return
        target = next((enemy for enemy in were_foes if enemy.id == target_enemy_id), None)
        if target is None:
            target = were_foes[0]
        if not self._commit_immediate_attack(session):
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        log_lines, _hit = throw_wolfsbane(member, target, bundle)
        session.log.extend(log_lines)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._apply_combat_result(
                session,
                tile,
                CombatRound(
                    party=session.party,
                    enemies=tile.enemies,
                    log=[],
                    combat_over=True,
                ),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )

    def _use_bandage(
        self,
        session: SessionState,
        character_id: str | None,
        target_character_id: str | None = None,
        *,
        show_rolls: bool,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Bandages cannot be applied during combat.")
            return
        applier = next((item for item in session.party if item.character_id == character_id), None)
        if applier is None:
            session.log.append("Choose a hero to apply the bandage.")
            return
        recipient_id = target_character_id or character_id
        recipient = next((item for item in session.party if item.character_id == recipient_id), None)
        if recipient is None:
            session.log.append("Choose a hero to receive the bandage.")
            return
        tile = self._current_tile(session)
        heroes_here = {member.character_id for member in combat_party(session, tile.id)}
        if applier.character_id not in heroes_here:
            session.log.append(f"{applier.name} is not on the current map element.")
            return
        if recipient.character_id not in heroes_here:
            session.log.append("Choose a hero on this map element to receive the bandage.")
            return
        ok, message = can_apply_bandage(
            applier,
            bandage_used_character_ids=set(session.bandage_used_character_ids),
        )
        if not ok:
            session.log.append(message)
            return
        ok, message = can_receive_bandage(recipient)
        if not ok:
            session.log.append(message)
            return
        bandage_name = bandages_in_inventory(applier)[0]
        applier.inventory = [item for item in applier.inventory if item != bandage_name]
        recipient.current_life = min(recipient.max_life, recipient.current_life + 1)
        session.bandage_used_character_ids.append(applier.character_id)
        if show_rolls:
            if applier.character_id == recipient.character_id:
                session.log.append(
                    f"{applier.name} applies {bandage_name} and recovers 1 Life "
                    f"({recipient.current_life}/{recipient.max_life})."
                )
            else:
                session.log.append(
                    f"{applier.name} bandages {recipient.name} with {bandage_name}; "
                    f"{recipient.name} recovers 1 Life ({recipient.current_life}/{recipient.max_life})."
                )

    def _end_bear_form(self, session: SessionState) -> None:
        owner_id = session.bear_form_owner_id
        if not owner_id:
            return
        member = next((item for item in session.party if item.character_id == owner_id), None)
        if member is None:
            session.bear_form_owner_id = None
            session.bear_form_start_life = 0
            session.bear_form_pre_life = 0
            return
        damage_as_bear = max(0, session.bear_form_start_life - member.current_life)
        carry_over = damage_as_bear // 2
        member.current_life = max(0, session.bear_form_pre_life - carry_over)
        if damage_as_bear:
            session.log.append(
                f"{member.name} reverts from bear form; half the wounds carry over ({carry_over} damage)."
            )
        elif any(status.strip().lower() == "bear form" for status in member.statuses):
            session.log.append(f"{member.name} reverts from bear form unscathed.")
        session.bear_form_owner_id = None
        session.bear_form_start_life = 0
        session.bear_form_pre_life = 0

    def _foes_strike_summoned_beast(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> None:
        if session.summoned_beast_life <= 0:
            return
        living_foes = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_foes:
            return
        owner = next((m for m in session.party if m.character_id == session.summoned_beast_owner_id), None)
        if owner is None or owner.current_life <= 0:
            session.summoned_beast_life = 0
            session.summoned_beast_owner_id = None
            return
        attacker = living_foes[0]
        beast_level = 3
        total, rolls = roll_exploding_for_level(attacker)
        if show_rolls:
            session.log.append(
                f"{attacker.name} strikes the summoned beast: "
                f"{' + '.join(str(value) for value in rolls)} = {total} vs L{beast_level}."
            )
        if not attack_hits(total, beast_level):
            session.log.append("The summoned beast shrugs off the blow.")
            return
        session.summoned_beast_life = max(0, session.summoned_beast_life - 1)
        session.log.append(
            f"The summoned beast takes 1 damage ({session.summoned_beast_life} Life remaining)."
        )
        if session.summoned_beast_life <= 0:
            session.summoned_beast_owner_id = None
            session.log.append("The summoned beast is slain.")

    def _foes_strike_druid_companion(
        self,
        session: SessionState,
        tile: TileState,
        *,
        show_rolls: bool,
    ) -> None:
        living_foes = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_foes or session.druid_companion_life <= 0:
            return
        attacker = living_foes[0]
        session.log.extend(
            foes_strike_companion(
                session,
                session.party,
                attacker.level,
                show_rolls=show_rolls,
            )
        )

    def _use_holy_water(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Holy water can only be thrown during combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to throw holy water.")
            return
        available = [item for item in member.inventory if is_holy_water(item)]
        if not available:
            session.log.append(f"{member.name} has no holy water.")
            return
        vial_name = item_name if item_name and item_name in member.inventory and is_holy_water(item_name) else None
        if vial_name is None:
            vial_name = available[0] if len(available) == 1 else None
        if vial_name is None:
            session.log.append("Choose which holy water vial to throw.")
            return

        tile = self._current_tile(session)
        party_here = combat_party(session, tile.id)
        if member.character_id not in {pc.character_id for pc in party_here}:
            session.log.append(f"{member.name} is not on the current map element.")
            return
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            session.log.append("There are no foes to target.")
            return
        undead_foes = [enemy for enemy in living_enemies if is_undead_foe(enemy)]
        if not undead_foes:
            session.log.append("There are no undead foes to target with holy water.")
            return
        target = next((enemy for enemy in undead_foes if enemy.id == target_enemy_id), None)
        if target is None:
            target = undead_foes[0]

        if not self._commit_immediate_attack(session):
            return
        member.inventory = [item for item in member.inventory if item != vial_name]
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        log_lines, _hit = throw_holy_water(member, target, show_rolls=show_rolls)
        session.log.extend(log_lines)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._apply_combat_result(
                session,
                tile,
                CombatRound(
                    party=session.party,
                    enemies=tile.enemies,
                    log=[],
                    combat_over=True,
                ),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )

    def _use_lantern_oil(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Lantern oil can only be splashed during combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to splash lantern oil.")
            return
        available = [item for item in member.inventory if is_lantern_oil(item)]
        if not available:
            session.log.append(f"{member.name} has no lantern oil.")
            return
        oil_name = item_name if item_name and item_name in member.inventory and is_lantern_oil(item_name) else None
        if oil_name is None:
            oil_name = available[0] if len(available) == 1 else None
        if oil_name is None:
            session.log.append("Choose which lantern oil flask to use.")
            return

        tile = self._current_tile(session)
        party_here = combat_party(session, tile.id)
        if member.character_id not in {pc.character_id for pc in party_here}:
            session.log.append(f"{member.name} is not on the current map element.")
            return
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            session.log.append("There are no foes to target.")
            return
        regen_foes = [enemy for enemy in living_enemies if "regeneration" in {tag.lower() for tag in enemy.tags}]
        if not regen_foes:
            session.log.append("There are no regenerating foes to burn with lantern oil.")
            return
        target = next((enemy for enemy in regen_foes if enemy.id == target_enemy_id), None)
        if target is None:
            target = regen_foes[0]

        if not self._commit_immediate_attack(session):
            return
        member.inventory = [item for item in member.inventory if item != oil_name]
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        log_lines, _hit = splash_lantern_oil(member, target, show_rolls=show_rolls)
        session.log.extend(log_lines)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._apply_combat_result(
                session,
                tile,
                CombatRound(
                    party=session.party,
                    enemies=tile.enemies,
                    log=[],
                    combat_over=True,
                ),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )

    def _eat_food_ration(self, session: SessionState, character_id: str | None) -> None:
        if session.mode != "exploration":
            session.log.append("Food rations are eaten during exploration or while camped outside.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to eat a Food ration.")
            return
        session.log.extend(eat_food_ration(session, member, session.party))
        session.log.extend(enforce_single_pole_carrier(session.party, session=session))

    def _feed_hungry_heroes(self, session: SessionState, character_ids: list[str] | None) -> None:
        if session.mode != "exploration":
            session.log.append("Food rations are eaten during exploration or while camped outside.")
            return
        session.log.extend(feed_hungry_heroes(session, session.party, character_ids=character_ids))
        session.log.extend(enforce_single_pole_carrier(session.party, session=session))

    def _milestone_member(self, session: SessionState, character_id: str | None) -> PartyMemberState | None:
        if not character_id:
            session.log.append("Choose a hero for this Milestone action.")
            return None
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("That hero is not in the active party.")
            return None
        return member

    def _use_hireling_ability(
        self,
        session: SessionState,
        hireling_id: str | None,
        ability: str | None,
        *,
        character_id: str | None = None,
        item_name: str | None = None,
        gold_amount: int | None = None,
        show_rolls: bool = True,
    ) -> None:
        from .hirelings import _hireling_by_id, _mark_ability_used, use_hireling_ability

        if not ability:
            session.log.append("Choose a retainer ability.")
            return
        log = use_hireling_ability(
            session,
            hireling_id,
            ability,
            character_id=character_id,
            item_name=item_name,
            gold_amount=gold_amount,
            show_rolls=show_rolls,
        )
        if log and log[0].startswith("GUIDE_REROLL:"):
            kind = log[0].split(":", 1)[1]
            hireling = _hireling_by_id(session, hireling_id)
            if hireling is None:
                return
            _mark_ability_used(hireling, "guide_reroll")
            tile = self._current_tile(session)
            if kind == "search":
                if not tile.searched:
                    session.log.append("Search this location first, then the guide can reroll the result.")
                    hireling.uses_spent.pop("guide_reroll", None)
                    return
                tile.searched = False
                session.pending_search_reward_tile_id = None
                session.log.append(f"{hireling.name} rerolls the search table.")
                self._search(session, character_id=character_id, show_rolls=show_rolls, explain_math=False)
                return
            if kind == "room":
                if tile.content_key == "entrance":
                    session.log.append("The guide cannot reroll the entrance.")
                    hireling.uses_spent.pop("guide_reroll", None)
                    return
                if tile.resolved or any(enemy.life > 0 for enemy in tile.enemies) or tile.defeated_enemies:
                    session.log.append("The guide can reroll room content only before foes are fought here.")
                    hireling.uses_spent.pop("guide_reroll", None)
                    return
                hcl = self._highest_character_level(session.party)
                content = self._roll_content(session, tile.tile_type, hcl)
                tile.content_key = content["key"]
                tile.description = content["description"]
                tile.objects = list(content["objects"])
                tile.enemies = list(content["enemies"])
                tile.initial_enemy_count = len(content["enemies"])
                tile.resolved = False
                tile.searched = False
                tile.trap_key = None
                tile.trap_level = None
                tile.trap_resolved = False
                tile.trap_probed = False
                tile.treasure_summary = None
                tile.treasure_gold = 0
                tile.treasure_items = []
                tile.treasure_claimed = False
                if content.get("treasure_summary"):
                    tile.treasure_summary = str(content["treasure_summary"])
                    tile.treasure_gold = int(content.get("treasure_gold") or 0)
                    tile.treasure_items = list(content.get("treasure_items") or [])
                tile.special_event_key = None
                tile.special_event_summary = None
                self._seed_tile_features(tile, hcl, show_rolls=show_rolls, session=session)
                self._resolve_event_foes(session, tile, show_rolls=show_rolls)
                session.log.append(f"{hireling.name} rerolls the room content table.")
                return
            if kind == "wandering":
                if not tile.enemies:
                    session.log.append("No wandering monsters are present to reroll.")
                    hireling.uses_spent.pop("guide_reroll", None)
                    return
                if session.mode == "combat":
                    session.log.append("The guide cannot reroll wandering monsters mid-fight.")
                    hireling.uses_spent.pop("guide_reroll", None)
                    return
                tile.enemies = []
                session.log.append(f"{hireling.name} rerolls the Wandering Monsters table.")
                self._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)
                return
            session.log.append("Unknown guide reroll type.")
            return
        session.log.extend(log)

    def _require_camped_for_milestone(self, session: SessionState) -> bool:
        if session.camped_outside:
            return True
        session.log.append("Milestone management is available only while camped outside the dungeon.")
        return False

    def _assign_milestone(self, session: SessionState, character_id: str | None, milestone_id: str | None) -> None:
        if not self._require_camped_for_milestone(session):
            return
        member = self._milestone_member(session, character_id)
        if member is None:
            return
        from .milestones import assign_milestone

        session.log.extend(assign_milestone(member, milestone_id))

    def _bind_scroll_librarian(self, session: SessionState, character_id: str | None, spell_name: str | None) -> None:
        if not self._require_camped_for_milestone(session):
            return
        member = self._milestone_member(session, character_id)
        if member is None:
            return
        from .milestones import bind_scroll_librarian

        session.log.extend(bind_scroll_librarian(member, spell_name or ""))

    def _craft_gem_collector_jewelry(self, session: SessionState, character_id: str | None) -> None:
        if not self._require_camped_for_milestone(session):
            return
        member = self._milestone_member(session, character_id)
        if member is None:
            return
        from .milestones import craft_gem_collector_jewelry

        session.log.extend(craft_gem_collector_jewelry(member))

    def _create_panoplia(self, session: SessionState, character_id: str | None) -> None:
        if not self._require_camped_for_milestone(session):
            return
        member = self._milestone_member(session, character_id)
        if member is None:
            return
        from .milestones import create_panoplia

        session.log.extend(create_panoplia(member))

    def _use_panoplia_favor(self, session: SessionState, character_id: str | None, favor_kind: str | None) -> None:
        if not self._require_camped_for_milestone(session):
            return
        member = self._milestone_member(session, character_id)
        if member is None or not favor_kind:
            session.log.append("Choose a Panoplia favor.")
            return
        from .milestones import use_panoplia_favor

        session.log.extend(use_panoplia_favor(member, favor_kind))

    def _pay_thrice_blessed_sacrifice(self, session: SessionState, character_id: str | None) -> None:
        if not self._require_camped_for_milestone(session):
            return
        member = self._milestone_member(session, character_id)
        if member is None:
            return
        from .milestones import pay_thrice_blessed_sacrifice

        session.log.extend(pay_thrice_blessed_sacrifice(member))

    def _use_mushroom(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to use the mushroom.")
            return
        available = [item for item in member.inventory if is_mushroom(item)]
        if not available:
            session.log.append(f"{member.name} has no mushrooms.")
            return
        mushroom_name = (
            item_name if item_name and item_name in member.inventory and is_mushroom(item_name) else None
        )
        if mushroom_name is None:
            mushroom_name = available[0] if len(available) == 1 else None
        if mushroom_name is None:
            session.log.append("Choose which mushroom to eat.")
            return
        kind = mushroom_kind(mushroom_name)
        if kind in {"red_death", "xicthul"}:
            self._use_fungal_throwable(
                session,
                member,
                mushroom_name,
                kind=kind,
                target_enemy_id=target_enemy_id,
                show_rolls=show_rolls,
            )
            return
        if kind == "morel_crusher":
            self._use_morel_crusher(session, member, mushroom_name, target_enemy_id=target_enemy_id, show_rolls=show_rolls)
            return
        if session.mode == "combat" and kind not in {"slumber_amanita", "puffball_smokebomb"}:
            session.log.append("It is not possible to eat mushrooms during combat.")
            return
        if session.mode not in {"exploration", "combat"}:
            session.log.append("Mushrooms can be used during exploration or combat when their rule allows it.")
            return
        log_lines, consumed = use_mushroom(
            member, mushroom_name, mode=session.mode, show_rolls=show_rolls, session=session
        )
        session.log.extend(log_lines)
        if consumed:
            member.inventory = [item for item in member.inventory if item != mushroom_name]
            if kind == "puffball_smokebomb":
                session.puffball_flee = True

    def _morel_crusher_unaffected_reason(self, session: SessionState, enemy: EnemyState) -> str | None:
        tags = {tag.lower() for tag in enemy.tags}
        name = enemy.name.lower()
        if session.reaction_key == "fight_to_death":
            return "Foes who rolled a fight-to-the-death Reaction are unaffected."
        if enemy.category == "boss" and "final_boss" in tags:
            return "Foes who never Test Morale are unaffected."
        if tags.intersection({"no_morale", "fear_attack"}):
            return "Foes who never Test Morale are unaffected."
        if tags.intersection({"undead", "spirit", "artificial", "construct", "clockwork", "elemental"}) or any(
            word in name for word in ("skeleton", "zombie", "wight", "wraith", "ghost")
        ):
            return "Unliving Foes are unaffected by Morel Crusher."
        if tags.intersection({"poison_immune", "immune_poison", "poison-immune"}):
            return "Poison-immune Foes are unaffected by Morel Crusher."
        return None

    def _use_morel_crusher(
        self,
        session: SessionState,
        member: PartyMemberState,
        item_name: str,
        *,
        target_enemy_id: str | None,
        show_rolls: bool,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Morel Crusher is broken during combat to frighten a foe.")
            return
        tile = self._current_tile(session)
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living:
            session.log.append("There are no foes to target with Morel Crusher.")
            return
        target = next((enemy for enemy in living if enemy.id == target_enemy_id), None)
        if target is None:
            session.log.append("Choose a foe to target with Morel Crusher.")
            return
        reason = self._morel_crusher_unaffected_reason(session, target)
        if reason:
            session.log.append(reason)
            return
        if not self._commit_immediate_attack(session):
            return
        member.inventory = [item for item in member.inventory if item != item_name]
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in combat_party(session, tile.id) if pc.current_life > 0}
        roll = roll_d6()
        template = self._monster_template_for_enemy(target)
        from .fungal_rare_items import morel_crusher_morale_total, template_morale_modifier

        morale_mod = template_morale_modifier(template)
        total = morel_crusher_morale_total(roll, morale_modifier=morale_mod)
        if show_rolls:
            detail = f"d6 = {roll} - 1"
            if morale_mod:
                detail += f" + {morale_mod} (foe Morale modifier)"
            session.log.append(f"Morel Crusher morale roll: {detail} = {total}.")
        if total <= 3:
            target.life = 0
            session.log.append(f"Morel Crusher frightens {target.name}; it flees.")
            result = CombatRound(
                party=session.party,
                enemies=tile.enemies,
                log=[],
                combat_over=not any(enemy.life > 0 for enemy in tile.enemies),
                morale_failed=True,
            )
            if result.combat_over:
                self._apply_combat_result(
                    session,
                    tile,
                    result,
                    show_rolls=show_rolls,
                    active_enemy_ids=active_enemy_ids,
                    standing_before=standing_before,
                )
            else:
                session.log.append("Other foes remain after the Morel Crusher.")
            return
        session.log.append(f"{target.name} resists the hallucinations.")

    def _use_fungal_throwable(
        self,
        session: SessionState,
        member: PartyMemberState,
        item_name: str,
        *,
        kind: str,
        target_enemy_id: str | None,
        show_rolls: bool,
    ) -> None:
        if session.mode != "combat":
            session.log.append(f"{item_name} is thrown during combat (requires 1 turn).")
            return
        tile = self._current_tile(session)
        party_here = combat_party(session, tile.id)
        if member.character_id not in {pc.character_id for pc in party_here}:
            session.log.append(f"{member.name} is not on the current map element.")
            return
        living = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living:
            session.log.append(f"There are no foes to target with {item_name}.")
            return
        target = next((enemy for enemy in living if enemy.id == target_enemy_id), None)
        if target is None:
            session.log.append(f"Choose a foe to throw {item_name} at.")
            return
        if not self._commit_immediate_attack(session):
            return
        member.inventory = [item for item in member.inventory if item != item_name]
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        from .fungal_rare_items import throw_red_death, throw_xicthuls_cap

        if kind == "red_death":
            log_lines, _consumed = throw_red_death(member, target, item_name, show_rolls=show_rolls)
        else:
            log_lines, _consumed = throw_xicthuls_cap(member, target, show_rolls=show_rolls)
        session.log.extend(log_lines)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._apply_combat_result(
                session,
                tile,
                CombatRound(
                    party=session.party,
                    enemies=tile.enemies,
                    log=[],
                    combat_over=True,
                ),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )

    def _use_acid_vial(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Acid vials can only be thrown during combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to throw acid.")
            return
        available = [item for item in member.inventory if is_acid_vial(item)]
        if not available:
            session.log.append(f"{member.name} has no acid vial.")
            return
        vial_name = item_name if item_name and item_name in member.inventory and is_acid_vial(item_name) else None
        if vial_name is None:
            vial_name = available[0] if len(available) == 1 else None
        if vial_name is None:
            session.log.append("Choose which acid vial to throw.")
            return

        tile = self._current_tile(session)
        party_here = combat_party(session, tile.id)
        if member.character_id not in {pc.character_id for pc in party_here}:
            session.log.append(f"{member.name} is not on the current map element.")
            return
        living_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
        if not living_enemies:
            session.log.append("There are no foes to target.")
            return
        target = next((enemy for enemy in living_enemies if enemy.id == target_enemy_id), None)
        if target is None:
            target = living_enemies[0]

        if not self._commit_immediate_attack(session):
            return
        member.inventory = [item for item in member.inventory if item != vial_name]
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        log_lines, _hit = throw_acid_vial(member, target, show_rolls=show_rolls)
        session.log.extend(log_lines)
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._apply_combat_result(
                session,
                tile,
                CombatRound(
                    party=session.party,
                    enemies=tile.enemies,
                    log=[],
                    combat_over=True,
                ),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )

    def _use_arrow_of_slaying(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        target_enemy_id: str | None = None,
        show_rolls: bool = True,
    ) -> None:
        if session.mode != "combat":
            session.log.append("Arrow of Slaying can only be used during combat.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to fire the Arrow of Slaying.")
            return
        if barbarian_cannot_use_magic(member.class_id):
            session.log.append("Barbarians cannot use magic items. Transfer the Arrow of Slaying to an ally.")
            return
        if not self._member_has_bow(member):
            session.log.append("Arrow of Slaying may be used only by a PC with a bow.")
            return
        available = [item for item in member.inventory if "arrow of slaying" in item.lower()]
        if not available:
            session.log.append(f"{member.name} has no Arrow of Slaying.")
            return
        arrow_name = item_name if item_name and item_name in member.inventory and "arrow of slaying" in item_name.lower() else available[0]
        designed_target = self._arrow_of_slaying_target_name(arrow_name)
        if not designed_target:
            session.log.append("This Arrow of Slaying has no designed target; find a PDF-rolled Arrow of Slaying first.")
            return

        tile = self._current_tile(session)
        party_here = combat_party(session, tile.id)
        if member.character_id not in {pc.character_id for pc in party_here}:
            session.log.append(f"{member.name} is not on the current map element.")
            return
        living_major = [enemy for enemy in tile.enemies if enemy.life > 0 and enemy.category in {"weird", "boss"}]
        if not living_major:
            session.log.append("Arrow of Slaying must target a living Major Foe.")
            return
        target = next((enemy for enemy in living_major if enemy.id == target_enemy_id), None)
        if target is None:
            target = next((enemy for enemy in living_major if enemy.name == designed_target), None) or living_major[0]
        if target.name != designed_target:
            session.log.append(
                f"Arrow of Slaying was made for {designed_target}; it cannot be used against {target.name}."
            )
            return

        if not self._commit_immediate_attack(session):
            return
        active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
        standing_before = {pc.character_id for pc in party_here if pc.current_life > 0}
        member.inventory.remove(arrow_name)
        apply_enemy_damage(target, 3, damage_kind="normal")
        session.log.append(f"{member.name} uses Arrow of Slaying on {target.name}: 3 automatic damage.")
        if apply_major_foe_level_drop(target):
            session.log.append(f"{target.name} is bloodied; its effective Level drops to L{target.level}.")
        if target.life <= 0:
            session.log.append(f"{target.name} is defeated by the Arrow of Slaying.")
        if not any(enemy.life > 0 for enemy in tile.enemies):
            self._apply_combat_result(
                session,
                tile,
                CombatRound(
                    party=session.party,
                    enemies=tile.enemies,
                    log=[],
                    combat_over=True,
                ),
                show_rolls=show_rolls,
                active_enemy_ids=active_enemy_ids,
                standing_before=standing_before,
            )

    def _member_has_bow(self, member: PartyMemberState) -> bool:
        if select_missile_weapon(member) is None:
            return False
        return any("bow" in item.lower() and "crossbow" not in item.lower() for item in member.inventory)

    def _arrow_of_slaying_target_name(self, item_name: str) -> str | None:
        match = re.search(r"target:\s*([^)]+)", item_name, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _use_potion(
        self,
        session: SessionState,
        character_id: str | None,
        item_name: str | None = None,
        *,
        show_rolls: bool,
    ) -> None:
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to use the potion.")
            return
        if session.mode in {"exploration", "combat"}:
            tile = self._current_tile(session)
            if member.character_id not in {pc.character_id for pc in combat_party(session, tile.id)}:
                session.log.append(f"{member.name} is not on the current map element.")
                return
        if barbarian_cannot_use_magic(member.class_id):
            session.log.append(
                f"{member.name} cannot use potions (barbarians may not use magic items, scrolls, or potions). "
                "Transfer the potion to an ally."
            )
            return

        available = usable_potions_in_inventory(member)
        if not available:
            session.log.append(f"{member.name} has no potions.")
            return
        potion_name = item_name if item_name and item_name in member.inventory else None
        if potion_name is None:
            if len(available) == 1:
                potion_name = available[0]
            else:
                session.log.append("Choose which potion to use.")
                return

        kind = potion_kind(potion_name)
        if kind == "sleep":
            if session.mode != "combat":
                session.log.append("Potion of Sleep can only be used during combat.")
                return
            tile = self._current_tile(session)
            if not any(enemy.life > 0 for enemy in tile.enemies):
                session.log.append("There are no foes to target.")
                return
            if not self._commit_immediate_attack(session):
                return
            from .courtship_lex import apply_lex_soul_tax_if_needed

            if not apply_lex_soul_tax_if_needed(session, member, potion_name, show_rolls=show_rolls):
                return
            remove_inventory_item(member, potion_name)
            session.log.append(f"{member.name} quaffs {potion_name}.")
            active_enemy_ids = {enemy.id for enemy in tile.enemies if enemy.life > 0}
            standing_before = {pc.character_id for pc in session.party if pc.current_life > 0}
            outcome = cast_sleep_effect(member, session.party, tile.enemies, show_rolls=show_rolls)
            session.log.extend(outcome.log)
            session.party = self._merge_party_outcome(session.party, outcome.party)
            tile.enemies = outcome.enemies
            if outcome.combat_over and session.mode == "combat":
                self._record_peaceful_quest_progress(session)
                result = CombatRound(
                    party=outcome.party,
                    enemies=outcome.enemies,
                    log=[],
                    combat_over=True,
                )
                self._apply_combat_result(
                    session,
                    tile,
                    result,
                    show_rolls=show_rolls,
                    active_enemy_ids=active_enemy_ids,
                    standing_before=standing_before,
                )
            return

        if kind != "healing":
            session.log.append(f"{member.name} does not know how to use {potion_name}.")
            return
        tile = self._current_tile(session) if session.mode in {"exploration", "combat"} else None
        from .forsaken_depths_citadel import fd_citadel_of_dead_blocks_healing

        dead_block = fd_citadel_of_dead_blocks_healing(session, tile, source="potion")
        if dead_block:
            session.log.append(dead_block)
            return
        blocked = bulwark_magical_healing_blocked(session, member)
        if blocked:
            session.log.append(blocked)
            return
        if member.character_id in session.potion_used_character_ids:
            session.log.append(f"{member.name} already drank a Potion of Healing this adventure.")
            return
        from .courtship_lex import apply_lex_soul_tax_if_needed

        if not apply_lex_soul_tax_if_needed(session, member, potion_name, show_rolls=show_rolls):
            return
        remove_inventory_item(member, potion_name)
        lost_life = member.max_life - member.current_life
        member.current_life = member.max_life
        session.potion_used_character_ids.append(member.character_id)
        if show_rolls:
            session.log.append(
                f"{member.name} drinks {potion_name} and restores {lost_life} Life "
                f"({member.current_life}/{member.max_life})."
            )

    def _accept_quest(self, session: SessionState, *, show_rolls: bool) -> None:
        if session.mode == "combat":
            session.log.append("Deal with the fight before speaking to the Lady in White.")
            return
        tile = self._current_tile(session)
        if not tile.lady_in_white_available:
            session.log.append("The Lady in White is not here.")
            return
        if session.active_quest is not None:
            session.log.append("A Quest is already in progress.")
            return
        speaker = self._member_by_marching_order(session, 1)
        if speaker is None:
            session.log.append("No hero is available to speak with the Lady in White.")
            return
        hcl = self._highest_character_level(session.party)
        ok, social_log = resolve_social_save(
            session,
            speaker,
            hcl,
            show_rolls=show_rolls,
            label="impress the Lady in White",
        )
        session.log.extend(social_log)
        if not ok:
            session.log.append("The Lady in White withdraws without offering a Quest.")
            return
        roll = roll_d6()
        if show_rolls:
            session.log.append(f"Quest roll: d6 = {roll}.")
        row = self.table_roller.lookup("quest_table", roll)
        if row is None:
            session.log.append("Quest table lookup failed.")
            return
        gold_required = None
        item_name = None
        if row["key"] == "bring_gold":
            gold_required = roll * 50
            party_gold = sum(member.gold for member in session.party if member.current_life > 0)
            if party_gold >= gold_required:
                gold_required *= 2
                session.log.append(f"Party already has {party_gold}gp; quest gold doubled to {gold_required}gp.")
        if row["key"] == "bring_item":
            magic_row = self.table_roller.lookup("dungeon_magic_treasure_table", roll_d6())
            if magic_row and magic_row.get("items"):
                item_name = magic_row["items"][0]
            elif magic_row:
                item_name = magic_row.get("result", "Magic item")
            else:
                item_name = "Magic item"
        boss_target_name = self._roll_quest_boss_target_name(session) if row["key"] == "bring_head" else None
        quest = quest_from_row(
            row,
            tile_id=tile.id,
            gold_required=gold_required,
            item_name=item_name,
            boss_target_name=boss_target_name,
        )
        session.active_quest = quest
        tile.lady_in_white_available = False
        session.log.append(f"Quest accepted: {quest.description}")
        if quest.gold_required:
            session.log.append(f"Quest progress: deliver {quest.gold_required}gp to this tile to complete the Quest.")
        elif quest.key == "bring_head":
            target = f" Quest target: {quest.boss_target_name}." if quest.boss_target_name else ""
            session.log.append(
                f"Quest progress: slay the Quest Boss, take its head, then return to this tile to claim the Epic reward.{target}"
            )
        elif quest.key == "bring_alive":
            session.log.append("Quest progress: subdue a Boss alive with Subdual damage, then return to this tile.")
        elif quest.key == "bring_item":
            session.log.append(f"Quest progress: find {quest.item_name} from a defeated Major Foe, then return to this tile.")
        elif quest.key == "peaceful_way":
            session.log.append(
                f"Quest progress: complete {quest.peaceful_required} peaceful encounters by bribe, peaceful reaction, or Sleep."
            )
        elif quest.key == "slay_all":
            session.log.append("Quest progress: defeat the Final Boss and clear all remaining foes.")

    def _refuse_quest(self, session: SessionState) -> None:
        tile = self._current_tile(session)
        if not tile.lady_in_white_available:
            session.log.append("The Lady in White is not here.")
            return
        session.lady_in_white_refused = True
        tile.lady_in_white_available = False
        session.log.append("You refuse the Quest. The Lady in White vanishes and will not return this adventure.")

    def _claim_quest_reward(self, session: SessionState, *, show_rolls: bool) -> None:
        quest = session.active_quest
        if quest is None:
            session.log.append("No active Quest.")
            return
        if session.adventure_type == "imported" and is_generated_tag_manifest(session.imported_manifest):
            session.log.append(
                "Quest reward blocked: generated Adventures Guild scenes use their printed scene rewards and TAG Action buttons, not the core Epic Rewards table."
            )
            session.log.append(
                "Use the current room prompt or Adventures Guild Actions for purchases, services, bounties, route rewards, XP markers, Guild share, banking, and closeout signoff."
            )
            return
        if quest.reward_claimed:
            session.log.append("Quest reward already claimed.")
            return
        tile = self._current_tile(session)
        requires_turn_in = quest.key in {"bring_gold", "bring_item", "bring_head", "bring_alive"}
        if requires_turn_in or not quest.completed:
            ready, message = quest_ready_to_complete(tile.id, quest, session)
            if not ready:
                session.log.append(f"Quest turn-in blocked: {message}")
                return
            if quest.key == "bring_gold":
                remaining = quest.gold_required
                for member in sorted(session.party, key=lambda item: item.marching_order):
                    if remaining <= 0 or member.current_life <= 0:
                        continue
                    paid = min(member.gold, remaining)
                    member.gold -= paid
                    remaining -= paid
            quest.completed = True
        reward_roll = roll_d6()
        if show_rolls:
            session.log.append(f"Epic reward roll: d6 = {reward_roll}.")
        row = self.table_roller.lookup("epic_rewards_table", reward_roll)
        if row is None:
            session.log.append("Epic Rewards table lookup failed.")
            return
        reward_text = epic_reward_item(row)
        survivors = [member for member in session.party if member.current_life > 0]
        if not survivors:
            session.log.append("There is no survivor to receive the Quest reward.")
            return
        key = row.get("key", "")
        if key not in {"gold_of_kerrak_dar", "enchanted_weapon"}:
            item_label = "Book of Skalitos (6 pages)" if key == "book_of_skalitos" else reward_text.split(".")[0]
            ok, message = can_add_item(survivors[0], item_label)
            if not ok:
                session.log.append(message)
                return
        quest.reward_claimed = True
        session.log.append(f"Quest complete! Epic reward: {reward_text}")
        if key == "gold_of_kerrak_dar":
            if KERRAK_DAR_STATUS not in survivors[0].statuses:
                survivors[0].statuses.append(KERRAK_DAR_STATUS)
            session.log.append(
                f"{survivors[0].name} marks Kerrak Dar's hoard; spend 1 held Clue while exploring to find 500gp."
            )
        elif key == "enchanted_weapon":
            if ENCHANTED_WEAPON_STATUS not in survivors[0].statuses:
                survivors[0].statuses.append(ENCHANTED_WEAPON_STATUS)
            session.log.append(f"{survivors[0].name}'s weapon is enchanted until adventure end.")
        else:
            if key == "book_of_skalitos":
                item_label = "Book of Skalitos (6 pages)"
            elif key == "arrow_of_slaying":
                target_name = self._roll_epic_major_foe_target_name(session) or "Major Foe"
                item_label = f"Arrow of Slaying (target: {target_name})"
                session.log.append(f"Arrow of Slaying target rolled: {target_name}.")
            else:
                item_label = reward_text.split(".")[0]
            survivors[0].inventory.append(item_label)
            session.log.append(f"{survivors[0].inventory[-1]} added to {survivors[0].name}'s inventory.")
        session.active_quest = None

    def _record_peaceful_quest_progress(self, session: SessionState) -> None:
        quest = session.active_quest
        if quest is None or quest.key != "peaceful_way" or quest.completed:
            return
        quest.peaceful_count += 1
        session.log.append(
            f"Peaceful quest progress: {quest.peaceful_count}/{quest.peaceful_required}."
        )
        if quest.peaceful_count >= quest.peaceful_required:
            quest.completed = True
            session.log.append("Quest objective complete: peaceful encounters finished. Claim your Epic reward.")

    def _update_quest_on_combat_end(
        self,
        session: SessionState,
        defeated: list[EnemyState],
        *,
        show_rolls: bool,
    ) -> None:
        quest = session.active_quest
        if quest is None or quest.completed:
            return
        cave_state = self._tag_cave_room_count_state(session)
        if cave_state is not None:
            tile = self._current_tile(session)
            recorded = cave_state["recorded"]
            state = cave_state["state"]
            final_room_tile_id = str(recorded.get("final_room_tile_id") or "")
            final_boss_ids = {
                enemy.id
                for enemy in defeated
                if "tag_treasure_map_finale" in {tag.lower() for tag in enemy.tags}
                or "final_boss" in {tag.lower() for tag in enemy.tags}
            }
            if final_room_tile_id and tile.id == final_room_tile_id and final_boss_ids:
                quest.completed = True
                quest.tag_procedure_signoff = True
                recorded["finale_defeated"] = True
                recorded["completed"] = True
                recorded["route_recorded"] = True
                state["map_cave_room_count"] = recorded
                state["route_recorded"] = True
                state["route_note"] = "Auto route: Underground caves target room reached and final Boss defeated."
                state["next_action"] = (
                    "Underground caves destination complete: final Boss defeated. "
                    "Claim the Treasure Map quest reward when ready, after any treasure, XP, Guild share, banking, or storage choices."
                )
                quest.tag_procedure_state = state
                session.log.append(
                    "TAG Treasure Map objective complete: Underground caves final Boss defeated. "
                    "Claim the Treasure Map quest reward when ready."
                )
                return
        from .forsaken_depths_map import is_fd_ruleset
        from .forsaken_depths_quest import update_fd_quest_on_combat_end

        if is_fd_ruleset(session):
            update_fd_quest_on_combat_end(session, defeated, show_rolls=show_rolls)
        if session.adventure_type == "imported":
            tile = self._current_tile(session)
            update_imported_quest_on_combat_end(session, defeated, tile)
            return
        for enemy in defeated:
            if quest.key == "bring_item" and not quest.item_collected and enemy.category in {"weird", "boss"}:
                if roll_d6() == 1:
                    quest.item_collected = True
                    session.log.append(f"Quest progress: {quest.item_name} found on {enemy.name}; return to the Quest-giver.")
                    session.log.append("Quest objective complete: return to the Quest-giver with the item.")
                elif show_rolls:
                    session.log.append(f"Quest progress: no {quest.item_name} found on {enemy.name}.")
            if enemy.category == "boss":
                if quest.key == "bring_head" and quest.boss_slay_pending and not enemy.subdued:
                    if quest.boss_target_name and enemy.name != quest.boss_target_name:
                        session.log.append(
                            f"Quest progress: {enemy.name} was slain, but the bring-head Quest target is {quest.boss_target_name}."
                        )
                        continue
                    quest.boss_slay_pending = False
                    quest.boss_head_acquired = True
                    session.log.append(f"Quest progress: {enemy.name} slain; the party takes its head.")
                    session.log.append("Quest objective ready: return to the Quest-giver's tile with the Boss head.")
                elif quest.key == "bring_head" and quest.boss_slay_pending and enemy.subdued:
                    session.log.append(
                        f"Quest progress: {enemy.name} was subdued, not slain; bring-head Quest still needs a slain Boss."
                    )
                elif quest.key == "bring_alive" and quest.boss_capture_pending and enemy.subdued:
                    quest.boss_capture_pending = False
                    quest.captured_boss_name = enemy.name
                    quest.completed = True
                    session.log.append(
                        f"Quest progress: {enemy.name} was subdued alive; return to the Quest-giver."
                    )
                    session.log.append("Quest objective complete: return to the Quest-giver with the living captive.")
                elif quest.key == "bring_alive" and quest.boss_capture_pending and not enemy.subdued:
                    session.log.append(
                        f"Quest progress: {enemy.name} was slain, not subdued; bring-alive Quest still needs a living captive."
                    )
        if quest.key == "slay_all" and session.final_boss_defeated:
            large_enough = (
                session.map_bounds_mode != "unlimited"
                or (session.map_state.width >= 20 and session.map_state.height >= 28)
            )
            all_clear = all(not any(e.life > 0 for e in tile.enemies) for tile in session.map_state.tiles)
            if large_enough and all_clear:
                quest.completed = True
                session.log.append("Quest progress: slay-all Quest complete! Claim your Epic reward.")
                session.log.append("Quest objective complete: Final Boss defeated and all foes cleared.")

    def _roll_quest_boss_target_name(self, session: SessionState) -> str | None:
        monsters = self.rules.monsters()
        table_key = self._resolve_monster_table_key(session, "boss", log_mixed_roll=False)
        table = monsters.get(table_key) or monsters.get("boss") or []
        if not table:
            return None
        return random.choice(table).get("name")

    def _roll_epic_major_foe_target_name(self, session: SessionState) -> str | None:
        monsters = self.rules.monsters()
        table_keys = major_foe_table_keys(monsters)
        if not table_keys:
            return None
        chosen_key = random.choice(table_keys)
        table = monsters.get(chosen_key, [])
        if not table:
            return None
        session.log.append(
            f"Arrow of Slaying: roll on any Major Foe table (EE p.163) → {chosen_key}."
        )
        return random.choice(table).get("name")

    def _old_school_level_up(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        show_rolls: bool,
        new_spell: str | None = None,
    ) -> None:
        if session.level_up_spell_pending_character_id:
            session.log.append("Finish the pending spell choice before leveling again.")
            return
        if session.xp_system != "old_school":
            session.log.append("Old School leveling is not active for this adventure.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to advance.")
            return
        if not self._can_assign_level_up(session, character_id or ""):
            session.log.append("Another hero must level next (same PC cannot level twice in a row).")
            return
        cost = old_school_level_cost(member.level)
        if session.old_school_xp_tally < cost:
            session.log.append(f"Need {cost} XP (tally {session.old_school_xp_tally}).")
            return
        session.old_school_xp_tally -= cost
        self._complete_level_up(session, member, new_spell=new_spell)
        if show_rolls:
            session.log.append(f"Old School XP spent: {cost} (tally {session.old_school_xp_tally}).")

    def _slower_xp_spend(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        xp_spent: int | None,
        show_rolls: bool,
        explain_math: bool,
        new_spell: str | None = None,
        advancement_fork: str | None = None,
        expert_skill_id: str | None = None,
        expert_skill_target: str | None = None,
        heroic_skill_id: str | None = None,
        legendary_skill_id: str | None = None,
        heroic_skill_target: str | None = None,
    ) -> None:
        if session.level_up_spell_pending_character_id:
            session.log.append("Finish the pending spell choice before spending more banked XP.")
            return
        if session.xp_system != "slower_advancement":
            session.log.append("Slower Advancement is not active for this adventure.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            session.log.append("Choose a living hero to advance.")
            return
        if not self._can_assign_level_up(session, character_id or ""):
            session.log.append("Another hero must level next (same PC cannot level twice in a row).")
            return
        target_level = member.level + 1
        minimum = target_level
        spent = xp_spent if xp_spent is not None else minimum
        if spent < minimum:
            session.log.append(f"Spend at least {minimum} banked XP to try for Level {target_level}.")
            return
        if session.slower_xp_bank < spent:
            session.log.append(f"Need {spent} banked XP (have {session.slower_xp_bank}).")
            return

        fork = advancement_fork or "level_up"
        blocked = self._validate_advancement_fork(
            member,
            fork,
            expert_skill_id=expert_skill_id,
            expert_skill_target=expert_skill_target,
            heroic_skill_id=heroic_skill_id,
            legendary_skill_id=legendary_skill_id,
            heroic_skill_target=heroic_skill_target,
        )
        if blocked:
            session.log.append(blocked)
            return

        purpose = {
            "level_up": "level_up",
            "learn_expert_skill": "learn_expert_skill",
            "learn_heroic_skill": "learn_heroic_skill",
            "learn_legendary_skill": "learn_legendary_skill",
        }[fork]
        session.slower_xp_bank -= spent
        bonus = spent - minimum
        from .heroic_skill_effects import consume_training_focus_bonus

        focus_bonus = consume_training_focus_bonus(session, member.character_id)
        bonus += focus_bonus
        result = perform_advancement_roll(member, bonus=bonus, purpose=purpose)
        if focus_bonus:
            session.log.append(f"{member.name} applies Training Focus (+{focus_bonus}).")
        if show_rolls:
            session.log.append(
                f"Slower {advancement_fork_label(fork).lower()} for {member.name}: {spent} XP banked, "
                f"{result.die_label} = {result.natural}"
                + (f" + {result.modifier} = {result.total}" if result.modifier else "")
                + f" vs Level {member.level}."
            )
        if explain_math:
            session.log.append(advancement_roll_explain(member))
        if advancement_succeeds(result, member.level):
            self._apply_advancement_success(
                session,
                member,
                fork,
                new_spell=new_spell,
                expert_skill_id=expert_skill_id,
                expert_skill_target=expert_skill_target,
                heroic_skill_id=heroic_skill_id,
                legendary_skill_id=legendary_skill_id,
                heroic_skill_target=heroic_skill_target,
            )
        elif fork == "level_up":
            session.log.append(f"{member.name} fails to advance (needs > {member.level} with bonus).")
        else:
            session.log.append(
                f"{member.name} fails to learn the {advancement_fork_label(fork).lower()} "
                f"(needs > {member.level} with bonus)."
            )

    def _spend_training_xp_rolls(
        self,
        session: SessionState,
        member: PartyMemberState,
        amount: int,
    ) -> tuple[bool, list[str], int, int]:
        if amount <= 0:
            return True, [], 0, 0
        available = member.xp + session.xp_rolls_pending
        if available < amount:
            return False, [], 0, 0
        remaining = amount
        log: list[str] = []
        banked_take = min(member.xp, remaining)
        if banked_take:
            member.xp -= banked_take
            remaining -= banked_take
            log.append(f"{member.name} spends {banked_take} assigned XP roll(s).")
        if remaining:
            session.xp_rolls_pending -= remaining
            log.append(f"{member.name} spends {remaining} pending party XP roll(s).")
        return True, log, banked_take, remaining

    def _enter_tier_training(
        self,
        session: SessionState,
        character_id: str | None,
        *,
        tier: str | None,
        use_xp: bool,
        show_rolls: bool,
    ) -> None:
        if session.mode == "combat":
            session.log.append("Tier training waits until combat ends.")
            return
        if tier not in {"expert", "heroic", "legendary", "epic"}:
            session.log.append("Choose Expert, Heroic, Legendary, or Epic tier training.")
            return
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None:
            session.log.append("Choose a hero for tier training.")
            return
        blocked = tier_entry_blocked_reason(member, tier)
        if blocked:
            session.log.append(blocked)
            return
        spec = tier_entry_requirements(tier)
        xp_cost = int(spec.get("xp", 0))
        gold_cost = int(spec.get("gold", 0))

        if tier == "expert" and use_xp:
            xp_alt = int(spec.get("xp_alt", 0))
            if xp_alt <= 0:
                session.log.append("Expert training requires gold payment.")
                return
            paid_xp, xp_log, _, _ = self._spend_training_xp_rolls(session, member, xp_alt)
            if not paid_xp:
                session.log.append(
                    f"Need {xp_alt} assigned or pending XP roll (have {member.xp + session.xp_rolls_pending})."
                )
                return
            if show_rolls:
                session.log.extend(xp_log)
                session.log.append(f"{member.name} enters Expert tier (1 XP roll spent; no gold).")
        else:
            if xp_cost > 0:
                paid_xp, xp_log, assigned_spent, pending_spent = self._spend_training_xp_rolls(session, member, xp_cost)
                if not paid_xp:
                    session.log.append(
                        f"Need {xp_cost} assigned or pending XP roll(s) for {tier.title()} training "
                        f"(have {member.xp + session.xp_rolls_pending})."
                    )
                    return
            else:
                xp_log = []
                assigned_spent = 0
                pending_spent = 0
            paid, payment_log = self._spend_outside_party_gold(session, gold_cost, label=f"{tier.title()} training")
            if not paid:
                if xp_cost > 0:
                    member.xp += assigned_spent
                    session.xp_rolls_pending += pending_spent
                available = self._outside_party_gold(session)
                session.log.append(
                    f"Need {gold_cost} gp in carried or home bank funds for {tier.title()} training "
                    f"(have {available})."
                )
                return
            if show_rolls:
                session.log.extend(xp_log)
                session.log.extend(payment_log)
                parts = [f"{gold_cost} gp"]
                if xp_cost:
                    parts.append(f"{xp_cost} banked XP roll(s)")
                session.log.append(
                    f"{member.name} enters {tier.title()} tier ({', '.join(parts)})."
                )

        if tier == "expert":
            member.expert_trained = True
        elif tier == "heroic":
            member.heroic_trained = True
        elif tier == "legendary":
            member.legendary_trained = True
        elif tier == "epic":
            member.epic_trained = True

    def _outside_party_gold(self, session: SessionState) -> int:
        return sum(member.gold + member.bank_gold for member in session.party if member.current_life > 0)

    def _spend_outside_party_gold(
        self,
        session: SessionState,
        amount: int,
        *,
        label: str,
    ) -> tuple[bool, list[str]]:
        if amount <= 0:
            return True, []
        if self._outside_party_gold(session) < amount:
            return False, []
        remaining = amount
        log: list[str] = []
        for member in sorted((item for item in session.party if item.current_life > 0), key=lambda item: item.marching_order):
            if remaining <= 0:
                break
            bank_take = min(member.bank_gold, remaining)
            if bank_take:
                member.bank_gold -= bank_take
                remaining -= bank_take
                log.append(f"{member.name} pays {bank_take}gp from home bank funds for {label}.")
            if remaining <= 0:
                break
            carry_take = min(member.gold, remaining)
            if carry_take:
                member.gold -= carry_take
                remaining -= carry_take
                log.append(f"{member.name} pays {carry_take}gp carried outside for {label}.")
        return True, log

    def _touch(self, session: SessionState) -> SessionState:
        session.updated_at = now_utc()
        return session
