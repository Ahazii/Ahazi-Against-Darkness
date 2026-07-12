from app.engine.map_connections import reciprocal_exit_on_tile, sync_connection_state
from app.schemas import ExitState, TileState


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
