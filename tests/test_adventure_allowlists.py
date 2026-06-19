from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.adventure_allowlists import (
    EXIT_DIRECTIONS,
    build_adventure_allowlists,
    build_boss_spawn_names,
    build_environment_pack,
    foe_names_for_validation,
)
from app.engine.adventure_manifest import validate_adventure_manifest
from app.engine.adventure_prompt import build_adventure_prompt, load_allowlists_payload
from app.rules.repository import RulesRepository
from app.schemas import AdventurePromptParameters

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules"


@pytest.fixture
def repo() -> RulesRepository:
    return RulesRepository(RULES, RULES / "_override")


def test_allowlists_include_schema_enums(repo: RulesRepository) -> None:
    allowlists = build_adventure_allowlists(repo, environment="dungeon")
    assert allowlists["source"] == "live_rules"
    assert list(EXIT_DIRECTIONS) == allowlists["exit_directions"]
    assert "foe_spawn_names" in allowlists
    assert "monsters_by_table" in allowlists
    assert "equipment_by_category" in allowlists
    assert "environment_packs" in allowlists
    assert "for_environment" in allowlists
    assert allowlists["for_environment"]["environment"] == "dungeon"


def test_prompt_allowlists_match_live_rules(repo: RulesRepository) -> None:
    live = build_adventure_allowlists(repo, environment="dungeon")
    prompt_lists = load_allowlists_payload(repo, environment="dungeon")
    assert prompt_lists["monster_spawn_names"] == live["monster_spawn_names"]
    assert prompt_lists["foe_spawn_names"] == live["foe_spawn_names"]
    assert prompt_lists["trap_keys"] == live["trap_keys"]


def test_prompt_includes_environment_pack_and_exit_directions(repo: RulesRepository) -> None:
    bosses = build_boss_spawn_names(repo)
    params = AdventurePromptParameters(
        theme="goblin warren",
        environment="dungeon",
        boss_type=bosses[0],
    )
    prompt = build_adventure_prompt(params, repo=repo)
    assert "PREFERRED FOES/TRAPS/EVENTS FOR environment='dungeon'" in prompt
    assert '"exit_directions"' in prompt
    assert "north" in prompt
    assert "no southwest" in prompt.lower() or "southwest" in prompt.lower()


def test_foe_spawn_names_include_bosses(repo: RulesRepository) -> None:
    allowlists = build_adventure_allowlists(repo)
    foes = foe_names_for_validation(allowlists)
    for boss in allowlists["boss_spawn_names"]:
        assert boss in foes


def test_environment_pack_subset_of_global(repo: RulesRepository) -> None:
    global_lists = build_adventure_allowlists(repo)
    pack = build_environment_pack(repo, "dungeon")
    global_foes = set(global_lists["monster_spawn_names"])
    assert set(pack["foe_names"]).issubset(global_foes)
    assert set(pack["trap_keys"]).issubset(set(global_lists["trap_keys"]))


def test_boss_in_finale_validates_when_spawnable(repo: RulesRepository) -> None:
    allowlists = build_adventure_allowlists(repo)
    boss = allowlists["boss_spawn_names"][0]
    manifest = {
        "schema_version": 1,
        "id": "boss-test",
        "title": "Boss Test",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
            "entrance_room_id": "a",
            "exit_room_id": "a",
        "quest": {
            "key": "slay_all",
            "objective_text": "Slay boss",
            "complete_when": {
                "type": "boss_defeated",
                "boss_name": boss,
                "room_id": "a",
            },
        },
        "rooms": [
            {
                "id": "a",
                "tile_key": "02",
                "title": "A",
                "description": "A",
                "exits": [],
                "triggers": [
                    {
                        "when": "on_enter",
                        "encounter": {"foes": [{"name": boss, "count": 1}]},
                    }
                ],
            },
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    result = validate_adventure_manifest(manifest, rules_repo=repo)
    assert result.valid, result.errors
