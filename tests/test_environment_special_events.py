from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.dungeon_table_roller import SubtableOutcome
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


@pytest.fixture
def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(rules=RulesRepository(packaged, packaged / "_override"), asset_dir=Path())


def _member(
    character_id: str,
    name: str,
    *,
    class_id: str = "warrior",
    gold: int = 0,
    inventory: list[str] | None = None,
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id=class_id,
        class_name=class_id.replace("_", " ").title(),
        level=1,
        xp=0,
        gold=gold,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        inventory=list(inventory or []),
    )


def _session(tile: TileState, party: list[PartyMemberState], *, environment: str) -> SessionState:
    tile.environment = environment
    return SessionState(
        id="sess",
        party_id="party",
        adventure_id="adv",
        adventure_type="random",
        party=party,
        map_state=MapState(current_tile_id=tile.id, tiles=[tile]),
        environment=environment,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _event_tile(key: str) -> TileState:
    return TileState(
        id="event",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Event Room",
        description="A special event.",
        content_key="special_event",
        special_event_key=key,
        special_event_summary=key,
    )


def test_cave_goblin_scout_payment_grants_save_status_and_blocks_surprise(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("cave_goblin_scout")
    hero = _member("h", "Hero", gold=10)
    session = _session(tile, [hero], environment="caverns")

    engine.advance(session, "resolve_environment_event", environment_event_choice="pay", show_rolls=False)

    assert hero.gold == 0
    assert session.caverns_scout_warning
    assert "Scout Warning +1 Saves (caverns)" in hero.statuses
    assert tile.environment_event_resolved

    tile.enemies.append(
        EnemyState(id="m", name="Morlock", category="minions", level=3, life=1, max_life=1, tags=["morlock"])
    )
    tile.initial_enemy_count = 1
    tile.wandering_ambush = True
    engine._begin_combat(session, "Morlocks attack.", show_rolls=False, tile=tile)

    assert not session.party_surprised
    assert any("Cave goblin scout warning" in line for line in session.log)


def test_dwarf_party_gem_adds_claimable_gem_and_rolls_wandering_risk(
    engine: RandomDungeonEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rolls = iter([4, 2])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls))
    tile = _event_tile("dwarf_party_gem")
    session = _session(tile, [_member("d", "Dori", class_id="dwarf")], environment="caverns")

    engine.advance(session, "resolve_environment_event", environment_event_choice="claim", show_rolls=True)

    assert tile.environment_event_resolved
    assert tile.treasure_items == ["Gem (40gp)"]
    assert tile.treasure_claimed is False
    assert not tile.enemies
    assert any("Dwarf gem value: d6 = 4 -> 40gp." in line for line in session.log)
    assert any("Dwarf gem wandering roll: d6 = 2." in line for line in session.log)


def test_morlock_spy_payment_blocks_morlock_surprise(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("morlock_spy")
    hero = _member("h", "Hero", gold=5)
    session = _session(tile, [hero], environment="caverns")

    engine.advance(session, "resolve_environment_event", environment_event_choice="pay", show_rolls=False)

    assert hero.gold == 0
    assert session.caverns_morlock_warning
    assert tile.environment_event_resolved

    tile.enemies.append(
        EnemyState(id="m", name="Morlock", category="minions", level=3, life=1, max_life=1, tags=["morlock"])
    )
    tile.initial_enemy_count = 1
    tile.wandering_ambush = True
    engine._begin_combat(session, "Morlocks attack.", show_rolls=False, tile=tile)

    assert not session.party_surprised
    assert any("Morlock spy warning" in line for line in session.log)


def test_dwarf_miner_limits_gem_purchases(
    engine: RandomDungeonEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    tile = _event_tile("dwarf_miner")
    hero = _member("h", "Hero", gold=100)
    session = _session(tile, [hero], environment="caverns")

    engine._announce_environment_event_choice(session, tile)

    assert session.dwarf_miner_gems_available == 2
    assert any("offers up to 2 gem" in line for line in session.log)

    engine.advance(session, "resolve_environment_event", environment_event_choice="buy_gem", show_rolls=False)
    assert session.dwarf_miner_gems_available == 1
    assert not tile.environment_event_resolved
    assert tile.treasure_items == ["Gem (25gp)"]

    engine.advance(session, "resolve_environment_event", environment_event_choice="buy_gem", show_rolls=False)
    assert session.dwarf_miner_gems_available == 0
    assert tile.environment_event_resolved
    assert hero.gold == 50
    assert len(tile.treasure_items) == 2

    engine.advance(session, "resolve_environment_event", environment_event_choice="buy_gem", show_rolls=False)
    assert any("No pending caverns or fungal special-event choice" in line for line in session.log)


def test_caverns_special_event_trap_uses_cavern_trap_table(
    engine: RandomDungeonEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    tile = _event_tile("trap")
    tile.content_key = "special_event"
    session = _session(tile, [_member("h", "Hero")], environment="caverns")
    monkeypatch.setattr(
        engine.table_roller,
        "roll_special_event",
        lambda **kwargs: SubtableOutcome("trap", "Trap. Roll on the Cavern Trap Table."),
    )
    monkeypatch.setattr(
        engine.table_roller,
        "roll_trap",
        lambda hcl, *, show_rolls, explain_math, environment: type(
            "TrapOutcome",
            (),
            {"trap_key": "rolling_boulder", "trap_level": 4, "summary": "Rolling Boulder trap"},
        )(),
    )

    engine._apply_special_event(session, tile, show_rolls=False, explain_math=False)

    assert tile.trap_key == "rolling_boulder"
    assert tile.trap_level == 4
    assert any("Trap triggered:" in line for line in session.log)


def test_mycelial_warning_ignores_next_fungal_trap(engine: RandomDungeonEngine) -> None:
    tile = TileState(
        id="trap",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Trap Room",
        description="Trap.",
        content_key="trap",
        trap_key="slime_patch",
        trap_level=3,
        objects=["Slime Patch trap"],
    )
    session = _session(tile, [_member("m", "Monk", class_id="mushroom_monk")], environment="fungal_grottoes")
    session.mycelial_warning_ready = True

    engine._prepare_tile_features(session, tile, show_rolls=False, explain_math=False)

    assert tile.trap_resolved
    assert not session.mycelial_warning_ready
    assert not tile.objects
    assert any("Mycelial warning" in line and "Trap" in line for line in session.log)


def test_fungal_cavemen_can_take_rare_mushroom_for_passage(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    tile = _event_tile("fungal_cavemen")
    hero = _member("h", "Hero", inventory=["Brown Cap Delight"])
    session = _session(tile, [hero], environment="fungal_grottoes")
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    engine.advance(session, "resolve_environment_event", environment_event_choice="feed_mushroom", show_rolls=False)

    assert tile.environment_event_resolved
    assert "Brown Cap Delight" not in hero.inventory
    assert session.environment == "caverns"
    assert tile.environment == "fungal_grottoes"
    assert "Secret Passage to caves" in tile.objects
    assert len(session.map_state.tiles) == 2
    destination = next(item for item in session.map_state.tiles if item.id != tile.id)
    assert destination.environment == "caverns"
    assert session.map_state.current_tile_id == destination.id


def test_fungal_cavemen_feed_food_opens_passage(
    engine: RandomDungeonEngine, monkeypatch
) -> None:
    tile = _event_tile("fungal_cavemen")
    hero = _member("h", "Hero", inventory=["Food ration"] * 4)
    session = _session(tile, [hero], environment="fungal_grottoes")
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    engine.advance(session, "resolve_environment_event", environment_event_choice="feed", show_rolls=False)

    assert tile.environment_event_resolved
    assert session.environment == "caverns"
    assert tile.environment == "fungal_grottoes"
    assert len(session.map_state.tiles) == 2
    destination = next(item for item in session.map_state.tiles if item.id != tile.id)
    assert destination.environment == "caverns"
    assert session.map_state.current_tile_id == destination.id


def test_fungal_merchant_sells_equipment_at_twenty_percent_markup(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("fungal_merchant")
    hero = _member("h", "Hero", gold=5)
    session = _session(tile, [hero], environment="fungal_grottoes")

    engine.advance(
        session,
        "resolve_environment_event",
        environment_event_choice="buy_equipment",
        character_id="h",
        item_name="lantern",
        show_rolls=False,
    )

    assert tile.environment_event_resolved
    assert session.fungal_merchant_met
    assert hero.gold == 0
    assert "Lantern" in hero.inventory
    assert any("for 5gp" in line for line in session.log)


def test_fungal_merchant_weapon_service_requires_target_weapon(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("fungal_merchant")
    hero = _member("h", "Hero", gold=50, inventory=["Hand weapon"])
    session = _session(tile, [hero], environment="fungal_grottoes")

    engine.advance(
        session,
        "resolve_environment_event",
        environment_event_choice="buy_equipment",
        character_id="h",
        item_name="silvering_light",
        show_rolls=False,
    )

    assert not tile.environment_event_resolved
    assert any("Choose a weapon" in line for line in session.log)


def test_fungal_merchant_applies_silvering_to_chosen_weapon(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("fungal_merchant")
    hero = _member("h", "Hero", gold=50, inventory=["Hand weapon"])
    session = _session(tile, [hero], environment="fungal_grottoes")

    engine.advance(
        session,
        "resolve_environment_event",
        environment_event_choice="buy_equipment",
        character_id="h",
        item_name="silvering_light",
        target_weapon="Hand weapon",
        show_rolls=False,
    )

    assert tile.environment_event_resolved
    assert any("(silvered)" in item for item in hero.inventory)
    assert hero.gold == 26


def test_halfling_scout_payment_grants_save_status_and_blocks_surprise(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("halfling_scout")
    hero = _member("h", "Hero", gold=10)
    session = _session(tile, [hero], environment="fungal_grottoes")

    engine.advance(session, "resolve_environment_event", environment_event_choice="pay", show_rolls=False)

    assert hero.gold == 0
    assert session.fungal_scout_warning
    assert "Scout Warning +1 Saves (fungal)" in hero.statuses
    assert tile.environment_event_resolved

    tile.enemies.append(
        EnemyState(id="m", name="Sporeling", category="minions", level=3, life=1, max_life=1, tags=["minions"])
    )
    tile.initial_enemy_count = 1
    tile.wandering_ambush = True
    engine._begin_combat(session, "Foes attack.", show_rolls=False, tile=tile)

    assert not session.party_surprised
    assert any("Halfling scout warning" in line for line in session.log)


def test_trap_rare_item_rolls_fungal_trap_and_rare_item(
    engine: RandomDungeonEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    tile = TileState(
        id="event",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Event Room",
        description="A special event.",
        content_key="special_event",
        objects=["Special Event"],
    )
    session = _session(tile, [_member("h", "Hero")], environment="fungal_grottoes")
    monkeypatch.setattr(
        engine.table_roller,
        "roll_special_event",
        lambda **kwargs: SubtableOutcome("trap_rare_item", "Trap then rare item."),
    )
    monkeypatch.setattr(
        engine.table_roller,
        "roll_trap",
        lambda hcl, *, show_rolls, explain_math, environment: type(
            "TrapOutcome",
            (),
            {"trap_key": "slime_patch", "trap_level": 3, "summary": "Slime Patch trap"},
        )(),
    )
    monkeypatch.setattr(
        engine.table_roller,
        "roll_magic_treasure",
        lambda **kwargs: type(
            "TreasureOutcome",
            (),
            {"summary": "Xicthul's Cap", "items": ["Xicthul's Cap"]},
        )(),
    )

    engine._apply_special_event(session, tile, show_rolls=False, explain_math=False)

    assert tile.trap_key == "slime_patch"
    assert tile.trap_level == 3
    assert "Xicthul's Cap" in tile.treasure_items
    assert tile.environment_event_resolved
    assert any("Rare item found" in line for line in session.log)


def test_fungal_merchant_repeat_routes_to_halfling_scout(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("fungal_merchant")
    session = _session(tile, [_member("h", "Hero")], environment="fungal_grottoes")
    session.fungal_merchant_met = True

    engine._announce_environment_event_choice(session, tile)

    assert tile.special_event_key == "halfling_scout"
    assert any("count this as the halfling scout" in line.lower() for line in session.log)


def test_mycelial_warning_choice_stores_ignore_flag(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("mycelial_warning")
    session = _session(tile, [_member("m", "Monk", class_id="mushroom_monk")], environment="fungal_grottoes")

    engine.advance(session, "resolve_environment_event", environment_event_choice="take_warning", show_rolls=False)

    assert tile.environment_event_resolved
    assert session.mycelial_warning_ready
    assert any("Mycelial warning stored" in line for line in session.log)


def test_mycelial_warning_ignores_wandering_monsters(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("wandering_monsters")
    session = _session(tile, [_member("m", "Monk", class_id="mushroom_monk")], environment="fungal_grottoes")
    session.mycelial_warning_ready = True

    engine._spawn_wandering_monsters(session, tile, show_rolls=False)

    assert not session.mycelial_warning_ready
    assert not tile.enemies
    assert any("Wandering Monsters" in line for line in session.log)
