from __future__ import annotations

import re
from typing import Any

from ..schemas import AdventurePromptParameters
from .adventure_allowlists import build_boss_spawn_names
from .adventure_tile_catalog import OPPOSITE, build_tile_catalog, pick_tile_key
from ..rules.repository import RulesRepository

from .adventure_prompt import LENGTH_ROOM_BOUNDS

# (from_room, direction, to_room) — reciprocal edges implied
SHORT_GRAPH_EDGES: tuple[tuple[str, str, str], ...] = (
    ("room-entrance", "north", "room-hall"),
    ("room-entrance", "east", "room-side-a"),
    ("room-hall", "north", "room-hub"),
    ("room-hub", "east", "room-side-b"),
    ("room-hub", "north", "room-approach"),
    ("room-approach", "north", "room-boss"),
    ("room-approach", "east", "room-exit"),
)

MEDIUM_GRAPH_EDGES: tuple[tuple[str, str, str], ...] = SHORT_GRAPH_EDGES + (
    ("room-side-a", "north", "room-alcove"),
    ("room-hall", "west", "room-storage"),
    ("room-hub", "west", "room-gallery"),
)

LONG_GRAPH_EDGES: tuple[tuple[str, str, str], ...] = MEDIUM_GRAPH_EDGES + (
    ("room-alcove", "east", "room-crypt"),
    ("room-storage", "south", "room-pit"),
    ("room-gallery", "north", "room-shrine"),
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "adventure"


def _graph_for_length(length: str) -> tuple[tuple[str, str, str], ...]:
    if length == "long":
        return LONG_GRAPH_EDGES
    if length == "medium":
        return MEDIUM_GRAPH_EDGES
    return SHORT_GRAPH_EDGES


def _room_exit_map(edges: tuple[tuple[str, str, str], ...]) -> dict[str, dict[str, str]]:
    """room_id -> {direction: to_room_id}"""
    rooms: dict[str, dict[str, str]] = {}
    for from_room, direction, to_room in edges:
        rooms.setdefault(from_room, {})[direction] = to_room
        rooms.setdefault(to_room, {})
    return rooms


def _assign_tile_keys(
    room_exit_map: dict[str, dict[str, str]],
    catalog: dict[str, Any],
    *,
    entrance_id: str,
    exit_id: str,
) -> dict[str, str]:
    assigned: dict[str, str] = {}
    used: set[str] = set()
    for room_id in sorted(room_exit_map, key=lambda rid: (-len(room_exit_map[rid]), rid)):
        required = set(room_exit_map[room_id])
        prefer = "room" if len(required) >= 2 else None
        prefer_role = None
        if room_id in (entrance_id, exit_id):
            prefer_role = "entrance_surface"
        else:
            prefer_role = "dungeon_interior"
        tile_key = pick_tile_key(
            required,
            catalog,
            used_keys=used,
            prefer_type=prefer,
            prefer_role=prefer_role,
        )
        if tile_key is None:
            tile_key = pick_tile_key(required, catalog, used_keys=set())
        if tile_key is None:
            raise ValueError(f"Cannot assign tile_key for room {room_id!r} (needs {sorted(required)}).")
        assigned[room_id] = tile_key
        used.add(tile_key)
    for room_id, tile_key in list(assigned.items()):
        extra = 0
        if room_id == entrance_id:
            extra += 1
        if room_id == exit_id:
            extra += 1
        native = set(catalog["tiles"][tile_key]["native_exit_directions"])
        if len(room_exit_map[room_id]) + extra > len(native):
            required = set(room_exit_map[room_id])
            replacement = pick_tile_key(required, catalog, used_keys=set())
            if replacement:
                assigned[room_id] = replacement
    return assigned


def _room_titles(room_id: str, tile_key: str, catalog: dict[str, Any]) -> tuple[str, str]:
    label = room_id.removeprefix("room-").replace("-", " ").title()
    shape = catalog["tiles"][tile_key]["shape_summary"]
    geometry = shape.split(". Use only")[0].strip()
    description = f"TODO: Expand this room — {geometry}."
    return label, description


def generate_adventure_skeleton(
    parameters: AdventurePromptParameters,
    *,
    repo: RulesRepository,
) -> dict[str, Any]:
    min_rooms, max_rooms = LENGTH_ROOM_BOUNDS[parameters.length]
    edges = _graph_for_length(parameters.length)
    room_exit_map = _room_exit_map(edges)
    if not (min_rooms <= len(room_exit_map) <= max_rooms):
        raise ValueError(
            f"Skeleton graph has {len(room_exit_map)} rooms; {parameters.length} requires {min_rooms}–{max_rooms}."
        )

    catalog = build_tile_catalog(repo)
    adventure_id = _slugify(parameters.theme)[:48]
    entrance_id = "room-entrance"
    exit_id = "room-exit"
    boss_id = "room-boss"
    tile_keys = _assign_tile_keys(room_exit_map, catalog, entrance_id=entrance_id, exit_id=exit_id)

    rooms: list[dict[str, Any]] = []
    for room_id in sorted(room_exit_map):
        title, description = _room_titles(room_id, tile_keys[room_id], catalog)
        exits: list[dict[str, Any]] = []
        for direction, to_room in sorted(room_exit_map[room_id].items()):
            native_kind = catalog["tiles"][tile_keys[room_id]]["native_exits"].get(direction, "passage")
            manifest_kind = "door" if native_kind == "door" else "passage"
            status = "closed" if manifest_kind == "door" else "open"
            exits.append(
                {
                    "id": f"{room_id}-{direction}",
                    "direction": direction,
                    "to": to_room,
                    "kind": manifest_kind,
                    "status": status,
                }
            )
        room: dict[str, Any] = {
            "id": room_id,
            "tile_key": tile_keys[room_id],
            "title": title,
            "description": description,
            "exits": exits,
            "triggers": [],
        }
        if room_id == boss_id:
            room["triggers"] = [
                {
                    "when": "on_enter",
                    "once": True,
                    "encounter": {"foes": [{"name": parameters.boss_type, "count": 1}]},
                }
            ]
        rooms.append(room)

    return {
        "schema_version": 1,
        "id": adventure_id,
        "title": f"TODO: Title for {parameters.theme}",
        "synopsis": f"TODO: Synopsis for {parameters.theme}.",
        "source": {
            "type": "ai",
            "parameters": parameters.model_dump(),
        },
        "recommended_levels": [parameters.party_level_min, parameters.party_level_max],
        "default_environment": parameters.environment,
        "entrance_room_id": entrance_id,
        "exit_room_id": exit_id,
        "quest": {
            "key": "slay_all",
            "objective_text": f"TODO: Defeat the {parameters.boss_type}.",
            "giver_room_id": entrance_id,
            "complete_when": {
                "type": "boss_defeated",
                "boss_name": parameters.boss_type,
                "room_id": boss_id,
            },
        },
        "npcs": [
            {
                "id": "quest-giver",
                "name": "TODO NPC",
                "room_id": entrance_id,
                "description": "TODO: Who sends the party in?",
                "dialogue": "TODO: Quest hook dialogue.",
            }
        ],
        "rooms": rooms,
        "ending": {
            "victory_text": "TODO: Victory text.",
            "defeat_text": "TODO: Defeat text.",
        },
        "_skeleton_notes": [
            "Fill every TODO field with original prose.",
            "Do not change room ids, tile_key values, or exit directions/to targets.",
            "Room descriptions must match each tile's shape_summary and walkable_map in TILE CATALOG.",
            "Only use exit directions listed in native_exit_ports for that tile_key.",
            "Add encounters/treasure/traps only using allowlisted keys.",
            f"Boss room is {boss_id}; finale must include {parameters.boss_type!r}.",
        ],
    }
