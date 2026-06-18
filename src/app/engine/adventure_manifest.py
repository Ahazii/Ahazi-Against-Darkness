from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..rules.repository import RulesRepository
from .adventure_allowlists import (
    COMPLETE_WHEN_TYPES,
    ENVIRONMENTS,
    EXIT_DIRECTIONS,
    EXIT_KINDS,
    EXIT_STATUSES,
    SOURCE_TYPES,
    TRIGGER_WHEN,
    build_adventure_allowlists,
    foe_names_for_validation,
)

SUPPORTED_SCHEMA_VERSION = 1
ADVENTURE_ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TILE_KEY_PATTERN = re.compile(r"^(0[1-6]|1[1-6]|2[1-6]|3[1-6]|4[1-6]|5[1-6]|6[1-6])$")

REQUIRED_ROOT_KEYS = (
    "schema_version",
    "id",
    "title",
    "synopsis",
    "source",
    "recommended_levels",
    "default_environment",
    "entrance_room_id",
    "exit_room_id",
    "quest",
    "rooms",
    "ending",
)

SOURCE_TYPES = set(SOURCE_TYPES)
COMPLETE_WHEN_TYPES = set(COMPLETE_WHEN_TYPES)
TRIGGER_WHEN = set(TRIGGER_WHEN)
EXIT_DIRECTIONS = set(EXIT_DIRECTIONS)
EXIT_KINDS = set(EXIT_KINDS)
EXIT_STATUSES = set(EXIT_STATUSES)

FORBIDDEN_TOP_LEVEL_KEYS = {"rules", "dice", "roll"}


@dataclass
class ManifestValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error_summary: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            joined = "; ".join(self.errors)
            raise ValueError(joined or "Adventure manifest is invalid.")


def load_adventure_manifest(path: Path | str) -> tuple[dict[str, Any] | None, ManifestValidationResult]:
    manifest_path = Path(path)
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, ManifestValidationResult(valid=False, errors=[f"Invalid JSON: {exc.msg}"])
    if not isinstance(raw, dict):
        return None, ManifestValidationResult(valid=False, errors=["Manifest root must be a JSON object."])
    result = validate_adventure_manifest(raw)
    if not result.valid:
        return None, result
    return raw, result


