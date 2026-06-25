from __future__ import annotations

from typing import Any

from ..rules.repository import RulesRepository, VALID_TILE_KEYS

BOSS_TABLE_KEYS = [
    "boss",
    "caverns_boss",
    "fungal_grottoes_boss",
    "fiendish_foes_boss",
]

MAJOR_FOE_TABLE_KEYS = [
    "weird",
    "boss",
    "caverns_weird",
    "caverns_boss",
    "fungal_grottoes_weird",
    "fungal_grottoes_boss",
    "fiendish_foes_weird",
    "fiendish_foes_boss",
]


def major_foe_table_keys(monsters: dict[str, Any]) -> list[str]:
    """All weird/boss tables for Arrow of Slaying and similar 'any Major Foe table' rolls."""
    eligible: list[str] = []
    for key in MAJOR_FOE_TABLE_KEYS:
        table = monsters.get(key)
        if isinstance(table, list) and table:
            eligible.append(key)
    return eligible


MONSTER_TABLE_KEYS = [
    "vermin",
    "minions",
    "weird",
    "boss",
    "caverns_vermin",
    "caverns_minions",
    "caverns_weird",
    "caverns_boss",
    "fungal_grottoes_vermin",
    "fungal_grottoes_minions",
    "fungal_grottoes_weird",
    "fungal_grottoes_boss",
    "fiendish_foes_vermin",
    "fiendish_foes_minions",
    "fiendish_foes_boss",
    "fiendish_foes_weird",
    "wandering",
]

TRAP_TABLE_KEYS = [
    "trap_table",
    "caverns_trap_table",
    "fungal_grottoes_trap_table",
]

SPECIAL_EVENT_TABLE_KEYS = [
    "dungeon_special_events_table",
    "caverns_special_events_table",
    "fungal_grottoes_special_events_table",
]

ENVIRONMENTS = ("dungeon", "caverns", "fungal_grottoes")

ENVIRONMENT_MONSTER_TABLES: dict[str, tuple[str, ...]] = {
    "dungeon": ("vermin", "minions", "weird", "boss", "wandering"),
    "caverns": (
        "caverns_vermin",
        "caverns_minions",
        "caverns_weird",
        "caverns_boss",
        "wandering",
    ),
    "fungal_grottoes": (
        "fungal_grottoes_vermin",
        "fungal_grottoes_minions",
        "fungal_grottoes_weird",
        "fungal_grottoes_boss",
        "wandering",
    ),
}

ENVIRONMENT_TRAP_TABLES: dict[str, str] = {
    "dungeon": "trap_table",
    "caverns": "caverns_trap_table",
    "fungal_grottoes": "fungal_grottoes_trap_table",
}

ENVIRONMENT_EVENT_TABLES: dict[str, str] = {
    "dungeon": "dungeon_special_events_table",
    "caverns": "caverns_special_events_table",
    "fungal_grottoes": "fungal_grottoes_special_events_table",
}

QUEST_KEYS = (
    "bring_head",
    "bring_gold",
    "bring_alive",
    "bring_item",
    "peaceful_way",
    "slay_all",
)

# Closed schema enums — validator and prompt must share these exactly.
EXIT_DIRECTIONS = (
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
)
EXIT_KINDS = ("door", "passage", "secret", "stairs", "chute")
EXIT_STATUSES = ("open", "closed", "locked", "blocked")
TRIGGER_WHEN = ("on_enter", "on_search", "on_treasure", "on_feature")
SOURCE_TYPES = ("ai", "pdf", "hand")
COMPLETE_WHEN_TYPES = (
    "boss_defeated",
    "item_collected",
    "room_reached",
    "peaceful_count",
)


def _table_row_keys(table: list[dict[str, Any]], field: str = "key") -> set[str]:
    keys: set[str] = set()
    for row in table:
        if not isinstance(row, dict):
            continue
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            keys.add(value.strip())
    return keys


def _monster_names_from_tables(
    monsters: dict[str, Any],
    table_keys: tuple[str, ...] | list[str],
) -> list[str]:
    names: set[str] = set()
    for table_key in table_keys:
        for entry in monsters.get(table_key, []):
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str) and name.strip():
                    names.add(name.strip())
    return sorted(names)


def build_boss_spawn_names(repo: RulesRepository) -> list[str]:
    monsters = repo.monsters()
    return _monster_names_from_tables(monsters, BOSS_TABLE_KEYS)


def build_monsters_by_table(repo: RulesRepository) -> dict[str, list[str]]:
    monsters = repo.monsters()
    grouped: dict[str, list[str]] = {}
    for table_key in MONSTER_TABLE_KEYS:
        names = _monster_names_from_tables(monsters, (table_key,))
        if names:
            grouped[table_key] = names
    return grouped


