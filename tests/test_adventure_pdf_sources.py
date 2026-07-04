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
    extract_adventure_package_candidates,
    load_adventure_package,
    package_detail,
    update_adventure_package_review,
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
    assert "nodes" in schema["properties"]
    assert "states" in schema["properties"]
    assert "rules" in schema["properties"]
    assert "ignored_records" in schema["properties"]
    assert "pins" in schema["properties"]["capabilities"]["items"]["enum"]
    assert "states" in schema["properties"]["capabilities"]["items"]["enum"]
    assert "rules" in schema["properties"]["capabilities"]["items"]["enum"]
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
    assert summary["maps"][0]["asset_path"] == "maps/manual-map-review-slot_1600x900.png"
    assert summary["maps"][0]["asset_url"] == "/api/adventures/packages/map-module-pdf/maps/manual-map-review-slot_1600x900.png"
    assert (data / "Adventures" / "map-module-pdf" / "maps" / "manual-map-review-slot_1600x900.README.txt").is_file()
    assert Path(summary["package_path"]).is_file()
    assert Path(summary["adventure_folder"]).name == "map-module-pdf"
    package = load_adventure_package(data, "map-module-pdf")
    assert package is not None
    assert package["source"]["source_pdf"] == "Adventure PDFs/Map Module.pdf"

    pinned = upsert_map_pin(
        data,
        "map-module-pdf",
        {
            "map_id": "manual-map-review-slot",
            "label": "1",
            "role": "entrance",
            "node_id": "room-1",
            "x": 42.5,
            "y": 63,
            "shape": "point",
            "notes": "Dungeon entrance marker on the reviewed map.",
        },
    )
    assert pinned["pin_count"] == 1
    assert pinned["maps"][0]["pins"][0]["role"] == "entrance"
    assert pinned["maps"][0]["pins"][0]["notes"] == "Dungeon entrance marker on the reviewed map."

    refreshed = create_or_refresh_package_from_pdf(root, data, "map-module-pdf")
    assert refreshed["pin_count"] == 1
    assert refreshed["maps"][0]["pins"][0]["node_id"] == "room-1"
    assert refreshed["maps"][0]["pins"][0]["role"] == "entrance"


def test_create_package_from_pdf_renders_map_pages_when_embedded_images_are_missing(monkeypatch, tmp_path: Path) -> None:
    from app.engine import adventure_packages

    root = tmp_path / "app"
    data = tmp_path / "data"
    root.mkdir()
    data.mkdir()
    pdf_dir = user_adventure_pdf_dir(data)
    pdf_dir.mkdir(parents=True)
    _write_blank_pdf(pdf_dir / "Rendered Map Module.pdf")
    scan_new_adventure_pdfs(root, data)

    def fake_no_embedded_images(pdf_path: Path, data_dir: Path, package_id: str, *, max_pages: int = 12):
        return []

    def fake_render_pages(pdf_path: Path, data_dir: Path, package_id: str, assessment: dict, *, max_pages: int = 12):
        asset_dir = adventure_packages.adventure_package_asset_dir(data_dir, package_id)
        (asset_dir / "page-004-render.png").write_bytes(b"fake png")
        return [
            {
                "id": "map-page-004-render",
                "title": "Page 4 rendered map review",
                "source_pdf": pdf_path.name,
                "source_page": 4,
                "asset_path": "maps/page-004-render.png",
                "coordinate_system": "percent",
                "pins": [],
                "extraction_note": "Rendered full PDF page because no embedded map image was exposed.",
            }
        ]

    monkeypatch.setattr(adventure_packages, "_extract_pdf_map_images", fake_no_embedded_images)
    monkeypatch.setattr(adventure_packages, "_render_pdf_map_pages", fake_render_pages)

    summary = create_or_refresh_package_from_pdf(root, data, "rendered-map-module-pdf")

    assert summary["map_count"] == 1
    assert summary["maps"][0]["id"] == "map-page-004-render"
    assert summary["maps"][0]["source_page"] == 4
    assert summary["maps"][0]["asset_exists"] is True
    assert "page-004-render.png" in summary["maps"][0]["asset_url"]
    assert (data / "Adventures" / "rendered-map-module-pdf" / "maps" / "page-004-render.png").is_file()


def test_adventure_package_schema_allows_role_marked_map_pins() -> None:
    schema = json.loads(Path("data/adventures/schema/adventure_package.v1.json").read_text(encoding="utf-8"))
    pin_schema = schema["properties"]["maps"]["items"]["properties"]["pins"]["items"]["properties"]
    assert "role" in pin_schema
    assert {"entrance", "exit", "stairs", "secret", "objective"}.issubset(set(pin_schema["role"]["enum"]))
    assert "notes" in pin_schema


