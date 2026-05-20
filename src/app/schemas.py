from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class CharacterClass(BaseModel):
    id: str
    name: str
    base_life: int
    attack_bonus: int = 0
    defense_bonus: int = 0
    save_bonus: int = 0
    starting_gold: int = 0
    starting_inventory: list[str] = Field(default_factory=list)
    starting_spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    implementation_status: str = "starter"


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


class TileDefinition(BaseModel):
    key: str = Field(pattern=r"^\d{2}$")
    name: str
    tile_type: Literal["room", "corridor", "unknown"] = "unknown"
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
    category: Literal["map", "character", "monster", "item", "condition", "ui"] = "map"
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


class Character(BaseModel):
    id: str
    name: str
    class_id: str
    class_name: str
    level: int = 1
    xp: int = 0
    gold: int = 0
    max_life: int
    current_life: int
    attack_bonus: int = 0
    defense_bonus: int = 0
    save_bonus: int = 0
    inventory: list[str] = Field(default_factory=list)
    spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    default_melee_weapon: str | None = None
    default_missile_weapon: str | None = None
    created_at: str
    updated_at: str


class CharacterTransferResult(BaseModel):
    message: str
    source: Character
    target: Character


class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
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


class PartyMemberState(BaseModel):
    character_id: str
    name: str
    class_id: str
    class_name: str
    level: int
    xp: int
    gold: int
    current_life: int
    max_life: int
    attack_bonus: int
    defense_bonus: int
    save_bonus: int
    marching_order: int = Field(default=1, ge=1, le=4)
    inventory: list[str] = Field(default_factory=list)
    spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    default_melee_weapon: str | None = None
    default_missile_weapon: str | None = None


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
    hidden_treasure_alarm_pending: bool = False
    healer_available: bool = False
    alchemist_available: bool = False
    lady_in_white_available: bool = False
    final_boss_treasure: bool = False


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
    fountain_used: bool = False
    wandering_healer_met: bool = False
    wandering_alchemist_met: bool = False
    blessed_undead_bonus_character_id: str | None = None
    cursed_character_id: str | None = None
    combat_round: int = 0
    missile_used_character_ids: list[str] = Field(default_factory=list)
    reaction_pending: bool = False
    reaction_checked: bool = False
    reaction_key: str | None = None
    reaction_bribe_gold: int = 0
    reaction_bribe_weapons: int = 0
    reaction_bribe_gold_per_foe: int = 0
    reaction_bribe_weapons_per_foe: int = 0
    reaction_bribe_foe_count: int = 0
    foes_strike_first: bool = False
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
    expended_spells: dict[str, list[str]] = Field(default_factory=dict)
    healing_prayer_uses: dict[str, int] = Field(default_factory=dict)
    old_school_xp_tally: int = 0
    slower_xp_bank: int = 0
    last_leveled_character_id: str | None = None
    level_up_spell_pending_character_id: str | None = None
    camped_outside: bool = False
    summoned_beast_life: int = 0
    summoned_beast_owner_id: str | None = None
    subdual_penalty_ignored: bool = False
    illusionary_fog_active: bool = False
    wielded_melee_weapons: dict[str, str] = Field(default_factory=dict)


class SessionAction(BaseModel):
    action: Literal[
        "explore",
        "search",
        "combat_round",
        "check_reaction",
        "pay_bribe",
        "cast_spell",
        "burn_scroll",
        "spellcast_door",
        "spend_clues_on_door",
        "copy_scroll",
        "flee",
        "withdraw",
        "rest",
        "open_door",
        "resolve_trap",
        "claim_treasure",
        "set_marching_order",
        "xp_roll",
        "buy_healing",
        "buy_alchemist",
        "use_potion",
        "accept_quest",
        "refuse_quest",
        "claim_quest_reward",
        "old_school_level_up",
        "pick_level_up_spell",
        "slower_xp_spend",
        "transfer_item",
        "transfer_gold",
        "set_default_weapon",
        "swap_weapon",
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
    subdual: bool = False
    alchemist_item: Literal["potion", "poison"] | None = None
    xp_spent: int | None = Field(default=None, ge=1)
    weapon_kind: Literal["melee", "missile"] | None = None


class AdventureDescriptor(BaseModel):
    id: str
    name: str
    source: str
    playable: bool
    notes: str
