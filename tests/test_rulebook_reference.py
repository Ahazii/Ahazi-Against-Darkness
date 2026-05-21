from __future__ import annotations

from pathlib import Path

from app.rules.repository import RulesRepository


def test_rulebook_reference_loads() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    entries = rules.rulebook_reference()
    assert len(entries) >= 5
    assert any(entry.get("id") == "resting" for entry in entries)


def test_rulebook_reference_search_rest() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    payload = rules.search_reference(q="rest")
    ids = {entry["id"] for entry in payload["entries"]}
    assert "resting" in ids


def test_rulebook_reference_category_filter() -> None:
    root = Path(__file__).resolve().parents[1]
    rules = RulesRepository(root / "data" / "rules", root / "data" / "rules")
    payload = rules.search_reference(category="classes")
    assert payload["entries"]
    assert all(entry.get("category") == "classes" for entry in payload["entries"])
