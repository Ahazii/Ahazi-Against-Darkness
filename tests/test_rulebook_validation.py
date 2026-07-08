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
    assert roller.lookup("treasure_table", 0)["result"] == "No treasure found."
    assert roller.lookup("treasure_table", 1)["gold"] == "1d6"
    assert "2d6 gp" in roller.lookup("treasure_table", 2)["result"]
    assert roller.lookup("treasure_table", 3)["items"] == ["Scroll/Bark/Prism with random spell"]
    assert "treasure chest" in roller.lookup("treasure_table", 5)["result"]
    assert roller.lookup("treasure_table", 6)["magic_table"] == "dungeon_magic_treasure"


def test_magic_treasure_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("dungeon_magic_treasure_table", 1)["items"] == ["Wand of Sleep (3 charges)"]
    assert "30gp per remaining charge" in roller.lookup("dungeon_magic_treasure_table", 1)["result"]
    assert "automatically pass a Defense roll" in roller.lookup("dungeon_magic_treasure_table", 2)["result"]
    assert "automatically bribe the next Foe" in roller.lookup("dungeon_magic_treasure_table", 3)["result"]
    assert roller.lookup("dungeon_magic_treasure_table", 4)["weapon_type_roll"] == "d6"
    assert roller.lookup("dungeon_magic_treasure_table", 5)["items"] == ["Potion of Healing"]
    assert roller.lookup("dungeon_magic_treasure_table", 6)["items"] == ["Fireball Staff (2 charges)"]
    assert roller.lookup("dungeon_magic_treasure_table", 6)["fungal_table"] == "fungal_grottoes_rare_mushroom_table"


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


