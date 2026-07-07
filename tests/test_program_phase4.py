from __future__ import annotations

from fastapi.testclient import TestClient

from app import main
from app.engine.abyss_tables import abyss_table_roll_keys, abyss_table_rows
from app.engine.tag_campaign import add_guidance_task, record_adventure_complete, save_campaign
from app.engine.forsaken_depths_heroic_spells import heroic_spell_names, is_fd_heroic_spell
from app.engine.ruleset_profiles import (
    class_allowed_for_profile,
    profile_by_id,
    resolve_profile_for_adventure,
)
from app.engine.states import state_payload
from app.engine.supplements import (
    LOCKED_CORE_SUPPLEMENT_ID,
    active_supplement_ids_for_legacy_session,
    enabled_supplement_ids_from_selection,
    supplement_payload,
)
from app.engine.terrain_registry import terrain_payload
from app.schemas import SessionState


def test_ruleset_profiles_resolve_legacy_ruleset_fields() -> None:
    ee = resolve_profile_for_adventure("random", ruleset="ee", courtship_enabled=False)
    assert ee.id == "ee_random"
    assert ee.ruleset == "ee"
    assert ee.courtship_enabled is False

    fd = resolve_profile_for_adventure("random", ruleset="forsaken_depths", courtship_enabled=True)
    assert fd.id == "forsaken_depths"
    assert fd.courtship_enabled is True
    assert "courtship" in fd.source_books

    fd_plain = resolve_profile_for_adventure("random", profile_id="forsaken_depths_no_courtship")
    assert fd_plain.courtship_enabled is False
    assert not class_allowed_for_profile("wandering_alchemist", fd_plain)
    assert class_allowed_for_profile("wandering_alchemist", fd)


