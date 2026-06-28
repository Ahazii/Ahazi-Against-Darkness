from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from app.engine.class_profiles import (
    LIFE_OFFSET,
    STARTING_WEALTH_ROLL,
    build_starting_inventory,
    max_life_for_level,
    roll_starting_wealth,
)
from app.engine.dice import roll_formula
from app.rules.repository import RulesRepository

# Expanded Edition Life and wealth validated against Four_Against_Darkness_Expanded_Edition.pdf (p.24–69).
# TCOTFD / Netherworld portraits via tools/extract_tcotfd_class_assets.py.
RULEBOOK_L1_LIFE: dict[str, int] = {
    "acrobat": 4,
    "assassin": 4,
    "barbarian": 8,
    "bulwark": 8,
    "cleric": 5,
    "dwarf": 6,
    "druid": 4,
    "elf": 5,
    "gnome": 5,
    "halfling": 4,
    "illusionist": 3,
    "kukla": 6,
    "light_gladiator": 6,
    "mushroom_monk": 5,
    "paladin": 7,
    "ranger": 7,
    "rogue": 4,
    "swashbuckler": 5,
    "warrior": 7,
    "wizard": 3,
}

EXPECTED_CLASS_CATALOG_SIGNATURE = "8d1577fa09c040ec16e983ef0cb0cfaac5d8eb17e398c52906763b021c2c2b30"
EXPECTED_CLASS_COUNT = 26
TCOTFD_PARTIAL_CLASS_IDS = frozenset({"demonologist", "cambion", "succubus"})
CLASS_CATALOG_SIGNATURE_FIELDS = (
    "id",
    "name",
    "base_life",
    "life_offset",
    "attack_bonus",
    "defense_bonus",
    "save_bonus",
    "starting_gold",
    "starting_wealth_roll",
    "starting_inventory",
    "starting_spells",
    "abilities",
    "implementation_status",
    "description",
)


def _rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def _classes_json() -> list[dict]:
    return json.loads((Path(__file__).resolve().parents[1] / "data" / "rules" / "classes.json").read_text(encoding="utf-8"))


def _signature(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_classes_json_exact_pdf_catalog_snapshot_locked() -> None:
    rows = _classes_json()
    snapshot = [{field: row.get(field) for field in CLASS_CATALOG_SIGNATURE_FIELDS} for row in rows]
    assert len(snapshot) == EXPECTED_CLASS_COUNT
    assert _signature(snapshot) == EXPECTED_CLASS_CATALOG_SIGNATURE
    assert [row["id"] for row in rows] == [
        "warrior",
        "cleric",
        "rogue",
        "wizard",
        "barbarian",
        "ranger",
        "dwarf",
        "elf",
        "halfling",
        "druid",
        "illusionist",
        "acrobat",
        "assassin",
        "bulwark",
        "gnome",
        "kukla",
        "light_gladiator",
        "mushroom_monk",
        "paladin",
        "swashbuckler",
        "wandering_alchemist",
        "satyr",
        "conservationist",
        "demonologist",
        "cambion",
        "succubus",
    ]


def test_life_offset_matches_rulebook_l1() -> None:
    for class_id, l1_life in RULEBOOK_L1_LIFE.items():
        assert max_life_for_level(class_id, 1) == l1_life, class_id
        assert LIFE_OFFSET[class_id] == l1_life - 1, class_id


def test_classes_json_synced_with_engine_life_and_wealth() -> None:
    rules = _rules()
    for profile in rules.classes():
        assert profile.life_offset == LIFE_OFFSET[profile.id]
        assert profile.base_life == max_life_for_level(profile.id, 1)
        assert profile.starting_wealth_roll == STARTING_WEALTH_ROLL[profile.id]
        if profile.id in TCOTFD_PARTIAL_CLASS_IDS:
            assert profile.implementation_status == "partial"
        else:
            assert profile.implementation_status == "validated"


def test_class_profiles_table_is_generated_from_locked_catalog() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    payload = TestClient(app).get("/api/rules/tables").json()
    rows = payload["class_profiles_table"]
    profiles = _rules().classes()
    assert len(rows) == EXPECTED_CLASS_COUNT
    assert [row["class"] for row in rows] == [profile.name for profile in profiles]
    for row, profile in zip(rows, profiles):
        assert row["l1_life"] == str(profile.base_life)
        assert row["starting_wealth"] == profile.starting_wealth_roll
        assert row["starting_gear"] == ", ".join(profile.starting_inventory)
        assert row["starting_spells"] == ", ".join(profile.starting_spells)


def test_ranger_and_paladin_use_six_plus_level_life() -> None:
    assert max_life_for_level("ranger", 1) == 7
    assert max_life_for_level("paladin", 1) == 7
    assert max_life_for_level("ranger", 3) == 9
    assert max_life_for_level("paladin", 3) == 9


def test_gnome_life_offset_is_four() -> None:
    assert max_life_for_level("gnome", 1) == 5


def test_roll_starting_wealth_respects_formula_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.engine.class_profiles.roll_formula", lambda formula: 42 if formula == "5d6" else 7)
    assert roll_starting_wealth("assassin") == 42
    assert roll_starting_wealth("warrior") == 7


def test_build_starting_inventory_rolls_rations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.engine.class_profiles.roll_formula", lambda formula: 9 if formula == "1d6+3" else 2)
    halfling = build_starting_inventory("halfling", [])
    assert halfling == ["Food rations (9)", "Sling", "Light hand weapon"]

    ranger = build_starting_inventory("ranger", [])
    assert ranger[-1] == "Food rations (2)"
    assert ranger.count("Hand weapon") == 2


def test_kukla_starting_inventory_includes_rings() -> None:
    gear = build_starting_inventory("kukla", ["Integrated tools"])
    assert "Red ring" in gear
    assert "Green ring" in gear


def test_swashbuckler_starting_inventory_matches_pdf_p61() -> None:
    gear = build_starting_inventory("swashbuckler", ["Hand weapon", "Light hand weapon", "Plumed/tricorn hat", "Half-cape"])
    assert gear == ["Hand weapon", "Light hand weapon", "Plumed/tricorn hat", "Half-cape"]
    assert "Bandage" not in gear


def test_d3_and_d6_formulas() -> None:
    assert 1 <= roll_formula("d3") <= 3
    assert 1 <= roll_formula("1d6+3") <= 9
    assert roll_formula("2") == 2
