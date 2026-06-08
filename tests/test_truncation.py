from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import ExitState, MapState, SessionState, TileDefinition, TileState


class _Rules:
    def __init__(self, tiles: dict[str, TileDefinition]) -> None:
        self._tiles = tiles

    def tiles(self) -> dict[str, TileDefinition]:
        return self._tiles


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


def _entrance_02() -> TileState:
    return TileState(
        id="entrance-02",
        x=0,
        y=0,
        tile_key="02",
        tile_type="room",
        footprint_width=7,
        footprint_height=6,
        walkable=["0001000", "0001000", "0111110", "0111111", "0111110", "0011100"],
        cell_shapes=["FFFFFFF", "FFFFFFF", "FFFFFFF", "FFFFFFF", "FFFFFFF", "FFFFFFF"],
        visible=["1111111", "1111111", "1111111", "1111111", "1111111", "1111111"],
        title="Entrance Map Element 02",
        description="Entrance Map Element 02",
        content_key="entrance",
        exits=[
            ExitState(id="02-south-passage", direction="south", kind="door", x=3, y=4, dungeon_exit=True),
            ExitState(id="02-north-passage", direction="north", kind="door", x=1, y=2),
            ExitState(id="02-east-door", direction="north", kind="passage", x=3, y=0),
            ExitState(id="02-west-door", direction="east", kind="door", x=5, y=3),
        ],
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


def test_inset_exit_edge_traces_through_walkable_corridor_to_boundary() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    tile = TileState(
        id="tile-26",
        x=0,
        y=-2,
        tile_key="26",
        tile_type="corridor",
        footprint_width=4,
        footprint_height=3,
        walkable=["0010", "0110", "0000"],
        visible=["1111", "1111", "0000"],
        title="Map Element 26",
        description="Map Element 26",
        exits=[
            ExitState(id="north", direction="north", kind="door", x=2, y=1),
            ExitState(id="south", direction="south", kind="door", x=1, y=1),
        ],
    )

    north_inside, north_outside = engine._exit_edge(tile, tile.exits[0])
    south_inside, south_outside = engine._exit_edge(tile, tile.exits[1])
    north_targets, _north_throat = engine._exit_portal_cells(tile, tile.exits[0])

    assert north_inside == (2, -2)
    assert north_outside == (2, -3)
    assert north_targets == {(2, -3)}
    assert north_outside not in engine._occupied_cells(tile)
    assert south_inside == (1, -1)
    assert south_outside == (1, 0)


def test_entrance_non_dungeon_exit_uses_authored_portal() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    entrance = _entrance_02()
    north_exit = next(exit_state for exit_state in entrance.exits if exit_state.id == "02-north-passage")

    inside, outside = engine._exit_edge(entrance, north_exit)
    targets, throat = engine._exit_portal_cells(entrance, north_exit)

    assert inside == (1, 2)
    assert outside == (1, 1)
    assert targets == {(1, 1)}
    assert throat == set()


def test_entrance_non_dungeon_placement_can_overlap_blocked_padding() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    entrance = _entrance_02()
    north_exit = next(exit_state for exit_state in entrance.exits if exit_state.id == "02-north-passage")
    session = SessionState(
        id="session-entrance-02",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[entrance], current_tile_id=entrance.id),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    tile_def = TileDefinition(
        key="32",
        name="Map Element 32",
        tile_type="corridor",
        footprint_width=6,
        footprint_height=5,
        walkable=["010010", "010010", "011110", "000010", "000010"],
        cell_shapes=["FFFFFF", "FFFFFF", "FFFFFF", "FFFFFF", "FFFFFF"],
        exits=[{"id": "match-south", "direction": "south", "kind": "door", "x": 4, "y": 4}],
    )
    exits = engine._rotated_exits(tile_def, 0)
    matching = exits[0]
    x, y = engine._aligned_origin(entrance, north_exit, matching, 6, 5)

    placement = engine._truncated_placement(
        session,
        x,
        y,
        6,
        5,
        tile_def,
        0,
        entrance,
        north_exit,
        exits,
        matching,
    )

    assert (x, y) == (-3, -3)
    assert placement is not None
    assert placement.walkable == tile_def.walkable
    assert placement.visible == ["111111", "111111", "111111", "111111", "111111"]


def test_entrance_dungeon_exit_target_stays_reserved() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    entrance = _entrance_02()
    north_exit = next(exit_state for exit_state in entrance.exits if exit_state.id == "02-north-passage")
    session = SessionState(
        id="session-entrance-dungeon-exit",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[entrance], current_tile_id=entrance.id),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    tile_def = TileDefinition(
        key="99",
        name="Blocked Dungeon Exit Candidate",
        tile_type="room",
        footprint_width=1,
        footprint_height=1,
        walkable=["1"],
        cell_shapes=["F"],
        exits=[{"id": "match-south", "direction": "south", "kind": "door", "x": 0, "y": 0}],
    )
    exits = engine._rotated_exits(tile_def, 0)
    matching = exits[0]

    placement = engine._truncated_placement(
        session,
        3,
        6,
        1,
        1,
        tile_def,
        0,
        entrance,
        north_exit,
        exits,
        matching,
    )

    assert engine._protected_dungeon_exit_cells(session, entrance, north_exit) == {(3, 6)}
    assert placement is None


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


def test_clip_origin_visible_preserves_entrance_tile() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    entrance = _tile_02_origin()
    entrance.content_key = "entrance"
    original_visible = list(entrance.visible)
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

    engine._clip_origin_visible_for_neighbor(entrance, neighbor)

    assert entrance.visible == original_visible


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


def test_placement_links_adjacent_reserved_exits_when_room_reaches_them() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin = TileState(
        id="origin-three-doors",
        x=0,
        y=0,
        tile_key="03",
        tile_type="room",
        footprint_width=3,
        footprint_height=1,
        walkable=["111"],
        cell_shapes=["FFF"],
        visible=["111"],
        title="Three North Doors",
        description="Three North Doors",
        exits=[
            ExitState(id="n1", direction="north", kind="door", x=0, y=0),
            ExitState(id="n2", direction="north", kind="door", x=1, y=0),
            ExitState(id="n3", direction="north", kind="door", x=2, y=0),
        ],
    )
    session = SessionState(
        id="session-three-doors",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[origin], current_tile_id=origin.id),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    tile_def = TileDefinition(
        key="98",
        name="Wide North Room",
        tile_type="room",
        footprint_width=3,
        footprint_height=1,
        walkable=["111"],
        cell_shapes=["FFF"],
        exits=[{"id": "match-south", "direction": "south", "kind": "door", "x": 0, "y": 0}],
    )
    exits = engine._rotated_exits(tile_def, 0)
    matching = exits[0]
    x, y = engine._aligned_origin(origin, origin.exits[0], matching, 3, 1)

    assert (x, y) == (0, -1)
    assert engine._placement_blocked(session, x, y, 3, 1, tile_def, 0, origin, origin.exits[0])

    placement = engine._truncated_placement(
        session,
        x,
        y,
        3,
        1,
        tile_def,
        0,
        origin,
        origin.exits[0],
        exits,
        matching,
    )

    assert placement is not None
    assert placement.walkable == ["111"]
    assert placement.visible == ["111"]

    neighbor = TileState(
        id="wide-neighbor",
        x=x,
        y=y,
        tile_key="98",
        tile_type="room",
        footprint_width=3,
        footprint_height=1,
        walkable=placement.walkable,
        cell_shapes=placement.cell_shapes,
        visible=placement.visible,
        title="Wide North Room",
        description="Wide North Room",
        exits=placement.exits,
    )
    session.map_state.tiles.append(neighbor)
    engine._set_reciprocal_exit(neighbor, origin, origin.exits[0])
    engine._connect_reserved_exits_to_neighbor(session, neighbor, origin, origin.exits[0])

    assert origin.exits[1].destination_tile_id == neighbor.id
    assert origin.exits[2].destination_tile_id == neighbor.id
    linked_back = [exit_state for exit_state in neighbor.exits if exit_state.destination_tile_id == origin.id]
    assert len(linked_back) == 3
    assert all(exit_state.kind == "door" for exit_state in linked_back)
    used_entry = next(exit_state for exit_state in linked_back if exit_state.x == 0)
    adjacent_links = [exit_state for exit_state in linked_back if exit_state.x in {1, 2}]
    assert used_entry.door_open is True
    assert all(exit_state.door_open is False for exit_state in adjacent_links)


def test_reserved_exit_can_connect_through_multi_square_blocked_throat() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    source = TileState(
        id="deep-source",
        x=0,
        y=0,
        tile_key="02",
        tile_type="room",
        footprint_width=1,
        footprint_height=3,
        walkable=["1", "0", "0"],
        cell_shapes=["F", "F", "F"],
        visible=["1", "1", "1"],
        title="Deep Door",
        description="Deep Door",
        exits=[ExitState(id="deep-door", direction="south", kind="door", x=0, y=0)],
    )
    origin = TileState(
        id="current-origin",
        x=5,
        y=0,
        tile_key="11",
        tile_type="room",
        footprint_width=1,
        footprint_height=1,
        walkable=["1"],
        visible=["1"],
        title="Current",
        description="Current",
        exits=[ExitState(id="origin-north", direction="north", kind="door", x=0, y=0)],
    )
    neighbor = TileState(
        id="new-neighbor",
        x=0,
        y=1,
        tile_key="12",
        tile_type="room",
        footprint_width=1,
        footprint_height=3,
        walkable=["1", "1", "1"],
        cell_shapes=["F", "F", "F"],
        visible=["1", "1", "1"],
        title="New Neighbor",
        description="New Neighbor",
        exits=[],
    )
    session = SessionState(
        id="session-deep-throat",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[source, origin, neighbor], current_tile_id=origin.id),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )

    engine._connect_reserved_exits_to_neighbor(session, neighbor, origin, origin.exits[0])
    for tile in session.map_state.tiles:
        if tile.id != neighbor.id:
            engine._clip_origin_visible_for_neighbor(tile, neighbor)

    assert source.exits[0].destination_tile_id == neighbor.id
    reciprocal = next(exit_state for exit_state in neighbor.exits if exit_state.destination_tile_id == source.id)
    assert reciprocal.direction == "north"
    assert (reciprocal.x, reciprocal.y) == (0, 2)
    assert reciprocal.kind == "door"
    assert reciprocal.door_open is False
    assert source.visible == ["1", "0", "0"]


