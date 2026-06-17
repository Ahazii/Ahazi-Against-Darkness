from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.engine.expert_skill_effects import expert_skill_implementation_rows
from app.engine.expert_skills import expert_skills_table_rows, expert_spells_table_rows
from app.engine.tier_skills import (
    class_tricks_implementation_rows,
    ee_class_trick_flags_table_rows,
    tier_skills_table_rows,
)
from app.main import app
from app.rules.repository import RulesRepository


SPELLS_SKILLS_COMBAT_TABLE_KEYS = [
    "basic_spells_table",
    "druid_spells_table",
    "illusionist_spells_table",
    "scrolls_table",
    "expert_skills_table",
    "expert_skill_implementation_table",
    "expert_spells_table",
    "heroic_skills_table",
    "legendary_skills_table",
    "class_tricks_implementation_table",
    "ee_class_trick_flags_table",
    "swashbuckler_traits_table",
    "combat_modifiers_table",
    "combat_notes",
]

EXPECTED_SPELLS_SKILLS_COMBAT_SIGNATURE = "56fc0ab782ef3bafee4bfde7e1480db417c8cd7f8a113ccfe06f90da554648da"
EXPECTED_SPELLS_SKILLS_COMBAT_ROW_COUNTS = {
    "basic_spells_table": 7,
    "druid_spells_table": 12,
    "illusionist_spells_table": 12,
    "scrolls_table": 6,
    "expert_skills_table": 41,
    "expert_skill_implementation_table": 41,
    "expert_spells_table": 6,
    "heroic_skills_table": 45,
    "legendary_skills_table": 20,
    "class_tricks_implementation_table": 25,
    "ee_class_trick_flags_table": 5,
    "swashbuckler_traits_table": 6,
    "combat_modifiers_table": 15,
    "combat_notes": 13,
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


def test_spells_skills_class_abilities_combat_family_exact_api_snapshot_locked() -> None:
    payload = _tables_payload()
    family = {key: payload[key] for key in SPELLS_SKILLS_COMBAT_TABLE_KEYS}

    assert {key: len(rows) for key, rows in family.items()} == EXPECTED_SPELLS_SKILLS_COMBAT_ROW_COUNTS
    assert _signature(family) == EXPECTED_SPELLS_SKILLS_COMBAT_SIGNATURE


def test_spells_skills_class_abilities_combat_pdf_rows_keep_source_pages() -> None:
    payload = _tables_payload()
    for key in SPELLS_SKILLS_COMBAT_TABLE_KEYS:
        rows = payload[key]
        assert rows, key
        if key == "combat_notes":
            assert all("p." in row for row in rows), key
            continue
        assert all(str(row.get("source_page", "")).strip() for row in rows), key


def test_spell_scroll_and_combat_static_tables_match_packaged_catalog_rows() -> None:
    packaged_tables = _repo().dungeon_tables()
    payload = _tables_payload()

    for key in (
        "basic_spells_table",
        "druid_spells_table",
        "illusionist_spells_table",
        "scrolls_table",
        "combat_modifiers_table",
        "combat_notes",
    ):
        assert payload[key] == packaged_tables[key]


def test_generated_skill_and_class_ability_tables_match_locked_catalogs() -> None:
    repo = _repo()
    payload = _tables_payload()
    expert_catalog = repo.expert_skills()

    assert payload["expert_skills_table"] == expert_skills_table_rows(expert_catalog)
    assert payload["expert_skill_implementation_table"] == expert_skill_implementation_rows(expert_catalog)
    assert payload["expert_spells_table"] == expert_spells_table_rows(expert_catalog)
    assert payload["heroic_skills_table"] == tier_skills_table_rows(repo.heroic_skills(), "heroic")
    assert payload["legendary_skills_table"] == tier_skills_table_rows(repo.legendary_skills(), "legendary")
    assert payload["class_tricks_implementation_table"] == class_tricks_implementation_rows()
    assert payload["ee_class_trick_flags_table"] == ee_class_trick_flags_table_rows(repo.ee_class_tricks())


def test_expert_implementation_table_is_abyss_only_and_ee_flags_are_separate() -> None:
    payload = _tables_payload()
    expert_names = {row["skill"] for row in payload["expert_skill_implementation_table"]}
    ee_names = {row["flag"] for row in payload["ee_class_trick_flags_table"]}

    assert "Whirlwind of Steel" in expert_names
    assert {"Sacrifice Defense", "Sacrifice Shield", "Army of Dolls", "Divine Smite"} <= ee_names
    assert expert_names.isdisjoint({"Sacrifice Defense", "Sacrifice Shield", "Army Of Dolls", "Divine Smite"})
