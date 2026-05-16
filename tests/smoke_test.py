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
        assert len(tiles) == 66
        assert tiles[0]["key"] == "01"
        tiles[0]["implementation_status"] = "test-edited"
        tiles[1]["tile_type"] = "room"
        tiles[1]["footprint_width"] = 3
        tiles[1]["footprint_height"] = 1
        tiles[1]["exits"] = [
            {"id": "02-south-middle", "direction": "south", "kind": "passage", "offset": 1},
        ]
        save_tiles = client.put("/api/rules/tiles", json=tiles)
        assert save_tiles.status_code == 200
        assert client.get("/api/rules/tiles").json()[0]["implementation_status"] == "test-edited"

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

        session_response = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        )
        assert session_response.status_code == 200
        session = session_response.json()
        assert session["mode"] == "exploration"
        assert len(session["party"]) == 4
        entrance = session["map_state"]["tiles"][0]
        assert {exit_state["direction"] for exit_state in entrance["exits"]} == {"north", "east", "west"}
        north_exit = next(exit_state for exit_state in entrance["exits"] if exit_state["direction"] == "north")

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_tile_key", lambda: "02")

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
        assert any(
            exit_state["direction"] == "south"
            and exit_state["offset"] == 1
            and exit_state["destination_tile_id"] == entrance["id"]
            for exit_state in current["exits"]
        )
