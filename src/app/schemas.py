from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class CharacterClass(BaseModel):
    id: str
    name: str
    base_life: int
    life_offset: int | None = None
    attack_bonus: int = 0
    defense_bonus: int = 0
    save_bonus: int = 0
    starting_gold: int = 0
    starting_wealth_roll: str = ""
    starting_inventory: list[str] = Field(default_factory=list)
    starting_spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    implementation_status: str = "starter"
    description: str = ""
    image: str = ""


ExitDirection = Literal[
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
]


class TileExitDefinition(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    label: str = Field(default="", max_length=80)
    direction: ExitDirection
    kind: Literal["passage", "door"]
    x: int = Field(default=0, ge=0, le=99)
    y: int = Field(default=0, ge=0, le=99)
    span: int = Field(default=1, ge=1, le=20)
    offset: int = Field(default=0, ge=0, le=99)
    position: float = Field(default=0.5, ge=0.0, le=1.0)
    dungeon_exit: bool = False


TileTerrain = Literal[
    "indoor",
    "outdoor",
    "forest",
    "swamp",
    "jungle",
    "desert",
    "water",
    "pond",
    "stream",
    "river",
    "lake",
    "seashore",
]


ForsakenDepthsRoomCode = Literal["NC", "ETC", "ETR", "END", "Ru", "Ca", "B"]


class TileDefinition(BaseModel):
    key: str = Field(pattern=r"^\d{2}$")
    name: str
    catalog: Literal["ee", "forsaken_depths", "forsaken_depths_rivers"] = "ee"
    tile_type: Literal["room", "corridor", "unknown"] = "unknown"
    terrain: TileTerrain = "indoor"
    image: str | None = None
    description: str = ""
    footprint_width: int = Field(default=1, ge=1, le=20)
    footprint_height: int = Field(default=1, ge=1, le=20)
    editor_cell_size: int = Field(default=80, ge=24, le=180)
    image_scale: float = Field(default=1.0, ge=0.1, le=20.0)
    image_offset_x: int = Field(default=0, ge=-1000, le=1000)
    image_offset_y: int = Field(default=0, ge=-1000, le=1000)
    walkable: list[str] = Field(default_factory=list)
    cell_shapes: list[str] = Field(default_factory=list)
    room_codes: list[ForsakenDepthsRoomCode] = Field(default_factory=list)
    exits: list[TileExitDefinition] = Field(default_factory=list)
    implementation_status: str = "placeholder-needs-rulebook-validation"


class IconDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    label: str
    category: Literal["map", "character", "monster", "item", "condition", "ui", "class"] = "map"
    description: str = ""
    file: str = ""
    fallback: str = ""
    source_url: str = ""
    attribution: str = ""
    license: str = ""
    notes: str = ""


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    class_id: str = Field(min_length=1, max_length=40)
    trait_id: str | None = None


class CharacterTransfer(BaseModel):
    target_character_id: str = Field(min_length=1)
    item_name: str | None = None
    gold_amount: int | None = Field(default=None, ge=1)


class CharacterWeaponDefaults(BaseModel):
    default_melee_weapon: str | None = None
    default_melee_weapon_secondary: str | None = None
    default_missile_weapon: str | None = None


class CharacterBuyEquipment(BaseModel):
    item_key: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1, le=99)
    target_weapon: str | None = None


class CharacterSellItem(BaseModel):
    item_name: str = Field(min_length=1)


class MilestonesProgress(BaseModel):
    active_id: str | None = None
    completed_ids: list[str] = Field(default_factory=list)
    levels_goblins: int = Field(default=0, ge=0)
    levels_orcs: int = Field(default=0, ge=0)
    levels_hobgoblins: int = Field(default=0, ge=0)
    levels_kobolds: int = Field(default=0, ge=0)
    lightning_damage: int = Field(default=0, ge=0)
    lightning_exploded: bool = False
    sleep_levels: int = Field(default=0, ge=0)
    witches_slayed: int = Field(default=0, ge=0)
    vermin_slayed: int = Field(default=0, ge=0)
    gaze_saves: int = Field(default=0, ge=0)
    scrolls_collected: int = Field(default=0, ge=0)
    scroll_librarian_spell: str | None = None
    gems_50gp: int = Field(default=0, ge=0)
    gem_collector_crafted: bool = False
    panoplia_ready_inventory: bool = False
    panoplia_styled: bool = False
    panoplia_favor_available: bool = False
    panoplia_favor_used: bool = False
    resurrection_count: int = Field(default=0, ge=0)
    thrice_blessed_unlocked: bool = False
    thrice_blessed_sacrifice_paid: bool = False
    extra_spell_slots: list[str] = Field(default_factory=list)


class CharacterSpendXp(BaseModel):
    advancement_fork: (
        Literal["level_up", "learn_expert_skill", "learn_heroic_skill", "learn_legendary_skill"] | None
    ) = None
    spell_name: str | None = None
    expert_skill_id: str | None = None
    expert_skill_target: str | None = None
    heroic_skill_id: str | None = None
    legendary_skill_id: str | None = None
    heroic_skill_target: str | None = None
    show_rolls: bool = True
    explain_math: bool = False


class EquipmentTransactionResult(BaseModel):
    message: str
    character: Character
    gold_received: int = 0


class Character(BaseModel):
    id: str
    name: str
    class_id: str
    class_name: str
    level: int = 1
    xp: int = 0
    gold: int = 0
    clues: int = Field(default=0, ge=0)
    secrets: list[str] = Field(default_factory=list)
    max_life: int
    current_life: int
    attack_bonus: int = 0
    defense_bonus: int = 0
    save_bonus: int = 0
    inventory: list[str] = Field(default_factory=list)
    spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    class_traits: list[str] = Field(default_factory=list)
    learned_expert_skills: list[str] = Field(default_factory=list)
    learned_heroic_skills: list[str] = Field(default_factory=list)
    learned_legendary_skills: list[str] = Field(default_factory=list)
    expert_skill_targets: dict[str, str] = Field(default_factory=dict)
    statuses: list[str] = Field(default_factory=list)
    madness: int = Field(default=0, ge=0)
    default_melee_weapon: str | None = None
    default_melee_weapon_secondary: str | None = None
    default_missile_weapon: str | None = None
    active_session_id: str | None = None
    companion_kind: str | None = None
    minor_encounters_cleared: int = 0
    expert_trained: bool = False
    heroic_trained: bool = False
    legendary_trained: bool = False
    epic_trained: bool = False
    milestones: MilestonesProgress = Field(default_factory=MilestonesProgress)
    created_at: str
    updated_at: str


class CharacterMilestoneRequest(BaseModel):
    milestone_id: str | None = None
    scroll_librarian_spell: str | None = None


