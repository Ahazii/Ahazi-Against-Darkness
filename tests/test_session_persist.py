from __future__ import annotations

import importlib
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.engine.roster_sync import persist_session_to_roster, roster_statuses, roster_xp
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def _member(**overrides) -> PartyMemberState:
    base = {
        "character_id": "hero-1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 1,
        "xp": 0,
        "gold": 0,
        "current_life": 3,
        "max_life": 3,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
    }
    base.update(overrides)
    return PartyMemberState(**base)


def test_roster_statuses_drop_combat_buffs() -> None:
    kept = roster_statuses(["Protection", "Cursed", "Enchanted weapon", "Mirror Image x2"])
    assert kept == ["Cursed", "Enchanted weapon"]


def test_roster_xp_uses_session_tallies() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="random",
        adventure_type="random",
        xp_system="old_school",
        old_school_xp_tally=420,
        party=[_member()],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="01", tile_type="room", title="E", description="E")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert roster_xp(session, 0) == 420

    session.xp_system = "slower_advancement"
    session.slower_xp_bank = 55
    assert roster_xp(session, 0) == 55


def test_complete_dungeon_persists_gold_level_and_healed_life(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        classes = client.get("/api/rules/classes").json()
        character_ids = []
        for index, class_id in enumerate([item["id"] for item in classes[:4]], start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Persist Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Persist Party", "character_ids": character_ids},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        session = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()
        stored = main.store.get("sessions", session["id"], main.SessionState.model_validate)
        assert stored is not None
        lead = stored.party[0]
        lead.gold = 250
        lead.level = 2
        lead.max_life = 4
        lead.current_life = 1
        lead.inventory = ["Potion of Healing"]
        lead.statuses = ["Protection", "Cursed"]
        main.store.save("sessions", stored)

        entrance = stored.map_state.tiles[0]
        dungeon_exit = next(exit_state for exit_state in entrance.exits if exit_state.dungeon_exit)
        stored.mode = "complete"
        stored.summary = ["Adventure complete."]
        for member in stored.party:
            if member.current_life > 0:
                member.current_life = member.max_life
        main.store.save("sessions", stored)

        notes = persist_session_to_roster(stored, main.store)
        assert notes

        character = main.store.get("characters", lead.character_id, main.Character.model_validate)
        assert character is not None
        assert character.gold == 250
        assert character.level == 2
        assert character.current_life == 4
        assert character.max_life == 4
        assert character.inventory == ["Potion of Healing"]
        assert character.statuses == ["Cursed"]

        advance_response = client.post(
            f"/api/sessions/{session['id']}/advance",
            json={"action": "explore", "exit_id": dungeon_exit.id},
        )
        assert advance_response.status_code == 200
        completed = advance_response.json()
        assert completed["mode"] == "complete"
        assert any("Character roster updated" in line for line in completed["summary"])

        characters = client.get("/api/characters").json()
        character = next(item for item in characters if item["id"] == lead.character_id)
        assert character["gold"] == 250
        assert character["level"] == 2
        assert character["current_life"] == character["max_life"]
        assert character["inventory"] == ["Potion of Healing"]
        assert character["statuses"] == ["Cursed"]
