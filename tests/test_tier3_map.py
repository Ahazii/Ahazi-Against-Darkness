from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller, environment_trap_table
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import ExitState, MapState, PartyMemberState, SessionState, TileState


def packaged() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "rules"


def roller() -> DungeonTableRoller:
    return DungeonTableRoller(RulesRepository(packaged(), packaged() / "_override").dungeon_tables())


def engine() -> RandomDungeonEngine:
    return RandomDungeonEngine(RulesRepository(packaged(), packaged() / "_override"), Path())


def base_session(**kwargs) -> SessionState:
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
    )
    defaults = dict(
        id="s",
        party_id="p",
        adventure_id="random",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def test_environment_trap_table_names() -> None:
    assert environment_trap_table("dungeon") == "trap_table"
    assert environment_trap_table("caverns") == "caverns_trap_table"
    assert environment_trap_table("fungal_grottoes") == "fungal_grottoes_trap_table"


def test_caverns_trap_roll_uses_cavern_table(monkeypatch) -> None:
    r = roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 2)
    outcome = r.roll_trap(2, show_rolls=True, explain_math=False, environment="caverns")
    assert "Rockslide" in outcome.summary


def test_fungal_treasure_six_uses_rare_item_table(monkeypatch) -> None:
    r = roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 6)
    outcome = r.roll_treasure(environment="fungal_grottoes", treasure_bonus=1)
    assert any("morel" in entry.lower() for entry in outcome.items + [outcome.summary])
    assert any("choice defaults to the Fungal Grottoes Rare Item Table" in entry for entry in outcome.log)


def test_healer_reroll_becomes_wandering_monsters(monkeypatch) -> None:
    r = roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 5)
    outcome = r.roll_special_event(healer_met=True, environment="dungeon")
    assert outcome.key == "wandering_monsters"


def test_caverns_special_event_table_exists() -> None:
    r = roller()
    row = r.lookup("caverns_special_events_table", 1)
    assert row is not None
    assert row["key"] == "trap"


def test_secret_passage_switches_environment(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    eng._offer_secret_passage(session, tile, show_rolls=True)
    assert session.pending_secret_passage_tile_id == tile.id
    eng._choose_secret_passage_environment(session, "fungal_grottoes", show_rolls=True)
    assert session.environment == "fungal_grottoes"
    assert tile.environment == "fungal_grottoes"
    assert session.pending_secret_passage_tile_id is None
    assert any("fungal grottoes" in entry for entry in session.log)


def test_caverns_enemies_use_environment_table(monkeypatch) -> None:
    eng = engine()
    session = base_session(environment="caverns")
    monkeypatch.setattr("app.engine.random_dungeon.random.choice", lambda items: items[0])
    enemies = eng._roll_enemy(session, "vermin", 2)
    assert enemies[0].name == "Echo Bats"


def test_paper_bounds_block_outside_placement() -> None:
    eng = engine()
    origin = TileState(
        id="origin",
        x=18,
        y=0,
        tile_key="02",
        tile_type="room",
        footprint_width=5,
        footprint_height=3,
        title="Edge",
        description="Edge",
        exits=[ExitState(id="east-exit", direction="east", kind="door", x=4, y=1)],
    )
    session = base_session(
        map_bounds_mode="paper",
        map_state=MapState(width=20, height=28, tiles=[origin], current_tile_id=origin.id),
    )
    cells = eng._candidate_footprint_cells(20, 0, 5, 3)
    assert eng._outside_paper_bounds(session, cells)
    assert eng._placement_blocked(session, 20, 0, 5, 3, None, 0, origin, origin.exits[0])


def test_paper_session_creation() -> None:
    eng = engine()
    session = eng.create_session(
        "id",
        "party",
        [
            PartyMemberState(
                character_id="h",
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
            )
        ],
        map_bounds_mode="paper",
    )
    assert session.map_bounds_mode == "paper"
    assert session.map_state.width == 20
    assert session.map_state.height == 28
    assert any("Paper map mode" in entry for entry in session.log)


def test_slay_all_requires_cleared_tiles() -> None:
    from app.schemas import ActiveQuestState, EnemyState

    eng = engine()
    tile_a = TileState(
        id="a",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="A",
        description="A",
        enemies=[],
    )
    tile_b = TileState(
        id="b",
        x=5,
        y=0,
        tile_key="12",
        tile_type="room",
        title="B",
        description="B",
        enemies=[
            EnemyState(id="g", name="Goblin", category="minions", level=3, life=1, max_life=1),
        ],
    )
    session = base_session(
        final_boss_defeated=True,
        active_quest=ActiveQuestState(tile_id="a", key="slay_all", description="Clear all"),
        map_state=MapState(tiles=[tile_a, tile_b], current_tile_id="a"),
    )
    eng._update_quest_on_combat_end(session, [], show_rolls=False)
    assert session.active_quest is not None
    assert not session.active_quest.completed

    tile_b.enemies = []
    eng._update_quest_on_combat_end(session, [], show_rolls=False)
    assert session.active_quest.completed


def test_slay_all_infinite_map_requires_minimum_area() -> None:
    from app.schemas import ActiveQuestState

    eng = engine()
    tile = TileState(
        id="a",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="A",
        description="A",
        enemies=[],
    )
    session = base_session(
        final_boss_defeated=True,
        active_quest=ActiveQuestState(tile_id="a", key="slay_all", description="Clear all"),
        map_state=MapState(width=19, height=28, tiles=[tile], current_tile_id="a"),
        map_bounds_mode="unlimited",
    )

    eng._update_quest_on_combat_end(session, [], show_rolls=False)
    assert session.active_quest is not None
    assert not session.active_quest.completed

    session.map_state.width = 20
    eng._update_quest_on_combat_end(session, [], show_rolls=False)
    assert session.active_quest.completed