def validate_adventure_manifest(
    data: dict[str, Any],
    *,
    rules_repo: RulesRepository | None = None,
) -> ManifestValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if rules_repo is None:
        packaged = Path(__file__).resolve().parents[3] / "data" / "rules"
        rules_repo = RulesRepository(packaged, packaged / "_override")

    allowlists = build_adventure_allowlists(rules_repo)
    foe_names = foe_names_for_validation(allowlists)
    tile_keys = set(allowlists["tile_keys"])
    equipment_items = set(allowlists["equipment_items"])
    trap_keys = set(allowlists["trap_keys"])
    event_keys = set(allowlists["special_event_keys"])

    for forbidden in FORBIDDEN_TOP_LEVEL_KEYS:
        if forbidden in data:
            errors.append(f"Forbidden top-level key {forbidden!r}.")

    for key in REQUIRED_ROOT_KEYS:
        if key not in data:
            errors.append(f"Missing required field {key!r}.")

    schema_version = data.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version {schema_version!r}; expected {SUPPORTED_SCHEMA_VERSION}.")

    adventure_id = data.get("id")
    if not isinstance(adventure_id, str) or not ADVENTURE_ID_PATTERN.fullmatch(adventure_id):
        errors.append("id must be a lowercase slug (letters, digits, hyphens).")

    for text_key in ("title", "synopsis"):
        value = data.get(text_key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{text_key} must be a non-empty string.")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object.")
    else:
        source_type = source.get("type")
        if source_type not in SOURCE_TYPES:
            errors.append(f"source.type must be one of {sorted(SOURCE_TYPES)}.")

    recommended_levels = data.get("recommended_levels")
    if (
        not isinstance(recommended_levels, list)
        or len(recommended_levels) != 2
        or not all(isinstance(level, int) and level >= 1 for level in recommended_levels)
    ):
        errors.append("recommended_levels must be [min, max] with integers >= 1.")
    elif recommended_levels[0] > recommended_levels[1]:
        errors.append("recommended_levels[0] must be <= recommended_levels[1].")

    default_environment = data.get("default_environment")
    if default_environment not in ENVIRONMENTS:
        errors.append(f"default_environment must be one of {list(ENVIRONMENTS)}.")

    rooms = data.get("rooms")
    if not isinstance(rooms, list) or not rooms:
        errors.append("rooms must be a non-empty array.")
        return ManifestValidationResult(
            valid=False,
            errors=errors,
            warnings=warnings,
            error_summary=summarize_manifest_errors(errors),
        )

    room_ids: set[str] = set()
    exit_ids: set[str] = set()
    room_by_id: dict[str, dict[str, Any]] = {}

    for index, room in enumerate(rooms):
        prefix = f"rooms[{index}]"
        if not isinstance(room, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        room_id = room.get("id")
        if not isinstance(room_id, str) or not room_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string.")
            continue
        if room_id in room_ids:
            errors.append(f"Duplicate room id {room_id!r}.")
        room_ids.add(room_id)
        room_by_id[room_id] = room

        tile_key = room.get("tile_key")
        if not isinstance(tile_key, str) or not TILE_KEY_PATTERN.fullmatch(tile_key):
            errors.append(f"{prefix}.tile_key must be a valid map element key (01–06, 11–66).")
        elif tile_key not in tile_keys:
            errors.append(f"{prefix}.tile_key {tile_key!r} is not in tiles.json.")

        for text_key in ("title", "description"):
            if not isinstance(room.get(text_key), str):
                errors.append(f"{prefix}.{text_key} must be a string.")

        environment = room.get("environment")
        if environment is not None and environment not in ENVIRONMENTS:
            errors.append(f"{prefix}.environment must be one of {list(ENVIRONMENTS)}.")

        exits = room.get("exits")
        if not isinstance(exits, list):
            errors.append(f"{prefix}.exits must be an array.")
        else:
            for exit_index, exit_def in enumerate(exits):
                exit_prefix = f"{prefix}.exits[{exit_index}]"
                if not isinstance(exit_def, dict):
                    errors.append(f"{exit_prefix} must be an object.")
                    continue
                for required in ("id", "direction", "to", "kind", "status"):
                    if required not in exit_def:
                        errors.append(f"{exit_prefix} missing {required!r}.")
                exit_id = exit_def.get("id")
                if isinstance(exit_id, str):
                    if exit_id in exit_ids:
                        errors.append(f"Duplicate exit id {exit_id!r}.")
                    exit_ids.add(exit_id)
                direction = exit_def.get("direction")
                if direction not in EXIT_DIRECTIONS:
                    errors.append(f"{exit_prefix}.direction {direction!r} is invalid.")
                kind = exit_def.get("kind")
                if kind not in EXIT_KINDS:
                    errors.append(f"{exit_prefix}.kind {kind!r} is invalid.")
                status = exit_def.get("status")
                if status not in EXIT_STATUSES:
                    errors.append(f"{exit_prefix}.status {status!r} is invalid.")
                to_room = exit_def.get("to")
                if not isinstance(to_room, str) or not to_room.strip():
                    errors.append(f"{exit_prefix}.to must be a non-empty string.")

        triggers = room.get("triggers", [])
        if triggers is None:
            triggers = []
        if not isinstance(triggers, list):
            errors.append(f"{prefix}.triggers must be an array.")
        else:
            for trigger_index, trigger in enumerate(triggers):
                trigger_prefix = f"{prefix}.triggers[{trigger_index}]"
                _validate_trigger(
                    trigger,
                    trigger_prefix,
                    errors,
                    foe_names,
                    equipment_items,
                    event_keys,
                    trap_keys,
                )

        trap = room.get("trap")
        if trap is not None:
            _validate_trap_ref(trap, f"{prefix}.trap", errors, trap_keys)

        special_event = room.get("special_event")
        if special_event is not None:
            _validate_event_ref(special_event, f"{prefix}.special_event", errors, event_keys)

    entrance_room_id = data.get("entrance_room_id")
    exit_room_id = data.get("exit_room_id")
    for room_ref_key, label in (
        ("entrance_room_id", "entrance"),
        ("exit_room_id", "exit"),
    ):
        room_ref = data.get(room_ref_key)
        if not isinstance(room_ref, str) or not room_ref.strip():
            errors.append(f"{room_ref_key} must be a non-empty string.")
        elif room_ref not in room_ids:
            errors.append(f"{room_ref_key} {room_ref!r} does not match any room id.")

    if isinstance(entrance_room_id, str) and isinstance(exit_room_id, str) and entrance_room_id == exit_room_id:
        warnings.append("entrance_room_id and exit_room_id are the same room.")

    for index, room in enumerate(rooms):
        if not isinstance(room, dict):
            continue
        room_id = room.get("id")
        exits = room.get("exits", [])
        if not isinstance(exits, list):
            continue
        for exit_index, exit_def in enumerate(exits):
            if not isinstance(exit_def, dict):
                continue
            to_room = exit_def.get("to")
            if isinstance(to_room, str) and to_room not in room_ids:
                errors.append(
                    f"rooms[{index}].exits[{exit_index}].to {to_room!r} does not match any room id."
                )

    if isinstance(entrance_room_id, str) and entrance_room_id in room_ids:
        unreachable = _unreachable_room_ids(room_by_id, entrance_room_id)
        if unreachable:
            errors.append(
                "Graph is not connected from entrance; unreachable rooms: "
                + ", ".join(sorted(unreachable))
            )
        if isinstance(exit_room_id, str) and exit_room_id in unreachable:
            errors.append(f"exit_room_id {exit_room_id!r} is not reachable from entrance.")

    quest = data.get("quest")
    if not isinstance(quest, dict):
        errors.append("quest must be an object.")
    else:
        for key in ("key", "objective_text", "complete_when"):
            if key not in quest:
                errors.append(f"quest.{key} is required.")
        giver_room_id = quest.get("giver_room_id")
        if giver_room_id is not None and giver_room_id not in room_ids:
            errors.append(f"quest.giver_room_id {giver_room_id!r} does not match any room id.")
        complete_when = quest.get("complete_when")
        if isinstance(complete_when, dict):
            _validate_complete_when(complete_when, room_ids, foe_names, equipment_items, errors)
        else:
            errors.append("quest.complete_when must be an object.")

    npcs = data.get("npcs", [])
    if npcs is None:
        npcs = []
    if not isinstance(npcs, list):
        errors.append("npcs must be an array.")
    else:
        npc_ids: set[str] = set()
        for index, npc in enumerate(npcs):
            prefix = f"npcs[{index}]"
            if not isinstance(npc, dict):
                errors.append(f"{prefix} must be an object.")
                continue
            npc_id = npc.get("id")
            if not isinstance(npc_id, str) or not npc_id.strip():
                errors.append(f"{prefix}.id must be a non-empty string.")
            elif npc_id in npc_ids:
                errors.append(f"Duplicate npc id {npc_id!r}.")
            else:
                npc_ids.add(npc_id)
            for key in ("name", "room_id", "description"):
                if not isinstance(npc.get(key), str):
                    errors.append(f"{prefix}.{key} must be a string.")
            room_id = npc.get("room_id")
            if isinstance(room_id, str) and room_id not in room_ids:
                errors.append(f"{prefix}.room_id {room_id!r} does not match any room id.")

    ending = data.get("ending")
    if not isinstance(ending, dict):
        errors.append("ending must be an object.")
    else:
        for key in ("victory_text", "defeat_text"):
            if not isinstance(ending.get(key), str) or not str(ending.get(key)).strip():
                errors.append(f"ending.{key} must be a non-empty string.")

    return ManifestValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        error_summary=summarize_manifest_errors(errors),
    )


