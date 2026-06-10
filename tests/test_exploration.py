from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller, SubtableOutcome
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
    engine.advance(session, "search")
    tile = session.map_state.tiles[0]
    assert tile.searched
    assert session.pending_search_reward_tile_id == tile.id
    assert "Clue" not in tile.objects

    engine.advance(session, "search", character_id="a", search_choice="clue")

    assert session.pending_search_reward_tile_id is None
    assert "Clue" in tile.objects
    assert session.party[0].clues == 1
    assert session.clues_found == 1
    assert any("1 Clue" in line for line in session.log)


def test_search_reward_choice_cannot_precede_roll(engine: RandomDungeonEngine) -> None:
    session = _session_with_tile(engine)
    engine.advance(session, "search", search_choice="clue")
    tile = session.map_state.tiles[0]
    assert not tile.searched
    assert session.clues_found == 0
    assert any("Roll Search first" in line for line in session.log)


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


def test_special_event_wandering_monsters_is_remembered(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.content_key = "special_event"
    monkeypatch.setattr(
        engine.table_roller,
        "roll_special_event",
        lambda **kwargs: SubtableOutcome("wandering_monsters", "Wandering Monsters attack!"),
    )

    def fake_spawn(session, tile, *, show_rolls, special_event=False):
        tile.initial_enemy_count = 1
        tile.enemies.append(
            EnemyState(id="wander", name="Rat", category="vermin", level=1, life=1, max_life=1, attacks=1)
        )
        session.mode = "combat"

    monkeypatch.setattr(engine, "_spawn_wandering_monsters", fake_spawn)

    engine._apply_special_event(session, tile, show_rolls=True, explain_math=False)

    assert tile.special_event_key == "wandering_monsters"
    assert tile.special_event_summary == "Wandering Monsters attack!"
    assert tile.enemies


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


def test_hidden_treasure_after_claimed_room_treasure_becomes_claimable(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    from app.engine.combat import CombatRound
    from app.engine.dungeon_table_roller import TreasureOutcome

    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.treasure_summary = "Ring of Teleportation (1 use)."
    tile.treasure_claimed = True

    treasure = TreasureOutcome(
        "Hidden treasure worth 50gp.",
        50,
        [],
        ["Hidden treasure: (50gp before complications).", "An alarm goes off, attracting Wandering Monsters!"],
        complication_effect="alarm",
    )
    monkeypatch.setattr(engine.table_roller, "roll_hidden_treasure", lambda hcl: treasure)

    def spawn_alarm_combat(session, tile, **kwargs):
        tile.enemies.append(
            EnemyState(id="wander", name="Centipedes", category="vermin", level=4, life=1, max_life=1, attacks=1)
        )
        engine._begin_combat(session, "Wandering Monsters attack!")

    monkeypatch.setattr(engine, "_spawn_wandering_monsters", spawn_alarm_combat)

    engine._grant_hidden_treasure(session, tile, show_rolls=True, explain_math=False)

    assert tile.treasure_claimed is False
    assert tile.hidden_treasure_alarm_pending is True

    defeated = [enemy.model_copy(deep=True) for enemy in tile.enemies]
    for enemy in defeated:
        enemy.life = 0
    engine._apply_combat_result(
        session,
        tile,
        CombatRound(party=session.party, enemies=defeated, log=[], combat_over=True, morale_failed=False),
        show_rolls=False,
    )

    assert tile.treasure_claimed is False
    assert tile.hidden_treasure_alarm_pending is False
    assert tile.treasure_gold == 50
    assert any("50gp" in line and "Claim Treasure" in line for line in session.log)


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


def test_backtrack_wandering_starts_combat_on_destination_tile(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    def spawn_vermin(_session, category, hcl):
        return [
            EnemyState(
                id="scorpion-1",
                name="Scorpions",
                category="vermin",
                level=4,
                life=1,
                max_life=1,
                attacks=1,
            )
        ]

    monkeypatch.setattr(engine, "_roll_wandering_enemies", spawn_vermin)
    session = _session_with_tile(engine)
    destination = TileState(
        id="dest",
        x=2,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Map Element 14",
        description="A hall.",
        exits=[
            ExitState(
                direction="west",
                kind="passage",
                status="open",
                destination_tile_id=session.map_state.tiles[0].id,
            )
        ],
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
    assert session.mode == "combat"
    assert session.map_state.current_tile_id == "dest"
    assert any(enemy.life > 0 for enemy in destination.enemies)
    assert not any("No foes remain to fight" in line for line in session.log)
    assert any("Wandering foes" in line for line in session.log)


def test_normalize_session_starts_orphaned_encounter(engine: RandomDungeonEngine) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(id="rat", name="Rat", category="vermin", level=1, life=1, max_life=1, attacks=1)
    ]
    session, _changed = engine.normalize_session(session)
    assert session.mode == "combat"
    assert session.reaction_pending
    assert any(enemy.life > 0 for enemy in tile.enemies)
    assert any("Encounter resumes" in line for line in session.log)


def test_entering_tile_with_foes_starts_encounter(engine: RandomDungeonEngine, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
    session = _session_with_tile(engine)
    origin = session.map_state.tiles[0]
    destination = TileState(
        id="foe-room",
        x=2,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Guard Room",
        description="A guarded room.",
        enemies=[
            EnemyState(id="rat", name="Rat", category="vermin", level=1, life=1, max_life=1, attacks=1)
        ],
        exits=[
            ExitState(
                direction="west",
                kind="passage",
                status="open",
                destination_tile_id=origin.id,
            )
        ],
    )
    session.map_state.tiles.append(destination)
    origin.exits = [
        ExitState(
            id="east-exit",
            direction="east",
            kind="passage",
            status="open",
            destination_tile_id=destination.id,
        )
    ]

    engine.advance(session, "explore", exit_id="east-exit", show_rolls=False)

    assert session.map_state.current_tile_id == "foe-room"
    assert session.mode == "combat"
    assert session.reaction_pending
    entry_exit = next(exit_state for exit_state in destination.exits if exit_state.destination_tile_id == origin.id)
    assert session.current_tile_entry_exit_id == entry_exit.id
    assert entry_exit.direction == "west"
    assert any("Encounter begins" in line for line in session.log)


def test_start_combat_begins_fight(engine: RandomDungeonEngine) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(id="rat", name="Rat", category="vermin", level=1, life=1, max_life=1, attacks=1)
    ]
    engine.advance(session, "start_combat", show_rolls=False)
    assert session.mode == "combat"
    assert session.reaction_pending
    assert any("Combat begins" in line for line in session.log)


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
    assert any("Treasure roll" in line and "d6 = 4" in line for line in session.log)
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
    assert tile.description == "No treasure found."
    assert tile.content_key == "empty"
    assert any("No treasure found." in line for line in session.log)


def test_trap_treasure_empty_hoard_message_after_resolve(engine: RandomDungeonEngine, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    session = _session_with_tile(engine)
    tile = TileState(
        id="start",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Trapped Empty Chest",
        description="Treasure is protected by a trap.",
        content_key="trap_treasure",
        objects=["Trap", "Treasure"],
    )
    session.map_state.tiles = [tile]
    engine._seed_tile_features(tile, 1, show_rolls=True, session=session)
    assert tile.trap_key
    assert tile.treasure_gold == 0
    assert "Treasure" not in tile.objects
    engine._resolve_trap(session, show_rolls=False, explain_math=False)
    assert tile.trap_resolved
    assert any("Trap cleared" in line and "No treasure found" in line for line in session.log)


def test_rogue_disarm_trap_treasure_announces_claim(engine: RandomDungeonEngine, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 4)
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda level: (4, [4]))
    session = _session_with_tile(engine)
    session.party[0].class_id = "rogue"
    session.party[0].class_name = "Rogue"
    tile = TileState(
        id="start",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Trapped Hoard",
        description="Treasure is protected by a trap.",
        content_key="trap_treasure",
        objects=["Trap", "Treasure"],
    )
    session.map_state.tiles = [tile]
    engine._seed_tile_features(tile, 1, show_rolls=True, session=session)
    assert tile.treasure_gold > 0
    engine._resolve_trap(session, show_rolls=False, explain_math=False)
    assert tile.trap_resolved
    assert any("Claim Treasure" in line for line in session.log)


def test_back_rank_rogue_does_not_disarm_trap_before_trigger(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda level: (99, [99]))
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda level: (1, [1]))
    session = _session_with_tile(engine)
    warrior = session.party[0]
    warrior.marching_order = 1
    rogue = _member().model_copy(
        update={
            "character_id": "rogue",
            "name": "Back Rogue",
            "class_id": "rogue",
            "class_name": "Rogue",
            "marching_order": 3,
        }
    )
    session.party.append(rogue)
    tile = session.map_state.tiles[0]
    tile.trap_key = "trapdoor"
    tile.trap_level = 99
    tile.objects = ["Trap"]

    engine._resolve_trap(session, show_rolls=False, explain_math=False)

    assert tile.trap_resolved is True
    assert not any("rogue disarms" in line.lower() for line in session.log)
    assert warrior.current_life < warrior.max_life
