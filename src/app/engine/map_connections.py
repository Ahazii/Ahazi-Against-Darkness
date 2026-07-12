from __future__ import annotations

from ..schemas import ExitState, TileState


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
