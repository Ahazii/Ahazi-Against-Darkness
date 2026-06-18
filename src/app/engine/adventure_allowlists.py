from __future__ import annotations

from typing import Any

from ..rules.repository import RulesRepository, VALID_TILE_KEYS

BOSS_TABLE_KEYS = [
    "boss",
    "caverns_boss",
    "fungal_grottoes_boss",
    "fiendish_foes_boss",
]

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

QUEST_KEYS = (
    "bring_head",
    "bring_gold",
    "bring_alive",
    "bring_item",
    "peaceful_way",
    "slay_all",
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


def build_boss_spawn_names(repo: RulesRepository) -> list[str]:
    monsters = repo.monsters()
    names: set[str] = set()
    for table_key in BOSS_TABLE_KEYS:
        for entry in monsters.get(table_key, []):
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str) and name.strip():
                    names.add(name.strip())
    return sorted(names)


def build_adventure_allowlists(repo: RulesRepository) -> dict[str, Any]:
    monsters = repo.monsters()
    monster_names: set[str] = set()
    for table_key in MONSTER_TABLE_KEYS:
        for entry in monsters.get(table_key, []):
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str) and name.strip():
                    monster_names.add(name.strip())

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

    return {
        "schema_version": 1,
        "monster_spawn_names": sorted(monster_names),
        "tile_keys": list(VALID_TILE_KEYS),
        "equipment_items": sorted(item_names),
        "trap_keys": sorted(trap_keys),
        "special_event_keys": sorted(event_keys),
        "quest_keys": list(QUEST_KEYS),
        "environments": list(ENVIRONMENTS),
        "boss_spawn_names": build_boss_spawn_names(repo),
    }
