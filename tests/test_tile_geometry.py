from app.engine.tile_geometry import (
    default_entry_cell,
    exit_cells,
    max_exit_span,
    occupied_cells,
    rotate_cell,
    rotate_direction,
    rotated_size,
    state_rows,
    visible_cells,
)
from app.schemas import TileState


def test_rotation_and_size_keep_rectangular_tile_coordinates_aligned() -> None:
    assert rotated_size(3, 2, 90) == (2, 3)
    assert rotate_cell(2, 1, 3, 2, 90) == (0, 2)
    assert rotate_direction("north", 90) == "east"


def test_exit_geometry_clamps_span_and_uses_expected_edge_anchor() -> None:
    assert default_entry_cell("south", 5, 3) == (2, 2)
    assert max_exit_span("north", 3, 0, 4, 2) == 1
    assert exit_cells(2, 0, "north", 4, 4, 2) == [(2, 0), (3, 0)]


def test_state_rows_returns_a_safe_full_grid_for_invalid_saved_rows() -> None:
    assert state_rows(["11"], 2, 2, "0") == ["00", "00"]
    assert state_rows(["10", "01"], 2, 2, "0") == ["10", "01"]


def test_tile_cells_respect_authored_walkable_and_visible_clipping() -> None:
    tile = TileState(
        id="tile",
        x=10,
        y=20,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="",
        footprint_width=2,
        footprint_height=2,
        walkable=["10", "01"],
        visible=["11", "00"],
    )

    assert occupied_cells(tile) == {(10, 20), (11, 21)}
    assert visible_cells(tile) == {(10, 20), (11, 20)}
