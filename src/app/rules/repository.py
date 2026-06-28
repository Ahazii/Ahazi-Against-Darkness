from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schemas import CharacterClass, IconDefinition, TileDefinition
from ..engine.tile_catalogs import TILE_CATALOG_FILES, TILE_CATALOG_KEYS, TileCatalogId, normalize_catalog_id


VALID_TILE_KEYS = sorted(TILE_CATALOG_KEYS["ee"])


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
        return self._merged_monsters()

    def _merged_monsters(self) -> dict[str, Any]:
        """Merge packaged bestiary with DATA_DIR overrides by table key and monster name."""
        packaged = self._load_packaged("monsters.json")
        fd_path = self.packaged_dir / "fd_monsters.json"
        if fd_path.exists():
            fd_monsters = json.loads(fd_path.read_text(encoding="utf-8"))
            for key, value in fd_monsters.items():
                packaged[key] = value
        courtship_path = self.packaged_dir / "courtship_monsters.json"
        if courtship_path.exists():
            courtship_monsters = json.loads(courtship_path.read_text(encoding="utf-8"))
            for key, value in courtship_monsters.items():
                packaged[key] = value
        override_path = self.override_dir / "monsters.json"
        if not override_path.exists():
            return packaged
        override = json.loads(override_path.read_text(encoding="utf-8"))
        if not isinstance(packaged, dict):
            return override if isinstance(override, dict) else packaged
        if not isinstance(override, dict):
            return packaged
        merged: dict[str, Any] = dict(packaged)
        for key, value in override.items():
            packaged_rows = merged.get(key)
            if isinstance(value, list) and isinstance(packaged_rows, list):
                by_name = {
                    item["name"]: dict(item)
                    for item in packaged_rows
                    if isinstance(item, dict) and item.get("name")
                }
                for item in value:
                    if isinstance(item, dict) and item.get("name"):
                        by_name[item["name"]] = {**by_name.get(item["name"], {}), **item}
                merged[key] = list(by_name.values())
            elif isinstance(value, dict) and isinstance(packaged_rows, dict):
                merged[key] = {**packaged_rows, **value}
            else:
                merged[key] = value
        return merged

    def dungeon_tables(self) -> dict[str, Any]:
        packaged = self._load_packaged("dungeon_tables.json")
        fd_path = self.packaged_dir / "forsaken_depths_tables.json"
        if fd_path.exists():
            fd_tables = json.loads(fd_path.read_text(encoding="utf-8"))
            for key, value in fd_tables.items():
                if key == "open_items" and isinstance(value, list):
                    existing = list(packaged.get("open_items") or [])
                    for item in value:
                        if item not in existing:
                            existing.append(item)
                    packaged["open_items"] = existing
                    continue
                if key == "ruleset_status" and isinstance(value, str):
                    base = str(packaged.get("ruleset_status") or "").strip()
                    packaged["ruleset_status"] = f"{base} {value}".strip() if base else value
                    continue
                if key in {"ruleset_status", "open_items", "validation"}:
                    continue
                packaged[key] = value
        courtship_path = self.packaged_dir / "courtship_tables.json"
        if courtship_path.exists():
            courtship_tables = json.loads(courtship_path.read_text(encoding="utf-8"))
            for key, value in courtship_tables.items():
                if key == "ruleset_status" and isinstance(value, str):
                    base = str(packaged.get("ruleset_status") or "").strip()
                    packaged["ruleset_status"] = f"{base} {value}".strip() if base else value
                    continue
                if key in {"ruleset_status", "validation"}:
                    continue
                packaged[key] = value
        abyss_path = self.packaged_dir / "abyss_tables.json"
        if abyss_path.exists():
            abyss_tables = json.loads(abyss_path.read_text(encoding="utf-8"))
            for key, value in abyss_tables.items():
                if key == "ruleset_status" and isinstance(value, str):
                    base = str(packaged.get("ruleset_status") or "").strip()
                    packaged["ruleset_status"] = f"{base} {value}".strip() if base else value
                    continue
                if key in {"ruleset_status", "validation"}:
                    continue
                packaged[key] = value
        bos_path = self.packaged_dir / "courtship_book_of_secrets.json"
        if bos_path.exists():
            bos_data = json.loads(bos_path.read_text(encoding="utf-8"))
            entries = bos_data.get("entries", {})
            if isinstance(entries, dict):
                rows: list[dict[str, Any]] = []
                for entry_id in sorted(entries.keys(), key=lambda item: int(item)):
                    row = entries[entry_id]
                    if not isinstance(row, dict):
                        continue
                    rows.append(
                        {
                            "roll": entry_id,
                            "name": row.get("name", ""),
                            "effect": row.get("effect", ""),
                            "summary": row.get("summary", ""),
                        }
                    )
                packaged["courtship_book_of_secrets_table"] = rows
        blossoms_path = self.packaged_dir / "courtship_blossoms_tables.json"
        if blossoms_path.exists():
            blossoms = json.loads(blossoms_path.read_text(encoding="utf-8"))
            for key, value in blossoms.items():
                if key in {"ruleset_status", "validation"}:
                    continue
                packaged[key] = value
        apothecary_path = self.packaged_dir / "courtship_apothecary_recipes.json"
        if apothecary_path.exists():
            apothecary = json.loads(apothecary_path.read_text(encoding="utf-8"))
            rows: list[dict[str, Any]] = []
            for recipe in apothecary.get("recipes", []):
                if not isinstance(recipe, dict):
                    continue
                rows.append(
                    {
                        "key": recipe.get("key", ""),
                        "name": recipe.get("name", ""),
                        "item": recipe.get("item", ""),
                        "cost_gp": recipe.get("cost_gp", 0),
                        "difficulty": recipe.get("difficulty", 0),
                        "duration": recipe.get("duration", ""),
                        "summary": recipe.get("summary", ""),
                        "ingredients": recipe.get("ingredients", []),
                    }
                )
            packaged["courtship_apothecary_recipes_table"] = rows
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

    def tiles(self, catalog: str | TileCatalogId = "ee") -> dict[str, TileDefinition]:
        catalog_id = normalize_catalog_id(catalog)
        allowed_keys = TILE_CATALOG_KEYS[catalog_id]
        filename = TILE_CATALOG_FILES[catalog_id]
        packaged_items = [
            item for item in self._load_packaged(filename) if item.get("key") in allowed_keys
        ]
        raw_by_key = {item["key"]: item for item in packaged_items}
        override = self.override_dir / filename
        if override.exists():
            override_items = [
                item for item in json.loads(override.read_text(encoding="utf-8")) if item.get("key") in allowed_keys
            ]
            if catalog_id == "ee" and len(override_items) < len(allowed_keys):
                pass
            else:
                raw_by_key = {item["key"]: item for item in packaged_items}
                for item in override_items:
                    raw_by_key[item["key"]] = item
        return {
            key: TileDefinition.model_validate({**raw_by_key[key], "catalog": catalog_id})
            for key in sorted(allowed_keys)
            if key in raw_by_key
        }

    def save_tiles(self, tiles: list[TileDefinition], catalog: str | TileCatalogId = "ee") -> None:
        catalog_id = normalize_catalog_id(catalog)
        self.override_dir.mkdir(parents=True, exist_ok=True)
        ordered = sorted(tiles, key=lambda tile: tile.key)
        payload = json.dumps([tile.model_dump() for tile in ordered], indent=2)
        (self.override_dir / TILE_CATALOG_FILES[catalog_id]).write_text(payload, encoding="utf-8")

    def expert_skills(self) -> dict[str, Any]:
        return self._load("expert_skills.json")

    def ee_class_tricks(self) -> dict[str, Any]:
        return self._load("ee_class_tricks.json")

    def heroic_skills(self) -> dict[str, Any]:
        return self._load("heroic_skills.json")

    def legendary_skills(self) -> dict[str, Any]:
        return self._load("legendary_skills.json")

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

    def search_reference(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        implementation_status: str | None = None,
    ) -> dict[str, Any]:
        entries = self.rulebook_reference()
        if category:
            normalized = category.strip().lower()
            entries = [entry for entry in entries if str(entry.get("category", "")).lower() == normalized]
        if implementation_status:
            normalized = implementation_status.strip().lower()
            entries = [
                entry
                for entry in entries
                if str(entry.get("implementation_status", "")).lower() == normalized
            ]
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
        return {"query": q, "category": category, "implementation_status": implementation_status, "count": len(entries), "entries": entries}
