"""Lightweight session list API for Home active/saved games."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _create_party(client: TestClient) -> str:
    character_ids: list[str] = []
    for index, class_id in enumerate(["warrior", "cleric", "rogue", "wizard"], start=1):
        response = client.post("/api/characters", json={"name": f"Summary Hero {index}", "class_id": class_id})
        assert response.status_code == 200
        character_ids.append(response.json()["id"])
    party = client.post("/api/parties", json={"name": "Summary Party", "character_ids": character_ids}).json()
    return party["id"]


def test_session_summaries_are_smaller_than_full_session_list(client: TestClient) -> None:
    party_id = _create_party(client)
    session = client.post(
        "/api/sessions",
        json={
            "party_id": party_id,
            "adventure_id": "random",
            "start_camped_outside": True,
        },
    ).json()

    summaries = client.get("/api/sessions/summaries").json()
    full = client.get("/api/sessions").json()

    assert len(summaries) == len(full) >= 1
    row = next(item for item in summaries if item["id"] == session["id"])
    full_row = next(item for item in full if item["id"] == session["id"])

    assert row["party_id"] == session["party_id"]
    assert row["adventure_id"] == "random"
    assert row["mode"] == session["mode"]
    assert row["tile_count"] == len(session["map_state"]["tiles"])
    assert row["active_supplement_ids"] == session["active_supplement_ids"]
    assert row["supplement_registry_version"] == 1
    assert row["state_registry_version"] == 1
    assert row["terrain_registry_version"] == 1
    assert "party" not in row
    assert "log" not in row
    assert "map_state" not in row
    assert len(str(row)) < len(str(full_row)) // 4
