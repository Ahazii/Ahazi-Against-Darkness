from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def local_rule_text_index_path(rules_dir: Path) -> Path:
    return rules_dir / "rule_text_index.json"


def clean_rule_pdf_text(text: str) -> str:
    cleaned = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def rule_pdf_text_fingerprint(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def extract_rule_page_texts(page: Any) -> list[dict[str, str]]:
    variants: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_variant(method: str, text: str) -> None:
        cleaned = clean_rule_pdf_text(text)
        fingerprint = rule_pdf_text_fingerprint(cleaned)
        if not fingerprint or fingerprint in seen:
            return
        seen.add(fingerprint)
        variants.append({"method": method, "text": cleaned})

    try:
        add_variant("plain", page.extract_text(extraction_mode="plain") or "")
    except TypeError:
        add_variant("plain", page.extract_text() or "")
    try:
        add_variant("layout", page.extract_text(extraction_mode="layout") or "")
    except Exception:  # noqa: BLE001
        pass
    fragments: list[str] = []

    def visit_text(text: str, *_args: Any) -> None:
        if str(text or "").strip():
            fragments.append(str(text))

    try:
        page.extract_text(visitor_text=visit_text)
        add_variant("positioned", " ".join(fragment.strip() for fragment in fragments if fragment.strip()))
    except Exception:  # noqa: BLE001
        pass
    return variants


def primary_rule_page_text_variant(variants: list[dict[str, str]]) -> dict[str, str]:
    clean_variants = [variant for variant in variants if rule_pdf_text_fingerprint(variant.get("text", ""))]
    if not clean_variants:
        return {"method": "", "text": ""}
    lengths = [len(rule_pdf_text_fingerprint(variant.get("text", ""))) for variant in clean_variants]
    longest = max(lengths) if lengths else 0
    by_method = {str(variant.get("method") or ""): variant for variant in clean_variants}
    preferred = ["layout", "plain", "positioned"]
    for method in preferred:
        variant = by_method.get(method)
        if variant and len(rule_pdf_text_fingerprint(variant.get("text", ""))) >= int(longest * 0.85):
            return variant
    return max(clean_variants, key=lambda variant: len(rule_pdf_text_fingerprint(variant.get("text", ""))))


def extract_rule_pdf_pages(pdf_path: Path) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf is required to extract uploaded rule PDF text.") from exc
    try:
        reader = PdfReader(str(pdf_path))
        pages: list[dict[str, Any]] = []
        for index, page in enumerate(reader.pages, start=1):
            variants = extract_rule_page_texts(page)
            if not variants:
                continue
            primary = primary_rule_page_text_variant(variants)
            text = clean_rule_pdf_text(primary.get("text", ""))
            pages.append(
                {
                    "page": index,
                    "text": text,
                    "methods": [item["method"] for item in variants],
                    "primary_method": primary.get("method", ""),
                }
            )
        return pages
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        if "cryptography" in message.lower() or "aes" in message.lower():
            raise RuntimeError(
                "This PDF uses AES encryption/protection. Install the cryptography Python package "
                "in the running server image, then rebuild/restart the container and index again."
            ) from exc
        raise


def display_page_number(pdf_page: int, page_offset: int = 0) -> int:
    printed_page = int(pdf_page) + int(page_offset)
    return printed_page if printed_page > 0 else int(pdf_page)


def page_label(pdf_page: int, page_offset: int = 0) -> str:
    display_page = display_page_number(pdf_page, page_offset)
    if int(page_offset) and display_page != int(pdf_page):
        return f"p.{display_page} (PDF p.{int(pdf_page)})"
    return f"p.{display_page}"


def load_local_rule_text_index(rules_dir: Path) -> dict[str, Any]:
    path = local_rule_text_index_path(rules_dir)
    if not path.exists():
        return {"schema_version": 1, "updated_at": "", "documents": [], "entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "updated_at": "", "documents": [], "entries": []}
    if not isinstance(data, dict):
        return {"schema_version": 1, "updated_at": "", "documents": [], "entries": []}
    data.setdefault("schema_version", 1)
    data.setdefault("updated_at", "")
    data.setdefault("documents", [])
    data.setdefault("entries", [])
    return data


def local_rule_text_status(rules_dir: Path) -> dict[str, Any]:
    path = local_rule_text_index_path(rules_dir)
    data = load_local_rule_text_index(rules_dir)
    entries = [entry for entry in data.get("entries", []) if isinstance(entry, dict)]
    documents = [item for item in data.get("documents", []) if isinstance(item, dict)]
    return {
        "path": str(path),
        "exists": path.exists(),
        "updated_at": str(data.get("updated_at") or ""),
        "documents": documents,
        "document_count": len(documents),
        "entry_count": len(entries),
    }


def local_rule_text_entries(rules_dir: Path) -> list[dict[str, Any]]:
    data = load_local_rule_text_index(rules_dir)
    entries: list[dict[str, Any]] = []
    for entry in data.get("entries", []):
        if not isinstance(entry, dict):
            continue
        body = str(entry.get("body") or "")
        if not body.strip():
            continue
        item = dict(entry)
        item.setdefault("category", "pdf_text")
        item.setdefault("implementation_status", "local_exact")
        item.setdefault("keywords", [])
        entries.append(item)
    return entries


def rule_reference_entry_matches(
    entry: dict[str, Any],
    *,
    q: str | None = None,
    category: str | None = None,
    implementation_status: str | None = None,
) -> bool:
    if category and str(entry.get("category", "")).lower() != category.strip().lower():
        return False
    if implementation_status and str(entry.get("implementation_status", "")).lower() != implementation_status.strip().lower():
        return False
    query = " ".join(str(q or "").split()).strip().lower()
    if not query:
        return True
    haystack = " ".join(
        [
            str(entry.get("id") or ""),
            str(entry.get("title") or ""),
            str(entry.get("summary") or ""),
            str(entry.get("body") or ""),
            str(entry.get("source") or ""),
            " ".join(str(item) for item in entry.get("keywords", []) if item is not None),
        ]
    ).lower()
    return all(term in haystack for term in query.split())


def merge_local_rule_text_reference(
    payload: dict[str, Any],
    *,
    rules_dir: Path,
    audience: str | None = None,
    q: str | None = None,
    category: str | None = None,
    implementation_status: str | None = None,
) -> dict[str, Any]:
    if (audience or "player").strip().lower() == "developer":
        return payload
    entries = [
        entry
        for entry in local_rule_text_entries(rules_dir)
        if rule_reference_entry_matches(entry, q=q, category=category, implementation_status=implementation_status)
    ]
    if not entries:
        return {**payload, "local_rule_text": local_rule_text_status(rules_dir)}
    merged = [*payload.get("entries", []), *entries]
    return {**payload, "count": len(merged), "entries": merged, "local_rule_text": local_rule_text_status(rules_dir)}


def build_rule_text_index_for_pdf(rules_dir: Path, pdf_path: Path, *, now: str, page_offset: int = 0) -> dict[str, Any]:
    rules_dir.mkdir(parents=True, exist_ok=True)
    pages = extract_rule_pdf_pages(pdf_path)
    existing = load_local_rule_text_index(rules_dir)
    source = f"DATA_DIR/rules/{pdf_path.name}"
    entries = [
        entry
        for entry in existing.get("entries", [])
        if isinstance(entry, dict) and entry.get("source") != source
    ]
    documents = [
        item
        for item in existing.get("documents", [])
        if isinstance(item, dict) and item.get("filename") != pdf_path.name
    ]
    stem = re.sub(r"[^a-z0-9]+", "-", pdf_path.stem.lower()).strip("-") or "rules-pdf"
    for page in pages:
        page_number = int(page["page"])
        source_page = display_page_number(page_number, page_offset)
        label = page_label(page_number, page_offset)
        text = str(page["text"])
        entries.append(
            {
                "id": f"local-pdf-{stem}-p{page_number}",
                "title": f"{pdf_path.stem} {label}",
                "category": "pdf_text",
                "implementation_status": "local_exact",
                "source_page": source_page,
                "pdf_page": page_number,
                "page_offset": int(page_offset),
                "page_label": label,
                "source": source,
                "summary": f"Exact local PDF text from {pdf_path.name}, {label}.",
                "body": text,
                "extraction_methods": list(page.get("methods") or []),
                "keywords": [pdf_path.stem, pdf_path.name, "exact pdf text", "local rules pdf"],
            }
        )
    documents.append(
        {
            "filename": pdf_path.name,
            "source": source,
            "size_bytes": pdf_path.stat().st_size,
            "indexed_at": now,
            "pages_indexed": len(pages),
            "page_offset": int(page_offset),
        }
    )
    index = {
        "schema_version": 1,
        "updated_at": now,
        "note": "Local/private exact rules PDF text. This file lives in DATA_DIR/rules and must not be committed.",
        "documents": sorted(documents, key=lambda item: str(item.get("filename", "")).lower()),
        "entries": sorted(entries, key=lambda item: (str(item.get("source", "")).lower(), int(item.get("source_page") or 0))),
    }
    local_rule_text_index_path(rules_dir).write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "filename": pdf_path.name,
        "pages_indexed": len(pages),
        "entries_indexed": len(pages),
        "page_offset": int(page_offset),
        "index_path": str(local_rule_text_index_path(rules_dir)),
        "message": f"Indexed {len(pages)} page(s) from {pdf_path.name} into DATA_DIR/rules/rule_text_index.json.",
        "index_status": local_rule_text_status(rules_dir),
    }


def update_rule_text_index_page_offset(rules_dir: Path, pdf_path: Path, *, page_offset: int, now: str) -> dict[str, Any]:
    """Relabel an already-indexed PDF without extracting its text again."""
    index = load_local_rule_text_index(rules_dir)
    source = f"DATA_DIR/rules/{pdf_path.name}"
    changed_entries = 0
    for entry in index.get("entries", []):
        if not isinstance(entry, dict) or str(entry.get("source") or "") != source:
            continue
        try:
            pdf_page = int(entry.get("pdf_page") or 0)
        except (TypeError, ValueError):
            continue
        if pdf_page < 1:
            continue
        label = page_label(pdf_page, page_offset)
        entry["source_page"] = display_page_number(pdf_page, page_offset)
        entry["page_offset"] = int(page_offset)
        entry["page_label"] = label
        entry["title"] = f"{pdf_path.stem} {label}"
        entry["summary"] = f"Exact local PDF text from {pdf_path.name}, {label}."
        changed_entries += 1

    changed_documents = 0
    for document in index.get("documents", []):
        if not isinstance(document, dict) or str(document.get("filename") or "") != pdf_path.name:
            continue
        document["page_offset"] = int(page_offset)
        changed_documents += 1

    if changed_entries or changed_documents:
        index["updated_at"] = now
        index["entries"] = sorted(
            [entry for entry in index.get("entries", []) if isinstance(entry, dict)],
            key=lambda item: (str(item.get("source", "")).lower(), int(item.get("pdf_page") or 0)),
        )
        local_rule_text_index_path(rules_dir).write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "entries_updated": changed_entries,
        "documents_updated": changed_documents,
        "page_offset": int(page_offset),
    }
