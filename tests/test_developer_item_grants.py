from __future__ import annotations

from fastapi.testclient import TestClient

from app import main
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def _create_character(client: TestClient, name: str, class_id: str) -> dict:
    response = client.post("/api/characters", json={"name": name, "class_id": class_id})
    assert response.status_code == 200
    return response.json()


def _item(catalog: dict, name: str) -> dict:
    return next(item for item in catalog["items"] if item["name"] == name)


def test_developer_item_catalog_requires_toggle_and_filters_supplements(client: TestClient) -> None:
    _create_character(client, "Merlin", "wizard")

    hidden = client.get("/api/developer/item-grants")
    assert hidden.status_code == 403

    enabled = client.put(
        "/api/preferences",
        json={"show_developer_item_grants": True, "enabled_supplement_ids": ["tag", "four-against-the-abyss"]},
    )
    assert enabled.status_code == 200
    assert enabled.json()["show_developer_item_grants"] is True

    response = client.get("/api/developer/item-grants")
    assert response.status_code == 200
    payload = response.json()
    names = {item["name"] for item in payload["items"]}
    assert "Gremlin repellant" in names
    assert "Bag of Carrying" in names
    assert "Ring of Three Wishes" in names
    assert "Scroll of Disbelief" in names
    assert "Small gemstone (25gp)" in names
    assert "Lucky Boat" not in names
    assert "Resurrection ritual" not in names
    assert "Magic Weapon (+1 Attack)" not in names
    assert "Adventurer's Dead Body" not in names
    assert "Adventurer’s Dead Body" not in names


def test_developer_grant_enforces_class_restrictions_and_syncs_real_bag(client: TestClient) -> None:
    barbarian = _create_character(client, "Conan", "barbarian")
    wizard = _create_character(client, "Merlin", "wizard")
    client.put(
        "/api/preferences",
        json={"show_developer_item_grants": True, "enabled_supplement_ids": ["tag"]},
    )
    catalog = client.get("/api/developer/item-grants").json()
    bag = _item(catalog, "Bag of Carrying")
    repellant = _item(catalog, "Gremlin repellant")
    heavy_armor = _item(catalog, "Heavy armor")
    assert bag["eligibility"][barbarian["id"]]["allowed"] is False
    assert bag["eligibility"][wizard["id"]]["allowed"] is True
    assert heavy_armor["eligibility"][wizard["id"]]["allowed"] is False

    refused = client.post(
        "/api/developer/item-grants",
        json={"character_id": barbarian["id"], "item_id": bag["id"]},
    )
    assert refused.status_code == 400
    assert "magic items" in refused.json()["detail"]

    member = PartyMemberState(
        character_id=wizard["id"],
        name=wizard["name"],
        class_id=wizard["class_id"],
        class_name=wizard["class_name"],
        level=wizard["level"],
        xp=wizard["xp"],
        gold=wizard["gold"],
        current_life=wizard["current_life"],
        max_life=wizard["max_life"],
        attack_bonus=wizard["attack_bonus"],
        defense_bonus=wizard["defense_bonus"],
        save_bonus=wizard["save_bonus"],
        inventory=[*wizard["inventory"], "Session-only treasure"],
    )
    tile = TileState(id="entrance", x=0, y=0, tile_key="11", tile_type="room", title="Entrance", description="Entrance")
    session = SessionState(
        id="developer-grant-session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[member],
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        camped_outside=True,
        created_at="2026-07-21T00:00:00Z",
        updated_at="2026-07-21T00:00:00Z",
    )
    main.store.save("sessions", session)

    bag_grant = client.post(
        "/api/developer/item-grants",
        json={"character_id": wizard["id"], "item_id": bag["id"]},
    )
    assert bag_grant.status_code == 200
    assert bag_grant.json()["updated_session_ids"] == [session.id]
    assert bag_grant.json()["character"]["inventory"].count("Bag of Carrying") == 1
    assert "Session-only treasure" in bag_grant.json()["character"]["inventory"]
    assert len(bag_grant.json()["character"]["item_containers"]) == 1

    second_bag_grant = client.post(
        "/api/developer/item-grants",
        json={"character_id": wizard["id"], "item_id": bag["id"]},
    )
    assert second_bag_grant.status_code == 200
    assert len(second_bag_grant.json()["character"]["item_containers"]) == 2

    repellant_grant = client.post(
        "/api/developer/item-grants",
        json={"character_id": wizard["id"], "item_id": repellant["id"]},
    )
    assert repellant_grant.status_code == 200
    synced = main.store.get("sessions", session.id, SessionState.model_validate)
    assert synced is not None
    assert "Gremlin repellant" in synced.party[0].inventory
    assert synced.party[0].item_containers
    assert any("Developer override: granted Bag of Carrying" in line for line in synced.log)

    packed = client.post(
        f"/api/sessions/{session.id}/advance",
        json={
            "action": "put_item_in_container",
            "character_id": wizard["id"],
            "item_name": "Session-only treasure",
            "item_container_id": synced.party[0].item_containers[1].id,
        },
    )
    assert packed.status_code == 200
    packed_session = packed.json()
    assert "Session-only treasure" not in packed_session["party"][0]["inventory"]
    assert packed_session["party"][0]["item_containers"][0]["contents"] == []
    assert packed_session["party"][0]["item_containers"][1]["contents"] == ["Session-only treasure"]
    assert any("puts Session-only treasure in Bag of Carrying" in line for line in packed_session["log"])

    applied = client.post(
        f"/api/sessions/{session.id}/advance",
        json={
            "action": "apply_gremlin_repellant",
            "character_id": wizard["id"],
            "target_character_id": wizard["id"],
            "item_name": "Bag of Carrying",
            "item_container_id": synced.party[0].item_containers[0].id,
        },
    )
    assert applied.status_code == 200
    applied_session = applied.json()
    assert "Gremlin repellant" not in applied_session["party"][0]["inventory"]
    assert applied_session["gremlin_protected_items"][0]["item_container_id"] == synced.party[0].item_containers[0].id


