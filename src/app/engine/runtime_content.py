from __future__ import annotations

"""Read-only adapter from legacy runtime data to the Supplement Workbench."""

import ast
import json
from pathlib import Path
import re
from typing import Any

from .states import resolve_state_registry
from .supplements import LOCKED_CORE_SUPPLEMENT_ID, supplement_registry
from .foe_catalog import ABYSS_FOE_TABLE_IDS
from .class_catalog import resolve_class_catalog
from .table_catalog import resolve_table_catalog
from .terrain_registry import resolve_terrain_registry


FOE_PROVIDER_FILES: dict[str, str] = {
    LOCKED_CORE_SUPPLEMENT_ID: "monsters.json",
    "forsaken-depths": "fd_monsters.json",
    "courtship": "courtship_monsters.json",
    "tag": "tag_monsters.json",
}
RUNTIME_MODULE_PATTERNS: dict[str, tuple[str, ...]] = {
    LOCKED_CORE_SUPPLEMENT_ID: ("engine/random_dungeon.py", "engine/combat.py", "engine/dungeon_table_roller.py", "engine/terrain.py", "engine/states.py", "rules/table_providers.py"),
    "four-against-the-abyss": ("engine/abyss_*.py",),
    "forsaken-depths": ("engine/forsaken_depths_*.py", "engine/fd_*.py"),
    "courtship": ("engine/courtship_*.py",),
    "tag": ("engine/tag_*.py",),
}


def _app_dir(root_dir: Path | None) -> Path:
    return root_dir / "src" / "app" if root_dir is not None else Path(__file__).resolve().parents[1]


def _rules_dir(root_dir: Path | None) -> Path:
    return root_dir / "data" / "rules" if root_dir is not None else Path(__file__).resolve().parents[3] / "data" / "rules"


def _provider_id(record: dict[str, Any]) -> str:
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return str(source.get("supplement_id") or "").strip()


def _public_symbols(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_")]


def runtime_modules(root_dir: Path | None, supplement_id: str) -> list[dict[str, Any]]:
    app_dir = _app_dir(root_dir)
    paths: list[Path] = []
    for pattern in RUNTIME_MODULE_PATTERNS.get(supplement_id, ()):
        paths.extend(sorted(app_dir.glob(pattern)))
    seen: set[Path] = set()
    modules: list[dict[str, Any]] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        source = resolved.read_text(encoding="utf-8")
        relative = resolved.relative_to(app_dir).as_posix()
        modules.append({
            "id": re.sub(r"[^a-z0-9]+", "-", relative.lower()).strip("-"),
            "title": path.stem.replace("_", " ").title(),
            "path": f"src/app/{relative}",
            "relative_path": relative,
            "symbols": _public_symbols(source),
            "line_count": len(source.splitlines()),
            "read_only": True,
        })
    return modules


def runtime_module_source(root_dir: Path | None, supplement_id: str, module_id: str) -> dict[str, Any]:
    module = next((item for item in runtime_modules(root_dir, supplement_id) if item["id"] == module_id), None)
    if module is None:
        raise KeyError(module_id)
    path = (_app_dir(root_dir) / str(module["relative_path"])).resolve()
    return {**module, "source": path.read_text(encoding="utf-8")}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _foe_groups(root_dir: Path | None, supplement_id: str, rules: Any) -> list[dict[str, Any]]:
    filename = FOE_PROVIDER_FILES.get(supplement_id)
    payload = _load_json(_rules_dir(root_dir) / filename) if filename else None
    if isinstance(payload, dict):
        return [{"id": key, "title": key.replace("_", " ").title(), "count": len(rows), "rows": rows} for key, rows in payload.items() if isinstance(rows, list)]
    if supplement_id != "four-against-the-abyss":
        return []
    tables = rules.dungeon_tables()
    return [
        {
            "id": table_id,
            "title": table_id.replace("_", " ").replace(" table", "").title(),
            "kind": "encounter_table",
            "count": len(rows),
            "rows": rows,
        }
        for table_id in ABYSS_FOE_TABLE_IDS
        if isinstance((rows := tables.get(table_id)), list)
    ]


def _table_records(root_dir: Path | None, supplement_id: str, rules: Any) -> list[dict[str, Any]]:
    catalog = resolve_table_catalog(root_dir, [supplement_id])
    tables = rules.dungeon_tables()
    records: list[dict[str, Any]] = []
    for definition in catalog.definitions():
        if _provider_id(definition) != supplement_id:
            continue
        table_id = str(definition.get("id") or "")
        value = tables.get(table_id)
        if value is not None:
            records.append({"id": table_id, "kind": definition.get("kind", "rule_table"), "row_count": len(value) if isinstance(value, (list, dict)) else 1, "value": value})
    return records


def _class_records(root_dir: Path | None, supplement_id: str, rules: Any) -> list[dict[str, Any]]:
    catalog = resolve_class_catalog(root_dir, [supplement_id])
    active_ids = set(catalog.class_ids)
    return [item.model_dump() for item in rules.classes() if item.id in active_ids]


def _item_records(supplement_id: str, rules: Any) -> list[dict[str, Any]]:
    if supplement_id != LOCKED_CORE_SUPPLEMENT_ID:
        return []
    return [item for item in rules.equipment_shop().get("items", []) if isinstance(item, dict)]


def _tile_records(supplement_id: str, rules: Any) -> list[dict[str, Any]]:
    catalogs = {LOCKED_CORE_SUPPLEMENT_ID: ("ee",), "forsaken-depths": ("forsaken_depths", "forsaken_depths_rivers")}.get(supplement_id, ())
    return [tile.model_dump() for catalog_id in catalogs for tile in rules.tiles(catalog_id).values()]


def runtime_supplement_content(root_dir: Path | None, data_dir: Path | None, supplement_id: str, rules: Any) -> dict[str, Any]:
    """Return a read-only view of current runtime content for one supplement."""
    manifest = next((item for item in supplement_registry(root_dir, data_dir) if item.get("id") == supplement_id), None)
    if manifest is None:
        raise KeyError(supplement_id)
    states = [item for item in resolve_state_registry([supplement_id]).definitions() if _provider_id(item) == supplement_id]
    terrain = [item for item in resolve_terrain_registry([supplement_id]).definitions() if _provider_id(item) == supplement_id]
    return {
        "read_only": True,
        "manifest": manifest,
        "runtime_modules": runtime_modules(root_dir, supplement_id),
        "content": {
            "states": states,
            "terrain": terrain,
            "tables": _table_records(root_dir, supplement_id, rules),
            "foe_groups": _foe_groups(root_dir, supplement_id, rules),
            "classes": _class_records(root_dir, supplement_id, rules),
            "items": _item_records(supplement_id, rules),
            "tiles": _tile_records(supplement_id, rules),
        },
        "notes": "Read-only adapter over current packaged data and runtime modules. It does not promote PDF review records or alter gameplay.",
    }
