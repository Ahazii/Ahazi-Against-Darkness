from __future__ import annotations

import json
import re
from pathlib import Path
from typing import get_args

from app.main import app
from app.rules.repository import RulesRepository
from app.schemas import SessionAction
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]

SPECIAL_ITEM_ACTIONS = {
    "use_map_fragment",
    "use_enchanted_paint",
    "use_berserkers_mushroom",
    "use_wolfsbane",
    "use_abyss_item",
    "spend_torch",
    "climb_from_pit",
}

ABYSS_CAMPAIGN_ACTIONS = {
    "start_abyss_campaign_plot",
    "abyss_plot_contribute_gold",
    "abyss_plot_take_artifact_piece",
    "abyss_plot_spend_clues",
    "abyss_plot_transfer_artifact",
    "abyss_plot_resolve_finale",
    "hunt_vampire_sire",
}

SPECIAL_REFERENCE_IDS = {
    "map_fragment",
    "enchanted_paint",
    "wand_of_power",
    "hidden_pit_escape",
}

COMBAT_MODIFIER_KEYS = {
    "door_tools",
    "torch_webs",
    "pit_trap",
    "treasure_special_items",
}

UI_MARKERS = [
    "use_map_fragment",
    "use_enchanted_paint",
    "use_berserkers_mushroom",
    "use_wolfsbane",
    "spend_torch",
    "climb_from_pit",
    "Use map fragment",
    "Wand of Power",
    "Throw wolfsbane",
    "use_abyss_item",
    "Wish: wound foe",
    "Eat Elven Bread",
    "Spend torch",
    "Eat Berserker's Mushroom",
    "Use Enchanted Paint",
    "Treat Lycanthropy",
    "treat_lycanthropy",
    "monastery lycanthropy cure",
    "appendAbyssCampaignActions",
    "start_abyss_campaign_plot",
    "abyss_plot_contribute_gold",
    "abyss_plot_take_artifact_piece",
    "abyss_plot_spend_clues",
    "abyss_plot_transfer_artifact",
    "abyss_plot_resolve_finale",
    "hunt_vampire_sire",
    "Start plot",
    "Fund rebellion",
    "Take artefact piece",
    "Hunt vampire sire",
]


def _session_actions() -> set[str]:
    return set(get_args(SessionAction.model_fields["action"].annotation))


def _engine_branches() -> set[str]:
    text = (ROOT / "src" / "app" / "engine" / "random_dungeon.py").read_text(encoding="utf-8")
    return set(re.findall(r'(?:if|elif) action == "([^"]+)"', text))


def _reference_ids() -> set[str]:
    repo = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules")
    return {entry["id"] for entry in repo.rulebook_reference()}


def _combat_modifier_keys() -> set[str]:
    tables = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules").dungeon_tables()
    return {row["key"] for row in tables["combat_modifiers_table"]}


def test_special_item_actions_are_schema_actions_and_engine_handlers() -> None:
    actions = _session_actions()
    branches = _engine_branches()
    assert SPECIAL_ITEM_ACTIONS <= actions
    assert SPECIAL_ITEM_ACTIONS <= branches
    assert "treat_lycanthropy" in actions
    assert "treat_lycanthropy" in branches
    assert ABYSS_CAMPAIGN_ACTIONS <= actions
    assert ABYSS_CAMPAIGN_ACTIONS <= branches


def test_special_item_reference_entries_exist() -> None:
    assert SPECIAL_REFERENCE_IDS <= _reference_ids()


def test_combat_modifiers_table_documents_special_items() -> None:
    keys = _combat_modifier_keys()
    assert COMBAT_MODIFIER_KEYS <= keys
    consumables = next(row for row in _tables()["combat_modifiers_table"] if row["key"] == "consumables")
    assert "10gp" in consumables["result"]
    assert "Wolfsbane" in consumables["result"]
    assert "not sold" in consumables["result"].lower() or "not in the home shop" in consumables["result"].lower()


def test_frontend_exposes_special_item_controls() -> None:
    app_js = (ROOT / "src" / "app" / "static" / "app.js").read_text(encoding="utf-8")
    for marker in UI_MARKERS:
        assert marker in app_js, marker


def test_mechanic_regression_map_links_special_items() -> None:
    data = json.loads((ROOT / "data" / "rules" / "mechanic_regression_map.json").read_text(encoding="utf-8"))
    treasure = next(family for family in data["families"] if family["id"] == "treasure")
    traps = next(family for family in data["families"] if family["id"] == "traps")
    assert SPECIAL_ITEM_ACTIONS - {"climb_from_pit"} <= set(treasure["engine_actions"])
    assert "climb_from_pit" in traps["engine_actions"]
    assert "tests/test_special_items.py" in treasure["tests"]
    assert {"map_fragment", "enchanted_paint", "wand_of_power"} <= set(treasure["reference_ids"])
    assert "hidden_pit_escape" in traps["reference_ids"]


def _tables() -> dict:
    return TestClient(app).get("/api/rules/tables").json()
