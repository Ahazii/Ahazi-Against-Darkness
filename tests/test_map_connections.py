from app.engine.map_connections import (
    inherit_connection_from_reciprocal,
    initialize_outside_entrance,
    reciprocal_exit_on_tile,
    sync_connection_state,
)
from app.schemas import ExitState, MapState, PartyMemberState, SessionState, TileState


def _tile(exits: list[ExitState]) -> TileState:
    return TileState(
        id="tile",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="",
        exits=exits,
    )


def test_sync_connection_copies_open_door_state_to_reciprocal_exit() -> None:
    source = ExitState(id="source", direction="east", kind="door", door_open=True, door_type="locked", door_level=3)
    target = ExitState(id="target", direction="west", kind="passage")

    sync_connection_state(source, target, passed_through=True)

    assert (target.kind, target.status, target.door_open, target.door_type, target.door_level) == (
        "door",
        "open",
        True,
        "locked",
        3,
    )


def test_reciprocal_exit_prefers_the_expected_direction() -> None:
    north = ExitState(id="north", direction="north", kind="passage", destination_tile_id="origin")
    west = ExitState(id="west", direction="west", kind="passage", destination_tile_id="origin")

    assert reciprocal_exit_on_tile(_tile([north, west]), "origin", direction="west") is west


def test_inherit_connection_reopens_the_saved_reciprocal_door() -> None:
    origin_exit = ExitState(id="origin", direction="east", kind="door", door_open=True, status="open", destination_tile_id="dest")
    reciprocal = ExitState(id="dest", direction="west", kind="door", door_open=False, destination_tile_id="origin")
    origin = _tile([origin_exit])
    origin.id = "origin"
    destination = _tile([reciprocal])
    destination.id = "dest"
    hero = PartyMemberState(character_id="hero", name="Hero", class_id="warrior", class_name="Warrior", level=1, xp=0, gold=0, current_life=3, max_life=3, attack_bonus=0, defense_bonus=0, save_bonus=0)
    session = SessionState(id="session", party_id="party", adventure_id="random", adventure_type="random", party=[hero], map_state=MapState(tiles=[origin, destination], current_tile_id="dest"), created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")

    inherit_connection_from_reciprocal(
        session,
        destination,
        reciprocal,
        tile_by_id=lambda active_session, tile_id: next((tile for tile in active_session.map_state.tiles if tile.id == tile_id), None),
        opposite={"east": "west", "west": "east"},
    )

    assert reciprocal.door_open is True


def test_initialize_outside_entrance_opens_the_dungeon_door_once() -> None:
    entrance = _tile([ExitState(id="outside", direction="south", kind="door", dungeon_exit=True, status="unexplored")])
    log: list[str] = []

    assert initialize_outside_entrance(entrance, log=log) is True
    assert entrance.exits[0].door_open is True
    assert entrance.exits[0].door_type == "unlocked"
    assert "remains open behind them" in log[0]
    assert initialize_outside_entrance(entrance, log=log) is False
