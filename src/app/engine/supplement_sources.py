from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .pdf_text_index import display_page_number, extract_rule_pdf_pages, page_label


SOURCE_ARTWORK_CATEGORIES = {
    "unknown",
    "foe",
    "mount",
    "companion_animal",
    "npc",
    "character_class",
    "room",
    "dungeon",
    "location",
    "item_equipment",
    "terrain",
    "map",
    "tile",
    "room_tile_sheet",
    "room_tile",
    "front_cover",
    "back_cover",
    "filler_decorative",
    "cover_title_page",
    "symbol_icon",
    "review_later",
    "ignore",
}


SUPPLEMENT_PACKAGE_ASSET_CATEGORIES = {
    "unknown",
    "world_map",
    "dungeon_map",
    "location_map",
    "room_tile_sheet",
    "room_tile",
    "foe_art",
    "npc_art",
    "item_equipment_art",
    "cover_title_art",
    "front_cover_art",
    "back_cover_art",
    "handout",
    "filler_art_reference",
    "ignore",
}


SOURCE_BLOCK_ASSIGNMENTS = {
    "unassigned",
    "front_cover",
    "back_cover",
    "title_page",
    "table_of_contents",
    "credits",
    "introduction",
    "history",
    "lore",
    "artwork_filler",
    "advertisement",
    "index",
    "designer_notes",
    "example_play",
    "legal",
    "rule_text",
    "adventure_narrative",
    "location",
    "foe",
    "mount",
    "companion_animal",
    "equipment",
    "character_class",
    "table",
    "state",
    "terrain",
    "map",
    "room_tile",
    "ignore",
    "manual_entry",
}


SOURCE_BLOCK_ASSIGNMENT_DESCRIPTIONS = {
    "unassigned": "Not reviewed yet. Keep new extraction results here until their purpose is known.",
    "front_cover": "The outside front cover of a source volume.",
    "back_cover": "The outside back cover of a source volume.",
    "title_page": "An internal title or half-title page, separate from the front cover.",
    "table_of_contents": "A contents listing used for source navigation, not a playable rules table.",
    "credits": "Authors, artists, editors, copyright, and publication credits.",
    "introduction": "Opening guidance explaining the supplement, its audience, scope, or how to use it.",
    "history": "Historical background or chronology relevant to the setting.",
    "lore": "Setting fiction, culture, legends, or world background that is not itself a rule.",
    "artwork_filler": "Decorative text fragments, captions, or filler associated with artwork.",
    "advertisement": "Promotional material for other products.",
    "index": "An alphabetical or topical index of source pages.",
    "designer_notes": "Author commentary about design intent or optional interpretation.",
    "example_play": "Worked examples that demonstrate rules or play procedures.",
    "legal": "Licensing, trademarks, disclaimers, and other legal notices.",
    "rule_text": "Exact source wording that defines or modifies a playable rule.",
    "adventure_narrative": "Exact narrative, boxed text, encounters, or branching adventure prose.",
    "location": "A named place with description, links, occupants, encounters, or map placement.",
    "foe": "A foe, monster, boss, minion, reaction, or combat profile.",
    "mount": "A rideable animal or creature. This is review data until its riding rules are promoted.",
    "companion_animal": "A domesticated companion animal that may accompany or fight beside the party. This is review data until its rules are promoted.",
    "equipment": "Equipment, treasure, consumables, services, or magic items.",
    "character_class": "A playable class, subclass, ancestry, or character option.",
    "table": "A printed lookup table that should later become reviewed machine rows.",
    "state": "A condition or persistent state applied to characters, foes, equipment, or play.",
    "terrain": "A terrain or environment type with playable effects.",
    "map": "Map content, map keys, regions, routes, or map-specific instructions.",
    "room_tile": "A random-dungeon room tile, tile key, exits, die result, or tile instructions.",
    "ignore": "Repeated headers, footers, page furniture, or material intentionally excluded from the module.",
    "manual_entry": "Reviewer-created replacement text used when PDF extraction is incomplete or incorrect.",
}


SUPPLEMENT_REQUIREMENT_TYPES = {
    "party_eligibility",
    "dependency",
    "environment",
    "table_routing",
    "procedure",
    "other",
}


SUPPLEMENT_REQUIREMENT_ENFORCEMENT = {"information", "warning", "hard_gate", "conditional_routing"}


SUPPLEMENT_TABLE_TYPE_DESCRIPTIONS = {
    "reference_lookup": "A readable lookup table kept as reviewed text until a later specialised importer is needed.",
    "foe_encounter": "A combat encounter table. Each row selects one or more foes, quantities, and combat details.",
    "treasure_reward": "A treasure, reward, item, currency, or service outcome table.",
    "room_content": "A room, corridor, encounter, or exploration-content outcome table.",
    "reaction": "A foe or NPC reaction result table.",
    "equipment_shop": "An equipment, service, price, or shop availability table.",
    "state_condition": "A state, condition, effect, or consequence lookup table.",
    "terrain_tile": "A terrain, map feature, room tile, or random-dungeon tile table.",
}

SUPPLEMENT_TABLE_TYPES = set(SUPPLEMENT_TABLE_TYPE_DESCRIPTIONS)

SUPPLEMENT_PROFILE_DESCRIPTIONS = {
    "foe": "A combat foe, monster, boss, minion, or other hostile profile.",
    "mount": "A rideable animal or creature with riding, movement, and carrying details.",
    "companion_animal": "A domesticated animal companion with combat and ownership/training details.",
    "character_class": "A playable class or character option with eligibility, abilities, progression, and equipment details.",
    "location": "A room, settlement, wilderness site, dungeon feature, encounter, shop, or quest location with optional exits, encounters, rewards, hazards, NPCs, and map links.",
}

SUPPLEMENT_PROFILE_TYPES = set(SUPPLEMENT_PROFILE_DESCRIPTIONS)
SUPPLEMENT_PROFILE_COLLECTIONS = {
    "foe": "reviewed_foes",
    "mount": "reviewed_mounts",
    "companion_animal": "reviewed_companion_animals",
    "character_class": "reviewed_character_classes",
    "location": "reviewed_locations",
}


def supplement_sources_root(data_dir: Path) -> Path:
    return data_dir / "Supplements" / "_sources"


def supplement_source_id(pdf_path: Path) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", pdf_path.stem.lower()).strip("-")
    return slug or "pdf-source"


def supplement_package_id(value: str | None, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or fallback or "").lower()).strip("-")
    return slug or "supplement-package"


GENERIC_SUPPLEMENT_PACKAGE_IDS = {"", "package", "supplement", "supplement-package", "module"}
GENERIC_SUPPLEMENT_PACKAGE_TITLES = {"", "package", "supplement", "supplement package", "module"}


def _source_pdf_stem(value: str | None) -> str:
    raw = str(value or "").replace("\\", "/").rsplit("/", 1)[-1]
    return Path(raw).stem.strip()


def _friendly_source_title(value: str | None, source_pdf: str | None = None, source_id: str | None = None) -> str:
    title = str(value or "").strip()
    if title and ("/" in title or "\\" in title):
        title = _source_pdf_stem(title)
    if title.lower() in GENERIC_SUPPLEMENT_PACKAGE_TITLES:
        title = ""
    if not title:
        title = _source_pdf_stem(source_pdf)
    if not title:
        title = str(source_id or "").replace("-", " ").replace("_", " ").strip()
    return re.sub(r"\s+", " ", title.replace("_", " ")).strip() or "Supplement Package"


def _source_package_id(scan: dict[str, Any], known_package_ids: set[str] | None = None) -> str:
    source_id = str(scan.get("source_id") or "supplement")
    raw = supplement_package_id(str(scan.get("supplement_id") or ""), source_id)
    if raw in GENERIC_SUPPLEMENT_PACKAGE_IDS:
        return source_id
    if known_package_ids and raw not in known_package_ids and source_id in known_package_ids:
        return source_id
    return raw


def supplement_source_folder(data_dir: Path, source_id: str) -> Path:
    safe = re.sub(r"[^a-z0-9._-]+", "-", source_id.lower()).strip(".-")
    return supplement_sources_root(data_dir) / (safe or "pdf-source")


def supplement_source_scan_path(data_dir: Path, source_id: str) -> Path:
    return supplement_source_folder(data_dir, source_id) / "source_blocks.json"


def supplement_source_artwork_dir(data_dir: Path, source_id: str) -> Path:
    return supplement_source_folder(data_dir, source_id) / "artwork"


def supplement_package_asset_dir(data_dir: Path, package_id: str) -> Path:
    safe = supplement_package_id(package_id, "supplement-package")
    return supplement_sources_root(data_dir) / "_package_assets" / safe


def supplement_package_asset_path(data_dir: Path, package_id: str, filename: str) -> Path:
    safe_name = Path(str(filename or "")).name
    return supplement_package_asset_dir(data_dir, package_id) / safe_name


def supplement_source_settings_path(data_dir: Path) -> Path:
    return supplement_sources_root(data_dir) / "source_settings.json"


def supplement_source_pdf_page_cache_dir(data_dir: Path, source_pdf: str | None, source_id: str = "") -> Path:
    stem = _source_pdf_stem(source_pdf) or source_id or "pdf-source"
    safe = re.sub(r"[^a-z0-9._-]+", "-", stem.lower()).strip(".-")
    return supplement_sources_root(data_dir) / "_pdf_page_cache" / (safe or "pdf-source")


def _remove_tree_inside(root: Path, target: Path) -> bool:
    root_resolved = root.resolve(strict=False)
    target_resolved = target.resolve(strict=False)
    if root_resolved != target_resolved and root_resolved not in target_resolved.parents:
        raise ValueError(f"Refusing to remove path outside supplement source workspace: {target}")
    if not target.exists():
        return False
    shutil.rmtree(target)
    return True


def _load_source_settings(data_dir: Path) -> dict[str, Any]:
    path = supplement_source_settings_path(data_dir)
    if not path.exists():
        return {"schema_version": 1, "sources": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "sources": {}}
    return payload if isinstance(payload, dict) else {"schema_version": 1, "sources": {}}


def _write_source_settings(data_dir: Path, payload: dict[str, Any]) -> None:
    path = supplement_source_settings_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload.setdefault("schema_version", 1)
    payload.setdefault("sources", {})
    payload.setdefault("packages", {})
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def pdf_source_settings(data_dir: Path, pdf_path: Path) -> dict[str, Any]:
    source_id = supplement_source_id(pdf_path)
    payload = _load_source_settings(data_dir)
    sources = payload.get("sources") if isinstance(payload.get("sources"), dict) else {}
    settings = sources.get(source_id) if isinstance(sources.get(source_id), dict) else {}
    package_id = supplement_package_id(settings.get("supplement_id"), source_id)
    return {
        "configured": bool(settings),
        "source_id": source_id,
        "filename": pdf_path.name,
        "page_offset": int(settings.get("page_offset") or 0),
        "supplement_id": package_id,
        "supplement_title": str(settings.get("supplement_title") or pdf_path.stem),
    }


def set_pdf_source_metadata(
    data_dir: Path,
    pdf_path: Path,
    *,
    page_offset: int | None = None,
    supplement_id: str | None = None,
    supplement_title: str | None = None,
) -> dict[str, Any]:
    source_id = supplement_source_id(pdf_path)
    payload = _load_source_settings(data_dir)
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        sources = {}
        payload["sources"] = sources
    previous = sources.get(source_id) if isinstance(sources.get(source_id), dict) else {}
    package_id = supplement_package_id(supplement_id or previous.get("supplement_id"), source_id)
    title = str(supplement_title or previous.get("supplement_title") or pdf_path.stem).strip() or pdf_path.stem
    sources[source_id] = {
        **previous,
        "source_id": source_id,
        "filename": pdf_path.name,
        "page_offset": int(page_offset if page_offset is not None else previous.get("page_offset") or 0),
        "supplement_id": package_id,
        "supplement_title": title,
    }
    packages = payload.get("packages")
    if not isinstance(packages, dict):
        packages = {}
        payload["packages"] = packages
    previous_package = packages.get(package_id) if isinstance(packages.get(package_id), dict) else {}
    packages[package_id] = {
        **previous_package,
        "supplement_id": package_id,
        "supplement_title": title,
        "assets": previous_package.get("assets") if isinstance(previous_package.get("assets"), list) else [],
        "requirements": previous_package.get("requirements") if isinstance(previous_package.get("requirements"), list) else [],
    }
    _write_source_settings(data_dir, payload)
    return sources[source_id]


def set_pdf_source_page_offset(data_dir: Path, pdf_path: Path, page_offset: int) -> dict[str, Any]:
    return set_pdf_source_metadata(data_dir, pdf_path, page_offset=page_offset)


