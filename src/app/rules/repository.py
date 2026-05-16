from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schemas import CharacterClass, TileDefinition


class RulesRepository:
    def __init__(self, packaged_dir: Path, override_dir: Path) -> None:
        self.packaged_dir = packaged_dir
        self.override_dir = override_dir

    def classes(self) -> list[CharacterClass]:
        return [CharacterClass.model_validate(item) for item in self._load("classes.json")]

    def class_by_id(self, class_id: str) -> CharacterClass | None:
        normalized = class_id.strip().lower()
        return next((profile for profile in self.classes() if profile.id == normalized), None)

    def monsters(self) -> dict[str, list[dict[str, Any]]]:
        return self._load("monsters.json")

    def dungeon_tables(self) -> dict[str, Any]:
        return self._load("dungeon_tables.json")

    def tiles(self) -> dict[str, TileDefinition]:
        return {
            item.key: item
            for item in [TileDefinition.model_validate(raw) for raw in self._load("tiles.json")]
        }

    def save_tiles(self, tiles: list[TileDefinition]) -> None:
        self.override_dir.mkdir(parents=True, exist_ok=True)
        ordered = sorted(tiles, key=lambda tile: tile.key)
        (self.override_dir / "tiles.json").write_text(
            json.dumps([tile.model_dump() for tile in ordered], indent=2),
            encoding="utf-8",
        )

    def _load(self, filename: str) -> Any:
        override = self.override_dir / filename
        path = override if override.exists() else self.packaged_dir / filename
        return json.loads(path.read_text(encoding="utf-8"))
