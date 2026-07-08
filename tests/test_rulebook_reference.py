from __future__ import annotations

import json
import re
from pathlib import Path

from app.rules.repository import RulesRepository

APP_ONLY_REFERENCE_IDS = {
    "player_export",
    "saved_games",
    "home_character_sheets",
    "icon_registry",
    "rules_tables_index",
    "play_context",
    "adventure_closeout_workflow",
    "campaign_chronicle",
    "guidance_task_statuses",
    "adventure_closeout_workflow_table",
    "campaign_chronicle_event_table",
    "guidance_task_status_table",
    "campaign_command_center",
    "go_adventure_closeout_gates",
    "campaign_command_center_table",
    "go_adventure_closeout_gate_table",
    "modern_tag_workflow_completion",
    "tag_generated_adventure_signoff",
    "tag_generated_lead_structure",
    "tag_closeout_checklist_automation",
    "tag_generated_prompt_playtest",
    "tag_local_narrative_overrides",
    "tag_rumor_playthrough_audit",
    "tag_treasure_map_playthrough_audit",
    "tag_thematic_dungeon_playthrough_audit",
    "modern_tag_workflow_table",
    "tag_generated_adventure_signoff_table",
    "tag_generated_lead_structure_table",
    "tag_closeout_checklist_automation_table",
    "tag_generated_prompt_playtest_table",
    "tag_rumor_playthrough_audit_table",
    "tag_treasure_map_playthrough_audit_table",
    "tag_thematic_dungeon_playthrough_audit_table",
    "campaign_world_builder",
    "campaign_membership_boundaries",
    "friendly_settlements",
    "troublesome_towns_placeholder",
    "campaign_hex_map_placeholder",
    "campaign_management_editing",
    "campaign_assignment_integrity",
    "campaign_assignment_integrity_table",
    "campaign_worldbuilder_schema_table",
    "modern_dashboard_management_polish",
    "modern_dashboard_management_table",
    "party_troupe_management",
    "settlement_management_workflow",
    "character_management_deep_polish",
    "go_adventure_setup_readiness",
    "go_adventure_tabbed_workflow",
    "exploration_narrative_layout",
    "user_artwork_placeholders",
    "application_artwork_slots",
    "camp_screen",
    "artwork_manager",
    "developer_playtest_preferences",
    "playtest_triage_workflow",
    "exploration_objective_clarity",
    "adventure_management_browser",
    "go_adventure_tabbed_workflow_table",
    "exploration_narrative_layout_table",
    "user_artwork_placeholders_table",
    "application_artwork_slots_table",
    "developer_preferences_table",
    "playtest_triage_workflow_table",
    "exploration_objective_clarity_table",
    "adventure_management_browser_table",
    "artwork_expansion_plan_table",
    "item_tooltip_coverage_table",
    "rules_artwork_registry",
    "pdf_artwork_boundary",
    "adventure_package_map_pinning_table",
    "adventure_package_review_workspace_table",
    "adventure_package_registry_diagnostics_table",
    "adventure_pdf_source_scan_table",
    "adventure_package_schema_table",
    "active_registry_tooltips_table",
    "registry_resolver_helpers_table",
    "settings_collapsible_panels_table",
    "reference_table_collapsible_navigation_table",
    "session_supplement_snapshot_table",
    "state_registry_navigation_table",
    "supplement_manifest_registry_table",
    "supplement_reference_filters_table",
    "terrain_registry_navigation_table",
}


def test_rulebook_reference_loads() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    entries = rules.rulebook_reference()
    assert len(entries) >= 110
    assert any(entry.get("id") == "resting" for entry in entries)
    assert all(entry.get("implementation_status") for entry in entries)
    per_skill = [entry for entry in entries if str(entry.get("id", "")).startswith("expert_skill_")]
    assert per_skill == []


def test_rulebook_reference_source_integrity() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    entries = rules.rulebook_reference()

    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids))
    assert {entry["id"] for entry in entries if entry.get("source_page") == 0} == APP_ONLY_REFERENCE_IDS

    allowed_categories = {"app_assets", "campaign", "classes", "combat", "economy", "equipment", "exploration", "quests", "spells", "tag"}
    allowed_statuses = {"implemented", "validated", "full", "partial", "planned"}
    for entry in entries:
        assert entry.get("title"), entry["id"]
        assert entry.get("summary"), entry["id"]
        assert entry.get("body"), entry["id"]
        assert entry.get("category") in allowed_categories, entry["id"]
        assert entry.get("implementation_status") in allowed_statuses, entry["id"]
        assert isinstance(entry.get("source_page"), int), entry["id"]
        if entry["id"] in APP_ONLY_REFERENCE_IDS:
            assert entry["source_page"] == 0, entry["id"]
        else:
            assert entry["source_page"] > 0, entry["id"]


