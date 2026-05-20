from __future__ import annotations

from typing import Literal

TileTerrain = Literal["indoor", "outdoor", "forest", "swamp", "jungle"]

VALID_TERRAINS: frozenset[str] = frozenset({"indoor", "outdoor", "forest", "swamp", "jungle"})


def normalize_terrain(value: str | None) -> str:
    if value and value in VALID_TERRAINS:
        return value
    return "indoor"


def tile_is_outdoors(terrain: str | None) -> bool:
    return normalize_terrain(terrain) != "indoor"


def entangle_terrain_ok(terrain: str | None) -> bool:
    return normalize_terrain(terrain) in {"forest", "swamp", "jungle"}


def forest_pathway_terrain_ok(terrain: str | None) -> bool:
    return normalize_terrain(terrain) in {"forest", "jungle"}
