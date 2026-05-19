from __future__ import annotations

from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import ExitState, MapState, PartyMemberState, SessionState, TileState
from pathlib import Path


def test_reciprocal_door_inherits_open_state() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin_exit = ExitState(
        id="origin-door",
        direction="north",
        kind="door",
        door_type="unlocked",
        door_open=True,
        door_result="Unlocked door.",
        destination_tile_id="dest",
    )
    origin = TileState(
        id="origin",
        x=0,
        y=1,
        tile_key="11",
        tile_type="room",
        title="Origin",
        description="Origin",
        exits=[origin_exit],
    )
    reciprocal = ExitState(id="dest-door", direction="south", kind="door")
    destination = TileState(
        id="dest",
        x=0,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Destination",
        description="Destination",
        exits=[reciprocal],
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[PartyMemberState(
            character_id="hero",
            name="Hero",
            class_id="warrior",
            class_name="Warrior",
            level=1,
            xp=0,
            gold=0,
            current_life=3,
            max_life=3,
            attack_bonus=0,
            defense_bonus=0,
            save_bonus=0,
        )],
        map_state=MapState(tiles=[origin, destination], current_tile_id="dest"),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    engine._set_reciprocal_exit(destination, origin, origin_exit)
    assert reciprocal.door_open is True
    assert reciprocal.door_type == "unlocked"

    reciprocal.door_open = False
    engine._inherit_open_door_from_reciprocal(session, destination, reciprocal)
    assert reciprocal.door_open is True
