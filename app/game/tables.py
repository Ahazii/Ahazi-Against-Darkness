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
                "door_table": [
                    "Magically sealed door (requires spellcasting)",
                    "Iron door (lockpick or destroy with magic)",
                    "Illusionary door (spend clues or illusionist)",
                    "Locked door (HCL+d6)",
                    "Unlocked door",
                    "Trap on door (HCL+d6)",
                    "Lever door (spend clue or gadget)",
                ],
            }
        self.vermin = [self._parse(entry) for entry in raw["vermin"]]
        self.minions = [self._parse(entry) for entry in raw["minions"]]
        self.weird = [self._parse(entry) for entry in raw["weird"]]
        self.boss = [self._parse(entry) for entry in raw["boss"]]
        self.door_table = raw.get("door_table", [])


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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_override(data_dir: Path, filename: str, fallback: Path) -> Path:
    override = data_dir / filename
    return override if override.exists() else fallback


def load_table_data(data_dir: Path) -> dict:
    base_dir = Path(__file__).resolve().parent / "data"
    data_path = _resolve_override(data_dir, "dungeon_tables.json", base_dir / "dungeon_tables.json")
    shapes_path = _resolve_override(data_dir, "tile_shapes.json", base_dir / "tile_shapes.json")
    tiles_table_path = _resolve_override(data_dir, "tile_table.json", base_dir / "tile_table.json")
    return {
        "tables": _load_json(data_path),
        "tile_shapes": _load_json(shapes_path),
        "tile_table": _load_json(tiles_table_path),
    }


def save_table_data(data_dir: Path, payload: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "dungeon_tables.json").write_text(
        json.dumps(payload.get("tables", {}), indent=2),
        encoding="utf-8",
    )
    (data_dir / "tile_shapes.json").write_text(
        json.dumps(payload.get("tile_shapes", []), indent=2),
        encoding="utf-8",
    )
    (data_dir / "tile_table.json").write_text(
        json.dumps(payload.get("tile_table", {}), indent=2),
        encoding="utf-8",
    )

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