class CharacterPanopliaFavorRequest(BaseModel):
    favor_kind: Literal["gold", "fine", "jail", "resurrection"]


class CharacterMilestoneResult(BaseModel):
    message: str
    character: Character
    log: list[str] = Field(default_factory=list)


class CharacterSpendXpResult(BaseModel):
    message: str
    character: Character
    log: list[str] = Field(default_factory=list)


class CharacterTransferResult(BaseModel):
    message: str
    source: Character
    target: Character


class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    character_ids: list[str] = Field(min_length=4, max_length=4)


class SessionPartyUpdate(BaseModel):
    character_ids: list[str] = Field(min_length=4, max_length=4)


class Party(BaseModel):
    id: str
    name: str
    character_ids: list[str]
    created_at: str
    updated_at: str


class EnemyState(BaseModel):
    id: str
    name: str
    category: str
    level: int
    life: int
    max_life: int
    attacks: int = 1
    tags: list[str] = Field(default_factory=list)
    initial_count: int = 1
    subdued: bool = False
    regen_suppressed: bool = False
    level_drop_applied: bool = False
    on_hit_effects: list[dict] = Field(default_factory=list)
    encounter_start_effects: list[dict] = Field(default_factory=list)
    per_turn_effects: list[dict] = Field(default_factory=list)
    special_attacks: list[dict] = Field(default_factory=list)
    party_attacks_received: int = Field(default=0, ge=0)


class AlchemistOrderState(BaseModel):
    potion_id: str
    potion_name: str
    character_id: str
    difficulty: int = Field(default=0, ge=0, le=6)
    material_gp: int = Field(default=0, ge=0)


class HirelingState(BaseModel):
    id: str
    retainer_type: str
    name: str
    life: int = Field(ge=0)
    max_life: int = Field(ge=1)
    marching_order: int = Field(ge=1, le=6)
    fee_paid_gp: int = Field(default=0, ge=0)
    assigned_character_id: str | None = None
    fanatical: bool = False
    treasure_share_paid: bool = False
    morale_storyteller_used: bool = False
    uses_spent: dict[str, int] = Field(default_factory=dict)
    cargo_gp: int = Field(default=0, ge=0, le=400)
    cargo_items: list[str] = Field(default_factory=list)
    carried_gear: str | None = None
    equipped_weapon: str | None = None
    equipped_armor: str | None = None
    lantern_lit: bool = False


class PartyMemberState(BaseModel):
    character_id: str
    name: str
    class_id: str
    class_name: str
    level: int
    xp: int
    gold: int
    bank_gold: int = Field(default=0, ge=0)
    clues: int = Field(default=0, ge=0)
    secrets: list[str] = Field(default_factory=list)
    current_life: int
    max_life: int
    attack_bonus: int
    defense_bonus: int
    save_bonus: int
    marching_order: int = Field(default=1, ge=1, le=4)
    inventory: list[str] = Field(default_factory=list)
    spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    class_traits: list[str] = Field(default_factory=list)
    learned_expert_skills: list[str] = Field(default_factory=list)
    learned_heroic_skills: list[str] = Field(default_factory=list)
    learned_legendary_skills: list[str] = Field(default_factory=list)
    expert_skill_targets: dict[str, str] = Field(default_factory=dict)
    expert_trained: bool = False
    heroic_trained: bool = False
    legendary_trained: bool = False
    epic_trained: bool = False
    statuses: list[str] = Field(default_factory=list)
    madness: int = Field(default=0, ge=0)
    default_melee_weapon: str | None = None
    default_melee_weapon_secondary: str | None = None
    default_missile_weapon: str | None = None
    starting_weapon_slots: int | None = None
    starting_shields: int | None = None
    companion_kind: str | None = None
    kukla_compartment_items: list[str] = Field(default_factory=list)
    kukla_compartment_gold: int = Field(default=0, ge=0, le=100)
    milestones: MilestonesProgress = Field(default_factory=MilestonesProgress)


