from __future__ import annotations

from fastapi.testclient import TestClient

from app import main
from app.db import Store, init_db
from app.main import app


def _isolated_client(monkeypatch, tmp_path) -> TestClient:
    db_path = tmp_path / "swashbuckler-traits.sqlite3"
    init_db(db_path)
    monkeypatch.setattr(main, "store", Store(db_path))
    return TestClient(app)


def test_create_swashbuckler_can_pick_pdf_trait(monkeypatch, tmp_path) -> None:
    client = _isolated_client(monkeypatch, tmp_path)
    response = client.post(
        "/api/characters",
        json={"name": "Trait Pick Swash", "class_id": "swashbuckler", "trait_id": "riposte"},
    )

    assert response.status_code == 200
    character = response.json()
    assert character["class_traits"] == ["Riposte"]
    assert "Plumed/tricorn hat" in character["inventory"]
    assert "Half-cape" in character["inventory"]
    assert "Bandage" not in character["inventory"]

    client.delete(f"/api/characters/{character['id']}")


def test_create_swashbuckler_rolls_trait_when_not_picked(monkeypatch, tmp_path) -> None:
    client = _isolated_client(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "roll_formula", lambda formula: 6 if formula == "d6" else 1)
    response = client.post("/api/characters", json={"name": "Trait Roll Swash", "class_id": "swashbuckler"})

    assert response.status_code == 200
    character = response.json()
    assert character["class_traits"] == ["Blade Dance"]

    client.delete(f"/api/characters/{character['id']}")


def test_non_swashbuckler_cannot_receive_swashbuckler_trait(monkeypatch, tmp_path) -> None:
    client = _isolated_client(monkeypatch, tmp_path)
    response = client.post(
        "/api/characters",
        json={"name": "Wrong Trait", "class_id": "warrior", "trait_id": "taunt"},
    )

    assert response.status_code == 400
    assert "Only Swashbucklers" in response.json()["detail"]
