from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any


SUPPLEMENT_REGISTRY_VERSION = 1
LOCKED_CORE_SUPPLEMENT_ID = "expanded-edition-core"
SUPPLEMENT_MANIFEST_FILENAME = "supplement.json"
SUPPLEMENT_MANIFEST_SCHEMA_PATH = "data/supplements/schema/supplement_manifest.v1.json"
SUPPLEMENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SUPPLEMENT_KINDS = {
    "core_rules",
    "rules_expansion",
    "adventure",
    "campaign",
    "tile_pack",
    "terrain_pack",
    "imported_pdf",
    "local_user",
}
SUPPLEMENT_STATUSES = {"active", "review_only", "planned", "deprecated"}
SUPPLEMENT_SOURCE_TYPES = {"pdf", "local_user", "packaged_data"}
SUPPLEMENT_CAPABILITIES = {
    "foes",
    "classes",
    "items",
    "tables",
    "states",
    "rules",
    "room_tiles",
    "terrain_types",
    "generators",
    "rules_reference",
    "campaign_state",
    "procedures",
    "locations",
    "narrative",
    "maps",
    "trackers",
    "artwork",
}

LEGACY_SUPPLEMENT_FIELDS: list[dict[str, str]] = [
    {
        "field": "ruleset",
        "status": "legacy_compatibility",
        "replacement": "active_supplements",
        "notes": "Kept for existing saves and random-adventure setup while supplements become the activation model.",
    },
    {
        "field": "ruleset_profile_id",
        "status": "legacy_compatibility",
        "replacement": "active_supplements",
        "notes": "Still chooses current random-generation profiles; future sessions should snapshot enabled supplement ids.",
    },
    {
        "field": "tile_catalog",
        "status": "legacy_compatibility",
        "replacement": "active_supplements + room_tiles",
        "notes": "Current map generation uses this field until room-tile packs are supplement-owned.",
    },
    {
        "field": "courtship_enabled",
        "status": "legacy_compatibility",
        "replacement": "active_supplements",
        "notes": "Existing Forsaken Depths profile switch; future behavior should come from supplement activation.",
    },
    {
        "field": "fiendish_foes_enabled",
        "status": "legacy_compatibility",
        "replacement": "active_supplements",
        "notes": "Current optional foe-family flag; future behavior should come from supplement activation.",
    },
    {
        "field": "tag_banking_enabled",
        "status": "legacy_compatibility",
        "replacement": "campaign_supplements",
        "notes": "Campaign preference remains in use until TAG is modeled as an enabled campaign supplement.",
    },
]