def test_rulebook_reference_table_mentions_resolve_to_home_tables() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    entries = rules.rulebook_reference()
    table_keys = set(TestClient(app).get("/api/rules/tables").json())
    mentioned: set[str] = set()
    for entry in entries:
        text = " ".join(str(entry.get(key, "")) for key in ("title", "summary", "body"))
        mentioned.update(re.findall(r"\b[a-z][a-z0-9_]*_table\b", text))

    assert mentioned
    assert sorted(mentioned - table_keys) == []


def test_rules_tables_index_covers_every_verified_home_table() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    by_id = {entry["id"]: entry for entry in rules.rulebook_reference()}
    index_body = by_id["rules_tables_index"]["body"]
    table_keys = {
        key
        for key in TestClient(app).get("/api/rules/tables").json()
        if key not in {"ruleset_status", "validation", "open_items"}
    }

    missing = sorted(key for key in table_keys if key not in index_body)
    assert missing == []


def test_rulebook_reference_no_per_skill_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    ids = {entry.get("id") for entry in rules.rulebook_reference()}
    assert "expert_skills" in ids
    assert "expert_spells" in ids
    assert "expert_skill_effects" not in ids
    assert not any(item.startswith("expert_skill_") for item in ids if item not in {"expert_skills", "expert_spells"})


def test_rulebook_reference_search_rest() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    payload = rules.search_reference(q="rest")
    ids = {entry["id"] for entry in payload["entries"]}
    assert "resting" in ids


def test_rulebook_reference_merges_appdata_override(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    packaged = root / "data" / "rules"
    override = tmp_path / "rules"
    override.mkdir()
    (override / "rulebook_reference.json").write_text(
        json.dumps({"entries": [{"id": "resting", "title": "Custom Rest Title", "category": "exploration"}]}),
        encoding="utf-8",
    )
    rules = RulesRepository(packaged, override)
    entries = rules.rulebook_reference()
    assert len(entries) >= 110
    resting = next(entry for entry in entries if entry["id"] == "resting")
    assert resting["title"] == "Custom Rest Title"
    assert any(entry["id"] == "dungeon_entrance" for entry in entries)


def test_rulebook_reference_category_filter() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    payload = rules.search_reference(category="classes")
    assert payload["entries"]
    assert all(entry.get("category") == "classes" for entry in payload["entries"])


def test_home_reference_filters_cover_payload_statuses_and_categories() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    entries = rules.rulebook_reference()
    index_html = (root / "src" / "app" / "static" / "index.html").read_text(encoding="utf-8")

    statuses = {entry["implementation_status"] for entry in entries}
    categories = {entry["category"] for entry in entries}
    for status in statuses:
        assert f'value="{status}"' in index_html
    for category in categories:
        assert f'value="{category}"' in index_html
    assert "PDFs in Rules" in index_html


def test_rulebook_reference_covers_camp_bank_and_magic_shop_limits() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    by_id = {entry["id"]: entry for entry in rules.rulebook_reference()}

    camp_body = by_id["camp_outside"]["body"]
    transfer_body = by_id["transfer_items"]["body"]
    shop_body = by_id["equipment_shop"]["body"]
    home_sheet_body = by_id["home_character_sheets"]["body"]
    icons_body = by_id["icon_registry"]["body"]
    paladin_body = by_id["paladin_prayer"]["body"]

    assert "Camp Outside panel" in camp_body
    assert "home bank is available" in camp_body
    assert "Home Screen Bank button" in camp_body
    assert "available roster heroes" in transfer_body
    assert "stored gear" in home_sheet_body
    assert "Banked XP spending" in home_sheet_body
    assert "generated defaults" in icons_body
    assert "monster-goblins" in icons_body
    assert "Prayer heal target selector" in paladin_body
    assert "Expanded Edition pp.81-88" in shop_body
    assert "fixed resale value" in shop_body
    assert "Recipe for a Potion" in shop_body
    assert "50gp potion price" in shop_body
    assert "Someone Will Pay Big Money for That triples" in shop_body
