from __future__ import annotations

from fastapi.testclient import TestClient

from app.engine.abyss_tables import abyss_table_roll_keys, abyss_table_rows
from app.engine.forsaken_depths_heroic_spells import heroic_spell_names, is_fd_heroic_spell
from app.engine.ruleset_profiles import (
    class_allowed_for_profile,
    profile_by_id,
    resolve_profile_for_adventure,
)
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


def test_campaign_api_lists_first_six_tag_services(client: TestClient) -> None:
    client.put("/api/campaign", json={"settlement_size": 0})
    response = client.get("/api/campaign/tag/services")

    assert response.status_code == 200
    services = response.json()["services"]
    assert [service["key"] for service in services] == [
        "bank_account",
        "bank_inheritance",
        "magic_locker",
        "platinum_exchange",
        "hidden_treasure_trove",
        "resurrection_blessing_tags",
    ]
    assert services[2]["status"] == "available"
    assert services[3]["status"] == "church_only"


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
