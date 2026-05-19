from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schemas import CharacterClass, IconDefinition, TileDefinition


VALID_TILE_KEYS = [f"0{die}" for die in range(1, 7)] + [f"{tens}{ones}" for tens in range(1, 7) for ones in range(1, 7)]


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
        packaged = self._load_packaged("dungeon_tables.json")
        override_path = self.override_dir / "dungeon_tables.json"
        if not override_path.exists():
            return packaged
        override = json.loads(override_path.read_text(encoding="utf-8"))
        merged = dict(packaged)
        for meta_key in ("ruleset_status", "open_items", "validation"):
            if meta_key in override:
                merged[meta_key] = override[meta_key]
        return merged

    def icons(self) -> list[IconDefinition]:
        return [IconDefinition.model_validate(item) for item in self._load("icons.json")]

    def save_icons(self, icons: list[IconDefinition]) -> None:
        self.override_dir.mkdir(parents=True, exist_ok=True)
        ordered = sorted(icons, key=lambda icon: icon.id)
        (self.override_dir / "icons.json").write_text(
            json.dumps([icon.model_dump() for icon in ordered], indent=2),
            encoding="utf-8",
        )

    def tiles(self) -> dict[str, TileDefinition]:
        raw_by_key = {item["key"]: item for item in self._load_packaged("tiles.json") if item.get("key") in VALID_TILE_KEYS}
        override = self.override_dir / "tiles.json"
        if override.exists():
            for item in json.loads(override.read_text(encoding="utf-8")):
                if item.get("key") in VALID_TILE_KEYS:
                    raw_by_key[item["key"]] = item
        return {key: TileDefinition.model_validate(raw_by_key[key]) for key in VALID_TILE_KEYS if key in raw_by_key}

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

    def _load_packaged(self, filename: str) -> Any:
        return json.loads((self.packaged_dir / filename).read_text(encoding="utf-8"))
