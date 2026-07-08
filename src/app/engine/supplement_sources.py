from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .pdf_text_index import extract_rule_pdf_pages


SOURCE_BLOCK_ASSIGNMENTS = {
    "unassigned",
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


def supplement_source_folder(data_dir: Path, source_id: str) -> Path:
    safe = re.sub(r"[^a-z0-9._-]+", "-", source_id.lower()).strip(".-")
    return supplement_sources_root(data_dir) / (safe or "pdf-source")


def supplement_source_scan_path(data_dir: Path, source_id: str) -> Path:
    return supplement_source_folder(data_dir, source_id) / "source_blocks.json"


def _page_text_blocks(text: str) -> list[str]:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", raw) if block.strip()]
    if len(blocks) <= 1:
        blocks = [block.strip() for block in raw.splitlines() if block.strip()]
    return blocks


def scan_supplement_source_pdf(data_dir: Path, pdf_path: Path, *, now: str) -> dict[str, Any]:
    source_id = supplement_source_id(pdf_path)
    folder = supplement_source_folder(data_dir, source_id)
    folder.mkdir(parents=True, exist_ok=True)
    existing = load_supplement_source_scan(data_dir, source_id)
    existing_by_text = {
        (int(block.get("source_page") or 0), str(block.get("text") or "")): block
        for block in existing.get("blocks", [])
        if isinstance(block, dict)
    }
    blocks: list[dict[str, Any]] = []
    pages = extract_rule_pdf_pages(pdf_path)
    for page in pages:
        page_no = int(page.get("page") or 0)
        methods = list(page.get("methods") or [])
        for index, text in enumerate(_page_text_blocks(str(page.get("text") or "")), start=1):
            previous = existing_by_text.get((page_no, text), {})
            assignment = str(previous.get("assignment") or "unassigned")
            if assignment not in SOURCE_BLOCK_ASSIGNMENTS:
                assignment = "unassigned"
            blocks.append(
                {
                    "id": f"{source_id}-p{page_no}-b{index:03d}",
                    "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
                    "source_page": page_no,
                    "block_index": index,
                    "assignment": assignment,
                    "review_status": str(previous.get("review_status") or "unreviewed"),
                    "text": text,
                    "extraction_methods": methods,
                    "notes": str(previous.get("notes") or ""),
                }
            )
    payload = {
        "schema_version": 1,
        "source_id": source_id,
        "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
        "updated_at": now,
        "note": "Local/private PDF source blocks for human review and supplement assignment. Exact text remains in DATA_DIR.",
        "assignment_options": sorted(SOURCE_BLOCK_ASSIGNMENTS),
        "blocks": blocks,
    }
    supplement_source_scan_path(data_dir, source_id).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "source_id": source_id,
        "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
        "blocks": len(blocks),
        "pages": len(pages),
        "path": str(supplement_source_scan_path(data_dir, source_id)),
        "message": f"Scanned {len(blocks)} review block(s) from {pdf_path.name} into DATA_DIR/Supplements/_sources/{source_id}/source_blocks.json.",
    }


def load_supplement_source_scan(data_dir: Path, source_id: str) -> dict[str, Any]:
    path = supplement_source_scan_path(data_dir, source_id)
    if not path.exists():
        return {"schema_version": 1, "source_id": source_id, "blocks": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "source_id": source_id, "blocks": []}
    return payload if isinstance(payload, dict) else {"schema_version": 1, "source_id": source_id, "blocks": []}
