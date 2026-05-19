from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller, parse_roll_range, resolve_gold_formula
from app.rules.repository import RulesRepository


@pytest.fixture
def roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def test_parse_roll_range() -> None:
    assert parse_roll_range("5-6") == (5, 6)
    assert parse_roll_range("12") == (12, 12)


def test_door_table_lookup(roller: DungeonTableRoller) -> None:
    row = roller.lookup("door_table", 11)
    assert row is not None
    assert row["door_type"] == "trap_door"


def test_trap_table_lookup_by_key(roller: DungeonTableRoller) -> None:
    row = roller.lookup_trap("falling_stone")
    assert row is not None
    assert row["damage"] == 2
    assert row["target"] == "rear"


def test_search_table_lookup(roller: DungeonTableRoller) -> None:
    assert roller.lookup_search(6).effect == "found_something"
    assert roller.lookup_search(2).effect == "nothing"