def test_ruleset_profiles_api(client: TestClient) -> None:
    response = client.get("/api/rules/profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert any(item["id"] == "ee_random" for item in profiles)
    assert any(item["id"] == "abyss" and "abyss" in item["source_books"] for item in profiles)
    assert any(item["id"] == "forsaken_depths" for item in profiles)

    filtered = client.get("/api/rules/classes", params={"ruleset_profile_id": "forsaken_depths_no_courtship"})
    assert filtered.status_code == 200
    class_ids = {item["id"] for item in filtered.json()}
    assert "wandering_alchemist" not in class_ids
    assert "warrior" in class_ids


def test_supplement_registry_marks_core_locked_and_legacy_fields() -> None:
    payload = supplement_payload()
    assert payload["schema_version"] == 1
    assert payload["read_only"] is True
    assert payload["locked_core_id"] == LOCKED_CORE_SUPPLEMENT_ID

    supplements = {item["id"]: item for item in payload["supplements"]}
    core = supplements[LOCKED_CORE_SUPPLEMENT_ID]
    assert core["locked"] is True
    assert core["enabled_by_default"] is True
    assert {"rules", "states", "room_tiles", "terrain_types"}.issubset(set(core["capabilities"]))

    forsaken_depths = supplements["forsaken-depths"]
    assert {"room_tiles", "terrain_types", "generators"}.issubset(set(forsaken_depths["capabilities"]))
    assert "forsaken_depths_rivers" in forsaken_depths["legacy_mappings"]["tile_catalog"]

    imported = supplements["imported-adventures"]
    assert imported["status"] == "review_only"
    assert {"maps", "locations", "narrative", "states", "rules"}.issubset(set(imported["capabilities"]))

    legacy = {item["field"]: item for item in payload["legacy_fields"]}
    for field in ["ruleset", "ruleset_profile_id", "tile_catalog", "courtship_enabled", "fiendish_foes_enabled", "tag_banking_enabled"]:
        assert legacy[field]["status"] == "legacy_compatibility"
    assert legacy["ruleset_profile_id"]["replacement"] == "active_supplements"


def test_supplements_api_is_read_only_registry(client: TestClient) -> None:
    response = client.get("/api/supplements")
    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    assert payload["locked_core_id"] == "expanded-edition-core"
    ids = {item["id"] for item in payload["supplements"]}
    assert {"expanded-edition-core", "four-against-the-abyss", "forsaken-depths", "courtship", "tag", "imported-adventures"}.issubset(ids)


def test_tag_banking_does_not_lock_tag_supplement_for_random_sessions() -> None:
    assert active_supplement_ids_for_legacy_session(tag_banking_enabled=True) == [LOCKED_CORE_SUPPLEMENT_ID]
    assert active_supplement_ids_for_legacy_session(tag_generated=True) == [LOCKED_CORE_SUPPLEMENT_ID, "tag"]


def test_enabled_supplement_preferences_keep_core_and_dependencies() -> None:
    assert enabled_supplement_ids_from_selection([]) == [LOCKED_CORE_SUPPLEMENT_ID]
    assert enabled_supplement_ids_from_selection(["forsaken-depths"]) == [LOCKED_CORE_SUPPLEMENT_ID, "forsaken-depths"]


def test_state_registry_maps_existing_statuses_and_counters() -> None:
    payload = state_payload()
    assert payload["schema_version"] == 1
    assert payload["read_only"] is True
    states = {item["id"]: item for item in payload["states"]}

    dark_plague = states["dark-plague"]
    assert dark_plague["source"]["supplement_id"] == "four-against-the-abyss"
    assert dark_plague["source"]["page"] == 37
    assert "Dark Plague" in dark_plague["legacy_mappings"]["statuses"]

    madness = states["madness"]
    assert madness["value_type"] == "counter"
    assert "PartyMemberState.madness" in madness["legacy_mappings"]["fields"]

    hungry = states["hungry"]
    assert "SessionState.hunger_rounds" in hungry["legacy_mappings"]["fields"]

    psychic = states["fd-psychic-residue-save"]
    assert psychic["source"]["page"] == 56
    assert "FD Psychic Residue +3 Save" in psychic["legacy_mappings"]["statuses"]

    legacy = {item["field"]: item for item in payload["legacy_fields"]}
    assert legacy["PartyMemberState.statuses"]["status"] == "legacy_compatibility"
    assert "madness_and_fear" in payload["families"]
    assert "equipment" in payload["scopes"]


def test_states_api_is_read_only_registry(client: TestClient) -> None:
    response = client.get("/api/states")
    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    ids = {item["id"] for item in payload["states"]}
    assert {"dark-plague", "lycanthropy", "madness", "hungry", "envenomed-weapon", "fd-psychic-residue-save"}.issubset(ids)


def test_terrain_registry_maps_existing_environment_and_terrain_values() -> None:
    payload = terrain_payload()
    assert payload["schema_version"] == 1
    assert payload["read_only"] is True
    records = {item["id"]: item for item in payload["terrain"]}

    assert {"dungeon", "caverns", "fungal_grottoes"}.issubset(set(payload["environment_values"]))
    assert {"indoor", "forest", "swamp", "jungle", "desert", "river"}.issubset(set(payload["terrain_values"]))
    assert {"river", "lake", "seashore"}.issubset(set(payload["water_values"]))
    assert {"forest", "swamp", "jungle"} == set(payload["entangle_values"])
    assert {"forest", "jungle"} == set(payload["forest_pathway_values"])

    forest = records["forest"]
    assert "Entangle can be used" in forest["interactions"]
    assert "Forest Pathway can be used" in forest["interactions"]

    fd_river = records["fd-river-bank"]
    assert fd_river["source"]["supplement_id"] == "forsaken-depths"
    assert "forsaken_depths_rivers" in fd_river["legacy_mappings"]["tile_catalog"]

    courtship_water = records["courtship-demesne-water"]
    assert courtship_water["source"]["page"] == 27
    assert courtship_water["review_status"] == "source_backed"

    legacy = {item["field"]: item for item in payload["legacy_fields"]}
    assert legacy["TileState.terrain"]["status"] == "legacy_compatibility"


def test_terrain_api_is_read_only_registry(client: TestClient) -> None:
    response = client.get("/api/terrain")
    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    ids = {item["id"] for item in payload["terrain"]}
    assert {"dungeon", "caverns", "fungal_grottoes", "forest", "water", "fd-river-bank", "courtship-demesne-water"}.issubset(ids)


def test_campaign_api_updates_tag_settlement(client: TestClient) -> None:
    response = client.put(
        "/api/campaign",
        json={
            "settlement_name": "Stoneford",
            "settlement_size": 2,
            "settlement_notes": "Has a guild apothecary.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["settlement_name"] == "Stoneford"
    assert payload["settlement_size"] == 2
    assert payload["settlement_notes"] == "Has a guild apothecary."


def test_app_preferences_persist_developer_fixed_result_selector(client: TestClient) -> None:
    response = client.get("/api/preferences")
    assert response.status_code == 200
    assert response.json()["show_tag_fixed_result_selector"] is False
    assert response.json()["enabled_supplement_ids"] == [LOCKED_CORE_SUPPLEMENT_ID]

    saved = client.put(
        "/api/preferences",
        json={"show_tag_fixed_result_selector": True, "enabled_supplement_ids": ["forsaken-depths", "tag"]},
    )
    assert saved.status_code == 200
    assert saved.json()["show_tag_fixed_result_selector"] is True
    assert saved.json()["enabled_supplement_ids"] == [LOCKED_CORE_SUPPLEMENT_ID, "forsaken-depths", "tag"]

    reloaded = client.get("/api/preferences")
    assert reloaded.status_code == 200
    assert reloaded.json()["show_tag_fixed_result_selector"] is True
    assert reloaded.json()["enabled_supplement_ids"] == [LOCKED_CORE_SUPPLEMENT_ID, "forsaken-depths", "tag"]

    rejected = client.put("/api/preferences", json={"enabled_supplement_ids": ["made-up-book"]})
    assert rejected.status_code == 400


def test_campaign_api_travels_to_new_tag_settlement(client: TestClient, monkeypatch) -> None:
    from app.engine import tag_campaign

    rolls = iter([6, 5, 5, 5])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    response = client.post(
        "/api/campaign/tag/travel-settlement",
        json={"destination_name": "Diram", "use_hex_map": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign"]["settlement_name"] == "Diram"
    assert payload["campaign"]["settlement_size"] == 3
    assert payload["campaign"]["days_passed"] == 12
    assert payload["entry"]["days"] == 12


def test_campaign_api_creates_selects_and_deletes_tag_settlements(client: TestClient) -> None:
    created = client.post(
        "/api/campaign/tag/settlement",
        json={"action": "create", "name": "Blue Ford", "size": 1, "notes": "River market."},
    )
    assert created.status_code == 200
    payload = created.json()
    settlement_id = payload["settlement"]["id"]
    assert payload["campaign"]["settlement_name"] == "Blue Ford"
    assert payload["campaign"]["settlement_size"] == 1
    assert any(item["name"] == "Blue Ford" for item in payload["campaign"]["tag_settlements"])

    client.post(
        "/api/campaign/tag/settlement",
        json={"action": "create", "name": "Red Mill", "size": -1, "notes": "Small road stop."},
    )
    selected = client.post(
        "/api/campaign/tag/settlement",
        json={"action": "select", "settlement_id": settlement_id},
    )
    assert selected.status_code == 200
    assert selected.json()["campaign"]["settlement_name"] == "Blue Ford"

    deleted = client.post(
        "/api/campaign/tag/settlement",
        json={"action": "delete", "settlement_id": settlement_id},
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert all(item["name"] != "Blue Ford" for item in deleted.json()["campaign"]["tag_settlements"])


def test_campaign_api_lists_tag_services(client: TestClient) -> None:
    client.put("/api/campaign", json={"settlement_size": 0})
    response = client.get("/api/campaign/tag/services")

    assert response.status_code == 200
    services = response.json()["services"]
    assert [service["key"] for service in services[:24]] == [
        "bank_account",
        "bank_inheritance",
        "magic_locker",
        "platinum_exchange",
        "hidden_treasure_trove",
        "resurrection_blessing_tags",
        "gems_jewelry_conversion",
        "bag_of_carrying",
        "ten_foot_pole",
        "lantern_hook",
        "very_nutritious_food",
        "poison_resistance_training",
        "martial_arts_training",
        "gambling_house",
        "treasure_maps",
        "moneylenders",
        "good_boots",
        "flammable_oil",
        "horn",
        "wineskin",
        "flail_axe",
        "aspergillum",
        "availability_rolls",
        "streetwise_rules",
    ]
    assert services[2]["status"] == "available"
    assert services[3]["status"] == "church_only"
    assert services[7]["availability_difficulty"] == 6
    assert services[15]["action"] == "moneylender_follow"
    assert services[18]["action"] == "horn_attract"


def test_rules_tables_api_includes_modern_large_reference_groups(client: TestClient) -> None:
    response = client.get("/api/rules/tables")
    assert response.status_code == 200
    payload = response.json()
    for key in [
        "monster_bestiary_table",
        "monster_reaction_tables",
        "map_elements_table",
        "icon_registry_table",
        "modern_tag_workflow_table",
        "tag_generated_adventure_signoff_table",
        "tag_generated_lead_structure_table",
        "tag_closeout_checklist_automation_table",
        "tag_generated_prompt_playtest_table",
        "tag_rumor_playthrough_audit_table",
        "tag_treasure_map_playthrough_audit_table",
        "tag_thematic_dungeon_playthrough_audit_table",
        "go_adventure_tabbed_workflow_table",
        "exploration_narrative_layout_table",
        "playtest_triage_workflow_table",
        "exploration_objective_clarity_table",
        "adventure_management_browser_table",
        "adventure_package_map_pinning_table",
        "adventure_package_review_workspace_table",
        "adventure_package_schema_table",
        "adventure_pdf_source_scan_table",
        "artwork_expansion_plan_table",
        "application_artwork_slots_table",
        "developer_preferences_table",
        "user_artwork_placeholders_table",
    ]:
        assert key in payload
        assert len(payload[key]) > 0
    assert any(row["name"] for row in payload["monster_bestiary_table"])
    assert any(row["catalog"] == "forsaken_depths" for row in payload["map_elements_table"])


def test_create_session_stores_ruleset_profile(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Profile Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "Profile Party", "character_ids": character_ids})
    assert party_response.status_code == 200

    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "random",
            "ruleset_profile_id": "forsaken_depths_no_courtship",
        },
    )
    assert session_response.status_code == 200
    payload = session_response.json()
    assert payload["ruleset_profile_id"] == "forsaken_depths_no_courtship"
    assert payload["ruleset"] == "forsaken_depths"
    assert payload["courtship_enabled"] is False
    assert payload["active_supplement_ids"] == ["expanded-edition-core", "forsaken-depths"]
    assert payload["supplement_registry_version"] == 1
    assert payload["state_registry_version"] == 1
    assert payload["terrain_registry_version"] == 1


def test_create_session_snapshots_courtship_supplement(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Courtship Snapshot Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "Courtship Snapshot Party", "character_ids": character_ids})
    assert party_response.status_code == 200

    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "courtship-demesne",
        },
    )
    assert session_response.status_code == 200
    payload = session_response.json()
    assert payload["ruleset_profile_id"] == "courtship_demesne"
    assert payload["active_supplement_ids"] == ["expanded-edition-core", "forsaken-depths", "courtship"]