def test_generate_tile_rerolls_when_first_map_element_cannot_be_placed(monkeypatch) -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin = TileState(
        id="origin",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        footprint_width=1,
        footprint_height=1,
        walkable=["1"],
        visible=["1"],
        title="Origin",
        description="Origin",
        exits=[ExitState(id="north", direction="north", kind="passage", x=0, y=0)],
    )
    bad_def = TileDefinition(
        key="11",
        name="Bad Candidate",
        tile_type="room",
        footprint_width=1,
        footprint_height=1,
        walkable=["1"],
        cell_shapes=["F"],
        exits=[{"id": "wrong-side", "direction": "north", "kind": "passage", "x": 0, "y": 0}],
    )
    good_def = TileDefinition(
        key="12",
        name="Good Candidate",
        tile_type="room",
        footprint_width=1,
        footprint_height=1,
        walkable=["1"],
        cell_shapes=["F"],
        exits=[{"id": "entry", "direction": "south", "kind": "passage", "x": 0, "y": 0}],
    )
    session = SessionState(
        id="session-reroll",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[origin], current_tile_id=origin.id),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    content_rolls: list[str] = []

    engine.rules = _Rules({"11": bad_def, "12": good_def})
    monkeypatch.setattr(engine, "_roll_generated_tile_key", lambda: "11")
    original_select = engine._select_placement

    def _select_placement(_session, _origin, _origin_exit, tile_type, tile_def):
        if tile_def and tile_def.key == "11":
            return None
        return original_select(_session, _origin, _origin_exit, tile_type, tile_def)

    monkeypatch.setattr(engine, "_select_placement", _select_placement)

    def _roll_content(_session, tile_type: str, _hcl: int) -> dict:
        content_rolls.append(tile_type)
        return engine._content("empty", "The area is quiet.", [], [], roll=8)

    monkeypatch.setattr(engine, "_roll_content", _roll_content)

    tile = engine._generate_tile(session, origin, origin.exits[0], hcl=1, show_rolls=True)

    assert tile is not None
    assert tile.tile_key == "12"
    assert (tile.x, tile.y) == (0, -1)
    assert content_rolls == ["room"]
    assert "Map element roll: d66 = 11; no legal placement, rerolling." in session.log
    assert "Map element roll: d66 = 12." in session.log
    assert session.log.count("Room content roll: 2d6 = 8.") == 1


