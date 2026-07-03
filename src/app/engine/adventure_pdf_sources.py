from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ADVENTURE_PDF_CACHE_FILENAME = "adventure_pdf_sources.json"
USER_ADVENTURE_PDF_DIRNAME = "Adventure PDFs"


@dataclass(frozen=True)
class AdventurePdfAssessment:
    id: str
    filename: str
    title: str
    source_path: str
    source_kind: str
    page_count: int
    encrypted: bool
    text_extractable: bool
    text_chars_first_pages: int
    text_density: int
    detected_type: str
    confidence: str
    conversion_status: str
    recommended_action: str
    map_signals: int
    table_signals: int
    foe_signals: int
    class_signals: int
    numbered_location_signals: int
    package_recommendation: str
    warnings: list[str]
    sample: str
    size_bytes: int
    mtime: float

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "title": self.title,
            "source_path": self.source_path,
            "source_kind": self.source_kind,
            "page_count": self.page_count,
            "encrypted": self.encrypted,
            "text_extractable": self.text_extractable,
            "text_chars_first_pages": self.text_chars_first_pages,
            "text_density": self.text_density,
            "detected_type": self.detected_type,
            "confidence": self.confidence,
            "conversion_status": self.conversion_status,
            "recommended_action": self.recommended_action,
            "map_signals": self.map_signals,
            "table_signals": self.table_signals,
            "foe_signals": self.foe_signals,
            "class_signals": self.class_signals,
            "numbered_location_signals": self.numbered_location_signals,
            "package_recommendation": self.package_recommendation,
            "warnings": self.warnings,
            "sample": self.sample,
            "size_bytes": self.size_bytes,
            "mtime": self.mtime,
        }


def adventure_pdf_cache_path(data_dir: Path) -> Path:
    return data_dir / ADVENTURE_PDF_CACHE_FILENAME


def user_adventure_pdf_dir(data_dir: Path) -> Path:
    return data_dir / USER_ADVENTURE_PDF_DIRNAME


