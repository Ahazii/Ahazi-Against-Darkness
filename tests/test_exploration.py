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


def test_all_indexed_special_feature_keys_have_engine_resolution(roller: DungeonTableRoller) -> None:
    handled = {"fountain", "blessed_temple", "armory", "cursed_altar", "statue", "puzzle_box"}
    indexed = {
        row["key"]
        for row in roller.tables["dungeon_special_features_table"]
        if isinstance(row, dict) and row.get("key")
    }
    assert indexed == handled


def test_all_indexed_cavern_special_feature_keys_have_engine_resolution(roller: DungeonTableRoller) -> None:
    handled = {"stalactites", "stalagmites", "boulders", "echo", "water_pools"}
    indexed = {
        row["key"]
        for row in roller.tables["caverns_special_features_table"]
        if isinstance(row, dict) and row.get("key")
    }
    assert indexed == handled


def test_all_indexed_special_event_keys_have_engine_resolution(roller: DungeonTableRoller) -> None:
    handled = {
        "ghost",
        "wandering_monsters",
        "trap",
        "trap_rare_item",
        "lady_in_white",
        "healer",
        "alchemist",
        "cavemen_explorers",
        "morlock_spy",
        "cave_goblin_scout",
        "dwarf_miner",
        "dwarf_party_gem",
        "fungal_cavemen",
        "spore_cloud",
        "halfling_scout",
        "fungal_merchant",
        "mycelial_warning",
    }
    for table_name in (
        "dungeon_special_events_table",
        "caverns_special_events_table",
        "fungal_grottoes_special_events_table",
    ):
        indexed = {
            row["key"]
            for row in roller.tables[table_name]
            if isinstance(row, dict) and row.get("key")
        }
        assert indexed <= handled


def test_roll_treasure_six_resolves_magic(roller: DungeonTableRoller, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 6)
    outcome = roller.roll_treasure(treasure_bonus=1)
    assert outcome.items
    assert "Magic treasure" not in outcome.items


def test_dungeon_magic_treasure_six_in_fungal_grottoes_rolls_rare_mushroom(
    roller: DungeonTableRoller,
    monkeypatch,
) -> None:
    rolls = iter([6, 1])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: next(rolls))

    outcome = roller.roll_magic_treasure(
        environment="fungal_grottoes",
        table_name="dungeon_magic_treasure_table",
    )

    assert outcome.items == ["Slumber Amanita"]
    assert any("Rare Mushroom" in line or "rare_mushroom" in line for line in outcome.log)


def test_caverns_treasure_four_rolls_illusionist_prism(roller: DungeonTableRoller, monkeypatch) -> None:
    rolls = iter([4])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: next(rolls))
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_formula", lambda formula: 11)

    outcome = roller.roll_treasure(environment="caverns")

    assert outcome.items == ["Prism of Illusionary Banquet"]
    assert any("Prism spell roll: d12 = 11 -> Illusionary Banquet." in line for line in outcome.log)


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


