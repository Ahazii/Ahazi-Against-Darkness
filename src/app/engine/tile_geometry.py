from __future__ import annotations

from collections.abc import Mapping

from ..schemas import ExitState, TileState


DIRECTION_ORDER = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
EXIT_SPAN_STEPS = {
    "north": (1, 0),
    "south": (1, 0),
    "east": (0, 1),
    "west": (0, 1),
    "northeast": (1, 1),
    "southwest": (1, 1),
    "southeast": (1, -1),
    "northwest": (1, -1),
}


def rotated_size(width: int, height: int, rotation: int) -> tuple[int, int]:
    return (height, width) if rotation in (90, 270) else (width, height)


def rotate_cell(x: int, y: int, width: int, height: int, rotation: int) -> tuple[int, int]:
    turns = (rotation // 90) % 4
    if turns == 1:
        return height - 1 - y, x
    if turns == 2:
        return width - 1 - x, height - 1 - y
    if turns == 3:
        return y, width - 1 - x
    return x, y


def rotate_direction(direction: str, rotation: int) -> str:
    turns = (rotation // 90) % 4
    index = DIRECTION_ORDER.index(direction)
    return DIRECTION_ORDER[(index + turns * 2) % len(DIRECTION_ORDER)]


def side_length(direction: str, width: int, height: int) -> int:
    if direction not in {"north", "south", "east", "west"}:
        return min(width, height)
    return width if direction in {"north", "south"} else height


def position_from_offset(offset: int, direction: str, width: int, height: int) -> float:
    length = side_length(direction, width, height)
    if length <= 1:
        return 0.5
    return max(0.0, min(1.0, offset / (length - 1)))


def exit_offset(direction: str, x: int, y: int) -> int:
    if direction not in {"north", "south", "east", "west"}:
        return min(x, y)
    return x if direction in {"north", "south"} else y


def max_exit_span(direction: str, x: int, y: int, width: int, height: int) -> int:
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    step_x, step_y = EXIT_SPAN_STEPS[direction]
    unlimited = width + height
    x_room = width - x if step_x > 0 else x + 1 if step_x < 0 else unlimited
    y_room = height - y if step_y > 0 else y + 1 if step_y < 0 else unlimited
    return max(1, min(x_room, y_room))


def exit_cells(
    x: int,
    y: int,
    direction: str,
    span: int,
    width: int,
    height: int,
) -> list[tuple[int, int]]:
    clamped_span = max(1, min(span, max_exit_span(direction, x, y, width, height)))
    step_x, step_y = EXIT_SPAN_STEPS[direction]
    return [(x + index * step_x, y + index * step_y) for index in range(clamped_span)]


def default_entry_cell(direction: str, width: int, height: int) -> tuple[int, int]:
    if direction == "northeast":
        return width - 1, 0
    if direction == "southeast":
        return width - 1, height - 1
    if direction == "southwest":
        return 0, height - 1
    if direction == "northwest":
        return 0, 0
    offset = max(0, side_length(direction, width, height) // 2)
    if direction in {"north", "south"}:
        return min(offset, width - 1), 0 if direction == "north" else height - 1
    return 0 if direction == "west" else width - 1, min(offset, height - 1)


def state_rows(rows: list[str], width: int, height: int, default: str) -> list[str]:
    if len(rows) == height and all(len(row) == width for row in rows):
        return rows
    return [default * width for _ in range(height)]


def footprint_cells(x: int, y: int, width: int, height: int) -> set[tuple[int, int]]:
    return {(x + dx, y + dy) for dx in range(width) for dy in range(height)}


def occupied_cells(tile: TileState) -> set[tuple[int, int]]:
    """Return the walkable world cells occupied by a rendered tile footprint."""
    width, height = rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    if len(tile.walkable) == height and all(len(row) == width for row in tile.walkable):
        return {
            (tile.x + local_x, tile.y + local_y)
            for local_y, row in enumerate(tile.walkable)
            for local_x, value in enumerate(row)
            if value != "0"
        }
    return footprint_cells(tile.x, tile.y, width, height)


def visible_cells(tile: TileState) -> set[tuple[int, int]]:
    """Return all non-clipped world cells visible on the tactical map."""
    width, height = rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    if len(tile.visible) == height and all(len(row) == width for row in tile.visible):
        return {
            (tile.x + local_x, tile.y + local_y)
            for local_y, row in enumerate(tile.visible)
            for local_x, value in enumerate(row)
            if value != "0"
        }
    return footprint_cells(tile.x, tile.y, width, height)


def trace_exit_portal(
    local_x: int,
    local_y: int,
    direction: str,
    width: int,
    height: int,
    walkable: list[str],
    visible: list[str],
    *,
    directions: Mapping[str, tuple[int, int]],
) -> tuple[tuple[int, int], tuple[int, int], set[tuple[int, int]]]:
    """Trace a portal from its anchor through an authored tile's clipped cells."""
    dx, dy = directions[direction]
    inside = (max(0, min(local_x, width - 1)), max(0, min(local_y, height - 1)))
    if walkable[inside[1]][inside[0]] == "0":
        prior_x = inside[0] - dx
        prior_y = inside[1] - dy
        if 0 <= prior_x < width and 0 <= prior_y < height and walkable[prior_y][prior_x] != "0":
            inside = (prior_x, prior_y)
    probe_x = inside[0] + dx
    probe_y = inside[1] + dy
    throat_cells: set[tuple[int, int]] = set()
    while 0 <= probe_x < width and 0 <= probe_y < height:
        if visible[probe_y][probe_x] == "0":
            return inside, (probe_x, probe_y), throat_cells
        if walkable[probe_y][probe_x] != "0":
            inside = (probe_x, probe_y)
        else:
            throat_cells.add((probe_x, probe_y))
        probe_x += dx
        probe_y += dy
    return inside, (probe_x, probe_y), throat_cells


def uses_authored_exit_portal(
    tile: TileState,
    exit_state: ExitState,
    *,
    directions: Mapping[str, tuple[int, int]],
    is_entrance_tile: bool,
) -> bool:
    if exit_state.dungeon_exit:
        return False
    width, height = rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    walkable = state_rows(tile.walkable, width, height, "1")
    dx, dy = directions[exit_state.direction]
    for local_x, local_y in exit_cells(
        exit_state.x,
        exit_state.y,
        exit_state.direction,
        exit_state.span,
        width,
        height,
    ):
        if walkable[local_y][local_x] == "0":
            inside_x = local_x - dx
            inside_y = local_y - dy
            if (
                0 <= inside_x < width
                and 0 <= inside_y < height
                and walkable[inside_y][inside_x] != "0"
            ):
                return True
        target_x = local_x + dx
        target_y = local_y + dy
        if 0 <= target_x < width and 0 <= target_y < height and walkable[target_y][target_x] == "0":
            if is_entrance_tile:
                return True
            next_x = target_x + dx
            next_y = target_y + dy
            if not (0 <= next_x < width and 0 <= next_y < height):
                return True
    return False


def authored_exit_edge(
    tile: TileState,
    exit_state: ExitState,
    *,
    directions: Mapping[str, tuple[int, int]],
) -> tuple[tuple[int, int], tuple[int, int]]:
    width, height = rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
    local_x, local_y = exit_cells(
        exit_state.x,
        exit_state.y,
        exit_state.direction,
        exit_state.span,
        width,
        height,
    )[0]
    dx, dy = directions[exit_state.direction]
    walkable = state_rows(tile.walkable, width, height, "1")
    if walkable[local_y][local_x] == "0":
        inside_local = (local_x - dx, local_y - dy)
        outside_local = (local_x, local_y)
    else:
        inside_local = (local_x, local_y)
        outside_local = (local_x + dx, local_y + dy)
    return (
        (tile.x + inside_local[0], tile.y + inside_local[1]),
        (tile.x + outside_local[0], tile.y + outside_local[1]),
    )
