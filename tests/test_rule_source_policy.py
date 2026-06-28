from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "Rules"
DATA_RULES_DIR = ROOT / "data" / "rules"


def _local_rule_pdf_names() -> list[str]:
    return sorted(path.name for path in RULES_DIR.glob("*.pdf"))


def _walk_sources(value: Any) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, child in value.items():
            if key == "source" and isinstance(child, str):
                found.append(child)
            found.extend(_walk_sources(child))
        return found
    if isinstance(value, list):
        found: list[str] = []
        for child in value:
            found.extend(_walk_sources(child))
        return found
    return []


CORE_RULEBOOKS = (
    "Four_Against_Darkness_Expanded_Edition.pdf",
    "Four-Against-the-Abyss.pdf",
    "Four_Against_the_Forsaken_Depths.pdf",
    "The_Courtship_of_Flower_Demons.pdf",
    "Tales_from_the_adventurers_guild.pdf",
    "Four Against_the_Netherworld.pdf",
)


def test_local_rules_folder_contains_core_rulebooks() -> None:
    pdfs = set(_local_rule_pdf_names())
    assert pdfs
    for pdf_name in CORE_RULEBOOKS:
        assert pdf_name in pdfs, pdf_name


def test_rule_coverage_lists_core_rules_pdfs() -> None:
    body = (ROOT / "docs" / "RULE_COVERAGE.md").read_text(encoding="utf-8")
    for pdf_name in CORE_RULEBOOKS:
        assert f"`Rules/{pdf_name}`" in body
    assert "Available for later extraction, not yet indexed/implemented" not in body


def test_packaged_rule_source_fields_reference_allowed_pdfs() -> None:
    allowed_markers = {
        "Expanded Edition",
        "Four Against Darkness",
        "Four Against the Abyss",
        "Four Against the Forsaken Depths",
        "Forsaken Depths",
        "Rules/Four_Against_the_Forsaken_Depths.pdf",
        "Fortress of the Warlord",
        "Tales from the Adventurers Guild",
        "Adventurers Guild",
        "Netherworld",
        "Courtship of Flower Demons",
        "TCOTFD",
        "4AD Magic Treasure",
        "4AD p.158",
        "Rules/The_Courtship_of_Flower_Demons.pdf",
        "Rules/Four_Against_Darkness_Expanded_Edition.pdf",
    }
    sources: list[str] = []
    for path in DATA_RULES_DIR.glob("*.json"):
        sources.extend(_walk_sources(json.loads(path.read_text(encoding="utf-8"))))

    invalid = [
        source
        for source in sorted(set(sources))
        if not any(marker in source for marker in allowed_markers)
    ]
    assert invalid == []