def summarize_manifest_errors(errors: list[str]) -> list[str]:
    """Collapse repetitive validation messages into a short checklist."""
    if not errors:
        return []

    import re
    from collections import Counter

    tile_key_count = 0
    exit_missing: Counter[str] = Counter()
    invalid_monsters: set[str] = set()
    invalid_items: set[str] = set()
    invalid_traps: set[str] = set()
    invalid_events: set[str] = set()
    invalid_exit_direction = False
    passthrough: list[str] = []

    for error in errors:
        if "tile_key must be a valid map element key" in error:
            tile_key_count += 1
            continue
        missing_exit = re.search(r"exits\[\d+\] missing '(\w+)'", error)
        if missing_exit:
            exit_missing[missing_exit.group(1)] += 1
            continue
        spawn = re.search(r"'([^']*)' is not a known foe spawn name", error)
        if spawn:
            invalid_monsters.add(spawn.group(1))
            continue
        if ".direction " in error and "is invalid" in error:
            invalid_exit_direction = True
            continue
        item = re.search(r"items\[\d+\] '([^']*)' is not a known equipment item", error)
        if item:
            invalid_items.add(item.group(1))
            continue
        trap = re.search(r"key '([^']*)' is not a known trap key", error)
        if trap:
            invalid_traps.add(trap.group(1))
            continue
        event = re.search(r"key '([^']*)' is not a known special event key", error)
        if event:
            invalid_events.add(event.group(1))
            continue
        if re.search(r"\.kind None is invalid", error) or re.search(r"\.status None is invalid", error):
            continue
        passthrough.append(error)

    summary: list[str] = []
    summary.extend(passthrough)
    if tile_key_count:
        summary.append(
            f"{tile_key_count} room(s) missing tile_key — each room needs a map tile id (e.g. \"11\", \"22\")."
        )
    for field, count in sorted(exit_missing.items()):
        summary.append(f"{count} exit(s) missing {field!r} (required on every exit).")
    if invalid_monsters:
        names = ", ".join(sorted(invalid_monsters))
        summary.append(f"Unknown foe names: {names}. Use exact strings from foe_spawn_names in the prompt.")
    if invalid_items:
        names = ", ".join(sorted(invalid_items))
        summary.append(f"Unknown treasure items: {names}. Use exact equipment names from the allowlist.")
    if invalid_traps:
        names = ", ".join(sorted(invalid_traps))
        summary.append(f"Unknown trap keys: {names}.")
    if invalid_exit_direction:
        summary.append(
            "Invalid exit direction(s) — use only north, south, east, west (no diagonals)."
        )
    if invalid_events:
        names = ", ".join(sorted(invalid_events))
        summary.append(f"Unknown special event keys: {names}.")
    return summary


