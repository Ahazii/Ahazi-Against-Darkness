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
    assert any("foe spawn name" in error for error in result.errors)


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


GEMINI_RAW = ROOT / "data" / "adventures" / "api-import-test" / "gemini-raw.json"


def test_missing_source_still_reports_room_errors(repo: RulesRepository) -> None:
    if not GEMINI_RAW.exists():
        pytest.skip("gemini fixture missing")
    data = json.loads(GEMINI_RAW.read_text(encoding="utf-8"))
    result = validate_adventure_manifest(data, rules_repo=repo)
    assert not result.valid
    assert any("Missing required field 'source'" in error for error in result.errors)
    assert any("tile_key" in error for error in result.errors)
    assert len(result.errors) > 10
    assert result.error_summary
    assert any("tile_key" in line for line in result.error_summary)
    assert any("Fallen Prior" in line or "Skeletons" in line for line in result.error_summary)


def test_warns_on_missing_reciprocal_exit(repo: RulesRepository) -> None:
    manifest = {
        "schema_version": 1,
        "id": "one-way",
        "title": "One Way",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
        "entrance_room_id": "a",
        "exit_room_id": "a",
        "quest": {
            "key": "slay_all",
            "objective_text": "Test",
            "complete_when": {"type": "room_reached", "room_id": "a"},
        },
        "rooms": [
            {
                "id": "a",
                "tile_key": "02",
                "title": "A",
                "description": "A",
                "exits": [
                    {
                        "id": "a-n",
                        "direction": "north",
                        "to": "b",
                        "kind": "passage",
                        "status": "open",
                    }
                ],
            },
            {
                "id": "b",
                "tile_key": "15",
                "title": "B",
                "description": "B",
                "exits": [],
            },
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    result = validate_adventure_manifest(manifest, rules_repo=repo)
    assert result.valid, result.errors
    assert any("reciprocal" in warning for warning in result.warnings)


def test_rejects_exit_kind_mismatch(repo: RulesRepository) -> None:
    manifest = {
        "schema_version": 1,
        "id": "kind-mismatch",
        "title": "Mismatch",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
        "entrance_room_id": "a",
        "exit_room_id": "a",
        "quest": {
            "key": "slay_all",
            "objective_text": "Test",
            "complete_when": {"type": "room_reached", "room_id": "a"},
        },
        "rooms": [
            {
                "id": "a",
                "tile_key": "02",
                "title": "A",
                "description": "A",
                "exits": [
                    {
                        "id": "a-e",
                        "direction": "east",
                        "to": "a",
                        "kind": "passage",
                        "status": "open",
                    }
                ],
            }
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    result = validate_adventure_manifest(manifest, rules_repo=repo)
    assert not result.valid
    assert any("kind" in error and "door" in error for error in result.errors)


def test_summarize_groups_repetitive_exit_errors(repo: RulesRepository, example_manifest: dict) -> None:
    bad = copy.deepcopy(example_manifest)
    for room in bad["rooms"]:
        room["exits"] = [{"direction": "north", "to": bad["rooms"][0]["id"]}]
    result = validate_adventure_manifest(bad, rules_repo=repo)
    assert not result.valid
    assert any("missing 'id'" in line for line in result.error_summary)
    assert any("missing 'kind'" in line for line in result.error_summary)
