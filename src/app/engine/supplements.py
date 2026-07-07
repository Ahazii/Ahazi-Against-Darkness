from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


SUPPLEMENT_REGISTRY_VERSION = 1
LOCKED_CORE_SUPPLEMENT_ID = "expanded-edition-core"
SUPPLEMENT_MANIFEST_FILENAME = "supplement.json"

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


def _normalize_manifest(raw: dict[str, Any], *, origin: str, path: Path, root_dir: Path | None, data_dir: Path | None) -> dict[str, Any]:
    supplement_id = str(raw.get("id") or "").strip()
    title = str(raw.get("title") or "").strip()
    kind = str(raw.get("kind") or "").strip()
    status = str(raw.get("status") or "").strip()
    if not supplement_id:
        raise ValueError("id is required.")
    if not title:
        raise ValueError(f"{supplement_id}: title is required.")
    if not kind:
        raise ValueError(f"{supplement_id}: kind is required.")
    if not status:
        raise ValueError(f"{supplement_id}: status is required.")
    capabilities = raw.get("capabilities") or []
    if not isinstance(capabilities, list):
        raise ValueError(f"{supplement_id}: capabilities must be an array.")
    manifest = deepcopy(raw)
    manifest["id"] = supplement_id
    manifest["title"] = title
    manifest["kind"] = kind
    manifest["status"] = status
    manifest["capabilities"] = [str(item) for item in capabilities]
    manifest["dependencies"] = [str(item) for item in manifest.get("dependencies") or []]
    manifest["conflicts"] = [str(item) for item in manifest.get("conflicts") or []]
    manifest["legacy_mappings"] = manifest.get("legacy_mappings") if isinstance(manifest.get("legacy_mappings"), dict) else {}
    manifest["source"] = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    manifest["locked"] = bool(manifest.get("locked"))
    manifest["enabled_by_default"] = bool(manifest.get("enabled_by_default"))
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
        "packaged_manifest_root": "ROOT/data/supplements",
        "local_manifest_root": "DATA_DIR/Supplements",
        "diagnostics": diagnostics,
    }
