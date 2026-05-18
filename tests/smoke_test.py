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
        tile_11["cell_shapes"] = ["EGJ"]
        tile_11["exits"] = [
            {
                "id": "11-south-middle",
                "label": "South middle",
                "direction": "south",
                "kind": "passage",
                "x": 1,
                "y": 0,
                "span": 2,
            },
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

        wounded = main.store.get("characters", character_ids[0], main.Character.model_validate)
        wounded.current_life = 1
        main.store.save("characters", wounded)
        heal_response = client.post(f"/api/characters/{character_ids[0]}/heal")
        assert heal_response.status_code == 200
        assert heal_response.json()["current_life"] == heal_response.json()["max_life"]

        party_response = client.post(
            "/api/parties",
            json={"name": "Smoke Party", "character_ids": character_ids},
        )
        assert party_response.status_code == 200
        party_id = party_response.json()["id"]
        for character_id in character_ids:
            character = main.store.get("characters", character_id, main.Character.model_validate)
            character.current_life = 1
            main.store.save("characters", character)
        heal_party_response = client.post(f"/api/parties/{party_id}/heal")
        assert heal_party_response.status_code == 200
        assert all(character["current_life"] == character["max_life"] for character in heal_party_response.json())
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
        delete_completed_response = client.delete(f"/api/sessions/{exit_session['id']}")
        assert delete_completed_response.status_code == 200
        assert delete_completed_response.json()["deleted"] is True
        assert client.get(f"/api/sessions/{exit_session['id']}").status_code == 404

        session_response = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        )
        assert session_response.status_code == 200
        session = session_response.json()
        assert session["saved_at"] is None
        save_response = client.post(f"/api/sessions/{session['id']}/save")
        assert save_response.status_code == 200
        saved_session = save_response.json()
        assert saved_session["saved_at"]
        listed_sessions = client.get("/api/sessions")
        assert listed_sessions.status_code == 200
        assert any(item["id"] == session["id"] and item["saved_at"] for item in listed_sessions.json())
        get_session = client.get(f"/api/sessions/{session['id']}")
        assert get_session.status_code == 200
        assert get_session.json()["id"] == session["id"]
        assert session["mode"] == "exploration"
        assert len(session["party"]) == 4
        entrance = session["map_state"]["tiles"][0]
        assert entrance["tile_key"] == "01"
        assert any(exit_state["dungeon_exit"] for exit_state in entrance["exits"])
        explore_exit = next(exit_state for exit_state in entrance["exits"] if not exit_state["dungeon_exit"])

        monkeypatch.setattr(random_dungeon, "roll_tile_key", lambda: "11")

        advance_response = client.post(
            f"/api/sessions/{session['id']}/advance",
            json={"action": "explore", "exit_id": explore_exit["id"]},
        )
        assert advance_response.status_code == 200
        advanced = advance_response.json()
        assert any("Room content roll: 2d6" in entry for entry in advanced["log"])
        assert len(advanced["map_state"]["tiles"]) == 2
        current = next(
            tile for tile in advanced["map_state"]["tiles"] if tile["id"] == advanced["map_state"]["current_tile_id"]
        )
        assert current["tile_key"] == "11"
        assert current["footprint_width"] == 3
        assert current["footprint_height"] == 1
        assert current["walkable"] == ["111"]
        assert current["cell_shapes"] == ["EGJ"]
        reciprocal = next(exit_state for exit_state in current["exits"] if exit_state["destination_tile_id"] == entrance["id"])
        assert reciprocal["label"] == "South middle"
        assert reciprocal["span"] == 2

        assert main.random_engine._rotate_rows(
            ["AB", "CD"],
            2,
            2,
            90,
            main.random_engine._rotate_cell_shape,
        ) == ["DC", "BA"]
        assert main.random_engine._rotate_rows(
            ["EG", "JL"],
            2,
            2,
            90,
            main.random_engine._rotate_cell_shape,
        ) == ["LH", "ME"]
        assert main.random_engine._rotate_rows(
            ["NO", "RU"],
            2,
            2,
            90,
            main.random_engine._rotate_cell_shape,
        ) == ["NT", "QU"]

        from app.schemas import ExitState, MapState, SessionState, TileDefinition, TileState

        timestamp = main.now_utc()
        origin = TileState(
            id="origin",
            x=0,
            y=0,
            tile_key="03",
            tile_type="room",
            footprint_width=3,
            footprint_height=1,
            walkable=["111"],
            cell_shapes=["FFF"],
            title="Origin",
            description="Origin",
            exits=[
                ExitState(id="n1", direction="north", kind="door", x=0, y=0),
                ExitState(id="n2", direction="north", kind="door", x=1, y=0),
                ExitState(id="n3", direction="north", kind="door", x=2, y=0),
            ],
        )
        placement_session = SessionState(
            id="placement",
            party_id="party",
            adventure_id="random",
            adventure_type="random",
            party=[],
            map_state=MapState(tiles=[origin], current_tile_id=origin.id),
            created_at=timestamp,
            updated_at=timestamp,
        )
        assert not main.random_engine._placement_blocked(placement_session, 0, -1, 1, 1, None, 0, origin, origin.exits[0])
        assert main.random_engine._placement_blocked(placement_session, 0, -1, 2, 1, None, 0, origin, origin.exits[0])
        truncation_def = TileDefinition(
            key="11",
            name="Truncation Test",
            tile_type="room",
            footprint_width=2,
            footprint_height=1,
            walkable=["11"],
            cell_shapes=["FF"],
            exits=[
                {"id": "match-south", "direction": "south", "kind": "door", "x": 0, "y": 0},
                {"id": "covered-north", "direction": "north", "kind": "door", "x": 1, "y": 0},
            ],
        )
        rotated_exits = main.random_engine._rotated_exits(truncation_def, 0)
        matching_exit = next(exit_state for exit_state in rotated_exits if exit_state.id == "match-south")
        truncation = main.random_engine._truncated_placement(
            placement_session,
            0,
            -1,
            2,
            1,
            truncation_def,
            0,
            origin,
            origin.exits[0],
            rotated_exits,
            matching_exit,
        )
        assert truncation is not None
        assert truncation.truncated is True
        assert truncation.walkable == ["10"]
        assert next(exit_state for exit_state in truncation.exits if exit_state.id == "covered-north").status == "blocked"

        guarded_session = main.store.get("sessions", session["id"], main.SessionState.model_validate)
        guarded_tile = guarded_session.map_state.tiles[0]
        guarded_session.mode = "exploration"
        guarded_session.map_state.current_tile_id = guarded_tile.id
        guarded_tile.footprint_width = max(2, guarded_tile.footprint_width)
        guarded_tile.footprint_height = max(1, guarded_tile.footprint_height)
        guarded_exit = guarded_tile.exits[0]
        guarded_exit.kind = "passage"
        guarded_exit.direction = "east"
        guarded_exit.x = 0
        guarded_exit.y = 0
        guarded_exit.status = "unexplored"
        guarded_exit.destination_tile_id = None
        guarded_exit.dungeon_exit = False
        main.store.save("sessions", guarded_session)
        guarded_response = client.post(
            f"/api/sessions/{session['id']}/advance",
            json={"action": "explore", "exit_id": guarded_exit.id},
        )
        assert guarded_response.status_code == 200
        guarded = guarded_response.json()
        assert len(guarded["map_state"]["tiles"]) == 2
        assert guarded["map_state"]["current_tile_id"] == guarded_session.map_state.current_tile_id
        assert any("same map element" in entry for entry in guarded["log"])
