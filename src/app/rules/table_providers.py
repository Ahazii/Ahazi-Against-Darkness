from __future__ import annotations

"""Packaged rule-table providers and their legacy-compatible merge order."""

import json
from pathlib import Path
from typing import Any, Iterable

from ..engine.supplements import LOCKED_CORE_SUPPLEMENT_ID


def _load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _append_ruleset_status(tables: dict[str, Any], value: Any) -> None:
    if not isinstance(value, str):
        return
    base = str(tables.get("ruleset_status") or "").strip()
    tables["ruleset_status"] = f"{base} {value}".strip() if base else value


def _merge_table_file(
    tables: dict[str, Any],
    path: Path,
    *,
    include_open_items: bool = False,
) -> None:
    for key, value in _load_object(path).items():
        if key == "ruleset_status":
            _append_ruleset_status(tables, value)
            continue
        if key == "open_items" and include_open_items and isinstance(value, list):
            existing = list(tables.get("open_items") or [])
            for item in value:
                if item not in existing:
                    existing.append(item)
            tables["open_items"] = existing
            continue
        if key in {"ruleset_status", "validation"} or (key == "open_items" and include_open_items):
            continue
        tables[key] = value


def _book_of_secrets_rows(path: Path) -> list[dict[str, Any]]:
    entries = _load_object(path).get("entries", {})
    if not isinstance(entries, dict):
        return []
    rows: list[dict[str, Any]] = []
    for entry_id in sorted(entries.keys(), key=lambda item: int(item)):
        row = entries[entry_id]
        if not isinstance(row, dict):
            continue
        rows.append({
            "roll": entry_id,
            "name": row.get("name", ""),
            "effect": row.get("effect", ""),
            "summary": row.get("summary", ""),
        })
    return rows


def _apothecary_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for recipe in _load_object(path).get("recipes", []):
        if not isinstance(recipe, dict):
            continue
        rows.append({
            "key": recipe.get("key", ""),
            "name": recipe.get("name", ""),
            "item": recipe.get("item", ""),
            "cost_gp": recipe.get("cost_gp", 0),
            "difficulty": recipe.get("difficulty", 0),
            "duration": recipe.get("duration", ""),
            "summary": recipe.get("summary", ""),
            "ingredients": recipe.get("ingredients", []),
        })
    return rows


def merge_packaged_dungeon_tables(
    packaged_dir: Path,
    active_supplement_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Merge packaged providers in the legacy order, optionally by snapshot.

    `None` retains the existing all-packaged-provider behaviour. The scoped
    form is intentionally unused by live table rollers until each provider
    family has source-backed parity coverage.
    """
    tables = _load_object(packaged_dir / "dungeon_tables.json")
    active_ids = None if active_supplement_ids is None else {
        LOCKED_CORE_SUPPLEMENT_ID,
        *(str(item).strip() for item in active_supplement_ids if str(item).strip()),
    }

    def enabled(supplement_id: str) -> bool:
        return active_ids is None or supplement_id in active_ids

    if enabled("forsaken-depths"):
        _merge_table_file(tables, packaged_dir / "forsaken_depths_tables.json", include_open_items=True)
    if enabled("courtship"):
        _merge_table_file(tables, packaged_dir / "courtship_tables.json")
    if enabled("four-against-the-abyss"):
        _merge_table_file(tables, packaged_dir / "abyss_tables.json")
    if enabled("courtship"):
        book_rows = _book_of_secrets_rows(packaged_dir / "courtship_book_of_secrets.json")
        if book_rows:
            tables["courtship_book_of_secrets_table"] = book_rows
        _merge_table_file(tables, packaged_dir / "courtship_blossoms_tables.json")
        apothecary_rows = _apothecary_rows(packaged_dir / "courtship_apothecary_recipes.json")
        if apothecary_rows:
            tables["courtship_apothecary_recipes_table"] = apothecary_rows
    return tables