def ensure_user_adventure_pdf_dir(data_dir: Path) -> Path:
    path = user_adventure_pdf_dir(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def adventure_pdf_source_dirs(root_dir: Path, data_dir: Path) -> list[tuple[str, Path]]:
    return [
        ("user", ensure_user_adventure_pdf_dir(data_dir)),
        ("legacy", root_dir / "Adventures"),
    ]


def load_adventure_pdf_assessments(data_dir: Path) -> dict[str, dict[str, Any]]:
    path = adventure_pdf_cache_path(data_dir)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    sources = payload.get("sources", {})
    if not isinstance(sources, dict):
        return {}
    return {str(key): value for key, value in sources.items() if isinstance(value, dict)}


def save_adventure_pdf_assessments(data_dir: Path, sources: dict[str, dict[str, Any]]) -> None:
    path = adventure_pdf_cache_path(data_dir)
    payload = {
        "schema_version": 1,
        "note": "Local cache of scanned adventure source PDFs. This records assessment metadata only; it does not convert or copy PDF text into playable modules.",
        "sources": dict(sorted(sources.items())),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _safe_pdf_id(path: Path, source_kind: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    slug = slug or "pdf-source"
    return slug if source_kind == "legacy" else f"{slug}-pdf"


def _clean_sample(text: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit]


def _title_from_text_or_filename(path: Path, text: str) -> str:
    compact = _clean_sample(text, 220)
    for splitter in (" Written by ", " A solitaire adventure", " An adventure", " Short Adventures"):
        if splitter in compact:
            compact = compact.split(splitter, 1)[0]
            break
    compact = compact.strip(" -:_")
    if 6 <= len(compact) <= 100 and not compact.lower().startswith("contents "):
        return compact
    return path.stem.replace("-", " ").replace("_", " ").title()


def _classify_pdf(text: str, page_count: int) -> tuple[str, str, str, list[str]]:
    lower = text.lower()
    warnings: list[str] = []
    scores = {
        "hex_crawl": 0,
        "short_adventure_collection": 0,
        "programmed_plus_random": 0,
        "programmed_wilderness": 0,
        "campaign_multi_part": 0,
        "supplement": 0,
        "programmed_dungeon": 0,
    }
    if "hex-crawl" in lower or "hex crawl" in lower or "numbered hexes" in lower:
        scores["hex_crawl"] += 5
    if "short adventures" in lower or re.search(r"adventure\s+1\s*:", lower):
        scores["short_adventure_collection"] += 4
    if "programmed dungeon" in lower:
        scores["programmed_dungeon"] += 4
    if "random dungeon" in lower and ("chapter two" in lower or "second" in lower):
        scores["programmed_plus_random"] += 4
    if "map of the" in lower and "chapter one" in lower:
        scores["programmed_plus_random"] += 2
        scores["programmed_dungeon"] += 2
    if "through the forest" in lower or "event tracker" in lower or "wilderness" in lower:
        scores["programmed_wilderness"] += 3
    if "three part adventure" in lower or "adventure one" in lower or "adventure two" in lower:
        scores["campaign_multi_part"] += 3
    if "new character class" in lower or "new rules" in lower or "table of contents" in lower and page_count > 50:
        scores["supplement"] += 2
    detected = max(scores, key=lambda key: scores[key])
    score = scores[detected]
    if score <= 1:
        detected = "unknown"
        confidence = "low"
    elif score < 4:
        confidence = "medium"
    else:
        confidence = "high"

    if detected == "hex_crawl":
        action = "Treat as a future hex-crawl importer target; do not force it into the room-manifest importer."
    elif detected == "short_adventure_collection":
        action = "Split into individual adventure records before creating any playable manifest."
    elif detected == "programmed_plus_random":
        action = "Create a draft manifest for the programmed chapter first; model later random chapters as custom rules/profile work."
    elif detected == "programmed_wilderness":
        action = "Create a draft route/scene manifest only after mapping its event tracker and branch rules."
    elif detected == "campaign_multi_part":
        action = "Split campaign parts into linked modules or a campaign bundle before import."
    elif detected == "supplement":
        action = "Inventory rules/tables separately before deciding whether a playable module exists."
    elif detected == "programmed_dungeon":
        action = "Candidate for the first draft-manifest extractor after map/key review."
    else:
        action = "Manual review needed before conversion."
        warnings.append("Could not confidently classify this PDF from the first extracted pages.")
    return detected, confidence, action, warnings


def _count_signal(text: str, patterns: tuple[str, ...]) -> int:
    lower = text.lower()
    return sum(len(re.findall(pattern, lower, flags=re.MULTILINE)) for pattern in patterns)


def _package_signals(text: str, detected_type: str) -> dict[str, int | str]:
    map_signals = _count_signal(
        text,
        (
            r"\bmap\b",
            r"\bhex-?map\b",
            r"\bnumbered hexes\b",
            r"\bnumbered locations\b",
            r"\bmap of\b",
        ),
    )
    table_signals = _count_signal(text, (r"\btable\b", r"\bd6\b", r"\b2d6\b", r"\bd66\b", r"\broll\b"))
    foe_signals = _count_signal(
        text,
        (
            r"\bvermin table\b",
            r"\bminion table\b",
            r"\bboss table\b",
            r"\bweird monster table\b",
            r"\bfinal boss\b",
            r"\bhcl\b",
            r"\blife points\b",
            r"\bmorale\b",
        ),
    )
    class_signals = _count_signal(
        text,
        (
            r"\bnew character class\b",
            r"\bnew class\b",
            r"^\s*class\s*:",
            r"\bclass abilities\b",
            r"\bstarting equipment\b",
        ),
    )
    numbered_location_signals = _count_signal(
        text,
        (
            r"^\s*\d{1,3}\s*[\).:-]",
            r"\bnumbered hexes\b",
            r"\bnumbered locations\b",
            r"\broom\s+\d{1,3}\b",
            r"\barea\s+\d{1,3}\b",
        ),
    )
    if class_signals:
        recommendation = "Needs adventure-package support for local classes before full conversion."
    elif map_signals and numbered_location_signals:
        recommendation = "Good candidate for PDF map-image import plus room/location pins."
    elif detected_type == "hex_crawl":
        recommendation = "Needs a map package with pinned hexes/locations before it becomes playable."
    elif table_signals or foe_signals:
        recommendation = "Needs adventure-package tables and foe/item additions before a playable manifest."
    else:
        recommendation = "Likely manifest-only after manual PDF review; no package signals found in scanned pages."
    return {
        "map_signals": map_signals,
        "table_signals": table_signals,
        "foe_signals": foe_signals,
        "class_signals": class_signals,
        "numbered_location_signals": numbered_location_signals,
        "package_recommendation": recommendation,
    }


def assess_adventure_pdf(path: Path, *, root_dir: Path, source_kind: str) -> AdventurePdfAssessment:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is present in app image/tests
        raise RuntimeError("pypdf is required to scan adventure PDFs.") from exc

    stat = path.stat()
    warnings: list[str] = []
    page_count = 0
    encrypted = False
    text = ""
    try:
        reader = PdfReader(str(path))
        encrypted = bool(reader.is_encrypted)
        page_count = len(reader.pages)
        page_texts: list[str] = []
        for page in reader.pages[: min(12, page_count)]:
            page_texts.append(page.extract_text() or "")
        text = "\n".join(page_texts)
    except Exception as exc:  # noqa: BLE001 - scanner should report bad PDFs, not crash the whole list
        warnings.append(f"PDF scan failed: {type(exc).__name__}: {exc}")
    text_chars = len(text)
    density = int(text_chars / max(1, min(12, page_count or 1)))
    text_extractable = text_chars >= 250
    if encrypted:
        warnings.append("PDF reports encryption/protection; extraction may require the server image cryptography support.")
    if not text_extractable:
        warnings.append("Low extracted text volume; this may be scanned/image-heavy or need manual OCR/review.")
    detected_type, confidence, action, classification_warnings = _classify_pdf(text, page_count)
    package_signals = _package_signals(text, detected_type)
    warnings.extend(classification_warnings)
    try:
        source_path = str(path.relative_to(root_dir)).replace("\\", "/")
    except ValueError:
        source_path = str(path)
    return AdventurePdfAssessment(
        id=_safe_pdf_id(path, source_kind),
        filename=path.name,
        title=_title_from_text_or_filename(path, text),
        source_path=source_path,
        source_kind=source_kind,
        page_count=page_count,
        encrypted=encrypted,
        text_extractable=text_extractable,
        text_chars_first_pages=text_chars,
        text_density=density,
        detected_type=detected_type,
        confidence=confidence,
        conversion_status="source_pdf_assessed",
        recommended_action=action,
        map_signals=int(package_signals["map_signals"]),
        table_signals=int(package_signals["table_signals"]),
        foe_signals=int(package_signals["foe_signals"]),
        class_signals=int(package_signals["class_signals"]),
        numbered_location_signals=int(package_signals["numbered_location_signals"]),
        package_recommendation=str(package_signals["package_recommendation"]),
        warnings=warnings,
        sample=_clean_sample(text),
        size_bytes=stat.st_size,
        mtime=stat.st_mtime,
    )


def _cache_key(path: Path, source_kind: str) -> str:
    return f"{source_kind}:{path.name}"


def scan_new_adventure_pdfs(root_dir: Path, data_dir: Path, *, force: bool = False) -> dict[str, Any]:
    sources = load_adventure_pdf_assessments(data_dir)
    scanned: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[str] = []
    for source_kind, directory in adventure_pdf_source_dirs(root_dir, data_dir):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.pdf")):
            key = _cache_key(path, source_kind)
            stat = path.stat()
            existing = sources.get(key)
            unchanged = (
                existing
                and existing.get("size_bytes") == stat.st_size
                and abs(float(existing.get("mtime", 0)) - stat.st_mtime) < 0.001
            )
            if unchanged and not force:
                skipped.append({"filename": path.name, "source_kind": source_kind, "reason": "already assessed"})
                continue
            try:
                assessment = assess_adventure_pdf(path, root_dir=root_dir, source_kind=source_kind)
            except RuntimeError as exc:
                errors.append(str(exc))
                continue
            data = assessment.to_json()
            sources[key] = data
            scanned.append(data)
    save_adventure_pdf_assessments(data_dir, sources)
    return {
        "scanned": scanned,
        "skipped": skipped,
        "sources": list(sources.values()),
        "errors": errors,
        "cache_path": str(adventure_pdf_cache_path(data_dir)),
        "user_pdf_dir": str(user_adventure_pdf_dir(data_dir)),
    }