class ExitState(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    label: str = Field(default="", max_length=80)
    direction: ExitDirection
    kind: Literal["passage", "door"]
    x: int = Field(default=0, ge=0, le=99)
    y: int = Field(default=0, ge=0, le=99)
    span: int = Field(default=1, ge=1, le=20)
    offset: int = Field(default=0, ge=0, le=99)
    position: float = Field(default=0.5, ge=0.0, le=1.0)
    dungeon_exit: bool = False
    status: Literal["unexplored", "open", "blocked"] = "unexplored"
    destination_tile_id: str | None = None
    door_result: str | None = None
    door_type: str | None = None
    door_level: int | None = None
    door_open: bool = False
    door_treasure_bonus: int = 0
    door_sealed_attempted: bool = False
    door_illusion_attempted_ids: list[str] = Field(default_factory=list)
    door_destroyed: bool = False
    nailed_shut: bool = False
    door_listened: bool = False
    listen_preview: str | None = None
    acute_hearing_cleared: bool = False


class TileState(BaseModel):
    id: str
    x: int
    y: int
    tile_key: str
    tile_type: Literal["room", "corridor"]
    rotation: int = Field(default=0, ge=0, le=270)
    footprint_width: int = Field(default=1, ge=1, le=20)
    footprint_height: int = Field(default=1, ge=1, le=20)
    editor_cell_size: int = Field(default=80, ge=24, le=180)
    image_scale: float = Field(default=1.0, ge=0.1, le=20.0)
    image_offset_x: int = Field(default=0, ge=-1000, le=1000)
    image_offset_y: int = Field(default=0, ge=-1000, le=1000)
    walkable: list[str] = Field(default_factory=list)
    cell_shapes: list[str] = Field(default_factory=list)
    visible: list[str] = Field(default_factory=list)
    image: str | None = None
    title: str
    description: str
    content_key: str = "empty"
    special_event_key: str | None = None
    special_event_summary: str | None = None
    objects: list[str] = Field(default_factory=list)
    enemies: list[EnemyState] = Field(default_factory=list)
    defeated_enemies: list[EnemyState] = Field(default_factory=list)
    fallen_character_ids: list[str] = Field(default_factory=list)
    exits: list[ExitState] = Field(default_factory=list)
    fd_side_sheet: bool = False
    fd_side_sheet_entry_used: bool = False
    tile_catalog: Literal["ee", "forsaken_depths", "forsaken_depths_rivers"] = "ee"
    room_codes: list[ForsakenDepthsRoomCode] = Field(default_factory=list)
    searched: bool = False
    resolved: bool = False
    trap_key: str | None = None
    trap_level: int | None = None
    trap_resolved: bool = False
    trap_probed: bool = False
    treasure_summary: str | None = None
    treasure_gold: int = 0
    treasure_items: list[str] = Field(default_factory=list)
    treasure_claimed: bool = False
    pending_treasure_choice: str | None = None
    fd_secret_passage_room: bool = False
    fd_jackpot_wandering_on_claim: bool = False
    initial_enemy_count: int = 0
    treasure_doubled: bool = False
    wandering_ambush: bool = False
    surprise_party: bool = False
    hidden_treasure_alarm_pending: bool = False
    hidden_treasure_complication_effect_pending: str | None = None
    hidden_pit_secret_passage_available: bool = False
    environment_event_resolved: bool = False
    healer_available: bool = False
    alchemist_available: bool = False
    lady_in_white_available: bool = False
    fd_lady_in_gray_available: bool = False
    fd_portal_available: bool = False
    fd_hidden_treasure_chamber: bool = False
    fd_hidden_treasure_claimed: bool = False
    fd_cyclopean_idol_available: bool = False
    fd_cyclopean_idol_resolved: bool = False
    final_boss_treasure: bool = False
    deal_treasure_forbidden: bool = False
    prisoner_discovered: bool = False
    prisoner_chains_broken: bool = False
    major_foe_encounter_counted: bool = False
    mantlebeast_spotted: bool = False
    mantlebeast_ambush_resolved: bool = False
    spider_webs_burned: bool = False
    environment: Literal["dungeon", "caverns", "fungal_grottoes"] = "dungeon"
    cavern_feature_key: str | None = None
    terrain: TileTerrain = "indoor"


class DetachedGroupState(BaseModel):
    tile_id: str
    character_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class CapturedEquipmentState(BaseModel):
    inventory: list[str] = Field(default_factory=list)
    default_melee_weapon: str | None = None
    default_melee_weapon_secondary: str | None = None
    default_missile_weapon: str | None = None


class ActiveQuestState(BaseModel):
    tile_id: str
    key: str
    description: str
    gold_required: int = 0
    item_name: str | None = None
    item_collected: bool = False
    peaceful_required: int = 3
    peaceful_count: int = 0
    boss_slay_pending: bool = False
    boss_capture_pending: bool = False
    boss_target_name: str | None = None
    boss_head_acquired: bool = False
    captured_boss_name: str | None = None
    completed: bool = False
    reward_claimed: bool = False
    quest_id: str = Field(default_factory=lambda: uuid4().hex)
    fd_oracle_character_id: str | None = None
    fd_quest_servitor_type: str | None = None
    fd_quest_servitor_found: bool = False
    fd_quest_servitor_pending_room: bool = False
    fd_quest_enemy_kind: str | None = None
    fd_quest_enemy_defeated: bool = False
    fd_quest_enemy_spawned: bool = False
    fd_quest_areas_until_spawn: int = Field(default=0, ge=0)
    fd_quest_inventory_snapshot: dict[str, list[str]] = Field(default_factory=dict)
    fd_quest_pages_found: int = Field(default=0, ge=0)
    fd_quest_pages_required: int = Field(default=0, ge=0)
    fd_quest_items_required: int = Field(default=0, ge=0)
    fd_quest_items_turned_in: int = Field(default=0, ge=0)
    fd_quest_idol_visits: int = Field(default=0, ge=0)
    fd_quest_idol_visits_required: int = Field(default=0, ge=0)
    fd_quest_dark_pits_rooms: int = Field(default=0, ge=0)
    fd_quest_dark_pits_cleared: bool = False


class MapState(BaseModel):
    width: int = 31
    height: int = 31
    tiles: list[TileState] = Field(default_factory=list)
    current_tile_id: str


class PendingMadnessChoiceState(BaseModel):
    character_id: str
    source: str


class PendingBodyguardInterceptState(BaseModel):
    protectee_id: str
    hireling_id: str
    enemy_id: str


class PendingCombatFoeAttack(BaseModel):
    enemy_id: str
    target_character_id: str


class CombatBodyguardPauseState(BaseModel):
    phase_index: int
    phases: list[str]
    remaining_attacks: list[PendingCombatFoeAttack] = Field(default_factory=list)


class PendingAcolyteBlessingState(BaseModel):
    cleric_id: str
    hireling_id: str


class PendingFallenTransferState(BaseModel):
    from_character_id: str
    kind: Literal["clues", "secrets"]


class PendingMyceliumSnareState(BaseModel):
    tile_id: str
    character_id: str


class DealWithFoeEntry(BaseModel):
    tile_id: str
    foe_name: str


class PendingEchoSpellState(BaseModel):
    caster_id: str
    spell_name: str
    tile_id: str
    exit_id: str | None = None
    target_character_id: str | None = None
    target_foe_id: str | None = None
    secondary_foe_id: str | None = None
    spell_target_mode: str | None = None
    life_transfer_amount: int | None = None
    teleport_tile_id: str | None = None
    teleport_character_ids: list[str] | None = None


class PlayContextView(BaseModel):
    """Enriched, non-persisted view of environment + terrain for the active map element."""

    environment: Literal["dungeon", "caverns", "fungal_grottoes"] = "dungeon"
    terrain: TileTerrain = "indoor"
    outdoors: bool = False
    weather_active: bool = False
    forest_pathway_active: bool = False
    entangle_ok: bool = False
    forest_pathway_ok: bool = False
    alter_weather_ok: bool = False
    lightning_strike_ok: bool = False
    ranger_outdoor_missile_ok: bool = False


class SessionState(BaseModel):
    id: str
    party_id: str
    adventure_id: str
    adventure_type: Literal["random", "imported"]
    mode: Literal["exploration", "combat", "complete"] = "exploration"
    party: list[PartyMemberState]
    map_state: MapState
    log: list[str] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    saved_at: str | None = None
    save_label: str | None = None
    fountain_used: bool = False
    characters_who_lost_life: list[str] = Field(default_factory=list)
    wandering_healer_met: bool = False
    wandering_alchemist_met: bool = False
    blessed_undead_bonus_character_id: str | None = None
    cursed_character_id: str | None = None
    combat_round: int = 0
    missile_used_character_ids: list[str] = Field(default_factory=list)
    hunger_rounds: dict[str, int] = Field(default_factory=dict)
    next_wandering_roll_bonus: int = Field(default=0, ge=0)
    firearm_fired_this_encounter: bool = False
    firearm_broken: dict[str, bool] = Field(default_factory=dict)
    firearm_reload_turns: dict[str, int] = Field(default_factory=dict)
    crossbow_needs_reload: list[str] = Field(default_factory=list)
    pole_carrier_id: str | None = None
    spell_used_character_ids: list[str] = Field(default_factory=list)
    reaction_pending: bool = False
    reaction_checked: bool = False
    reaction_nudge_pending: bool = False
    reaction_pre_adjust_roll: int | None = Field(default=None, ge=1, le=6)
    reaction_key: str | None = None
    reaction_bribe_gold: int = 0
    reaction_bribe_weapons: int = 0
    reaction_bribe_gold_per_foe: int = 0
    reaction_bribe_weapons_per_foe: int = 0
    reaction_bribe_foe_count: int = 0
    reaction_trade_stock: list[str] = Field(default_factory=list)
    reaction_trade_active: bool = False
    reaction_no_fools_gold: bool = False
    reaction_sleep_attack_bonus: int = 0
    foes_strike_first: bool = False
    party_surprised: bool = False
    party_attacked_immediately: bool = False
    foe_flee_strike_pending: bool = False
    minor_encounters_defeated: int = 0
    clues_found: int = 0
    xp_rolls_pending: int = 0
    alchemist_potion_bought: list[str] = Field(default_factory=list)
    alchemist_poison_bought: list[str] = Field(default_factory=list)
    xp_system: Literal["classical", "slow_and_sure", "old_school", "slower_advancement"] = "classical"
    major_foes_encountered: int = 0
    final_boss_designated: bool = False
    final_boss_defeated: bool = False
    lady_in_white_refused: bool = False
    lady_in_gray_refused: bool = False
    active_quest: ActiveQuestState | None = None
    fd_secondary_quest: ActiveQuestState | None = None
    potion_used_character_ids: list[str] = Field(default_factory=list)
    bandage_used_character_ids: list[str] = Field(default_factory=list)
    map_fragment_used: bool = False
    torch_spent_this_combat: bool = False
    combat_lanterns_extinguished: bool = False
    spear_shield_readied: list[str] = Field(default_factory=list)
    monster_encounter_start_applied: bool = False
    gremlin_wm_protection_pending: bool = False
    miner_amulet_consumed: bool = False
    herbal_tonic_used_character_ids: list[str] = Field(default_factory=list)
    expended_spells: dict[str, list[str]] = Field(default_factory=dict)
    healing_prayer_uses: dict[str, int] = Field(default_factory=dict)
    old_school_xp_tally: int = 0
    slower_xp_bank: int = 0
    last_leveled_character_id: str | None = None
    level_up_spell_pending_character_id: str | None = None
    hirelings: list[HirelingState] = Field(default_factory=list)
    professional_services_used: int = Field(default=0, ge=0)
    professional_buffs: dict[str, object] = Field(default_factory=dict)
    alchemist_order: AlchemistOrderState | None = None
    camped_outside: bool = False
    current_tile_entry_exit_id: str | None = None
    summoned_beast_life: int = 0
    summoned_beast_owner_id: str | None = None
    druid_companion_life: int = 0
    druid_companion_max_life: int = 0
    druid_companion_level: int = 3
    druid_companion_kind: str | None = None
    druid_companion_owner_id: str | None = None
    bear_form_owner_id: str | None = None
    bear_form_start_life: int = 0
    bear_form_pre_life: int = 0
    subdual_penalty_ignored: bool = False
    illusionary_fog_active: bool = False
    alter_weather_active: bool = False
    forest_pathway_active: bool = False
    glamour_mask_character_id: str | None = None
    glamour_mask_reroll_available: bool = False
    illusionary_servant_active: bool = False
    illusionary_servant_owner_id: str | None = None
    wielded_melee_weapons: dict[str, str] = Field(default_factory=dict)
    body_carrier_id: str | None = None
    carried_body_id: str | None = None
    fallen_outside_character_ids: list[str] = Field(default_factory=list)
    permanently_lost_character_ids: list[str] = Field(default_factory=list)
    environment: Literal["dungeon", "caverns", "fungal_grottoes"] = "dungeon"
    ruleset: Literal["ee", "forsaken_depths"] = "ee"
    tile_catalog: Literal["ee", "forsaken_depths", "forsaken_depths_rivers"] = "ee"
    fd_river_type: Literal["oblivion", "tears", "death", "flame", "conjuration", "serpent"] | None = None
    fd_boat_status: Literal["ok", "damaged", "destroyed"] = "ok"
    fd_travel_mode: Literal["boat", "foot"] = "boat"
    fd_boatman_present: bool = False
    fd_boatman_kind: str | None = None
    fd_river_processed_tile_ids: list[str] = Field(default_factory=list)
    fd_boat_fireproof: bool = False
    fd_waste_of_time_skip_hazard_stretches: int = Field(default=0, ge=0)
    fd_conjuration_consulted_tile_ids: list[str] = Field(default_factory=list)
    fd_flame_stretch_count: int = Field(default=0, ge=0)
    fd_oblivion_madness_redemption_used: bool = False
    fd_oblivion_madness_redemption_pending: bool = False
    fd_hallucination_content_rolls: int = Field(default=0, ge=0)
    fd_hallucination_revelation_available: bool = False
    fd_revelation_negate_ambush: bool = False
    fd_revelation_auto_defend: bool = False
    fd_revelation_auto_save: bool = False
    fd_revelation_auto_search: bool = False
    fd_revelation_preview_explore: bool = False
    fd_flood_bow_penalty_rooms: int = Field(default=0, ge=0)
    fd_portal_tile_id: str | None = None
    courtship_demesne_active: bool = False
    courtship_demesne_region: (
        Literal["seaside", "riverside", "meadows", "woods", "mountain", "palace"] | None
    ) = None
    courtship_return_tile_id: str | None = None
    courtship_entry_source: Literal["standalone", "fd_portal", "flower_portal"] | None = None
    courtship_melancholy: dict[str, int] = Field(default_factory=dict)
    courtship_keywords: list[str] = Field(default_factory=list)
    courtship_pending_pathways: list[str] | None = None
    courtship_pending_choice: (
        Literal[
            "woo_or_fight",
            "occlith",
            "lady_of_lament",
            "seduce_or_fight",
            "disturbing_altar",
            "queens_vault",
            "lex_cambion",
            "lex_cambion_pick",
            "maze_lost",
            "matron_wooing",
            "matron_head_reward",
            "matron_head_deliver",
            "mistress_quest_ingredients",
            "bountiful_harvest",
            "shovel_substitute",
            "aetheric_conversion",
            "song_of_charm",
            "flower_portal_destination",
            "apothecary_brew",
        ]
        | None
    ) = None
    courtship_pending_choice_label: str | None = None
    courtship_apothecary_brew_locked: bool = False
    courtship_shovel_substitute_tier: Literal["common", "uncommon"] | None = None
    courtship_buried_stash_region: (
        Literal["seaside", "riverside", "meadows", "woods", "mountain", "palace"] | None
    ) = None
    courtship_buried_stash_items: list[str] = Field(default_factory=list)
    courtship_pavilion_rest_used: bool = False
    courtship_pathway_secret_trail: bool = False
    courtship_encounter_reroll_spent: bool = False
    courtship_uniques_seen: list[str] = Field(default_factory=list)
    courtship_enabled: bool = False
    courtship_woo_active: bool = False
    courtship_woo_template: str | None = None
    courtship_woo_category: str | None = None
    courtship_woo_giving_penalty: int = Field(default=0, ge=0)
    courtship_woo_withholding_penalty: int = Field(default=0, ge=0)
    courtship_woo_dominant_blocked: bool = False
    courtship_woo_dominant_stance: bool = False
    courtship_woo_passionate_stance: bool = False
    courtship_woo_successes: int = Field(default=0, ge=0)
    courtship_woo_speaker_id: str | None = None
    courtship_matron_pleasures_applied: list[str] = Field(default_factory=list)
    courtship_matron_head_quest_active: bool = False
    courtship_lady_keepsake_bonus: int = Field(default=0, ge=0)
    courtship_lex_picks_remaining: int = Field(default=0, ge=0)
    courtship_lex_picks_taken: list[str] = Field(default_factory=list)
    courtship_lex_granted_items: list[str] = Field(default_factory=list)
    courtship_lex_soul_taxed: list[str] = Field(default_factory=list)
    courtship_truelove_character_id: str | None = None
    courtship_lady_heart_broken: bool = False
    courtship_lady_doubles_active: bool = False
    courtship_damsel_penalty_pending: bool = False
    courtship_damsel_penalty_mode: Literal["life", "madness"] | None = None
    courtship_combat_entry: int | None = None
    courtship_disarmed_items: dict[str, list[str]] = Field(default_factory=dict)
    courtship_mirror_first_hit_pending: bool = False
    courtship_handmaiden_blur_active: bool = False
    courtship_handmaiden_blur_cancelled: bool = False
    courtship_matron_slain: bool = False
    courtship_matron_respawned: bool = False
    courtship_necrogaunt_hits: dict[str, int] = Field(default_factory=dict)
    courtship_necrogaunt_carried: list[str] = Field(default_factory=list)
    courtship_necrogaunt_rescue_active: bool = False
    courtship_necrogaunt_rescue_deadline_round: int | None = None
    courtship_vault_combat_no_flee: bool = False
    courtship_blossoms_scroll_pending: str | None = None
    courtship_libidinal_character_id: str | None = None
    courtship_libidinal_reroll_available: bool = False
    courtship_virile_might_character_id: str | None = None
    fd_idol_pending_choice: (
        Literal["secret_clue", "secret_search", "lady_in_black", "heroic_learn"] | None
    ) = None
    fd_idol_heroic_spell: str | None = None
    fd_idol_walking_flee_shift: bool = False
    fd_illusionary_distraction_active: bool = False
    fd_contact_forgotten_god_resurrected: list[str] = Field(default_factory=list)
    pending_fd_cairn_natural_one: dict[str, str] | None = None
    fd_magic_citadel_mr_active: bool = False
    fd_citadel_type: str | None = None
    fd_citadel_room_count: int | None = Field(default=None, ge=0)
    fd_citadel_entry_tile_id: str | None = None
    fd_side_sheet_active: bool = False
    fd_side_sheet_kind: Literal["citadel", "ruins", "dark_pits"] | None = None
    fd_side_sheet_origin_tile_id: str | None = None
    fd_side_sheet_rooms_total: int = Field(default=0, ge=0)
    fd_side_sheet_rooms_entered: int = Field(default=0, ge=0)
    fd_side_sheet_visited_tile_ids: list[str] = Field(default_factory=list)
    fd_secret_passage_tile_id: str | None = None
    fd_secret_passage_traps_cleared: int = Field(default=0, ge=0)
    fd_secret_passage_weird_defeated: int = Field(default=0, ge=0)
    fd_secret_passage_unlocked: bool = False
    fd_stirs_in_darkness_remaining: int = Field(default=0, ge=0)
    fd_stirs_processed_tile_ids: list[str] = Field(default_factory=list)
    fd_silk_treasure_used: bool = False
    fd_forgotten_spells: dict[str, list[str]] = Field(default_factory=dict)
    fiendish_foes_enabled: bool = True
    map_bounds_mode: Literal["unlimited", "paper"] = "unlimited"
    unlimited_map_element_cap: int = Field(default=60, ge=1, le=999)
    rest_used: bool = False
    rest_available: bool = False
    rest_block_reason: str = ""
    party_editable: bool = False
    rage_uses_spent: dict[str, int] = Field(default_factory=dict)
    luck_points_spent: dict[str, int] = Field(default_factory=dict)
    panache_points: dict[str, int] = Field(default_factory=dict)
    paladin_prayer_spent: dict[str, int] = Field(default_factory=dict)
    nourishing_meal_used: bool = False
    pending_save_reroll: dict[str, str | int] | None = None
    acrobat_tricks_spent: dict[str, int] = Field(default_factory=dict)
    gnome_gadgets_spent: dict[str, int] = Field(default_factory=dict)
    mushroom_spore_uses: dict[str, int] = Field(default_factory=dict)
    foe_level_penalties: dict[str, int] = Field(default_factory=dict)
    assassin_hidden_id: str | None = None
    assassin_mark_enemy_id: str | None = None
    gnome_smokescreen_ready: bool = False
    skip_parting_flee: bool = False
    puffball_flee: bool = False
    acrobat_skip_attack: dict[str, bool] = Field(default_factory=dict)
    prisoner_chain_skip_attack: dict[str, bool] = Field(default_factory=dict)
    rescued_prisoner_active: bool = False
    rescued_prisoner_holder_id: str | None = None
    prisoner_reward_choice: Literal["magic", "gold"] | None = None
    gladiator_counter_pending: dict[str, dict[str, str | int]] = Field(default_factory=dict)
    gladiator_counter_used: list[str] = Field(default_factory=list)
    swashbuckler_flourishing_used: list[str] = Field(default_factory=list)
    swashbuckler_riposte_used: list[str] = Field(default_factory=list)
    swashbuckler_taunt_used: list[str] = Field(default_factory=list)
    swashbuckler_lucky_hat_used: list[str] = Field(default_factory=list)
    swashbuckler_daring_escape_used: list[str] = Field(default_factory=list)
    swashbuckler_blade_dance_used: list[str] = Field(default_factory=list)
    swashbuckler_blade_dance_bonus: dict[str, int] = Field(default_factory=dict)
    swashbuckler_blade_dance_attack_spent: list[str] = Field(default_factory=list)
    swashbuckler_daring_escape_bonus: dict[str, dict[str, str | int]] = Field(default_factory=dict)
    foe_taunt_pending: dict[str, int] = Field(default_factory=dict)
    foe_taunt_active: dict[str, int] = Field(default_factory=dict)
    pending_defense_reroll: dict[str, str | int] | None = None
    pending_defense_reroll_blocked_damage: dict[str, str] | None = None
    evasion_character_ids: list[str] = Field(default_factory=list)
    expert_encounter_spent: dict[str, list[str]] = Field(default_factory=dict)
    expert_protective_incense_target: str | None = None
    phasing_panther_escape_used: list[str] = Field(default_factory=list)
    expert_spore_doses: dict[str, int] = Field(default_factory=dict)
    expert_knife_thrown: dict[str, str] = Field(default_factory=dict)
    expert_acute_hearing_tiles: list[str] = Field(default_factory=list)
    pending_treasure_reroll_tile_id: str | None = None
    pending_hidden_complication_reroll_tile_id: str | None = None
    pending_search_reroll_tile_id: str | None = None
    pending_pole_search_reroll_tile_id: str | None = None
    pending_search_reward_tile_id: str | None = None
    divine_smite_used: list[str] = Field(default_factory=list)
    army_of_dolls_deployed: list[str] = Field(default_factory=list)
    sacrifice_shield_used: list[str] = Field(default_factory=list)
    hyphae_used: list[str] = Field(default_factory=list)
    kukla_doll_active: list[str] = Field(default_factory=list)
    graceful_save_reroll_id: str | None = None
    hyphae_search_bonus_id: str | None = None
    paladin_steed_active_id: str | None = None
    continual_light_owner_id: str | None = None
    heroes_rest_used: bool = False
    forfeited_shields: dict[str, str] = Field(default_factory=dict)
    heroic_courage_used: list[str] = Field(default_factory=list)
    legendary_courage_used: list[str] = Field(default_factory=list)
    training_focus_bonus: dict[str, int] = Field(default_factory=dict)
    aggressive_stance_penalty: list[str] = Field(default_factory=list)
    heroic_carnage_bonus: dict[str, int] = Field(default_factory=dict)
    detached_groups: list[DetachedGroupState] = Field(default_factory=list)
    detached_wandering_pending: list[str] = Field(default_factory=list)
    detached_combat_rounds: dict[str, int] = Field(default_factory=dict)
    detached_missile_used_character_ids: dict[str, list[str]] = Field(default_factory=dict)
    druid_call_of_wild_turns: dict[str, int] = Field(default_factory=dict)
    druid_call_of_wild_used: list[str] = Field(default_factory=list)
    scout_encounter_origin_tile_ids: dict[str, str] = Field(default_factory=dict)
    scout_reaction_checked_tile_ids: list[str] = Field(default_factory=list)
    scout_lag_character_id: str | None = None
    heros_banquet_used: bool = False
    song_of_elidra_used: bool = False
    mass_blessing_used: bool = False
    mass_blessing_active_round: int = -1
    protected_by_fate_used: list[str] = Field(default_factory=list)
    yogic_preservation_used: list[str] = Field(default_factory=list)
    restore_mental_capacity_used: bool = False
    copy_grimoire_used: list[str] = Field(default_factory=list)
    visited_tile_ids: list[str] = Field(default_factory=list)
    ward_of_protection_targets: dict[str, str] = Field(default_factory=dict)
    secret_weakness_foe_id: str | None = None
    secret_weakness_character_id: str | None = None
    secret_enemy_foe_id: str | None = None
    secret_enemy_character_id: str | None = None
    terrifying_secret_pending_character_id: str | None = None
    secret_diet_character_ids: list[str] = Field(default_factory=list)
    secret_temporary_spells: dict[str, list[str]] = Field(default_factory=dict)
    secret_chaos_fanatics_active: bool = False
    secret_yummy_meal_active: bool = False
    deal_with_foe_entries: list[DealWithFoeEntry] = Field(default_factory=list)
    major_foes_defeated_this_adventure: int = 0
    capture_mode: bool = False
    captured_character_ids: list[str] = Field(default_factory=list)
    captured_stripped_equipment: dict[str, CapturedEquipmentState] = Field(default_factory=dict)
    capture_foe_name: str | None = None
    capture_origin_tile_id: str | None = None
    capture_hideout_tile_id: str | None = None
    capture_hideout_reaction_checked: bool = False
    capture_hideout_reaction_key: str | None = None
    active_group_tile_id: str | None = None
    caverns_morlock_warning: bool = False
    caverns_scout_warning: bool = False
    fungal_scout_warning: bool = False
    mycelial_warning_ready: bool = False
    fungal_merchant_met: bool = False
    pending_secret_passage_tile_id: str | None = None
    pending_secret_passage_hidden_pit: bool = False
    pending_tile_content_choice_tile_id: str | None = None
    pending_echo_spell: PendingEchoSpellState | None = None
    pending_madness_choice: PendingMadnessChoiceState | None = None
    pending_bodyguard_intercept: PendingBodyguardInterceptState | None = None
    combat_bodyguard_pause: CombatBodyguardPauseState | None = None
    pending_acolyte_blessing: PendingAcolyteBlessingState | None = None
    pending_fallen_transfer: PendingFallenTransferState | None = None
    pending_mycelium_snare: PendingMyceliumSnareState | None = None
    pending_free_slaves_tile_id: str | None = None
    pending_end_of_combat_poison: list[tuple[str, int, str]] = Field(default_factory=list)
    madness_exit_healed: bool = False
    strong_will_madness_ignored: list[str] = Field(default_factory=list)
    alchemist_event_tile_ids: list[str] = Field(default_factory=list)
    cavern_water_pool_healed_character_ids: list[str] = Field(default_factory=list)
    cavern_contaminated_character_ids: list[str] = Field(default_factory=list)
    dwarf_miner_gems_available: int = Field(default=0, ge=0)
    dwarf_miner_trade_preview_done: bool = False
    imported_entrance_pending: bool = False
    imported_fired_triggers: list[str] = Field(default_factory=list)
    imported_exit_tile_id: str | None = None
    imported_manifest: dict | None = None
    imported_quest_complete_when: dict | None = None
    play_context: PlayContextView | None = Field(default=None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fiendish_foes(cls, data):
        if isinstance(data, dict) and "fiendish_foes_enabled" not in data:
            legacy = data.get("fiendish_foes_mode")
            if legacy is not None:
                data["fiendish_foes_enabled"] = legacy in {"always", "mixed"}
            else:
                data["fiendish_foes_enabled"] = True
        return data


class SessionListSummary(BaseModel):
    """Lightweight session row for Home active/saved game lists."""

    id: str
    party_id: str
    adventure_id: str
    adventure_type: Literal["random", "imported"]
    mode: Literal["exploration", "combat", "complete"] = "exploration"
    camped_outside: bool = False
    save_label: str | None = None
    saved_at: str | None = None
    updated_at: str
    created_at: str
    tile_count: int = Field(default=0, ge=0)
    imported_title: str | None = None
    imported_room_count: int | None = Field(default=None, ge=0)
    active_quest_description: str | None = None


class SessionAction(BaseModel):
    action: Literal[
        "explore",
        "return_to_dungeon",
        "search",
        "look",
        "combat_round",
        "start_combat",
        "turn_back_from_mantlebeast",
        "check_reaction",
        "pay_bribe",
        "pay_bribe_fools_gold",
        "trade_information",
        "reaction_choice",
        "cast_spell",
        "burn_scroll",
        "use_magic_item",
        "spellcast_door",
        "spend_clues_on_door",
        "reveal_secret_with_clues",
        "learn_spell_with_clues",
        "use_secret",
        "pass_using_deal",
        "break_prisoner_chains",
        "choose_prisoner_reward",
        "copy_scroll",
        "flee",
        "withdraw",
        "rest",
        "open_door",
        "listen_at_door",
        "resolve_trap",
        "resolve_special_feature",
        "resolve_environment_event",
        "claim_treasure",
        "set_marching_order",
        "xp_roll",
        "bank_xp_roll",
        "spend_banked_xp",
        "buy_healing",
        "buy_alchemist",
        "use_potion",
        "use_holy_water",
        "use_lantern_oil",
        "use_mushroom",
        "eat_food_ration",
        "feed_hungry_heroes",
        "use_acid_vial",
        "use_arrow_of_slaying",
        "use_bandage",
        "accept_quest",
        "refuse_quest",
        "claim_quest_reward",
        "claim_kerrak_dar_hoard",
        "old_school_level_up",
        "pick_level_up_spell",
        "slower_xp_spend",
        "enter_tier_training",
        "transfer_item",
        "transfer_gold",
        "deposit_bank_gold",
        "withdraw_bank_gold",
        "deposit_party_bank_gold",
        "set_default_weapon",
        "swap_weapon",
        "carry_body",
        "drop_body",
        "attempt_resurrection",
        "accept_fallen_loss",
        "use_class_ability",
        "detach_heroes",
        "reattach_heroes",
        "scout_ahead",
        "detached_combat_round",
        "scout_reaction",
        "rush_to_scout",
        "scout_flee_back",
        "set_active_group",
        "call_of_the_wild",
        "bank_training_focus",
        "find_captive_hideout",
        "pay_captive_ransom",
        "use_hidden_pit_clue",
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
        "use_map_fragment",
        "use_enchanted_paint",
        "use_wolfsbane",
        "use_berserkers_mushroom",
        "spend_torch",
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
        "enter_fd_side_sheet",
        "exit_fd_side_sheet",
        "assign_milestone",
        "bind_scroll_librarian",
        "craft_gem_collector_jewelry",
        "create_panoplia",
        "use_panoplia_favor",
        "pay_thrice_blessed_sacrifice",
        "hire_retainer",
        "dismiss_hireling",
        "assign_hireling",
        "set_hireling_marching_order",
        "pay_hireling_treasure_share",
        "resurrect_hireling",
        "use_professional_service",
        "commission_alchemist",
        "use_hireling_ability",
        "apply_silversmith_coating",
        "apply_poison_expert_coating",
        "use_fortune_reroll",
        "ready_spear_shield",
        "surgeon_burn_scroll",
        "use_blossoms_item",
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
    ]
    exit_id: str | None = None
    dungeon_exit_intent: Literal["complete", "return"] | None = None
    direction: ExitDirection | None = None
    character_id: str | None = None
    target_character_id: str | None = None
    item_name: str | None = None
    target_weapon: str | None = None
    gold_amount: int | None = Field(default=None, ge=1)
    marching_order: int | None = Field(default=None, ge=1, le=6)
    show_rolls: bool = True
    explain_math: bool = False
    search_choice: Literal["hidden_treasure", "secret_door", "secret_passage", "clue"] | None = None
    special_feature_choice: Literal[
        "touch_statue",
        "leave_statue",
        "attempt_puzzle_box",
        "leave_puzzle_box",
        "bless_temple",
    ] | None = None
    tile_content_choice: Literal["searchable", "secret_passage_2_clues"] | None = None
    secret_passage_environment: Literal["dungeon", "caverns", "fungal_grottoes"] | None = None
    environment_event_choice: Literal[
        "feed",
        "feed_mushroom",
        "fight",
        "pay",
        "decline",
        "claim",
        "buy_gem",
        "buy_equipment",
        "sell_gems",
        "sell_mushrooms",
        "take_warning",
    ] | None = None
    madness_choice: Literal["damage", "madness"] | None = None
    bodyguard_intercept_choice: Literal["intercept", "decline"] | None = None
    acolyte_blessing_choice: Literal["try", "skip"] | None = None
    envenom_weapon_kind: Literal["melee", "missile"] | None = None
    fallen_transfer_kind: Literal["clues", "secrets"] | None = None
    free_slaves_choice: Literal["free", "decline"] | None = None
    paint_choice: Literal["food_rations", "shop_item", "paint_door"] | None = None
    paint_direction: Literal["north", "south", "east", "west"] | None = None
    paint_quantity: int | None = Field(default=None, ge=1, le=8)
    paint_item_key: str | None = None
    use_prayer_bead: bool = False
    wand_power_charges: int | None = Field(default=None, ge=1, le=6)
    fd_revelation_choice: (
        Literal["negate_ambush", "auto_defend", "auto_save", "auto_search", "preview_room"] | None
    ) = None
    fd_secret_passage_destination: Literal["abyss", "netherworld", "citadel"] | None = None
    fd_portal_destination: Literal["abyss", "netherworld", "demesne"] | None = None
    courtship_region: Literal["seaside", "riverside", "meadows", "woods", "mountain", "palace"] | None = None
    courtship_encounter_shift: Literal["reroll", "up", "down"] | None = None
    courtship_choice: str | None = None
    courtship_dominant_stance: bool | None = None
    courtship_passionate_stance: bool | None = None
    courtship_damsel_penalty: Literal["life", "madness"] | None = None
    fd_idol_choice: (
        Literal["secret_clue", "secret_search", "lady_sacrifice", "lady_quest_roll", "heroic_learn"] | None
    ) = None
    fd_cairn_natural_one_choice: Literal["life", "spell"] | None = None
    fd_quest_reward_choice: Literal["xp_all", "heroic_item"] | None = None
    fd_quest_from_treasure: bool = False
    fd_quest_id: str | None = None
    treasure_outcome_choice: (
        Literal[
            "gem",
            "prism",
            "food_rations",
            "rare_mushroom",
            "dungeon_magic",
            "scroll",
            "weapon",
            "light_weapon",
            "hand_weapon",
            "two_handed_weapon",
            "bow",
            "crossbow",
            "sling",
            "leafsteel",
            "heavy_armor",
            "lantern",
            "blessing_scroll",
            "random_scroll",
            "chicken_blood",
            "red_death_damage",
            "red_death_level",
        ]
        | None
    ) = None
    secret_id: str | None = None
    spell_name: str | None = None
    pay_bribe: bool = False
    trade_information_choice: Literal["sell", "buy", "decline"] | None = None
    reaction_choice: Literal["accept", "decline", "done"] | None = None
    reaction_bribe_mode: Literal["food", "gold", "mushroom", "all_gold"] | None = None
    subdual: bool = False
    alchemist_item: Literal["potion", "poison"] | None = None
    xp_spent: int | None = Field(default=None, ge=1)
    weapon_kind: Literal["melee", "missile"] | None = None
    attack_targets: dict[str, str] | None = None
    attack_secondary_targets: dict[str, str] | None = None
    double_kick_targets: dict[str, list[str]] | None = None
    protective_incense_targets: dict[str, str] | None = None
    nail_doors: bool = False
    rest_choices: dict[str, Literal["life", "ability"]] | None = None
    combat_abilities: dict[str, Literal["rage", "panache_attack", "panache_defense", "luck_attack", "luck_defense", "gnome_gadget", "flip_kick", "gladiator_parry", "bulwark_sacrifice", "sacrifice_shield", "double_kick", "deadly_strike", "dead_shot", "double_attack", "double_shot", "protective_incense", "whirlwind_of_steel", "knife_throwing", "continual_light", "divine_smite", "mass_blessing", "restore", "ward_of_protection", "acrobat_knife_throw", "illusionist_knife_throw", "illusionist_continual_light", "flourishing_strike", "riposte"]] | None = None
    panache_spend: int | None = Field(default=None, ge=1, le=12)
    use_daring_escape: bool = False
    guard_targets: dict[str, str] | None = None
    gadget_points: int | None = Field(default=None, ge=1, le=12)
    use_luck_flee: bool = False
    class_ability: (
        Literal[
            "paladin_heal",
            "paladin_reroll_save",
            "paladin_summon_steed",
            "halfling_reroll_save",
            "acrobat_shift_position",
            "acrobat_distract",
            "acrobat_leap_harm",
            "acrobat_serpent_twist",
            "acrobat_evade",
            "gnome_smokescreen",
            "gnome_gadget_trap",
            "gnome_gadget_door",
            "gnome_gadget_free",
            "halfling_luck_treasure",
            "halfling_luck_search",
            "halfling_luck_hidden_complication",
            "mushroom_spore_cloud",
            "assassin_hide",
            "illusionist_distract",
            "illusionist_continual_light",
            "turn_undead",
            "combat_acrobatics",
            "continual_light",
            "lesser_necromancy",
            "throw_spore",
            "acrobat_graceful_move",
            "mushroom_hyphae",
            "kukla_army_of_dolls",
            "kukla_green_ring_revive",
            "kukla_red_ring_poison",
            "kukla_compartment_stash",
            "kukla_compartment_retrieve",
            "restore_mental_capacity",
            "swashbuckler_taunt",
            "lucky_hat",
            "blade_dance",
        ]
        | None
    ) = None
    foe_id: str | None = None
    secondary_foe_id: str | None = None
    spell_target_mode: Literal["minions", "single"] | None = None
    nourishing_meal: bool = False
    nourishing_meal_eaters: list[str] | None = None
    everyone_eats: bool = False
    feed_character_ids: list[str] | None = None
    tier_training: Literal["expert", "heroic", "legendary"] | None = None
    use_xp_for_tier: bool = False
    advancement_fork: (
        Literal["level_up", "learn_expert_skill", "learn_heroic_skill", "learn_legendary_skill"] | None
    ) = None
    expert_skill_id: str | None = None
    expert_skill_target: str | None = None
    heroic_skill_id: str | None = None
    legendary_skill_id: str | None = None
    heroic_skill_target: str | None = None
    reaction_adjust: int | None = Field(default=None, ge=-1, le=1)
    glamour_mask_reroll: bool = False
    life_transfer_amount: int | None = Field(default=None, ge=1)
    teleport_tile_id: str | None = None
    teleport_character_ids: list[str] | None = None
    save_label: str | None = Field(default=None, max_length=80)
    detached_character_ids: list[str] | None = None
    detached_tile_id: str | None = None
    trap_boulder_origin: Literal["front", "back"] | None = None
    trap_boulder_block_exit_id: str | None = None
    trap_snare_item_name: str | None = Field(default=None, max_length=120)
    milestone_id: str | None = None
    scroll_librarian_spell: str | None = None
    panoplia_favor_kind: Literal["gold", "fine", "jail", "resurrection"] | None = None
    hireling_id: str | None = None
    retainer_type: str | None = None
    professional_id: str | None = None
    hireling_marching_order: int | None = Field(default=None, ge=5, le=6)
    hireling_ability: (
        Literal[
            "minstrel_song",
            "surgeon_heal",
            "guide_reroll_room",
            "guide_reroll_search",
            "guide_reroll_wandering",
            "porter_load_gold",
            "porter_load_item",
            "spear_hand_gear",
            "spear_return_gear",
        ]
        | None
    ) = None
    fortune_roll_value: int | None = Field(default=None, ge=1, le=8)
    alchemist_potion_id: str | None = None


class SaveSessionRequest(BaseModel):
    label: str | None = Field(default=None, max_length=80)


class AdventureDescriptor(BaseModel):
    id: str
    name: str
    source: str
    playable: bool
    notes: str
    removable: bool = False


class AdventurePromptParameters(BaseModel):
    theme: str = Field(min_length=1, max_length=120)
    difficulty: Literal["easy", "standard", "hard"] = "standard"
    length: Literal["short", "medium", "long"] = "medium"
    style: str = Field(default="grim", min_length=1, max_length=80)
    environment: Literal["dungeon", "caverns", "fungal_grottoes"] = "dungeon"
    boss_type: str = Field(min_length=1, max_length=80)
    party_level_min: int = Field(default=1, ge=1, le=20)
    party_level_max: int = Field(default=3, ge=1, le=20)


class AdventurePromptResponse(BaseModel):
    prompt: str
    parameters: AdventurePromptParameters
    room_count_hint: str


class AdventureSkeletonResponse(BaseModel):
    skeleton: dict
    valid: bool
    errors: list[str] = Field(default_factory=list)
