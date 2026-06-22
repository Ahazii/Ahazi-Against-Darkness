from __future__ import annotations

from pathlib import Path

from app.engine.adventure_session import create_session_from_manifest
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import PartyMemberState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _party_member() -> PartyMemberState:
    return PartyMemberState.model_validate({
        "character_id": "hero-1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 5,
        "expert_trained": True,
        "max_life": 12,
        "current_life": 12,
        "gold": 200,
        "xp": 0,
        "inventory": ["Hand weapon", "Light armor"],
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
    })


def test_random_session_can_start_camped_outside() -> None:
    eng = engine()
    session = eng.create_session(
        "camp-start",
        "party-1",
        [_party_member()],
        start_camped_outside=True,
    )
    assert session.camped_outside is True
    assert session.imported_entrance_pending is False
    assert any("camp outside" in entry.lower() for entry in session.log)


def test_imported_session_defers_entrance_until_reenter() -> None:
    eng = engine()
    manifest = {
        "id": "camp-entrance-test",
        "title": "Camp Entrance Test",
        "synopsis": "Test",
        "version": 1,
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
                "title": "Gate",
                "description": "A gate.",
                "exits": [],
                "triggers": [
                    {
                        "when": "on_enter",
                        "once": True,
                        "encounter": {"foes": [{"name": "Goblins", "count": 1}]},
                    }
                ],
            }
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    session = create_session_from_manifest(
        eng,
        "imported-camp",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
        start_camped_outside=True,
    )
    entrance = next(tile for tile in session.map_state.tiles if tile.content_key == "entrance")
    assert session.camped_outside is True
    assert session.imported_entrance_pending is True
    assert not entrance.enemies
    assert not any("Entered Gate" in entry for entry in session.log)

    eng.advance(session, "return_to_dungeon")
    assert session.camped_outside is False
    assert session.imported_entrance_pending is False
    assert entrance.enemies
    assert any("Entered Gate" in entry for entry in session.log)
