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

    assert "exit wide-north has blocked anchor 1,0 without a traversable interior square." in issues


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


def test_diagonal_exit_span_validation() -> None:
    valid = validate_tile_definition({
        "key": "11",
        "name": "Diagonal room",
        "tile_type": "room",
        "footprint_width": 3,
        "footprint_height": 3,
        "walkable": ["111", "111", "111"],
        "cell_shapes": ["FFF", "FFF", "FFF"],
        "exits": [{
            "id": "northeast-wide",
            "direction": "northeast",
            "kind": "passage",
            "x": 0,
            "y": 0,
            "span": 3,
        }],
    })
    assert valid == []

    invalid = validate_tile_definition({
        "key": "11",
        "name": "Diagonal room",
        "tile_type": "room",
        "footprint_width": 3,
        "footprint_height": 3,
        "walkable": ["111", "111", "111"],
        "cell_shapes": ["FFF", "FFF", "FFF"],
        "exits": [{
            "id": "southeast-wide",
            "direction": "southeast",
            "kind": "door",
            "x": 1,
            "y": 0,
            "span": 2,
        }],
    })
    assert "exit southeast-wide span extends outside the footprint grid." in invalid


def test_exit_may_use_one_blocked_padding_anchor() -> None:
    issues = validate_tile_definition({
        "key": "23",
        "name": "River bend",
        "catalog": "forsaken_depths_rivers",
        "tile_type": "corridor",
        "footprint_width": 3,
        "footprint_height": 1,
        "walkable": ["120"],
        "cell_shapes": ["FFF"],
        "exits": [{
            "id": "east-padding",
            "direction": "east",
            "kind": "passage",
            "x": 2,
            "y": 0,
        }],
    }, catalog="forsaken_depths_rivers")

    assert issues == []


def test_tiles_validation_api() -> None:
    from app.main import app

    client = TestClient(app)
    payload = client.get("/api/rules/tiles/validation").json()
    assert payload["valid"] is True
    assert payload["issues"] == {}


def test_entrance_tile_02_inset_exit_metadata_regression() -> None:
    """Regression: tile 02 inset exits must not be rewritten to footprint edges."""
    repo = RulesRepository(packaged(), packaged() / "_override")
    tile = repo.tiles()["02"]
    by_id = {exit.id: exit for exit in tile.exits}

    assert tile.footprint_width == 6
    assert tile.footprint_height == 6
    assert set(by_id) == {"02-south-passage", "02-north-passage", "02-north-door", "02-east-door"}

    north_passage = by_id["02-north-passage"]
    assert north_passage.direction == "north"
    assert north_passage.kind == "door"
    assert north_passage.x == 1
    assert north_passage.y == 2
    assert north_passage.dungeon_exit is False
    assert tile.walkable[north_passage.y][north_passage.x] == "1"
    assert tile.walkable[north_passage.y - 1][north_passage.x] == "0"

    south_passage = by_id["02-south-passage"]
    assert south_passage.direction == "south"
    assert south_passage.y == 4
    assert south_passage.y != tile.footprint_height - 1
    assert south_passage.dungeon_exit is True

    east_door = by_id["02-east-door"]
    assert east_door.direction == "east"
    assert east_door.x == 5
    assert east_door.y == 3

    north_door = by_id["02-north-door"]
    assert north_door.direction == "north"
    assert north_door.kind == "passage"
    assert north_door.x == 3
    assert north_door.y == 0