def test_room_content_room_roll_9_is_searchable_with_secret_passage_choice(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(9, "room")
    assert outcome is not None
    assert outcome.key == "searchable"
    assert outcome.enemy_category is None
    assert outcome.choices == ["secret_passage_2_clues"]


def test_room_content_room_roll_10_is_weird_monsters(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(10, "room")
    assert outcome is not None
    assert outcome.enemy_category == "weird"


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
    assert parse_roll_range("6+") == (6, 999)


def test_open_ended_table_rolls_match_high_values(roller: DungeonTableRoller) -> None:
    assert roller.lookup("treasure_table", 6)["roll"] == "6+"
    assert roller.lookup("treasure_table", 99)["roll"] == "6+"


META_TABLE_KEYS = {"ruleset_status", "open_items", "validation"}
API_MERGED_TABLE_KEYS = {
    "equipment_shop_table",
    "item_tooltip_coverage_table",
    "class_profiles_table",
    "expert_skills_table",
    "expert_skill_implementation_table",
    "expert_spells_table",
    "heroic_skills_table",
    "legendary_skills_table",
    "class_tricks_implementation_table",
    "ee_class_trick_flags_table",
    "map_elements_validation_table",
    "forsaken_depths_map_elements_validation_table",
    "forsaken_depths_rivers_map_elements_validation_table",
    "forsaken_depths_room_codes_table",
    "fd_room_content_table",
    "fd_river_type_table",
    "fd_river_hazard_table",
    "fd_river_encounter_table",
    "fd_vermin_table",
    "fd_minions_table",
    "fd_horde_table",
    "fd_event_table",
    "fd_quest_table",
    "fd_heroic_magic_item_table",
    "fd_legendary_magic_item_table",
    "fd_legendary_spell_table",
    "fd_cyclopean_idol_table",
    "courtship_seaside_encounter_table",
    "courtship_riverside_encounter_table",
    "courtship_woods_encounter_table",
    "courtship_mountain_encounter_table",
    "courtship_meadows_encounter_table",
    "courtship_palace_encounter_table",
    "courtship_book_of_secrets_table",
    "courtship_blossoms_magic_item_table",
    "courtship_blossoms_spell_scrolls_table",
    "courtship_lex_shop_table",
    "courtship_apothecary_recipes_table",
    "fd_trap_table",
    "fd_hallucination_table",
    "fd_ruins_content_table",
    "fd_citadel_table",
    "fd_citadel_weird_table",
    "fd_treasure_table",
    "fd_wandering_monsters_table",
    "fd_boss_table",
    "fd_weird_table",
    "tier_training_costs_table",
    "hirelings_table",
    "milestones_table",
}

VERIFIED_RULE_TABLE_KEYS = {
    "abyss_boss_table",
    "abyss_dragon_table",
    "abyss_minions_table",
    "abyss_magic_treasure_table",
    "abyss_magical_defense_table",
    "abyss_room_content_table",
    "abyss_scroll_table",
    "abyss_special_feature_table",
    "abyss_trap_table",
    "abyss_treasure_table",
    "abyss_enchanted_banquet_table",
    "abyss_unique_event_table",
    "abyss_useful_stuff_table",
    "abyss_vermin_table",
    "abyss_weird_table",
    "basic_spells_table",
    "caverns_special_events_table",
    "caverns_special_features_table",
    "caverns_special_item_table",
    "caverns_trap_table",
    "caverns_water_pool_table",
    "class_tricks_implementation_table",
    "class_profiles_table",
    "clue_spends_table",
    "combat_modifiers_table",
    "combat_notes",
    "default_reaction_table",
    "door_table",
    "druid_spells_table",
    "dungeon_magic_treasure_table",
    "dungeon_special_events_table",
    "dungeon_special_features_table",
    "economy_services_table",
    "ee_class_trick_flags_table",
    "epic_rewards_table",
    "equipment_shop_table",
    "item_tooltip_coverage_table",
    "experience_classical_table",
    "experience_old_school_table",
    "experience_slow_sure_table",
    "experience_slower_table",
    "expert_skill_implementation_table",
    "expert_skills_table",
    "expert_spells_table",
    "fungal_grottoes_rare_item_table",
    "fungal_grottoes_rare_mushroom_table",
    "fungal_grottoes_special_events_table",
    "fungal_grottoes_trap_table",
    "heroic_skills_table",
    "hidden_treasure_table",
    "hirelings_table",
    "icon_registry_table",
    "milestones_table",
    "illusionist_spells_table",
    "legendary_skills_table",
    "major_reaction_table",
    "map_elements_table",
    "map_elements_validation_table",
    "monster_bestiary_table",
    "monster_reaction_tables",
    "forsaken_depths_map_elements_validation_table",
    "forsaken_depths_rivers_map_elements_validation_table",
    "forsaken_depths_room_codes_table",
    "fd_event_table",
    "fd_quest_table",
    "fd_heroic_magic_item_table",
    "fd_legendary_magic_item_table",
    "fd_legendary_spell_table",
    "fd_cyclopean_idol_table",
    "courtship_seaside_encounter_table",
    "courtship_riverside_encounter_table",
    "courtship_woods_encounter_table",
    "courtship_mountain_encounter_table",
    "courtship_meadows_encounter_table",
    "courtship_palace_encounter_table",
    "courtship_book_of_secrets_table",
    "courtship_blossoms_magic_item_table",
    "courtship_blossoms_spell_scrolls_table",
    "courtship_lex_shop_table",
    "courtship_apothecary_recipes_table",
    "fd_trap_table",
    "fd_hallucination_table",
    "fd_ruins_content_table",
    "fd_citadel_table",
    "fd_citadel_weird_table",
    "fd_treasure_table",
    "fd_wandering_monsters_table",
    "fd_boss_table",
    "fd_weird_table",
    "fd_horde_table",
    "fd_minions_table",
    "fd_room_content_table",
    "fd_river_encounter_table",
    "fd_river_hazard_table",
    "fd_river_type_table",
    "fd_vermin_table",
    "minion_reaction_table",
    "play_context_table",
    "quest_table",
    "room_content_table",
    "scrolls_table",
    "search_table",
    "secrets_table",
    "special_event_wandering_table",
    "swashbuckler_traits_table",
    "tier_training_costs_table",
    "trap_table",
    "treasure_table",
    "fiendish_foes_treasure_table",
    "fiendish_foes_magic_treasure_table",
    "vermin_reaction_table",
    "wandering_monsters_table",
    "adventure_closeout_workflow_table",
    "adventure_management_browser_table",
    "adventure_package_map_pinning_table",
    "adventure_package_review_workspace_table",
    "adventure_package_registry_diagnostics_table",
    "adventure_package_schema_table",
    "adventure_pdf_source_scan_table",
    "application_artwork_slots_table",
    "artwork_expansion_plan_table",
    "artwork_registry_table",
    "campaign_assignment_integrity_table",
    "campaign_chronicle_event_table",
    "campaign_command_center_table",
    "campaign_worldbuilder_schema_table",
    "character_management_readiness_table",
    "developer_preferences_table",
    "active_registry_tooltips_table",
    "registry_resolver_helpers_table",
    "settings_collapsible_panels_table",
    "reference_table_collapsible_navigation_table",
    "exploration_narrative_layout_table",
    "exploration_objective_clarity_table",
    "go_adventure_closeout_gate_table",
    "go_adventure_setup_readiness_table",
    "go_adventure_tabbed_workflow_table",
    "guidance_task_status_table",
    "modern_dashboard_management_table",
    "modern_tag_workflow_table",
    "playtest_triage_workflow_table",
    "session_supplement_snapshot_table",
    "state_registry_navigation_table",
    "supplement_manifest_registry_table",
    "supplement_reference_filters_table",
    "terrain_registry_navigation_table",
    "tag_closeout_checklist_automation_table",
    "tag_generated_adventure_signoff_table",
    "tag_generated_lead_structure_table",
    "tag_generated_prompt_playtest_table",
    "tag_guild_job_playthrough_audit_table",
    "tag_rumor_playthrough_audit_table",
    "tag_thematic_dungeon_playthrough_audit_table",
    "tag_treasure_map_playthrough_audit_table",
    "user_artwork_placeholders_table",
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
    "chaos_fanatics",
    "corridor_leads",
    "yummy_meal",
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


def test_home_rules_tables_are_all_classified_for_pdf_compliance() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    payload = TestClient(app).get("/api/rules/tables", params={"audience": "all"}).json()
    actual = {key for key in payload if key not in META_TABLE_KEYS and key != "open_items"}
    assert actual == VERIFIED_RULE_TABLE_KEYS


def test_player_rules_tables_hide_app_workflow_tables() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    payload = TestClient(app).get("/api/rules/tables").json()
    assert "equipment_shop_table" in payload
    assert "monster_bestiary_table" in payload
    assert "settings_collapsible_panels_table" not in payload
    assert "tag_guild_job_playthrough_audit_table" not in payload
    assert "adventure_package_schema_table" not in payload
    developer_payload = TestClient(app).get("/api/rules/tables", params={"audience": "developer"}).json()
    assert "equipment_shop_table" not in developer_payload
    assert "settings_collapsible_panels_table" in developer_payload
    assert "adventure_package_schema_table" in developer_payload


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
    assert payload["class_profiles_table"]
    assert payload["expert_skills_table"]
    assert payload["expert_spells_table"]
    assert payload["heroic_skills_table"]
    assert payload["legendary_skills_table"]
    assert payload["class_tricks_implementation_table"]
    assert payload["ee_class_trick_flags_table"]
    assert payload["map_elements_validation_table"]
    assert payload["forsaken_depths_map_elements_validation_table"]
    assert len(payload["forsaken_depths_map_elements_validation_table"]) == 36
    assert payload["forsaken_depths_rivers_map_elements_validation_table"]
    assert len(payload["forsaken_depths_rivers_map_elements_validation_table"]) == 36
    assert payload["forsaken_depths_room_codes_table"]
    assert len(payload["forsaken_depths_room_codes_table"]) == 8
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
    assert "tile catalogs" in app_js
    assert "forsaken_depths_rivers" in app_js
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
    assert payload["audience"] == "player"
    assert any(entry.get("id") == "resting" for entry in payload["entries"])
    assert not any(entry.get("id") == "settings_collapsible_panels_table" for entry in payload["entries"])
    search = client.get("/api/rules/reference", params={"q": "rage"}).json()
    assert search["count"] >= 1
    developer_payload = client.get("/api/rules/reference", params={"audience": "developer"}).json()
    assert developer_payload["audience"] == "developer"
    assert any(entry.get("id") == "settings_collapsible_panels_table" for entry in developer_payload["entries"])


def test_rules_reference_merges_local_exact_pdf_text_index(tmp_path: Path, monkeypatch) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from app import main as main_module

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "rule_text_index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-07-08T10:00:00Z",
                "documents": [{"filename": "Owned Rules.pdf", "pages_indexed": 1}],
                "entries": [
                    {
                        "id": "local-pdf-owned-rules-p12",
                        "title": "Owned Rules p.12",
                        "category": "pdf_text",
                        "implementation_status": "local_exact",
                        "source_page": 12,
                        "source": "DATA_DIR/rules/Owned Rules.pdf",
                        "summary": "Exact local PDF text.",
                        "body": "Exact private wording about lantern oil and dungeon doors.",
                        "keywords": ["Owned Rules.pdf", "local rules pdf"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, data_dir=tmp_path, rules_dir=rules_dir),
    )

    client = TestClient(main_module.app)
    player_payload = client.get("/api/rules/reference", params={"q": "lantern oil"}).json()
    assert player_payload["local_rule_text"]["entry_count"] == 1
    assert any(entry["id"] == "local-pdf-owned-rules-p12" for entry in player_payload["entries"])
    developer_payload = client.get(
        "/api/rules/reference",
        params={"audience": "developer", "q": "lantern oil"},
    ).json()
    assert not any(entry["id"] == "local-pdf-owned-rules-p12" for entry in developer_payload["entries"])


def test_index_rule_pdf_text_writes_local_appdata_index(tmp_path: Path, monkeypatch) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from app import main as main_module
    from app.engine import pdf_text_index

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "Owned Rules.pdf").write_bytes(b"%PDF-local-test")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, data_dir=tmp_path, rules_dir=rules_dir),
    )
    monkeypatch.setattr(
        pdf_text_index,
        "extract_rule_pdf_pages",
        lambda _path: [{"page": 3, "text": "Exact private wording about madness checks."}],
    )

    payload = TestClient(main_module.app).post(
        "/api/rules/index-pdf-text",
        json={"filename": "Owned Rules.pdf"},
    ).json()
    assert payload["pages_indexed"] == 1
    index = json.loads((rules_dir / "rule_text_index.json").read_text(encoding="utf-8"))
    assert index["documents"][0]["filename"] == "Owned Rules.pdf"
    assert index["entries"][0]["body"] == "Exact private wording about madness checks."
    assert index["entries"][0]["source"] == "DATA_DIR/rules/Owned Rules.pdf"


def test_index_rule_pdf_text_applies_manual_printed_page_offset(tmp_path: Path, monkeypatch) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from app import main as main_module
    from app.engine import pdf_text_index

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "Troublesome Towns.pdf").write_bytes(b"%PDF-local-test")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, data_dir=tmp_path, rules_dir=rules_dir),
    )
    monkeypatch.setattr(
        pdf_text_index,
        "extract_rule_pdf_pages",
        lambda _path: [{"page": 8, "text": "House of Ill Repute", "methods": ["layout"]}],
    )

    payload = TestClient(main_module.app).post(
        "/api/rules/index-pdf-text",
        json={"filename": "Troublesome Towns.pdf", "page_offset": -6},
    ).json()
    assert payload["page_offset"] == -6
    index = json.loads((rules_dir / "rule_text_index.json").read_text(encoding="utf-8"))
    entry = index["entries"][0]
    assert entry["pdf_page"] == 8
    assert entry["source_page"] == 2
    assert entry["page_label"] == "p.2 (PDF p.8)"
    assert index["documents"][0]["page_offset"] == -6


