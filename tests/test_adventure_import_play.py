from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engine.adventure_import import import_adventure_manifest, list_installed_adventure_ids
from app.engine.adventure_session import create_session_from_manifest
from app.main import app
from app.rules.repository import RulesRepository
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import PartyMemberState

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules"
EXAMPLE = ROOT / "data" / "adventures" / "examples" / "crypt-of-whispers" / "adventure.json"


@pytest.fixture
def repo() -> RulesRepository:
    return RulesRepository(RULES, RULES / "_override")


@pytest.fixture
def engine(repo: RulesRepository) -> RandomDungeonEngine:
    return RandomDungeonEngine(repo, ROOT / "assets")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _party_member() -> PartyMemberState:
    return PartyMemberState.model_validate({
        "character_id": "hero-1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 2,
        "max_life": 8,
        "current_life": 8,
        "gold": 50,
        "xp": 0,
        "inventory": ["Hand weapon", "Light armor"],
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
    })


def test_import_and_list_installed(repo: RulesRepository, tmp_path: Path) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    manifest["id"] = "test-crypt-import"
    path, result = import_adventure_manifest(tmp_path, manifest, rules_repo=repo, overwrite=True)
    assert result.valid, result.errors
    assert path is not None
    assert "test-crypt-import" in list_installed_adventure_ids(tmp_path)


def test_create_session_from_manifest(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-1",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    assert session.adventure_type == "imported"
    assert len(session.map_state.tiles) == 5
    assert session.active_quest is not None
    assert session.imported_exit_tile_id is not None
    assert session.map_state.current_tile_id in {tile.id for tile in session.map_state.tiles}


def test_list_adventures_includes_crypt(client: TestClient) -> None:
    adventures = client.get("/api/adventures").json()
    crypt = next((item for item in adventures if item["id"] == "crypt-of-whispers"), None)
    assert crypt is not None
    assert crypt["playable"] is True


def test_validate_and_import_api(client: TestClient) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    manifest["id"] = "api-import-test"
    validation = client.post("/api/adventures/validate", json={"manifest": manifest}).json()
    assert validation["valid"] is True
    imported = client.post("/api/adventures/import", json={"manifest": manifest, "overwrite": True}).json()
    assert imported["adventure_id"] == "api-import-test"
    adventures = client.get("/api/adventures").json()
    assert any(item["id"] == "api-import-test" and item["playable"] for item in adventures)
