from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, ExitState, MapState, PartyMemberState, SessionState, TileState


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


def test_hidden_treasure_alarm_defers_claim_until_combat_ends(engine: RandomDungeonEngine, monkeypatch) -> None:
    from app.engine.combat import CombatRound
    from app.engine.dungeon_table_roller import TreasureOutcome

    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    treasure = TreasureOutcome(
        "Hidden treasure worth 10gp.",
        10,
        [],
        ["Hidden treasure: (10gp before complications).", "An alarm goes off, attracting Wandering Monsters!"],
        complication_effect="alarm",
    )
    monkeypatch.setattr(engine.table_roller, "roll_hidden_treasure", lambda hcl: treasure)

    def spawn_alarm_combat(session, tile, **kwargs):
        tile.enemies.append(
            EnemyState(id="wander", name="Rat", category="vermin", level=1, life=1, max_life=1, attacks=1)
        )
        engine._begin_combat(session, "Wandering Monsters attack!")

    monkeypatch.setattr(engine, "_spawn_wandering_monsters", spawn_alarm_combat)

    engine._grant_hidden_treasure(session, tile, show_rolls=True, explain_math=False)

    assert tile.hidden_treasure_alarm_pending is True
    assert tile.treasure_gold == 10
    assert session.mode == "combat"
    assert not any("can be claimed here" in line for line in session.log)
    assert any("alarm must be answered" in line.lower() for line in session.log)

    defeated = [enemy.model_copy(deep=True) for enemy in tile.enemies]
    for enemy in defeated:
        enemy.life = 0
    engine._apply_combat_result(
        session,
        tile,
        CombatRound(party=session.party, enemies=defeated, log=[], combat_over=True, morale_failed=True),
        show_rolls=False,
    )

    assert session.mode == "exploration"
    assert tile.hidden_treasure_alarm_pending is False
    assert any("10gp" in line and "Claim Treasure" in line for line in session.log)


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


def test_treasure_room_seeds_claimable_loot_on_entry(engine: RandomDungeonEngine, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 4)
    session = _session_with_tile(engine)
    tile = TileState(
        id="treasure-room",
        x=1,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Treasure Room",
        description="There is treasure here.",
        content_key="treasure",
        objects=["Treasure"],
    )
    engine._seed_tile_features(tile, 1, show_rolls=True, session=session)
    assert tile.treasure_gold > 0
    assert "Treasure" in tile.objects
    assert any("Treasure roll: d6 = 4." in line for line in session.log)
    assert "Treasure is available to claim." in session.log


def test_treasure_room_empty_roll_clears_marker(engine: RandomDungeonEngine, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    session = _session_with_tile(engine)
    tile = TileState(
        id="empty-treasure",
        x=1,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Empty Hoard",
        description="There is treasure here.",
        content_key="treasure",
        objects=["Treasure"],
    )
    engine._seed_tile_features(tile, 1, show_rolls=True, session=session)
    assert tile.treasure_gold == 0
    assert tile.treasure_items == []
    assert "Treasure" not in tile.objects
    assert any("No treasure found." in line for line in session.log)