def test_pdf_source_offset_is_reused_for_indexing_and_source_scans(tmp_path: Path, monkeypatch) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from app import main as main_module
    from app.engine import pdf_text_index, supplement_sources

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "Troublesome Towns.pdf").write_bytes(b"%PDF-local-test")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, data_dir=tmp_path, rules_dir=rules_dir),
    )
    monkeypatch.setattr(
        supplement_sources,
        "extract_rule_pdf_pages",
        lambda _path: [{"page": 8, "text": "House of Ill Repute", "methods": ["layout"]}],
    )
    monkeypatch.setattr(
        pdf_text_index,
        "extract_rule_pdf_pages",
        lambda _path: [{"page": 8, "text": "House of Ill Repute", "methods": ["layout"]}],
    )
    client = TestClient(main_module.app)

    scan_payload = client.post(
        "/api/supplements/source-scan",
        json={"filename": "Troublesome Towns.pdf", "page_offset": -6},
    ).json()
    assert scan_payload["page_offset"] == -6
    pdfs = client.get("/api/rules/pdfs").json()
    assert pdfs["uploaded"][0]["source_settings"]["page_offset"] == -6

    index_payload = client.post(
        "/api/rules/index-pdf-text",
        json={"filename": "Troublesome Towns.pdf"},
    ).json()
    assert index_payload["page_offset"] == -6
    index = json.loads((rules_dir / "rule_text_index.json").read_text(encoding="utf-8"))
    assert index["entries"][0]["page_label"] == "p.2 (PDF p.8)"


