from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    class_name: str = Field(min_length=1, max_length=30)
    level: int = Field(ge=1, le=20)


class Character(BaseModel):
    id: str
    name: str
    class_name: str
    level: int
    max_life: int
    attack_bonus: int
    defense_bonus: int
    created_at: datetime


class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    character_ids: list[str] = Field(min_length=1)


class Party(BaseModel):
    id: str
    name: str
    character_ids: list[str]
    created_at: datetime


class Enemy(BaseModel):
    id: str
    name: str
    level: int
    life: int
    attacks: int


class DoorState(BaseModel):
    id: str
    result: str


class Tile(BaseModel):
    id: str
    x: int
    y: int
    tile_type: Literal["room", "corridor"]
    content: str
    enemies: list[Enemy] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    visited: bool = False
    searched: bool = False
    search_result: str | None = None
    doors: list[DoorState] = Field(default_factory=list)


class MapState(BaseModel):
    width: int
    height: int
    tiles: list[Tile]
    current_tile_id: str


class PartyStatus(BaseModel):
    character_id: str
    name: str
    class_name: str
    level: int
    current_life: int
    max_life: int
    attack_bonus: int
    defense_bonus: int


class SessionState(BaseModel):
    id: str
    party_id: str
    mode: Literal["exploration", "combat", "complete"]
    adventure_type: Literal["random", "imported"]
    adventure_id: str | None = None
    map_state: MapState
    party_status: list[PartyStatus]
    log: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