def _relabel_page_record(record: dict[str, Any], page_offset: int) -> bool:
    try:
        pdf_page = int(record.get("pdf_page") or 0)
    except (TypeError, ValueError):
        return False
    if pdf_page < 1:
        return False
    old_source_page = record.get("source_page")
    record["source_page"] = display_page_number(pdf_page, page_offset)
    record["page_offset"] = int(page_offset)
    try:
        pdf_page_end = int(record.get("pdf_page_end") or 0)
    except (TypeError, ValueError):
        pdf_page_end = 0
    if pdf_page_end > 0:
        record["source_page_end"] = display_page_number(pdf_page_end, page_offset)
        record["page_label"] = f"{page_label(pdf_page, page_offset)} to {page_label(pdf_page_end, page_offset)}"
    else:
        record["page_label"] = page_label(pdf_page, page_offset)
    title = str(record.get("title") or "")
    if re.fullmatch(r"Page\s+-?\d+\s+image\s+\d+", title, flags=re.IGNORECASE):
        image_number = title.rsplit(" ", 1)[-1]
        record["title"] = f"Page {record['source_page']} image {image_number}"
    elif re.fullmatch(r"Rendered\s+page\s+-?\d+", title, flags=re.IGNORECASE):
        record["title"] = f"Rendered page {record['source_page']}"
    return old_source_page != record["source_page"]


def _merge_orphaned_package_assets(
    data_dir: Path,
    settings_payload: dict[str, Any],
    *,
    old_package_id: str,
    new_package_id: str,
    new_package_title: str,
    moving_source_id: str,
) -> int:
    if old_package_id == new_package_id:
        return 0
    sources = settings_payload.get("sources") if isinstance(settings_payload.get("sources"), dict) else {}
    if any(
        supplement_package_id(source.get("supplement_id"), str(source_id)) == old_package_id
        for source_id, source in sources.items()
        if isinstance(source, dict)
    ):
        return 0
    known_package_ids = {
        supplement_package_id(str(package.get("supplement_id") or package_id), str(package_id))
        for package_id, package in _package_settings(settings_payload).items()
        if isinstance(package, dict)
    }
    for scan_path in supplement_sources_root(data_dir).glob("*/source_blocks.json"):
        if scan_path.parent.name == moving_source_id:
            continue
        try:
            scan = json.loads(scan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(scan, dict) and _source_package_id({**scan, "source_id": scan_path.parent.name}, known_package_ids) == old_package_id:
            return 0
    packages = _package_settings(settings_payload)
    old_package = packages.get(old_package_id) if isinstance(packages.get(old_package_id), dict) else None
    if old_package is None:
        return 0
    new_package = packages.get(new_package_id) if isinstance(packages.get(new_package_id), dict) else {
        "supplement_id": new_package_id,
        "supplement_title": new_package_title,
        "assets": [],
    }
    existing_assets = [item for item in new_package.get("assets", []) if isinstance(item, dict)]
    existing_names = {str(item.get("filename") or "") for item in existing_assets}
    old_dir = supplement_package_asset_dir(data_dir, old_package_id)
    new_dir = supplement_package_asset_dir(data_dir, new_package_id)
    migrated = 0
    for asset in old_package.get("assets", []):
        if not isinstance(asset, dict):
            continue
        filename = Path(str(asset.get("filename") or "")).name
        if not filename:
            continue
        source_path = old_dir / filename
        target_path = new_dir / filename
        if filename not in existing_names:
            new_dir.mkdir(parents=True, exist_ok=True)
            if source_path.is_file() and not target_path.exists():
                shutil.move(str(source_path), str(target_path))
            moved = dict(asset)
            moved["asset_url"] = f"/api/supplements/source-packages/{new_package_id}/assets/{filename}"
            existing_assets.append(moved)
            existing_names.add(filename)
            migrated += 1
        elif source_path.is_file():
            if not target_path.exists():
                new_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(target_path))
            else:
                source_path.unlink()
    new_package.update({
        "supplement_id": new_package_id,
        "supplement_title": new_package_title,
        "assets": existing_assets,
    })
    packages[new_package_id] = new_package
    del packages[old_package_id]
    if old_dir.is_dir() and not any(old_dir.iterdir()):
        old_dir.rmdir()
    return migrated


def update_supplement_source_metadata(
    data_dir: Path,
    source_id: str,
    *,
    page_offset: int,
    supplement_id: str | None = None,
    supplement_title: str | None = None,
    source_filename: str = "",
) -> dict[str, Any]:
    """Apply printed-page and package metadata to every existing review artifact."""
    clean_source_id = supplement_package_id(source_id, "pdf-source")
    payload = load_supplement_source_scan(data_dir, clean_source_id)
    settings_payload = _load_source_settings(data_dir)
    settings_sources = settings_payload.get("sources") if isinstance(settings_payload.get("sources"), dict) else {}
    previous_settings = settings_sources.get(clean_source_id) if isinstance(settings_sources.get(clean_source_id), dict) else {}
    source_pdf = str(payload.get("source_pdf") or previous_settings.get("filename") or source_filename or "")
    filename = Path(source_pdf.replace("\\", "/")).name
    if not filename:
        raise KeyError(clean_source_id)
    old_package_id = supplement_package_id(
        str(payload.get("supplement_id") or previous_settings.get("supplement_id") or ""),
        clean_source_id,
    )
    new_package_id = supplement_package_id(supplement_id, old_package_id)
    new_package_title = str(
        supplement_title
        or payload.get("supplement_title")
        or previous_settings.get("supplement_title")
        or _friendly_source_title(None, filename, new_package_id)
    ).strip()
    settings_sources[clean_source_id] = {
        **previous_settings,
        "source_id": clean_source_id,
        "filename": filename,
        "page_offset": int(page_offset),
        "supplement_id": new_package_id,
        "supplement_title": new_package_title,
    }
    settings_payload["sources"] = settings_sources

    relabelled = 0
    seen_lists: set[int] = set()
    for key in (
        "raw_blocks",
        "reviewed_blocks",
        "blocks",
        "continuation_candidates",
        "raw_artwork",
        "reviewed_artwork",
        "artwork",
        "reviewed_tables",
        "tables",
    ):
        records = payload.get(key)
        if not isinstance(records, list) or id(records) in seen_lists:
            continue
        seen_lists.add(id(records))
        for record in records:
            if not isinstance(record, dict):
                continue
            record["supplement_id"] = new_package_id
            record["supplement_title"] = new_package_title
            if _relabel_page_record(record, page_offset):
                relabelled += 1
    payload.update({
        "supplement_id": new_package_id,
        "supplement_title": new_package_title,
        "page_offset": int(page_offset),
    })
    migrated_assets = _merge_orphaned_package_assets(
        data_dir,
        settings_payload,
        old_package_id=old_package_id,
        new_package_id=new_package_id,
        new_package_title=new_package_title,
        moving_source_id=clean_source_id,
    )
    packages = _package_settings(settings_payload)
    target_package = packages.get(new_package_id) if isinstance(packages.get(new_package_id), dict) else {}
    packages[new_package_id] = {
        **target_package,
        "supplement_id": new_package_id,
        "supplement_title": new_package_title,
        "assets": target_package.get("assets") if isinstance(target_package.get("assets"), list) else [],
    }
    _write_source_settings(data_dir, settings_payload)
    if supplement_source_scan_path(data_dir, clean_source_id).exists():
        save_supplement_source_scan(data_dir, clean_source_id, payload)
    return {
        "source_id": clean_source_id,
        "filename": filename,
        "page_offset": int(page_offset),
        "supplement_id": new_package_id,
        "supplement_title": new_package_title,
        "previous_supplement_id": old_package_id,
        "records_relabelled": relabelled,
        "assets_migrated": migrated_assets,
    }


def _package_settings(payload: dict[str, Any]) -> dict[str, Any]:
    packages = payload.get("packages")
    if not isinstance(packages, dict):
        packages = {}
        payload["packages"] = packages
    return packages


def upsert_supplement_package(
    data_dir: Path,
    *,
    supplement_id: str | None,
    supplement_title: str | None,
    fallback: str,
) -> dict[str, Any]:
    payload = _load_source_settings(data_dir)
    packages = _package_settings(payload)
    package_id = supplement_package_id(supplement_id, fallback)
    previous = packages.get(package_id) if isinstance(packages.get(package_id), dict) else {}
    title = str(supplement_title or previous.get("supplement_title") or fallback).strip() or fallback
    packages[package_id] = {
        **previous,
        "supplement_id": package_id,
        "supplement_title": title,
        "assets": previous.get("assets") if isinstance(previous.get("assets"), list) else [],
        "requirements": previous.get("requirements") if isinstance(previous.get("requirements"), list) else [],
    }
    _write_source_settings(data_dir, payload)
    return packages[package_id]


def _clean_string_list(value: Any) -> list[str]:
    values = value if isinstance(value, list) else re.split(r"[,\n;]+", str(value or ""))
    return [str(item).strip() for item in values if str(item).strip()]


def upsert_supplement_package_requirement(
    data_dir: Path,
    package_id: str,
    requirement: dict[str, Any],
    requirement_id: str = "",
) -> dict[str, Any]:
    payload = _load_source_settings(data_dir)
    packages = _package_settings(payload)
    safe_package_id = supplement_package_id(package_id, "supplement-package")
    package = packages.get(safe_package_id) if isinstance(packages.get(safe_package_id), dict) else None
    if package is None:
        raise KeyError(package_id)
    requirements = [item for item in package.get("requirements", []) if isinstance(item, dict)]
    existing = next((item for item in requirements if str(item.get("id") or "") == requirement_id), None)
    if requirement_id and existing is None:
        raise KeyError(requirement_id)
    title = str(requirement.get("title") or (existing or {}).get("title") or "Supplement requirement").strip()
    if not title:
        raise ValueError("Requirement title is required.")
    requirement_type = str(requirement.get("requirement_type") or (existing or {}).get("requirement_type") or "other")
    if requirement_type not in SUPPLEMENT_REQUIREMENT_TYPES:
        raise ValueError("Unknown supplement requirement type.")
    enforcement = str(requirement.get("enforcement") or (existing or {}).get("enforcement") or "information")
    if enforcement not in SUPPLEMENT_REQUIREMENT_ENFORCEMENT:
        raise ValueError("Unknown supplement requirement enforcement mode.")
    party_scope = str(requirement.get("party_scope") or "all")
    if party_scope not in {"all", "any", "none"}:
        party_scope = "all"
    if existing is None:
        base_id = supplement_package_id(title, f"requirement-{len(requirements) + 1}")
        next_id = base_id
        suffix = 2
        known_ids = {str(item.get("id") or "") for item in requirements}
        while next_id in known_ids:
            next_id = f"{base_id}-{suffix}"
            suffix += 1
        existing = {
            "id": next_id,
            "exact_text": str(requirement.get("exact_text") or ""),
            "source_id": str(requirement.get("source_id") or ""),
            "source_pdf": str(requirement.get("source_pdf") or ""),
            "source_block_id": str(requirement.get("source_block_id") or ""),
            "source_page": requirement.get("source_page"),
            "pdf_page": requirement.get("pdf_page"),
            "page_label": str(requirement.get("page_label") or ""),
        }
        requirements.append(existing)
    existing.update(
        {
            "title": title,
            "requirement_type": requirement_type,
            "enforcement": enforcement,
            "party_scope": party_scope,
            "minimum_party_level": max(0, int(requirement.get("minimum_party_level") or 0)),
            "trigger": str(requirement.get("trigger") or ""),
            "environment": str(requirement.get("environment") or ""),
            "required_supplement_ids": _clean_string_list(requirement.get("required_supplement_ids")),
            "replacement_tables": _clean_string_list(requirement.get("replacement_tables")),
            "retained_tables": _clean_string_list(requirement.get("retained_tables")),
            "interpretation": str(requirement.get("interpretation") or ""),
            "review_status": str(requirement.get("review_status") or "draft"),
        }
    )
    package["requirements"] = requirements
    packages[safe_package_id] = package
    _write_source_settings(data_dir, payload)
    return {"requirement": existing, "message": "Supplement requirement saved."}


def delete_supplement_package_requirement(data_dir: Path, package_id: str, requirement_id: str) -> dict[str, Any]:
    payload = _load_source_settings(data_dir)
    packages = _package_settings(payload)
    safe_package_id = supplement_package_id(package_id, "supplement-package")
    package = packages.get(safe_package_id) if isinstance(packages.get(safe_package_id), dict) else None
    if package is None:
        raise KeyError(package_id)
    requirements = [item for item in package.get("requirements", []) if isinstance(item, dict)]
    kept = [item for item in requirements if str(item.get("id") or "") != requirement_id]
    if len(kept) == len(requirements):
        raise KeyError(requirement_id)
    package["requirements"] = kept
    packages[safe_package_id] = package
    _write_source_settings(data_dir, payload)
    return {"requirement_id": requirement_id, "message": "Supplement requirement deleted."}