def test_rule_pdf_page_extraction_uses_layout_and_positioned_text() -> None:
    from app.engine import pdf_text_index

    class FakePage:
        def extract_text(self, *args, **kwargs):
            visitor = kwargs.get("visitor_text")
            if visitor:
                visitor("One Bite", None, None, None, None)
                visitor("At A Time", None, None, None, None)
                return "ignored visitor return"
            if kwargs.get("extraction_mode") == "layout":
                return "Sidebar Box\nOne Bite At A Time"
            return "Normal flowing page text only."

    variants = pdf_text_index.extract_rule_page_texts(FakePage())
    body = "\n".join(item["text"] for item in variants)
    assert [item["method"] for item in variants] == ["plain", "layout", "positioned"]
    assert "One Bite At A Time" in body
    assert "One Bite At A Time" in pdf_text_index.clean_rule_pdf_text(body)


def test_supplement_source_scan_writes_unassigned_review_blocks(tmp_path: Path, monkeypatch) -> None:
    from app.engine import supplement_sources

    pdf = tmp_path / "Troublesome Towns.pdf"
    pdf.write_bytes(b"%PDF-local-test")
    monkeypatch.setattr(
        supplement_sources,
        "extract_rule_pdf_pages",
        lambda _path: [
            {
                "page": 3,
                "text": "House of Ill Repute\n\nQuest (Steal): A shady geezer offers a reward.",
                "methods": ["plain", "layout"],
            },
            {
                "page": 4,
                "text": "continued indenture contract.",
                "methods": ["plain", "layout"],
            }
        ],
    )

    result = supplement_sources.scan_supplement_source_pdf(tmp_path, pdf, now="2026-07-08T11:00:00Z", page_offset=-1)
    assert result["blocks"] == 3
    assert result["continuation_candidates"] == 1
    assert result["page_offset"] == -1
    path = tmp_path / "Supplements" / "_sources" / "troublesome-towns" / "source_blocks.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["page_offset"] == -1
    assert "title_page" in payload["assignment_options"]
    assert "table_of_contents" in payload["assignment_options"]
    assert "artwork_filler" in payload["assignment_options"]
    assert "history" in payload["assignment_options"]
    assert payload["raw_blocks"][0]["text"] == "House of Ill Repute"
    assert payload["reviewed_blocks"][0]["text"] == "House of Ill Repute"
    assert payload["blocks"][0]["assignment"] == "unassigned"
    assert payload["blocks"][0]["id"] == "troublesome-towns-p2-pdf3-b001"
    assert payload["blocks"][0]["text"] == "House of Ill Repute"
    assert payload["blocks"][0]["pdf_page"] == 3
    assert payload["blocks"][0]["source_page"] == 2
    assert payload["blocks"][0]["page_label"] == "p.2 (PDF p.3)"
    assert payload["blocks"][0]["extraction_methods"] == ["plain", "layout"]
    assert payload["continuation_candidates"][0]["page_label"] == "p.2 (PDF p.3) to p.3 (PDF p.4)"
    assert payload["continuation_candidates"][0]["assignment"] == "page_boundary_candidate"
    assert "continued indenture contract" in payload["continuation_candidates"][0]["text"]
    scans = supplement_sources.list_supplement_source_scans(tmp_path)
    assert scans == [
        {
            "source_id": "troublesome-towns",
            "source_pdf": "DATA_DIR/rules/Troublesome Towns.pdf",
            "updated_at": "2026-07-08T11:00:00Z",
            "page_offset": -1,
            "blocks": 3,
            "raw_blocks": 3,
            "continuation_candidates": 1,
            "artwork": 0,
            "reviewed_blocks": 0,
            "assignment_counts": {"unassigned": 3},
            "path": str(path),
        }
    ]


