from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .pdf_text_index import display_page_number, extract_rule_pdf_pages, page_label


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


def _source_block_id(source_id: str, source_page: int, pdf_page: int, index: int) -> str:
    if source_page == pdf_page:
        return f"{source_id}-p{source_page}-b{index:03d}"
    return f"{source_id}-p{source_page}-pdf{pdf_page}-b{index:03d}"


def scan_supplement_source_pdf(data_dir: Path, pdf_path: Path, *, now: str, page_offset: int = 0) -> dict[str, Any]:
    source_id = supplement_source_id(pdf_path)
    folder = supplement_source_folder(data_dir, source_id)
    folder.mkdir(parents=True, exist_ok=True)
    existing = load_supplement_source_scan(data_dir, source_id)
    existing_by_text: dict[tuple[int, str], dict[str, Any]] = {}
    for block in existing.get("blocks", []):
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "")
        pdf_page = int(block.get("pdf_page") or block.get("source_page") or 0)
        existing_by_text[(pdf_page, text)] = block
    blocks: list[dict[str, Any]] = []
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
            blocks.append(block)
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
    payload = {
        "schema_version": 1,
        "source_id": source_id,
        "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
        "updated_at": now,
        "page_offset": int(page_offset),
        "note": "Local/private PDF source blocks for human review and supplement assignment. Exact text remains in DATA_DIR.",
        "assignment_options": sorted(SOURCE_BLOCK_ASSIGNMENTS),
        "blocks": blocks,
        "continuation_candidates": continuation_candidates,
    }
    supplement_source_scan_path(data_dir, source_id).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "source_id": source_id,
        "source_pdf": f"DATA_DIR/rules/{pdf_path.name}",
        "blocks": len(blocks),
        "continuation_candidates": len(continuation_candidates),
        "pages": len(pages),
        "page_offset": int(page_offset),
        "path": str(supplement_source_scan_path(data_dir, source_id)),
        "message": f"Scanned {len(blocks)} review block(s) and {len(continuation_candidates)} page-boundary candidate(s) from {pdf_path.name} into DATA_DIR/Supplements/_sources/{source_id}/source_blocks.json.",
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


def list_supplement_source_scans(data_dir: Path) -> list[dict[str, Any]]:
    root = supplement_sources_root(data_dir)
    if not root.exists():
        return []
    scans: list[dict[str, Any]] = []
    for scan_path in sorted(root.glob("*/source_blocks.json")):
        source_id = scan_path.parent.name
        payload = load_supplement_source_scan(data_dir, source_id)
        blocks = [block for block in payload.get("blocks", []) if isinstance(block, dict)]
        continuation_candidates = [block for block in payload.get("continuation_candidates", []) if isinstance(block, dict)]
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
                "source_pdf": str(payload.get("source_pdf") or ""),
                "updated_at": str(payload.get("updated_at") or ""),
                "page_offset": int(payload.get("page_offset") or 0),
                "blocks": len(blocks),
                "continuation_candidates": len(continuation_candidates),
                "reviewed_blocks": reviewed,
                "assignment_counts": assignments,
                "path": str(scan_path),
            }
        )
    return scans