def test_legacy_session_without_snapshot_metadata_still_loads() -> None:
    session = SessionState.model_validate(
        {
            "id": "legacy-session",
            "party_id": "party",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [],
            "map_state": {"width": 31, "height": 31, "tiles": [], "current_tile_id": ""},
            "created_at": "2026-07-07T00:00:00Z",
            "updated_at": "2026-07-07T00:00:00Z",
        }
    )
    assert session.active_supplement_ids == []
    assert session.supplement_registry_version == 0
    assert session.state_registry_version == 0
    assert session.terrain_registry_version == 0


def test_campaign_world_assignment_propagates_to_parties_and_characters(client: TestClient) -> None:
    created = client.post(
        "/api/campaign/world",
        json={"action": "create", "entity": "campaign", "name": "Second World", "description": "Assignment test."},
    )
    assert created.status_code == 200
    second_campaign_id = created.json()["campaign"]["active_world_campaign_id"]

    settlement = client.post(
        "/api/campaign/world",
        json={"action": "create", "entity": "settlement", "name": "Riverhome", "campaign_id": second_campaign_id, "size": 1},
    )
    assert settlement.status_code == 200
    settlement_id = settlement.json()["campaign"]["world_settlements"][-1]["id"]

    guild = client.post(
        "/api/campaign/world",
        json={"action": "create", "entity": "guild", "name": "River Guild", "campaign_id": second_campaign_id},
    )
    assert guild.status_code == 200
    guild_id = guild.json()["campaign"]["world_guilds"][-1]["id"]

    troupe = client.post(
        "/api/campaign/world",
        json={
            "action": "create",
            "entity": "troupe",
            "name": "River Troupe",
            "campaign_id": second_campaign_id,
            "guild_id": guild_id,
            "home_settlement_id": settlement_id,
        },
    )
    assert troupe.status_code == 200
    troupe_id = troupe.json()["campaign"]["world_troupes"][-1]["id"]

    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"World Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_id = response.json()["id"]
        character_ids.append(character_id)
        assigned = client.post(
            "/api/campaign/world",
            json={"action": "assign_character_troupe", "character_id": character_id, "troupe_id": troupe_id},
        )
        assert assigned.status_code == 200

    party_response = client.post(
        "/api/parties",
        json={"name": "World Party", "character_ids": character_ids, "troupe_id": troupe_id},
    )
    assert party_response.status_code == 200
    party = party_response.json()
    assert party["campaign_id"] == second_campaign_id
    assert party["troupe_id"] == troupe_id

    for character_id in character_ids:
        character = client.get("/api/characters").json()
        row = next(item for item in character if item["id"] == character_id)
        assert row["campaign_id"] == second_campaign_id
        assert row["guild_id"] == guild_id
        assert row["troupe_id"] == troupe_id
        assert row["party_id"] == party["id"]

    moved = client.post(
        "/api/campaign/world",
        json={"action": "assign", "entity": "troupe", "troupe_id": troupe_id, "campaign_id": "norindaal"},
    )
    assert moved.status_code == 200
    party_after = next(item for item in client.get("/api/parties").json() if item["id"] == party["id"])
    assert party_after["campaign_id"] == "norindaal"
    characters_after = client.get("/api/characters").json()
    assert {row["campaign_id"] for row in characters_after if row["id"] in character_ids} == {"norindaal"}


