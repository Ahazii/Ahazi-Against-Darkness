from __future__ import annotations

from collections.abc import Callable, Mapping

from ..schemas import ExitState, SessionState, TileState


def clear_door_state(exit_state: ExitState) -> None:
    exit_state.door_type = None
    exit_state.door_level = None
    exit_state.door_result = None
    exit_state.door_open = False
    exit_state.door_treasure_bonus = 0


def sync_connection_state(
    source: ExitState,
    target: ExitState,
    *,
    passed_through: bool = False,
) -> None:
    """Copy the shared state of one map connection to its reciprocal exit."""
    target.kind = source.kind
    target.span = max(source.span, target.span)
    target.door_destroyed = source.door_destroyed
    target.nailed_shut = source.nailed_shut
    if source.kind == "door":
        target.door_type = source.door_type
        target.door_level = source.door_level
        target.door_result = source.door_result
        target.door_treasure_bonus = source.door_treasure_bonus
        if source.nailed_shut:
            target.status = "blocked"
            target.door_open = False
        else:
            target.status = "open"
            target.door_open = True if passed_through else source.door_open
        return
    target.status = "open"
    clear_door_state(target)


def reciprocal_exit_on_tile(
    tile: TileState,
    other_tile_id: str,
    *,
    direction: str | None = None,
) -> ExitState | None:
    matches = [exit_state for exit_state in tile.exits if exit_state.destination_tile_id == other_tile_id]
    if not matches:
        return None
    if direction:
        return next((exit_state for exit_state in matches if exit_state.direction == direction), matches[0])
    return matches[0]


def persist_open_connection(
    session: SessionState,
    origin: TileState,
    origin_exit: ExitState,
    *,
    tile_by_id: Callable[[SessionState, str | None], TileState | None],
    opposite: Mapping[str, str],
) -> None:
    """Persist an open connection on both map elements after the party traverses it."""
    origin_exit.status = "open"
    if origin_exit.kind == "door":
        origin_exit.door_open = True
    if not origin_exit.destination_tile_id:
        return
    destination = tile_by_id(session, origin_exit.destination_tile_id)
    if destination is None:
        return
    reciprocal = reciprocal_exit_on_tile(
        destination,
        origin.id,
        direction=opposite[origin_exit.direction],
    )
    if reciprocal is not None:
        sync_connection_state(origin_exit, reciprocal, passed_through=True)


def inherit_connection_from_reciprocal(
    session: SessionState,
    current: TileState,
    exit_state: ExitState,
    *,
    tile_by_id: Callable[[SessionState, str | None], TileState | None],
    opposite: Mapping[str, str],
) -> None:
    """Repair one side of a saved connection from an already-open reciprocal side."""
    if exit_state.door_open or not exit_state.destination_tile_id:
        return
    other_tile = tile_by_id(session, exit_state.destination_tile_id)
    if other_tile is None:
        return
    reciprocal = reciprocal_exit_on_tile(
        other_tile,
        current.id,
        direction=opposite[exit_state.direction],
    )
    if reciprocal is None:
        return
    if reciprocal.kind == "passage" and reciprocal.status == "open":
        sync_connection_state(reciprocal, exit_state, passed_through=True)
    elif reciprocal.kind == "door" and reciprocal.door_open:
        sync_connection_state(reciprocal, exit_state, passed_through=True)
