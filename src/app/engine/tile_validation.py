from __future__ import annotations

from typing import Any

from ..schemas import TileDefinition
from .tile_catalogs import (
    DUNGEON_ROOM_CODES,
    RIVER_ROOM_CODES,
    TILE_CATALOG_KEYS,
    VALID_WALKABLE_CODES,
    TileCatalogId,
    WALKABLE_FLOOR,
    WALKABLE_WATER,
)

VALID_SHAPES = frozenset("FABCDEGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
VALID_DIRECTIONS = frozenset(
    {"north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"}
)
VALID_KINDS = frozenset({"door", "passage", "stairs", "chute", "window"})
VALID_ROOM_CODES = frozenset({*DUNGEON_ROOM_CODES, *RIVER_ROOM_CODES})
EXIT_DIRECTION_DELTAS = {
    "north": (0, -1),
    "northeast": (1, -1),
    "east": (1, 0),
    "southeast": (1, 1),
    "south": (0, 1),
    "southwest": (-1, 1),
    "west": (-1, 0),
    "northwest": (-1, -1),
}


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
            if label == "walkable" and char not in VALID_WALKABLE_CODES:
                issues.append(f"{label} row {index} has invalid walkable code '{char}'.")
    return issues


def _exit_in_bounds(exit_data: dict[str, Any], width: int, height: int) -> bool:
    x = int(exit_data.get("x", 0))
    y = int(exit_data.get("y", 0))
    return 0 <= x < width and 0 <= y < height


def _exit_cells(exit_data: dict[str, Any]) -> list[tuple[int, int]]:
    x = int(exit_data.get("x", 0))
    y = int(exit_data.get("y", 0))
    span = max(1, int(exit_data.get("span", exit_data.get("width", 1)) or 1))
    direction = str(exit_data.get("direction", "")).lower()
    span_steps = {
        "north": (1, 0),
        "south": (1, 0),
        "east": (0, 1),
        "west": (0, 1),
        "northeast": (1, 1),
        "southwest": (1, 1),
        "southeast": (1, -1),
        "northwest": (1, -1),
    }
    step_x, step_y = span_steps.get(direction, (0, 0))
    return [(x + offset * step_x, y + offset * step_y) for offset in range(span)]


def _traversable_cell(char: str) -> bool:
    return char in {WALKABLE_FLOOR, WALKABLE_WATER}


def _exit_cell_has_traversable_interior(
    walkable: list[str],
    cell_x: int,
    cell_y: int,
    direction: str,
    width: int,
    height: int,
) -> bool:
    if _traversable_cell(walkable[cell_y][cell_x]):
        return True
    dx, dy = EXIT_DIRECTION_DELTAS.get(direction, (0, 0))
    inside_x = cell_x - dx
    inside_y = cell_y - dy
    return (
        0 <= inside_x < width
        and 0 <= inside_y < height
        and _traversable_cell(walkable[inside_y][inside_x])
    )


def validate_tile_definition(
    tile: TileDefinition | dict[str, Any],
    *,
    catalog: TileCatalogId = "ee",
) -> list[str]:
    if isinstance(tile, TileDefinition):
        data = tile.model_dump()
        catalog = tile.catalog
    else:
        data = dict(tile)
        catalog = str(data.get("catalog") or catalog)
    issues: list[str] = []
    key = str(data.get("key", ""))
    allowed_keys = TILE_CATALOG_KEYS.get(catalog, TILE_CATALOG_KEYS["ee"])
    if key not in allowed_keys:
        issues.append(f"key {key} is not valid for catalog {catalog}.")
    width = int(data.get("footprint_width", 1))
    height = int(data.get("footprint_height", 1))
    walkable = list(data.get("walkable") or [])
    shapes = list(data.get("cell_shapes") or [])
    issues.extend(_grid_issues(walkable, width, height, "walkable"))
    if shapes:
        issues.extend(_grid_issues(shapes, width, height, "cell_shapes"))
    elif walkable:
        issues.append("cell_shapes missing while walkable grid is defined.")
    room_codes = list(data.get("room_codes") or [])
    allowed_room_codes = set(DUNGEON_ROOM_CODES if catalog == "forsaken_depths" else RIVER_ROOM_CODES if catalog == "forsaken_depths_rivers" else ())
    for code in room_codes:
        if code not in VALID_ROOM_CODES:
            issues.append(f"invalid room code {code!r}.")
        elif catalog == "ee" and code:
            issues.append(f"room code {code!r} is not used in the EE catalog.")
        elif allowed_room_codes and code not in allowed_room_codes:
            issues.append(f"room code {code!r} is not valid for catalog {catalog}.")
    exits = list(data.get("exits") or [])
    if not exits:
        issues.append("no exits defined.")
    dungeon_exit_count = sum(1 for exit_data in exits if exit_data.get("dungeon_exit"))
    starting_keys = {f"0{index}" for index in range(1, 7)}
    if catalog == "ee":
        if key in starting_keys and dungeon_exit_count != 1:
            issues.append(f"starting entrance tile must define exactly one dungeon exit, found {dungeon_exit_count}.")
        if key not in starting_keys and dungeon_exit_count:
            issues.append(f"generated tile must not define dungeon exits, found {dungeon_exit_count}.")
    elif dungeon_exit_count:
        issues.append(f"{catalog} tiles must not define dungeon exits, found {dungeon_exit_count}.")
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
        for cell_x, cell_y in _exit_cells(exit_data):
            if not (0 <= cell_x < width and 0 <= cell_y < height):
                issues.append(f"exit {exit_id} span extends outside the footprint grid.")
                break
            if len(walkable) == height and all(len(row) == width for row in walkable):
                if not _exit_cell_has_traversable_interior(
                    walkable,
                    cell_x,
                    cell_y,
                    direction,
                    width,
                    height,
                ):
                    issues.append(
                        f"exit {exit_id} has blocked anchor {cell_x},{cell_y} without a traversable interior square."
                    )
                    break
    tile_type = str(data.get("tile_type", "unknown"))
    if tile_type not in {"room", "corridor", "unknown"}:
        issues.append(f"invalid tile_type {tile_type!r}.")
    if walkable and not any(_traversable_cell(char) for row in walkable for char in row):
        issues.append("no walkable or water squares marked.")
    return issues


def validate_tile_catalog(
    tiles: dict[str, TileDefinition],
    *,
    catalog: TileCatalogId = "ee",
) -> dict[str, list[str]]:
    allowed_keys = TILE_CATALOG_KEYS[catalog]
    report: dict[str, list[str]] = {}
    for key in sorted(allowed_keys):
        if key not in tiles:
            report[key] = ["missing from catalog."]
            continue
        issues = validate_tile_definition(tiles[key], catalog=catalog)
        if issues:
            report[key] = issues
    return report


def map_elements_validation_table_rows(
    tiles: dict[str, TileDefinition],
    *,
    catalog: TileCatalogId = "ee",
) -> list[dict[str, str]]:
    catalog_issues = validate_tile_catalog(tiles, catalog=catalog)
    rows: list[dict[str, str]] = []
    for key in sorted(TILE_CATALOG_KEYS[catalog]):
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
                    "notes": f"Not in {catalog} tile catalog.",
                }
            )
            continue
        issues = catalog_issues.get(key, [])
        room_code_note = ", ".join(tile.room_codes) if tile.room_codes else ""
        rows.append(
            {
                "key": key,
                "name": tile.name,
                "type": tile.tile_type,
                "footprint": f"{tile.footprint_width}×{tile.footprint_height}",
                "exits": str(len(tile.exits or [])),
                "editor_status": tile.implementation_status,
                "validation": "pass" if not issues else f"fail ({len(issues)})",
                "notes": "; ".join([note for note in [room_code_note, *issues[:2]] if note]),
            }
        )
    return rows