def test_supplement_source_scan_preserves_existing_assignment(tmp_path: Path, monkeypatch) -> None:
    from app.engine import supplement_sources

    pdf = tmp_path / "Mixed Book.pdf"
    pdf.write_bytes(b"%PDF-local-test")
    source_dir = tmp_path / "Supplements" / "_sources" / "mixed-book"
    source_dir.mkdir(parents=True)
    (source_dir / "source_blocks.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_id": "mixed-book",
                "blocks": [
                    {
                        "source_page": 4,
                        "text": "Foe: Clockwork Beggar L4",
                        "assignment": "foe",
                        "review_status": "checked",
                        "notes": "Manual review kept.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        supplement_sources,
        "extract_rule_pdf_pages",
        lambda _path: [{"page": 4, "text": "Foe: Clockwork Beggar L4", "methods": ["layout"]}],
    )

    supplement_sources.scan_supplement_source_pdf(tmp_path, pdf, now="2026-07-08T11:05:00Z")
    payload = json.loads((source_dir / "source_blocks.json").read_text(encoding="utf-8"))
    assert payload["blocks"][0]["assignment"] == "foe"
    assert payload["blocks"][0]["review_status"] == "checked"
    assert payload["blocks"][0]["notes"] == "Manual review kept."
    assert payload["reviewed_blocks"][0]["assignment"] == "foe"
    assert payload["raw_blocks"][0]["text"] == "Foe: Clockwork Beggar L4"


def test_supplement_source_rescan_preserves_reviewed_edits_when_raw_blocks_change(tmp_path: Path, monkeypatch) -> None:
    from app.engine import supplement_sources

    pdf = tmp_path / "Mutable Book.pdf"
    pdf.write_bytes(b"%PDF-local-test")
    pages = [{"page": 1, "text": "Original block", "methods": ["layout"]}]
    monkeypatch.setattr(supplement_sources, "extract_rule_pdf_pages", lambda _path: pages)

    supplement_sources.scan_supplement_source_pdf(tmp_path, pdf, now="2026-07-08T11:05:00Z")
    supplement_sources.update_supplement_source_block(
        tmp_path,
        "mutable-book",
        "mutable-book-p1-b001",
        {"text": "Reviewed edited block", "assignment": "title_page", "review_status": "checked"},
    )
    pages[:] = [{"page": 1, "text": "Changed raw extraction", "methods": ["layout"]}]
    supplement_sources.scan_supplement_source_pdf(tmp_path, pdf, now="2026-07-08T11:06:00Z")

    payload = json.loads((tmp_path / "Supplements" / "_sources" / "mutable-book" / "source_blocks.json").read_text(encoding="utf-8"))
    assert payload["raw_blocks"][0]["text"] == "Changed raw extraction"
    assert payload["reviewed_blocks"][0]["text"] == "Reviewed edited block"
    assert payload["reviewed_blocks"][0]["assignment"] == "title_page"


def test_source_block_review_update_split_and_merge(tmp_path: Path, monkeypatch) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from app import main as main_module
    from app.engine import supplement_sources

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "Mixed Book.pdf").write_bytes(b"%PDF-local-test")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, data_dir=tmp_path, rules_dir=rules_dir),
    )
    monkeypatch.setattr(
        supplement_sources,
        "extract_rule_pdf_pages",
        lambda _path: [{"page": 1, "text": "Alpha\n\nBeta", "methods": ["layout"]}],
    )
    client = TestClient(main_module.app)
    client.post("/api/supplements/source-scan", json={"filename": "Mixed Book.pdf"})

    save_payload = client.patch(
        "/api/supplements/source-scans/mixed-book/blocks/mixed-book-p1-b001",
        json={"text": "Alpha edited", "assignment": "rule_text", "review_status": "checked"},
    ).json()
    assert save_payload["block"]["assignment"] == "rule_text"
    assert save_payload["block"]["text"] == "Alpha edited"

    split_payload = client.post(
        "/api/supplements/source-scans/mixed-book/blocks/mixed-book-p1-b002/split",
        json={"parts": ["Beta part 1", "Beta part 2"]},
    ).json()
    assert len(split_payload["blocks"]) == 2

    merge_payload = client.post(
        "/api/supplements/source-scans/mixed-book/blocks/merge-selected",
        json={"block_ids": ["mixed-book-p1-b002-split01", "mixed-book-p1-b002-split02"]},
    ).json()
    assert "Beta part 1" in merge_payload["block"]["text"]
    assert "Beta part 2" in merge_payload["block"]["text"]
    move_payload = client.post(
        "/api/supplements/source-scans/mixed-book/blocks/mixed-book-p1-b001/move",
        json={"direction": "down"},
    ).json()
    assert move_payload["block"]["id"] == "mixed-book-p1-b001"
    saved = client.get("/api/supplements/source-scans/mixed-book").json()
    assert saved["blocks"][1]["id"] == "mixed-book-p1-b001"
    detail = client.get("/api/supplements/source-scans/mixed-book").json()
    assert detail["source_pdf_url"] == "/api/rules/pdf/Mixed%20Book.pdf"
    assert detail["source_pdf_page_url"] == "/api/rules/pdf-page/Mixed%20Book.pdf"


