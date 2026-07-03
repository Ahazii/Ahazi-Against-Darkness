from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfWriter

from app.engine.adventure_pdf_sources import (
    adventure_pdf_cache_path,
    scan_new_adventure_pdfs,
    user_adventure_pdf_dir,
)


def _write_blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    with path.open("wb") as handle:
        writer.write(handle)


def test_scan_new_adventure_pdfs_assesses_and_caches_user_folder(tmp_path: Path) -> None:
    root = tmp_path / "app"
    data = tmp_path / "data"
    root.mkdir()
    data.mkdir()
    pdf_dir = user_adventure_pdf_dir(data)
    pdf_dir.mkdir(parents=True)
    _write_blank_pdf(pdf_dir / "Test Dungeon.pdf")

    result = scan_new_adventure_pdfs(root, data)

    assert len(result["scanned"]) == 1
    scanned = result["scanned"][0]
    assert scanned["filename"] == "Test Dungeon.pdf"
    assert scanned["source_kind"] == "user"
    assert scanned["conversion_status"] == "source_pdf_assessed"
    assert scanned["text_extractable"] is False
    assert "Manual review" in scanned["recommended_action"] or scanned["recommended_action"]
    cache = json.loads(adventure_pdf_cache_path(data).read_text(encoding="utf-8"))
    assert "user:Test Dungeon.pdf" in cache["sources"]

    second = scan_new_adventure_pdfs(root, data)
    assert second["scanned"] == []
    assert second["skipped"][0]["reason"] == "already assessed"


def test_scan_new_adventure_pdfs_classifies_hex_crawl_text(monkeypatch, tmp_path: Path) -> None:
    from app.engine import adventure_pdf_sources

    root = tmp_path / "app"
    legacy = root / "Adventures"
    data = tmp_path / "data"
    legacy.mkdir(parents=True)
    data.mkdir()
    path = legacy / "Hex Trouble.pdf"
    _write_blank_pdf(path)

    def fake_assess(pdf_path: Path, *, root_dir: Path, source_kind: str):
        detected, confidence, action, warnings = adventure_pdf_sources._classify_pdf(
            "A Four Against Darkness Hex-Crawl Adventure. Numbered hexes, blank hexes, tunnels, and a full page hex-map.",
            53,
        )
        return adventure_pdf_sources.AdventurePdfAssessment(
            id="hex-trouble",
            filename=pdf_path.name,
            title="Hex Trouble",
            source_path="Adventures/Hex Trouble.pdf",
            source_kind=source_kind,
            page_count=53,
            encrypted=False,
            text_extractable=True,
            text_chars_first_pages=400,
            text_density=80,
            detected_type=detected,
            confidence=confidence,
            conversion_status="source_pdf_assessed",
            recommended_action=action,
            warnings=warnings,
            sample="Hex crawl sample.",
            size_bytes=pdf_path.stat().st_size,
            mtime=pdf_path.stat().st_mtime,
        )

    monkeypatch.setattr(adventure_pdf_sources, "assess_adventure_pdf", fake_assess)

    result = scan_new_adventure_pdfs(root, data)

    assert result["scanned"][0]["detected_type"] == "hex_crawl"
    assert "hex-crawl importer" in result["scanned"][0]["recommended_action"]
