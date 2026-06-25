from __future__ import annotations

from typing import Any

from ..rules.repository import RulesRepository, VALID_TILE_KEYS
from ..schemas import TileDefinition

OPPOSITE = {
    "north": "south",
    "northeast": "southwest",
    "east": "west",
    "southeast": "northwest",
    "south": "north",
    "southwest": "northeast",
    "west": "east",
    "northwest": "southeast",
}

ENTRANCE_TILE_KEYS = frozenset(f"0{d}" for d in range(1, 7))


def tile_role(tile_key: str) -> str:
    if tile_key in ENTRANCE_TILE_KEYS:
        return "entrance_surface"
    return "dungeon_interior"


def native_exit_directions(tile_def: TileDefinition | None) -> dict[str, str]:
    """Map direction -> native portal kind (passage/door) from tiles.json."""
    if tile_def is None:
        return {}
    result: dict[str, str] = {}
    for exit_def in tile_def.exits:
        result[exit_def.direction] = exit_def.kind
    return result


def exit_port_label(direction: str, x: int, y: int, width: int, height: int) -> str:
    """Human label for where a portal sits on the tile edge (for AI room descriptions)."""
    if direction not in {"north", "south", "east", "west"}:
        return direction
    if direction in ("north", "south"):
        third = max(1, width // 3)
        if x < third:
            side = "west"
        elif x >= width - third:
            side = "east"
        else:
            side = "center"
        return f"{direction}-{side}"
    third = max(1, height // 3)
    if y < third:
        side = "north"
    elif y >= height - third:
        side = "south"
    else:
        side = "center"
    return f"{direction}-{side}"


def native_exit_ports(tile_def: TileDefinition) -> list[dict[str, Any]]:
    width = tile_def.footprint_width
    height = tile_def.footprint_height
    ports: list[dict[str, Any]] = []
    for exit_def in tile_def.exits:
        ports.append(
            {
                "direction": exit_def.direction,
                "kind": exit_def.kind,
                "port": exit_port_label(exit_def.direction, exit_def.x, exit_def.y, width, height),
                "x": exit_def.x,
                "y": exit_def.y,
                "span": exit_def.span,
            }
        )
    return ports


def walkable_ascii(rows: list[str]) -> list[str]:
    return [row.replace("0", ".").replace("1", "#") for row in rows]


def _walkable_cells(rows: list[str]) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            if cell != "0":
                cells.append((x, y))
    return cells


def describe_tile_shape(tile_def: TileDefinition, exit_ports: list[dict[str, Any]]) -> str:
    rows = tile_def.walkable
    width = tile_def.footprint_width
    height = tile_def.footprint_height
    cells = _walkable_cells(rows)
    if not cells:
        return f"{tile_def.tile_type}, empty walkable area on {width}x{height} footprint"

    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    bbox_w = max(xs) - min(xs) + 1
    bbox_h = max(ys) - min(ys) + 1
    fill_ratio = len(cells) / max(1, width * height)
    avg_x = sum(xs) / len(cells)
    avg_y = sum(ys) / len(cells)

    if height == 1 or bbox_h == 1:
        shape = "straight east-west corridor"
    elif width == 1 or bbox_w == 1:
        shape = "straight north-south corridor"
    elif bbox_w >= 5 and bbox_h >= 4 and fill_ratio > 0.45:
        shape = "large open chamber"
    elif bbox_w <= 3 and bbox_h >= 4:
        shape = "narrow vertical passage"
    elif bbox_h <= 3 and bbox_w >= 5:
        shape = "wide horizontal hall"
    elif len(cells) <= 4:
        shape = "tiny alcove or landing"
    elif fill_ratio < 0.3:
        shape = "irregular sparse floor (use modest prose)"
    else:
        shape = f"{tile_def.tile_type}"

    floor_hint = ""
    center_x, center_y = (width - 1) / 2, (height - 1) / 2
    if avg_y < center_y - 0.5:
        floor_hint = "; walkable floor mainly in the north half"
    elif avg_y > center_y + 0.5:
        floor_hint = "; walkable floor mainly in the south half"
    elif avg_x < center_x - 0.5:
        floor_hint = "; walkable floor mainly in the west half"
    elif avg_x > center_x + 0.5:
        floor_hint = "; walkable floor mainly in the east half"

    port_labels = ", ".join(
        f"{port['port']} ({port['kind']})" for port in exit_ports
    )
    return (
        f"{shape} on {width}x{height} grid ({len(cells)} walkable squares{floor_hint}). "
        f"Use only these portal locations: {port_labels}."
    )


def build_tile_catalog_entry(tile_def: TileDefinition) -> dict[str, Any]:
    native = native_exit_directions(tile_def)
    exit_ports = native_exit_ports(tile_def)
    return {
        "tile_key": tile_def.key,
        "name": tile_def.name,
        "tile_role": tile_role(tile_def.key),
        "tile_type": tile_def.tile_type,
        "footprint_width": tile_def.footprint_width,
        "footprint_height": tile_def.footprint_height,
        "footprint": f"{tile_def.footprint_width}x{tile_def.footprint_height}",
        "native_exit_directions": sorted(native),
        "native_exits": native,
        "native_exit_ports": exit_ports,
        "exit_count": len(exit_ports),
        "shape_summary": describe_tile_shape(tile_def, exit_ports),
        "walkable_map": walkable_ascii(tile_def.walkable),
    }


def build_tile_catalog(repo: RulesRepository) -> dict[str, Any]:
    tiles = repo.tiles()
    by_key: dict[str, dict[str, Any]] = {}
    by_exit_count: dict[str, list[str]] = {}
    by_role: dict[str, list[str]] = {"entrance_surface": [], "dungeon_interior": []}
    for key in VALID_TILE_KEYS:
        tile_def = tiles.get(key)
        if tile_def is None:
            continue
        entry = build_tile_catalog_entry(tile_def)
        by_key[key] = entry
        bucket = str(entry["exit_count"])
        by_exit_count.setdefault(bucket, []).append(key)
        by_role[entry["tile_role"]].append(key)
    for bucket in by_exit_count:
        by_exit_count[bucket] = sorted(by_exit_count[bucket])
    for role in by_role:
        by_role[role] = sorted(by_role[role])
    return {
        "schema_version": 1,
        "tiles": by_key,
        "tile_keys_by_exit_count": by_exit_count,
        "tile_keys_by_role": by_role,
        "authoring_rules": [
            "tile_role entrance_surface (01–06): use ONLY for entrance_room_id (surface / stairs down).",
            "tile_role dungeon_interior (11–66): use for all rooms inside the dungeon.",
            "Every manifest exit direction must match native_exit_ports on the chosen tile_key.",
            "Only declare exits on directions listed in native_exit_ports — you cannot add portals on other edges.",
            "Write room descriptions using shape_summary and walkable_map (# = floor, . = wall/void).",
            "Mention where doors/passages are (e.g. north-center door) so text matches the map art.",
            "Do not copy tile_key chains from examples — pick tiles that match each room's exit layout.",
            "Entrance and exit rooms also receive a dungeon surface/leave portal on an unused native direction at play time.",
        ],
    }


def tile_catalog_for_prompt(repo: RulesRepository) -> dict[str, Any]:
    """Condensed catalog for LLM prompts — shape + exit port positions per tile."""
    full = build_tile_catalog(repo)
    slim_tiles: dict[str, dict[str, Any]] = {}
    for key, entry in full["tiles"].items():
        slim_tiles[key] = {
            "name": entry["name"],
            "tile_role": entry["tile_role"],
            "footprint": entry["footprint"],
            "tile_type": entry["tile_type"],
            "shape_summary": entry["shape_summary"],
            "native_exit_ports": entry["native_exit_ports"],
            "walkable_map": entry["walkable_map"],
        }
    return {
        "authoring_rules": full["authoring_rules"],
        "tile_keys_by_exit_count": full["tile_keys_by_exit_count"],
        "tile_keys_by_role": full["tile_keys_by_role"],
        "tiles": slim_tiles,
    }


def pick_tile_key(
    required_directions: set[str],
    catalog: dict[str, Any],
    *,
    used_keys: set[str] | None = None,
    prefer_type: str | None = None,
    prefer_role: str | None = None,
) -> str | None:
    used = used_keys or set()
    candidates: list[tuple[str, dict[str, Any]]] = []
    for key, entry in catalog["tiles"].items():
        native = set(entry.get("native_exit_directions") or [])
        if not required_directions <= native:
            continue
        if prefer_type and entry.get("tile_type") != prefer_type:
            continue
        if prefer_role and entry.get("tile_role") != prefer_role:
            continue
        candidates.append((key, entry))
    if not candidates and prefer_type:
        for key, entry in catalog["tiles"].items():
            native = set(entry.get("native_exit_directions") or [])
            if required_directions <= native:
                if prefer_role and entry.get("tile_role") != prefer_role:
                    continue
                candidates.append((key, entry))
    if not candidates and prefer_role:
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
            ports = entry.get("native_exit_ports") or []
            port_hint = ", ".join(port["port"] for port in ports) or "none"
            errors.append(
                f"Room {room_id!r} (tile_key {tile_key}) cannot use exit {direction!r} — "
                f"tile portals are {port_hint}."
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
    role = entry.get("tile_role")
    if role == "entrance_surface" and room_id not in (entrance_room_id, exit_room_id):
        errors.append(
            f"Room {room_id!r} uses entrance surface tile {tile_key} (01–06); "
            "reserve 01–06 for entrance_room_id or exit_room_id only."
        )
    if (
        role == "dungeon_interior"
        and room_id in (entrance_room_id, exit_room_id)
        and tile_key not in ENTRANCE_TILE_KEYS
    ):
        errors.append(
            f"Room {room_id!r} is entrance/exit but tile_key {tile_key} is a dungeon interior tile; "
            "prefer entrance_surface tiles 01–06 for the surface room."
        )
    return errors


def validate_exit_kind(
    tile_key: str,
    direction: str,
    kind: str,
    catalog: dict[str, Any],
    *,
    room_id: str,
    exit_label: str,
    native_exits: dict[str, str] | None = None,
) -> list[str]:
    entry = catalog["tiles"].get(tile_key)
    if entry is None:
        return []
    native = native_exits if native_exits is not None else entry.get("native_exits") or {}
    expected = native.get(direction)
    if expected is None:
        return []
    if kind != expected:
        return [
            f"Room {room_id!r} {exit_label} kind {kind!r} does not match tile {tile_key} native portal "
            f"({direction} is {expected!r} on this tile)."
        ]
    return []


def collect_reciprocal_exit_warnings(room_by_id: dict[str, dict[str, Any]]) -> list[str]:
    """Warn when A→B lacks B→A — engine can repair layout but maps may misalign."""
    warnings: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for room_id, room in room_by_id.items():
        exits = room.get("exits")
        if not isinstance(exits, list):
            continue
        for exit_def in exits:
            if not isinstance(exit_def, dict):
                continue
            direction = exit_def.get("direction")
            to_room = exit_def.get("to")
            if direction not in OPPOSITE or not isinstance(to_room, str) or to_room not in room_by_id:
                continue
            pair_key = (room_id, str(direction), to_room)
            if pair_key in seen:
                continue
            opposite = OPPOSITE[str(direction)]
            target = room_by_id[to_room]
            target_exits = target.get("exits") if isinstance(target, dict) else None
            reciprocal = False
            if isinstance(target_exits, list):
                reciprocal = any(
                    isinstance(item, dict)
                    and item.get("direction") == opposite
                    and item.get("to") == room_id
                    for item in target_exits
                )
            if not reciprocal:
                warnings.append(
                    f"Room {room_id!r} exit {direction}→{to_room!r} has no reciprocal "
                    f"{opposite}→{room_id!r} on the target room (import may place rooms far apart)."
                )
                seen.add(pair_key)
                seen.add((to_room, opposite, room_id))
    return warnings


def collect_incoming_link_warnings(room_by_id: dict[str, dict[str, Any]]) -> list[str]:
    """Warn when a room is linked to but declares no exits (common LLM one-way graph bug)."""
    incoming: dict[str, list[tuple[str, str]]] = {}
    for room_id, room in room_by_id.items():
        exits = room.get("exits")
        if not isinstance(exits, list):
            continue
        for exit_def in exits:
            if not isinstance(exit_def, dict):
                continue
            direction = exit_def.get("direction")
            to_room = exit_def.get("to")
            if not isinstance(direction, str) or not isinstance(to_room, str) or to_room not in room_by_id:
                continue
            incoming.setdefault(to_room, []).append((room_id, direction))

    warnings: list[str] = []
    for target_id, links in sorted(incoming.items()):
        target = room_by_id.get(target_id)
        if not isinstance(target, dict):
            continue
        target_exits = target.get("exits")
        if isinstance(target_exits, list) and target_exits:
            continue
        sources = ", ".join(f"{source!r} ({direction})" for source, direction in links)
        warnings.append(
            f"Room {target_id!r} has no exits but is linked from {sources}. "
            f"Add reciprocal exit(s) on {target_id!r} (engine can patch at runtime, but maps misalign)."
        )
    return warnings
