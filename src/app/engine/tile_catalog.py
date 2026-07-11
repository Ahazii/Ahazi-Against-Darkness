from __future__ import annotations

"""Supplement-scoped catalogue of random-dungeon room tiles.

Authored maps and pinned locations are deliberately excluded. This catalogue
only records the reusable random-dungeon tiles supplied by the current
supplement snapshot; placement and generation remain in the legacy engine.
"""

import json
from pathlib import Path
from typing import Any

from .supplement_content_catalog import (
    ResolvedSupplementContentCatalog,
    packaged_rules_dir,
    resolve_supplement_content_catalog,
)
from .supplements import LOCKED_CORE_SUPPLEMENT_ID
from .tile_catalogs import TILE_CATALOG_FILES


TILE_CATALOG_VERSION = 1
TILE_CATALOG_PROVIDERS: tuple[tuple[str, str], ...] = (
    (LOCKED_CORE_SUPPLEMENT_ID, "ee"),
    ("forsaken-depths", "forsaken_depths"),
    ("forsaken-depths", "forsaken_depths_rivers"),
)


class ResolvedTileCatalog(ResolvedSupplementContentCatalog):
    """Tile-named view of the shared supplement content catalogue."""

    @property
    def tile_ids(self) -> tuple[str, ...]:
        return self.record_ids

    @property
    def excluded_tile_ids(self) -> tuple[str, ...]:
        return self.excluded_record_ids

    def definitions(self) -> list[dict[str, Any]]:
        return self.records()


def packaged_tile_definitions(root_dir: Path | None) -> list[dict[str, Any]]:
    """List packaged tile identities without invoking map placement logic."""
    definitions: list[dict[str, Any]] = []
    rules_dir = packaged_rules_dir(root_dir)
    for supplement_id, catalog_id in TILE_CATALOG_PROVIDERS:
        filename = TILE_CATALOG_FILES[catalog_id]
        path = rules_dir / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            definitions.append({
                "id": f"{catalog_id}:{key}",
                "kind": "random_dungeon_tile",
                "key": key,
                "catalog_id": catalog_id,
                "source": {
                    "supplement_id": supplement_id,
                    "rule_file": filename,
                },
            })
    return definitions


def resolve_tile_catalog(root_dir: Path | None, active_supplement_ids: list[str] | tuple[str, ...]) -> ResolvedTileCatalog:
    resolved = resolve_supplement_content_catalog(
        packaged_tile_definitions(root_dir),
        active_supplement_ids,
        default_provider_id=LOCKED_CORE_SUPPLEMENT_ID,
    )
    return ResolvedTileCatalog(
        active_supplement_ids=resolved.active_supplement_ids,
        provider_ids=resolved.provider_ids,
        record_ids=resolved.record_ids,
        excluded_record_ids=resolved.excluded_record_ids,
        _records=tuple(resolved.records()),
    )