def _validate_trigger(
    trigger: Any,
    prefix: str,
    errors: list[str],
    foe_names: set[str],
    equipment_items: set[str],
    event_keys: set[str],
    trap_keys: set[str],
) -> None:
    if not isinstance(trigger, dict):
        errors.append(f"{prefix} must be an object.")
        return
    when = trigger.get("when")
    if when not in TRIGGER_WHEN:
        errors.append(f"{prefix}.when {when!r} is invalid.")
    once = trigger.get("once", True)
    if not isinstance(once, bool):
        errors.append(f"{prefix}.once must be a boolean.")

    encounter = trigger.get("encounter")
    if encounter is not None:
        if not isinstance(encounter, dict):
            errors.append(f"{prefix}.encounter must be an object.")
        else:
            foes = encounter.get("foes")
            if not isinstance(foes, list) or not foes:
                errors.append(f"{prefix}.encounter.foes must be a non-empty array.")
            else:
                for foe_index, foe in enumerate(foes):
                    foe_prefix = f"{prefix}.encounter.foes[{foe_index}]"
                    if not isinstance(foe, dict):
                        errors.append(f"{foe_prefix} must be an object.")
                        continue
                    name = foe.get("name")
                    count = foe.get("count")
                    if not isinstance(name, str) or name not in foe_names:
                        errors.append(
                            f"{foe_prefix}.name {name!r} is not a known foe spawn name."
                        )
                    if not isinstance(count, int) or count < 1:
                        errors.append(f"{foe_prefix}.count must be an integer >= 1.")
                    extra_keys = set(foe) - {"name", "count"}
                    if extra_keys:
                        errors.append(f"{foe_prefix} has unsupported fields: {sorted(extra_keys)}.")

    treasure = trigger.get("treasure")
    if treasure is not None:
        _validate_treasure(treasure, f"{prefix}.treasure", errors, equipment_items)

    special_event = trigger.get("special_event")
    if special_event is not None:
        _validate_event_ref(special_event, f"{prefix}.special_event", errors, event_keys)

    trap = trigger.get("trap")
    if trap is not None:
        _validate_trap_ref(trap, f"{prefix}.trap", errors, trap_keys)

    log = trigger.get("log")
    if log is not None and not isinstance(log, str):
        errors.append(f"{prefix}.log must be a string.")