def add_supplement_package_asset(
    data_dir: Path,
    *,
    filename: str,
    data: bytes,
    content_type: str,
    supplement_id: str | None,
    supplement_title: str | None,
    asset_kind: str = "map_or_image",
    title: str = "",
    category: str = "unknown",
    notes: str = "",
    parent_asset_id: str = "",
    now: str = "",
) -> dict[str, Any]:
    clean_name = Path(str(filename or "")).name.strip()
    if not clean_name:
        raise ValueError("Missing source asset filename.")
    package = upsert_supplement_package(data_dir, supplement_id=supplement_id, supplement_title=supplement_title, fallback=Path(clean_name).stem)
    package_id = str(package.get("supplement_id") or supplement_package_id(None, Path(clean_name).stem))
    asset_dir = supplement_package_asset_dir(data_dir, package_id)
    asset_dir.mkdir(parents=True, exist_ok=True)
    target = (asset_dir / clean_name).resolve()
    if not target.is_relative_to(asset_dir.resolve()):
        raise ValueError("Invalid source asset filename.")
    target.write_bytes(data)

    payload = _load_source_settings(data_dir)
    packages = _package_settings(payload)
    stored_package = packages.get(package_id) if isinstance(packages.get(package_id), dict) else dict(package)
    assets = stored_package.get("assets") if isinstance(stored_package.get("assets"), list) else []
    previous = next((item for item in assets if isinstance(item, dict) and item.get("filename") == clean_name), {})
    asset_id = supplement_package_id(Path(clean_name).stem, "asset")
    clean_category = str(category or previous.get("category") or "unknown")
    if clean_category not in SUPPLEMENT_PACKAGE_ASSET_CATEGORIES:
        clean_category = "unknown"
    record = {
        **previous,
        "id": asset_id,
        "filename": clean_name,
        "asset_kind": str(asset_kind or "map_or_image"),
        "title": str(title or previous.get("title") or Path(clean_name).stem).strip() or Path(clean_name).stem,
        "category": clean_category,
        "review_status": str(previous.get("review_status") or "unreviewed"),
        "content_type": str(content_type or ""),
        "size_bytes": len(data),
        "updated_at": now,
        "asset_url": f"/api/supplements/source-packages/{package_id}/assets/{clean_name}",
        "notes": str(notes or previous.get("notes") or ""),
        "parent_asset_id": str(parent_asset_id or previous.get("parent_asset_id") or ""),
    }
    next_assets = [item for item in assets if not isinstance(item, dict) or item.get("filename") != clean_name]
    next_assets.append(record)
    stored_package.update(
        {
            "supplement_id": package_id,
            "supplement_title": str(package.get("supplement_title") or package_id),
            "assets": next_assets,
        }
    )
    packages[package_id] = stored_package
    _write_source_settings(data_dir, payload)
    return {
        "supplement_id": package_id,
        "supplement_title": stored_package["supplement_title"],
        "asset": record,
        "path": str(target),
        "message": f"Imported {clean_name} into supplement package {stored_package['supplement_title']}.",
    }


def update_supplement_package_asset(data_dir: Path, package_id: str, asset_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    payload = _load_source_settings(data_dir)
    packages = _package_settings(payload)
    safe_package_id = supplement_package_id(package_id, "supplement-package")
    package = packages.get(safe_package_id) if isinstance(packages.get(safe_package_id), dict) else None
    if package is None:
        raise KeyError(package_id)
    assets = package.get("assets") if isinstance(package.get("assets"), list) else []
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("id") != asset_id:
            continue
        if "title" in changes:
            asset["title"] = str(changes.get("title") or "").strip()
        if "category" in changes:
            category = str(changes.get("category") or "unknown")
            asset["category"] = category if category in SUPPLEMENT_PACKAGE_ASSET_CATEGORIES else "unknown"
        if "review_status" in changes:
            asset["review_status"] = str(changes.get("review_status") or "unreviewed")
        if "asset_kind" in changes:
            asset["asset_kind"] = str(changes.get("asset_kind") or "map_or_image")
        if "notes" in changes:
            asset["notes"] = str(changes.get("notes") or "")
        package["assets"] = assets
        packages[safe_package_id] = package
        _write_source_settings(data_dir, payload)
        return {"asset": asset, "message": "Package source asset saved."}
    raise KeyError(asset_id)


def delete_supplement_package_asset(data_dir: Path, package_id: str, asset_id: str) -> dict[str, Any]:
    payload = _load_source_settings(data_dir)
    packages = _package_settings(payload)
    safe_package_id = supplement_package_id(package_id, "supplement-package")
    package = packages.get(safe_package_id) if isinstance(packages.get(safe_package_id), dict) else None
    if package is None:
        raise KeyError(package_id)
    assets = package.get("assets") if isinstance(package.get("assets"), list) else []
    kept: list[dict[str, Any]] = []
    removed: dict[str, Any] | None = None
    for asset in assets:
        if isinstance(asset, dict) and asset.get("id") == asset_id:
            removed = asset
            continue
        if isinstance(asset, dict):
            kept.append(asset)
    if removed is None:
        raise KeyError(asset_id)
    filename = str(removed.get("filename") or "")
    if filename:
        path = supplement_package_asset_path(data_dir, safe_package_id, filename)
        base = supplement_package_asset_dir(data_dir, safe_package_id).resolve()
        try:
            resolved = path.resolve()
            if resolved.is_relative_to(base) and resolved.is_file():
                resolved.unlink()
        except OSError:
            pass
    package["assets"] = kept
    packages[safe_package_id] = package
    _write_source_settings(data_dir, payload)
    return {"asset_id": asset_id, "message": "Package source asset deleted."}


def _page_text_blocks(text: str) -> list[str]:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", raw) if block.strip()]
    if len(blocks) <= 1:
        blocks = [block.strip() for block in raw.splitlines() if block.strip()]
    return blocks


def _source_block_id(source_id: str, source_page: int, pdf_page: int, index: int) -> str:
    if source_page == pdf_page:
        return f"{source_id}-p{source_page}-b{index:03d}"
    return f"{source_id}-p{source_page}-pdf{pdf_page}-b{index:03d}"


def _review_blocks_from_existing(existing: dict[str, Any]) -> list[dict[str, Any]]:
    reviewed = existing.get("reviewed_blocks")
    if isinstance(reviewed, list) and reviewed:
        return [block for block in reviewed if isinstance(block, dict)]
    blocks = existing.get("blocks")
    if isinstance(blocks, list):
        return [block for block in blocks if isinstance(block, dict)]
    return []


def _review_artwork_from_existing(existing: dict[str, Any]) -> list[dict[str, Any]]:
    reviewed = existing.get("reviewed_artwork")
    if isinstance(reviewed, list) and reviewed:
        return [item for item in reviewed if isinstance(item, dict)]
    raw = existing.get("raw_artwork")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _review_tables_from_existing(existing: dict[str, Any]) -> list[dict[str, Any]]:
    reviewed = existing.get("reviewed_tables")
    if isinstance(reviewed, list):
        return [item for item in reviewed if isinstance(item, dict)]
    tables = existing.get("tables")
    if isinstance(tables, list):
        return [item for item in tables if isinstance(item, dict)]
    return []


def _review_foes_from_existing(existing: dict[str, Any]) -> list[dict[str, Any]]:
    foes = existing.get("reviewed_foes")
    if isinstance(foes, list):
        return [item for item in foes if isinstance(item, dict)]
    return []


def _review_profiles_from_existing(existing: dict[str, Any], profile_type: str) -> list[dict[str, Any]]:
    collection = SUPPLEMENT_PROFILE_COLLECTIONS.get(profile_type)
    if not collection:
        return []
    if profile_type == "foe":
        return _review_foes_from_existing(existing)
    profiles = existing.get(collection)
    return [item for item in profiles if isinstance(item, dict)] if isinstance(profiles, list) else []


def _profile_id(source_id: str, profile_type: str, name: str, source_block_id: str = "") -> str:
    return supplement_package_id(f"{source_id}-{profile_type}-{name or source_block_id}", f"provisional-{profile_type}")


def draft_supplement_source_profile(data_dir: Path, source_id: str, block_id: str, profile_type: str = "") -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    block = next((item for item in payload.get("reviewed_blocks", []) if isinstance(item, dict) and item.get("id") == block_id), None)
    if block is None:
        raise KeyError(block_id)
    resolved_type = str(profile_type or block.get("assignment") or "")
    if resolved_type not in SUPPLEMENT_PROFILE_TYPES:
        raise ValueError("Assign this source block as Foe, Mount, Companion Animal, Character Class, or Location before creating its profile.")
    first_line = next((line.strip() for line in str(block.get("text") or "").splitlines() if line.strip()), "")
    name = str(block.get("title") or first_line or "").strip()[:160]
    profile = {
        "id": _profile_id(source_id, resolved_type, name, block_id),
        "profile_type": resolved_type,
        "name": name,
        "source_block_id": block_id,
        "source_pdf": str(block.get("source_pdf") or payload.get("source_pdf") or ""),
        "source_page": block.get("source_page"),
        "pdf_page": block.get("pdf_page"),
        "page_label": str(block.get("page_label") or ""),
        "exact_source_text": str(block.get("text") or ""),
        "description": "",
        "special_rules": "",
        "modifiers": [],
        "states_inflicted": [],
        "weaknesses": [],
        "reaction_table_id": "",
        "reaction_rows": [],
        "location_type": "location",
        "foe_ids": [],
        "foe_table_id": "",
        "treasure_text": "",
        "treasure_table_id": "",
        "trap_text": "",
        "trap_procedure_id": "",
        "exits": [],
        "friendly_npcs": [],
        "quests": [],
        "map_id": "",
        "map_pin_id": "",
        "room_tile_id": "",
        "portrait_artwork_id": "",
        "review_status": "draft",
        "notes": "",
    }
    return {"profile": profile, "profile_descriptions": SUPPLEMENT_PROFILE_DESCRIPTIONS, "message": f"Drafted {resolved_type.replace('_', ' ')} profile from source block."}


def upsert_supplement_source_profile(data_dir: Path, source_id: str, profile_type: str, profile_payload: dict[str, Any]) -> dict[str, Any]:
    resolved_type = str(profile_type or profile_payload.get("profile_type") or "")
    if resolved_type not in SUPPLEMENT_PROFILE_TYPES:
        raise ValueError("Unknown provisional profile type.")
    payload = load_supplement_source_scan(data_dir, source_id)
    name = str(profile_payload.get("name") or "").strip()
    if not name:
        raise ValueError("Enter a profile name before saving.")
    profile_id = str(profile_payload.get("id") or _profile_id(source_id, resolved_type, name, str(profile_payload.get("source_block_id") or ""))).strip()
    profile = {
        "id": profile_id,
        "profile_type": resolved_type,
        "name": name,
        "source_block_id": str(profile_payload.get("source_block_id") or ""),
        "source_pdf": str(profile_payload.get("source_pdf") or payload.get("source_pdf") or ""),
        "source_page": profile_payload.get("source_page"),
        "pdf_page": profile_payload.get("pdf_page"),
        "page_label": str(profile_payload.get("page_label") or ""),
        "exact_source_text": str(profile_payload.get("exact_source_text") or ""),
        "description": str(profile_payload.get("description") or ""),
        "special_rules": str(profile_payload.get("special_rules") or ""),
        "modifiers": _clean_profile_modifiers(profile_payload.get("modifiers")),
        "states_inflicted": _clean_string_list(profile_payload.get("states_inflicted")),
        "weaknesses": _clean_string_list(profile_payload.get("weaknesses")),
        "reaction_table_id": str(profile_payload.get("reaction_table_id") or ""),
        "reaction_rows": _clean_location_lines(profile_payload.get("reaction_rows"), ("roll", "key", "result", "exact_text")),
        "level": str(profile_payload.get("level") or ""),
        "attack": str(profile_payload.get("attack") or ""),
        "defense": str(profile_payload.get("defense") or ""),
        "category": str(profile_payload.get("category") or ""),
        "quantity_expression": str(profile_payload.get("quantity_expression") or ""),
        "riding_requirements": str(profile_payload.get("riding_requirements") or ""),
        "movement": str(profile_payload.get("movement") or ""),
        "carrying_capacity": str(profile_payload.get("carrying_capacity") or ""),
        "owner_training": str(profile_payload.get("owner_training") or ""),
        "eligibility": str(profile_payload.get("eligibility") or ""),
        "abilities": _clean_string_list(profile_payload.get("abilities")),
        "progression": str(profile_payload.get("progression") or ""),
        "equipment_restrictions": str(profile_payload.get("equipment_restrictions") or ""),
        "location_type": str(profile_payload.get("location_type") or "location"),
        "foe_ids": _clean_string_list(profile_payload.get("foe_ids")),
        "foe_table_id": str(profile_payload.get("foe_table_id") or ""),
        "treasure_text": str(profile_payload.get("treasure_text") or ""),
        "treasure_table_id": str(profile_payload.get("treasure_table_id") or ""),
        "trap_text": str(profile_payload.get("trap_text") or ""),
        "trap_procedure_id": str(profile_payload.get("trap_procedure_id") or ""),
        "exits": _clean_location_lines(profile_payload.get("exits"), ("label", "to_location_id", "condition", "exact_text")),
        "friendly_npcs": _clean_location_lines(profile_payload.get("friendly_npcs"), ("name", "role", "offers", "linked_ids", "exact_text")),
        "quests": _clean_location_lines(profile_payload.get("quests"), ("giver", "quest_or_procedure_id", "exact_text")),
        "map_id": str(profile_payload.get("map_id") or ""),
        "map_pin_id": str(profile_payload.get("map_pin_id") or ""),
        "room_tile_id": str(profile_payload.get("room_tile_id") or ""),
        "portrait_artwork_id": str(profile_payload.get("portrait_artwork_id") or ""),
        "review_status": str(profile_payload.get("review_status") or "provisional"),
        "notes": str(profile_payload.get("notes") or ""),
    }
    collection = SUPPLEMENT_PROFILE_COLLECTIONS[resolved_type]
    profiles = _review_profiles_from_existing(payload, resolved_type)
    next_profiles = [item for item in profiles if str(item.get("id") or "") != profile_id]
    next_profiles.append(profile)
    payload[collection] = next_profiles
    save_supplement_source_scan(data_dir, source_id, payload)
    return {"profile": profile, "message": f"Saved provisional {resolved_type.replace('_', ' ')} profile {name}."}


def _table_id_from_title(source_id: str, title: str, block_id: str = "") -> str:
    base = re.sub(r"[^a-z0-9]+", "_", str(title or "").lower()).strip("_")
    if not base:
        base = re.sub(r"[^a-z0-9]+", "_", str(block_id or "").lower()).strip("_")
    if not base:
        base = "reviewed_table"
    prefix = re.sub(r"[^a-z0-9]+", "_", str(source_id or "source").lower()).strip("_") or "source"
    return f"{prefix}_{base}_table"


def _clean_table_title(text: str, fallback: str) -> str:
    for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines():
        clean = line.strip(" :-\t")
        if clean:
            return clean[:120]
    return fallback


def _parse_table_rows(text: str) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    unmatched: list[str] = []
    row_pattern = re.compile(
        r"^\s*(?P<key>(?:d?\d{1,3}|[A-Z])(?:\s*[-\u2013\u2014]\s*(?:d?\d{1,3}|[A-Z]))?|\d{1,2}[.)])\s+[:.)-]?\s*(?P<result>.+?)\s*$",
        re.IGNORECASE,
    )
    for raw_line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = row_pattern.match(line)
        if match:
            pending = {
                "key": re.sub(r"\s+", "", match.group("key").rstrip(".)")),
                "result": match.group("result").strip(),
                "notes": "",
            }
            rows.append(pending)
        elif pending:
            pending["result"] = f"{pending.get('result') or ''} {line}".strip()
        else:
            unmatched.append(line)
    status = "parsed" if rows else "manual_entry_needed"
    if unmatched and rows:
        status = "parsed_with_unmatched_header"
    return rows, status


def _source_table_text(text: Any) -> str:
    """Remove obvious PDF footer residue while retaining wording for row review."""
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in raw.splitlines()]
    kept = [line for line in lines if line and not re.fullmatch(r"\d{1,3}", line)]
    return re.sub(r"\s+", " ", " ".join(kept)).strip()