def test_source_artwork_extraction_and_review_preserves_metadata(tmp_path: Path, monkeypatch) -> None:
    import sys
    import types

    from app.engine import supplement_sources

    class FakeImage:
        name = "portrait.png"
        data = b"png-data"

    class FakePage:
        images = [FakeImage()]

    class FakeReader:
        def __init__(self, _path: str):
            self.pages = [FakePage()]

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=FakeReader))
    pdf = tmp_path / "Artwork Book.pdf"
    pdf.write_bytes(b"%PDF-local-test")

    result = supplement_sources.extract_supplement_source_artwork(tmp_path, pdf, now="2026-07-09T10:00:00Z", page_offset=-1)
    assert result["raw_artwork"] == 1
    payload = supplement_sources.load_supplement_source_scan(tmp_path, "artwork-book")
    art = payload["reviewed_artwork"][0]
    assert art["page_label"] == "p.1 (PDF p.1)" or art["page_label"] == "p.1"
    assert art["category"] == "unknown"
    assert (tmp_path / "Supplements" / "_sources" / "artwork-book" / "artwork" / "raw" / "page-001-image-01.png").read_bytes() == b"png-data"

    supplement_sources.update_supplement_source_artwork(
        tmp_path,
        "artwork-book",
        art["id"],
        {"title": "Goblin portrait", "category": "foe", "notes": "Use for goblin entry.", "review_status": "checked"},
    )
    supplement_sources.extract_supplement_source_artwork(tmp_path, pdf, now="2026-07-09T10:01:00Z", page_offset=-1)
    payload = supplement_sources.load_supplement_source_scan(tmp_path, "artwork-book")
    assert payload["reviewed_artwork"][0]["title"] == "Goblin portrait"
    assert payload["reviewed_artwork"][0]["category"] == "foe"