def test_update_package_review_saves_nodes_and_reports_diagnostics(tmp_path: Path) -> None:
    root = tmp_path / "app"
    data = tmp_path / "data"
    root.mkdir()
    data.mkdir()
    pdf_dir = user_adventure_pdf_dir(data)
    pdf_dir.mkdir(parents=True)
    _write_blank_pdf(pdf_dir / "Review Module.pdf")
    scan_new_adventure_pdfs(root, data)
    create_or_refresh_package_from_pdf(root, data, "review-module-pdf")

    updated = update_adventure_package_review(
        data,
        "review-module-pdf",
        {
            "title": "Review Module",
            "source_pages": "1, 2, 5",
            "review_status": "review_in_progress",
            "review_notes": "Opening scene checked against the source PDF.",
            "nodes": [
                {
                    "id": "scene-1",
                    "type": "scene",
                    "title": "Opening Scene",
                    "source_page": 1,
                    "player_text": "The reviewed opening text.",
                    "app_notes": "Ask for a choice before branching.",
                    "foe_ids": ["black-knight"],
                    "item_ids": ["emerald-necklace"],
                    "procedure_ids": ["opening-choice"],
                    "branches": [{"label": "Continue", "to": "scene-2"}],
                    "review_status": "ready_for_manifest",
                },
                {
                    "id": "scene-2",
                    "type": "scene",
                    "title": "Second Scene",
                    "source_page": 2,
                    "player_text": "The reviewed follow-up text.",
                    "review_status": "checked",
                },
            ],
            "ignored_records": [
                {
                    "id": "page-header",
                    "name": "Page Header",
                    "source_page": 1,
                    "notes": "Marked wrong during review.",
                    "review_status": "ignored",
                    "original_list": "items",
                }
            ],
            "foes": [
                {
                    "id": "black-knight",
                    "name": "Black Knight",
                    "source_page": 2,
                    "notes": "HCL+2 boss, 5 Life.",
                    "review_status": "checked",
                    "life": 5,
                }
            ],
            "items": [
                {
                    "id": "emerald-necklace",
                    "name": "Emerald Necklace",
                    "source_page": 2,
                    "notes": "Reward item.",
                    "review_status": "needs_pdf_check",
                    "value_gp": 250,
                }
            ],
            "procedures": [
                {
                    "id": "opening-choice",
                    "title": "Opening Choice",
                    "source_page": 1,
                    "steps": [{"op": "show_choice", "choices": ["Continue"]}],
                    "review_status": "checked",
                }
            ],
        },
    )

    assert updated["title"] == "Review Module"
    assert updated["source"]["source_pages"] == [1, 2, 5]
    assert updated["review"]["status"] == "review_in_progress"
    assert updated["node_count"] == 2
    assert updated["ignored_record_count"] == 1
    assert updated["diagnostics"]["valid"] is True
    assert updated["diagnostics"]["errors"] == []
    detail = package_detail(data, "review-module-pdf")
    assert detail["nodes"][0]["id"] == "scene-1"
    assert detail["nodes"][0]["foe_ids"] == ["black-knight"]
    assert detail["nodes"][0]["item_ids"] == ["emerald-necklace"]
    assert detail["nodes"][0]["procedure_ids"] == ["opening-choice"]
    assert detail["foes"][0]["life"] == 5
    assert detail["items"][0]["value_gp"] == 250
    assert detail["procedures"][0]["steps"][0]["op"] == "show_choice"
    assert detail["ignored_records"][0]["original_list"] == "items"
    assert detail["review"]["notes"] == "Opening scene checked against the source PDF."


def test_package_candidate_extraction_populates_human_review_lists(monkeypatch, tmp_path: Path) -> None:
    from app.engine import adventure_packages

    root = tmp_path / "app"
    data = tmp_path / "data"
    root.mkdir()
    data.mkdir()
    pdf_dir = user_adventure_pdf_dir(data)
    pdf_dir.mkdir(parents=True)
    _write_blank_pdf(pdf_dir / "Candidate Module.pdf")
    scan_new_adventure_pdfs(root, data)

    def fake_pages(pdf_path: Path, *, max_pages: int = 80):
        return [
            {
                "page": 3,
                "text": """
                Room 1: Gatehouse
                The gatehouse smells of smoke. If you open the iron door, go to Room 2.
                Room 2: Chapel
                Test Save vs L4 or fight the Black Knight.
                Black Knight HCL+2 boss, 5 Life points, Morale +1.
                New character class: Cave Scout
                Treasure Table
                1-2 10 gp
                3-4 Potion of Healing
                5-6 Magic Sword
                The party may claim the Emerald Necklace reward.
                Special rule: when this happens, the alarm clock advances.
                Poisoned characters suffer a condition until cured.
                """,
            }
        ]

    monkeypatch.setattr(adventure_packages, "_extract_pdf_text_pages", fake_pages)

    summary = create_or_refresh_package_from_pdf(root, data, "candidate-module-pdf")

    assert summary["node_count"] >= 2
    assert summary["table_count"] >= 1
    assert summary["foe_count"] >= 1
    assert summary["class_count"] >= 1
    assert summary["item_count"] >= 1
    assert summary["state_count"] >= 1
    assert summary["rule_count"] >= 1
    package = load_adventure_package(data, "candidate-module-pdf")
    assert package is not None
    assert any(node["id"] == "room-1" for node in package["nodes"])
    assert any(table["title"] == "Treasure Table" for table in package["tables"])
    assert any(foe["name"] == "Black Knight" for foe in package["foes"])
    assert any("emerald-necklace" in item["id"] for item in package["items"])
    assert any("poisoned" in state["id"] for state in package["states"])
    assert any("special-rule" in rule["id"] or "alarm-clock" in rule["id"] for rule in package["rules"])

    # Re-running extraction merges by id instead of duplicating the candidate lists.
    updated = extract_adventure_package_candidates(root, data, "candidate-module-pdf")
    assert updated["candidate_changes"]["nodes"] == 0
    assert updated["candidate_changes"]["tables"] == 0
    assert updated["candidate_changes"]["states"] == 0
    assert updated["candidate_changes"]["rules"] == 0
