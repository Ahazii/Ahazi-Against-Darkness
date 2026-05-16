from __future__ import annotations

import importlib
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient


def test_random_session_smoke(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)
        classes = client.get("/api/rules/classes").json()
        tiles = client.get("/api/rules/tiles").json()
        class_ids = [item["id"] for item in classes[:4]]
        assert len(tiles) == 42
        assert tiles[0]["key"] == "01"
        tiles[0]["implementation_status"] = "test-edited"
        tile_11 = next(item for item in tiles if item["key"] == "11")
        tile_11["tile_type"] = "room"
        tile_11["footprint_width"] = 3
        tile_11["footprint_height"] = 1
        tile_11["walkable"] = ["111"]
        tile_11["cell_shapes"] = ["FAF"]
        tile_11["exits"] = [
            {"id": "11-south-middle", "label": "South middle", "direction": "south", "kind": "passage", "x": 1, "y": 0},
        ]
        save_tiles = client.put("/api/rules/tiles", json=tiles)
        assert save_tiles.status_code == 200
        assert client.get("/api/rules/tiles").json()[0]["implementation_status"] == "test-edited"
        bad_tiles = client.get("/api/rules/tiles").json()
        bad_11 = next(item for item in bad_tiles if item["key"] == "11")
        bad_11["exits"][0]["dungeon_exit"] = True
        assert client.put("/api/rules/tiles", json=bad_tiles).status_code == 400

        character_ids = []
        for index, class_id in enumerate(class_ids, start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_response = client.post(
            "/api/parties",
            json={"name": "Smoke Party", "character_ids": character_ids},
        )
        assert party_response.status_code == 200
        party_id = party_response.json()["id"]
        update_party_response = client.put(
            f"/api/parties/{party_id}",
            json={"name": "Updated Smoke Party", "character_ids": character_ids},
        )
        assert update_party_response.status_code == 200
        assert update_party_response.json()["name"] == "Updated Smoke Party"
        blocked_delete = client.delete(f"/api/characters/{character_ids[0]}")
        assert blocked_delete.status_code == 400
        throwaway_party_response = client.post(
            "/api/parties",
            json={"name": "Throwaway Party", "character_ids": character_ids},
        )
        assert throwaway_party_response.status_code == 200
        delete_party_response = client.delete(f"/api/parties/{throwaway_party_response.json()['id']}")
        assert delete_party_response.status_code == 200
        assert delete_party_response.json()["deleted"] is True

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        exit_session_response = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        )
        assert exit_session_response.status_code == 200
        exit_session = exit_session_response.json()
        start = exit_session["map_state"]["tiles"][0]
        dungeon_exit = next(exit_state for exit_state in start["exits"] if exit_state["dungeon_exit"])
        complete_response = client.post(
            f"/api/sessions/{exit_session['id']}/advance",
            json={"action": "explore", "exit_id": dungeon_exit["id"]},
        )
        assert complete_response.status_code == 200
        completed = complete_response.json()
        assert completed["mode"] == "complete"
        assert completed["summary"]

        session_response = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        )
        assert session_response.status_code == 200
        session = session_response.json()
        listed_sessions = client.get("/api/sessions")
        assert listed_sessions.status_code == 200
        assert any(item["id"] == session["id"] for item in listed_sessions.json())
        get_session = client.get(f"/api/sessions/{session['id']}")
        assert get_session.status_code == 200
        assert get_session.json()["id"] == session["id"]
        assert session["mode"] == "exploration"
        assert len(session["party"]) == 4
        entrance = session["map_state"]["tiles"][0]
        assert entrance["tile_key"] == "01"
        assert {exit_state["direction"] for exit_state in entrance["exits"]} == {"north", "east", "south", "west"}
        north_exit = next(exit_state for exit_state in entrance["exits"] if exit_state["direction"] == "north")

        monkeypatch.setattr(random_dungeon, "roll_tile_key", lambda: "11")

        advance_response = client.post(
            f"/api/sessions/{session['id']}/advance",
            json={"action": "explore", "exit_id": north_exit["id"]},
        )
        assert advance_response.status_code == 200
        advanced = advance_response.json()
        assert len(advanced["map_state"]["tiles"]) == 2
        current = next(
            tile for tile in advanced["map_state"]["tiles"] if tile["id"] == advanced["map_state"]["current_tile_id"]
        )
        assert current["x"] == -1
        assert current["y"] == -1
        assert current["rotation"] == 0
        assert current["footprint_width"] == 3
        assert current["footprint_height"] == 1
        assert current["walkable"] == ["111"]
        assert current["cell_shapes"] == ["FAF"]
        assert any(
            exit_state["direction"] == "south"
            and exit_state["label"] == "South middle"
            and exit_state["x"] == 1
            and exit_state["y"] == 0
            and exit_state["destination_tile_id"] == entrance["id"]
            for exit_state in current["exits"]
        )
