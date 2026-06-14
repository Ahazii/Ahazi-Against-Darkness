from __future__ import annotations

import importlib
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from app.engine.equipment_shop import buy_equipment, list_shop_for_class, sell_item, sell_quote
from app.schemas import Character


@pytest.fixture
def catalog() -> dict:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    import json

    return json.loads((packaged / "equipment_shop.json").read_text(encoding="utf-8"))


def _character(**overrides) -> Character:
    base = {
        "id": "c1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 1,
        "xp": 0,
        "gold": 100,
        "max_life": 5,
        "current_life": 5,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "inventory": ["Hand weapon"],
        "spells": [],
        "abilities": [],
        "statuses": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return Character.model_validate(base)


def test_warrior_can_buy_shield(catalog) -> None:
    hero = _character(gold=20)
    ok, message = buy_equipment(hero, catalog, item_key="shield")
    assert ok
    assert "Shield" in hero.inventory
    assert hero.gold == 15
    assert "buys" in message


def test_buy_equipment_quantity(catalog) -> None:
    hero = _character(gold=30)
    ok, message = buy_equipment(hero, catalog, item_key="bandage", quantity=5)

    assert ok
    assert hero.inventory.count("Bandage") == 5
    assert hero.gold == 5
    assert "5x Bandage" in message
    assert "25gp" in message


def test_buy_equipment_quantity_requires_total_gold(catalog) -> None:
    hero = _character(gold=20)
    ok, message = buy_equipment(hero, catalog, item_key="bandage", quantity=5)

    assert not ok
    assert hero.inventory.count("Bandage") == 0
    assert hero.gold == 20
    assert "needs 25gp" in message


def test_barbarian_cannot_buy_potion(catalog) -> None:
    hero = _character(class_id="barbarian", class_name="Barbarian", gold=200)
    ok, message = buy_equipment(hero, catalog, item_key="potion")
    assert not ok
    assert "Barbarians" in message


def test_potion_recipe_secret_discounts_healing_potion(catalog) -> None:
    hero = _character(gold=60, secrets=["potion_recipe"])
    rows = list_shop_for_class(catalog, hero.class_id, character=hero)
    potion = next(item for item in rows if item["key"] == "potion")

    assert potion["price_gp"] == 50
    assert potion["price_note"] == "Recipe for a Potion Secret price"

    ok, message = buy_equipment(hero, catalog, item_key="potion")
    assert ok
    assert hero.gold == 10
    assert "Potion of Healing" in hero.inventory
    assert "Recipe for a Potion" in message


def test_sell_hand_weapon_for_half_price(catalog) -> None:
    hero = _character(inventory=["Hand weapon"], gold=0)
    ok, message, payout = sell_item(hero, catalog, item_name="Hand weapon")
    assert ok
    assert payout == 3
    assert hero.gold == 3
    assert hero.inventory == []
    assert "sells" in message


def test_sell_mace_as_hand_weapon(catalog) -> None:
    hero = _character(inventory=["Mace"], gold=0)
    ok, _, payout = sell_item(hero, catalog, item_name="Mace")
    assert ok
    assert payout == 3


def test_sell_quote_for_potion(catalog) -> None:
    hero = _character(inventory=["Potion of Healing"])
    quote = sell_quote(hero, catalog, item_name="Potion of Healing")
    assert quote["quote_gp"] == 50


def test_book_of_skalitos_resale_only_when_unused(catalog) -> None:
    hero = _character(inventory=["Book of Skalitos (6 pages)", "Book of Skalitos (5 pages)"])

    unused = sell_quote(hero, catalog, item_name="Book of Skalitos (6 pages)")
    used = sell_quote(hero, catalog, item_name="Book of Skalitos (5 pages)")

    assert unused["quote_gp"] == 650
    assert used["quote_gp"] != 650


def test_sell_misc_loot_rolls_d6_times_d6(catalog, monkeypatch) -> None:
    from app.engine import equipment_shop

    hero = _character(inventory=["Rusty bucket"], gold=0)
    rolls = iter([4, 5])

    def fake_roll() -> int:
        return next(rolls)

    monkeypatch.setattr(equipment_shop, "roll_d6", fake_roll)
    ok, _, payout = sell_item(hero, catalog, item_name="Rusty bucket")
    assert ok
    assert payout == 20


def test_big_money_buyer_triples_one_gem_sale_and_is_consumed(catalog, monkeypatch) -> None:
    from app.engine import equipment_shop

    hero = _character(inventory=["Ruby gem"], gold=0, secrets=["big_money_buyer"])
    quote = sell_quote(hero, catalog, item_name="Ruby gem")
    assert quote["quote_gp"] is None
    assert "triples" in quote["note"]

    rolls = iter([2, 3])
    monkeypatch.setattr(equipment_shop, "roll_d6", lambda: next(rolls))
    ok, message, payout = sell_item(hero, catalog, item_name="Ruby gem")

    assert ok
    assert payout == 18
    assert hero.gold == 18
    assert hero.secrets == []
    assert "Big Money Buyer" in message


def test_roster_gold_transfer_ignores_carry_limit(monkeypatch) -> None:
    from app.engine.inventory import transfer_character_gold

    source = _character(id="a", name="Alpha", gold=250)
    target = _character(id="b", name="Bravo", gold=0)
    ok, message = transfer_character_gold(source, target, amount=100)
    assert ok
    assert source.gold == 150
    assert target.gold == 100
    assert "100gp" in message


def test_equipment_shop_api(monkeypatch) -> None:
    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        warrior = client.post("/api/characters", json={"name": "War", "class_id": "warrior"}).json()
        catalog = client.get(f"/api/rules/equipment-shop?class_id=warrior").json()
        assert any(item["key"] == "shield" for item in catalog["items"])

        warrior_record = main.store.get("characters", warrior["id"], main.Character.model_validate)
        assert warrior_record is not None
        warrior_record.gold = 50
        main.store.save("characters", warrior_record)

        buy = client.post(
            f"/api/characters/{warrior['id']}/buy-equipment",
            json={"item_key": "rope", "quantity": 3},
        )
        assert buy.status_code == 200
        assert buy.json()["character"]["inventory"].count("Rope") == 3

        warrior_record = main.store.get("characters", warrior["id"], main.Character.model_validate)
        assert warrior_record is not None
        warrior_record.gold = 50
        warrior_record.secrets = ["potion_recipe"]
        main.store.save("characters", warrior_record)
        recipe_catalog = client.get(
            f"/api/rules/equipment-shop?class_id=warrior&character_id={warrior['id']}"
        ).json()
        potion_row = next(item for item in recipe_catalog["items"] if item["key"] == "potion")
        assert potion_row["price_gp"] == 50
        recipe_buy = client.post(
            f"/api/characters/{warrior['id']}/buy-equipment",
            json={"item_key": "potion"},
        )
        assert recipe_buy.status_code == 200
        assert recipe_buy.json()["character"]["gold"] == 0

        sell = client.post(
            f"/api/characters/{warrior['id']}/sell-item",
            json={"item_name": "Hand weapon"},
        )
        assert sell.status_code == 200
        assert sell.json()["gold_received"] == 3
