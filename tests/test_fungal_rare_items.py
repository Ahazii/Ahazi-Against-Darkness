from __future__ import annotations

from pathlib import Path

from app.engine.consumables import mushroom_kind, mushroom_resale_value, use_mushroom
from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.fungal_rare_items import (
    RED_DEATH_DAMAGE_ITEM,
    RED_DEATH_LEVEL_ITEM,
    eat_white_angel_mushroom,
    expire_white_angel_mushrooms,
    resolve_red_death_treasure,
    throw_red_death,
    throw_xicthuls_cap,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _member(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=4,
        max_life=5,
        current_life=5,
        marching_order=1,
        inventory=[],
        statuses=[],
        spells=[],
        learned_expert_skills=[],
        gold=0,
        clues=0,
        xp=0,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def test_red_death_treasure_choice_damage() -> None:
    log: list[str] = []
    summary, gold, items, extra = resolve_red_death_treasure("red_death_damage", log)
    assert gold == 0
    assert items == [RED_DEATH_DAMAGE_ITEM]
    assert "damage" in summary.lower()
    assert extra


def test_red_death_treasure_choice_level() -> None:
    log: list[str] = []
    summary, gold, items, extra = resolve_red_death_treasure("red_death_level", log)
    assert items == [RED_DEATH_LEVEL_ITEM]
    assert "level" in summary.lower()
    assert extra


def test_roller_stages_red_death_choice(monkeypatch) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 3)
    outcome = roller.roll_magic_treasure(
        environment="fungal_grottoes",
        table_name="fungal_grottoes_rare_item_table",
    )
    assert outcome.choice_key == "fungal_red_death"


def test_roller_resolves_red_death_choice() -> None:
    roller = _roller()
    outcome = roller.resolve_environment_treasure_choice("fungal_red_death", "red_death_level")
    assert outcome.items == [RED_DEATH_LEVEL_ITEM]


def test_white_angel_basket_roll(monkeypatch) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.fungal_rare_items.roll_formula", lambda _f: 4)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 5)
    outcome = roller.roll_magic_treasure(
        environment="fungal_grottoes",
        table_name="fungal_grottoes_rare_item_table",
    )
    assert len(outcome.items) == 4
    assert all("White Angel Mushroom" in item for item in outcome.items)


def test_throw_red_death_damage() -> None:
    hero = _member()
    foe = EnemyState(id="f1", name="Brute", category="weird", level=4, life=3, max_life=3)
    log, ok = throw_red_death(hero, foe, RED_DEATH_DAMAGE_ITEM, show_rolls=False)
    assert ok
    assert foe.life == 2
    assert any("automatic damage" in line.lower() for line in log)


def test_throw_red_death_ignored_by_skeleton() -> None:
    hero = _member()
    foe = EnemyState(
        id="f1",
        name="Skeleton",
        category="minions",
        level=3,
        life=1,
        max_life=1,
        tags=["undead"],
    )
    log, ok = throw_red_death(hero, foe, RED_DEATH_DAMAGE_ITEM, show_rolls=False)
    assert ok is False
    assert foe.life == 1
    assert any("unliving" in line.lower() for line in log)


def test_throw_red_death_level_drop() -> None:
    hero = _member()
    foe = EnemyState(id="f1", name="Brute", category="weird", level=4, life=3, max_life=3)
    log, ok = throw_red_death(hero, foe, RED_DEATH_LEVEL_ITEM, show_rolls=False)
    assert ok
    assert foe.level == 3
    assert any("level drops" in line.lower() for line in log)


def test_throw_xicthuls_cap(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.fungal_rare_items.roll_d3", lambda: 2)
    hero = _member(current_life=5)
    foe = EnemyState(id="f1", name="Brute", category="weird", level=4, life=4, max_life=4)
    log, ok = throw_xicthuls_cap(hero, foe, show_rolls=True)
    assert ok
    assert hero.current_life == 4
    assert foe.life == 2
    assert any("d3 chaos damage = 2" in line for line in log)


def test_eat_white_angel_mushroom_heals() -> None:
    hero = _member(current_life=2)
    log, ok = eat_white_angel_mushroom(hero)
    assert ok
    assert hero.current_life == 4
    assert any("heals 2 life" in line.lower() for line in log)


def test_expire_white_angel_at_adventure_end() -> None:
    hero = _member(inventory=["White Angel Mushroom", "White Angel Mushroom"])
    logs = expire_white_angel_mushrooms([hero])
    assert hero.inventory == [
        "White Angel Mushroom (10gp resale)",
        "White Angel Mushroom (10gp resale)",
    ]
    assert logs


def test_white_angel_mushroom_kinds_and_resale() -> None:
    assert mushroom_kind("Red Death (1 damage)") == "red_death"
    assert mushroom_kind("Xicthul's Cap") == "xicthul"
    assert mushroom_kind("White Angel Mushroom") == "white_angel"
    value, _ = mushroom_resale_value("White Angel Mushroom (10gp resale)")
    assert value == 10


def test_use_red_death_in_combat_via_engine() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    eng = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())
    hero = _member(inventory=[RED_DEATH_DAMAGE_ITEM])
    foe = EnemyState(id="f1", name="Brute", category="weird", level=4, life=3, max_life=3)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        enemies=[foe],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        reaction_checked=True,
        reaction_key="fight",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(
        session,
        "use_mushroom",
        character_id=hero.character_id,
        item_name=RED_DEATH_DAMAGE_ITEM,
        foe_id="f1",
        show_rolls=False,
    )
    assert RED_DEATH_DAMAGE_ITEM not in hero.inventory
    assert foe.life == 2


def test_white_angel_exploration_use() -> None:
    hero = _member(inventory=["White Angel Mushroom"], current_life=3)
    log, ok = use_mushroom(hero, "White Angel Mushroom", mode="exploration", show_rolls=False)
    assert ok
    assert hero.current_life == 5
    assert log