SUPPLEMENTS: list[dict[str, Any]] = [
    {
        "id": LOCKED_CORE_SUPPLEMENT_ID,
        "title": "Four Against Darkness Expanded Edition",
        "kind": "core_rules",
        "status": "active",
        "locked": True,
        "enabled_by_default": True,
        "source": {
            "type": "pdf",
            "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf",
        },
        "capabilities": [
            "foes",
            "classes",
            "items",
            "tables",
            "states",
            "rules",
            "room_tiles",
            "terrain_types",
            "generators",
            "rules_reference",
        ],
        "dependencies": [],
        "conflicts": [],
        "legacy_mappings": {
            "ruleset": ["ee"],
            "ruleset_profile_id": ["ee_random"],
            "tile_catalog": ["ee"],
        },
        "notes": "Locked-on base game content. Gameplay still reads current data/rules files during migration.",
    },
    {
        "id": "four-against-the-abyss",
        "title": "Four Against the Abyss",
        "kind": "rules_expansion",
        "status": "active",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "pdf",
            "source_pdf": "Four-Against-the-Abyss.pdf",
        },
        "capabilities": [
            "foes",
            "items",
            "tables",
            "states",
            "rules",
            "campaign_state",
            "procedures",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "ruleset_profile_id": ["abyss"],
        },
        "notes": "Abyss-specific tables, afflictions, items, and campaign-state behavior remain wired through existing modules.",
    },
    {
        "id": "forsaken-depths",
        "title": "Four Against the Forsaken Depths",
        "kind": "rules_expansion",
        "status": "active",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "pdf",
            "source_pdf": "Four_Against_the_Forsaken_Depths.pdf",
        },
        "capabilities": [
            "foes",
            "classes",
            "items",
            "tables",
            "states",
            "rules",
            "room_tiles",
            "terrain_types",
            "generators",
            "procedures",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "ruleset": ["forsaken_depths"],
            "ruleset_profile_id": ["forsaken_depths", "forsaken_depths_no_courtship"],
            "tile_catalog": ["forsaken_depths", "forsaken_depths_rivers"],
        },
        "notes": "Current terrain, river, tile, and profile behavior stays in existing Forsaken Depths modules.",
    },
    {
        "id": "courtship",
        "title": "The Courtship of Flower Demons",
        "kind": "rules_expansion",
        "status": "active",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "pdf",
            "source_pdf": "The_Courtship_of_Flower_Demons.pdf",
        },
        "capabilities": [
            "foes",
            "classes",
            "items",
            "tables",
            "states",
            "rules",
            "terrain_types",
            "locations",
            "procedures",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "courtship_enabled": ["true"],
            "ruleset_profile_id": ["forsaken_depths"],
        },
        "notes": "Courtship content is currently enabled through the Forsaken Depths profile switch.",
    },
    {
        "id": "tag",
        "title": "Tales from the Adventurers' Guild",
        "kind": "campaign",
        "status": "active",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "pdf",
            "source_pdf": "Tales_from_the_adventurers_guild.pdf",
        },
        "capabilities": [
            "tables",
            "states",
            "rules",
            "procedures",
            "locations",
            "campaign_state",
            "generators",
            "narrative",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "tag_banking_enabled": ["true"],
            "adventure_type": ["tag_generated"],
        },
        "notes": "TAG guild, finance, generated-lead, and closeout behavior remains in current campaign/adventure modules.",
    },
    {
        "id": "imported-adventures",
        "title": "Imported Adventure Packages",
        "kind": "imported_pdf",
        "status": "review_only",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "local_user",
            "source_path": "DATA_DIR/Adventures",
        },
        "capabilities": [
            "foes",
            "classes",
            "items",
            "tables",
            "maps",
            "locations",
            "states",
            "rules",
            "trackers",
            "procedures",
            "artwork",
            "narrative",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "adventure_type": ["imported"],
        },
        "notes": "Local reviewed packages can contain exact PDF narrative text. They are not executable rule code.",
    },
]


def _manifest_display_path(path: Path, *, root_dir: Path | None = None, data_dir: Path | None = None) -> str:
    for label, base in (("DATA_DIR", data_dir), ("ROOT", root_dir)):
        if base is None:
            continue
        try:
            return f"{label}/{path.relative_to(base).as_posix()}"
        except ValueError:
            continue
    return path.as_posix()


