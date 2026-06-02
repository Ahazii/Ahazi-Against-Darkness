from __future__ import annotations

from typing import Any

from ..schemas import TileDefinition

VALID_SHAPES = frozenset("FABCDEGHIJKLMNOPQRSTU")
VALID_DIRECTIONS = frozenset({"north", "east", "south", "west"})
VALID_KINDS = frozenset({"door", "passage", "stairs", "chute", "window"})
STARTING_KEYS = {f"{index:02d}" for index in range(1, 7)}
GENERATED_KEYS = {f"{tens}{ones}" for tens in range(1, 7) for ones in range(1, 7)}


def _grid_issues(rows: list[str], width: int, height: int, label: str) -> list[str]:
    issues: list[str] = []
    if len(rows) != height:
        issues.append(f"{label} has {len(rows)} rows, expected {height}.")
    for index, row in enumerate(rows):
        if len(row) != width:
            issues.append(f"{label} row {index} width {len(row)}, expected {width}.")
        for char in row:
            if label == "cell_shapes" and char not in VALID_SHAPES:
                issues.append(f"{label} row {index} has invalid shape code '{char}'.")
            if label == "walkable" and char not in {"0", "1"}:
                issues.append(f"{label} row {index} has invalid walkable code '{char}'.")
    return issues


def _exit_in_bounds(exit_data: dict[str, Any], width: int, height: int) -> bool:
    x = int(exit_data.get("x", 0))
    y = int(exit_data.get("y", 0))
    return 0 <= x < width and 0 <= y < height


def validate_tile_definition(tile: TileDefinition | dict[str, Any]) -> list[str]:
    if isinstance(tile, TileDefinition):
        data = tile.model_dump()
    else:
        data = dict(tile)
    issues: list[str] = []
    key = str(data.get("key", ""))
    if key not in STARTING_KEYS | GENERATED_KEYS:
        issues.append(f"key {key} is not in starting (01–06) or generated (11–66) sets.")
    width = int(data.get("footprint_width", 1))
    height = int(data.get("footprint_height", 1))
    walkable = list(data.get("walkable") or [])
    shapes = list(data.get("cell_shapes") or [])
    issues.extend(_grid_issues(walkable, width, height, "walkable"))
    if shapes:
        issues.extend(_grid_issues(shapes, width, height, "cell_shapes"))
    elif walkable:
        issues.append("cell_shapes missing while walkable grid is defined.")
    exits = list(data.get("exits") or [])
    if not exits:
        issues.append("no exits defined.")
    seen_ids: set[str] = set()
    for exit_data in exits:
        exit_id = str(exit_data.get("id", ""))
        if not exit_id:
            issues.append("exit missing id.")
            continue
        if exit_id in seen_ids:
            issues.append(f"duplicate exit id {exit_id}.")
        seen_ids.add(exit_id)
        direction = str(exit_data.get("direction", "")).lower()
        if direction not in VALID_DIRECTIONS:
            issues.append(f"exit {exit_id} has invalid direction {direction!r}.")
        kind = str(exit_data.get("kind", "door")).lower()
        if kind not in VALID_KINDS:
            issues.append(f"exit {exit_id} has invalid kind {kind!r}.")
        if not _exit_in_bounds(exit_data, width, height):
            issues.append(f"exit {exit_id} is outside the footprint grid.")
    tile_type = str(data.get("tile_type", "unknown"))
    if tile_type not in {"room", "corridor", "unknown"}:
        issues.append(f"invalid tile_type {tile_type!r}.")
    return issues


def validate_tile_catalog(tiles: dict[str, TileDefinition]) -> dict[str, list[str]]:
    report: dict[str, list[str]] = {}
    for key in sorted(STARTING_KEYS | GENERATED_KEYS):
        if key not in tiles:
            report[key] = ["missing from catalog."]
            continue
        issues = validate_tile_definition(tiles[key])
        if issues:
            report[key] = issues
    return report


def map_elements_validation_table_rows(tiles: dict[str, TileDefinition]) -> list[dict[str, str]]:
    catalog_issues = validate_tile_catalog(tiles)
    rows: list[dict[str, str]] = []
    for key in sorted(STARTING_KEYS | GENERATED_KEYS):
        tile = tiles.get(key)
        if tile is None:
            rows.append(
                {
                    "key": key,
                    "name": "(missing)",
                    "type": "",
                    "footprint": "",
                    "exits": "0",
                    "editor_status": "",
                    "validation": "missing",
                    "notes": "Not in tiles.json catalog.",
                }
            )
            continue
        issues = catalog_issues.get(key, [])
        rows.append(
            {
                "key": key,
                "name": tile.name,
                "type": tile.tile_type,
                "footprint": f"{tile.footprint_width}×{tile.footprint_height}",
                "exits": str(len(tile.exits or [])),
                "editor_status": tile.implementation_status,
                "validation": "pass" if not issues else f"fail ({len(issues)})",
                "notes": "; ".join(issues[:3]),
            }
        )
    return rows