def test_source_artwork_extraction_renders_pages_when_no_embedded_images(tmp_path: Path, monkeypatch) -> None:
    import sys
    import types

    from app.engine import supplement_sources

    class FakePage:
        images = []

    class FakeReader:
        def __init__(self, _path: str):
            self.pages = [FakePage(), FakePage()]

    def fake_run(command, capture_output, text, check, timeout):
        output_prefix = Path(command[-1])
        output_prefix.parent.mkdir(parents=True, exist_ok=True)
        output_prefix.with_suffix(".png").write_bytes(b"rendered-page")

        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        return Result()

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=FakeReader))
    monkeypatch.setattr(supplement_sources.shutil, "which", lambda name: "pdftoppm" if name == "pdftoppm" else None)
    monkeypatch.setattr(supplement_sources.subprocess, "run", fake_run)
    pdf = tmp_path / "Circular Art.pdf"
    pdf.write_bytes(b"%PDF-local-test")

    result = supplement_sources.extract_supplement_source_artwork(tmp_path, pdf, now="2026-07-09T11:00:00Z", page_offset=0)
    assert result["raw_artwork"] == 2
    payload = supplement_sources.load_supplement_source_scan(tmp_path, "circular-art")
    assert payload["reviewed_artwork"][0]["candidate_type"] == "rendered_page"
    assert payload["reviewed_artwork"][0]["category"] == "review_later"
    assert (tmp_path / "Supplements" / "_sources" / "circular-art" / "artwork" / "rendered_pages" / "page-001-render.png").read_bytes() == b"rendered-page"


def test_rule_pdf_page_preview_renders_cached_png(tmp_path: Path, monkeypatch) -> None:
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from app import main as main_module

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "Mixed Book.pdf").write_bytes(b"%PDF-local-test")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, data_dir=tmp_path, rules_dir=rules_dir),
    )
    monkeypatch.setattr(main_module.shutil, "which", lambda name: "pdftoppm" if name == "pdftoppm" else None)

    def fake_run(command, capture_output, text, check, timeout):
        output_prefix = Path(command[-1])
        output_prefix.parent.mkdir(parents=True, exist_ok=True)
        output_prefix.with_suffix(".png").write_bytes(b"fake-png")

        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        return Result()

    monkeypatch.setattr(main_module.subprocess, "run", fake_run)

    response = TestClient(main_module.app).get("/api/rules/pdf-page/Mixed%20Book.pdf?page=2")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"fake-png"


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
