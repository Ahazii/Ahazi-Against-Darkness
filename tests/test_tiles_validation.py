from __future__ import annotations

from pathlib import Path

from app.engine.tile_validation import validate_tile_catalog, validate_tile_definition
from app.rules.repository import RulesRepository
from fastapi.testclient import TestClient


def packaged() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "rules"


def test_catalog_has_all_starting_and_generated_keys() -> None:
    repo = RulesRepository(packaged(), packaged() / "_override")
    issues = validate_tile_catalog(repo.tiles())
    assert issues == {}, issues


def test_each_tile_has_consistent_grid() -> None:
    repo = RulesRepository(packaged(), packaged() / "_override")
    for key, tile in sorted(repo.tiles().items()):
        tile_issues = validate_tile_definition(tile)
        assert tile_issues == [], f"{key}: {tile_issues}"


def test_tiles_validation_api() -> None:
    from app.main import app

    client = TestClient(app)
    payload = client.get("/api/rules/tiles/validation").json()
    assert payload["valid"] is True
    assert payload["issues"] == {}
