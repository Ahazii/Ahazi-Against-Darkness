from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..db import now_utc
from ..schemas import ActiveQuestState, ExitState, MapState, PartyMemberState, SessionState, TileState
from .adventure_runtime import IMPORTED_ROOM_PREFIX, fire_imported_triggers, quest_from_manifest
from .tag_compat import tag_reference_from_manifest
from .experience import campaign_mode_label, normalize_unlimited_map_element_cap
from .roster_sync import initial_xp_tally
from .expert_skill_effects import prepare_adventure_expert_items
from .heroic_skill_effects import mark_tile_visited
from .inventory import snapshot_carry_baseline
from .weapons import prune_weapon_defaults
from .fiendish_foes import fiendish_foes_session_label, normalize_fiendish_foes_enabled, party_fiendish_foes_eligible

if True:
    from .random_dungeon import OPPOSITE, RandomDungeonEngine

PLACEMENT_GAP = 0
SURFACE_EXIT_DIRECTIONS = ("south", "north", "west", "east")


def _room_dict(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {room["id"]: room for room in manifest.get("rooms", []) if isinstance(room, dict) and room.get("id")}


def _manifest_exit_kind(kind: str) -> str:
    return "door" if kind in {"door", "secret", "stairs"} else "passage"


def _manifest_exit_status(manifest_status: str, kind: str) -> tuple[str, bool]:
    if manifest_status == "blocked":
        return "blocked", False
    if manifest_status == "open":
        return "open", True
    if manifest_status == "closed":
        return "open", False
    if manifest_status == "locked":
        return "open", False
    return "open", False


def _apply_manifest_door_state(
    exit_state: ExitState,
    manifest_status: str,
    kind: str,
) -> None:
    """Imported doors use manifest status — never leave door_type None (procedural roll)."""
    if kind != "door":
        exit_state.door_type = None
        exit_state.door_result = None
        exit_state.door_level = None
        return
    if manifest_status == "locked":
        exit_state.door_type = "locked"
        exit_state.door_level = 1
        exit_state.door_result = "Locked door."
    else:
        exit_state.door_type = "unlocked"
        exit_state.door_level = None
        exit_state.door_result = "Unlocked door." if manifest_status == "open" else None


def _walkable_rows(engine: RandomDungeonEngine, tile_def, width: int, height: int) -> list[str]:
    if tile_def is None:
        return engine._visible_rows(width, height)
    return engine._normalized_walkable(tile_def, width, height)


def _walkable_edge_cell(rows: list[str], direction: str, width: int, height: int) -> tuple[int, int]:
    if direction not in {"north", "south", "east", "west"}:
        deltas = {
            "northeast": (1, -1),
            "southeast": (1, 1),
            "southwest": (-1, 1),
            "northwest": (-1, -1),
        }
        dx, dy = deltas.get(direction, (0, 0))
        cells = [(x, y) for y in range(height) for x in range(width) if rows[y][x] != "0"]
        if cells:
            return max(cells, key=lambda cell: cell[0] * dx + cell[1] * dy)
    if direction == "north":
        for y in range(height):
            row = [(x, y) for x in range(width) if rows[y][x] != "0"]
            if row:
                return row[len(row) // 2]
    elif direction == "south":
        for y in range(height - 1, -1, -1):
            row = [(x, y) for x in range(width) if rows[y][x] != "0"]
            if row:
                return row[len(row) // 2]
    elif direction == "west":
        for x in range(width):
            col = [(x, y) for y in range(height) if rows[y][x] != "0"]
            if col:
                return col[len(col) // 2]
    elif direction == "east":
        for x in range(width - 1, -1, -1):
            col = [(x, y) for y in range(height) if rows[y][x] != "0"]
            if col:
                return col[len(col) // 2]
    return (max(0, width // 2), max(0, height // 2))


def _apply_exit_geometry(
    engine: RandomDungeonEngine,
    exit_state: ExitState,
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    exit_state.x = x
    exit_state.y = y
    exit_state.offset = engine._exit_offset(exit_state.direction, x, y)
    exit_state.position = engine._position_from_offset(exit_state.offset, exit_state.direction, width, height)
    exit_state.span = max(1, min(exit_state.span, engine._max_exit_span(exit_state.direction, x, y, width, height)))


def _ensure_exit_on_walkable(
    engine: RandomDungeonEngine,
    exit_state: ExitState,
    tile_def,
    width: int,
    height: int,
) -> None:
    width_r, height_r = engine._rotated_size(width, height, 0)
    rows = _walkable_rows(engine, tile_def, width, height)
    native_cells = _native_portal_cells(tile_def)
    if (exit_state.x, exit_state.y) in native_cells:
        _apply_exit_geometry(engine, exit_state, exit_state.x, exit_state.y, width_r, height_r)
        return
    if rows[exit_state.y][exit_state.x] != "0":
        _apply_exit_geometry(engine, exit_state, exit_state.x, exit_state.y, width_r, height_r)
        return
    x, y = _walkable_edge_cell(rows, exit_state.direction, width_r, height_r)
    _apply_exit_geometry(engine, exit_state, x, y, width_r, height_r)


def _exit_from_tile_def(
    engine: RandomDungeonEngine,
    tile_def,
    direction: str,
    *,
    kind: str | None = None,
    used_native_cells: set[tuple[int, int]] | None = None,
) -> ExitState | None:
    if tile_def is None:
        return None
    used = used_native_cells or set()

    def _candidates() -> list[ExitState]:
        pool = [
            exit_state
            for exit_state in engine._rotated_exits(tile_def, 0)
            if exit_state.direction == direction and (exit_state.x, exit_state.y) not in used
        ]
        if kind:
            kind_matches = [exit_state for exit_state in pool if exit_state.kind == kind]
            if kind_matches:
                pool = kind_matches
        if not pool:
            pool = [
                exit_state
                for exit_state in engine._rotated_exits(tile_def, 0)
                if exit_state.direction == direction
            ]
            if kind:
                kind_matches = [exit_state for exit_state in pool if exit_state.kind == kind]
                if kind_matches:
                    pool = kind_matches
        return pool

    candidates = _candidates()
    if not candidates:
        return None
    chosen = candidates[0].model_copy(deep=True)
    used.add((chosen.x, chosen.y))
    return chosen


def _native_portal_cells(tile_def) -> set[tuple[int, int]]:
    if tile_def is None:
        return set()
    return {(exit_def.x, exit_def.y) for exit_def in tile_def.exits}


def _build_manifest_exits(
    engine: RandomDungeonEngine,
    room: dict[str, Any],
    tile_def,
    width: int,
    height: int,
) -> list[ExitState]:
    width_r, height_r = engine._rotated_size(width, height, 0)
    exits: list[ExitState] = []
    used_native_cells: set[tuple[int, int]] = set()
    for manifest_exit in room.get("exits") or []:
        if not isinstance(manifest_exit, dict):
            continue
        direction = str(manifest_exit.get("direction", "north"))
        kind = _manifest_exit_kind(str(manifest_exit.get("kind", "passage")))
        status, door_open = _manifest_exit_status(str(manifest_exit.get("status", "open")), kind)
        exit_state = _exit_from_tile_def(
            engine,
            tile_def,
            direction,
            kind=kind,
            used_native_cells=used_native_cells,
        )
        if exit_state is None:
            rows = _walkable_rows(engine, tile_def, width, height)
            x, y = _walkable_edge_cell(rows, direction, width_r, height_r)
            exit_state = engine._new_exit(
                direction=direction,
                kind=kind,
                width=width_r,
                height=height_r,
                status="blocked" if status == "blocked" else "open",
                exit_id=str(manifest_exit.get("id") or uuid4().hex),
            )
            _apply_exit_geometry(engine, exit_state, x, y, width_r, height_r)
        else:
            _ensure_exit_on_walkable(engine, exit_state, tile_def, width, height)
        exit_state.id = str(manifest_exit.get("id") or exit_state.id)
        exit_state.kind = kind
        if status != "unexplored":
            exit_state.status = status
        manifest_status = str(manifest_exit.get("status", "open"))
        _apply_manifest_door_state(exit_state, manifest_status, kind)
        if kind == "door":
            exit_state.door_open = manifest_status == "open"
        else:
            exit_state.door_open = door_open
        exits.append(exit_state)
    return exits


def _unused_direction(tile: TileState) -> str:
    used = {exit_state.direction for exit_state in tile.exits}
    for direction in SURFACE_EXIT_DIRECTIONS:
        if direction not in used:
            return direction
    return "south"


def _ensure_surface_entrance_exit(engine: RandomDungeonEngine, tile: TileState) -> None:
    if any(exit_state.dungeon_exit for exit_state in tile.exits):
        return
    direction = _unused_direction(tile)
    width, height = engine._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    tile_def = engine.rules.tiles().get(tile.tile_key)
    rows = _walkable_rows(engine, tile_def, tile.footprint_width, tile.footprint_height)
    x, y = _walkable_edge_cell(rows, direction, width, height)
    surface_exit = engine._new_exit(
        direction=direction,
        kind="passage",
        width=width,
        height=height,
        status="open",
        dungeon_exit=True,
        exit_id=f"{tile.id}-surface",
    )
    _apply_exit_geometry(engine, surface_exit, x, y, width, height)
    surface_exit.door_open = True
    tile.exits.append(surface_exit)


def _ensure_dungeon_leave_exit(engine: RandomDungeonEngine, tile: TileState) -> None:
    if any(exit_state.dungeon_exit for exit_state in tile.exits):
        return
    direction = _unused_direction(tile)
    width, height = engine._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    tile_def = engine.rules.tiles().get(tile.tile_key)
    rows = _walkable_rows(engine, tile_def, tile.footprint_width, tile.footprint_height)
    x, y = _walkable_edge_cell(rows, direction, width, height)
    leave_exit = engine._new_exit(
        direction=direction,
        kind="passage",
        width=width,
        height=height,
        status="open",
        dungeon_exit=True,
        exit_id=f"{tile.id}-leave",
        label="Stairs to daylight",
    )
    _apply_exit_geometry(engine, leave_exit, x, y, width, height)
    leave_exit.door_open = True
    tile.exits.append(leave_exit)


def _ensure_direction_exit_on_tile(
    engine: RandomDungeonEngine,
    tile: TileState,
    tile_def,
    direction: str,
    *,
    kind: str,
    manifest_status: str,
    exit_id: str | None = None,
) -> ExitState:
    """Add a graph-reciprocal exit when the manifest only declared one direction."""
    existing = next(
        (item for item in tile.exits if item.direction == direction and not item.dungeon_exit),
        None,
    )
    if existing is not None:
        _ensure_exit_on_walkable(
            engine,
            existing,
            tile_def,
            tile.footprint_width,
            tile.footprint_height,
        )
        return existing
    width_r, height_r = engine._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    rows = tile.walkable
    x, y = _walkable_edge_cell(rows, direction, width_r, height_r)
    status, door_open = _manifest_exit_status(manifest_status, kind)
    exit_state = engine._new_exit(
        direction=direction,
        kind=kind,
        width=width_r,
        height=height_r,
        status="blocked" if status == "blocked" else "open",
        exit_id=exit_id or f"{tile.id}-{direction}-reciprocal",
    )
    _apply_exit_geometry(engine, exit_state, x, y, width_r, height_r)
    _apply_manifest_door_state(exit_state, manifest_status, kind)
    if kind == "door":
        exit_state.door_open = manifest_status == "open"
    else:
        exit_state.door_open = door_open
    tile.exits.append(exit_state)
    return exit_state


def _reciprocal_manifest_status(source_manifest: dict[str, Any]) -> str:
    return str(source_manifest.get("status", "open"))


def _ensure_reciprocal_exits_from_manifest(
    manifest: dict[str, Any],
    engine: RandomDungeonEngine,
    tiles_by_room: dict[str, TileState],
) -> None:
    rooms = _room_dict(manifest)
    for room_id, room in rooms.items():
        tile = tiles_by_room[room_id]
        tile_def = engine.rules.tiles().get(room["tile_key"])
        for manifest_exit in room.get("exits") or []:
            if not isinstance(manifest_exit, dict):
                continue
            target_id = manifest_exit.get("to")
            direction = manifest_exit.get("direction")
            if not isinstance(target_id, str) or target_id not in tiles_by_room:
                continue
            if not isinstance(direction, str):
                continue
            reciprocal_direction = OPPOSITE.get(direction, "south")
            target_tile = tiles_by_room[target_id]
            target_def = engine.rules.tiles().get(rooms[target_id]["tile_key"])
            kind = _manifest_exit_kind(str(manifest_exit.get("kind", "passage")))
            status = _reciprocal_manifest_status(manifest_exit)
            _ensure_direction_exit_on_tile(
                engine,
                target_tile,
                target_def,
                reciprocal_direction,
                kind=kind,
                manifest_status=status,
                exit_id=f"{target_id}-{reciprocal_direction}-from-{room_id}",
            )


def _layout_exit_for_direction(
    tile: TileState,
    direction: str,
) -> ExitState:
    existing = next((item for item in tile.exits if item.direction == direction and not item.dungeon_exit), None)
    if existing is not None:
        return existing
    width, height = tile.footprint_width, tile.footprint_height
    x, y = _walkable_edge_cell(tile.walkable, direction, width, height)
    return ExitState(direction=direction, kind="passage", x=x, y=y, status="open", door_open=True)


def _bbox_child_position(
    engine: RandomDungeonEngine,
    parent: TileState,
    child: TileState,
    parent_exit: ExitState,
    child_exit: ExitState,
    direction: str,
) -> tuple[int, int]:
    """Place child so its reciprocal portal lands on the parent portal's outside cell."""
    del direction
    _, parent_outside = engine._exit_edge(parent, parent_exit)
    child_at_origin = child.model_copy(update={"x": 0, "y": 0})
    child_inside, _ = engine._exit_edge(child_at_origin, child_exit)
    return parent_outside[0] - child_inside[0], parent_outside[1] - child_inside[1]


def _layout_rooms(
    manifest: dict[str, Any],
    engine: RandomDungeonEngine,
    tiles_by_room: dict[str, TileState],
) -> dict[str, tuple[int, int]]:
    rooms = _room_dict(manifest)
    entrance_id = manifest["entrance_room_id"]
    positions: dict[str, tuple[int, int]] = {entrance_id: (0, 0)}
    queue = [entrance_id]

    while queue:
        room_id = queue.pop(0)
        parent = tiles_by_room[room_id]
        px, py = positions[room_id]
        parent_placed = parent.model_copy(update={"x": px, "y": py})

        for exit_def in rooms[room_id].get("exits", []):
            if not isinstance(exit_def, dict):
                continue
            target_id = exit_def.get("to")
            if not isinstance(target_id, str) or target_id not in rooms:
                continue
            if target_id in positions:
                continue
            direction = str(exit_def.get("direction", "north"))
            exit_id = exit_def.get("id")
            parent_exit = next(
                (item for item in parent_placed.exits if item.id == exit_id),
                next((item for item in parent_placed.exits if item.direction == direction), None),
            )
            if parent_exit is None:
                continue
            child = tiles_by_room[target_id]
            reciprocal_direction = OPPOSITE.get(direction, "south")
            child_room = rooms[target_id]
            reciprocal_def = next(
                (
                    item
                    for item in child_room.get("exits", [])
                    if isinstance(item, dict) and item.get("direction") == reciprocal_direction
                ),
                None,
            )
            child_exit = None
            if isinstance(reciprocal_def, dict):
                reciprocal_id = reciprocal_def.get("id")
                child_exit = next(
                    (item for item in child.exits if item.id == reciprocal_id),
                    None,
                )
            if child_exit is None:
                child_exit = next(
                    (item for item in child.exits if item.direction == reciprocal_direction),
                    None,
                )
            if child_exit is None:
                child_exit = _layout_exit_for_direction(child, reciprocal_direction)
            positions[target_id] = _bbox_child_position(
                engine,
                parent_placed,
                child,
                parent_exit,
                child_exit,
                direction,
            )
            queue.append(target_id)

    for room_id in rooms:
        if room_id not in positions:
            positions[room_id] = (len(positions) * 8, 0)
    return positions


def _snap_portal_pair(
    engine: RandomDungeonEngine,
    tile_a: TileState,
    exit_a: ExitState,
    tile_b: TileState,
    exit_b: ExitState,
) -> None:
    """Align reciprocal portals by shifting the child tile — keep exit cells on tile artwork."""
    _, outside_a = engine._exit_edge(tile_a, exit_a)
    inside_b, _ = engine._exit_edge(tile_b, exit_b)
    tile_b.x += outside_a[0] - inside_b[0]
    tile_b.y += outside_a[1] - inside_b[1]


def _ensure_all_exits_walkable(engine: RandomDungeonEngine, tiles: list[TileState]) -> None:
    for tile in tiles:
        tile_def = engine.rules.tiles().get(tile.tile_key)
        width, height = tile.footprint_width, tile.footprint_height
        for exit_state in tile.exits:
            _ensure_exit_on_walkable(engine, exit_state, tile_def, width, height)


def _imported_layout_bfs_order(manifest: dict[str, Any]) -> list[str]:
    rooms = _room_dict(manifest)
    entrance_id = manifest["entrance_room_id"]
    order: list[str] = []
    queue = [entrance_id]
    seen = {entrance_id}
    while queue:
        room_id = queue.pop(0)
        order.append(room_id)
        for exit_def in rooms[room_id].get("exits", []):
            if not isinstance(exit_def, dict):
                continue
            target_id = exit_def.get("to")
            if isinstance(target_id, str) and target_id in rooms and target_id not in seen:
                seen.add(target_id)
                queue.append(target_id)
    for room_id in rooms:
        if room_id not in order:
            order.append(room_id)
    return order


def _resolve_manifest_connection_exits(
    parent: TileState,
    child: TileState,
    manifest_exit: dict[str, Any],
) -> tuple[ExitState | None, ExitState | None]:
    direction = str(manifest_exit.get("direction", "north"))
    exit_id = manifest_exit.get("id")
    parent_exit = next(
        (item for item in parent.exits if item.id == exit_id),
        next((item for item in parent.exits if item.direction == direction and not item.dungeon_exit), None),
    )
    reciprocal = OPPOSITE.get(direction, "south")
    child_exit = next(
        (item for item in child.exits if item.direction == reciprocal and not item.dungeon_exit),
        None,
    )
    return parent_exit, child_exit


def _apply_imported_walkable_truncation(
    engine: RandomDungeonEngine,
    manifest: dict[str, Any],
    tiles_by_room: dict[str, TileState],
) -> None:
    """Carve walkable grids at each link so doors meet like procedural map placement."""
    rooms = _room_dict(manifest)
    placed: set[str] = set()
    for room_id in _imported_layout_bfs_order(manifest):
        child = tiles_by_room[room_id]
        for parent_id in placed:
            parent = tiles_by_room[parent_id]
            for manifest_exit in rooms[parent_id].get("exits") or []:
                if not isinstance(manifest_exit, dict) or manifest_exit.get("to") != room_id:
                    continue
                parent_exit, child_exit = _resolve_manifest_connection_exits(parent, child, manifest_exit)
                if parent_exit is None or child_exit is None:
                    continue
                engine.carve_imported_neighbor_connection(parent, child, parent_exit, child_exit)
                engine.carve_imported_neighbor_connection(child, parent, child_exit, parent_exit)
        placed.add(room_id)


def _wire_imported_connections(
    manifest: dict[str, Any],
    rooms: dict[str, dict[str, Any]],
    engine: RandomDungeonEngine,
    tiles_by_room: dict[str, TileState],
    room_tile_ids: dict[str, str],
) -> None:
    _ = manifest
    tile_by_id = {tile.id: tile for tile in tiles_by_room.values()}
    for room_id, room in rooms.items():
        tile = tiles_by_room[room_id]
        for manifest_exit in room.get("exits") or []:
            if not isinstance(manifest_exit, dict):
                continue
            direction = manifest_exit.get("direction")
            target_room = manifest_exit.get("to")
            exit_id = manifest_exit.get("id")
            if not isinstance(target_room, str) or target_room not in room_tile_ids:
                continue
            exit_state = next(
                (item for item in tile.exits if item.id == exit_id),
                next((item for item in tile.exits if item.direction == direction), None),
            )
            if exit_state is None:
                continue
            exit_state.destination_tile_id = room_tile_ids[target_room]
            reciprocal_tile = tile_by_id[room_tile_ids[target_room]]
            reciprocal_direction = OPPOSITE.get(str(direction), "south")
            reciprocal = next(
                (
                    item
                    for item in reciprocal_tile.exits
                    if item.direction == reciprocal_direction and item.destination_tile_id in (None, tile.id)
                ),
                None,
            )
            if reciprocal is None:
                target_def = engine.rules.tiles().get(rooms[target_room]["tile_key"])
                reciprocal = _ensure_direction_exit_on_tile(
                    engine,
                    reciprocal_tile,
                    target_def,
                    reciprocal_direction,
                    kind=exit_state.kind,
                    manifest_status=str(manifest_exit.get("status", "open")),
                    exit_id=f"{target_room}-{reciprocal_direction}-from-{room_id}",
                )
            reciprocal.destination_tile_id = tile.id
            reciprocal.status = "open"
            if reciprocal.kind == "door" and exit_state.kind == "door":
                reciprocal.door_open = exit_state.door_open


def repair_stuck_imported_treasure(session: SessionState) -> bool:
    """Unstick manifest loot added after a procedural combat treasure claim."""
    changed = False
    for tile in session.map_state.tiles:
        if tile.treasure_claimed and (tile.treasure_gold > 0 or tile.treasure_items):
            tile.treasure_claimed = False
            changed = True
    return changed


def repair_imported_map_layout(engine: RandomDungeonEngine, session: SessionState) -> bool:
    """Recompute imported adventure tile positions to fix footprint overlap hiding exits."""
    if session.adventure_type != "imported":
        return False
    manifest = session.imported_manifest
    if not isinstance(manifest, dict) or not manifest.get("rooms"):
        return False
    tiles_by_room: dict[str, TileState] = {}
    entrance_room_id = manifest.get("entrance_room_id")
    for tile in session.map_state.tiles:
        key = tile.content_key or ""
        if key == "entrance" and isinstance(entrance_room_id, str):
            tiles_by_room[entrance_room_id] = tile
            continue
        if key.startswith(IMPORTED_ROOM_PREFIX):
            tiles_by_room[key[len(IMPORTED_ROOM_PREFIX) :]] = tile
    if len(tiles_by_room) < 2:
        return False
    _ensure_reciprocal_exits_from_manifest(manifest, engine, tiles_by_room)
    rooms = _room_dict(manifest)
    room_tile_ids = {room_id: tile.id for room_id, tile in tiles_by_room.items()}
    _wire_imported_connections(manifest, rooms, engine, tiles_by_room, room_tile_ids)
    positions = _layout_rooms(manifest, engine, tiles_by_room)
    for room_id, tile in tiles_by_room.items():
        pos = positions.get(room_id)
        if pos is not None:
            tile.x, tile.y = pos
    _snap_connected_exits(engine, session.map_state.tiles)
    _apply_imported_walkable_truncation(engine, manifest, tiles_by_room)
    _ensure_all_exits_walkable(engine, session.map_state.tiles)
    return True


def _snap_connected_exits(engine: RandomDungeonEngine, tiles: list[TileState]) -> None:
    tile_by_id = {tile.id: tile for tile in tiles}
    seen: set[tuple[str, str]] = set()
    for tile in tiles:
        for exit_state in tile.exits:
            if not exit_state.destination_tile_id:
                continue
            other = tile_by_id.get(exit_state.destination_tile_id)
            if other is None:
                continue
            pair_key = tuple(sorted((tile.id, other.id)))
            if pair_key in seen:
                continue
            reciprocal_direction = OPPOSITE.get(exit_state.direction)
            reciprocal = next(
                (
                    item
                    for item in other.exits
                    if item.direction == reciprocal_direction and item.destination_tile_id == tile.id
                ),
                None,
            )
            if reciprocal is None:
                continue
            seen.add(pair_key)
            _snap_portal_pair(engine, tile, exit_state, other, reciprocal)


def enter_imported_entrance_tile(
    engine: RandomDungeonEngine,
    session: SessionState,
    entrance_tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    session.log.append(f"Entered {entrance_tile.title}: {entrance_tile.description}")
    fire_imported_triggers(engine, session, entrance_tile, "on_enter", show_rolls=show_rolls)
    if entrance_tile.enemies and session.mode == "exploration":
        engine._announce_encounter(session, entrance_tile, show_rolls=show_rolls)


def apply_start_camped_outside(engine: RandomDungeonEngine, session: SessionState) -> None:
    entrance = engine._entrance_tile(session)
    session.map_state.current_tile_id = entrance.id
    session.current_tile_entry_exit_id = None
    engine._refresh_tile_connections(session, entrance)
    engine._initialize_outside_entrance(entrance)
    session.mode = "exploration"
    session.camped_outside = True
    session.summary = []
    session.log.append("The party makes camp outside the dungeon entrance before entering.")
    session.log.append(
        "Hire retainers, bank gold, shop, or regroup, then (Re)enter Dungeon when ready."
    )


def create_session_from_manifest(
    engine: RandomDungeonEngine,
    session_id: str,
    party_id: str,
    party: list[PartyMemberState],
    manifest: dict[str, Any],
    *,
    adventure_id: str,
    xp_system: str = "classical",
    map_bounds_mode: str = "unlimited",
    unlimited_map_element_cap: int = 60,
    fiendish_foes_enabled: bool = True,
    start_camped_outside: bool = False,
) -> SessionState:
    rooms = _room_dict(manifest)
    room_tile_ids: dict[str, str] = {}
    tiles_by_room: dict[str, TileState] = {}
    default_environment = manifest.get("default_environment", "dungeon")
    exit_room_id = manifest.get("exit_room_id")

    for room_id, room in rooms.items():
        tile_def = engine.rules.tiles().get(room["tile_key"])
        width = tile_def.footprint_width if tile_def else 1
        height = tile_def.footprint_height if tile_def else 1
        tile_type = engine._tile_type(tile_def.tile_type if tile_def else "room")
        tile_id = uuid4().hex
        room_tile_ids[room_id] = tile_id
        is_entrance = room_id == manifest["entrance_room_id"]
        is_exit = room_id == exit_room_id

        exits = _build_manifest_exits(engine, room, tile_def, width, height)

        trap = room.get("trap")
        trap_key = trap.get("key") if isinstance(trap, dict) else None
        trap_level = trap.get("level") if isinstance(trap, dict) else None
        special_event = room.get("special_event")
        special_event_key = special_event.get("key") if isinstance(special_event, dict) else None

        tile = TileState(
            id=tile_id,
            x=0,
            y=0,
            tile_key=room["tile_key"],
            tile_type=tile_type,
            rotation=0,
            footprint_width=width,
            footprint_height=height,
            editor_cell_size=tile_def.editor_cell_size if tile_def else 80,
            image_scale=tile_def.image_scale if tile_def else 1.0,
            image_offset_x=tile_def.image_offset_x if tile_def else 0,
            image_offset_y=tile_def.image_offset_y if tile_def else 0,
            walkable=engine._normalized_walkable(tile_def, width, height),
            cell_shapes=engine._normalized_cell_shapes(tile_def, width, height),
            visible=engine._visible_rows(width, height),
            image=engine._tile_image(room["tile_key"], tile_def.image if tile_def else None),
            title=room.get("title", room_id),
            description=room.get("description", ""),
            content_key="entrance" if is_entrance else f"{IMPORTED_ROOM_PREFIX}{room_id}",
            objects=["Entrance"] if is_entrance else [],
            exits=exits,
            environment=room.get("environment") or default_environment,
            terrain=(
                "outdoor"
                if is_entrance
                else room.get("terrain") or (tile_def.terrain if tile_def else "indoor")
            ),
            trap_key=trap_key,
            trap_level=int(trap_level) if isinstance(trap_level, int) else None,
            special_event_key=special_event_key,
            resolved=bool(room.get("starts_resolved")),
        )
        if is_entrance:
            _ensure_surface_entrance_exit(engine, tile)
        if is_exit:
            _ensure_dungeon_leave_exit(engine, tile)
        tiles_by_room[room_id] = tile

    _ensure_reciprocal_exits_from_manifest(manifest, engine, tiles_by_room)

    tiles = list(tiles_by_room.values())
    tile_by_id = {tile.id: tile for tile in tiles}
    room_tile_ids = {room_id: tile.id for room_id, tile in tiles_by_room.items()}
    _wire_imported_connections(manifest, rooms, engine, tiles_by_room, room_tile_ids)

    positions = _layout_rooms(manifest, engine, tiles_by_room)
    for room_id, tile in tiles_by_room.items():
        tile.x, tile.y = positions[room_id]
    _snap_connected_exits(engine, tiles)
    _apply_imported_walkable_truncation(engine, manifest, tiles_by_room)
    _ensure_all_exits_walkable(engine, tiles)

    entrance_tile_id = room_tile_ids[manifest["entrance_room_id"]]
    giver_room_id = manifest.get("quest", {}).get("giver_room_id") or manifest["entrance_room_id"]
    giver_tile_id = room_tile_ids.get(giver_room_id, entrance_tile_id)

    for index, member in enumerate(party, start=1):
        member.marching_order = index
        prune_weapon_defaults(member)

    valid_xp = {"classical", "slow_and_sure", "old_school", "slower_advancement"}
    chosen_xp = xp_system if xp_system in valid_xp else "classical"
    valid_bounds = {"unlimited", "paper"}
    chosen_bounds = map_bounds_mode if map_bounds_mode in valid_bounds else "unlimited"
    chosen_cap = normalize_unlimited_map_element_cap(unlimited_map_element_cap)
    map_width = max(31, max(tile.x + tile.footprint_width for tile in tiles) + 4)
    map_height = max(31, max(tile.y + tile.footprint_height for tile in tiles) + 4)
    if chosen_bounds == "paper":
        map_width = max(20, map_width)
        map_height = max(28, map_height)

    party_xp = [member.xp for member in party]
    tag_reference = tag_reference_from_manifest(manifest)
    if tag_reference:
        objective_text = str((manifest.get("quest") or {}).get("objective_text") or "").strip()
        log = [
            f"Adventure begins: {manifest.get('title', adventure_id)}.",
        ]
        if objective_text:
            log.append(f"Objective: {objective_text}")
    else:
        log = [
            f"Imported adventure: {manifest.get('title', adventure_id)}.",
            manifest.get("synopsis", ""),
            f"Campaign mode: {campaign_mode_label(chosen_xp)}.",
        ]
    starting_clues = sum(max(0, member.clues) for member in party)
    if starting_clues and not tag_reference:
        log.append(f"Party begins with {starting_clues} carried Clue(s).")
    prepare_adventure_expert_items(party, log)
    for member in party:
        snapshot_carry_baseline(member)
    chosen_fiendish = normalize_fiendish_foes_enabled(fiendish_foes_enabled)
    eligible = party_fiendish_foes_eligible(party)
    if not tag_reference:
        log.append(fiendish_foes_session_label(chosen_fiendish, eligible=eligible) + ".")

    timestamp = now_utc()
    entrance_tile = tile_by_id[entrance_tile_id]
    if entrance_tile.content_key == "entrance":
        engine._initialize_outside_entrance(entrance_tile, log=log)

    session = SessionState(
        id=session_id,
        party_id=party_id,
        adventure_id=adventure_id,
        adventure_type="imported",
        mode="exploration",
        party=party,
        map_state=MapState(
            width=map_width,
            height=map_height,
            tiles=tiles,
            current_tile_id=entrance_tile_id,
        ),
        log=[line for line in log if line],
        clues_found=starting_clues,
        xp_system=chosen_xp,
        map_bounds_mode=chosen_bounds,
        unlimited_map_element_cap=chosen_cap,
        fiendish_foes_enabled=chosen_fiendish,
        environment=entrance_tile.environment,
        old_school_xp_tally=initial_xp_tally(party_xp) if chosen_xp == "old_school" else 0,
        slower_xp_bank=initial_xp_tally(party_xp) if chosen_xp == "slower_advancement" else 0,
        created_at=timestamp,
        updated_at=timestamp,
        active_quest=quest_from_manifest(manifest, giver_tile_id=giver_tile_id),
        imported_fired_triggers=[],
        imported_exit_tile_id=exit_room_id or None,
        imported_manifest=manifest,
        imported_quest_complete_when=dict(manifest.get("quest", {}).get("complete_when") or {}),
    )
    mark_tile_visited(session, entrance_tile_id)
    if start_camped_outside:
        session.imported_entrance_pending = True
        apply_start_camped_outside(engine, session)
    else:
        enter_imported_entrance_tile(engine, session, entrance_tile, show_rolls=True)
    return session
