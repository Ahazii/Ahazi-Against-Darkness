from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


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


class TileExitDefinition(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    label: str = Field(default="", max_length=80)
    direction: Literal["north", "east", "south", "west"]
    kind: Literal["passage", "door"]
    x: int = Field(default=0, ge=0, le=99)
    y: int = Field(default=0, ge=0, le=99)
    span: int = Field(default=1, ge=1, le=20)
    offset: int = Field(default=0, ge=0, le=99)
    position: float = Field(default=0.5, ge=0.0, le=1.0)
    dungeon_exit: bool = False


TileTerrain = Literal["indoor", "outdoor", "forest", "swamp", "jungle"]


class TileDefinition(BaseModel):
    key: str = Field(pattern=r"^\d{2}$")
    name: str
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


class CharacterSellItem(BaseModel):
    item_name: str = Field(min_length=1)


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
    max_life: int
    current_life: int
    attack_bonus: int = 0
    defense_bonus: int = 0
    save_bonus: int = 0
    inventory: list[str] = Field(default_factory=list)
    spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    learned_expert_skills: list[str] = Field(default_factory=list)
    learned_heroic_skills: list[str] = Field(default_factory=list)
    learned_legendary_skills: list[str] = Field(default_factory=list)
    expert_skill_targets: dict[str, str] = Field(default_factory=dict)
    statuses: list[str] = Field(default_factory=list)
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
    created_at: str
    updated_at: str


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
    current_life: int
    max_life: int
    attack_bonus: int
    defense_bonus: int
    save_bonus: int
    marching_order: int = Field(default=1, ge=1, le=4)
    inventory: list[str] = Field(default_factory=list)
    spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    learned_expert_skills: list[str] = Field(default_factory=list)
    learned_heroic_skills: list[str] = Field(default_factory=list)
    learned_legendary_skills: list[str] = Field(default_factory=list)
    expert_skill_targets: dict[str, str] = Field(default_factory=dict)
    expert_trained: bool = False
    heroic_trained: bool = False
    legendary_trained: bool = False
    epic_trained: bool = False
    statuses: list[str] = Field(default_factory=list)
    default_melee_weapon: str | None = None
    default_melee_weapon_secondary: str | None = None
    default_missile_weapon: str | None = None
    starting_weapon_slots: int | None = None
    starting_shields: int | None = None
    companion_kind: str | None = None
    kukla_compartment_items: list[str] = Field(default_factory=list)
    kukla_compartment_gold: int = Field(default=0, ge=0, le=100)


class ExitState(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    label: str = Field(default="", max_length=80)
    direction: Literal["north", "east", "south", "west"]
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
    objects: list[str] = Field(default_factory=list)
    enemies: list[EnemyState] = Field(default_factory=list)
    defeated_enemies: list[EnemyState] = Field(default_factory=list)
    fallen_character_ids: list[str] = Field(default_factory=list)
    exits: list[ExitState] = Field(default_factory=list)
    searched: bool = False
    resolved: bool = False
    trap_key: str | None = None
    trap_level: int | None = None
    trap_resolved: bool = False
    treasure_summary: str | None = None
    treasure_gold: int = 0
    treasure_items: list[str] = Field(default_factory=list)
    treasure_claimed: bool = False
    initial_enemy_count: int = 0
    treasure_doubled: bool = False
    wandering_ambush: bool = False
    surprise_party: bool = False
    hidden_treasure_alarm_pending: bool = False
    healer_available: bool = False
    alchemist_available: bool = False
    lady_in_white_available: bool = False
    final_boss_treasure: bool = False
    environment: Literal["dungeon", "caverns", "fungal_grottoes"] = "dungeon"
    terrain: TileTerrain = "indoor"


class DetachedGroupState(BaseModel):
    tile_id: str
    character_ids: list[str] = Field(default_factory=list)
    reason: str = ""


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
    captured_boss_name: str | None = None
    completed: bool = False
    reward_claimed: bool = False


class MapState(BaseModel):
    width: int = 31
    height: int = 31
    tiles: list[TileState] = Field(default_factory=list)
    current_tile_id: str


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
    wandering_healer_met: bool = False
    wandering_alchemist_met: bool = False
    blessed_undead_bonus_character_id: str | None = None
    cursed_character_id: str | None = None
    combat_round: int = 0
    missile_used_character_ids: list[str] = Field(default_factory=list)
    spell_used_character_ids: list[str] = Field(default_factory=list)
    reaction_pending: bool = False
    reaction_checked: bool = False
    reaction_key: str | None = None
    reaction_bribe_gold: int = 0
    reaction_bribe_weapons: int = 0
    reaction_bribe_gold_per_foe: int = 0
    reaction_bribe_weapons_per_foe: int = 0
    reaction_bribe_foe_count: int = 0
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
    active_quest: ActiveQuestState | None = None
    potion_used_character_ids: list[str] = Field(default_factory=list)
    bandage_used_character_ids: list[str] = Field(default_factory=list)
    expended_spells: dict[str, list[str]] = Field(default_factory=dict)
    healing_prayer_uses: dict[str, int] = Field(default_factory=dict)
    old_school_xp_tally: int = 0
    slower_xp_bank: int = 0
    last_leveled_character_id: str | None = None
    level_up_spell_pending_character_id: str | None = None
    camped_outside: bool = False
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
    illusionary_servant_active: bool = False
    illusionary_servant_owner_id: str | None = None
    wielded_melee_weapons: dict[str, str] = Field(default_factory=dict)
    body_carrier_id: str | None = None
    carried_body_id: str | None = None
    fallen_outside_character_ids: list[str] = Field(default_factory=list)
    permanently_lost_character_ids: list[str] = Field(default_factory=list)
    environment: Literal["dungeon", "caverns", "fungal_grottoes"] = "dungeon"
    map_bounds_mode: Literal["unlimited", "paper"] = "unlimited"
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
    acrobat_skip_attack: dict[str, bool] = Field(default_factory=dict)
    gladiator_counter_pending: dict[str, dict[str, str | int]] = Field(default_factory=dict)
    gladiator_counter_used: list[str] = Field(default_factory=list)
    evasion_character_ids: list[str] = Field(default_factory=list)
    expert_encounter_spent: dict[str, list[str]] = Field(default_factory=dict)
    expert_protective_incense_target: str | None = None
    expert_spore_doses: dict[str, int] = Field(default_factory=dict)
    expert_knife_thrown: dict[str, str] = Field(default_factory=dict)
    expert_acute_hearing_tiles: list[str] = Field(default_factory=list)
    pending_treasure_reroll_tile_id: str | None = None
    pending_search_reroll_tile_id: str | None = None
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


class SessionAction(BaseModel):
    action: Literal[
        "explore",
        "search",
        "combat_round",
        "start_combat",
        "check_reaction",
        "pay_bribe",
        "trade_information",
        "cast_spell",
        "burn_scroll",
        "use_magic_item",
        "spellcast_door",
        "spend_clues_on_door",
        "reveal_secret_with_clues",
        "learn_spell_with_clues",
        "copy_scroll",
        "flee",
        "withdraw",
        "rest",
        "open_door",
        "listen_at_door",
        "resolve_trap",
        "claim_treasure",
        "set_marching_order",
        "xp_roll",
        "buy_healing",
        "buy_alchemist",
        "use_potion",
        "use_holy_water",
        "use_lantern_oil",
        "use_mushroom",
        "use_acid_vial",
        "use_bandage",
        "accept_quest",
        "refuse_quest",
        "claim_quest_reward",
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
        "bank_training_focus",
    ]
    exit_id: str | None = None
    direction: Literal["north", "east", "south", "west"] | None = None
    character_id: str | None = None
    target_character_id: str | None = None
    item_name: str | None = None
    gold_amount: int | None = Field(default=None, ge=1)
    marching_order: int | None = Field(default=None, ge=1, le=4)
    show_rolls: bool = True
    explain_math: bool = False
    search_choice: Literal["hidden_treasure", "secret_door", "secret_passage", "clue"] | None = None
    spell_name: str | None = None
    pay_bribe: bool = False
    trade_information_choice: Literal["sell", "buy", "decline"] | None = None
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
    combat_abilities: dict[str, Literal["rage", "panache_attack", "panache_defense", "luck_attack", "luck_defense", "gnome_gadget", "flip_kick", "gladiator_parry", "bulwark_sacrifice", "sacrifice_shield", "double_kick", "deadly_strike", "double_attack", "double_shot", "protective_incense", "whirlwind_of_steel", "knife_throwing", "continual_light", "divine_smite", "mass_blessing", "restore", "ward_of_protection", "acrobat_knife_throw", "illusionist_knife_throw", "illusionist_continual_light"]] | None = None
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
        ]
        | None
    ) = None
    foe_id: str | None = None
    secondary_foe_id: str | None = None
    spell_target_mode: Literal["minions", "single"] | None = None
    nourishing_meal: bool = False
    nourishing_meal_eaters: list[str] | None = None
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
    life_transfer_amount: int | None = Field(default=None, ge=1)
    teleport_tile_id: str | None = None
    teleport_character_ids: list[str] | None = None
    save_label: str | None = Field(default=None, max_length=80)
    detached_character_ids: list[str] | None = None


class SaveSessionRequest(BaseModel):
    label: str | None = Field(default=None, max_length=80)


class AdventureDescriptor(BaseModel):
    id: str
    name: str
    source: str
    playable: bool
    notes: str
