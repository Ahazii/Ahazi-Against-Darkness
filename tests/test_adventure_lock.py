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
