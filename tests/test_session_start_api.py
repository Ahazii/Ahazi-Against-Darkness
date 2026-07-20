from __future__ import annotations

from fastapi.testclient import TestClient


def test_character_gender_persists_and_syncs_to_session_member(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        payload = {"name": f"Gender Hero {index}", "class_id": class_id}
        if index == 1:
            payload["gender"] = "female"
        response = client.post("/api/characters", json=payload)
        assert response.status_code == 200
        if index == 1:
            assert response.json()["gender"] == "female"
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "Gender Party", "character_ids": character_ids})
    assert party_response.status_code == 200
    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "random",
            "xp_system": "classical",
            "map_bounds_mode": "unlimited",
            "unlimited_map_element_cap": 60,
            "start_camped_outside": False,
        },
    )
    assert session_response.status_code == 200
    first_member = session_response.json()["party"][0]
    assert first_member["gender"] == "female"

    update = client.post(f"/api/characters/{character_ids[0]}/gender", json={"gender": "male"})
    assert update.status_code == 200
    assert update.json()["gender"] == "male"
    refreshed = client.get(f"/api/sessions/{session_response.json()['id']}")
    assert refreshed.status_code == 200
    assert refreshed.json()["party"][0]["gender"] == "male"


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
    assert payload["active_supplement_ids"] == ["expanded-edition-core", "imported-adventures"]
    assert payload["supplement_registry_version"] == 1
    assert payload["state_registry_version"] == 2
    assert payload["terrain_registry_version"] == 1
    assert (
        "Supplements locked for this session: "
        "Four Against Darkness Expanded Edition, Imported Adventure Packages."
    ) in payload["log"]


def test_create_session_accepts_per_session_supplement_snapshot(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Supplement Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "Supplement Party", "character_ids": character_ids})
    assert party_response.status_code == 200

    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "random",
            "ruleset_profile_id": "ee_random",
            "active_supplement_ids": ["courtship", "tag"],
        },
    )

    assert session_response.status_code == 200
    payload = session_response.json()
    assert payload["active_supplement_ids"] == ["expanded-edition-core", "courtship", "tag"]
    assert payload["supplement_registry_version"] == 1
    assert {
        (source["supplement_id"], source["kind"], source["path"])
        for source in payload["declared_content_sources"]
    } >= {
        ("expanded-edition-core", "tables", "data/rules/dungeon_tables.json"),
        ("courtship", "items", "data/rules/courtship_blossoms_tables.json"),
        ("tag", "foes", "data/rules/tag_monsters.json"),
    }
    assert (
        "Supplements locked for this session: "
        "Four Against Darkness Expanded Edition, The Courtship of Flower Demons, Tales from the Adventurers' Guild."
    ) in payload["log"]


def test_create_session_infers_forsaken_profile_from_supplement_snapshot(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"FD Supplement Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "FD Supplement Party", "character_ids": character_ids})
    assert party_response.status_code == 200

    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "random",
            "active_supplement_ids": ["forsaken-depths"],
        },
    )

    assert session_response.status_code == 200
    payload = session_response.json()
    assert payload["ruleset_profile_id"] == "forsaken_depths_no_courtship"
    assert payload["ruleset"] == "forsaken_depths"
    assert payload["courtship_enabled"] is False
    assert payload["active_supplement_ids"] == ["expanded-edition-core", "forsaken-depths"]
    assert (
        "Supplements locked for this session: "
        "Four Against Darkness Expanded Edition, Four Against the Forsaken Depths."
    ) in payload["log"]


def test_create_session_infers_abyss_profile_from_supplement_snapshot(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Abyss Supplement Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "Abyss Supplement Party", "character_ids": character_ids})
    assert party_response.status_code == 200

    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "random",
            "active_supplement_ids": ["four-against-the-abyss"],
        },
    )

    assert session_response.status_code == 200
    payload = session_response.json()
    assert payload["ruleset_profile_id"] == "abyss"
    assert payload["active_supplement_ids"] == ["expanded-edition-core", "four-against-the-abyss"]
    assert (
        "Supplements locked for this session: "
        "Four Against Darkness Expanded Edition, Four Against the Abyss."
    ) in payload["log"]


def test_create_session_rejects_unknown_per_session_supplement(client: TestClient) -> None:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Bad Supplement Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])

    party_response = client.post("/api/parties", json={"name": "Bad Supplement Party", "character_ids": character_ids})
    assert party_response.status_code == 200

    session_response = client.post(
        "/api/sessions",
        json={
            "party_id": party_response.json()["id"],
            "adventure_id": "random",
            "active_supplement_ids": ["made-up-book"],
        },
    )

    assert session_response.status_code == 400
    assert "Unknown supplement id: made-up-book" in session_response.json()["detail"]
