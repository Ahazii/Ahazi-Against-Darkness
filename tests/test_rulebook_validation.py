from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller, parse_roll_range, resolve_gold_formula
from app.rules.repository import RulesRepository


@pytest.fixture
def tables() -> dict:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override").dungeon_tables()


@pytest.fixture
def roller(tables: dict) -> DungeonTableRoller:
    return DungeonTableRoller(tables)


def test_door_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("door_table", 2)["door_type"] == "sealed"
    assert roller.lookup("door_table", 3)["door_type"] == "iron"
    assert roller.lookup("door_table", 4)["door_type"] == "illusion"
    assert roller.lookup("door_table", 5)["door_type"] == "locked"
    assert roller.lookup("door_table", 10)["door_type"] == "unlocked"
    assert roller.lookup("door_table", 11)["door_type"] == "trap_door"
    assert roller.lookup("door_table", 12)["door_type"] == "lever"


def test_trap_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("trap_table", 1)["trap_key"] == "dart"
    assert roller.lookup("trap_table", 1)["target"] == "random"
    assert roller.lookup("trap_table", 2)["save"] == "poison"
    assert roller.lookup("trap_table", 3)["save"] == "trapdoor"
    assert roller.lookup("trap_table", 6)["damage"] == 2
    assert roller.lookup("trap_table", 6)["shield_applies"] is False


def test_treasure_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("treasure_table", 1)["result"] == "No treasure found."
    assert roller.lookup("treasure_table", 2)["gold"] == "1d6"
    assert roller.lookup("treasure_table", 3)["gold"] == "2d6"
    assert roller.lookup("treasure_table", 4)["gold"] == "2d6*5"
    assert roller.lookup("treasure_table", 5)["gold"] == "3d6*10"
    assert roller.lookup("treasure_table", 6)["magic_table"] == "dungeon_magic_treasure"


def test_magic_treasure_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("dungeon_magic_treasure_table", 1)["items"] == ["Wand of Sleep (3 charges)"]
    assert roller.lookup("dungeon_magic_treasure_table", 5)["items"] == ["Potion of Healing"]
    assert roller.lookup("dungeon_magic_treasure_table", 6)["items"] == ["Fireball Staff (2 charges)"]


def test_wandering_monsters_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("wandering_monsters_table", 2)["enemy_category"] == "vermin"
    assert roller.lookup("wandering_monsters_table", 6)["enemy_category"] == "boss"


def test_search_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup_search(0).effect == "wandering_monsters"
    assert roller.lookup_search(1).effect == "wandering_monsters"
    assert roller.lookup_search(2).effect == "nothing"
    assert roller.lookup_search(5).effect == "found_something"
    assert roller.lookup_search(6).effect == "found_something"


def test_experience_and_economy_tables_present(roller: DungeonTableRoller) -> None:
    assert "experience_classical_table" in roller.tables
    assert "quest_table" in roller.tables
    assert roller.lookup("economy_services_table", 1)["service"] == "wandering_healer"
    assert roller.lookup("quest_table", 1)["key"] == "bring_head"
    assert roller.lookup("epic_rewards_table", 1)["key"] == "book_of_skalitos"


