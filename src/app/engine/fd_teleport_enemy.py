"""Forsaken Depths Teleport Enemy return tracking (FD p.19)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from ..schemas import EnemyState, SessionState, TeleportEnemyReturnState, TileState
from .dice import roll_d6
from .reactions import (
    apply_reaction_overlays,
    build_reaction_outcome,
    lookup_reaction_row,
    normalize_reaction_row,
    resolve_reaction_source,
)


def _tile_by_id(session: SessionState, tile_id: str | None) -> TileState | None:
    if not tile_id:
        return None
    return next((tile for tile in session.map_state.tiles if tile.id == tile_id), None)


def _passable_neighbor_ids(tile: TileState) -> list[str]:
    ids: list[str] = []
    for exit_state in tile.exits:
        if not exit_state.destination_tile_id:
            continue
        if exit_state.status == "blocked":
            continue
        if exit_state.kind == "door" and not exit_state.door_open:
            continue
        ids.append(exit_state.destination_tile_id)
    return ids


def _passable_between(session: SessionState, source_id: str, dest_id: str) -> bool:
    source = _tile_by_id(session, source_id)
    if source is None:
        return False
    return dest_id in _passable_neighbor_ids(source)


def _paths_from_origin(session: SessionState, origin_id: str) -> list[list[str]]:
    visited_ids = set(session.visited_tile_ids or [])
    visited_ids.add(origin_id)
    queue: deque[list[str]] = deque([[origin_id]])
    seen = {origin_id}
    paths: list[list[str]] = []
    while queue:
        path = queue.popleft()
        paths.append(path)
        tile = _tile_by_id(session, path[-1])
        if tile is None:
            continue
        for neighbor_id in sorted(_passable_neighbor_ids(tile)):
            if neighbor_id in seen or neighbor_id not in visited_ids:
                continue
            seen.add(neighbor_id)
            queue.append([*path, neighbor_id])
    return paths


def queue_teleport_enemy_return(
    session: SessionState,
    enemy: EnemyState,
    *,
    origin_tile_id: str,
    distance: int,
    log: list[str],
) -> None:
    paths = [path for path in _paths_from_origin(session, origin_tile_id) if len(path) > 1]
    if not paths:
        log.append(
            f"{enemy.name} has no visited room/hex/area to return from and stays out of this combat (FD p.19)."
        )
        return
    exact = [path for path in paths if len(path) - 1 == distance]
    candidates = exact or [path for path in paths if len(path) - 1 <= distance] or paths
    chosen = max(candidates, key=lambda path: (len(path), path[-1]))
    route = list(reversed(chosen))
    start = _tile_by_id(session, route[0])
    state = TeleportEnemyReturnState(
        enemy=enemy.model_copy(deep=True),
        origin_tile_id=origin_tile_id,
        current_tile_id=route[0],
        route_tile_ids=route,
        turns_remaining=max(0, len(route) - 1),
    )
    session.fd_teleport_enemy_returns.append(state)
    place = start.title if start else "a visited area"
    if len(chosen) - 1 != distance:
        log.append(
            f"Teleport Enemy rolled {distance}, but only {len(chosen) - 1} passable visited room(s) were available; "
            f"{enemy.name} lands in {place} and starts back (FD p.19)."
        )
    else:
        log.append(f"{enemy.name} lands in {place} and starts back toward the fight (FD p.19).")


def tick_teleport_enemy_returns(
    session: SessionState,
    *,
    log: list[str] | None = None,
    reason: str = "turn",
    reaction_tables: dict[str, list[dict]] | None = None,
    roll_reaction: Callable[[str, int], dict | None] | None = None,
) -> None:
    output = log if log is not None else session.log
    remaining: list[TeleportEnemyReturnState] = []
    for pending in session.fd_teleport_enemy_returns:
        if pending.blocked:
            remaining.append(pending)
            continue
        route = list(pending.route_tile_ids or [])
        if len(route) <= 1:
            _restore_enemy(session, pending, output)
            continue
        source_id, dest_id = route[0], route[1]
        source = _tile_by_id(session, source_id)
        dest = _tile_by_id(session, dest_id)
        if source is None or dest is None or not _passable_between(session, source_id, dest_id):
            pending.blocked = True
            place = source.title if source else "its return route"
            output.append(
                f"{pending.enemy.name} cannot return from {place}; an obstacle blocks the route (FD p.19)."
            )
            remaining.append(pending)
            continue
        pending.current_tile_id = dest_id
        pending.route_tile_ids = route[1:]
        pending.turns_remaining = max(0, len(pending.route_tile_ids) - 1)
        output.append(
            f"{pending.enemy.name} moves one room/hex/area back after {reason}; "
            f"{pending.turns_remaining} to go (FD p.19)."
        )
        if dest_id == pending.origin_tile_id:
            _restore_enemy(session, pending, output)
            continue
        _resolve_occupied_room_reaction(
            pending,
            dest,
            output,
            reaction_tables=reaction_tables or {},
            roll_reaction=roll_reaction,
        )
        remaining.append(pending)
    session.fd_teleport_enemy_returns = remaining


def _resolve_occupied_room_reaction(
    pending: TeleportEnemyReturnState,
    dest: TileState,
    log: list[str],
    *,
    reaction_tables: dict[str, list[dict]],
    roll_reaction: Callable[[str, int], dict | None] | None,
) -> None:
    living = [enemy for enemy in dest.enemies if enemy.life > 0]
    if not living:
        return
    source = resolve_reaction_source(living, reaction_tables)
    roll = roll_d6()
    if source.inline_rows:
        row = lookup_reaction_row(source.inline_rows, roll)
        table_label = f"{source.label} reaction table"
    else:
        table_label = source.table_name or "default_reaction_table"
        row = roll_reaction(table_label, roll) if roll_reaction else None
    if row is None:
        row = {"key": "fight", "result": "The occupants attack!", "foes_first": True}
        table_label = "default reaction fallback"
    row = normalize_reaction_row(apply_reaction_overlays(row, living, roll) or row)
    outcome = build_reaction_outcome(row, hcl=max(1, pending.enemy.level), foe_count=len(living))
    log.append(
        f"Teleport Enemy occupied-room reaction: {pending.enemy.name} crosses {dest.title}; "
        f"d6 = {roll} on {table_label} (FD p.19)."
    )
    log.append(f"Occupied-room reaction outcome: {outcome.result}")
    if outcome.foes_first or outcome.key in {"fight", "fight_to_death", "capture", "puzzle", "magic_challenge"}:
        log.append(
            f"{dest.title}'s occupants engage {pending.enemy.name}; resolve that monster clash if it matters "
            "before the returning foe reaches the party (FD p.19)."
        )
    else:
        log.append(f"{dest.title}'s occupants do not block {pending.enemy.name}'s return route (FD p.19).")


def _restore_enemy(session: SessionState, pending: TeleportEnemyReturnState, log: list[str]) -> None:
    origin = _tile_by_id(session, pending.origin_tile_id)
    if origin is None:
        log.append(f"{pending.enemy.name}'s original combat area no longer exists; it cannot return (FD p.19).")
        return
    enemy = pending.enemy.model_copy(deep=True)
    enemy.life = max(1, enemy.life)
    enemy.tags = [tag for tag in enemy.tags if tag != "fd_teleported_away"]
    origin.enemies.append(enemy)
    log.append(f"{enemy.name} returns to {origin.title} and rejoins the encounter (FD p.19).")
