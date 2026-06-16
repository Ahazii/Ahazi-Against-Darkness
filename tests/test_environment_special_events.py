from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.random_dungeon import RandomDungeonEngine
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


def test_fungal_cavemen_can_take_rare_mushroom_for_passage(engine: RandomDungeonEngine) -> None:
    tile = _event_tile("fungal_cavemen")
    hero = _member("h", "Hero", inventory=["Brown Cap Delight"])
    session = _session(tile, [hero], environment="fungal_grottoes")

    engine.advance(session, "resolve_environment_event", environment_event_choice="feed_mushroom", show_rolls=False)

    assert tile.environment_event_resolved
    assert "Brown Cap Delight" not in hero.inventory
    assert session.environment == "caverns"
    assert "Secret Passage to caves" in tile.objects


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