def _foe_encounter_row_candidates(text: Any) -> list[dict[str, Any]]:
    source = _source_table_text(text)
    # Foe encounter tables normally begin every result with a compact roll marker
    # followed by a quantity expression (for example, "2 d6+1 Imps").  Requiring
    # that quantity keeps prose such as "2 wolves" from becoming a false row.
    marker = re.compile(r"(?<![A-Za-z0-9])(?P<roll>[1-6])\s+(?=(?:(?:\d+)?d\d+(?:[+-]\d+)?|\d+d\d+|\d+)\s+[A-Z])")
    matches = list(marker.finditer(source))
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        exact_text = source[start:end].strip()
        exact_text = re.sub(r"\s+\*\s*If you get the same result.*$", "", exact_text, flags=re.IGNORECASE).strip()
        if not exact_text:
            continue
        detail = exact_text[len(match.group("roll")) :].strip()
        intro = re.match(
            r"(?P<quantity>(?:(?:\d+)?d\d+(?:[+-]\d+)?|\d+))\s+(?P<name>.+?)\.\s*Level\s+(?P<level>\d+)(?P<after>.*)$",
            detail,
            flags=re.IGNORECASE,
        )
        quantity = intro.group("quantity") if intro else ""
        name = intro.group("name").strip() if intro else ""
        level = intro.group("level") if intro else ""
        after = intro.group("after").strip() if intro else detail
        first_clause = re.split(r"[.;]", after, maxsplit=1)[0].strip(" ,")
        category = ""
        if first_clause:
            category = re.sub(r"^(?:flying|undead|demonic|rattish|hellspawn|minor|major)\s+", "", first_clause, flags=re.IGNORECASE).strip()
            category = category.split(",")[0].strip()
        rows.append(
            {
                "roll": match.group("roll"),
                "foe_name": name,
                "description": "",
                "quantity": quantity,
                "level": level,
                "attack": "",
                "defense": "",
                "category": category,
                "states_inflicted": [],
                "weaknesses": [],
                "special_rules": after,
                "modifiers": [],
                "exact_text": exact_text,
                "notes": "Imported candidate. Check every field against the exact source wording.",
            }
        )
    return rows


def suggest_supplement_source_table_rows(data_dir: Path, source_id: str, block_id: str, table_type: str = "reference_lookup") -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    block = next((item for item in payload.get("reviewed_blocks", []) if isinstance(item, dict) and item.get("id") == block_id), None)
    if block is None:
        raise KeyError(block_id)
    resolved_type = _table_type(table_type)
    text = str(block.get("text") or "")
    if resolved_type == "foe_encounter":
        rows = _foe_encounter_row_candidates(text)
        method = "foe encounter roll/quantity markers"
    else:
        parsed, _status = _parse_table_rows(text)
        rows = [_clean_reference_table_row(row) for row in parsed]
        method = "line-start roll markers"
    return {
        "rows": rows,
        "table_type": resolved_type,
        "source_block_id": block_id,
        "method": method,
        "message": f"Found {len(rows)} candidate row(s) using {method}. Review every imported field against the exact source text.",
    }


def _table_type(value: Any) -> str:
    candidate = str(value or "reference_lookup").strip()
    return candidate if candidate in SUPPLEMENT_TABLE_TYPES else "reference_lookup"


def _clean_profile_modifiers(value: Any) -> list[dict[str, str]]:
    raw_items = value if isinstance(value, list) else str(value or "").splitlines()
    modifiers: list[dict[str, str]] = []
    for raw in raw_items:
        if isinstance(raw, dict):
            target = str(raw.get("target") or "Other").strip() or "Other"
            adjustment = str(raw.get("adjustment") or "").strip()
            scope = str(raw.get("scope") or "").strip()
            exact_text = str(raw.get("exact_text") or "").strip()
        else:
            parts = [part.strip() for part in str(raw or "").split("|")]
            if not any(parts):
                continue
            target, adjustment, scope, exact_text = (parts + ["", "", "", ""])[:4]
            target = target or "Other"
            exact_text = exact_text or str(raw).strip()
        modifiers.append({"target": target, "adjustment": adjustment, "scope": scope, "exact_text": exact_text})
    return modifiers


def _clean_location_lines(value: Any, fields: tuple[str, ...]) -> list[dict[str, str]]:
    raw_items = value if isinstance(value, list) else str(value or "").splitlines()
    records: list[dict[str, str]] = []
    for raw in raw_items:
        if isinstance(raw, dict):
            record = {field: str(raw.get(field) or "").strip() for field in fields}
        else:
            parts = [part.strip() for part in str(raw or "").split("|")]
            if not any(parts):
                continue
            record = {field: part for field, part in zip(fields, parts, strict=False)}
            for field in fields:
                record.setdefault(field, "")
        if any(record.values()):
            records.append(record)
    return records


def _clean_foe_encounter_row(row: dict[str, Any]) -> dict[str, Any]:
    states = _clean_string_list(row.get("states_inflicted"))
    weaknesses = _clean_string_list(row.get("weaknesses"))
    roll = str(row.get("roll") or row.get("key") or "").strip()
    exact_text = str(row.get("exact_text") or row.get("result") or "").strip()
    return {
        "roll": roll,
        "foe_name": str(row.get("foe_name") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "quantity": str(row.get("quantity") or "").strip(),
        "level": str(row.get("level") or "").strip(),
        "attack": str(row.get("attack") or "").strip(),
        "defense": str(row.get("defense") or "").strip(),
        "category": str(row.get("category") or "").strip(),
        "states_inflicted": states,
        "weaknesses": weaknesses,
        "reaction_table_id": str(row.get("reaction_table_id") or "").strip(),
        "reaction_rows": _clean_location_lines(row.get("reaction_rows"), ("roll", "key", "result", "exact_text")),
        "special_rules": str(row.get("special_rules") or "").strip(),
        "modifiers": _clean_profile_modifiers(row.get("modifiers")),
        "exact_text": exact_text,
        "notes": str(row.get("notes") or "").strip(),
    }


def _clean_reference_table_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "roll": str(row.get("roll") or row.get("key") or "").strip(),
        "outcome": str(row.get("outcome") or row.get("result") or "").strip(),
        "exact_text": str(row.get("exact_text") or row.get("result") or "").strip(),
        "notes": str(row.get("notes") or "").strip(),
    }


def _provisional_foes_from_table(table: dict[str, Any]) -> list[dict[str, Any]]:
    if _table_type(table.get("table_type")) != "foe_encounter":
        return []
    foes: list[dict[str, Any]] = []
    for row in table.get("rows", []):
        if not isinstance(row, dict):
            continue
        name = str(row.get("foe_name") or "").strip()
        # A profile is only created once the combat essentials are actually reviewed.
        if not name or not all(str(row.get(field) or "").strip() for field in ("level", "attack", "defense")):
            continue
        foe_id = supplement_package_id(f"{table.get('id')}-{name}", "provisional-foe")
        foes.append(
            {
                "id": foe_id,
                "name": name,
                "description": str(row.get("description") or "").strip(),
                "level": str(row.get("level") or "").strip(),
                "attack": str(row.get("attack") or "").strip(),
                "defense": str(row.get("defense") or "").strip(),
                "category": str(row.get("category") or "").strip(),
                "states_inflicted": list(row.get("states_inflicted") or []),
                "weaknesses": list(row.get("weaknesses") or []),
                "reaction_table_id": str(row.get("reaction_table_id") or "").strip(),
                "reaction_rows": list(row.get("reaction_rows") or []),
                "special_rules": str(row.get("special_rules") or "").strip(),
                "modifiers": list(row.get("modifiers") or []),
                "quantity_expression": str(row.get("quantity") or "").strip(),
                "exact_source_text": str(row.get("exact_text") or "").strip(),
                "source_table_id": str(table.get("id") or ""),
                "source_row_roll": str(row.get("roll") or "").strip(),
                "source_block_id": str(table.get("source_block_id") or ""),
                "source_pdf": str(table.get("source_pdf") or ""),
                "source_page": table.get("source_page"),
                "pdf_page": table.get("pdf_page"),
                "page_label": str(table.get("page_label") or ""),
                "review_status": "provisional",
                "notes": "Created automatically from a reviewed Foe Encounter table row; validate against the PDF before activation.",
            }
        )
    return foes