def test_room_content_corridor_roll_4_is_searchable(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(4, "corridor")
    assert outcome is not None
    assert outcome.key == "searchable"


def test_room_content_room_roll_4_is_special_event(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(4, "room")
    assert outcome is not None
    assert outcome.key == "special_event"


def test_room_content_room_roll_9_is_minions(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(9, "room")
    assert outcome is not None
    assert outcome.enemy_category == "minions"


def test_room_content_corridor_roll_12_is_empty(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(12, "corridor")
    assert outcome is not None
    assert outcome.key == "empty"


def test_room_content_room_roll_12_is_dragon_lair(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(12, "room")
    assert outcome is not None
    assert outcome.key == "lair"
    assert outcome.enemy_category == "boss"
    assert outcome.enemy_tags == ["dragon"]


def test_roll_enemy_honors_required_tags(monkeypatch) -> None:
    from app.engine.random_dungeon import RandomDungeonEngine
    from app.schemas import MapState, SessionState

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(rules=RulesRepository(packaged, packaged / "_override"), asset_dir=Path())
    monkeypatch.setattr("app.engine.random_dungeon.random.choice", lambda items: items[0])
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[], current_tile_id="x"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    enemies = engine._roll_enemy(session, "boss", 1, required_tags=["dragon"])

    assert len(enemies) == 1
    assert enemies[0].name == "Young Dragon"
    assert "dragon" in enemies[0].tags


def test_hidden_treasure_formula(monkeypatch) -> None:
    rolls = iter([2, 3])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: next(rolls))
    assert resolve_gold_formula("(HCL+d6)*(HCL+d6)", hcl=2) == 20


def test_parse_roll_range() -> None:
    assert parse_roll_range("5-6") == (5, 6)
    assert parse_roll_range("0-1") == (0, 1)


META_TABLE_KEYS = {"ruleset_status", "open_items", "validation"}
API_MERGED_TABLE_KEYS = {
    "equipment_shop_table",
    "expert_skills_table",
    "expert_skill_implementation_table",
    "expert_spells_table",
    "heroic_skills_table",
    "legendary_skills_table",
    "class_tricks_implementation_table",
    "map_elements_validation_table",
    "tier_training_costs_table",
}

EXPANDED_SECRET_IDS = {
    "weakness_of_a_foe",
    "deal_with_a_foe",
    "hidden_treasure_location",
    "magic_item_location",
    "true_name_spiritual_entity",
    "new_spell",
    "magical_power_increase",
    "scroll_location",
    "potion_recipe",
    "terrifying_secret",
    "big_money_buyer",
    "enemy_in_dungeon",
    "prisoner",
    "dragonslayer_bloodline",
    "secret_diet",
    "someone_imprisoned",
}


def test_home_page_lists_all_dungeon_tables(tables: dict) -> None:
    app_js = (Path(__file__).resolve().parents[1] / "src" / "app" / "static" / "app.js").read_text(
        encoding="utf-8"
    )
    start = app_js.index("const RULES_TABLE_ORDER = [")
    end = app_js.index("];", start)
    block = app_js[start:end]
    ordered = [
        line.strip().strip(",").strip('"')
        for line in block.splitlines()
        if line.strip().startswith('"')
    ]
    data_keys = {key for key in tables if key not in META_TABLE_KEYS} | API_MERGED_TABLE_KEYS
    missing_from_home = sorted(data_keys - set(ordered))
    stale_on_home = sorted(set(ordered) - data_keys)
    assert not missing_from_home, f"dungeon_tables keys missing from RULES_TABLE_ORDER: {missing_from_home}"
    assert not stale_on_home, f"RULES_TABLE_ORDER entries not in dungeon_tables.json: {stale_on_home}"


def test_secrets_table_matches_expanded_secret_catalog(tables: dict) -> None:
    rows = tables["secrets_table"]
    keys = [row["key"] for row in rows]
    assert len(keys) == len(set(keys))
    assert set(keys) == EXPANDED_SECRET_IDS
    implementations = {row["key"]: row.get("implementation") for row in rows}
    assert implementations["weakness_of_a_foe"] == "wired"
    assert implementations["deal_with_a_foe"] == "wired"
    assert implementations["hidden_treasure_location"] == "wired"
    assert implementations["magic_item_location"] == "wired"
    assert implementations["scroll_location"] == "wired"
    assert implementations["dragonslayer_bloodline"] == "wired"
    assert implementations["potion_recipe"] == "wired"
    assert implementations["terrifying_secret"] == "wired"
    assert implementations["big_money_buyer"] == "wired"
    assert implementations["secret_diet"] == "wired"
    assert implementations["true_name_spiritual_entity"] == "wired"
    assert implementations["new_spell"] == "wired"
    assert implementations["magical_power_increase"] == "wired"
    assert implementations["enemy_in_dungeon"] == "wired"
    assert implementations["prisoner"] == "wired"


def test_tables_api_includes_equipment_shop() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = client.get("/api/rules/tables").json()
    assert "equipment_shop_table" in payload
    assert payload["equipment_shop_table"]
    assert any("sell" in row.get("roll", "") for row in payload["equipment_shop_table"])
    assert payload["expert_skills_table"]
    assert payload["expert_spells_table"]
    assert payload["heroic_skills_table"]
    assert payload["legendary_skills_table"]
    assert payload["class_tricks_implementation_table"]
    assert payload["map_elements_validation_table"]
    assert payload["tier_training_costs_table"]
    expert_training = next(row for row in payload["tier_training_costs_table"] if row["tier"] == "Expert")
    assert expert_training["banked_xp"] == "0, or 1 instead of gold"
    assert "separate XP roll" in expert_training["notes"]


def test_rules_reference_clarifies_expert_training_gate() -> None:
    reference = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "rules" / "rulebook_reference.json").read_text(
            encoding="utf-8"
        )
    )
    by_id = {entry["id"]: entry for entry in reference["entries"]}
    expert_body = by_id["expert_skills"]["body"]
    xp_body = by_id["classical_xp"]["body"]
    assert "Expert tier entry is separate" in expert_body
    assert "one advancement XP roll" in expert_body
    assert "Expert-trained L5+ heroes" in xp_body
    assert "500gp or 1 banked XP roll" in xp_body


def test_home_page_rules_panel_includes_bestiary_and_reactions() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "src" / "app" / "static" / "app.js").read_text(
        encoding="utf-8"
    )
    index_html = (Path(__file__).resolve().parents[1] / "src" / "app" / "static" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "Monster bestiary" in app_js
    assert "Monster reaction tables" in app_js
    assert "Class profiles" in app_js
    assert "renderClassProfileTables" in app_js
    assert "renderMonsterBestiaryTables" in app_js
    assert "renderMonsterReactionRulesTables" in app_js
    assert "Map elements" in app_js
    assert "renderMapElementTables" in app_js
    assert "Icon registry" in app_js
    assert "renderIconRegistryTables" in app_js
    assert "generated defaults + icons.json" in app_js
    assert "room states, each playable class, monster categories, and every named monster" in app_js
    assert "Targeted uses show party-sheet selectors" in app_js
    assert 'getElementById("monster-bestiary")' not in app_js
    assert "Rules reference" in index_html
    assert "generated/custom icon registry" in index_html
    assert "renderRulesReference" in app_js
    assert "rules-reference-search" in index_html
    assert "rules-reference-status" in index_html


def test_rules_reference_api_returns_entries() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = client.get("/api/rules/reference").json()
    assert payload["count"] >= 110
    assert any(entry.get("id") == "resting" for entry in payload["entries"])
    search = client.get("/api/rules/reference", params={"q": "rage"}).json()
    assert search["count"] >= 1


def test_spell_and_scroll_tables_present(tables: dict) -> None:
    for key in (
        "basic_spells_table",
        "druid_spells_table",
        "illusionist_spells_table",
        "scrolls_table",
    ):
        assert key in tables
        assert isinstance(tables[key], list)
        assert tables[key]
