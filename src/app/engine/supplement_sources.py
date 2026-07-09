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
    "npc",
    "character_class",
    "room",
    "dungeon",
    "location",
    "item_equipment",
    "terrain",
    "map",
    "tile",
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
    "handout",
    "filler_art_reference",
    "ignore",
}


SOURCE_BLOCK_ASSIGNMENTS = {
    "unassigned",
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


def supplement_sources_root(data_dir: Path) -> Path:
    return data_dir / "Supplements" / "_sources"


def supplement_source_id(pdf_path: Path) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", pdf_path.stem.lower()).strip("-")
    return slug or "pdf-source"


def supplement_package_id(value: str | None, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or fallback or "").lower()).strip("-")
    return slug or "supplement-package"


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
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def pdf_source_settings(data_dir: Path, pdf_path: Path) -> dict[str, Any]:
    source_id = supplement_source_id(pdf_path)
    payload = _load_source_settings(data_dir)
    sources = payload.get("sources") if isinstance(payload.get("sources"), dict) else {}
    settings = sources.get(source_id) if isinstance(sources.get(source_id), dict) else {}
    package_id = supplement_package_id(settings.get("supplement_id"), source_id)
    return {
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
    _write_source_settings(data_dir, payload)
    return sources[source_id]


def set_pdf_source_page_offset(data_dir: Path, pdf_path: Path, page_offset: int) -> dict[str, Any]:
    return set_pdf_source_metadata(data_dir, pdf_path, page_offset=page_offset)


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
    }
    _write_source_settings(data_dir, payload)
    return packages[package_id]


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


def scan_supplement_source_pdf(
    data_dir: Path,
    pdf_path: Path,
    *,
    now: str,
    page_offset: int = 0,
    supplement_id: str | None = None,
    supplement_title: str | None = None,
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
        for index, text in enumerate(_page_text_blocks(str(page.get("text") or "")), start=1):
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
    reviewed_blocks = existing_reviewed_blocks or [dict(block) for block in raw_blocks]
    payload = {
        "schema_version": 1,
        "source_id": source_id,
        "supplement_id": package_id,
        "supplement_title": package_title,
        "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
        "updated_at": now,
        "page_offset": int(page_offset),
        "note": "Local/private PDF source blocks for human review and supplement assignment. Exact text remains in DATA_DIR. Re-scans update raw_blocks; reviewed_blocks preserve human edits.",
        "assignment_options": sorted(SOURCE_BLOCK_ASSIGNMENTS),
        "artwork_categories": sorted(SOURCE_ARTWORK_CATEGORIES),
        "raw_blocks": raw_blocks,
        "reviewed_blocks": reviewed_blocks,
        "blocks": reviewed_blocks,
        "continuation_candidates": continuation_candidates,
        "raw_artwork": existing.get("raw_artwork", []),
        "reviewed_artwork": _review_artwork_from_existing(existing),
    }
    supplement_source_scan_path(data_dir, source_id).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "source_id": source_id,
        "supplement_id": package_id,
        "supplement_title": package_title,
        "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
        "blocks": len(reviewed_blocks),
        "raw_blocks": len(raw_blocks),
        "continuation_candidates": len(continuation_candidates),
        "pages": len(pages),
        "page_offset": int(page_offset),
        "path": str(supplement_source_scan_path(data_dir, source_id)),
        "message": f"Scanned {len(raw_blocks)} raw block(s), preserved {len(reviewed_blocks)} reviewed block(s), and found {len(continuation_candidates)} page-boundary candidate(s) from {pdf_path.name}.",
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
    payload["reviewed_blocks"] = reviewed
    payload["blocks"] = reviewed
    payload["reviewed_artwork"] = reviewed_artwork
    payload["artwork"] = reviewed_artwork
    if "raw_blocks" not in payload:
        payload["raw_blocks"] = [dict(block) for block in reviewed]
    if "raw_artwork" not in payload:
        payload["raw_artwork"] = [dict(item) for item in reviewed_artwork]
    payload["assignment_options"] = sorted(SOURCE_BLOCK_ASSIGNMENTS)
    payload["artwork_categories"] = sorted(SOURCE_ARTWORK_CATEGORIES)
    return payload


def save_supplement_source_scan(data_dir: Path, source_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    payload["source_id"] = str(payload.get("source_id") or source_id)
    reviewed = _review_blocks_from_existing(payload)
    reviewed_artwork = _review_artwork_from_existing(payload)
    payload["reviewed_blocks"] = reviewed
    payload["blocks"] = reviewed
    payload["reviewed_artwork"] = reviewed_artwork
    payload["artwork"] = reviewed_artwork
    payload["assignment_options"] = sorted(SOURCE_BLOCK_ASSIGNMENTS)
    payload["artwork_categories"] = sorted(SOURCE_ARTWORK_CATEGORIES)
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
        if "assignment" in changes:
            assignment = str(changes.get("assignment") or "unassigned")
            block["assignment"] = assignment if assignment in SOURCE_BLOCK_ASSIGNMENTS else "unassigned"
        if "review_status" in changes:
            block["review_status"] = str(changes.get("review_status") or "unreviewed")
        if "notes" in changes:
            block["notes"] = str(changes.get("notes") or "")
        save_supplement_source_scan(data_dir, source_id, payload)
        return {"block": block, "message": "Source block saved."}
    raise KeyError(block_id)


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
                    "block_index": f"{block.get('block_index') or index + 1}.{part_index}",
                    "review_status": "edited",
                    "notes": str(block.get("notes") or ""),
                }
            )
        payload["reviewed_blocks"] = blocks[:index] + replacement + blocks[index + 1 :]
        save_supplement_source_scan(data_dir, source_id, payload)
        return {"blocks": replacement, "message": f"Split source block into {len(replacement)} blocks."}
    raise KeyError(block_id)


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
            "text": f"{first.get('text') or ''}\n\n{second.get('text') or ''}".strip(),
            "review_status": "edited",
            "notes": "Merged manually in the PDF / Supplement Workbench.",
            "merged_block_ids": [first.get("id"), second.get("id")],
        }
        payload["reviewed_blocks"] = blocks[:first_index] + [merged] + blocks[second_index + 1 :]
        save_supplement_source_scan(data_dir, source_id, payload)
        return {"block": merged, "message": "Merged adjacent source blocks."}
    raise KeyError(block_id)