def draft_supplement_source_table(data_dir: Path, source_id: str, block_id: str, changes: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = payload.get("reviewed_blocks", [])
    block = next((item for item in blocks if isinstance(item, dict) and item.get("id") == block_id), None)
    if block is None:
        raise KeyError(block_id)
    changes = changes or {}
    title = str(changes.get("title") or _clean_table_title(str(block.get("text") or ""), str(block.get("page_label") or "Reviewed table"))).strip()
    table_id = str(changes.get("table_id") or _table_id_from_title(source_id, title, block_id)).strip()
    rows, parser_status = _parse_table_rows(str(block.get("text") or ""))
    table = {
        "id": table_id,
        "title": title,
        "source_block_id": block_id,
        "source_pdf": str(block.get("source_pdf") or payload.get("source_pdf") or ""),
        "source_page": block.get("source_page"),
        "pdf_page": block.get("pdf_page"),
        "page_label": str(block.get("page_label") or ""),
        "assignment": "table",
        "table_type": _table_type(changes.get("table_type")),
        "roll_expression": str(changes.get("roll_expression") or "").strip(),
        "columns": ["roll", "outcome", "exact_text", "notes"],
        "rows": rows,
        "parser_status": parser_status,
        "review_status": "draft",
        "notes": str(changes.get("notes") or ""),
    }
    return {"table": table, "message": f"Drafted {len(rows)} table row(s) from source block."}


def upsert_supplement_source_table(data_dir: Path, source_id: str, table_payload: dict[str, Any]) -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    table_id = str(table_payload.get("id") or "").strip()
    if not table_id:
        table_id = _table_id_from_title(source_id, str(table_payload.get("title") or ""), str(table_payload.get("source_block_id") or ""))
    table_type = _table_type(table_payload.get("table_type"))
    rows = table_payload.get("rows") if isinstance(table_payload.get("rows"), list) else []
    clean_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        clean_row = _clean_foe_encounter_row(row) if table_type == "foe_encounter" else _clean_reference_table_row(row)
        if not any(str(value or "").strip() for value in clean_row.values() if not isinstance(value, list)) and not any(clean_row.get(key) for key in ("states_inflicted", "weaknesses")):
            continue
        clean_rows.append(clean_row)
    table = {
        "id": table_id,
        "title": str(table_payload.get("title") or table_id).strip(),
        "source_block_id": str(table_payload.get("source_block_id") or ""),
        "source_pdf": str(table_payload.get("source_pdf") or payload.get("source_pdf") or ""),
        "source_page": table_payload.get("source_page"),
        "pdf_page": table_payload.get("pdf_page"),
        "page_label": str(table_payload.get("page_label") or ""),
        "assignment": "table",
        "table_type": table_type,
        "roll_expression": str(table_payload.get("roll_expression") or "").strip(),
        "columns": ["roll", "foe_name", "description", "quantity", "level", "attack", "defense", "category", "states_inflicted", "weaknesses", "reaction_table_id", "reaction_rows", "modifiers", "special_rules", "exact_text", "notes"] if table_type == "foe_encounter" else ["roll", "outcome", "exact_text", "notes"],
        "rows": clean_rows,
        "parser_status": str(table_payload.get("parser_status") or "manual_reviewed"),
        "review_status": str(table_payload.get("review_status") or "reviewed"),
        "notes": str(table_payload.get("notes") or ""),
    }
    tables = _review_tables_from_existing(payload)
    replaced = False
    for index, existing in enumerate(tables):
        if str(existing.get("id") or "") == table_id:
            tables[index] = table
            replaced = True
            break
    if not replaced:
        tables.append(table)
    payload["reviewed_tables"] = tables
    generated_foes = _provisional_foes_from_table(table)
    existing_foes = [
        foe
        for foe in _review_foes_from_existing(payload)
        if str(foe.get("source_table_id") or "") != table_id
    ]
    payload["reviewed_foes"] = existing_foes + generated_foes
    save_supplement_source_scan(data_dir, source_id, payload)
    return {
        "table": table,
        "provisional_foes": generated_foes,
        "message": f"Saved reviewed table {table_id} with {len(clean_rows)} row(s) and {len(generated_foes)} provisional foe profile(s).",
    }


def scan_supplement_source_pdf(
    data_dir: Path,
    pdf_path: Path,
    *,
    now: str,
    page_offset: int = 0,
    supplement_id: str | None = None,
    supplement_title: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    source_settings = set_pdf_source_metadata(
        data_dir,
        pdf_path,
        page_offset=page_offset,
        supplement_id=supplement_id,
        supplement_title=supplement_title,
    )
    source_id = supplement_source_id(pdf_path)
    package_id = supplement_package_id(source_settings.get("supplement_id"), source_id)
    package_title = str(source_settings.get("supplement_title") or pdf_path.stem)
    folder = supplement_source_folder(data_dir, source_id)
    folder.mkdir(parents=True, exist_ok=True)
    existing = load_supplement_source_scan(data_dir, source_id)
    existing_by_text: dict[tuple[int, str], dict[str, Any]] = {}
    existing_reviewed_blocks = _review_blocks_from_existing(existing)
    for block in existing_reviewed_blocks:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "")
        pdf_page = int(block.get("pdf_page") or block.get("source_page") or 0)
        existing_by_text[(pdf_page, text)] = block
    raw_blocks: list[dict[str, Any]] = []
    blocks_by_pdf_page: dict[int, list[dict[str, Any]]] = {}
    pages = extract_rule_pdf_pages(pdf_path)
    for page in pages:
        page_no = int(page.get("page") or 0)
        source_page = display_page_number(page_no, page_offset)
        methods = list(page.get("methods") or [])
        review_blocks = page.get("review_blocks") if isinstance(page.get("review_blocks"), list) else []
        text_blocks = [str(text).strip() for text in review_blocks if str(text).strip()] or _page_text_blocks(str(page.get("text") or ""))
        if review_blocks:
            methods = [*methods, "positioned_sections"]
        for index, text in enumerate(text_blocks, start=1):
            previous = existing_by_text.get((page_no, text), {})
            assignment = str(previous.get("assignment") or "unassigned")
            if assignment not in SOURCE_BLOCK_ASSIGNMENTS:
                assignment = "unassigned"
            block = {
                "id": _source_block_id(source_id, source_page, page_no, index),
                "supplement_id": package_id,
                "supplement_title": package_title,
                "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
                "source_page": source_page,
                "pdf_page": page_no,
                "page_offset": int(page_offset),
                "page_label": page_label(page_no, page_offset),
                "block_index": index,
                "assignment": assignment,
                "review_status": str(previous.get("review_status") or "unreviewed"),
                "text": text,
                "extraction_methods": methods,
                "notes": str(previous.get("notes") or ""),
            }
            raw_blocks.append(block)
            blocks_by_pdf_page.setdefault(page_no, []).append(block)
    continuation_candidates: list[dict[str, Any]] = []
    for left_page, right_page in zip(sorted(blocks_by_pdf_page), sorted(blocks_by_pdf_page)[1:]):
        if right_page != left_page + 1:
            continue
        left_blocks = blocks_by_pdf_page.get(left_page) or []
        right_blocks = blocks_by_pdf_page.get(right_page) or []
        if not left_blocks or not right_blocks:
            continue
        left = left_blocks[-1]
        right = right_blocks[0]
        left_source = int(left.get("source_page") or left_page)
        right_source = int(right.get("source_page") or right_page)
        continuation_candidates.append(
            {
                "id": f"{source_id}-p{left_source}-to-p{right_source}-pdf{left_page}-to-pdf{right_page}",
                "supplement_id": package_id,
                "supplement_title": package_title,
                "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
                "source_page": left_source,
                "source_page_end": right_source,
                "pdf_page": left_page,
                "pdf_page_end": right_page,
                "page_offset": int(page_offset),
                "page_label": f"{page_label(left_page, page_offset)} to {page_label(right_page, page_offset)}",
                "block_ids": [left.get("id"), right.get("id")],
                "assignment": "page_boundary_candidate",
                "review_status": "candidate",
                "text": f"{left.get('text') or ''}\n\n{right.get('text') or ''}".strip(),
                "extraction_methods": ["page_boundary_candidate"],
                "notes": "Possible page-spanning text. Review before assigning or copying into a supplement.",
            }
        )
    reviewed_blocks = [dict(block) for block in raw_blocks] if overwrite else existing_reviewed_blocks or [dict(block) for block in raw_blocks]
    payload = {
        "schema_version": 1,
        "source_id": source_id,
        "supplement_id": package_id,
        "supplement_title": package_title,
        "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
        "updated_at": now,
        "page_offset": int(page_offset),
        "note": "Local/private PDF source blocks for human review and supplement assignment. Exact text remains in DATA_DIR. Re-scans update raw_blocks; reviewed_blocks preserve human edits unless overwrite is requested.",
        "assignment_options": sorted(SOURCE_BLOCK_ASSIGNMENTS),
        "assignment_descriptions": SOURCE_BLOCK_ASSIGNMENT_DESCRIPTIONS,
        "artwork_categories": sorted(SOURCE_ARTWORK_CATEGORIES),
        "raw_blocks": raw_blocks,
        "reviewed_blocks": reviewed_blocks,
        "blocks": reviewed_blocks,
        "continuation_candidates": continuation_candidates,
        "raw_artwork": existing.get("raw_artwork", []),
        "reviewed_artwork": _review_artwork_from_existing(existing),
        "reviewed_tables": _review_tables_from_existing(existing),
        "reviewed_foes": _review_foes_from_existing(existing),
        "reviewed_mounts": _review_profiles_from_existing(existing, "mount"),
        "reviewed_companion_animals": _review_profiles_from_existing(existing, "companion_animal"),
        "reviewed_character_classes": _review_profiles_from_existing(existing, "character_class"),
    }
    supplement_source_scan_path(data_dir, source_id).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "source_id": source_id,
        "supplement_id": package_id,
        "supplement_title": package_title,
        "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
        "blocks": len(reviewed_blocks),
        "raw_blocks": len(raw_blocks),
        "overwrite": bool(overwrite),
        "continuation_candidates": len(continuation_candidates),
        "pages": len(pages),
        "page_offset": int(page_offset),
        "path": str(supplement_source_scan_path(data_dir, source_id)),
        "message": (
            f"Scanned {len(raw_blocks)} raw block(s), "
            f"{'rebuilt' if overwrite else 'preserved'} {len(reviewed_blocks)} reviewed block(s), "
            f"and found {len(continuation_candidates)} page-boundary candidate(s) from {pdf_path.name}."
        ),
    }


def load_supplement_source_scan(data_dir: Path, source_id: str) -> dict[str, Any]:
    path = supplement_source_scan_path(data_dir, source_id)
    if not path.exists():
        return {"schema_version": 1, "source_id": source_id, "blocks": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "source_id": source_id, "blocks": []}
    if not isinstance(payload, dict):
        return {"schema_version": 1, "source_id": source_id, "blocks": []}
    payload["supplement_id"] = str(payload.get("supplement_id") or supplement_package_id(None, source_id))
    payload["supplement_title"] = str(payload.get("supplement_title") or payload.get("source_pdf") or source_id)
    reviewed = _review_blocks_from_existing(payload)
    reviewed_artwork = _review_artwork_from_existing(payload)
    reviewed_tables = _review_tables_from_existing(payload)
    reviewed_foes = _review_foes_from_existing(payload)
    reviewed_mounts = _review_profiles_from_existing(payload, "mount")
    reviewed_companion_animals = _review_profiles_from_existing(payload, "companion_animal")
    reviewed_character_classes = _review_profiles_from_existing(payload, "character_class")
    reviewed_locations = _review_profiles_from_existing(payload, "location")
    payload["reviewed_blocks"] = reviewed
    payload["blocks"] = reviewed
    payload["reviewed_artwork"] = reviewed_artwork
    payload["artwork"] = reviewed_artwork
    payload["reviewed_tables"] = reviewed_tables
    payload["tables"] = reviewed_tables
    payload["reviewed_foes"] = reviewed_foes
    payload["foes"] = reviewed_foes
    payload["reviewed_mounts"] = reviewed_mounts
    payload["mounts"] = reviewed_mounts
    payload["reviewed_companion_animals"] = reviewed_companion_animals
    payload["companion_animals"] = reviewed_companion_animals
    payload["reviewed_character_classes"] = reviewed_character_classes
    payload["character_classes"] = reviewed_character_classes
    payload["reviewed_locations"] = reviewed_locations
    payload["locations"] = reviewed_locations
    if "raw_blocks" not in payload:
        payload["raw_blocks"] = [dict(block) for block in reviewed]
    if "raw_artwork" not in payload:
        payload["raw_artwork"] = [dict(item) for item in reviewed_artwork]
    payload["assignment_options"] = sorted(SOURCE_BLOCK_ASSIGNMENTS)
    payload["assignment_descriptions"] = SOURCE_BLOCK_ASSIGNMENT_DESCRIPTIONS
    payload["artwork_categories"] = sorted(SOURCE_ARTWORK_CATEGORIES)
    payload["table_types"] = SUPPLEMENT_TABLE_TYPE_DESCRIPTIONS
    payload["profile_types"] = SUPPLEMENT_PROFILE_DESCRIPTIONS
    return payload


