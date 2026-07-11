from __future__ import annotations

"""Supplement-scoped catalogue of packaged foe definitions.

This catalogue records ownership and session scope only. Combat continues to
use its established legacy loaders until a later, source-locked migration can
move one encounter family at a time without changing live behaviour.
"""

import json
from pathlib import Path
import re
from typing import Any

from .supplement_content_catalog import (
    ResolvedSupplementContentCatalog,
    resolve_supplement_content_catalog,
)
from .supplements import LOCKED_CORE_SUPPLEMENT_ID


FOE_CATALOG_VERSION = 1
FOE_PROVIDER_FILES: tuple[tuple[str, str], ...] = (
    (LOCKED_CORE_SUPPLEMENT_ID, "monsters.json"),
    ("forsaken-depths", "fd_monsters.json"),
    ("courtship", "courtship_monsters.json"),
    ("tag", "tag_monsters.json"),
)
ABYSS_FOE_TABLE_IDS = (
    "abyss_vermin_table",
    "abyss_minions_table",
    "abyss_weird_table",
    "abyss_boss_table",
    "abyss_dragon_table",
)


class ResolvedFoeCatalog(ResolvedSupplementContentCatalog):
    """Foe-named view of the shared supplement content catalogue."""

    @property
    def foe_ids(self) -> tuple[str, ...]:
        return self.record_ids

    @property
    def excluded_foe_ids(self) -> tuple[str, ...]:
        return self.excluded_record_ids

    def definitions(self) -> list[dict[str, Any]]:
        return self.records()


def packaged_rules_dir(root_dir: Path | None) -> Path:
    if root_dir is not None:
        return root_dir / "data" / "rules"
    return Path(__file__).resolve().parents[3] / "data" / "rules"


def _foe_id(provider_id: str, group: str, name: str, index: int) -> str:
    parts = [provider_id, group, name or str(index + 1)]
    return re.sub(r"[^a-z0-9]+", "-", "-".join(parts).lower()).strip("-")


def _definitions_from_rows(
    provider_id: str,
    source_file: str,
    group: str,
    rows: list[Any],
) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("title") or "").strip()
        if not name:
            continue
        foe_id = _foe_id(provider_id, group, name, index)
        if foe_id in seen_ids:
            foe_id = f"{foe_id}-{index + 1}"
        seen_ids.add(foe_id)
        definitions.append({
            "id": foe_id,
            "kind": "foe",
            "name": name,
            "group": group,
            "source": {
                "supplement_id": provider_id,
                "rule_file": source_file,
                "row_key": str(row.get("roll") or index + 1),
            },
        })
    return definitions


def packaged_foe_definitions(root_dir: Path | None) -> list[dict[str, Any]]:
    """List packaged foe identities without loading combat effects."""
    definitions: list[dict[str, Any]] = []
    rules_dir = packaged_rules_dir(root_dir)
    for provider_id, filename in FOE_PROVIDER_FILES:
        path = rules_dir / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        for group, rows in payload.items():
            if isinstance(rows, list):
                definitions.extend(_definitions_from_rows(provider_id, filename, str(group), rows))

    abyss_path = rules_dir / "abyss_tables.json"
    if abyss_path.exists():
        payload = json.loads(abyss_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            for table_id in ABYSS_FOE_TABLE_IDS:
                rows = payload.get(table_id)
                if isinstance(rows, list):
                    definitions.extend(_definitions_from_rows("four-against-the-abyss", "abyss_tables.json", table_id, rows))
    return definitions


def resolve_foe_catalog(root_dir: Path | None, active_supplement_ids: list[str] | tuple[str, ...]) -> ResolvedFoeCatalog:
    resolved = resolve_supplement_content_catalog(
        packaged_foe_definitions(root_dir),
        active_supplement_ids,
        default_provider_id=LOCKED_CORE_SUPPLEMENT_ID,
    )
    return ResolvedFoeCatalog(
        active_supplement_ids=resolved.active_supplement_ids,
        provider_ids=resolved.provider_ids,
        record_ids=resolved.record_ids,
        excluded_record_ids=resolved.excluded_record_ids,
        _records=tuple(resolved.records()),
    )
