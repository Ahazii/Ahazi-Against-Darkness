from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..db import now_utc
from ..schemas import ActiveQuestState, ExitState, MapState, PartyMemberState, SessionState, TileState
from .adventure_runtime import IMPORTED_ROOM_PREFIX, fire_imported_triggers, quest_from_manifest
from .experience import campaign_mode_label
from .roster_sync import initial_xp_tally
from .expert_skill_effects import prepare_adventure_expert_items
from .heroic_skill_effects import mark_tile_visited
from .inventory import snapshot_carry_baseline
from .weapons import prune_weapon_defaults

if True:
    from .random_dungeon import OPPOSITE, RandomDungeonEngine

PLACEMENT_GAP = 0
SURFACE_EXIT_DIRECTIONS = ("south", "north", "west", "east")


def _room_dict(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {room["id"]: room for room in manifest.get("rooms", []) if isinstance(room, dict) and room.get("id")}


def _neighbor_position(
    parent_x: int,
    parent_y: int,
    parent_w: int,
    parent_h: int,
    child_w: int,
    child_h: int,
    direction: str,
) -> tuple[int, int]:
    if direction == "north":
        return parent_x, parent_y - child_h
    if direction == "south":
        return parent_x, parent_y + parent_h
    if direction == "east":
        return parent_x + parent_w, parent_y
    if direction == "west":
        return parent_x - child_w, parent_y
    return parent_x, parent_y


def _manifest_exit_kind(kind: str) -> str:
    return "door" if kind in {"door", "secret", "stairs"} else "passage"


def _manifest_exit_status(manifest_status: str, kind: str) -> tuple[str, bool]:
    if manifest_status == "blocked":
        return "blocked", False
    if manifest_status == "open":
        return "open", kind == "passage" or manifest_status == "open"
    return "open", False


def _exit_from_tile_def(
    engine: RandomDungeonEngine,
    tile_def,
    direction: str,
) -> ExitState | None:
    if tile_def is None:
        return None
    for exit_state in engine._rotated_exits(tile_def, 0):
        if exit_state.direction == direction:
            return exit_state.model_copy(deep=True)
    return None


def _build_manifest_exits(
    engine: RandomDungeonEngine,
    room: dict[str, Any],
    tile_def,
    width: int,
    height: int,
) -> list[ExitState]:
    width_r, height_r = engine._rotated_size(width, height, 0)
    exits: list[ExitState] = []
    for manifest_exit in room.get("exits") or []:
        if not isinstance(manifest_exit, dict):
            continue
        direction = str(manifest_exit.get("direction", "north"))
        kind = _manifest_exit_kind(str(manifest_exit.get("kind", "passage")))
        status, door_open = _manifest_exit_status(str(manifest_exit.get("status", "open")), kind)
        exit_state = _exit_from_tile_def(engine, tile_def, direction)
        if exit_state is None:
            exit_state = engine._new_exit(
                direction=direction,
                kind=kind,
                width=width_r,
                height=height_r,
                status="blocked" if status == "blocked" else "open",
                exit_id=str(manifest_exit.get("id") or uuid4().hex),
            )
        exit_state.id = str(manifest_exit.get("id") or exit_state.id)
        exit_state.kind = kind
        if status != "unexplored":
            exit_state.status = status
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
    width, height = engine._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    direction = _unused_direction(tile)
    surface_exit = engine._new_exit(
        direction=direction,
        kind="passage",
        width=width,
        height=height,
        status="open",
        dungeon_exit=True,
        exit_id=f"{tile.id}-surface",
    )
    surface_exit.door_open = True
    tile.exits.append(surface_exit)


def _ensure_dungeon_leave_exit(engine: RandomDungeonEngine, tile: TileState) -> None:
    if any(exit_state.dungeon_exit for exit_state in tile.exits):
        return
    width, height = engine._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    direction = _unused_direction(tile)
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
    leave_exit.door_open = True
    tile.exits.append(leave_exit)


def _layout_rooms(manifest: dict[str, Any], engine: RandomDungeonEngine) -> dict[str, tuple[int, int]]:
    rooms = _room_dict(manifest)
    entrance_id = manifest["entrance_room_id"]
    positions: dict[str, tuple[int, int]] = {entrance_id: (0, 0)}
    queue = [entrance_id]
    visited = {entrance_id}

    while queue:
        room_id = queue.pop(0)
        room = rooms[room_id]
        px, py = positions[room_id]
        parent_def = engine.rules.tiles().get(room["tile_key"])
        parent_w = parent_def.footprint_width if parent_def else 1
        parent_h = parent_def.footprint_height if parent_def else 1

        for exit_def in room.get("exits", []):
            if not isinstance(exit_def, dict):
                continue
            target_id = exit_def.get("to")
            if not isinstance(target_id, str) or target_id not in rooms:
                continue
            if target_id in positions:
                continue
            child = rooms[target_id]
            child_def = engine.rules.tiles().get(child["tile_key"])
            child_w = child_def.footprint_width if child_def else 1
            child_h = child_def.footprint_height if child_def else 1
            direction = exit_def.get("direction", "north")
            cx, cy = _neighbor_position(px, py, parent_w, parent_h, child_w, child_h, direction)
            positions[target_id] = (cx, cy)
            if target_id not in visited:
                visited.add(target_id)
                queue.append(target_id)

    for room_id in rooms:
        positions.setdefault(room_id, (len(positions) * 3, 0))
    return positions


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
) -> SessionState:
    rooms = _room_dict(manifest)
    positions = _layout_rooms(manifest, engine)
    room_tile_ids: dict[str, str] = {}
    tiles: list[TileState] = []
    default_environment = manifest.get("default_environment", "dungeon")
    exit_room_id = manifest.get("exit_room_id")

    for room_id, room in rooms.items():
        tile_def = engine.rules.tiles().get(room["tile_key"])
        width = tile_def.footprint_width if tile_def else 1
        height = tile_def.footprint_height if tile_def else 1
        tile_type = engine._tile_type(tile_def.tile_type if tile_def else "room")
        x, y = positions[room_id]
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
            x=x,
            y=y,
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
            terrain=tile_def.terrain if tile_def else "indoor",
            trap_key=trap_key,
            trap_level=int(trap_level) if isinstance(trap_level, int) else None,
            special_event_key=special_event_key,
            resolved=bool(room.get("starts_resolved")),
        )
        if is_entrance:
            _ensure_surface_entrance_exit(engine, tile)
        if is_exit:
            _ensure_dungeon_leave_exit(engine, tile)
        tiles.append(tile)

    tile_by_id = {tile.id: tile for tile in tiles}
    for room_id, room in rooms.items():
        tile = next(item for item in tiles if item.id == room_tile_ids[room_id])
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
                reciprocal = next(
                    (item for item in reciprocal_tile.exits if item.direction == reciprocal_direction),
                    None,
                )
            if reciprocal is not None:
                reciprocal.destination_tile_id = tile.id
                reciprocal.status = "open"
                if reciprocal.kind == "door":
                    reciprocal.door_open = exit_state.door_open

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
    map_width = max(31, max(tile.x + tile.footprint_width for tile in tiles) + 4)
    map_height = max(31, max(tile.y + tile.footprint_height for tile in tiles) + 4)
    if chosen_bounds == "paper":
        map_width = max(20, map_width)
        map_height = max(28, map_height)

    party_xp = [member.xp for member in party]
    log = [
        f"Imported adventure: {manifest.get('title', adventure_id)}.",
        manifest.get("synopsis", ""),
        f"Campaign mode: {campaign_mode_label(chosen_xp)}.",
    ]
    starting_clues = sum(max(0, member.clues) for member in party)
    if starting_clues:
        log.append(f"Party begins with {starting_clues} carried Clue(s).")
    prepare_adventure_expert_items(party, log)
    for member in party:
        snapshot_carry_baseline(member)

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
    session.log.append(f"Entered {entrance_tile.title}: {entrance_tile.description}")
    fire_imported_triggers(engine, session, entrance_tile, "on_enter", show_rolls=True)
    if entrance_tile.enemies and session.mode == "exploration":
        engine._announce_encounter(session, entrance_tile, show_rolls=True)
    return session