def merge_selected_supplement_source_blocks(data_dir: Path, source_id: str, block_ids: list[str]) -> dict[str, Any]:
    clean_ids = [str(block_id) for block_id in block_ids if str(block_id)]
    if len(clean_ids) < 2:
        raise ValueError("Select at least two blocks to merge.")
    payload = load_supplement_source_scan(data_dir, source_id)
    blocks = payload.get("reviewed_blocks", [])
    indexes = [index for index, block in enumerate(blocks) if isinstance(block, dict) and block.get("id") in clean_ids]
    if len(indexes) != len(set(clean_ids)):
        raise KeyError("One or more selected source blocks were not found.")
    indexes = sorted(indexes)
    if indexes != list(range(indexes[0], indexes[-1] + 1)):
        raise ValueError("Selected blocks must be adjacent before they can be merged.")
    selected = [blocks[index] for index in indexes]
    first = selected[0]
    last = selected[-1]
    merged = {
        **first,
        "id": f"{first.get('id')}-merged-{last.get('id')}",
        "text": "\n\n".join(str(block.get("text") or "").strip() for block in selected if str(block.get("text") or "").strip()),
        "review_status": "edited",
        "notes": "Merged manually from selected adjacent blocks in the PDF / Supplement Workbench.",
        "merged_block_ids": [block.get("id") for block in selected],
    }
    payload["reviewed_blocks"] = blocks[: indexes[0]] + [merged] + blocks[indexes[-1] + 1 :]
    save_supplement_source_scan(data_dir, source_id, payload)
    return {"block": merged, "message": f"Merged {len(selected)} selected source blocks."}


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


def supplement_source_artwork_path(data_dir: Path, source_id: str, filename: str) -> Path:
    safe = Path(str(filename or "")).name
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
                "supplement_title": str(payload.get("supplement_title") or payload.get("source_pdf") or source_id),
                "source_pdf": str(payload.get("source_pdf") or ""),
                "updated_at": str(payload.get("updated_at") or ""),
                "page_offset": int(payload.get("page_offset") or 0),
                "blocks": len(blocks),
                "raw_blocks": len(raw_blocks),
                "continuation_candidates": len(continuation_candidates),
                "artwork": len(artwork),
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
    for package_id, package_payload in setting_packages.items():
        if not isinstance(package_payload, dict):
            continue
        safe_id = supplement_package_id(str(package_payload.get("supplement_id") or package_id), str(package_id))
        assets = [item for item in package_payload.get("assets", []) if isinstance(item, dict)]
        grouped[safe_id] = {
            "supplement_id": safe_id,
            "supplement_title": str(package_payload.get("supplement_title") or safe_id),
            "source_count": 0,
            "asset_count": len(assets),
            "asset_categories": sorted(SUPPLEMENT_PACKAGE_ASSET_CATEGORIES),
            "blocks": 0,
            "artwork": 0,
            "reviewed_blocks": 0,
            "sources": [],
            "assets": assets,
        }
    for scan in list_supplement_source_scans(data_dir):
        package_id = supplement_package_id(str(scan.get("supplement_id") or ""), str(scan.get("source_id") or "supplement"))
        package = grouped.setdefault(
            package_id,
            {
                "supplement_id": package_id,
                "supplement_title": str(scan.get("supplement_title") or package_id),
                "source_count": 0,
                "asset_count": 0,
                "asset_categories": sorted(SUPPLEMENT_PACKAGE_ASSET_CATEGORIES),
                "blocks": 0,
                "artwork": 0,
                "reviewed_blocks": 0,
                "sources": [],
                "assets": [],
            },
        )
        package["source_count"] = int(package.get("source_count") or 0) + 1
        package["blocks"] = int(package.get("blocks") or 0) + int(scan.get("blocks") or 0)
        package["artwork"] = int(package.get("artwork") or 0) + int(scan.get("artwork") or 0)
        package["reviewed_blocks"] = int(package.get("reviewed_blocks") or 0) + int(scan.get("reviewed_blocks") or 0)
        package["sources"].append(scan)
    return sorted(grouped.values(), key=lambda item: str(item.get("supplement_title") or item.get("supplement_id") or ""))
