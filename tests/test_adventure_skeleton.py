from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine.adventure_manifest import validate_adventure_manifest
from app.engine.adventure_session import create_session_from_manifest
from app.engine.adventure_skeleton import generate_adventure_skeleton
from app.engine.adventure_tile_catalog import build_tile_catalog
from app.engine.dungeon_table_roller import DungeonTableRoller, attempt_open_door
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import AdventurePromptParameters, PartyMemberState

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules"
EXAMPLE = ROOT / "data" / "adventures" / "examples" / "crypt-of-whispers" / "adventure.json"


@pytest.fixture
def repo() -> RulesRepository:
    return RulesRepository(RULES, RULES / "_override")


@pytest.fixture
def engine(repo: RulesRepository) -> RandomDungeonEngine:
    return RandomDungeonEngine(repo, ROOT / "assets")


def _party_member() -> PartyMemberState:
    return PartyMemberState.model_validate({
        "character_id": "hero-1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 2,
        "max_life": 8,
        "current_life": 8,
        "gold": 50,
        "xp": 0,
        "inventory": ["Hand weapon", "Light armor"],
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
    })


def test_skeleton_validates(repo: RulesRepository) -> None:
    bosses = __import__(
        "app.engine.adventure_allowlists", fromlist=["build_boss_spawn_names"]
    ).build_boss_spawn_names(repo)
    params = AdventurePromptParameters(theme="goblin cave", boss_type=bosses[0])
    skeleton = generate_adventure_skeleton(params, repo=repo)
    assert "_skeleton_notes" in skeleton
    check = {k: v for k, v in skeleton.items() if not str(k).startswith("_")}
    result = validate_adventure_manifest(check, rules_repo=repo)
    assert result.valid, result.errors


def test_tile_catalog_lists_native_exits(repo: RulesRepository) -> None:
    catalog = build_tile_catalog(repo)
    assert "tiles" in catalog
    assert catalog["tiles"]["11"]["native_exit_directions"] == ["south"]


def test_example_crypt_validates_with_tile_catalog(repo: RulesRepository) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    result = validate_adventure_manifest(manifest, rules_repo=repo)
    assert result.valid, result.errors


def test_imported_closed_door_uses_manifest_type_not_procedural_roll(
    engine: RandomDungeonEngine,
) -> None:
    manifest = {
        "schema_version": 1,
        "id": "door-test",
        "title": "Door Test",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
        "entrance_room_id": "a",
        "exit_room_id": "b",
        "quest": {
            "key": "slay_all",
            "objective_text": "Test",
            "complete_when": {"type": "room_reached", "room_id": "b"},
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
                        "kind": "door",
                        "status": "closed",
                    }
                ],
            },
            {
                "id": "b",
                "tile_key": "11",
                "title": "B",
                "description": "B",
                "exits": [
                    {
                        "id": "b-s",
                        "direction": "south",
                        "to": "a",
                        "kind": "passage",
                        "status": "open",
                    }
                ],
            },
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    session = create_session_from_manifest(
        engine,
        "s1",
        "p1",
        [_party_member()],
        manifest,
        adventure_id="door-test",
    )
    room_a = next(tile for tile in session.map_state.tiles if tile.title == "A")
    north = next(exit_state for exit_state in room_a.exits if exit_state.direction == "north")
    assert north.door_type == "unlocked"
    assert north.door_open is False
    roller = DungeonTableRoller(engine.rules)
    attempt_open_door(
        north,
        _party_member(),
        hcl=2,
        show_rolls=False,
        explain_math=False,
        roller=roller,
        party=[_party_member()],
    )
    assert north.door_type == "unlocked"
    assert north.door_type != "illusion"


def test_invalid_tile_exit_direction_fails(repo: RulesRepository) -> None:
    manifest = {
        "schema_version": 1,
        "id": "tile-mismatch",
        "title": "Mismatch",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
        "entrance_room_id": "hub",
        "exit_room_id": "hub",
        "quest": {
            "key": "slay_all",
            "objective_text": "Test",
            "complete_when": {"type": "room_reached", "room_id": "hub"},
        },
        "rooms": [
            {
                "id": "hub",
                "tile_key": "33",
                "title": "Hub",
                "description": "Hub",
                "exits": [
                    {
                        "id": "hub-n",
                        "direction": "north",
                        "to": "hub",
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
    assert any("native exits" in error for error in result.errors)
