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


def test_starting_tile_requires_exactly_one_dungeon_exit() -> None:
    issues = validate_tile_definition({
        "key": "01",
        "name": "Entrance",
        "tile_type": "room",
        "footprint_width": 2,
        "footprint_height": 1,
        "walkable": ["11"],
        "cell_shapes": ["FF"],
        "exits": [{"id": "north", "direction": "north", "kind": "door", "x": 0, "y": 0}],
    })

    assert "starting entrance tile must define exactly one dungeon exit, found 0." in issues


def test_generated_tile_rejects_dungeon_exit() -> None:
    issues = validate_tile_definition({
        "key": "11",
        "name": "Room",
        "tile_type": "room",
        "footprint_width": 1,
        "footprint_height": 1,
        "walkable": ["1"],
        "cell_shapes": ["F"],
        "exits": [{
            "id": "exit",
            "direction": "north",
            "kind": "door",
            "x": 0,
            "y": 0,
            "dungeon_exit": True,
        }],
    })

    assert "generated tile must not define dungeon exits, found 1." in issues


def test_exit_span_must_touch_walkable_cells() -> None:
    issues = validate_tile_definition({
        "key": "11",
        "name": "Room",
        "tile_type": "room",
        "footprint_width": 3,
        "footprint_height": 1,
        "walkable": ["101"],
        "cell_shapes": ["FFF"],
        "exits": [{"id": "wide-north", "direction": "north", "kind": "door", "x": 0, "y": 0, "span": 2}],
    })

    assert "exit wide-north touches blocked cell 1,0." in issues


def test_exit_span_must_stay_in_bounds() -> None:
    issues = validate_tile_definition({
        "key": "11",
        "name": "Room",
        "tile_type": "room",
        "footprint_width": 2,
        "footprint_height": 1,
        "walkable": ["11"],
        "cell_shapes": ["FF"],
        "exits": [{"id": "wide-north", "direction": "north", "kind": "door", "x": 1, "y": 0, "span": 2}],
    })

    assert "exit wide-north span extends outside the footprint grid." in issues


def test_tiles_validation_api() -> None:
    from app.main import app

    client = TestClient(app)
    payload = client.get("/api/rules/tiles/validation").json()
    assert payload["valid"] is True
    assert payload["issues"] == {}
