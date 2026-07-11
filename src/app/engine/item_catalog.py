from __future__ import annotations

"""Supplement-scoped catalogue of structured equipment and item rewards."""

import json
from pathlib import Path
import re
from typing import Any

from .supplement_content_catalog import (
    ResolvedSupplementContentCatalog,
    packaged_rules_dir,
    resolve_supplement_content_catalog,
)
from .supplements import LOCKED_CORE_SUPPLEMENT_ID


ITEM_CATALOG_VERSION = 1
TABLE_ITEM_SOURCES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "four-against-the-abyss",
        "abyss_tables.json",
        ("abyss_useful_stuff_table", "abyss_magic_treasure_table", "abyss_magical_defense_table", "abyss_scroll_table"),
    ),
    (
        "forsaken-depths",
        "forsaken_depths_tables.json",
        ("fd_heroic_magic_item_table", "fd_legendary_magic_item_table"),
    ),
    (
        "courtship",
        "courtship_blossoms_tables.json",
        ("courtship_blossoms_magic_item_table", "courtship_blossoms_spell_scrolls_table"),
    ),
)


class ResolvedItemCatalog(ResolvedSupplementContentCatalog):
    """Item-named view of the shared supplement content catalogue."""

    @property
    def item_ids(self) -> tuple[str, ...]:
        return self.record_ids

    @property
    def excluded_item_ids(self) -> tuple[str, ...]:
        return self.excluded_record_ids

    def definitions(self) -> list[dict[str, Any]]:
        return self.records()


def _record_id(provider_id: str, table_id: str, item_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", f"{provider_id}-{table_id}-{item_id}".lower()).strip("-")


def _table_item_definitions(provider_id: str, filename: str, table_id: str, rows: Any) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    for index, row in enumerate(rows if isinstance(rows, list) else []):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("item") or "").strip()
        if not name:
            continue
        item_id = str(row.get("key") or row.get("roll") or index + 1)
        definitions.append({
            "id": _record_id(provider_id, table_id, item_id),
            "kind": "table_backed_item",
            "name": name,
            "source": {
                "supplement_id": provider_id,
                "rule_file": filename,
                "table_id": table_id,
                "row_key": item_id,
            },
        })
    return definitions


def packaged_item_definitions(root_dir: Path | None) -> list[dict[str, Any]]:
    """List direct shop equipment and structured table-backed item identities."""
    rules_dir = packaged_rules_dir(root_dir)
    definitions: list[dict[str, Any]] = []
    shop_path = rules_dir / "equipment_shop.json"
    if shop_path.exists():
        shop = json.loads(shop_path.read_text(encoding="utf-8"))
        for item in shop.get("items", []) if isinstance(shop, dict) else []:
            if not isinstance(item, dict) or not item.get("key"):
                continue
            definitions.append({
                "id": str(item["key"]),
                "kind": "shop_equipment",
                "name": str(item.get("name") or item["key"]),
                "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "rule_file": "equipment_shop.json"},
            })
    for provider_id, filename, table_ids in TABLE_ITEM_SOURCES:
        path = rules_dir / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        for table_id in table_ids:
            definitions.extend(_table_item_definitions(provider_id, filename, table_id, payload.get(table_id)))
    return definitions


def resolve_item_catalog(root_dir: Path | None, active_supplement_ids: list[str] | tuple[str, ...]) -> ResolvedItemCatalog:
    resolved = resolve_supplement_content_catalog(
        packaged_item_definitions(root_dir),
        active_supplement_ids,
        default_provider_id=LOCKED_CORE_SUPPLEMENT_ID,
    )
    return ResolvedItemCatalog(
        active_supplement_ids=resolved.active_supplement_ids,
        provider_ids=resolved.provider_ids,
        record_ids=resolved.record_ids,
        excluded_record_ids=resolved.excluded_record_ids,
        _records=tuple(resolved.records()),
    )
