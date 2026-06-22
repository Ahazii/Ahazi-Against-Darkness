from __future__ import annotations

from app.engine.experience import UNLIMITED_MAP_ELEMENT_CAP, map_elements_at_cap
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


def test_unlimited_map_cap_reached() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        party=[],
        map_bounds_mode="unlimited",
        map_state=MapState(
            tiles=[_tile(f"t{i}") for i in range(UNLIMITED_MAP_ELEMENT_CAP)],
            current_tile_id="t0",
        ),
        created_at="now",
        updated_at="now",
    )
    assert map_elements_at_cap(session)