def _string_list(value: Any, field: str, errors: list[str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{field} must be an array.")
        return []
    clean: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{field}[{index}] must be a non-empty string.")
            continue
        clean.append(item.strip())
    if len(clean) != len(set(clean)):
        errors.append(f"{field} must not contain duplicates.")
    return clean


def validate_supplement_manifest(raw: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if raw.get("schema_version") != SUPPLEMENT_REGISTRY_VERSION:
        errors.append(f"schema_version must be {SUPPLEMENT_REGISTRY_VERSION}.")
    supplement_id = str(raw.get("id") or "").strip()
    if not supplement_id:
        errors.append("id is required.")
    elif not SUPPLEMENT_ID_RE.match(supplement_id):
        errors.append("id must use lowercase letters, numbers, underscores, or hyphens and start with a letter or number.")
    for field in ("title", "kind", "status"):
        if not str(raw.get(field) or "").strip():
            errors.append(f"{field} is required.")
    kind = str(raw.get("kind") or "").strip()
    if kind and kind not in SUPPLEMENT_KINDS:
        errors.append(f"kind must be one of: {', '.join(sorted(SUPPLEMENT_KINDS))}.")
    status = str(raw.get("status") or "").strip()
    if status and status not in SUPPLEMENT_STATUSES:
        errors.append(f"status must be one of: {', '.join(sorted(SUPPLEMENT_STATUSES))}.")
    if not isinstance(raw.get("locked"), bool):
        errors.append("locked must be a boolean.")
    if not isinstance(raw.get("enabled_by_default"), bool):
        errors.append("enabled_by_default must be a boolean.")

    source = raw.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object.")
    else:
        source_type = str(source.get("type") or "").strip()
        if source_type not in SUPPLEMENT_SOURCE_TYPES:
            errors.append(f"source.type must be one of: {', '.join(sorted(SUPPLEMENT_SOURCE_TYPES))}.")
        if source_type == "pdf" and not str(source.get("source_pdf") or "").strip():
            errors.append("source.source_pdf is required for pdf supplements.")
        if source_type == "local_user" and not str(source.get("source_path") or "").strip():
            errors.append("source.source_path is required for local_user supplements.")

    capabilities = _string_list(raw.get("capabilities"), "capabilities", errors)
    if not capabilities:
        errors.append("capabilities must include at least one capability.")
    for capability in capabilities:
        if capability not in SUPPLEMENT_CAPABILITIES:
            errors.append(f"Unknown capability {capability!r}.")
    content_sources = raw.get("content_sources", [])
    if not isinstance(content_sources, list):
        errors.append("content_sources must be an array.")
    else:
        for index, entry in enumerate(content_sources):
            if not isinstance(entry, dict):
                errors.append(f"content_sources[{index}] must be an object.")
                continue
            kind = str(entry.get("kind") or "").strip()
            path = str(entry.get("path") or "").strip()
            if kind not in SUPPLEMENT_CAPABILITIES and kind != "spells":
                errors.append(f"content_sources[{index}].kind is unknown.")
            if not path:
                errors.append(f"content_sources[{index}].path is required.")
            if "description" in entry and not isinstance(entry.get("description"), str):
                errors.append(f"content_sources[{index}].description must be a string.")
    _string_list(raw.get("dependencies"), "dependencies", errors)
    _string_list(raw.get("conflicts"), "conflicts", errors)

    legacy_mappings = raw.get("legacy_mappings")
    if not isinstance(legacy_mappings, dict):
        errors.append("legacy_mappings must be an object.")
    else:
        for key, value in legacy_mappings.items():
            if not isinstance(key, str) or not key.strip():
                errors.append("legacy_mappings keys must be non-empty strings.")
                continue
            _string_list(value, f"legacy_mappings.{key}", errors)
    if "notes" in raw and not isinstance(raw.get("notes"), str):
        errors.append("notes must be a string.")
    return errors


def _normalize_manifest(raw: dict[str, Any], *, origin: str, path: Path, root_dir: Path | None, data_dir: Path | None) -> dict[str, Any]:
    validation_errors = validate_supplement_manifest(raw)
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    supplement_id = str(raw.get("id") or "").strip()
    title = str(raw.get("title") or "").strip()
    kind = str(raw.get("kind") or "").strip()
    status = str(raw.get("status") or "").strip()
    manifest = deepcopy(raw)
    manifest["id"] = supplement_id
    manifest["title"] = title
    manifest["kind"] = kind
    manifest["status"] = status
    manifest["capabilities"] = _string_list(raw.get("capabilities"), "capabilities", [])
    manifest["content_sources"] = [
        {
            "kind": str(entry.get("kind") or "").strip(),
            "path": str(entry.get("path") or "").strip(),
            "description": str(entry.get("description") or "").strip(),
        }
        for entry in raw.get("content_sources", [])
        if isinstance(entry, dict)
    ]
    manifest["dependencies"] = _string_list(manifest.get("dependencies"), "dependencies", [])
    manifest["conflicts"] = _string_list(manifest.get("conflicts"), "conflicts", [])
    manifest["legacy_mappings"] = {
        str(key): _string_list(value, f"legacy_mappings.{key}", [])
        for key, value in (manifest.get("legacy_mappings") or {}).items()
    }
    manifest["registry_origin"] = origin
    manifest["manifest_path"] = _manifest_display_path(path, root_dir=root_dir, data_dir=data_dir)
    return manifest


def _load_manifest_dir(
    directory: Path,
    *,
    origin: str,
    root_dir: Path | None,
    data_dir: Path | None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    manifests: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    if not directory.exists():
        return manifests, diagnostics
    for path in sorted(directory.glob(f"*/{SUPPLEMENT_MANIFEST_FILENAME}")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("manifest root must be an object.")
            manifests.append(_normalize_manifest(raw, origin=origin, path=path, root_dir=root_dir, data_dir=data_dir))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            diagnostics.append(
                {
                    "severity": "warning",
                    "path": _manifest_display_path(path, root_dir=root_dir, data_dir=data_dir),
                    "message": f"Could not load supplement manifest: {exc}",
                }
            )
    return manifests, diagnostics


def supplement_registry_with_diagnostics(
    root_dir: Path | None = None,
    data_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    supplements = []
    seen: set[str] = set()
    diagnostics: list[dict[str, str]] = []

    def append_records(records: list[dict[str, Any]], *, replace: bool = False) -> None:
        nonlocal supplements
        for record in records:
            supplement_id = str(record.get("id") or "")
            if not supplement_id:
                continue
            if supplement_id in seen:
                if not replace:
                    diagnostics.append(
                        {
                            "severity": "warning",
                            "path": str(record.get("manifest_path") or ""),
                            "message": f"Duplicate supplement id {supplement_id!r} ignored.",
                        }
                    )
                    continue
                supplements = [item for item in supplements if item.get("id") != supplement_id]
            seen.add(supplement_id)
            supplements.append(record)

    append_records([{**deepcopy(item), "registry_origin": "builtin_fallback", "manifest_path": ""} for item in SUPPLEMENTS])
    if root_dir is not None:
        packaged, packaged_diagnostics = _load_manifest_dir(
            root_dir / "data" / "supplements",
            origin="packaged_manifest",
            root_dir=root_dir,
            data_dir=data_dir,
        )
        diagnostics.extend(packaged_diagnostics)
        append_records(packaged, replace=True)
    if data_dir is not None:
        local, local_diagnostics = _load_manifest_dir(
            data_dir / "Supplements",
            origin="local_manifest",
            root_dir=root_dir,
            data_dir=data_dir,
        )
        diagnostics.extend(local_diagnostics)
        append_records(local, replace=False)
    canonical_order = {str(item["id"]): index for index, item in enumerate(SUPPLEMENTS)}
    supplements.sort(
        key=lambda item: (
            canonical_order.get(str(item.get("id") or ""), len(canonical_order)),
            str(item.get("title") or ""),
        )
    )
    known = {str(item.get("id") or "") for item in supplements}
    for item in supplements:
        supplement_id = str(item.get("id") or "")
        for field in ("dependencies", "conflicts"):
            for referenced_id in item.get(field, []):
                if referenced_id not in known:
                    label = "dependency" if field == "dependencies" else "conflict"
                    diagnostics.append(
                        {
                            "severity": "warning",
                            "path": str(item.get("manifest_path") or supplement_id),
                            "message": f"Supplement {supplement_id!r} references unknown {label} {referenced_id!r}.",
                        }
                    )
        for conflict_id in item.get("conflicts", []):
            other = next((candidate for candidate in supplements if candidate.get("id") == conflict_id), None)
            if other is not None and supplement_id not in (other.get("conflicts") or []):
                diagnostics.append(
                    {
                        "severity": "warning",
                        "path": str(item.get("manifest_path") or supplement_id),
                        "message": f"Supplement {supplement_id!r} conflicts with {conflict_id!r}, but the reverse conflict is not declared.",
                    }
                )
    return supplements, diagnostics


def supplement_registry(root_dir: Path | None = None, data_dir: Path | None = None) -> list[dict[str, Any]]:
    supplements, _diagnostics = supplement_registry_with_diagnostics(root_dir, data_dir)
    return deepcopy(supplements)


def _append_unique(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def known_supplement_ids(supplements: list[dict[str, Any]] | None = None) -> set[str]:
    registry = supplements if supplements is not None else SUPPLEMENTS
    return {str(item["id"]) for item in registry}


def supplement_titles_for_ids(supplement_ids: list[str] | None, supplements: list[dict[str, Any]] | None = None) -> list[str]:
    """Return display titles for a stored supplement snapshot."""
    registry = supplements if supplements is not None else SUPPLEMENTS
    titles_by_id = {str(item["id"]): str(item["title"]) for item in registry}
    titles: list[str] = []
    for raw_id in supplement_ids or []:
        supplement_id = str(raw_id or "").strip()
        if supplement_id:
            titles.append(titles_by_id.get(supplement_id, supplement_id))
    return titles


def supplement_selection_issues(supplement_ids: list[str], supplements: list[dict[str, Any]] | None = None) -> list[str]:
    registry = supplements if supplements is not None else SUPPLEMENTS
    selected = set(supplement_ids)
    by_id = {str(item["id"]): item for item in registry}
    issues: list[str] = []
    for supplement_id in sorted(selected):
        supplement = by_id.get(supplement_id)
        if not supplement:
            continue
        for dependency_id in supplement.get("dependencies", []):
            if dependency_id not in selected:
                issues.append(f"{supplement_id} requires {dependency_id}.")
        for conflict_id in supplement.get("conflicts", []):
            if conflict_id in selected:
                issues.append(f"{supplement_id} conflicts with {conflict_id}.")
    return issues


def supplement_snapshot_log_line(supplement_ids: list[str] | None, supplements: list[dict[str, Any]] | None = None) -> str:
    titles = supplement_titles_for_ids(supplement_ids, supplements)
    if not titles:
        return "Supplements locked for this session: legacy session with no supplement snapshot metadata."
    return f"Supplements locked for this session: {', '.join(titles)}."


def enabled_supplement_ids_from_selection(
    selected_ids: list[str] | None,
    supplements: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Normalize saved defaults or per-session supplement selections."""
    registry = supplements if supplements is not None else SUPPLEMENTS
    known = known_supplement_ids(registry)
    ids = [LOCKED_CORE_SUPPLEMENT_ID]
    for raw_id in selected_ids or []:
        supplement_id = str(raw_id or "").strip()
        if not supplement_id:
            continue
        if supplement_id not in known:
            raise ValueError(f"Unknown supplement id: {supplement_id}")
        _append_unique(ids, supplement_id)
        supplement = next((item for item in registry if item["id"] == supplement_id), {})
        for dependency_id in supplement.get("dependencies", []):
            if dependency_id not in known:
                raise ValueError(f"Unknown supplement dependency: {dependency_id}")
            _append_unique(ids, dependency_id)
    issues = supplement_selection_issues(ids, registry)
    if issues:
        raise ValueError(" ".join(issues))
    return ids


def legacy_random_profile_id_for_supplements(supplement_ids: list[str] | None) -> str:
    """Return the current random-session profile that best matches supplements."""
    enabled = set(supplement_ids or [])
    if "four-against-the-abyss" in enabled:
        return "abyss"
    if "forsaken-depths" in enabled and "courtship" in enabled:
        return "forsaken_depths"
    if "forsaken-depths" in enabled:
        return "forsaken_depths_no_courtship"
    return "ee_random"


def active_supplement_ids_for_legacy_session(
    *,
    adventure_type: str = "random",
    ruleset: str = "ee",
    ruleset_profile_id: str | None = None,
    courtship_enabled: bool = False,
    tag_banking_enabled: bool = False,
    tile_catalog: str | None = None,
    tag_generated: bool = False,
) -> list[str]:
    ids = [LOCKED_CORE_SUPPLEMENT_ID]
    profile = (ruleset_profile_id or "").strip().lower()
    chosen_ruleset = (ruleset or "").strip().lower()
    catalog = (tile_catalog or "").strip().lower()
    if profile == "abyss":
        _append_unique(ids, "four-against-the-abyss")
    if (
        chosen_ruleset == "forsaken_depths"
        or profile.startswith("forsaken_depths")
        or profile == "courtship_demesne"
        or catalog.startswith("forsaken_depths")
    ):
        _append_unique(ids, "forsaken-depths")
    if courtship_enabled or profile == "courtship_demesne":
        _append_unique(ids, "courtship")
    if tag_generated:
        _append_unique(ids, "tag")
    if adventure_type == "imported":
        _append_unique(ids, "imported-adventures")
    return ids


def supplement_payload(root_dir: Path | None = None, data_dir: Path | None = None) -> dict[str, Any]:
    supplements, diagnostics = supplement_registry_with_diagnostics(root_dir, data_dir)
    return {
        "schema_version": SUPPLEMENT_REGISTRY_VERSION,
        "read_only": True,
        "locked_core_id": LOCKED_CORE_SUPPLEMENT_ID,
        "supplements": supplements,
        "legacy_fields": deepcopy(LEGACY_SUPPLEMENT_FIELDS),
        "manifest_filename": SUPPLEMENT_MANIFEST_FILENAME,
        "manifest_schema": f"ROOT/{SUPPLEMENT_MANIFEST_SCHEMA_PATH}",
        "packaged_manifest_root": "ROOT/data/supplements",
        "local_manifest_root": "DATA_DIR/Supplements",
        "diagnostics": diagnostics,
    }
