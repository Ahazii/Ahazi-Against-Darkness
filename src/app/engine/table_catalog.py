from __future__ import annotations

"""Supplement-scoped catalogue of packaged rule-table providers."""

import json
from pathlib import Path
from typing import Any

from .supplement_content_catalog import (
    ResolvedSupplementContentCatalog,
    packaged_rules_dir,
    resolve_supplement_content_catalog,
)
from .supplements import LOCKED_CORE_SUPPLEMENT_ID


TABLE_CATALOG_VERSION = 1
TABLE_PROVIDER_FILES: tuple[tuple[str, str], ...] = (
    (LOCKED_CORE_SUPPLEMENT_ID, "dungeon_tables.json"),
    ("forsaken-depths", "forsaken_depths_tables.json"),
    ("four-against-the-abyss", "abyss_tables.json"),
    ("courtship", "courtship_tables.json"),
    ("courtship", "courtship_blossoms_tables.json"),
)
DERIVED_TABLE_KEYS: dict[str, tuple[str, ...]] = {
    LOCKED_CORE_SUPPLEMENT_ID: ("equipment_shop_table",),
    "courtship": ("courtship_book_of_secrets_table", "courtship_apothecary_recipes_table"),
}
TABLE_META_KEYS = {"ruleset_status", "open_items", "validation"}


class ResolvedTableCatalog(ResolvedSupplementContentCatalog):
    """Table-named view of the reusable source catalogue."""

    @property
    def table_ids(self) -> tuple[str, ...]:
        return self.record_ids

    @property
    def excluded_table_ids(self) -> tuple[str, ...]:
        return self.excluded_record_ids

    def definitions(self) -> list[dict[str, Any]]:
        return self.records()


def packaged_table_definitions(root_dir: Path | None) -> list[dict[str, Any]]:
    """List table identities from packaged provider files without loading effects."""
    definitions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    rules_dir = packaged_rules_dir(root_dir)
    for supplement_id, filename in TABLE_PROVIDER_FILES:
        path = rules_dir / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        for table_id in payload:
            if table_id in TABLE_META_KEYS or table_id in seen_ids:
                continue
            seen_ids.add(table_id)
            definitions.append({
                "id": table_id,
                "kind": "rule_table",
                "source": {"supplement_id": supplement_id, "rule_file": filename},
            })
    for supplement_id, table_ids in DERIVED_TABLE_KEYS.items():
        for table_id in table_ids:
            if table_id in seen_ids:
                continue
            seen_ids.add(table_id)
            definitions.append({
                "id": table_id,
                "kind": "derived_rule_table",
                "source": {"supplement_id": supplement_id, "rule_file": "derived"},
            })
    return definitions


def resolve_table_catalog(root_dir: Path | None, active_supplement_ids: list[str] | tuple[str, ...]) -> ResolvedTableCatalog:
    resolved = resolve_supplement_content_catalog(
        packaged_table_definitions(root_dir),
        active_supplement_ids,
        default_provider_id=LOCKED_CORE_SUPPLEMENT_ID,
    )
    return ResolvedTableCatalog(
        active_supplement_ids=resolved.active_supplement_ids,
        provider_ids=resolved.provider_ids,
        record_ids=resolved.record_ids,
        excluded_record_ids=resolved.excluded_record_ids,
        _records=tuple(resolved.records()),
    )
