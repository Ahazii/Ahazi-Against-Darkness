from __future__ import annotations

import importlib
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient


def test_characters_lock_during_adventure_and_clear_on_complete(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        classes = client.get("/api/rules/classes").json()
        character_ids = []
        for index, class_id in enumerate([item["id"] for item in classes[:4]], start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Lock Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Lock Party", "character_ids": character_ids},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        session = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()
        session_id = session["id"]

        characters = client.get("/api/characters").json()
        for character_id in character_ids:
            character = next(item for item in characters if item["id"] == character_id)
            assert character["active_session_id"] == session_id

        duplicate = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        )
        assert duplicate.status_code == 409

        client.post(f"/api/sessions/{session_id}/save")
        saved = client.get("/api/sessions").json()
        assert any(item["id"] == session_id and item.get("saved_at") for item in saved)

        stored = main.store.get("sessions", session_id, main.SessionState.model_validate)
        assert stored is not None
        stored.mode = "complete"
        stored.summary = ["Done."]
        for member in stored.party:
            if member.current_life > 0:
                member.current_life = member.max_life
        main.store.save("sessions", stored)

        completed = client.post(
            f"/api/sessions/{session_id}/advance",
            json={"action": "search"},
        ).json()
        assert completed["mode"] == "complete"
        assert completed.get("saved_at") is None

        characters = client.get("/api/characters").json()
        for character_id in character_ids:
            character = next(item for item in characters if item["id"] == character_id)
            assert character["active_session_id"] is None

        saved_after = [item for item in client.get("/api/sessions").json() if item.get("saved_at")]
        assert not any(item["id"] == session_id for item in saved_after)

        retry = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        )
        assert retry.status_code == 200


def test_reconcile_clears_orphaned_character_locks(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        classes = client.get("/api/rules/classes").json()
        character_id = client.post(
            "/api/characters",
            json={"name": "Orphan Hero", "class_id": classes[0]["id"]},
        ).json()["id"]

        party_id = client.post(
            "/api/parties",
            json={"name": "Orphan Party", "character_ids": [character_id, character_id, character_id, character_id]},
        )
        assert party_id.status_code == 400

        character_ids = []
        for index, class_id in enumerate([item["id"] for item in classes[:4]], start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Orphan Mate {index}", "class_id": class_id},
            )
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Orphan Party", "character_ids": character_ids},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        session_id = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()["id"]

        stored = main.store.get("characters", character_ids[0], main.Character.model_validate)
        assert stored is not None
        assert stored.active_session_id == session_id

        main.store.delete("sessions", session_id)
        for character_id in character_ids:
            character = main.store.get("characters", character_id, main.Character.model_validate)
            assert character is not None
            character.active_session_id = session_id
            main.store.save("characters", character)

        characters = client.get("/api/characters").json()
        for character_id in character_ids:
            character = next(item for item in characters if item["id"] == character_id)
            assert character["active_session_id"] is None

        retry = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        )
        assert retry.status_code == 200


