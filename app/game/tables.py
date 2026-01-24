from __future__ import annotations

import json
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
        raw = json.loads(data_path.read_text(encoding="utf-8"))
        self.vermin = [self._parse(entry) for entry in raw["vermin"]]
        self.minions = [self._parse(entry) for entry in raw["minions"]]
        self.weird = [self._parse(entry) for entry in raw["weird"]]
        self.boss = [self._parse(entry) for entry in raw["boss"]]

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
