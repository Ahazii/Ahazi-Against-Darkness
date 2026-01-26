from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .dice import roll_formula
from .formulas import eval_formula


@dataclass(frozen=True)
class FoeTemplate:
    name: str
    level_formula: str
    count_formula: str
    life: int
    attacks: int


@dataclass(frozen=True)
class FoeInstance:
    name: str
    level: int
    count: int
    life: int
    attacks: int


class DungeonTables:
    def __init__(self) -> None:
        data_path = Path(__file__).resolve().parent / "data" / "dungeon_tables.json"
        try:
            raw = json.loads(data_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logging.warning("Dungeon table data missing at %s, using defaults.", data_path)
            raw = {
                "vermin": [
                    {
                        "name": "Rats",
                        "level_formula": "HCL",
                        "count_formula": "2d6",
                        "life": 1,
                        "attacks": 1,
                    }
                ],
                "minions": [
                    {
                        "name": "Goblins",
                        "level_formula": "HCL+2",
                        "count_formula": "d6+3",
                        "life": 1,
                        "attacks": 1,
                    }
                ],
                "weird": [
                    {
                        "name": "Giant Spider",
                        "level_formula": "HCL+4",
                        "count_formula": "1",
                        "life": 3,
                        "attacks": 2,
                    }
                ],
                "boss": [
                    {
                        "name": "Ogre",
                        "level_formula": "HCL+4",
                        "count_formula": "1",
                        "life": 6,
                        "attacks": 1,
                    }
                ],
            }
        self.vermin = [self._parse(entry) for entry in raw["vermin"]]
        self.minions = [self._parse(entry) for entry in raw["minions"]]
        self.weird = [self._parse(entry) for entry in raw["weird"]]
        self.boss = [self._parse(entry) for entry in raw["boss"]]


IMPLEMENTED_TABLES = [
    "Tile Content Table (2d6)",
    "Search Table (d6)",
    "Wandering Monsters Table (d6)",
    "Door Table (2d6)",
    "Dungeon Vermin Table (sample subset)",
    "Dungeon Minions Table (sample subset)",
    "Dungeon Weird Monsters Table (sample subset)",
    "Dungeon Boss Monsters Table (sample subset)",
]


def list_implemented_tables() -> list[str]:
    return IMPLEMENTED_TABLES

    def _parse(self, entry: dict) -> FoeTemplate:
        return FoeTemplate(
            name=entry["name"],
            level_formula=entry["level_formula"],
            count_formula=entry["count_formula"],
            life=entry["life"],
            attacks=entry["attacks"],
        )

    def roll_foe(self, table_name: str, hcl: int) -> FoeInstance:
        table = getattr(self, table_name)
        template = table[roll_formula("d6") - 1]
        level = eval_formula(template.level_formula.replace("HCL", str(hcl)), {"HCL": hcl})
        count = roll_formula(template.count_formula)
        return FoeInstance(
            name=template.name,
            level=max(1, level),
            count=max(1, count),
            life=template.life,
            attacks=template.attacks,
        )
