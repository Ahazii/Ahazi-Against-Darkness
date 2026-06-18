from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.engine.adventure_manifest import load_adventure_manifest, validate_adventure_manifest
from app.rules.repository import RulesRepository

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules"
EXAMPLE = ROOT / "data" / "adventures" / "examples" / "crypt-of-whispers" / "adventure.json"


@pytest.fixture
def repo() -> RulesRepository:
    return RulesRepository(RULES, RULES / "_override")


@pytest.fixture
def example_manifest() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_manifest_validates(repo: RulesRepository, example_manifest: dict) -> None:
    result = validate_adventure_manifest(example_manifest, rules_repo=repo)
    assert result.valid, result.errors


def test_load_example_from_disk() -> None:
    manifest, result = load_adventure_manifest(EXAMPLE)
    assert result.valid, result.errors
    assert manifest is not None
    assert manifest["id"] == "crypt-of-whispers"
    assert len(manifest["rooms"]) == 5


def test_rejects_unknown_monster(repo: RulesRepository, example_manifest: dict) -> None:
    bad = copy.deepcopy(example_manifest)
    bad["rooms"][1]["triggers"][0]["encounter"]["foes"][0]["name"] = "Not A Real Monster"
    result = validate_adventure_manifest(bad, rules_repo=repo)
    assert not result.valid
    assert any("monster spawn name" in error for error in result.errors)


def test_rejects_unreachable_room(repo: RulesRepository, example_manifest: dict) -> None:
    bad = copy.deepcopy(example_manifest)
    bad["rooms"].append(
        {
            "id": "island-room",
            "tile_key": "15",
            "title": "Isolated",
            "description": "No exits in or out.",
            "exits": [],
        }
    )
    result = validate_adventure_manifest(bad, rules_repo=repo)
    assert not result.valid
    assert any("not connected" in error for error in result.errors)


def test_rejects_unknown_exit_target(repo: RulesRepository, example_manifest: dict) -> None:
    bad = copy.deepcopy(example_manifest)
    bad["rooms"][0]["exits"][0]["to"] = "missing-room"
    result = validate_adventure_manifest(bad, rules_repo=repo)
    assert not result.valid
    assert any("does not match any room id" in error for error in result.errors)


def test_rejects_forbidden_top_level_key(repo: RulesRepository, example_manifest: dict) -> None:
    bad = copy.deepcopy(example_manifest)
    bad["dice"] = [1, 2, 3]
    result = validate_adventure_manifest(bad, rules_repo=repo)
    assert not result.valid
    assert any("Forbidden top-level key 'dice'" in error for error in result.errors)


def test_rejects_invalid_tile_key(repo: RulesRepository, example_manifest: dict) -> None:
    bad = copy.deepcopy(example_manifest)
    bad["rooms"][0]["tile_key"] = "99"
    result = validate_adventure_manifest(bad, rules_repo=repo)
    assert not result.valid
    assert any("tile_key" in error for error in result.errors)


def test_rejects_extra_foe_fields(repo: RulesRepository, example_manifest: dict) -> None:
    bad = copy.deepcopy(example_manifest)
    bad["rooms"][1]["triggers"][0]["encounter"]["foes"][0]["hp"] = 10
    result = validate_adventure_manifest(bad, rules_repo=repo)
    assert not result.valid
    assert any("unsupported fields" in error for error in result.errors)


def test_rejects_unknown_trap_key(repo: RulesRepository, example_manifest: dict) -> None:
    bad = copy.deepcopy(example_manifest)
    bad["rooms"][0]["trap"] = {"key": "not_a_trap", "level": 2}
    result = validate_adventure_manifest(bad, rules_repo=repo)
    assert not result.valid
    assert any("trap key" in error for error in result.errors)


def test_accepts_known_trap_key(repo: RulesRepository, example_manifest: dict) -> None:
    good = copy.deepcopy(example_manifest)
    good["rooms"][0]["trap"] = {"key": "dart", "level": 2}
    result = validate_adventure_manifest(good, rules_repo=repo)
    assert result.valid, result.errors


def test_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    manifest, result = load_adventure_manifest(path)
    assert manifest is None
    assert not result.valid
    assert any("Invalid JSON" in error for error in result.errors)