def _validate_treasure(
    treasure: Any,
    prefix: str,
    errors: list[str],
    equipment_items: set[str],
) -> None:
    if not isinstance(treasure, dict):
        errors.append(f"{prefix} must be an object.")
        return
    gold = treasure.get("gold", 0)
    if not isinstance(gold, int) or gold < 0:
        errors.append(f"{prefix}.gold must be an integer >= 0.")
    items = treasure.get("items", [])
    if items is None:
        items = []
    if not isinstance(items, list):
        errors.append(f"{prefix}.items must be an array.")
    else:
        for item_index, item_name in enumerate(items):
            if not isinstance(item_name, str) or item_name not in equipment_items:
                errors.append(
                    f"{prefix}.items[{item_index}] {item_name!r} is not a known equipment item."
                )


def _validate_trap_ref(
    trap: Any,
    prefix: str,
    errors: list[str],
    trap_keys: set[str],
) -> None:
    if not isinstance(trap, dict):
        errors.append(f"{prefix} must be an object.")
        return
    key = trap.get("key")
    if not isinstance(key, str) or key not in trap_keys:
        errors.append(f"{prefix}.key {key!r} is not a known trap key.")
    level = trap.get("level")
    if level is not None and (not isinstance(level, int) or level < 1):
        errors.append(f"{prefix}.level must be an integer >= 1 when present.")


def _validate_event_ref(
    event: Any,
    prefix: str,
    errors: list[str],
    event_keys: set[str],
) -> None:
    if not isinstance(event, dict):
        errors.append(f"{prefix} must be an object.")
        return
    key = event.get("key")
    if not isinstance(key, str) or key not in event_keys:
        errors.append(f"{prefix}.key {key!r} is not a known special event key.")


def _validate_complete_when(
    complete_when: dict[str, Any],
    room_ids: set[str],
    foe_names: set[str],
    equipment_items: set[str],
    errors: list[str],
) -> None:
    complete_type = complete_when.get("type")
    if complete_type not in COMPLETE_WHEN_TYPES:
        errors.append(f"quest.complete_when.type {complete_type!r} is invalid.")
        return

    if complete_type == "boss_defeated":
        boss_name = complete_when.get("boss_name")
        if not isinstance(boss_name, str) or boss_name not in foe_names:
            errors.append(f"quest.complete_when.boss_name {boss_name!r} is not a known foe spawn name.")
        room_id = complete_when.get("room_id")
        if room_id is not None and room_id not in room_ids:
            errors.append(f"quest.complete_when.room_id {room_id!r} does not match any room id.")

    elif complete_type == "item_collected":
        item_name = complete_when.get("item_name")
        if not isinstance(item_name, str) or item_name not in equipment_items:
            errors.append(f"quest.complete_when.item_name {item_name!r} is not a known equipment item.")

    elif complete_type == "room_reached":
        room_id = complete_when.get("room_id")
        if not isinstance(room_id, str) or room_id not in room_ids:
            errors.append(f"quest.complete_when.room_id {room_id!r} does not match any room id.")

    elif complete_type == "peaceful_count":
        peaceful_required = complete_when.get("peaceful_required")
        if not isinstance(peaceful_required, int) or peaceful_required < 1:
            errors.append("quest.complete_when.peaceful_required must be an integer >= 1.")


def _unreachable_room_ids(room_by_id: dict[str, dict[str, Any]], entrance_room_id: str) -> set[str]:
    visited: set[str] = set()
    queue = [entrance_room_id]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        room = room_by_id.get(current)
        if not isinstance(room, dict):
            continue
        exits = room.get("exits", [])
        if not isinstance(exits, list):
            continue
        for exit_def in exits:
            if not isinstance(exit_def, dict):
                continue
            neighbor = exit_def.get("to")
            if isinstance(neighbor, str) and neighbor in room_by_id and neighbor not in visited:
                queue.append(neighbor)
    return set(room_by_id) - visited
