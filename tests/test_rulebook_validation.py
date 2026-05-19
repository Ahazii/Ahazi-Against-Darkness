from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller, parse_roll_range, resolve_gold_formula
from app.rules.repository import RulesRepository


@pytest.fixture
def tables() -> dict:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override").dungeon_tables()


@pytest.fixture
def roller(tables: dict) -> DungeonTableRoller:
    return DungeonTableRoller(tables)


def test_door_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("door_table", 2)["door_type"] == "sealed"
    assert roller.lookup("door_table", 3)["door_type"] == "iron"
    assert roller.lookup("door_table", 4)["door_type"] == "illusion"
    assert roller.lookup("door_table", 5)["door_type"] == "locked"
    assert roller.lookup("door_table", 10)["door_type"] == "unlocked"
    assert roller.lookup("door_table", 11)["door_type"] == "trap_door"
    assert roller.lookup("door_table", 12)["door_type"] == "lever"


def test_trap_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("trap_table", 1)["trap_key"] == "dart"
    assert roller.lookup("trap_table", 1)["target"] == "random"
    assert roller.lookup("trap_table", 2)["save"] == "poison"
    assert roller.lookup("trap_table", 3)["save"] == "trapdoor"
    assert roller.lookup("trap_table", 6)["damage"] == 2
    assert roller.lookup("trap_table", 6)["shield_applies"] is False


def test_treasure_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("treasure_table", 1)["result"] == "No treasure found."
    assert roller.lookup("treasure_table", 2)["gold"] == "1d6"
    assert roller.lookup("treasure_table", 3)["gold"] == "2d6"
    assert roller.lookup("treasure_table", 4)["gold"] == "2d6*5"
    assert roller.lookup("treasure_table", 5)["gold"] == "3d6*10"
    assert roller.lookup("treasure_table", 6)["magic_table"] == "dungeon_magic_treasure"


def test_magic_treasure_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("dungeon_magic_treasure_table", 1)["items"] == ["Wand of Sleep (3 charges)"]
    assert roller.lookup("dungeon_magic_treasure_table", 5)["items"] == ["Potion of Healing"]
    assert roller.lookup("dungeon_magic_treasure_table", 6)["items"] == ["Fireball Staff (2 charges)"]


def test_wandering_monsters_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup("wandering_monsters_table", 2)["enemy_category"] == "vermin"
    assert roller.lookup("wandering_monsters_table", 6)["enemy_category"] == "boss"


def test_search_table_matches_rulebook(roller: DungeonTableRoller) -> None:
    assert roller.lookup_search(0).effect == "wandering_monsters"
    assert roller.lookup_search(1).effect == "wandering_monsters"
    assert roller.lookup_search(2).effect == "nothing"
    assert roller.lookup_search(5).effect == "found_something"
    assert roller.lookup_search(6).effect == "found_something"


def test_room_content_corridor_roll_4_is_searchable(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(4, "corridor")
    assert outcome is not None
    assert outcome.key == "searchable"


def test_room_content_room_roll_4_is_special_event(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(4, "room")
    assert outcome is not None
    assert outcome.key == "special_event"


def test_room_content_room_roll_9_is_minions(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(9, "room")
    assert outcome is not None
    assert outcome.enemy_category == "minions"


def test_room_content_corridor_roll_12_is_empty(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(12, "corridor")
    assert outcome is not None
    assert outcome.key == "empty"


def test_room_content_room_roll_12_is_dragon_lair(roller: DungeonTableRoller) -> None:
    outcome = roller.lookup_room_content(12, "room")
    assert outcome is not None
    assert outcome.key == "lair"
    assert outcome.enemy_category == "boss"
    assert outcome.enemy_tags == ["dragon"]


def test_roll_enemy_honors_required_tags(monkeypatch) -> None:
    from app.engine.random_dungeon import RandomDungeonEngine

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(rules=RulesRepository(packaged, packaged / "_override"), asset_dir=Path())
    monkeypatch.setattr("app.engine.random_dungeon.random.choice", lambda items: items[0])

    enemies = engine._roll_enemy("boss", 1, required_tags=["dragon"])

    assert len(enemies) == 1
    assert enemies[0].name == "Dragon"
    assert "dragon" in enemies[0].tags


def test_hidden_treasure_formula(monkeypatch) -> None:
    rolls = iter([2, 3])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: next(rolls))
    assert resolve_gold_formula("(HCL+d6)*(HCL+d6)", hcl=2) == 20


def test_parse_roll_range() -> None:
    assert parse_roll_range("5-6") == (5, 6)
    assert parse_roll_range("0-1") == (0, 1)
