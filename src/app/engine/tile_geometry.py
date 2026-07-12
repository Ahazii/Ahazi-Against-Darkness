from __future__ import annotations


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
