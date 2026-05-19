from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import ExitState, MapState, PartyMemberState, SessionState, TileState


@pytest.fixture
def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(rules=RulesRepository(packaged, packaged / "_override"), asset_dir=Path())


@pytest.fixture
def roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def test_wandering_monsters_table_lookup(roller: DungeonTableRoller) -> None:
    assert roller.lookup("wandering_monsters_table", 1)["enemy_category"] == "vermin"
    assert roller.lookup("wandering_monsters_table", 4)["enemy_category"] == "minions"
    assert roller.lookup("wandering_monsters_table", 5)["enemy_category"] == "weird"
    assert roller.lookup("wandering_monsters_table", 6)["enemy_category"] == "boss"


def test_magic_treasure_table_has_six_entries(roller: DungeonTableRoller) -> None:
    for roll in range(1, 7):
        row = roller.lookup("dungeon_magic_treasure_table", roll)
        assert row is not None
        assert row.get("items")


def test_roll_treasure_six_resolves_magic(roller: DungeonTableRoller, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 6)
    outcome = roller.roll_treasure()
    assert outcome.items
    assert "Magic treasure" not in outcome.items


def test_search_choice_clue(engine: RandomDungeonEngine, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
    session = _session_with_tile(engine)
    engine.advance(session, "search", search_choice="clue")
    tile = session.map_state.tiles[0]
    assert tile.searched
    assert "Clue" in tile.objects
    assert any("1 Clue" in line for line in session.log)


def test_backtrack_wandering_on_one(engine: RandomDungeonEngine, monkeypatch) -> None:
    triggered: list[bool] = []

    def fake_spawn(session, tile, *, show_rolls, special_event=False):
        triggered.append(True)
        session.mode = "combat"
        session.log.append("Wandering Monsters attack!")

    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    monkeypatch.setattr(engine, "_spawn_wandering_monsters", fake_spawn)
    session = _session_with_tile(engine)
    destination = TileState(
        id="dest",
        x=2,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Hall",
        description="A hall.",
        exits=[ExitState(direction="west", kind="passage", status="open", destination_tile_id=session.map_state.tiles[0].id)],
    )
    session.map_state.tiles.append(destination)
    origin = session.map_state.tiles[0]
    origin.exits = [
        ExitState(
            id="east-exit",
            direction="east",
            kind="passage",
            status="open",
            destination_tile_id="dest",
        )
    ]
    engine.advance(session, "explore", exit_id="east-exit")
    assert triggered
    assert session.mode == "combat"
    assert any("Backtrack roll" in line for line in session.log)


def test_special_event_ghost(engine: RandomDungeonEngine, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.content_key = "special_event"
    engine._apply_special_event(session, tile, show_rolls=True, explain_math=False)
    assert any("ghost" in line.lower() for line in session.log)


def _member() -> PartyMemberState:
    return PartyMemberState(
        character_id="a",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
    )


def _session_with_tile(engine: RandomDungeonEngine) -> SessionState:
    tile = TileState(
        id="start",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Start",
        description="Start room.",
    )
    return SessionState(
        id="sess",
        party_id="party",
        adventure_id="adv",
        adventure_type="random",
        party=[_member()],
        map_state=MapState(current_tile_id="start", tiles=[tile]),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
