from __future__ import annotations

from pathlib import Path

from app.engine import random_dungeon
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import ExitState, MapState, PartyMemberState, SessionState, TileState


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
    engine._inherit_connection_from_reciprocal(session, destination, reciprocal)
    assert reciprocal.door_open is True


def test_passage_entry_converts_reciprocal_door_to_open_passage() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin_exit = ExitState(
        id="origin-passage",
        direction="north",
        kind="passage",
        status="open",
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
    entry = ExitState(
        id="dest-south-door",
        direction="south",
        kind="door",
        door_type="locked",
        door_open=False,
        door_result="Locked door.",
    )
    destination = TileState(
        id="dest",
        x=0,
        y=0,
        tile_key="66",
        tile_type="room",
        title="Map Element 66",
        description="Dragon lair",
        exits=[entry],
    )

    engine._set_reciprocal_exit(destination, origin, origin_exit)

    assert entry.kind == "passage"
    assert entry.status == "open"
    assert entry.destination_tile_id == "origin"
    assert entry.door_type is None
    assert entry.door_open is False


def test_persist_open_connection_keeps_passage_return_path() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin_exit = ExitState(
        id="origin-passage",
        direction="north",
        kind="passage",
        status="open",
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
    entry = ExitState(
        id="dest-entry",
        direction="south",
        kind="passage",
        status="open",
        destination_tile_id="origin",
    )
    destination = TileState(
        id="dest",
        x=0,
        y=0,
        tile_key="66",
        tile_type="room",
        title="Destination",
        description="Destination",
        exits=[entry],
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

    engine._persist_open_connection(session, origin, origin_exit)

    assert entry.kind == "passage"
    assert entry.status == "open"
    assert entry.door_type is None


def test_persist_open_connection_syncs_open_door() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin_exit = ExitState(
        id="origin-door",
        direction="north",
        kind="door",
        door_type="unlocked",
        door_open=True,
        door_result="Unlocked door.",
        status="open",
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
    entry = ExitState(
        id="dest-entry",
        direction="south",
        kind="passage",
        status="open",
        destination_tile_id="origin",
    )
    destination = TileState(
        id="dest",
        x=0,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Destination",
        description="Destination",
        exits=[entry],
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

    engine._persist_open_connection(session, origin, origin_exit)

    assert origin_exit.door_open is True
    assert entry.kind == "door"
    assert entry.door_open is True
    assert entry.door_type == "unlocked"


def test_explore_allows_return_through_open_passage_connection(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin_exit = ExitState(
        id="origin-door",
        direction="north",
        kind="door",
        door_type="unlocked",
        door_open=True,
        door_result="Unlocked door.",
        status="open",
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
    entry = ExitState(
        id="dest-entry",
        direction="south",
        kind="door",
        door_type="unlocked",
        door_open=True,
        door_result="Unlocked door.",
        status="open",
        destination_tile_id="origin",
    )
    destination = TileState(
        id="dest",
        x=0,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Destination",
        description="Destination",
        exits=[entry],
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

    engine._explore(session, exit_id="dest-entry")

    assert session.map_state.current_tile_id == "origin"
    assert "Open it before moving through" not in "\n".join(session.log)


def test_entrance_door_stays_open_after_round_trip(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    entrance_door = ExitState(
        id="entrance-east",
        direction="east",
        kind="door",
        door_type="unlocked",
        door_open=True,
        status="open",
        destination_tile_id="inner",
    )
    entrance = TileState(
        id="entrance",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        exits=[entrance_door],
    )
    inner_exit = ExitState(
        id="inner-west",
        direction="west",
        kind="door",
        door_type="unlocked",
        door_open=True,
        status="open",
        destination_tile_id="entrance",
    )
    inner = TileState(
        id="inner",
        x=1,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Inner",
        description="Inner",
        exits=[inner_exit],
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
        map_state=MapState(tiles=[entrance, inner], current_tile_id="inner"),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )

    entrance_door.door_open = False
    inner_exit.door_open = True

    engine._explore(session, exit_id="inner-west")
    assert session.map_state.current_tile_id == "entrance"
    assert entrance_door.door_open is True
    assert "Open it before moving through" not in "\n".join(session.log)


def test_first_explore_from_entrance_opens_chosen_door(monkeypatch) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())
    monkeypatch.setattr(engine, "_roll_generated_tile_key", lambda: "11")
    monkeypatch.setattr(random_dungeon.random, "shuffle", lambda items: None)
    entrance_door = ExitState(id="entrance-north", direction="north", kind="door")
    entrance = TileState(
        id="entrance",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        footprint_width=7,
        footprint_height=3,
        exits=[entrance_door],
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
        map_state=MapState(tiles=[entrance], current_tile_id="entrance"),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )

    engine._explore(session, exit_id="entrance-north")

    assert entrance_door.door_open is True
    assert any("passes through the north entrance" in entry for entry in session.log)
    assert len(session.map_state.tiles) == 2


def test_explore_blocks_closed_door_until_opened() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    closed_door = ExitState(id="north-door", direction="north", kind="door", door_type="unlocked")
    origin = TileState(
        id="origin",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Origin",
        description="Origin",
        exits=[closed_door],
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
        map_state=MapState(tiles=[origin], current_tile_id="origin"),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )

    engine._explore(session, exit_id="north-door")

    assert closed_door.door_open is False
    assert session.map_state.current_tile_id == "origin"
    assert any("Open it before moving through" in entry for entry in session.log)


def test_normalize_session_clears_stale_combat_mode() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    origin = TileState(
        id="origin",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Origin",
        description="Origin",
        enemies=[],
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        reaction_pending=True,
        reaction_checked=False,
        combat_round=0,
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
        map_state=MapState(tiles=[origin], current_tile_id="origin"),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )

    normalized, changed = engine.normalize_session(session)

    assert changed
    assert normalized.mode == "exploration"
    assert not normalized.reaction_pending
    assert not normalized.reaction_checked