def test_adventure_completion_creates_chronicle_and_guidance(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Closeout Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])
    party_response = client.post("/api/parties", json={"name": "Closeout Party", "character_ids": character_ids})
    assert party_response.status_code == 200
    party_id = party_response.json()["id"]

    session = SessionState.model_validate(
        {
            "id": "closeout-session",
            "party_id": party_id,
            "adventure_id": "random",
            "adventure_type": "random",
            "mode": "complete",
            "party": [],
            "map_state": {"width": 1, "height": 1, "tiles": [], "current_tile_id": "t0"},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )
    campaign = record_adventure_complete(main.store, session)
    assert any(entry.event_type == "adventure_completed" for entry in campaign.campaign_chronicle)
    open_tasks = [task for task in campaign.guidance_tasks if task.status == "open"]
    assert any(task.title.startswith("Review adventure") for task in open_tasks)

    task = open_tasks[0]
    update = client.post("/api/campaign/guidance-task", json={"task_id": task.id, "status": "dismissed"})
    assert update.status_code == 200
    payload = update.json()["campaign"]
    assert any(item["id"] == task.id and item["status"] == "dismissed" for item in payload["guidance_tasks"])
    assert any(item["event_type"] == "adventure_completed" for item in payload["campaign_chronicle"])


def test_campaign_command_center_guidance_export_and_start_gate(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Gate Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])
    party_response = client.post("/api/parties", json={"name": "Gate Party", "character_ids": character_ids})
    assert party_response.status_code == 200
    party_id = party_response.json()["id"]

    session = SessionState.model_validate(
        {
            "id": "gate-closeout-session",
            "party_id": party_id,
            "adventure_id": "random",
            "adventure_type": "random",
            "mode": "complete",
            "party": [],
            "map_state": {"width": 1, "height": 1, "tiles": [], "current_tile_id": "t0"},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )
    campaign = record_adventure_complete(main.store, session)
    add_guidance_task(
        campaign,
        title="Required gate review",
        body="Required closeout review for start-gate override coverage.",
        category="closeout",
        priority="required",
        reference="App test guidance.",
        rules_reference_id="go_adventure_closeout_gates",
    )
    save_campaign(main.store, campaign)

    command = client.get("/api/campaign/command-center")
    assert command.status_code == 200
    payload = command.json()
    assert payload["campaign_name"] == "Norindaal"
    assert any(item["name"] == "Gate Party" for item in payload["parties"])
    assert payload["open_guidance"]

    guidance = client.get("/api/campaign/guidance-tasks", params={"status": "open", "priority": "required"})
    assert guidance.status_code == 200
    assert guidance.json()["count"] >= 1

    markdown = client.get("/api/campaign/chronicle/export", params={"format": "markdown"})
    assert markdown.status_code == 200
    assert "Adventure" in markdown.text

    gate = client.get("/api/campaign/closeout-gate", params={"party_id": party_id})
    assert gate.status_code == 200
    assert gate.json()["can_start"] is True
    assert gate.json()["requires_override"] is True
    assert any(issue["severity"] == "override" for issue in gate.json()["issues"])

    blocked = client.post("/api/sessions", json={"party_id": party_id, "adventure_id": "random"})
    assert blocked.status_code == 409
    assert "explicit override" in blocked.json()["detail"]

    started = client.post(
        "/api/sessions",
        json={"party_id": party_id, "adventure_id": "random", "allow_start_anyway": True},
    )
    assert started.status_code == 200


def test_campaign_bulk_assign_orphans(client: TestClient) -> None:
    response = client.post("/api/characters", json={"name": "Orphan Hero", "class_id": "warrior"})
    assert response.status_code == 200
    character_id = response.json()["id"]
    character = main.store.get("characters", character_id, main.Character.model_validate)
    assert character is not None
    character.campaign_id = None
    character.guild_id = None
    character.troupe_id = None
    main.store.save("characters", character)

    cleanup = client.post("/api/campaign/world", json={"action": "bulk_assign_campaign", "campaign_id": "norindaal"})
    assert cleanup.status_code == 200
    assert cleanup.json()["messages"]
    updated = next(item for item in client.get("/api/characters").json() if item["id"] == character_id)
    assert updated["campaign_id"] == "norindaal"
    assert updated["guild_id"] == "adventurers-guild"
    assert updated["troupe_id"] == "troupe1"


def test_heroic_spell_catalog_matches_fd_table() -> None:
    names = heroic_spell_names()
    assert len(names) == 6
    assert names == [
        "Boatman's Luck",
        "Eldritch Fist",
        "Mass Blessing",
        "Fire of Truth",
        "Teleport Enemy",
        "Mass Invisibility",
    ]
    assert is_fd_heroic_spell("Fire of Truth")
    assert not is_fd_heroic_spell("Fireball")


def test_abyss_phase_b_room_content_table_indexed() -> None:
    rows = abyss_table_rows("abyss_room_content_table")
    assert len(rows) == 11
    assert abyss_table_roll_keys("abyss_room_content_table") == [
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
    ]
    assert abyss_table_roll_keys("abyss_boss_table") == ["1", "2", "3", "4", "5", "6"]


def test_campaign_api_and_adventure_completion(client: TestClient) -> None:
    campaign = client.get("/api/campaign").json()
    assert campaign["id"] == "default"
    assert campaign["days_passed"] >= 0

    updated = client.put("/api/campaign", json={"tag_banking_enabled": True}).json()
    assert updated["tag_banking_enabled"] is True

    from app.engine.courtship_apothecary_brew import tag_settlement_apothecary_available

    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [],
            "map_state": {"width": 1, "height": 1, "tiles": [], "current_tile_id": "t0"},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "tag_banking_enabled": True,
        }
    )
    assert tag_settlement_apothecary_available(session) is True

    demesne = profile_by_id("courtship_demesne")
    assert demesne is not None
    assert resolve_profile_for_adventure("courtship-demesne").id == "courtship_demesne"
