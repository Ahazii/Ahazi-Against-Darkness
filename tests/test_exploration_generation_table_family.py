from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.engine.tile_validation import map_elements_validation_table_rows, validate_tile_catalog
from app.main import app
from app.rules.repository import RulesRepository


EXPLORATION_GENERATION_TABLE_KEYS = [
    "door_table",
    "trap_table",
    "caverns_trap_table",
    "fungal_grottoes_trap_table",
    "search_table",
    "wandering_monsters_table",
    "room_content_table",
    "special_event_wandering_table",
    "dungeon_special_features_table",
    "dungeon_special_events_table",
    "caverns_special_events_table",
    "fungal_grottoes_special_events_table",
    "map_elements_validation_table",
]

EXPECTED_EXPLORATION_GENERATION_SIGNATURE = "61ef19f1d5d5d79980c2fdb575c661b66c7e89423196a309b74ba10cfcf2ac1e"
EXPECTED_EXPLORATION_GENERATION_ROW_COUNTS = {
    "door_table": 7,
    "trap_table": 6,
    "caverns_trap_table": 6,
    "fungal_grottoes_trap_table": 6,
    "search_table": 4,
    "wandering_monsters_table": 4,
    "room_content_table": 11,
    "special_event_wandering_table": 4,
    "dungeon_special_features_table": 6,
    "dungeon_special_events_table": 6,
    "caverns_special_events_table": 6,
    "fungal_grottoes_special_events_table": 6,
    "map_elements_validation_table": 42,
}


def _rules_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "rules"


def _repo() -> RulesRepository:
    packaged = _rules_dir()
    return RulesRepository(packaged, packaged / "_override")


def _tables_payload() -> dict:
    return TestClient(app).get("/api/rules/tables").json()


def _signature(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_exploration_doors_traps_generation_table_family_exact_api_snapshot_locked() -> None:
    payload = _tables_payload()
    family = {key: payload[key] for key in EXPLORATION_GENERATION_TABLE_KEYS}

    assert {key: len(rows) for key, rows in family.items()} == EXPECTED_EXPLORATION_GENERATION_ROW_COUNTS
    assert _signature(family) == EXPECTED_EXPLORATION_GENERATION_SIGNATURE


def test_exploration_doors_traps_generation_pdf_rows_keep_source_pages() -> None:
    payload = _tables_payload()
    for key in EXPLORATION_GENERATION_TABLE_KEYS:
        if key == "map_elements_validation_table":
            continue
        rows = payload[key]
        assert rows, key
        assert all(str(row.get("source_page", "")).strip() for row in rows), key


def test_map_elements_validation_table_is_generated_from_locked_tiles_catalog() -> None:
    repo = _repo()
    tiles = repo.tiles()

    assert validate_tile_catalog(tiles) == {}
    assert _tables_payload()["map_elements_validation_table"] == map_elements_validation_table_rows(tiles)


def test_exploration_family_static_tables_match_packaged_catalog_rows() -> None:
    packaged_tables = _repo().dungeon_tables()
    payload = _tables_payload()

    for key in EXPLORATION_GENERATION_TABLE_KEYS:
        if key == "map_elements_validation_table":
            continue
        assert payload[key] == packaged_tables[key]
