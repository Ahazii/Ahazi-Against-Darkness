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

        advance_response = client.post(
            f"/api/sessions/{session['id']}/advance",
            json={"action": "explore"},
        )
        assert advance_response.status_code == 200
        assert len(advance_response.json()["map_state"]["tiles"]) >= 1
