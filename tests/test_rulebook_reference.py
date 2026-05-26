from __future__ import annotations

import json
from pathlib import Path

from app.rules.repository import RulesRepository


def test_rulebook_reference_loads() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    entries = rules.rulebook_reference()
    assert len(entries) >= 110
    assert any(entry.get("id") == "resting" for entry in entries)
    assert all(entry.get("implementation_status") for entry in entries)
    per_skill = [entry for entry in entries if str(entry.get("id", "")).startswith("expert_skill_")]
    assert per_skill == []


def test_rulebook_reference_no_per_skill_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    ids = {entry.get("id") for entry in rules.rulebook_reference()}
    assert "expert_skills" in ids
    assert "expert_spells" in ids
    assert "expert_skill_effects" not in ids
    assert not any(item.startswith("expert_skill_") for item in ids if item not in {"expert_skills", "expert_spells"})


def test_rulebook_reference_search_rest() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    payload = rules.search_reference(q="rest")
    ids = {entry["id"] for entry in payload["entries"]}
    assert "resting" in ids


def test_rulebook_reference_merges_appdata_override(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    packaged = root / "data" / "rules"
    override = tmp_path / "rules"
    override.mkdir()
    (override / "rulebook_reference.json").write_text(
        json.dumps({"entries": [{"id": "resting", "title": "Custom Rest Title", "category": "exploration"}]}),
        encoding="utf-8",
    )
    rules = RulesRepository(packaged, override)
    entries = rules.rulebook_reference()
    assert len(entries) >= 110
    resting = next(entry for entry in entries if entry["id"] == "resting")
    assert resting["title"] == "Custom Rest Title"
    assert any(entry["id"] == "dungeon_entrance" for entry in entries)


def test_rulebook_reference_category_filter() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    payload = rules.search_reference(category="classes")
    assert payload["entries"]
    assert all(entry.get("category") == "classes" for entry in payload["entries"])