def save_supplement_source_scan(data_dir: Path, source_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    payload["source_id"] = str(payload.get("source_id") or source_id)
    reviewed = _review_blocks_from_existing(payload)
    reviewed_artwork = _review_artwork_from_existing(payload)
    reviewed_tables = _review_tables_from_existing(payload)
    reviewed_foes = _review_foes_from_existing(payload)
    reviewed_mounts = _review_profiles_from_existing(payload, "mount")
    reviewed_companion_animals = _review_profiles_from_existing(payload, "companion_animal")
    reviewed_character_classes = _review_profiles_from_existing(payload, "character_class")
    reviewed_locations = _review_profiles_from_existing(payload, "location")
    payload["reviewed_blocks"] = reviewed
    payload["blocks"] = reviewed
    payload["reviewed_artwork"] = reviewed_artwork
    payload["artwork"] = reviewed_artwork
    payload["reviewed_tables"] = reviewed_tables
    payload["tables"] = reviewed_tables
    payload["reviewed_foes"] = reviewed_foes
    payload["foes"] = reviewed_foes
    payload["reviewed_mounts"] = reviewed_mounts
    payload["mounts"] = reviewed_mounts
    payload["reviewed_companion_animals"] = reviewed_companion_animals
    payload["companion_animals"] = reviewed_companion_animals
    payload["reviewed_character_classes"] = reviewed_character_classes
    payload["character_classes"] = reviewed_character_classes
    payload["reviewed_locations"] = reviewed_locations
    payload["locations"] = reviewed_locations
    payload["assignment_options"] = sorted(SOURCE_BLOCK_ASSIGNMENTS)
    payload["assignment_descriptions"] = SOURCE_BLOCK_ASSIGNMENT_DESCRIPTIONS
    payload["artwork_categories"] = sorted(SOURCE_ARTWORK_CATEGORIES)
    payload["table_types"] = SUPPLEMENT_TABLE_TYPE_DESCRIPTIONS
    payload["profile_types"] = SUPPLEMENT_PROFILE_DESCRIPTIONS
    path = supplement_source_scan_path(data_dir, source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def update_supplement_source_block(data_dir: Path, source_id: str, block_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    for block in payload.get("reviewed_blocks", []):
        if not isinstance(block, dict) or block.get("id") != block_id:
            continue
        if "text" in changes:
            block["text"] = str(changes.get("text") or "").strip()
        if "title" in changes:
            block["title"] = str(changes.get("title") or "").strip()[:160]
        if "assignment" in changes:
            assignment = str(changes.get("assignment") or "unassigned")
            block["assignment"] = assignment if assignment in SOURCE_BLOCK_ASSIGNMENTS else "unassigned"
        if "title" in changes:
            block["title"] = str(changes.get("title") or "").strip()[:160]
        if "review_status" in changes:
            block["review_status"] = str(changes.get("review_status") or "unreviewed")
        if "notes" in changes:
            block["notes"] = str(changes.get("notes") or "")
        save_supplement_source_scan(data_dir, source_id, payload)
        return {"block": block, "message": "Source block saved."}
    raise KeyError(block_id)


def update_supplement_source_blocks(data_dir: Path, source_id: str, block_ids: list[str], changes: dict[str, Any]) -> dict[str, Any]:
    clean_ids = [str(block_id or "").strip() for block_id in block_ids if str(block_id or "").strip()]
    if not clean_ids:
        raise ValueError("Select one or more source blocks first.")
    payload = load_supplement_source_scan(data_dir, source_id)
    wanted = set(clean_ids)
    updated: list[dict[str, Any]] = []
    for block in payload.get("reviewed_blocks", []):
        if not isinstance(block, dict) or str(block.get("id") or "") not in wanted:
            continue
        if "assignment" in changes:
            assignment = str(changes.get("assignment") or "unassigned")
            block["assignment"] = assignment if assignment in SOURCE_BLOCK_ASSIGNMENTS else "unassigned"
        if "review_status" in changes:
            block["review_status"] = str(changes.get("review_status") or "unreviewed")
        if "notes" in changes:
            block["notes"] = str(changes.get("notes") or "")
        updated.append(block)
    if len(updated) != len(wanted):
        raise KeyError("One or more selected source blocks were not found.")
    save_supplement_source_scan(data_dir, source_id, payload)
    return {
        "blocks": updated,
        "updated_count": len(updated),
        "message": f"Updated {len(updated)} source block(s).",
    }


def split_supplement_source_block(data_dir: Path, source_id: str, block_id: str, parts: list[str]) -> dict[str, Any]:
    clean_parts = [str(part).strip() for part in parts if str(part).strip()]
    if len(clean_parts) < 2:
        raise ValueError("Split needs at least two non-empty blocks.")
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = payload.get("reviewed_blocks", [])
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or block.get("id") != block_id:
            continue
        replacement = []
        for part_index, text in enumerate(clean_parts, start=1):
            replacement.append(
                {
                    **block,
                    "id": f"{block_id}-split{part_index:02d}",
                    "text": text,
                    "title": str(block.get("title") or "") if part_index == 1 else "",
                    "block_index": f"{block.get('block_index') or index + 1}.{part_index}",
                    "review_status": "edited",
                    "notes": str(block.get("notes") or ""),
                }
            )
        payload["reviewed_blocks"] = blocks[:index] + replacement + blocks[index + 1 :]
        save_supplement_source_scan(data_dir, source_id, payload)
        return {"blocks": replacement, "message": f"Split source block into {len(replacement)} blocks."}
    raise KeyError(block_id)


def _source_phrase_pattern(phrase: str) -> re.Pattern[str]:
    clean_parts = [part for part in re.split(r"\s+", str(phrase or "").strip()) if part]
    if not clean_parts:
        raise ValueError("Enter a phrase to split and ignore.")
    clean_phrase = " ".join(clean_parts)
    if len(clean_phrase) < 3:
        raise ValueError("The ignore phrase must be at least 3 characters long.")
    return re.compile(r"\s+".join(re.escape(part) for part in clean_parts), re.IGNORECASE)


def _unique_source_block_id(base_id: str, used_ids: set[str]) -> str:
    candidate = base_id
    suffix = 1
    while candidate in used_ids:
        suffix += 1
        candidate = f"{base_id}-{suffix:02d}"
    used_ids.add(candidate)
    return candidate


def _normalise_source_review_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold()


def _merged_source_review_text(blocks: list[dict[str, Any]]) -> str:
    kept: list[tuple[str, str]] = []
    for block in blocks:
        text = str(block.get("text") or "").strip()
        normalised = _normalise_source_review_text(text)
        if not normalised:
            continue
        if any(normalised == seen or (len(normalised) >= 40 and normalised in seen) for seen, _ in kept):
            continue
        kept = [
            (seen, kept_text)
            for seen, kept_text in kept
            if not (len(seen) >= 40 and seen in normalised)
        ]
        kept.append((normalised, text))
    return "\n\n".join(text for _, text in kept)


def _renumber_source_review_blocks(blocks: list[dict[str, Any]]) -> None:
    for order, block in enumerate(blocks, start=1):
        if isinstance(block, dict):
            block["review_order"] = order


def _dedupe_reviewed_source_blocks(blocks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    kept: list[dict[str, Any]] = []
    text_by_page: dict[tuple[str, str], list[tuple[str, int]]] = {}
    removed = 0
    for block in blocks:
        if not isinstance(block, dict):
            continue
        assignment = str(block.get("assignment") or "unassigned")
        normalised = _normalise_source_review_text(block.get("text"))
        if assignment == "ignore" or len(normalised) < 80:
            kept.append(block)
            continue
        page_key = str(block.get("pdf_page") or block.get("source_page") or block.get("page_label") or "")
        bucket_key = (page_key, assignment)
        bucket = text_by_page.setdefault(bucket_key, [])
        duplicate_of: int | None = None
        replace_indexes: list[int] = []
        for seen_text, kept_index in bucket:
            if normalised == seen_text or normalised in seen_text:
                duplicate_of = kept_index
                break
            if seen_text in normalised:
                replace_indexes.append(kept_index)
        if duplicate_of is not None:
            removed += 1
            continue
        for kept_index in sorted(replace_indexes, reverse=True):
            removed += 1
            kept.pop(kept_index)
            for entries in text_by_page.values():
                entries[:] = [
                    (text, index - 1 if index > kept_index else index)
                    for text, index in entries
                    if index != kept_index
                ]
        bucket.append((normalised, len(kept)))
        kept.append(block)
    _renumber_source_review_blocks(kept)
    return kept, removed


def _source_duplicate_preview(text: Any, limit: int = 360) -> str:
    preview = re.sub(r"\s+", " ", str(text or "")).strip()
    return preview if len(preview) <= limit else f"{preview[:limit].rstrip()}..."


def reviewed_source_duplicate_groups(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for block in blocks:
        if not isinstance(block, dict):
            continue
        assignment = str(block.get("assignment") or "unassigned")
        normalised = _normalise_source_review_text(block.get("text"))
        if assignment == "ignore" or len(normalised) < 40:
            continue
        page_key = str(block.get("pdf_page") or block.get("source_page") or block.get("page_label") or "")
        bucket_key = (page_key, assignment)
        page_groups = buckets.setdefault(bucket_key, [])
        matched: dict[str, Any] | None = None
        for group in page_groups:
            canonical = str(group.get("canonical") or "")
            if normalised == canonical or normalised in canonical or canonical in normalised:
                matched = group
                break
        if matched is None:
            page_groups.append({"canonical": normalised, "items": [(normalised, block)]})
        else:
            matched["items"].append((normalised, block))
            if len(normalised) > len(str(matched.get("canonical") or "")):
                matched["canonical"] = normalised

    groups: list[dict[str, Any]] = []
    for page_groups in buckets.values():
        for group in page_groups:
            items = list(group.get("items") or [])
            if len(items) < 2:
                continue
            ordered_items = sorted(enumerate(items), key=lambda item: (-len(item[1][0]), item[0]))
            keep_index = ordered_items[0][0]
            keep_block = items[keep_index][1]
            duplicates = [block for index, (_normalised, block) in enumerate(items) if index != keep_index]
            if not duplicates:
                continue
            group_id = f"dup-{len(groups) + 1:03d}-{keep_block.get('pdf_page') or keep_block.get('source_page') or 'page'}"
            groups.append(
                {
                    "id": group_id,
                    "reason": "same-page duplicate or contained text",
                    "assignment": str(keep_block.get("assignment") or "unassigned"),
                    "page_label": str(keep_block.get("page_label") or ""),
                    "pdf_page": keep_block.get("pdf_page"),
                    "source_page": keep_block.get("source_page"),
                    "keep_block": {
                        "id": keep_block.get("id"),
                        "page_label": keep_block.get("page_label"),
                        "block_index": keep_block.get("block_index"),
                        "assignment": keep_block.get("assignment") or "unassigned",
                        "text": str(keep_block.get("text") or ""),
                        "preview": _source_duplicate_preview(keep_block.get("text")),
                    },
                    "duplicate_blocks": [
                        {
                            "id": block.get("id"),
                            "page_label": block.get("page_label"),
                            "block_index": block.get("block_index"),
                            "assignment": block.get("assignment") or "unassigned",
                            "text": str(block.get("text") or ""),
                            "preview": _source_duplicate_preview(block.get("text")),
                        }
                        for block in duplicates
                    ],
                    "suggested_duplicate_block_ids": [str(block.get("id")) for block in duplicates if block.get("id")],
                    "candidate_count": len(items),
                }
            )
    return groups


def find_supplement_source_duplicate_blocks(data_dir: Path, source_id: str) -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    path = supplement_source_scan_path(data_dir, source_id)
    if not path.exists():
        raise KeyError(source_id)
    blocks = payload.get("reviewed_blocks", [])
    if not isinstance(blocks, list):
        blocks = []
    groups = reviewed_source_duplicate_groups(blocks)
    duplicate_ids = [block_id for group in groups for block_id in group.get("suggested_duplicate_block_ids", [])]
    return {
        "source_id": source_id,
        "group_count": len(groups),
        "suggested_duplicate_count": len(duplicate_ids),
        "groups": groups,
        "message": f"Found {len(groups)} probable duplicate group(s), with {len(duplicate_ids)} suggested removable block(s).",
    }


def delete_supplement_source_blocks(data_dir: Path, source_id: str, block_ids: list[str], reason: str = "") -> dict[str, Any]:
    clean_ids = list(dict.fromkeys(str(block_id) for block_id in block_ids if str(block_id)))
    if not clean_ids:
        raise ValueError("Select at least one source block to remove.")
    payload = load_supplement_source_scan(data_dir, source_id)
    path = supplement_source_scan_path(data_dir, source_id)
    if not path.exists():
        raise KeyError(source_id)
    blocks = payload.get("reviewed_blocks", [])
    if not isinstance(blocks, list):
        blocks = []
    remove_ids = set(clean_ids)
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if str(block.get("id") or "") in remove_ids:
            removed.append(block)
            continue
        kept.append(block)
    if len(removed) != len(remove_ids):
        raise KeyError("One or more selected source blocks were not found.")
    _renumber_source_review_blocks(kept)
    log = payload.get("duplicate_cleanup_log") if isinstance(payload.get("duplicate_cleanup_log"), list) else []
    log.append(
        {
            "removed_block_ids": [str(block.get("id") or "") for block in removed],
            "reason": str(reason or "manual duplicate cleanup"),
        }
    )
    payload["duplicate_cleanup_log"] = log
    payload["reviewed_blocks"] = kept
    save_supplement_source_scan(data_dir, source_id, payload)
    return {
        "source_id": source_id,
        "removed_count": len(removed),
        "removed_block_ids": [str(block.get("id") or "") for block in removed],
        "message": f"Removed {len(removed)} reviewed source block(s).",
    }


def hide_supplement_source_duplicate_fragments(data_dir: Path, source_id: str) -> dict[str, Any]:
    """Hide old line-fragment duplicates while retaining the reviewed source audit trail."""
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = [block for block in payload.get("reviewed_blocks", []) if isinstance(block, dict)]
    by_page: dict[int, list[dict[str, Any]]] = {}
    for block in blocks:
        try:
            pdf_page = int(block.get("pdf_page") or 0)
        except (TypeError, ValueError):
            continue
        if pdf_page > 0:
            by_page.setdefault(pdf_page, []).append(block)

    hidden: list[dict[str, Any]] = []
    affected_pages: set[int] = set()
    for pdf_page, page_blocks in by_page.items():
        containers = [
            _normalise_source_review_text(block.get("text"))
            for block in page_blocks
            if str(block.get("assignment") or "unassigned") != "ignore"
            and len(_normalise_source_review_text(block.get("text"))) >= 180
        ]
        if not containers:
            continue
        for block in page_blocks:
            if str(block.get("assignment") or "unassigned") == "ignore":
                continue
            normalised = _normalise_source_review_text(block.get("text"))
            if not (3 <= len(normalised) < 180):
                continue
            if not any(normalised != container and normalised in container for container in containers):
                continue
            existing_note = str(block.get("notes") or "").strip()
            block["assignment"] = "ignore"
            block["review_status"] = "edited"
            block["notes"] = f"{existing_note}\nAuto-hidden duplicate fragment contained in a longer same-page reviewed block.".strip()
            hidden.append(block)
            affected_pages.add(pdf_page)
    if not hidden:
        raise ValueError("No short duplicate fragments were found inside longer same-page reviewed blocks.")
    save_supplement_source_scan(data_dir, source_id, payload)
    return {
        "source_id": source_id,
        "hidden_count": len(hidden),
        "pages": len(affected_pages),
        "hidden_block_ids": [str(block.get("id") or "") for block in hidden],
        "message": f"Hidden {len(hidden)} duplicate fragment(s) across {len(affected_pages)} PDF page(s).",
    }


def reset_supplement_source_workspace(data_dir: Path, source_id: str) -> dict[str, Any]:
    clean_source_id = supplement_package_id(source_id, "pdf-source")
    root = supplement_sources_root(data_dir)
    settings_payload = _load_source_settings(data_dir)
    settings_sources = settings_payload.get("sources") if isinstance(settings_payload.get("sources"), dict) else {}
    settings_packages = settings_payload.get("packages") if isinstance(settings_payload.get("packages"), dict) else {}
    settings_payload["sources"] = settings_sources
    settings_payload["packages"] = settings_packages

    source_settings = settings_sources.get(clean_source_id) if isinstance(settings_sources.get(clean_source_id), dict) else {}
    scan_payload = load_supplement_source_scan(data_dir, clean_source_id)
    scan_path = supplement_source_scan_path(data_dir, clean_source_id)
    source_pdf = str(scan_payload.get("source_pdf") or source_settings.get("filename") or "")
    raw_package_id = str(scan_payload.get("supplement_id") or source_settings.get("supplement_id") or "")
    package_ids = {clean_source_id}
    if raw_package_id:
        package_ids.add(supplement_package_id(raw_package_id, clean_source_id))
    if raw_package_id.lower() in GENERIC_SUPPLEMENT_PACKAGE_IDS:
        package_ids.add("supplement-package")

    known_package_ids = {
        supplement_package_id(str(payload.get("supplement_id") or package_id), str(package_id))
        for package_id, payload in settings_packages.items()
        if isinstance(payload, dict)
    }
    package_ids.add(_source_package_id({**scan_payload, **source_settings, "source_id": clean_source_id}, known_package_ids))

    removed_paths: list[str] = []
    removed_settings: list[str] = []

    for target in [
        supplement_source_folder(data_dir, clean_source_id),
        supplement_source_pdf_page_cache_dir(data_dir, source_pdf, clean_source_id),
    ]:
        if _remove_tree_inside(root, target):
            removed_paths.append(str(target))

    if clean_source_id in settings_sources:
        del settings_sources[clean_source_id]
        removed_settings.append(f"sources.{clean_source_id}")

    for package_id in sorted(package_ids):
        if package_id in settings_packages:
            del settings_packages[package_id]
            removed_settings.append(f"packages.{package_id}")
        package_dir = supplement_package_asset_dir(data_dir, package_id)
        if _remove_tree_inside(root, package_dir):
            removed_paths.append(str(package_dir))

    if not scan_path.exists() and not removed_paths and not removed_settings:
        raise KeyError(clean_source_id)

    _write_source_settings(data_dir, settings_payload)
    return {
        "source_id": clean_source_id,
        "removed_paths": removed_paths,
        "removed_settings": removed_settings,
        "message": (
            f"Reset source workspace for {clean_source_id}. "
            "Reviewed blocks, reviewed tables, extracted artwork, package assets, and rendered page cache were removed."
        ),
    }


def split_matching_supplement_source_phrase_to_ignore(data_dir: Path, source_id: str, phrase: str) -> dict[str, Any]:
    pattern = _source_phrase_pattern(phrase)
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = payload.get("reviewed_blocks", [])
    if not isinstance(blocks, list):
        blocks = []
    used_ids = {str(block.get("id") or "") for block in blocks if isinstance(block, dict) and block.get("id")}
    next_blocks: list[dict[str, Any]] = []
    changed_blocks = 0
    ignored_occurrences = 0
    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "")
        matches = list(pattern.finditer(text))
        if not matches:
            next_blocks.append(block)
            continue
        if str(block.get("assignment") or "") == "ignore" and all(match.start() == 0 and match.end() == len(text) for match in matches):
            next_blocks.append(block)
            continue
        changed_blocks += 1
        base_id = str(block.get("id") or f"{source_id}-block-{index:03d}")
        cursor = 0
        part_index = 1
        replacement: list[dict[str, Any]] = []
        for match in matches:
            before = text[cursor : match.start()].strip()
            if before:
                replacement.append(
                    {
                        **block,
                        "id": _unique_source_block_id(f"{base_id}-keep{part_index:02d}", used_ids),
                        "text": before,
                        "block_index": f"{block.get('block_index') or index}.{part_index}",
                        "review_status": "edited",
                    }
                )
                part_index += 1
            ignored_text = text[match.start() : match.end()].strip()
            if ignored_text:
                ignored_occurrences += 1
                note = f"Auto-split ignored phrase: {ignored_text[:120]}"
                existing_note = str(block.get("notes") or "").strip()
                replacement.append(
                    {
                        **block,
                        "id": _unique_source_block_id(f"{base_id}-ignore{part_index:02d}", used_ids),
                        "text": ignored_text,
                        "assignment": "ignore",
                        "block_index": f"{block.get('block_index') or index}.{part_index}",
                        "review_status": "edited",
                        "notes": f"{existing_note}\n{note}".strip(),
                    }
                )
                part_index += 1
            cursor = match.end()
        after = text[cursor:].strip()
        if after:
            replacement.append(
                {
                    **block,
                    "id": _unique_source_block_id(f"{base_id}-keep{part_index:02d}", used_ids),
                    "text": after,
                    "block_index": f"{block.get('block_index') or index}.{part_index}",
                    "review_status": "edited",
                }
            )
        if replacement:
            next_blocks.extend(replacement)
        else:
            next_blocks.append({**block, "assignment": "ignore", "review_status": "edited"})
    if not ignored_occurrences:
        raise ValueError("No occurrences of that phrase were found in reviewed source blocks.")
    next_blocks, duplicate_removed = _dedupe_reviewed_source_blocks(next_blocks)
    payload["reviewed_blocks"] = next_blocks
    save_supplement_source_scan(data_dir, source_id, payload)
    dedupe_note = f" Removed {duplicate_removed} duplicate reviewed block(s)." if duplicate_removed else ""
    return {
        "phrase": str(phrase or "").strip(),
        "changed_blocks": changed_blocks,
        "ignored_occurrences": ignored_occurrences,
        "blocks": len(next_blocks),
        "duplicate_blocks_removed": duplicate_removed,
        "message": f"Split {ignored_occurrences} occurrence(s) into ignored source blocks across {changed_blocks} reviewed block(s).{dedupe_note}",
    }


def merge_supplement_source_block(data_dir: Path, source_id: str, block_id: str, direction: str = "next") -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = payload.get("reviewed_blocks", [])
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or block.get("id") != block_id:
            continue
        other_index = index - 1 if direction == "previous" else index + 1
        if other_index < 0 or other_index >= len(blocks) or not isinstance(blocks[other_index], dict):
            raise ValueError("No adjacent source block is available to merge.")
        first_index, second_index = sorted([index, other_index])
        first = blocks[first_index]
        second = blocks[second_index]
        merged = {
            **first,
            "id": f"{first.get('id')}-merged-{second.get('id')}",
            "text": _merged_source_review_text([first, second]),
            "review_status": "edited",
            "notes": "Merged manually in the PDF / Supplement Workbench.",
            "merged_block_ids": [first.get("id"), second.get("id")],
        }
        next_blocks, _duplicate_removed = _dedupe_reviewed_source_blocks(blocks[:first_index] + [merged] + blocks[second_index + 1 :])
        payload["reviewed_blocks"] = next_blocks
        save_supplement_source_scan(data_dir, source_id, payload)
        return {"block": merged, "message": "Merged adjacent source blocks."}
    raise KeyError(block_id)


def merge_selected_supplement_source_blocks(data_dir: Path, source_id: str, block_ids: list[str]) -> dict[str, Any]:
    clean_ids = list(dict.fromkeys(str(block_id) for block_id in block_ids if str(block_id)))
    if len(clean_ids) < 2:
        raise ValueError("Select at least two blocks to merge.")
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = payload.get("reviewed_blocks", [])
    indexes = [index for index, block in enumerate(blocks) if isinstance(block, dict) and block.get("id") in clean_ids]
    if len(indexes) != len(set(clean_ids)):
        raise KeyError("One or more selected source blocks were not found.")
    indexes = sorted(indexes)
    selected_id_set = set(clean_ids)
    intervening = [
        block
        for index, block in enumerate(blocks[indexes[0] : indexes[-1] + 1], start=indexes[0])
        if isinstance(block, dict)
        and block.get("id") not in selected_id_set
        and str(block.get("assignment") or "unassigned") != "ignore"
    ]
    if intervening:
        raise ValueError(
            f"The selected range contains {len(intervening)} non-ignored intervening block(s). "
            "Select them as well, or use Merge Page to combine every non-ignored block on that PDF page."
        )
    selected = [blocks[index] for index in indexes]
    first = selected[0]
    last = selected[-1]
    merged = {
        **first,
        "id": f"{first.get('id')}-merged-{last.get('id')}",
        "text": _merged_source_review_text(selected),
        "review_status": "edited",
        "notes": "Merged manually from selected visible blocks in the PDF / Supplement Workbench.",
        "merged_block_ids": [block.get("id") for block in selected],
    }
    next_blocks: list[dict[str, Any]] = []
    merged_inserted = False
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        if index == indexes[0] and not merged_inserted:
            next_blocks.append(merged)
            merged_inserted = True
            continue
        if block.get("id") in selected_id_set:
            continue
        next_blocks.append(block)
    next_blocks, duplicate_removed = _dedupe_reviewed_source_blocks(next_blocks)
    payload["reviewed_blocks"] = next_blocks
    save_supplement_source_scan(data_dir, source_id, payload)
    dedupe_note = f" Removed {duplicate_removed} duplicate reviewed block(s)." if duplicate_removed else ""
    return {"block": merged, "duplicate_blocks_removed": duplicate_removed, "message": f"Merged {len(selected)} selected source blocks.{dedupe_note}"}


def merge_supplement_source_page(data_dir: Path, source_id: str, block_id: str) -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = [block for block in payload.get("reviewed_blocks", []) if isinstance(block, dict)]
    anchor = next((block for block in blocks if str(block.get("id") or "") == block_id), None)
    if anchor is None:
        raise KeyError(block_id)
    pdf_page = int(anchor.get("pdf_page") or 0)
    if pdf_page < 1:
        raise ValueError("The selected block has no physical PDF page reference.")
    page_blocks = [
        block
        for block in blocks
        if int(block.get("pdf_page") or 0) == pdf_page
        and str(block.get("assignment") or "unassigned") != "ignore"
    ]
    if len(page_blocks) < 2:
        raise ValueError("This PDF page does not have at least two non-ignored blocks to merge.")
    page_ids = {str(block.get("id") or "") for block in page_blocks}
    page_assignments = {str(block.get("assignment") or "unassigned") for block in page_blocks}
    first = page_blocks[0]
    used_ids = {str(block.get("id") or "") for block in blocks}
    merged = {
        **first,
        "id": _unique_source_block_id(f"{source_id}-pdf{pdf_page}-page-merge", used_ids),
        "assignment": page_assignments.pop() if len(page_assignments) == 1 else "unassigned",
        "text": _merged_source_review_text(page_blocks),
        "review_status": "edited",
        "notes": "Merged every non-ignored text block on this physical PDF page in the PDF / Supplement Workbench.",
        "merged_block_ids": [block.get("id") for block in page_blocks],
    }
    next_blocks: list[dict[str, Any]] = []
    merged_inserted = False
    for block in blocks:
        current_id = str(block.get("id") or "")
        if current_id in page_ids:
            if not merged_inserted:
                next_blocks.append(merged)
                merged_inserted = True
            continue
        next_blocks.append(block)
    _renumber_source_review_blocks(next_blocks)
    payload["reviewed_blocks"] = next_blocks
    save_supplement_source_scan(data_dir, source_id, payload)
    return {
        "block": merged,
        "merged_count": len(page_blocks),
        "ignored_blocks_preserved": len(
            [
                block
                for block in blocks
                if int(block.get("pdf_page") or 0) == pdf_page
                and str(block.get("assignment") or "unassigned") == "ignore"
            ]
        ),
        "message": f"Merged {len(page_blocks)} non-ignored blocks from {first.get('page_label') or f'PDF page {pdf_page}'}."
    }


def move_supplement_source_block(data_dir: Path, source_id: str, block_id: str, direction: str) -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = payload.get("reviewed_blocks", [])
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or block.get("id") != block_id:
            continue
        target = index - 1 if direction == "up" else index + 1
        if target < 0 or target >= len(blocks):
            raise ValueError("Source block cannot move any further in that direction.")
        blocks[index], blocks[target] = blocks[target], blocks[index]
        for order, item in enumerate(blocks, start=1):
            if isinstance(item, dict):
                item["review_order"] = order
        payload["reviewed_blocks"] = blocks
        save_supplement_source_scan(data_dir, source_id, payload)
        return {"block": blocks[target], "message": f"Moved source block {direction}."}
    raise KeyError(block_id)


def extract_supplement_source_artwork(
    data_dir: Path,
    pdf_path: Path,
    *,
    now: str,
    page_offset: int = 0,
    supplement_id: str | None = None,
    supplement_title: str | None = None,
) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is present in app image/tests
        raise RuntimeError("pypdf is required to extract PDF artwork images.") from exc

    source_settings = set_pdf_source_metadata(
        data_dir,
        pdf_path,
        page_offset=page_offset,
        supplement_id=supplement_id,
        supplement_title=supplement_title,
    )
    source_id = supplement_source_id(pdf_path)
    package_id = supplement_package_id(source_settings.get("supplement_id"), source_id)
    package_title = str(source_settings.get("supplement_title") or pdf_path.stem)
    payload = load_supplement_source_scan(data_dir, source_id)
    payload["supplement_id"] = package_id
    payload["supplement_title"] = package_title
    artwork_dir = supplement_source_artwork_dir(data_dir, source_id) / "raw"
    artwork_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(pdf_path))
    raw_records: list[dict[str, Any]] = []
    for page_index, page in enumerate(reader.pages, start=1):
        try:
            images = list(page.images)
        except Exception:  # noqa: BLE001 - PDF image extraction support varies
            images = []
        for image_index, image in enumerate(images, start=1):
            image_name = Path(str(getattr(image, "name", "") or f"image-{image_index}.bin")).name
            extension = Path(image_name).suffix.lower() or ".bin"
            filename = f"page-{page_index:03d}-image-{image_index:02d}{extension}"
            data = getattr(image, "data", b"")
            if not isinstance(data, bytes) or not data:
                continue
            (artwork_dir / filename).write_bytes(data)
            source_page = display_page_number(page_index, page_offset)
            raw_records.append(
                {
                    "id": f"{source_id}-art-p{source_page}-pdf{page_index}-i{image_index:02d}",
                    "supplement_id": package_id,
                    "supplement_title": package_title,
                    "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
                    "source_page": source_page,
                    "pdf_page": page_index,
                    "page_label": page_label(page_index, page_offset),
                    "filename": filename,
                    "asset_url": f"/api/supplements/source-scans/{source_id}/artwork/{filename}",
                    "title": f"Page {source_page} image {image_index}",
                    "category": "unknown",
                    "candidate_type": "embedded_image",
                    "review_status": "unreviewed",
                    "notes": "",
                }
            )
    if not raw_records:
        pdftoppm = shutil.which("pdftoppm")
        if not pdftoppm:
            raise RuntimeError("No embedded PDF images were exposed, and pdftoppm is unavailable for rendered-page artwork fallback.")
        rendered_dir = supplement_source_artwork_dir(data_dir, source_id) / "rendered_pages"
        rendered_dir.mkdir(parents=True, exist_ok=True)
        for page_index in range(1, len(reader.pages) + 1):
            filename = f"page-{page_index:03d}-render.png"
            output_prefix = rendered_dir / f"page-{page_index:03d}-render"
            output = rendered_dir / filename
            result = subprocess.run(
                [
                    pdftoppm,
                    "-f",
                    str(page_index),
                    "-l",
                    str(page_index),
                    "-singlefile",
                    "-png",
                    "-r",
                    "150",
                    str(pdf_path),
                    str(output_prefix),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0 or not output.is_file():
                continue
            source_page = display_page_number(page_index, page_offset)
            raw_records.append(
                {
                    "id": f"{source_id}-art-render-p{source_page}-pdf{page_index}",
                    "supplement_id": package_id,
                    "supplement_title": package_title,
                    "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
                    "source_page": source_page,
                    "pdf_page": page_index,
                    "page_label": page_label(page_index, page_offset),
                    "filename": filename,
                    "asset_url": f"/api/supplements/source-scans/{source_id}/artwork/{filename}",
                    "title": f"Rendered page {source_page}",
                    "category": "review_later",
                    "candidate_type": "rendered_page",
                    "review_status": "unreviewed",
                    "notes": "Rendered full PDF page because no embedded artwork images were exposed. Use as a review/crop source.",
                }
            )
    existing_reviewed = _review_artwork_from_existing(payload)
    existing_by_filename = {str(item.get("filename") or ""): item for item in existing_reviewed if isinstance(item, dict)}
    reviewed_artwork = [existing_by_filename.get(str(item.get("filename") or ""), dict(item)) for item in raw_records]
    payload["raw_artwork"] = raw_records
    payload["reviewed_artwork"] = reviewed_artwork
    payload["artwork"] = reviewed_artwork
    payload["artwork_categories"] = sorted(SOURCE_ARTWORK_CATEGORIES)
    payload["artwork_updated_at"] = now
    save_supplement_source_scan(data_dir, source_id, payload)
    return {
        "source_id": source_id,
        "supplement_id": package_id,
        "supplement_title": package_title,
        "raw_artwork": len(raw_records),
        "reviewed_artwork": len(reviewed_artwork),
        "path": str(artwork_dir),
        "message": f"Extracted {len(raw_records)} artwork candidate(s) from {pdf_path.name}; reviewed artwork metadata was preserved where filenames matched.",
    }


def update_supplement_source_artwork(data_dir: Path, source_id: str, artwork_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    for item in payload.get("reviewed_artwork", []):
        if not isinstance(item, dict) or item.get("id") != artwork_id:
            continue
        if "title" in changes:
            item["title"] = str(changes.get("title") or "").strip()
        if "category" in changes:
            category = str(changes.get("category") or "unknown")
            item["category"] = category if category in SOURCE_ARTWORK_CATEGORIES else "unknown"
        if "review_status" in changes:
            item["review_status"] = str(changes.get("review_status") or "unreviewed")
        if "notes" in changes:
            item["notes"] = str(changes.get("notes") or "")
        save_supplement_source_scan(data_dir, source_id, payload)
        return {"artwork": item, "message": "Artwork review saved."}
    raise KeyError(artwork_id)


def add_supplement_source_artwork_crop(
    data_dir: Path,
    source_id: str,
    filename: str,
    data: bytes,
    *,
    title: str,
    parent_artwork_id: str = "",
    category: str = "character_class",
    tile_key: str = "",
    notes: str = "",
) -> dict[str, Any]:
    payload = load_supplement_source_scan(data_dir, source_id)
    if not supplement_source_scan_path(data_dir, source_id).exists():
        raise KeyError(source_id)
    clean_stem = re.sub(r"[^a-z0-9_-]+", "-", Path(str(filename or "portrait-crop.png")).stem.lower()).strip("-") or "portrait-crop"
    crop_dir = supplement_source_artwork_dir(data_dir, source_id) / "crops"
    crop_dir.mkdir(parents=True, exist_ok=True)
    clean_name = f"{clean_stem}.png"
    suffix = 2
    while (crop_dir / clean_name).exists():
        clean_name = f"{clean_stem}-{suffix}.png"
        suffix += 1
    path = crop_dir / clean_name
    path.write_bytes(data)
    parent = next(
        (item for item in payload.get("reviewed_artwork", []) if isinstance(item, dict) and item.get("id") == parent_artwork_id),
        {},
    )
    used_ids = {str(item.get("id") or "") for item in payload.get("reviewed_artwork", []) if isinstance(item, dict)}
    artwork_id = f"{source_id}-crop-{clean_stem}"
    suffix = 2
    while artwork_id in used_ids:
        artwork_id = f"{source_id}-crop-{clean_stem}-{suffix}"
        suffix += 1
    clean_category = category if category in SOURCE_ARTWORK_CATEGORIES else "unknown"
    artwork = {
        "id": artwork_id,
        "source_pdf": str(parent.get("source_pdf") or payload.get("source_pdf") or ""),
        "source_page": parent.get("source_page"),
        "pdf_page": parent.get("pdf_page"),
        "page_label": str(parent.get("page_label") or ""),
        "filename": clean_name,
        "asset_url": f"/api/supplements/source-scans/{source_id}/artwork/{clean_name}",
        "title": str(title or clean_stem).strip(),
        "category": clean_category,
        "candidate_type": "masked_tile" if clean_category == "room_tile" else "masked_crop",
        "review_status": "checked",
        "notes": str(notes or f"Masked artwork crop from {parent_artwork_id or 'source artwork'}.").strip(),
        "parent_artwork_id": str(parent_artwork_id or ""),
        "tile_key": str(tile_key or "").strip(),
        "size_bytes": len(data),
    }
    reviewed = [item for item in payload.get("reviewed_artwork", []) if isinstance(item, dict)]
    reviewed.append(artwork)
    payload["reviewed_artwork"] = reviewed
    save_supplement_source_scan(data_dir, source_id, payload)
    return {"artwork": artwork, "message": f"Saved masked artwork crop {artwork['title']}."}


def supplement_source_artwork_path(data_dir: Path, source_id: str, filename: str) -> Path:
    safe = Path(str(filename or "")).name
    crop = supplement_source_artwork_dir(data_dir, source_id) / "crops" / safe
    if crop.is_file():
        return crop
    raw = supplement_source_artwork_dir(data_dir, source_id) / "raw" / safe
    if raw.is_file():
        return raw
    return supplement_source_artwork_dir(data_dir, source_id) / "rendered_pages" / safe


def list_supplement_source_scans(data_dir: Path) -> list[dict[str, Any]]:
    root = supplement_sources_root(data_dir)
    if not root.exists():
        return []
    scans: list[dict[str, Any]] = []
    for scan_path in sorted(root.glob("*/source_blocks.json")):
        source_id = scan_path.parent.name
        payload = load_supplement_source_scan(data_dir, source_id)
        blocks = [block for block in payload.get("blocks", []) if isinstance(block, dict)]
        raw_blocks = [block for block in payload.get("raw_blocks", []) if isinstance(block, dict)]
        continuation_candidates = [block for block in payload.get("continuation_candidates", []) if isinstance(block, dict)]
        artwork = [item for item in payload.get("reviewed_artwork", []) if isinstance(item, dict)]
        tables = [item for item in payload.get("reviewed_tables", []) if isinstance(item, dict)]
        assignments: dict[str, int] = {}
        reviewed = 0
        for block in blocks:
            assignment = str(block.get("assignment") or "unassigned")
            assignments[assignment] = assignments.get(assignment, 0) + 1
            if str(block.get("review_status") or "") not in {"", "unreviewed"}:
                reviewed += 1
        scans.append(
            {
                "source_id": str(payload.get("source_id") or source_id),
                "supplement_id": str(payload.get("supplement_id") or supplement_package_id(None, source_id)),
                "supplement_title": _friendly_source_title(payload.get("supplement_title"), payload.get("source_pdf"), source_id),
                "source_pdf": str(payload.get("source_pdf") or ""),
                "updated_at": str(payload.get("updated_at") or ""),
                "page_offset": int(payload.get("page_offset") or 0),
                "blocks": len(blocks),
                "raw_blocks": len(raw_blocks),
                "continuation_candidates": len(continuation_candidates),
                "artwork": len(artwork),
                "tables": len(tables),
                "reviewed_blocks": reviewed,
                "assignment_counts": assignments,
                "path": str(scan_path),
            }
        )
    return scans


def list_supplement_source_packages(data_dir: Path) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    settings = _load_source_settings(data_dir)
    setting_packages = settings.get("packages") if isinstance(settings.get("packages"), dict) else {}
    known_package_ids: set[str] = set()
    for package_id, package_payload in setting_packages.items():
        if not isinstance(package_payload, dict):
            continue
        safe_id = supplement_package_id(str(package_payload.get("supplement_id") or package_id), str(package_id))
        known_package_ids.add(safe_id)
        assets = [item for item in package_payload.get("assets", []) if isinstance(item, dict)]
        requirements = [item for item in package_payload.get("requirements", []) if isinstance(item, dict)]
        grouped[safe_id] = {
            "supplement_id": safe_id,
            "supplement_title": _friendly_source_title(package_payload.get("supplement_title"), None, safe_id),
            "source_count": 0,
            "asset_count": len(assets),
            "requirement_count": len(requirements),
            "asset_categories": sorted(SUPPLEMENT_PACKAGE_ASSET_CATEGORIES),
            "blocks": 0,
            "artwork": 0,
            "tables": 0,
            "reviewed_blocks": 0,
            "sources": [],
            "assets": assets,
            "requirements": requirements,
        }
    for scan in list_supplement_source_scans(data_dir):
        package_id = _source_package_id(scan, known_package_ids)
        scan["supplement_id"] = package_id
        package = grouped.setdefault(
            package_id,
            {
                "supplement_id": package_id,
                "supplement_title": _friendly_source_title(scan.get("supplement_title"), scan.get("source_pdf"), package_id),
                "source_count": 0,
                "asset_count": 0,
                "requirement_count": 0,
                "asset_categories": sorted(SUPPLEMENT_PACKAGE_ASSET_CATEGORIES),
                "blocks": 0,
                "artwork": 0,
                "tables": 0,
                "reviewed_blocks": 0,
                "sources": [],
                "assets": [],
                "requirements": [],
            },
        )
        if str(package.get("supplement_title") or "").strip().lower() in GENERIC_SUPPLEMENT_PACKAGE_TITLES:
            package["supplement_title"] = _friendly_source_title(scan.get("supplement_title"), scan.get("source_pdf"), package_id)
        package["source_count"] = int(package.get("source_count") or 0) + 1
        package["blocks"] = int(package.get("blocks") or 0) + int(scan.get("blocks") or 0)
        package["artwork"] = int(package.get("artwork") or 0) + int(scan.get("artwork") or 0)
        package["tables"] = int(package.get("tables") or 0) + int(scan.get("tables") or 0)
        package["reviewed_blocks"] = int(package.get("reviewed_blocks") or 0) + int(scan.get("reviewed_blocks") or 0)
        package["sources"].append(scan)
    return sorted(grouped.values(), key=lambda item: str(item.get("supplement_title") or item.get("supplement_id") or ""))
