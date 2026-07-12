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


def refresh_tile_connections(
    session: SessionState,
    tile: TileState,
    *,
    inherit_connection: Callable[[SessionState, TileState, ExitState], None],
    sync_linked_door: Callable[[SessionState, TileState, ExitState], None],
) -> None:
    """Repair every saved reciprocal connection on a map element before it is used."""
    for exit_state in tile.exits:
        if not exit_state.destination_tile_id:
            continue
        inherit_connection(session, tile, exit_state)
        if exit_state.kind == "door" and exit_state.door_open:
            sync_linked_door(session, tile, exit_state)


def initialize_outside_entrance(entrance: TileState, *, log: list[str] | None = None) -> bool:
    """Open the dungeon-entry exit behind the party (Expanded Edition p.25)."""
    changed = False
    for exit_state in entrance.exits:
        if not exit_state.dungeon_exit or exit_state.nailed_shut or exit_state.door_destroyed:
            continue
        if exit_state.status == "open" and (exit_state.kind != "door" or exit_state.door_open):
            continue
        exit_state.status = "open"
        if exit_state.kind == "door":
            exit_state.door_open = True
            exit_state.door_type = exit_state.door_type or "unlocked"
        changed = True
        if log is not None:
            exit_label = "door" if exit_state.kind == "door" else "opening"
            log.append(
                f"The party entered through the {exit_state.direction} {exit_label}; it remains open behind them."
            )
    return changed


def set_reciprocal_exit(
    destination: TileState,
    origin: TileState,
    origin_exit: ExitState,
    *,
    opposite: Mapping[str, str],
    exit_edge: Callable[[TileState, ExitState], tuple[tuple[int, int], tuple[int, int]]],
    rotated_size: Callable[[int, int, int], tuple[int, int]],
    new_exit: Callable[..., ExitState],
) -> ExitState:
    """Select or create the exit on a destination tile which returns to the origin."""
    reciprocal_direction = opposite[origin_exit.direction]
    origin_inside, _ = exit_edge(origin, origin_exit)
    reciprocal = next(
        (
            exit_state
            for exit_state in destination.exits
            if exit_state.direction == reciprocal_direction
            and exit_state.destination_tile_id in (None, origin.id)
            and exit_edge(destination, exit_state)[1] == origin_inside
        ),
        None,
    ) or next(
        (exit_state for exit_state in destination.exits if exit_state.direction == reciprocal_direction),
        None,
    )
    if reciprocal is None:
        width, height = rotated_size(
            destination.footprint_width,
            destination.footprint_height,
            destination.rotation,
        )
        reciprocal = new_exit(
            direction=reciprocal_direction,
            kind=origin_exit.kind,
            width=width,
            height=height,
            status="open",
            span=origin_exit.span,
        )
        destination.exits.append(reciprocal)
    reciprocal.status = "open"
    reciprocal.destination_tile_id = origin.id
    sync_connection_state(origin_exit, reciprocal, passed_through=True)
    return reciprocal


def sync_linked_door(
    session: SessionState,
    current: TileState,
    exit_state: ExitState,
    *,
    tile_by_id: Callable[[SessionState, str | None], TileState | None],
    opposite: Mapping[str, str],
) -> None:
    """Synchronize a manually changed door with its connected reciprocal door."""
    if exit_state.kind != "door" or not exit_state.destination_tile_id:
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
    sync_connection_state(exit_state, reciprocal, passed_through=exit_state.door_open)
    if not exit_state.nailed_shut:
        reciprocal.status = "open"
