from __future__ import annotations

from fastapi.testclient import TestClient

from app.engine.states import state_definition_for_status, state_definitions_for_statuses
from app.engine.terrain_registry import terrain_definitions_for_context


def test_state_resolver_matches_legacy_status_shapes() -> None:
    assert state_definition_for_status("Dark Plague")["id"] == "dark-plague"
    assert state_definition_for_status("Cursed (-1 Def)")["id"] == "cursed"
    assert state_definition_for_status("Poisoned L5")["id"] == "poisoned-lingering"
    assert state_definition_for_status("Longsword (poisoned)")["id"] == "envenomed-weapon"


def test_state_resolver_deduplicates_multiple_visible_labels() -> None:
    matches = state_definitions_for_statuses(["Poisoned", "Poisoned L5", "Dark Plague"])
    assert [match["id"] for match in matches] == ["poisoned-lingering", "dark-plague"]


def test_terrain_resolver_matches_environment_terrain_and_catalog() -> None:
    dungeon = terrain_definitions_for_context(environment="dungeon", terrain="indoor")
    assert {entry["id"] for entry in dungeon} >= {"dungeon", "indoor"}

    fd_river = terrain_definitions_for_context(tile_catalog="forsaken_depths_rivers")
    assert [entry["id"] for entry in fd_river] == ["fd-river-bank"]

    assert terrain_definitions_for_context(environment="", terrain=None, tile_catalog=None) == []


def test_state_resolver_api_matches_repeated_and_comma_labels(client: TestClient) -> None:
    repeated = client.get("/api/registry/resolve/states", params=[("label", "Cursed (-1 Def)"), ("label", "Poisoned L5")])
    assert repeated.status_code == 200
    repeated_payload = repeated.json()
    assert repeated_payload["read_only"] is True
    assert [match["state"]["id"] for match in repeated_payload["matches"]] == ["cursed", "poisoned-lingering"]

    comma = client.get("/api/registry/resolve/states", params={"labels": "Dark Plague, Longsword (poisoned)"})
    assert comma.status_code == 200
    assert [match["state"]["id"] for match in comma.json()["matches"]] == ["dark-plague", "envenomed-weapon"]


def test_terrain_resolver_api_matches_context(client: TestClient) -> None:
    dungeon = client.get("/api/registry/resolve/terrain", params={"environment": "dungeon", "terrain": "indoor"})
    assert dungeon.status_code == 200
    payload = dungeon.json()
    assert payload["read_only"] is True
    assert {entry["id"] for entry in payload["matches"]} >= {"dungeon", "indoor"}

    river = client.get("/api/registry/resolve/terrain", params={"tile_catalog": "forsaken_depths_rivers"})
    assert river.status_code == 200
    assert [entry["id"] for entry in river.json()["matches"]] == ["fd-river-bank"]
