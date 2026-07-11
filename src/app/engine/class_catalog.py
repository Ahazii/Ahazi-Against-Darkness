from __future__ import annotations

"""Supplement-scoped catalogue of packaged character classes."""

import json
from pathlib import Path
from typing import Any

from .supplement_content_catalog import (
    ResolvedSupplementContentCatalog,
    packaged_rules_dir,
    resolve_supplement_content_catalog,
)
from .supplements import LOCKED_CORE_SUPPLEMENT_ID, declared_content_sources


CLASS_CATALOG_VERSION = 1


class ResolvedClassCatalog(ResolvedSupplementContentCatalog):
    """Class-named view of the shared supplement content catalogue."""

    @property
    def class_ids(self) -> tuple[str, ...]:
        return self.record_ids

    @property
    def excluded_class_ids(self) -> tuple[str, ...]:
        return self.excluded_record_ids

    def definitions(self) -> list[dict[str, Any]]:
        return self.records()


def packaged_class_definitions(root_dir: Path | None) -> list[dict[str, Any]]:
    """Read class ownership from the existing profile data without executing class rules."""
    rules_dir = packaged_rules_dir(root_dir)
    classes_path = rules_dir / "classes.json"
    profiles_path = rules_dir / "ruleset_profiles.json"
    if not classes_path.exists():
        return []
    classes = json.loads(classes_path.read_text(encoding="utf-8"))
    profile_data = json.loads(profiles_path.read_text(encoding="utf-8")) if profiles_path.exists() else {}
    class_source_books = profile_data.get("class_source_books", {}) if isinstance(profile_data, dict) else {}
    if not isinstance(class_source_books, dict):
        class_source_books = {}
    declared_paths = {
        entry["supplement_id"]: Path(entry["path"]).name
        for entry in declared_content_sources(root_dir, None, "classes")
        if Path(entry["path"]).name == "classes.json"
    }
    definitions: list[dict[str, Any]] = []
    for item in classes if isinstance(classes, list) else []:
        if not isinstance(item, dict):
            continue
        class_id = str(item.get("id") or "").strip()
        if not class_id:
            continue
        source_books = class_source_books.get(class_id, [])
        provider_id = str(source_books[0]) if isinstance(source_books, list) and source_books else LOCKED_CORE_SUPPLEMENT_ID
        if declared_paths and provider_id not in declared_paths:
            continue
        definitions.append({
            "id": class_id,
            "kind": "character_class",
            "name": str(item.get("name") or class_id),
            "source": {
                "supplement_id": provider_id,
                "rule_file": declared_paths.get(provider_id, "classes.json"),
                "ownership_file": "ruleset_profiles.json" if provider_id != LOCKED_CORE_SUPPLEMENT_ID else "",
            },
        })
    return definitions


def resolve_class_catalog(root_dir: Path | None, active_supplement_ids: list[str] | tuple[str, ...]) -> ResolvedClassCatalog:
    resolved = resolve_supplement_content_catalog(
        packaged_class_definitions(root_dir),
        active_supplement_ids,
        default_provider_id=LOCKED_CORE_SUPPLEMENT_ID,
    )
    return ResolvedClassCatalog(
        active_supplement_ids=resolved.active_supplement_ids,
        provider_ids=resolved.provider_ids,
        record_ids=resolved.record_ids,
        excluded_record_ids=resolved.excluded_record_ids,
        _records=tuple(resolved.records()),
    )
