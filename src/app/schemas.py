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
    image_scale: float = Field(default=1.0, ge=0.1, le=5.0)
    image_offset_x: int = Field(default=0, ge=-1000, le=1000)
    image_offset_y: int = Field(default=0, ge=-1000, le=1000)
    walkable: list[str] = Field(default_factory=list)
    cell_shapes: list[str] = Field(default_factory=list)
    exits: list[TileExitDefinition] = Field(default_factory=list)
    implementation_status: str = "placeholder"


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    class_id: str = Field(min_length=1, max_length=40)


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
    created_at: str
    updated_at: str


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
    inventory: list[str] = Field(default_factory=list)
    spells: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)


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
    image_scale: float = Field(default=1.0, ge=0.1, le=5.0)
    image_offset_x: int = Field(default=0, ge=-1000, le=1000)
    image_offset_y: int = Field(default=0, ge=-1000, le=1000)
    walkable: list[str] = Field(default_factory=list)
    cell_shapes: list[str] = Field(default_factory=list)
    image: str | None = None
    title: str
    description: str
    content_key: str = "empty"
    objects: list[str] = Field(default_factory=list)
    enemies: list[EnemyState] = Field(default_factory=list)
    exits: list[ExitState] = Field(default_factory=list)
    searched: bool = False
    resolved: bool = False


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


class SessionAction(BaseModel):
    action: Literal["explore", "search", "combat_round", "rest"]
    exit_id: str | None = None
    direction: Literal["north", "east", "south", "west"] | None = None


class AdventureDescriptor(BaseModel):
    id: str
    name: str
    source: str
    playable: bool
    notes: str