def test_active_session_supplements_extend_grant_catalog_for_that_character(client: TestClient) -> None:
    wizard = _create_character(client, "Merlin", "wizard")
    client.put(
        "/api/preferences",
        json={"show_developer_item_grants": True, "enabled_supplement_ids": []},
    )
    member = PartyMemberState(
        character_id=wizard["id"],
        name=wizard["name"],
        class_id=wizard["class_id"],
        class_name=wizard["class_name"],
        level=wizard["level"],
        xp=wizard["xp"],
        gold=wizard["gold"],
        current_life=wizard["current_life"],
        max_life=wizard["max_life"],
        attack_bonus=wizard["attack_bonus"],
        defense_bonus=wizard["defense_bonus"],
        save_bonus=wizard["save_bonus"],
    )
    tile = TileState(id="entrance", x=0, y=0, tile_key="11", tile_type="room", title="Entrance", description="Entrance")
    main.store.save(
        "sessions",
        SessionState(
            id="tag-session",
            party_id="party",
            adventure_id="random",
            adventure_type="random",
            party=[member],
            active_supplement_ids=["expanded-edition-core", "tag"],
            map_state=MapState(tiles=[tile], current_tile_id=tile.id),
            created_at="2026-07-21T00:00:00Z",
            updated_at="2026-07-21T00:00:00Z",
        ),
    )

    catalog = client.get("/api/developer/item-grants").json()
    bag = _item(catalog, "Bag of Carrying")
    assert bag["eligibility"][wizard["id"]]["allowed"] is True
    granted = client.post(
        "/api/developer/item-grants",
        json={"character_id": wizard["id"], "item_id": bag["id"]},
    )
    assert granted.status_code == 200
    assert granted.json()["updated_session_ids"] == ["tag-session"]


def test_developer_grant_keeps_multiple_active_session_inventories_isolated(client: TestClient) -> None:
    wizard = _create_character(client, "Merlin", "wizard")
    client.put(
        "/api/preferences",
        json={"show_developer_item_grants": True, "enabled_supplement_ids": []},
    )
    catalog = client.get("/api/developer/item-grants").json()
    repellant = _item(catalog, "Gremlin repellant")
    for session_id, unique_item, updated_at in (
        ("older-session", "Older session treasure", "2026-07-20T00:00:00Z"),
        ("newer-session", "Newer session treasure", "2026-07-21T00:00:00Z"),
    ):
        member = PartyMemberState(
            character_id=wizard["id"],
            name=wizard["name"],
            class_id=wizard["class_id"],
            class_name=wizard["class_name"],
            level=wizard["level"],
            xp=wizard["xp"],
            gold=wizard["gold"],
            current_life=wizard["current_life"],
            max_life=wizard["max_life"],
            attack_bonus=wizard["attack_bonus"],
            defense_bonus=wizard["defense_bonus"],
            save_bonus=wizard["save_bonus"],
            inventory=[unique_item],
        )
        tile = TileState(id="entrance", x=0, y=0, tile_key="11", tile_type="room", title="Entrance", description="Entrance")
        main.store.save(
            "sessions",
            SessionState(
                id=session_id,
                party_id="party",
                adventure_id="random",
                adventure_type="random",
                party=[member],
                map_state=MapState(tiles=[tile], current_tile_id=tile.id),
                created_at=updated_at,
                updated_at=updated_at,
            ),
        )

    response = client.post(
        "/api/developer/item-grants",
        json={"character_id": wizard["id"], "item_id": repellant["id"]},
    )
    assert response.status_code == 200
    older = main.store.get("sessions", "older-session", SessionState.model_validate)
    newer = main.store.get("sessions", "newer-session", SessionState.model_validate)
    assert older is not None and newer is not None
    assert older.party[0].inventory == ["Older session treasure", "Gremlin repellant"]
    assert newer.party[0].inventory == ["Newer session treasure", "Gremlin repellant"]
    assert response.json()["character"]["inventory"] == newer.party[0].inventory


def test_developer_item_grant_rejects_disabled_supplement_item(client: TestClient) -> None:
    wizard = _create_character(client, "Merlin", "wizard")
    client.put(
        "/api/preferences",
        json={"show_developer_item_grants": True, "enabled_supplement_ids": ["tag"]},
    )
    rejected = client.post(
        "/api/developer/item-grants",
        json={"character_id": wizard["id"], "item_id": "forsaken-depths:fd_heroic_magic_item_table:lucky_boat:lucky-boat"},
    )
    assert rejected.status_code == 400
    assert "enabled default or active-session supplement catalog" in rejected.json()["detail"]
