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
        merged = self._merged_rules_list("classes.json", key="id")
        return [CharacterClass.model_validate(item) for item in merged]

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

    def equipment_shop(self) -> dict[str, Any]:
        packaged = self._load_packaged("equipment_shop.json")
        override_path = self.override_dir / "equipment_shop.json"
        if not override_path.exists():
            return packaged
        override = json.loads(override_path.read_text(encoding="utf-8"))
        if not isinstance(override, dict):
            return packaged
        merged = dict(packaged)
        for meta_key, value in override.items():
            if meta_key == "items" and isinstance(value, list):
                by_key = {item.get("key"): item for item in packaged.get("items", []) if item.get("key")}
                for item in value:
                    if item.get("key"):
                        by_key[item["key"]] = item
                merged["items"] = list(by_key.values())
            else:
                merged[meta_key] = value
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
        packaged_items = [
            item for item in self._load_packaged("tiles.json") if item.get("key") in VALID_TILE_KEYS
        ]
        raw_by_key = {item["key"]: item for item in packaged_items}
        override = self.override_dir / "tiles.json"
        if override.exists():
            override_items = [
                item
                for item in json.loads(override.read_text(encoding="utf-8"))
                if item.get("key") in VALID_TILE_KEYS
            ]
            # Ignore stale partial exports in the data volume; they used to shadow packaged tiles.
            if len(override_items) >= len(VALID_TILE_KEYS):
                raw_by_key = {item["key"]: item for item in packaged_items}
                for item in override_items:
                    raw_by_key[item["key"]] = item
        return {key: TileDefinition.model_validate(raw_by_key[key]) for key in VALID_TILE_KEYS if key in raw_by_key}

    def save_tiles(self, tiles: list[TileDefinition]) -> None:
        self.override_dir.mkdir(parents=True, exist_ok=True)
        ordered = sorted(tiles, key=lambda tile: tile.key)
        payload = json.dumps([tile.model_dump() for tile in ordered], indent=2)
        (self.override_dir / "tiles.json").write_text(payload, encoding="utf-8")
        (self.packaged_dir / "tiles.json").write_text(payload, encoding="utf-8")

    def _load(self, filename: str) -> Any:
        override = self.override_dir / filename
        path = override if override.exists() else self.packaged_dir / filename
        return json.loads(path.read_text(encoding="utf-8"))

    def _merged_rules_list(self, filename: str, *, key: str) -> list[dict[str, Any]]:
        """Merge packaged rules with DATA_DIR overrides; packaged rows fill gaps after image updates."""
        packaged = self._load_packaged(filename)
        if not isinstance(packaged, list):
            return packaged
        override_path = self.override_dir / filename
        if not override_path.exists():
            return packaged
        override = json.loads(override_path.read_text(encoding="utf-8"))
        if not isinstance(override, list):
            return packaged
        by_key = {item[key]: dict(item) for item in packaged if isinstance(item, dict) and item.get(key)}
        for item in override:
            if isinstance(item, dict) and item.get(key):
                item_id = item[key]
                by_key[item_id] = {**by_key.get(item_id, {}), **item}
        return list(by_key.values())

    def _load_packaged(self, filename: str) -> Any:
        return json.loads((self.packaged_dir / filename).read_text(encoding="utf-8"))

    def rulebook_reference(self) -> list[dict[str, Any]]:
        packaged = self._load_packaged("rulebook_reference.json")
        entries = packaged.get("entries", []) if isinstance(packaged, dict) else []
        override_path = self.override_dir / "rulebook_reference.json"
        if not override_path.exists():
            return entries
        override = json.loads(override_path.read_text(encoding="utf-8"))
        override_entries = override.get("entries", []) if isinstance(override, dict) else []
        by_id = {item["id"]: dict(item) for item in entries if isinstance(item, dict) and item.get("id")}
        for item in override_entries:
            if isinstance(item, dict) and item.get("id"):
                item_id = item["id"]
                by_id[item_id] = {**by_id.get(item_id, {}), **item}
        return list(by_id.values())

    def search_reference(self, *, q: str | None = None, category: str | None = None) -> dict[str, Any]:
        entries = self.rulebook_reference()
        if category:
            normalized = category.strip().lower()
            entries = [entry for entry in entries if str(entry.get("category", "")).lower() == normalized]
        if q:
            query = q.strip().lower()
            if query:

                def score(entry: dict[str, Any]) -> int:
                    title = str(entry.get("title", "")).lower()
                    summary = str(entry.get("summary", "")).lower()
                    body = str(entry.get("body", "")).lower()
                    keywords = " ".join(str(item) for item in entry.get("keywords", [])).lower()
                    haystack = f"{title} {summary} {body} {keywords}"
                    if title == query:
                        return 100
                    if query in title:
                        return 80
                    if any(query == kw.lower() for kw in entry.get("keywords", [])):
                        return 70
                    if query in keywords:
                        return 60
                    if query in summary:
                        return 50
                    if query in body:
                        return 30
                    if query in haystack:
                        return 10
                    return 0

                scored = [(score(entry), entry) for entry in entries]
                entries = [entry for points, entry in scored if points > 0]
                entries.sort(key=lambda entry: score(entry), reverse=True)
        return {"query": q, "category": category, "count": len(entries), "entries": entries}
