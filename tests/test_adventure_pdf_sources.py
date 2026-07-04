from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfWriter

from app.engine.adventure_pdf_sources import (
    adventure_pdf_cache_path,
    scan_new_adventure_pdfs,
    user_adventure_pdf_dir,
)
from app.engine.adventure_packages import (
    create_or_refresh_package_from_pdf,
    load_adventure_package,
    upsert_map_pin,
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
            map_signals=2,
            table_signals=0,
            foe_signals=0,
            class_signals=0,
            numbered_location_signals=1,
            package_recommendation="Good candidate for PDF map-image import plus room/location pins.",
            warnings=warnings,
            sample="Hex crawl sample.",
            size_bytes=pdf_path.stat().st_size,
            mtime=pdf_path.stat().st_mtime,
        )

    monkeypatch.setattr(adventure_pdf_sources, "assess_adventure_pdf", fake_assess)

    result = scan_new_adventure_pdfs(root, data)

    assert result["scanned"][0]["detected_type"] == "hex_crawl"
    assert "hex-crawl importer" in result["scanned"][0]["recommended_action"]
    assert result["scanned"][0]["map_signals"] == 2
    assert result["scanned"][0]["numbered_location_signals"] == 1
    assert "map-image import" in result["scanned"][0]["package_recommendation"]


def test_package_signals_identify_maps_tables_foes_and_classes() -> None:
    from app.engine import adventure_pdf_sources

    signals = adventure_pdf_sources._package_signals(
        """
        Map of the ruins. Numbered locations:
        1) Gatehouse
        2) Chapel
        Roll d6 on the minion table. The final boss has HCL+2 life points.
        New character class: Cave Scout. Starting equipment follows.
        """,
        "programmed_dungeon",
    )

    assert signals["map_signals"] >= 2
    assert signals["numbered_location_signals"] >= 2
    assert signals["table_signals"] >= 2
    assert signals["foe_signals"] >= 2
    assert signals["class_signals"] >= 2
    assert "local classes" in signals["package_recommendation"]


def test_adventure_package_schema_is_declarative_and_map_pin_ready() -> None:
    schema_path = Path("data/adventures/schema/adventure_package.v1.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    procedure_op = (
        schema["properties"]["procedures"]["items"]["properties"]["steps"]["items"]["properties"]["op"]["enum"]
    )

    assert "maps" in schema["properties"]
    assert "pins" in schema["properties"]["capabilities"]["items"]["enum"]
    assert "pin_location" in procedure_op
    assert "script" not in procedure_op
    assert "javascript" not in procedure_op
    assert "python" not in procedure_op


def test_create_package_from_pdf_creates_manual_map_slot_and_preserves_pins(tmp_path: Path) -> None:
    root = tmp_path / "app"
    data = tmp_path / "data"
    root.mkdir()
    data.mkdir()
    pdf_dir = user_adventure_pdf_dir(data)
    pdf_dir.mkdir(parents=True)
    _write_blank_pdf(pdf_dir / "Map Module.pdf")
    scan_new_adventure_pdfs(root, data)

    summary = create_or_refresh_package_from_pdf(root, data, "map-module-pdf")

    assert summary["package_id"] == "map-module-pdf"
    assert summary["map_count"] == 1
    assert summary["maps"][0]["id"] == "manual-map-review-slot"
    assert summary["maps"][0]["asset_path"] == "adventures/map-module-pdf/maps/manual-map-review-slot_1600x900.png"
    assert (data / "assets" / "adventures" / "map-module-pdf" / "maps" / "manual-map-review-slot_1600x900.README.txt").is_file()
    assert Path(summary["package_path"]).is_file()
    package = load_adventure_package(data, "map-module-pdf")
    assert package is not None
    assert package["source"]["source_pdf"] == "Adventure PDFs/Map Module.pdf"

    pinned = upsert_map_pin(
        data,
        "map-module-pdf",
        {
            "map_id": "manual-map-review-slot",
            "label": "1",
            "node_id": "room-1",
            "x": 42.5,
            "y": 63,
            "shape": "point",
        },
    )
    assert pinned["pin_count"] == 1

    refreshed = create_or_refresh_package_from_pdf(root, data, "map-module-pdf")
    assert refreshed["pin_count"] == 1
    assert refreshed["maps"][0]["pins"][0]["node_id"] == "room-1"