def test_regroup_party_while_camped(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        classes = client.get("/api/rules/classes").json()
        character_ids = []
        for index, class_id in enumerate([item["id"] for item in classes[:5]], start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Regroup Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Regroup Party", "character_ids": character_ids[:4]},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        session = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()
        session_id = session["id"]

        stored = main.store.get("sessions", session_id, main.SessionState.model_validate)
        assert stored is not None
        stored.camped_outside = True
        stored.saved_at = "2026-05-19T12:00:00Z"
        main.store.save("sessions", stored)

        replacement = character_ids[4]
        regroup = client.put(
            f"/api/sessions/{session_id}/party",
            json={"character_ids": character_ids[:3] + [replacement]},
        )
        assert regroup.status_code == 200
        updated = regroup.json()
        assert updated["party_editable"] is True
        member_ids = {member["character_id"] for member in updated["party"]}
        assert replacement in member_ids
        assert character_ids[3] not in member_ids

        freed = main.store.get("characters", character_ids[3], main.Character.model_validate)
        assert freed is not None
        assert freed.active_session_id is None

        replacement_char = main.store.get("characters", replacement, main.Character.model_validate)
        assert replacement_char is not None
        assert replacement_char.active_session_id == session_id


def test_saved_game_without_camp_cannot_swap_party(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        classes = client.get("/api/rules/classes").json()
        character_ids = []
        for index, class_id in enumerate([item["id"] for item in classes[:5]], start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Saved Swap Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Saved Swap Party", "character_ids": character_ids[:4]},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        session = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()
        session_id = session["id"]

        stored = main.store.get("sessions", session_id, main.SessionState.model_validate)
        assert stored is not None
        stored.saved_at = "2026-05-19T12:00:00Z"
        stored.camped_outside = False
        main.store.save("sessions", stored)

        loaded = client.get(f"/api/sessions/{session_id}")
        assert loaded.status_code == 200
        assert loaded.json()["party_editable"] is False

        replacement = character_ids[4]
        regroup = client.put(
            f"/api/sessions/{session_id}/party",
            json={"character_ids": character_ids[:3] + [replacement]},
        )
        assert regroup.status_code == 400
        assert "camped outside" in regroup.json()["detail"]


def test_roster_character_can_spend_banked_xp(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        from app.engine import random_dungeon
        from app.engine.dice import AdvancementRollResult

        monkeypatch.setattr(
            random_dungeon,
            "perform_advancement_roll",
            lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(
                natural=6, total=6, sides=6, modifier=bonus, purpose=purpose
            ),
        )

        class_id = next(item["id"] for item in client.get("/api/rules/classes").json() if item["id"] == "warrior")
        created = client.post("/api/characters", json={"name": "Banked XP Hero", "class_id": class_id}).json()
        character = main.store.get("characters", created["id"], main.Character.model_validate)
        assert character is not None
        character.xp = 1
        main.store.save("characters", character)

        spent = client.post(
            f"/api/characters/{created['id']}/spend-xp",
            json={"advancement_fork": "level_up"},
        )
        assert spent.status_code == 200
        body = spent.json()
        assert body["character"]["xp"] == 0
        assert body["character"]["level"] == 2
        assert any("Banked level-up roll" in line for line in body["log"])


def test_regroup_party_preserves_fallen_body_record(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        classes = client.get("/api/rules/classes").json()
        character_ids = []
        for index, class_id in enumerate([item["id"] for item in classes[:5]], start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Body Regroup Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Body Regroup Party", "character_ids": character_ids[:4]},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        session = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()
        session_id = session["id"]
        fallen_id = character_ids[0]
        replacement_id = character_ids[4]

        stored = main.store.get("sessions", session_id, main.SessionState.model_validate)
        assert stored is not None
        current = next(tile for tile in stored.map_state.tiles if tile.id == stored.map_state.current_tile_id)
        current.fallen_character_ids.append(fallen_id)
        stored.party[0].current_life = 0
        stored.party[0].statuses.append("Fallen")
        stored.camped_outside = True
        main.store.save("sessions", stored)

        regroup = client.put(
            f"/api/sessions/{session_id}/party",
            json={"character_ids": character_ids[1:4] + [replacement_id]},
        )
        assert regroup.status_code == 200
        updated = regroup.json()
        active_party_ids = main.store.get("parties", party_id, main.Party.model_validate).character_ids
        assert active_party_ids == character_ids[1:4] + [replacement_id]
        assert fallen_id in {member["character_id"] for member in updated["party"]}
        fallen = next(member for member in updated["party"] if member["character_id"] == fallen_id)
        assert fallen["current_life"] == 0
        current = next(tile for tile in updated["map_state"]["tiles"] if tile["id"] == updated["map_state"]["current_tile_id"])
        assert fallen_id in current["fallen_character_ids"]

        fallen_character = main.store.get("characters", fallen_id, main.Character.model_validate)
        assert fallen_character is not None
        assert fallen_character.active_session_id == session_id


def test_missing_fallen_member_restored_for_body_recovery(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        classes = client.get("/api/rules/classes").json()
        character_ids = []
        for index, class_id in enumerate([item["id"] for item in classes[:4]], start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Recovery Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Recovery Party", "character_ids": character_ids},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        session = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()
        session_id = session["id"]
        fallen_id = character_ids[0]
        carrier_id = character_ids[1]

        stored = main.store.get("sessions", session_id, main.SessionState.model_validate)
        assert stored is not None
        current = next(tile for tile in stored.map_state.tiles if tile.id == stored.map_state.current_tile_id)
        current.fallen_character_ids.append(fallen_id)
        stored.party = [member for member in stored.party if member.character_id != fallen_id]
        main.store.save("sessions", stored)

        repaired = client.get(f"/api/sessions/{session_id}")
        assert repaired.status_code == 200
        repaired_body = repaired.json()
        restored = next(member for member in repaired_body["party"] if member["character_id"] == fallen_id)
        assert restored["current_life"] == 0

        carried = client.post(
            f"/api/sessions/{session_id}/advance",
            json={
                "action": "carry_body",
                "character_id": carrier_id,
                "target_character_id": fallen_id,
            },
        )
        assert carried.status_code == 200
        carried_body = carried.json()
        assert carried_body["body_carrier_id"] == carrier_id
        assert carried_body["carried_body_id"] == fallen_id
