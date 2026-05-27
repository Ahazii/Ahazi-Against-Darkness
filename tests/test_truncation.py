from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import ExitState, MapState, SessionState, TileDefinition, TileState


def _tile_02_origin() -> TileState:
    return TileState(
        id="origin-02",
        x=0,
        y=0,
        tile_key="02",
        tile_type="room",
        footprint_width=5,
        footprint_height=6,
        walkable=["00100", "00100", "11111", "11111", "11111", "01110"],
        cell_shapes=["FFFFF", "FFFFF", "FFFFF", "FFFFF", "FFFFF", "FBFAF"],
        visible=["11111", "11111", "11111", "11111", "11111", "11111"],
        title="Entrance 02",
        description="Entrance 02",
        exits=[ExitState(id="02-north", direction="north", kind="door", x=0, y=2)],
    )


def _north_room_def() -> TileDefinition:
    return TileDefinition(
        key="12",
        name="North Room",
        tile_type="room",
        footprint_width=5,
        footprint_height=3,
        walkable=["11111", "11111", "11111"],
        cell_shapes=["FFFFF", "FFFFF", "FFFFF"],
        exits=[{"id": "match-south", "direction": "south", "kind": "door", "x": 0, "y": 2, "span": 1}],
    )


def test_recessed_entry_allows_full_origin_overlap_visible() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin = _tile_02_origin()
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[origin], current_tile_id=origin.id),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    tile_def = _north_room_def()
    exits = engine._rotated_exits(tile_def, 0)
    matching = exits[0]
    x, y = engine._aligned_origin(origin, origin.exits[0], matching, 5, 3)

    placement = engine._truncated_placement(
        session,
        x,
        y,
        5,
        3,
        tile_def,
        0,
        origin,
        origin.exits[0],
        exits,
        matching,
    )

    assert placement is not None
    assert placement.visible == ["11111", "11111", "11111"]
    assert placement.walkable == ["11111", "11111", "11111"]


def test_clip_origin_visible_hides_throat_rows_covered_by_neighbor() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin = _tile_02_origin()
    neighbor = TileState(
        id="north-room",
        x=0,
        y=-1,
        tile_key="12",
        tile_type="room",
        footprint_width=5,
        footprint_height=3,
        walkable=["11111", "11111", "11111"],
        visible=["11111", "11111", "11111"],
        title="North Room",
        description="North Room",
    )

    engine._clip_origin_visible_for_neighbor(origin, neighbor)

    assert origin.visible[0] == "00000"
    assert origin.visible[1] == "00000"
    assert origin.visible[2] == "11111"


def test_truncation_strips_overlap_back_into_origin() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin = TileState(
        id="origin-east",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        footprint_width=4,
        footprint_height=4,
        walkable=["1111", "1111", "1111", "1111"],
        cell_shapes=["FFFF", "FFFF", "FFFF", "FFFF"],
        visible=["1111", "1111", "1111", "1111"],
        title="Origin",
        description="Origin",
        exits=[ExitState(id="east", direction="east", kind="door", x=3, y=1)],
    )
    session = SessionState(
        id="session-east-overlap",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[origin], current_tile_id=origin.id),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    tile_def = TileDefinition(
        key="99",
        name="East Overlap",
        tile_type="room",
        footprint_width=4,
        footprint_height=4,
        walkable=["1111", "1111", "1111", "1111"],
        cell_shapes=["FFFF", "FFFF", "FFFF", "FFFF"],
        exits=[{"id": "west-entry", "direction": "west", "kind": "door", "x": 3, "y": 1}],
    )
    exits = engine._rotated_exits(tile_def, 0)
    matching = exits[0]
    x, y = engine._aligned_origin(origin, origin.exits[0], matching, 4, 4)
    assert (x, y) == (1, 0)

    placement = engine._truncated_placement(
        session,
        x,
        y,
        4,
        4,
        tile_def,
        0,
        origin,
        origin.exits[0],
        exits,
        matching,
    )

    assert placement is not None
    assert placement.truncated is True
    assert placement.visible == ["0001", "0001", "0001", "0001"]
    assert placement.walkable == ["0001", "0001", "0001", "0001"]


def test_strip_neighbor_origin_overlap_on_existing_tile() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin = TileState(
        id="origin-east",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        footprint_width=4,
        footprint_height=4,
        walkable=["1111", "1111", "1111", "1111"],
        visible=["1111", "1111", "1111", "1111"],
        title="Origin",
        description="Origin",
        exits=[ExitState(id="east", direction="east", kind="door", x=3, y=1, destination_tile_id="neighbor")],
    )
    neighbor = TileState(
        id="neighbor",
        x=1,
        y=0,
        tile_key="99",
        tile_type="room",
        footprint_width=4,
        footprint_height=4,
        walkable=["1111", "1111", "1111", "1111"],
        visible=["1111", "1111", "1111", "1111"],
        title="Neighbor",
        description="Neighbor",
        exits=[ExitState(id="west-entry", direction="west", kind="door", x=3, y=1, destination_tile_id="origin-east")],
    )

    engine._strip_neighbor_origin_overlap(origin, neighbor, origin.exits[0])

    assert neighbor.visible == ["0001", "0001", "0001", "0001"]
    assert neighbor.walkable == ["0001", "0001", "0001", "0001"]


def test_truncation_strips_from_entry_side_not_exit_side() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    removed = engine._directional_truncation_cells({(1, 2), (1, 3)}, 4, 4, "south")
    assert (1, 2) in removed
    assert (1, 3) in removed
    assert (1, 1) not in removed
    assert (1, 0) not in removed
