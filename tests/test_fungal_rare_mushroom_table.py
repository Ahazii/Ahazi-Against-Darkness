from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.consumables import mushroom_resale_value, mushroom_standard_buy_price
from app.engine.dungeon_table_roller import DungeonTableRoller
from app.rules.repository import RulesRepository


def _roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


@pytest.mark.parametrize(
    ("roll", "item"),
    [
        (1, "Slumber Amanita"),
        (2, "Puffball Smokebomb"),
        (3, "Brown Cap Delight"),
        (4, "Phoenix Mushroom"),
        (5, "Purple Truffle"),
        (6, "Healer's Chanterelle"),
    ],
)
def test_rare_mushroom_table_grants_pdf_items(roll: int, item: str, monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: roll)
    outcome = roller.roll_rare_mushroom_loot()
    assert outcome.items == [item]
    assert item in outcome.summary


def test_rare_mushroom_resale_values_match_pdf() -> None:
    assert mushroom_standard_buy_price("Slumber Amanita") == 10
    assert mushroom_standard_buy_price("Puffball Smokebomb") == 5
    assert mushroom_standard_buy_price("Brown Cap Delight") == 15
    assert mushroom_standard_buy_price("Phoenix Mushroom") == 15
    value, _ = mushroom_resale_value("Slumber Amanita")
    assert value == 10
