from __future__ import annotations

from pathlib import Path

from app.engine.inventory import transfer_character_gold, transfer_character_item, transfer_gold, transfer_inventory_item
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def member(
    *,
    character_id: str,
    name: str,
    marching_order: int = 1,
    gold: int = 0,
    inventory: list[str] | None = None,
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=gold,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=marching_order,
        inventory=list(inventory or []),
    )


def exploration_session(party: list[PartyMemberState]) -> SessionState:
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=party,
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def test_transfer_inventory_item_between_party_members() -> None:
    alpha = member(character_id="a", name="Alpha", inventory=["Short Sword"])
    bravo = member(character_id="b", name="Bravo", marching_order=2)
    ok, message = transfer_inventory_item(
        [alpha, bravo],
        from_character_id="a",
        to_character_id="b",
        item_name="Short Sword",
    )
    assert ok
    assert alpha.inventory == []
    assert bravo.inventory == ["Short Sword"]
    assert "Alpha gives Short Sword to Bravo" in message


def test_transfer_inventory_item_rejects_missing_item() -> None:
    alpha = member(character_id="a", name="Alpha")
    bravo = member(character_id="b", name="Bravo", marching_order=2)
    ok, message = transfer_inventory_item(
        [alpha, bravo],
        from_character_id="a",
        to_character_id="b",
        item_name="Potion of Healing",
    )
    assert not ok
    assert "does not carry" in message


def test_transfer_gold_between_party_members() -> None:
    alpha = member(character_id="a", name="Alpha", gold=20)
    bravo = member(character_id="b", name="Bravo", marching_order=2, gold=5)
    ok, message = transfer_gold(
        [alpha, bravo],
        from_character_id="a",
        to_character_id="b",
        amount=7,
    )
    assert ok
    assert alpha.gold == 13
    assert bravo.gold == 12
    assert "Alpha gives 7gp to Bravo" in message


def test_transfer_item_blocked_in_combat() -> None:
    from app.schemas import EnemyState

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    party = [
        member(character_id="a", name="Alpha", inventory=["Dagger"]),
        member(character_id="b", name="Bravo", marching_order=2),
    ]
    session = exploration_session(party)
    session.mode = "combat"
    session.map_state.tiles[0].enemies = [
        EnemyState(id="e1", name="Rat", category="vermin", level=1, life=1, max_life=1),
    ]
    engine.advance(
        session,
        "transfer_item",
        character_id="a",
        target_character_id="b",
        item_name="Dagger",
    )
    assert party[0].inventory == ["Dagger"]
    assert party[1].inventory == []
    assert any("exploration" in entry.lower() for entry in session.log)


def saved_character(*, character_id: str, name: str, gold: int = 0, inventory: list[str] | None = None):
    from app.schemas import Character

    return Character(
        id=character_id,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=gold,
        max_life=3,
        current_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=list(inventory or []),
        spells=[],
        abilities=[],
        statuses=[],
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def test_transfer_character_item_between_saved_characters() -> None:
    alpha = saved_character(character_id="a", name="Alpha", inventory=["Shield"])
    bravo = saved_character(character_id="b", name="Bravo")
    ok, message = transfer_character_item(alpha, bravo, item_name="Shield")
    assert ok
    assert alpha.inventory == []
    assert bravo.inventory == ["Shield"]
    assert "Alpha gives Shield to Bravo" in message


def test_transfer_character_gold_between_saved_characters() -> None:
    alpha = saved_character(character_id="a", name="Alpha", gold=12)
    bravo = saved_character(character_id="b", name="Bravo", gold=3)
    ok, message = transfer_character_gold(alpha, bravo, amount=4)
    assert ok
    assert alpha.gold == 8
    assert bravo.gold == 7
    assert "Alpha gives 4gp to Bravo" in message


def test_transfer_character_api(monkeypatch) -> None:
    import importlib
    from tempfile import TemporaryDirectory

    from fastapi.testclient import TestClient

    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)
        classes = client.get("/api/rules/classes").json()
        class_id = classes[0]["id"]
        alpha = client.post("/api/characters", json={"name": "Alpha", "class_id": class_id}).json()
        bravo = client.post("/api/characters", json={"name": "Bravo", "class_id": class_id}).json()
        alpha_record = main.store.get("characters", alpha["id"], main.Character.model_validate)
        assert alpha_record is not None
        alpha_record.inventory.append("Relic Blade")
        main.store.save("characters", alpha_record)
        response = client.post(
            f"/api/characters/{alpha['id']}/transfer",
            json={"target_character_id": bravo["id"], "item_name": "Relic Blade"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["message"] == "Alpha gives Relic Blade to Bravo."
        assert "Relic Blade" not in payload["source"]["inventory"]
        assert "Relic Blade" in payload["target"]["inventory"]