def build_equipment_by_category(repo: RulesRepository) -> dict[str, list[str]]:
    equipment = repo.equipment_shop()
    grouped: dict[str, set[str]] = {}
    for item in equipment.get("items", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        category = item.get("category", "other")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(category, str) or not category.strip():
            category = "other"
        grouped.setdefault(category.strip(), set()).add(name.strip())
    return {key: sorted(values) for key, values in sorted(grouped.items())}


def build_environment_pack(
    repo: RulesRepository,
    environment: str,
) -> dict[str, list[str]]:
    if environment not in ENVIRONMENTS:
        environment = "dungeon"
    monsters = repo.monsters()
    tables = repo.dungeon_tables()
    monster_tables = ENVIRONMENT_MONSTER_TABLES[environment]
    trap_table = ENVIRONMENT_TRAP_TABLES[environment]
    event_table = ENVIRONMENT_EVENT_TABLES[environment]
    return {
        "environment": environment,
        "foe_names": _monster_names_from_tables(monsters, monster_tables),
        "trap_keys": sorted(_table_row_keys(tables.get(trap_table, []), field="trap_key")),
        "special_event_keys": sorted(_table_row_keys(tables.get(event_table, []), field="key")),
    }


def build_adventure_allowlists(
    repo: RulesRepository,
    *,
    environment: str | None = None,
) -> dict[str, Any]:
    monsters = repo.monsters()
    monster_names = set(_monster_names_from_tables(monsters, MONSTER_TABLE_KEYS))
    boss_names = set(build_boss_spawn_names(repo))
    foe_spawn_names = sorted(monster_names | boss_names)

    tables = repo.dungeon_tables()
    trap_keys: set[str] = set()
    for table_key in TRAP_TABLE_KEYS:
        trap_keys |= _table_row_keys(tables.get(table_key, []), field="trap_key")

    event_keys: set[str] = set()
    for table_key in SPECIAL_EVENT_TABLE_KEYS:
        event_keys |= _table_row_keys(tables.get(table_key, []), field="key")

    equipment = repo.equipment_shop()
    item_names: set[str] = set()
    for item in equipment.get("items", []):
        if isinstance(item, dict):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                item_names.add(name.strip())

    payload: dict[str, Any] = {
        "schema_version": 1,
        "source": "live_rules",
        "schema_enums": {
            "exit_directions": list(EXIT_DIRECTIONS),
            "exit_kinds": list(EXIT_KINDS),
            "exit_statuses": list(EXIT_STATUSES),
            "trigger_when": list(TRIGGER_WHEN),
            "source_types": list(SOURCE_TYPES),
            "quest_complete_when_types": list(COMPLETE_WHEN_TYPES),
            "quest_keys": list(QUEST_KEYS),
            "environments": list(ENVIRONMENTS),
        },
        "exit_directions": list(EXIT_DIRECTIONS),
        "exit_kinds": list(EXIT_KINDS),
        "exit_statuses": list(EXIT_STATUSES),
        "trigger_when": list(TRIGGER_WHEN),
        "source_types": list(SOURCE_TYPES),
        "quest_complete_when_types": list(COMPLETE_WHEN_TYPES),
        "quest_keys": list(QUEST_KEYS),
        "environments": list(ENVIRONMENTS),
        "monster_spawn_names": sorted(monster_names),
        "boss_spawn_names": sorted(boss_names),
        "foe_spawn_names": foe_spawn_names,
        "monsters_by_table": build_monsters_by_table(repo),
        "tile_keys": list(VALID_TILE_KEYS),
        "equipment_items": sorted(item_names),
        "equipment_by_category": build_equipment_by_category(repo),
        "trap_keys": sorted(trap_keys),
        "special_event_keys": sorted(event_keys),
        "traps_by_table": {
            table_key: sorted(_table_row_keys(tables.get(table_key, []), field="trap_key"))
            for table_key in TRAP_TABLE_KEYS
            if tables.get(table_key)
        },
        "events_by_table": {
            table_key: sorted(_table_row_keys(tables.get(table_key, []), field="key"))
            for table_key in SPECIAL_EVENT_TABLE_KEYS
            if tables.get(table_key)
        },
        "environment_packs": {
            env: build_environment_pack(repo, env) for env in ENVIRONMENTS
        },
    }
    if environment:
        payload["for_environment"] = build_environment_pack(repo, environment)
    return payload


def foe_names_for_validation(allowlists: dict[str, Any]) -> set[str]:
    return set(allowlists.get("foe_spawn_names") or allowlists.get("monster_spawn_names") or [])
