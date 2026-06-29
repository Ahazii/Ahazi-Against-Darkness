from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_session_accepts_frontend_json_scalar_payload(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "Payload Party", "character_ids": character_ids})
    assert party_response.status_code == 200

    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "random",
            "xp_system": "classical",
            "map_bounds_mode": "unlimited",
            "unlimited_map_element_cap": 60,
            "fiendish_foes_enabled": True,
            "start_camped_outside": False,
        },
    )

    assert session_response.status_code == 200
    payload = session_response.json()
    assert payload["unlimited_map_element_cap"] == 60
    assert payload["fiendish_foes_enabled"] is True


def test_create_imported_session_ignores_random_profile_payload(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Imported Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "Imported Party", "character_ids": character_ids})
    assert party_response.status_code == 200

    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "crypt-of-whispers",
            "ruleset_profile_id": "ee_random",
            "xp_system": "classical",
            "map_bounds_mode": "unlimited",
            "unlimited_map_element_cap": 60,
        },
    )

    assert session_response.status_code == 200
    payload = session_response.json()
    assert payload["adventure_type"] == "imported"
    assert payload["adventure_id"] == "crypt-of-whispers"
