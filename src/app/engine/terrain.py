"""Minimal play-context flags for outdoor terrain and environment (no hex map).

Two axes:
- **environment** — table routing (dungeon, caverns, fungal_grottoes)
- **terrain** — biome / indoor-outdoor (indoor, outdoor, forest, swamp, jungle, …)

Session flags (weather, forest pathway) layer on top for EE druid/illusionist rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..schemas import SessionState, TileState

EnvironmentKind = Literal["dungeon", "caverns", "fungal_grottoes"]

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

VALID_ENVIRONMENTS: frozenset[str] = frozenset({"dungeon", "caverns", "fungal_grottoes"})

VALID_TERRAINS: frozenset[str] = frozenset(
    {
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
    }
)

ENTANGLE_TERRAINS: frozenset[str] = frozenset({"forest", "swamp", "jungle"})
FOREST_PATHWAY_TERRAINS: frozenset[str] = frozenset({"forest", "jungle"})
WATER_TERRAINS: frozenset[str] = frozenset({"water", "pond", "stream", "river", "lake", "seashore"})


def normalize_environment(value: str | None) -> EnvironmentKind:
    if value and value in VALID_ENVIRONMENTS:
        return value  # type: ignore[return-value]
    return "dungeon"


def normalize_terrain(value: str | None) -> TileTerrain:
    if value and value in VALID_TERRAINS:
        return value  # type: ignore[return-value]
    return "indoor"


def tile_is_outdoors(terrain: str | None) -> bool:
    return normalize_terrain(terrain) != "indoor"


def entangle_terrain_ok(terrain: str | None) -> bool:
    return normalize_terrain(terrain) in ENTANGLE_TERRAINS


def forest_pathway_terrain_ok(terrain: str | None) -> bool:
    return normalize_terrain(terrain) in FOREST_PATHWAY_TERRAINS


@dataclass(frozen=True)
class PlayContext:
    """Resolved context for the current map element and session."""

    environment: EnvironmentKind
    terrain: TileTerrain
    outdoors: bool
    weather_active: bool
    forest_pathway_active: bool

    @property
    def entangle_ok(self) -> bool:
        return entangle_terrain_ok(self.terrain)

    @property
    def forest_pathway_ok(self) -> bool:
        return forest_pathway_terrain_ok(self.terrain)

    @property
    def alter_weather_ok(self) -> bool:
        return self.outdoors

    @property
    def lightning_strike_ok(self) -> bool:
        return self.outdoors

    @property
    def ranger_outdoor_missile_ok(self) -> bool:
        return self.outdoors

    @property
    def druid_companion_wilderness_ok(self) -> bool:
        return self.outdoors

    def label(self) -> str:
        parts = [self.environment.replace("_", " ")]
        if self.terrain != "indoor":
            parts.append(self.terrain.replace("_", " "))
        if self.weather_active:
            parts.append("altered weather")
        if self.forest_pathway_active:
            parts.append("forest pathway")
        return " · ".join(parts)

    def as_dict(self) -> dict[str, bool | str]:
        return {
            "environment": self.environment,
            "terrain": self.terrain,
            "outdoors": self.outdoors,
            "weather_active": self.weather_active,
            "forest_pathway_active": self.forest_pathway_active,
            "entangle_ok": self.entangle_ok,
            "forest_pathway_ok": self.forest_pathway_ok,
            "alter_weather_ok": self.alter_weather_ok,
            "lightning_strike_ok": self.lightning_strike_ok,
            "ranger_outdoor_missile_ok": self.ranger_outdoor_missile_ok,
        }


def resolve_play_context(
    tile: TileState | None,
    session: SessionState | None = None,
    *,
    terrain: str | None = None,
    environment: str | None = None,
) -> PlayContext:
    env = normalize_environment(
        environment
        or (tile.environment if tile is not None else None)
        or (session.environment if session is not None else None)
    )
    ter = normalize_terrain(terrain or (tile.terrain if tile is not None else None))
    weather = bool(session is not None and session.alter_weather_active)
    pathway = bool(session is not None and session.forest_pathway_active)
    return PlayContext(
        environment=env,
        terrain=ter,
        outdoors=tile_is_outdoors(ter),
        weather_active=weather,
        forest_pathway_active=pathway,
    )