def test_special_event_logs_summary_line_without_rolls(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.content_key = "special_event"
    monkeypatch.setattr(
        engine.table_roller,
        "roll_special_event",
        lambda **kwargs: SubtableOutcome("healer", "A wandering healer offers healing for 10gp per Life."),
    )

    engine._apply_special_event(session, tile, show_rolls=False, explain_math=False)

    assert "Event: A wandering healer offers healing for 10gp per Life." in session.log
    assert any(line.startswith("Event: A wandering healer is here:") for line in session.log)
    assert tile.healer_available is True


def test_ghost_event_logs_targeted_effect(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    monkeypatch.setattr(
        "app.engine.heroic_skill_effects.resolve_fear_save",
        lambda *args, **kwargs: (False, ["Hero fails fear."]),
    )

    engine._resolve_ghost_event(session, show_rolls=False)

    assert session.party[0].current_life == 4
    assert session.pending_madness_choice is not None
    assert f"Event: {session.party[0].name} fails the ghost fear save." in session.log
    assert any("Madness" in line for line in session.log)


def test_ghost_event_logs_paladin_immunity(engine: RandomDungeonEngine) -> None:
    session = _session_with_tile(engine)
    session.party[0].class_id = "paladin"
    session.party[0].class_name = "Paladin"

    engine._resolve_ghost_event(session, show_rolls=False)

    assert session.party[0].current_life == 4
    assert f"{session.party[0].name} is immune to fear." in session.log
    assert not any("gains 1 Madness from the ghost" in line for line in session.log)


def test_fungal_spore_cloud_event_applies_pdf_poison_save(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    session.environment = "fungal_grottoes"
    session.party[0].current_life = 4
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    engine._resolve_fungal_spore_cloud_event(session, hcl=4, show_rolls=False)

    assert session.party[0].current_life == 2
    assert any("Effect: Hero loses 2 Life to the spore cloud." in line for line in session.log)


def test_repeated_healer_special_event_rerolls(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    session.wandering_healer_met = True
    tile = session.map_state.tiles[0]
    tile.content_key = "special_event"
    rolls = iter([5, 3])

    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: next(rolls))

    engine._apply_special_event(session, tile, show_rolls=False, explain_math=False)

    assert tile.special_event_key == "lady_in_white"
    assert "Event: A Lady in White offers a Quest." in session.log


def test_repeated_alchemist_special_event_routes_to_trap(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    session.wandering_alchemist_met = True
    tile = session.map_state.tiles[0]
    tile.content_key = "special_event"
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 6)

    engine._apply_special_event(session, tile, show_rolls=False, explain_math=False)

    assert tile.special_event_key == "trap"
    assert tile.trap_key
    assert tile.trap_resolved is False
    assert any(line.startswith("Event: The alchemist has already passed; a trap triggers instead.") for line in session.log)
    assert any(line.startswith("Event: Trap triggered:") for line in session.log)


def test_refused_lady_special_event_routes_to_trap(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    session.lady_in_white_refused = True
    tile = session.map_state.tiles[0]
    tile.content_key = "special_event"
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 3)

    engine._apply_special_event(session, tile, show_rolls=False, explain_math=False)

    assert tile.special_event_key == "trap"
    assert tile.trap_key
    assert tile.trap_resolved is False
    assert any(line.startswith("Event: The Lady in White will not return; a trap triggers instead.") for line in session.log)
    assert any(line.startswith("Event: Trap triggered:") for line in session.log)


def test_special_feature_logs_feature_line_without_rolls(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    monkeypatch.setattr(
        engine.table_roller,
        "roll_special_feature",
        lambda environment="dungeon": SubtableOutcome("armory", "Armory: PCs may change weapons within class limits."),
    )

    engine._apply_special_feature(session, tile, show_rolls=False, explain_math=False)

    assert "Feature: Armory: PCs may change weapons within class limits." in session.log
    assert "Event: The armory allows weapon changes within class limits." in session.log
    assert tile.content_key == "armory"


def test_statue_feature_waits_for_player_choice(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    monkeypatch.setattr(
        engine.table_roller,
        "roll_special_feature",
        lambda environment="dungeon": SubtableOutcome("statue", "Statue: leave alone or touch (d6: 1-3 living statue, 4-6 breaks for gold)."),
    )

    engine._apply_special_feature(session, tile, show_rolls=False, explain_math=False)

    assert tile.special_event_key == "statue"
    assert tile.resolved is False
    assert not tile.enemies
    assert "Event: Statue feature awaits your choice: leave it alone or touch it." in session.log


def test_statue_feature_can_be_left_alone(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.content_key = "special_feature"
    tile.special_event_key = "statue"

    engine.advance(session, "resolve_special_feature", special_feature_choice="leave_statue", show_rolls=False)

    assert tile.resolved is True
    assert not tile.enemies
    assert "Event: The party leaves the statue alone." in session.log


def test_touching_statue_can_animate_it(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.content_key = "special_feature"
    tile.special_event_key = "statue"
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    engine.advance(session, "resolve_special_feature", special_feature_choice="touch_statue", show_rolls=False)

    assert tile.resolved is True
    assert session.mode == "combat"
    assert any(enemy.name == "Living Statue" for enemy in tile.enemies)


def test_puzzle_box_feature_failed_attempt_stays_pending(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.content_key = "special_feature"
    tile.special_event_key = "puzzle_box"
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    engine.advance(session, "resolve_special_feature", special_feature_choice="attempt_puzzle_box", show_rolls=False)

    assert tile.resolved is False
    assert session.party[0].current_life == 3
    assert f"Effect: {session.party[0].name} takes 1 damage from the puzzle box." in session.log


def test_puzzle_box_feature_can_be_left_alone(engine: RandomDungeonEngine) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.content_key = "special_feature"
    tile.special_event_key = "puzzle_box"

    engine.advance(session, "resolve_special_feature", special_feature_choice="leave_puzzle_box", show_rolls=False)

    assert tile.resolved is True
    assert tile.treasure_summary is None
    assert "Event: The party leaves the puzzle box alone." in session.log


def test_cursed_altar_logs_targeted_effect_for_summary(engine: RandomDungeonEngine, monkeypatch) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    monkeypatch.setattr(
        engine.table_roller,
        "roll_special_feature",
        lambda environment="dungeon": SubtableOutcome("cursed_altar", "Cursed Altar: a random PC is cursed (-1 Defense)."),
    )
    monkeypatch.setattr("app.engine.random_dungeon.random.choice", lambda living: living[0])

    engine._apply_special_feature(session, tile, show_rolls=False, explain_math=False)

    assert session.cursed_character_id == session.party[0].character_id
    assert any(
        line == f"Effect: Cursed Altar curses {session.party[0].name} (-1 Defense until broken)."
        for line in session.log
    )


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
    assert tile.treasure_items == ["Scroll of Fireball"]
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
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
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
    assert tile.treasure_items == ["Scroll of Fireball"]
    engine._resolve_trap(session, show_rolls=False, explain_math=False)
    assert tile.trap_resolved
    assert any("Claim Treasure" in line for line in session.log)


def test_back_rank_rogue_does_not_disarm_trap_before_trigger(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda *args, **kwargs: (99, [99]))
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
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


def test_rolling_boulder_requires_pdf_choices_and_blocks_selected_opening(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.trap_key = "rolling_boulder"
    tile.trap_level = 4
    tile.objects = ["Trap"]
    tile.exits = [
        ExitState(id="north", direction="north", kind="passage", status="open"),
        ExitState(id="south", direction="south", kind="passage", status="open"),
    ]
    session.party = [
        _member(),
        _member().model_copy(
            update={
                "character_id": "b",
                "name": "Rear",
                "marching_order": 2,
            }
        ),
    ]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    engine.advance(session, "resolve_trap", show_rolls=False, explain_math=False)

    assert tile.trap_resolved is False
    assert any("choose whether it comes from the front or back" in line for line in session.log)

    engine.advance(
        session,
        "resolve_trap",
        show_rolls=False,
        explain_math=False,
        trap_boulder_origin="back",
        trap_boulder_block_exit_id="south",
    )

    assert tile.trap_resolved is True
    assert tile.exits[0].status == "open"
    assert tile.exits[1].status == "blocked"
    assert session.party[0].current_life == 4
    assert session.party[1].current_life == 2
    assert any("blocks the south opening" in line for line in session.log)


def test_spore_cloud_trap_runs_pdf_wandering_monster_follow_up(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.trap_key = "spore_cloud"
    tile.trap_level = 4
    tile.objects = ["Trap"]
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    rolls = iter([(1, [1]), (6, [6])])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: next(rolls))
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    spawned: list[str] = []

    def fake_spawn(_session, spawn_tile, **kwargs):
        spawned.append(spawn_tile.id)

    monkeypatch.setattr(engine, "_spawn_wandering_monsters", fake_spawn)

    engine.advance(session, "resolve_trap", show_rolls=True, explain_math=False)

    assert spawned == ["start"]
    assert tile.trap_resolved is True
    assert any("Spore Cloud wandering-monster roll: d6 = 1" in line for line in session.log)


def test_slime_patch_trap_runs_pdf_wandering_monster_follow_up(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.trap_key = "slime_patch"
    tile.trap_level = 4
    tile.objects = ["Trap"]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    spawned: list[str] = []

    def fake_spawn(_session, spawn_tile, **kwargs):
        spawned.append(spawn_tile.id)

    monkeypatch.setattr(engine, "_spawn_wandering_monsters", fake_spawn)

    engine.advance(session, "resolve_trap", show_rolls=True, explain_math=False)

    assert spawned == ["start"]
    assert "Fallen prone (slime patch)" in session.party[0].statuses
    assert any("Slime Patch wandering-monster roll: d6 = 1" in line for line in session.log)


def test_shrieking_mushroom_spawns_when_pdf_chance_calls_wanderers(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.trap_key = "shrieking_mushroom"
    tile.trap_level = 4
    tile.objects = ["Trap"]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    spawned: list[str] = []

    def fake_spawn(_session, spawn_tile, **kwargs):
        spawned.append(spawn_tile.id)

    monkeypatch.setattr(engine, "_spawn_wandering_monsters", fake_spawn)

    engine.advance(session, "resolve_trap", show_rolls=True, explain_math=False)

    assert spawned == ["start"]
    assert any("The shrieking mushroom calls Wandering Monsters." in line for line in session.log)


def test_hidden_pit_exposes_one_clue_secret_passage_follow_up(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.trap_key = "hidden_pit"
    tile.trap_level = 4
    tile.objects = ["Trap"]
    session.party[0].clues = 1
    session.clues_found = 1
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)

    engine.advance(session, "resolve_trap", show_rolls=False, explain_math=False)

    assert tile.trap_resolved is True
    assert tile.hidden_pit_secret_passage_available is True
    assert any("spend 1 held Clue" in line for line in session.log)

    engine.advance(session, "use_hidden_pit_clue", show_rolls=False, explain_math=False)
    engine.advance(
        session,
        "choose_secret_passage_environment",
        secret_passage_environment="caverns",
        show_rolls=False,
        explain_math=False,
    )

    assert tile.hidden_pit_secret_passage_available is False
    assert session.party[0].clues == 0
    assert session.clues_found == 0
    assert "Secret Passage" in tile.objects
    assert session.environment == "caverns"
    assert session.pending_secret_passage_tile_id is None
    assert any("spends 1 Clue at the bottom of the hidden pit" in line for line in session.log)


def test_hidden_pit_secret_passage_follow_up_requires_held_clue(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    session = _session_with_tile(engine)
    tile = session.map_state.tiles[0]
    tile.trap_key = "hidden_pit"
    tile.trap_level = 4
    tile.objects = ["Trap"]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    engine.advance(session, "resolve_trap", show_rolls=False, explain_math=False)
    engine.advance(session, "use_hidden_pit_clue", show_rolls=False, explain_math=False)

    assert tile.hidden_pit_secret_passage_available is True
    assert "Secret Passage" not in tile.objects
    assert any("requires 1 held Clue" in line for line in session.log)
