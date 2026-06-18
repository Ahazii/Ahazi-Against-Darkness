from __future__ import annotations

from typing import Any

from ..rules.repository import RulesRepository, VALID_TILE_KEYS
from ..schemas import TileDefinition

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}


def native_exit_directions(tile_def: TileDefinition | None) -> dict[str, str]:
    """Map direction -> native portal kind (passage/door) from tiles.json."""
    if tile_def is None:
        return {}
    result: dict[str, str] = {}
    for exit_def in tile_def.exits:
        result[exit_def.direction] = exit_def.kind
    return result


def build_tile_catalog_entry(tile_def: TileDefinition) -> dict[str, Any]:
    native = native_exit_directions(tile_def)
    return {
        "tile_key": tile_def.key,
        "name": tile_def.name,
        "tile_type": tile_def.tile_type,
        "footprint_width": tile_def.footprint_width,
        "footprint_height": tile_def.footprint_height,
        "footprint": f"{tile_def.footprint_width}x{tile_def.footprint_height}",
        "native_exit_directions": sorted(native),
        "native_exits": native,
        "exit_count": len(native),
    }


def build_tile_catalog(repo: RulesRepository) -> dict[str, Any]:
    tiles = repo.tiles()
    by_key: dict[str, dict[str, Any]] = {}
    by_exit_count: dict[str, list[str]] = {}
    for key in VALID_TILE_KEYS:
        tile_def = tiles.get(key)
        if tile_def is None:
            continue
        entry = build_tile_catalog_entry(tile_def)
        by_key[key] = entry
        bucket = str(entry["exit_count"])
        by_exit_count.setdefault(bucket, []).append(key)
    for bucket in by_exit_count:
        by_exit_count[bucket] = sorted(by_exit_count[bucket])
    return {
        "schema_version": 1,
        "tiles": by_key,
        "tile_keys_by_exit_count": by_exit_count,
        "authoring_rules": [
            "Every manifest exit direction must exist on the chosen tile_key (see native_exit_directions).",
            "Do not copy tile_key chains from examples — pick tiles that match each room's exit layout.",
            "Write descriptions that fit the footprint and native exits (corridor vs hall vs dead-end).",
            "Entrance and exit rooms also receive a dungeon surface/leave portal on an unused native direction.",
        ],
    }


def tile_catalog_for_prompt(repo: RulesRepository) -> dict[str, Any]:
    """Condensed catalog for LLM prompts (all tiles, grouped by exit count)."""
    full = build_tile_catalog(repo)
    return {
        "authoring_rules": full["authoring_rules"],
        "tile_keys_by_exit_count": full["tile_keys_by_exit_count"],
        "tiles": full["tiles"],
    }


def pick_tile_key(
    required_directions: set[str],
    catalog: dict[str, Any],
    *,
    used_keys: set[str] | None = None,
    prefer_type: str | None = None,
) -> str | None:
    used = used_keys or set()
    candidates: list[tuple[str, dict[str, Any]]] = []
    for key, entry in catalog["tiles"].items():
        native = set(entry.get("native_exit_directions") or [])
        if not required_directions <= native:
            continue
        if prefer_type and entry.get("tile_type") != prefer_type:
            continue
        candidates.append((key, entry))
    if not candidates and prefer_type:
        for key, entry in catalog["tiles"].items():
            native = set(entry.get("native_exit_directions") or [])
            if required_directions <= native:
                candidates.append((key, entry))
    if not candidates:
        return None

    def sort_key(item: tuple[str, dict[str, Any]]) -> tuple:
        key, entry = item
        return (key in used, abs(entry["exit_count"] - len(required_directions)), key)

    return sorted(candidates, key=sort_key)[0][0]


def validate_room_exit_directions(
    tile_key: str,
    exit_directions: set[str],
    catalog: dict[str, Any],
    *,
    room_id: str,
    entrance_room_id: str,
    exit_room_id: str,
) -> list[str]:
    entry = catalog["tiles"].get(tile_key)
    if entry is None:
        return []
    native = set(entry.get("native_exit_directions") or [])
    errors: list[str] = []
    for direction in sorted(exit_directions):
        if direction not in native:
            errors.append(
                f"Room {room_id!r} (tile_key {tile_key}) cannot use exit {direction!r} — "
                f"tile native exits are {sorted(native)}."
            )
    extra_portals = 0
    if room_id == entrance_room_id:
        extra_portals += 1
    if room_id == exit_room_id:
        extra_portals += 1
    if len(exit_directions) + extra_portals > len(native):
        errors.append(
            f"Room {room_id!r} (tile_key {tile_key}) needs {len(exit_directions) + extra_portals} "
            f"distinct portal directions (including surface/leave) but tile only has {len(native)}."
        )
    return errors
