from __future__ import annotations

from app.engine.experience import (
    DEFAULT_UNLIMITED_MAP_ELEMENT_CAP,
    map_elements_at_cap,
    normalize_unlimited_map_element_cap,
)
from app.schemas import MapState, SessionState, TileState


def _tile(tile_id: str) -> TileState:
    return TileState(
        id=tile_id,
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
    )


def test_normalize_unlimited_map_element_cap() -> None:
    assert normalize_unlimited_map_element_cap(None) == DEFAULT_UNLIMITED_MAP_ELEMENT_CAP
    assert normalize_unlimited_map_element_cap("80") == 80
    assert normalize_unlimited_map_element_cap(0) == 1
    assert normalize_unlimited_map_element_cap(5000) == 999
    assert normalize_unlimited_map_element_cap("abc", default=60) == 60


def test_unlimited_map_cap_reached() -> None:
    cap = 42
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        party=[],
        map_bounds_mode="unlimited",
        unlimited_map_element_cap=cap,
        map_state=MapState(
            tiles=[_tile(f"t{i}") for i in range(cap)],
            current_tile_id="t0",
        ),
        created_at="now",
        updated_at="now",
    )
    assert map_elements_at_cap(session)
