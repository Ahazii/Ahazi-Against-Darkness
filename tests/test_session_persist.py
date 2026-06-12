from __future__ import annotations

import importlib
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.engine.roster_sync import persist_session_to_roster, roster_statuses, roster_xp, sync_party_members_to_roster
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import Character, MapState, PartyMemberState, SessionState, TileState


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


def test_secret_diet_life_bonus_is_not_persisted_to_roster(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        character = Character(
            id="hero-1",
            name="Hero",
            class_id="warrior",
            class_name="Warrior",
            level=1,
            xp=0,
            gold=0,
            current_life=5,
            max_life=5,
            attack_bonus=0,
            defense_bonus=0,
            save_bonus=0,
            active_session_id="s",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        main.store.save("characters", character)
        member = _member(current_life=6, max_life=6)
        session = SessionState(
            id="s",
            party_id="p",
            adventure_id="random",
            adventure_type="random",
            party=[member],
            secret_diet_character_ids=["hero-1"],
            map_state=MapState(
                tiles=[TileState(id="t", x=0, y=0, tile_key="01", tile_type="room", title="E", description="E")],
                current_tile_id="t",
            ),
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

        persist_session_to_roster(session, main.store)

        saved = main.store.get("characters", "hero-1", Character.model_validate)
        assert saved is not None
        assert saved.current_life == 5
        assert saved.max_life == 5


def test_new_session_starts_with_roster_clues(monkeypatch) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())
    monkeypatch.setattr("app.engine.random_dungeon.roll_start_tile_key", lambda: "01")
    session = engine.create_session(
        "s",
        "p",
        [
            _member(character_id="hero-1", clues=2),
            _member(character_id="hero-2", clues=1, marching_order=2),
        ],
    )

    assert session.clues_found == 3
    assert any("3 carried Clue" in line for line in session.log)


def test_sync_party_members_to_roster_updates_gold_and_inventory(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        character = Character(
            id="hero-1",
            name="Hero",
            class_id="warrior",
            class_name="Warrior",
            level=1,
            xp=0,
            gold=250,
            max_life=3,
            current_life=3,
            attack_bonus=0,
            defense_bonus=0,
            save_bonus=0,
            inventory=["Dagger"],
            spells=[],
            abilities=[],
            statuses=[],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        main.store.save("characters", character)
        member = _member(gold=180, bank_gold=70, inventory=["Hand weapon"])
        session = SessionState(
            id="s",
            party_id="p",
            adventure_id="random",
            adventure_type="random",
            party=[member],
            map_state=MapState(
                tiles=[TileState(id="t", x=0, y=0, tile_key="01", tile_type="room", title="E", description="E")],
                current_tile_id="t",
            ),
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        sync_party_members_to_roster(session, main.store, {"hero-1"})
        saved = main.store.get("characters", "hero-1", Character.model_validate)
        assert saved is not None
        assert saved.gold == 250
        assert saved.inventory == ["Hand weapon"]


def test_new_session_splits_roster_gold_into_carried_and_bank(monkeypatch) -> None:
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
                json={"name": f"Bank Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_id = response.json()["id"]
            character = main.store.get("characters", character_id, main.Character.model_validate)
            assert character is not None
            character.gold = 250 if index == 1 else 0
            main.store.save("characters", character)
            character_ids.append(character_id)

        party_id = client.post(
            "/api/parties",
            json={"name": "Bank Party", "character_ids": character_ids},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")
        session = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()
        member = next(item for item in session["party"] if item["character_id"] == character_ids[0])
        assert member["gold"] == 200
        assert member["bank_gold"] == 50


def test_complete_dungeon_migrates_legacy_pooled_clues_to_one_living_roster_member(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        for character_id, name in [("hero-1", "Hero"), ("hero-2", "Ally")]:
            character = Character(
                id=character_id,
                name=name,
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                max_life=3,
                current_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=[],
                spells=[],
                abilities=[],
                statuses=[],
                clues=5,
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
            main.store.save("characters", character)
        session = SessionState(
            id="s",
            party_id="p",
            adventure_id="random",
            adventure_type="random",
            clues_found=4,
            party=[_member(character_id="hero-1"), _member(character_id="hero-2", marching_order=2)],
            map_state=MapState(
                tiles=[TileState(id="t", x=0, y=0, tile_key="01", tile_type="room", title="E", description="E")],
                current_tile_id="t",
            ),
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

        notes = persist_session_to_roster(session, main.store)

        first = main.store.get("characters", "hero-1", Character.model_validate)
        second = main.store.get("characters", "hero-2", Character.model_validate)
        assert first is not None and second is not None
        assert first.clues == 4
        assert second.clues == 0
        assert any("4 Clue" in note for note in notes)


def test_complete_dungeon_persists_individual_clue_holders(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        for character_id, name in [("hero-1", "Hero"), ("hero-2", "Ally")]:
            character = Character(
                id=character_id,
                name=name,
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                max_life=3,
                current_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=[],
                spells=[],
                abilities=[],
                statuses=[],
                clues=0,
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
            main.store.save("characters", character)
        session = SessionState(
            id="s",
            party_id="p",
            adventure_id="random",
            adventure_type="random",
            clues_found=4,
            party=[
                _member(character_id="hero-1", clues=3),
                _member(character_id="hero-2", marching_order=2, clues=1),
            ],
            map_state=MapState(
                tiles=[TileState(id="t", x=0, y=0, tile_key="01", tile_type="room", title="E", description="E")],
                current_tile_id="t",
            ),
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

        notes = persist_session_to_roster(session, main.store)

        first = main.store.get("characters", "hero-1", Character.model_validate)
        second = main.store.get("characters", "hero-2", Character.model_validate)
        assert first is not None and second is not None
        assert first.clues == 3
        assert second.clues == 1
        assert any("3 Clue" in note for note in notes)
        assert any("1 Clue" in note for note in notes)


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


def test_return_camp_syncs_roster_shop_to_active_session(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        character_ids = []
        for index in range(4):
            response = client.post(
                "/api/characters",
                json={"name": f"Camp Shop Hero {index + 1}", "class_id": "warrior"},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Camp Shop Party", "character_ids": character_ids},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")
        session = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()

        stored = main.store.get("sessions", session["id"], main.SessionState.model_validate)
        assert stored is not None
        buyer = stored.party[0]
        buyer.gold = 20
        buyer.bank_gold = 30
        buyer.current_life = 1
        exit_id = next(exit_state.id for exit_state in stored.map_state.tiles[0].exits if exit_state.dungeon_exit)
        main.store.save("sessions", stored)

        camped = client.post(
            f"/api/sessions/{session['id']}/advance",
            json={"action": "explore", "exit_id": exit_id, "dungeon_exit_intent": "return"},
        )
        assert camped.status_code == 200
        camped_body = camped.json()
        assert camped_body["mode"] == "exploration"
        assert camped_body["camped_outside"] is True
        camped_buyer = camped_body["party"][0]
        assert camped_buyer["current_life"] == camped_buyer["max_life"]

        roster_buyer = main.store.get("characters", buyer.character_id, main.Character.model_validate)
        assert roster_buyer is not None
        assert roster_buyer.active_session_id == session["id"]
        assert roster_buyer.gold == 50
        assert roster_buyer.current_life == roster_buyer.max_life

        stored = main.store.get("sessions", session["id"], main.SessionState.model_validate)
        assert stored is not None
        buyer = stored.party[0]
        buyer.gold = 2
        buyer.bank_gold = 30
        main.store.save("sessions", stored)

        buy = client.post(
            f"/api/characters/{buyer.character_id}/buy-equipment",
            json={"item_key": "lantern"},
        )
        assert buy.status_code == 200
        bought_character = buy.json()["character"]
        assert "Lantern" in bought_character["inventory"]

        refreshed = client.get(f"/api/sessions/{session['id']}").json()
        refreshed_buyer = next(member for member in refreshed["party"] if member["character_id"] == buyer.character_id)
        assert "Lantern" in refreshed_buyer["inventory"]
        assert refreshed_buyer["gold"] + refreshed_buyer["bank_gold"] == bought_character["gold"]
        assert refreshed_buyer["gold"] == 2
        assert refreshed_buyer["bank_gold"] == bought_character["gold"] - 2