def test_generate_tile_falls_back_to_one_square_dead_end_when_all_candidates_fail(monkeypatch) -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin = TileState(
        id="origin",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        footprint_width=1,
        footprint_height=1,
        walkable=["1"],
        visible=["1"],
        title="Origin",
        description="Origin",
        exits=[ExitState(id="north", direction="north", kind="door", x=0, y=0, door_open=True)],
    )
    bad_def = TileDefinition(
        key="11",
        name="Bad Candidate",
        tile_type="room",
        footprint_width=1,
        footprint_height=1,
        walkable=["1"],
        cell_shapes=["F"],
        exits=[{"id": "wrong-side", "direction": "north", "kind": "door", "x": 0, "y": 0}],
    )
    session = SessionState(
        id="session-fallback",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[origin], current_tile_id=origin.id),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )

    engine.rules = _Rules({"11": bad_def})
    monkeypatch.setattr(engine, "_roll_generated_tile_key", lambda: "11")
    monkeypatch.setattr(engine, "_select_placement", lambda *_args, **_kwargs: None)

    tile = engine._generate_tile(session, origin, origin.exits[0], hcl=1, show_rolls=True)

    assert tile is not None
    assert tile.tile_key == "00"
    assert tile.tile_type == "corridor"
    assert tile.walkable == ["1"]
    assert tile.visible == ["1"]
    assert tile.exits[0].direction == "south"
    assert tile.exits[0].kind == "door"
    assert "No generated map element could be placed after 1 attempt; drawing a 1x1 dead end." in session.log
    assert "Emergency placement fallback: 1x1 dead-end map element." in session.log
    assert "Emergency dead-end fallback: no room content roll." in session.log
