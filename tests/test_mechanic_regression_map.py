from __future__ import annotations

import json
import re
from pathlib import Path
from typing import get_args

from fastapi.testclient import TestClient

from app.main import app
from app.rules.repository import RulesRepository
from app.schemas import SessionAction


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "data" / "rules" / "mechanic_regression_map.json"

TARGET_FAMILY_IDS = {
    "secrets",
    "reactions",
    "quests",
    "special_events",
    "traps",
    "treasure",
    "class_abilities",
    "environment_passage",
    "fiendish_foes",
    "milestones",
    "camp_outside_start",
    "hirelings",
}

HANDLED_REACTION_KEYS = {
    "blood_offering",
    "bribe",
    "bribe_food",
    "bribe_food_or_gem",
    "bribe_food_per_foe",
    "bribe_gem",
    "bribe_gem_or_two_handed_weapon",
    "bribe_magic_item",
    "bribe_gold_or_food",
    "bribe_ration_gold_or_mushroom",
    "bribe_scrolls_or_potions",
    "bribe_treasure_or_magic_item",
    "buy_weapons",
    "challenge_of_champions",
    "fight",
    "fight_to_death",
    "flee",
    "flee_if_outnumbered",
    "ignore",
    "magic_challenge",
    "offer_food",
    "offer_information",
    "peaceful",
    "puzzle",
    "quest",
    "sleep",
    "trade_information",
    "trade",
    "trial_of_champions",
}


def _regression_map() -> dict:
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))


def _rules_tables() -> dict:
    return TestClient(app).get("/api/rules/tables").json()


def _reference_ids() -> set[str]:
    repo = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules")
    return {entry["id"] for entry in repo.rulebook_reference()}


def _frontend_text() -> str:
    parts = [
        (ROOT / "src" / "app" / "static" / "app.js").read_text(encoding="utf-8"),
        (ROOT / "src" / "app" / "static" / "index.html").read_text(encoding="utf-8"),
        (ROOT / "src" / "app" / "static" / "styles.css").read_text(encoding="utf-8"),
    ]
    return "\n".join(parts).lower()


def _session_actions() -> set[str]:
    return set(get_args(SessionAction.model_fields["action"].annotation))


def _engine_action_branches() -> set[str]:
    text = (ROOT / "src" / "app" / "engine" / "random_dungeon.py").read_text(encoding="utf-8")
    return set(re.findall(r'(?:if|elif) action == "([^"]+)"', text))


def _partial_structured_rows() -> set[str]:
    tables = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules").dungeon_tables()
    rows: set[str] = set()
    for table_key, table_rows in tables.items():
        if not isinstance(table_rows, list):
            continue
        for row in table_rows:
            if not isinstance(row, dict) or row.get("implementation") != "partial":
                continue
            label = row.get("spell") or row.get("key") or row.get("result")
            rows.add(f"{table_key}:{row.get('roll', row.get('key'))}:{label}")
    return rows


def test_mechanic_regression_map_covers_requested_target_families() -> None:
    data = _regression_map()
    families = {family["id"]: family for family in data["families"]}

    assert set(families) == TARGET_FAMILY_IDS
    assert "full hex-map wilderness from Fortress remains deferred" in data["fortress_of_the_warlord_note"]
    for family in families.values():
        assert family["status"]
        assert family["table_keys"]
        assert family["reference_ids"]
        assert family["engine_actions"]
        assert family["ui_markers"]
        assert family["tests"]
        assert family["persistence_fields"]
        assert family["split_party_scope"]


def test_mechanic_regression_map_links_to_existing_tables_reference_actions_ui_and_tests() -> None:
    tables = set(_rules_tables()) | {"named_monster_reaction_tables"}
    reference_ids = _reference_ids()
    actions = _session_actions()
    engine_branches = _engine_action_branches()
    frontend_text = _frontend_text()
    schema_only_actions = {"start_combat", "flee", "withdraw", "xp_roll", "bank_xp_roll"}

    for family in _regression_map()["families"]:
        assert set(family["table_keys"]) <= tables, family["id"]
        assert set(family["reference_ids"]) <= reference_ids, family["id"]
        for action in family["engine_actions"]:
            assert action in actions, f"{family['id']} references unknown action {action}"
            assert action in engine_branches or action in schema_only_actions, (
                f"{family['id']} action {action} is not handled by RandomDungeonEngine.advance"
            )
        for marker in family["ui_markers"]:
            assert marker.lower() in frontend_text, f"{family['id']} UI marker missing: {marker}"
        for test_path in family["tests"]:
            assert (ROOT / test_path).exists(), f"{family['id']} test path missing: {test_path}"


def test_partial_structured_rows_are_explicitly_flagged_as_unimplemented_indexed_rules() -> None:
    mapped = {item["structured_row"] for item in _regression_map()["unimplemented_indexed_rules"]}

    assert _partial_structured_rows() <= mapped


def test_indexed_monster_reaction_keys_are_either_handled_or_flagged() -> None:
    monsters = json.loads((ROOT / "data" / "rules" / "monsters.json").read_text(encoding="utf-8"))
    reaction_keys = {
        row["key"]
        for rows in monsters["reaction_tables"].values()
        for row in rows
        if isinstance(row, dict) and row.get("key")
    }
    flagged = {
        item["structured_row"].rsplit(":", 1)[-1]
        for item in _regression_map()["unimplemented_indexed_rules"]
        if item["structured_row"].startswith("monsters.json:")
    }

    assert reaction_keys <= HANDLED_REACTION_KEYS | flagged
    assert flagged == set()


def test_scroll_copy_no_longer_marked_partial_after_engine_wiring() -> None:
    tables = _rules_tables()
    copy_row = next(row for row in tables["scrolls_table"] if row["key"] == "copy")

    assert copy_row["implementation"] == "yes"
    assert "copy_scroll" in _session_actions()
    assert "copy_scroll" in _engine_action_branches()
