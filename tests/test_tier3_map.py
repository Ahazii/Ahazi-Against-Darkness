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
    assert outcome.choice_key == "fungal_rare_or_dungeon_magic"
    resolved = r.resolve_environment_treasure_choice(
        outcome.choice_key,
        "rare_mushroom",
        environment="fungal_grottoes",
    )
    assert any("morel" in entry.lower() for entry in resolved.items + [resolved.summary])


def test_healer_reroll_rerolls_special_event(monkeypatch) -> None:
    r = roller()
    rolls = iter([5, 3])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: next(rolls))
    outcome = r.roll_special_event(healer_met=True, environment="dungeon")
    assert outcome.key == "lady_in_white"


def test_caverns_special_event_table_exists() -> None:
    r = roller()
    row = r.lookup("caverns_special_events_table", 1)
    assert row is not None
    assert row["key"] == "cave_goblin_scout"


def test_secret_passage_switches_environment(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    tile.environment = "dungeon"
    session.environment = "dungeon"
    eng._offer_secret_passage(session, tile, show_rolls=True)
    assert session.pending_secret_passage_tile_id == tile.id
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    eng._choose_secret_passage_environment(
        session,
        "fungal_grottoes",
        show_rolls=True,
        explain_math=False,
    )
    assert session.environment == "fungal_grottoes"
    assert tile.environment == "dungeon"
    assert session.pending_secret_passage_tile_id is None
    assert len(session.map_state.tiles) == 2
    destination = next(item for item in session.map_state.tiles if item.id != tile.id)
    assert destination.environment == "fungal_grottoes"
    assert session.map_state.current_tile_id == destination.id
    passage_exit = next(
        exit_state
        for exit_state in tile.exits
        if "secret passage" in (exit_state.label or "").lower()
    )
    assert passage_exit.destination_tile_id == destination.id
    assert any("fungal grottoes" in entry for entry in session.log)
    assert "Secret Passage" in tile.objects


def test_repair_incomplete_secret_passage(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    tile.content_key = "entrance"
    tile.environment = "caverns"
    tile.objects = ["Entrance", "Secret Passage"]
    session.environment = "caverns"
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    repaired, changed = eng.normalize_session(session)
    assert changed is True
    assert len(repaired.map_state.tiles) == 2
    assert tile.environment == "dungeon"
    assert repaired.map_state.current_tile_id != tile.id
    assert any("Repaired incomplete secret passage" in entry for entry in repaired.log)


def test_secret_passage_return_syncs_environment(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    source = session.map_state.tiles[0]
    source.environment = "dungeon"
    session.environment = "dungeon"
    eng._offer_secret_passage(session, source, show_rolls=False)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    monkeypatch.setattr(RandomDungeonEngine, "_announce_encounter", lambda *args, **kwargs: None)
    eng._choose_secret_passage_environment(
        session,
        "caverns",
        show_rolls=False,
        explain_math=False,
    )
    destination = next(item for item in session.map_state.tiles if item.id != source.id)
    assert session.environment == "caverns"
    return_exit = next(
        exit_state
        for exit_state in destination.exits
        if exit_state.destination_tile_id == source.id
    )
    eng._explore(session, exit_id=return_exit.id, show_rolls=False, explain_math=False)
    assert session.map_state.current_tile_id == source.id
    assert session.environment == "dungeon"


def test_sync_session_environment_from_tile() -> None:
    eng = engine()
    session = base_session()
    source = session.map_state.tiles[0]
    source.environment = "dungeon"
    session.environment = "caverns"
    eng._sync_session_environment_from_tile(session, source)
    assert session.environment == "dungeon"


def test_fungal_roll_5_room_offers_secret_passage_placement(monkeypatch) -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
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
    origin = TileState(
        id="origin",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Origin",
        description="Origin",
        environment="fungal_grottoes",
        exits=[],
    )
    exit_state = ExitState(
        id="north-exit",
        direction="north",
        kind="passage",
        x=0,
        y=0,
        status="open",
    )
    origin.exits.append(exit_state)
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="random",
        adventure_type="random",
        party=[hero],
        map_state=MapState(tiles=[origin], current_tile_id=origin.id),
        environment="fungal_grottoes",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 5)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    monkeypatch.setattr(RandomDungeonEngine, "_roll_generated_tile_key", lambda self: "24")
    eng._explore(session, exit_id=exit_state.id, show_rolls=False, explain_math=False)
    fungal_room = next(tile for tile in session.map_state.tiles if tile.id != origin.id)
    assert fungal_room.tile_type == "room"
    assert session.pending_secret_passage_tile_id == fungal_room.id
    assert "Secret Passage" in fungal_room.objects
    eng._choose_secret_passage_environment(
        session,
        "caverns",
        show_rolls=False,
        explain_math=False,
    )
    assert len(session.map_state.tiles) == 3
    assert origin.environment == "fungal_grottoes"
    destination = next(
        tile for tile in session.map_state.tiles if tile.id not in {origin.id, fungal_room.id}
    )
    assert destination.environment == "caverns"
    assert session.map_state.current_tile_id == destination.id


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
