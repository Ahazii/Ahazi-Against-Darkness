from __future__ import annotations

from pathlib import Path

from app.engine.special_items import (
    BERSERKER_MUSHROOM_STATUS,
    apply_enchanted_paint,
    apply_wand_cast_bonus,
    can_bash_door,
    climb_from_pit,
    consume_wand_cast_bonus,
    consume_wand_power_charges,
    eat_berserkers_mushroom,
    extra_door_modifier,
    flee_blocked_by_web,
    format_wand_of_power,
    mark_pit_trapped,
    paintable_shop_items,
    resolve_special_treasure_items,
    roll_wand_of_power_charges,
    wand_cast_bonus,
)
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, PartyMemberState, SessionState

ROOT = Path(__file__).resolve().parents[1]


def _shop_catalog() -> dict:
    rules_dir = ROOT / "data" / "rules"
    return RulesRepository(rules_dir, rules_dir / "_override").equipment_shop()


def _member(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        max_life=5,
        current_life=5,
        marching_order=1,
        inventory=[],
        statuses=[],
        spells=[],
        learned_expert_skills=[],
        gold=0,
        clues=0,
        xp=0,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _session(party: list[PartyMemberState]) -> SessionState:
    return SessionState(
        id="sess-1",
        party_id="party-1",
        adventure_id="adv-1",
        adventure_type="random",
        party=party,
        map_state={"current_tile_id": "tile-1", "tiles": []},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_crowbar_allows_bash_and_bonus():
    member = _member(inventory=["Crowbar"])
    assert can_bash_door(member, "locked") is True
    assert extra_door_modifier(member, door_type="locked", bashing=True, lockpicking=False) == 1


def test_good_lockpicks_door_bonus():
    member = _member(inventory=["Good lockpicks"])
    assert extra_door_modifier(member, door_type="locked", bashing=False, lockpicking=True) == 1


def test_flee_blocked_by_spider_web_until_torch_spent():
    spider = EnemyState(
        id="foe-1",
        name="Giant spider",
        level=2,
        life=3,
        max_life=3,
        category="weird",
        tags=["web"],
    )
    blocked, _ = flee_blocked_by_web([spider], torch_spent=False)
    assert blocked is True
    blocked_after, _ = flee_blocked_by_web([spider], torch_spent=True)
    assert blocked_after is False


def test_wand_of_power_charge_roll_and_consume():
    item, charges, _log = roll_wand_of_power_charges(roll_fn=lambda _count: [2, 1])
    assert charges == 3
    assert item == format_wand_of_power(3)
    updated = consume_wand_power_charges(item, 2)
    assert updated == format_wand_of_power(1)
    assert consume_wand_power_charges(item, 3) is None


def test_wand_cast_bonus_status():
    member = _member()
    apply_wand_cast_bonus(member, 2)
    assert wand_cast_bonus(member) == 2
    consume_wand_cast_bonus(member)
    assert wand_cast_bonus(member) == 0


def test_enchanted_paint_creates_shop_item(monkeypatch):
    member = _member(inventory=["Enchanted Paint"])
    catalog = _shop_catalog()
    monkeypatch.setattr("app.engine.special_items.roll_d6", lambda: 3)
    log, used, depleted = apply_enchanted_paint(
        member,
        choice="shop_item",
        item_key="crowbar",
        shop_catalog=catalog,
        show_rolls=False,
    )
    assert used is True
    assert depleted is False
    assert "Crowbar" in member.inventory
    assert any("Enchanted Paint" in item for item in member.inventory)
    assert any("Crowbar" in line for line in log)


def test_paintable_shop_items_pdf_p186_limits():
    catalog = _shop_catalog()
    paintable = paintable_shop_items(catalog)
    keys = {item["key"] for item in paintable}
    assert "crowbar" in keys
    assert "hand_weapon" in keys
    assert "heavy_armor" not in keys  # 30gp
    assert "flammable_oil" not in keys  # liquid
    assert "potion" not in keys  # magic
    assert "amulet" not in keys  # magic item ≤15gp still excluded
    assert all(item["price_gp"] <= 15 for item in paintable)


def test_enchanted_paint_rejects_invalid_shop_item():
    member = _member(inventory=["Enchanted Paint"])
    catalog = _shop_catalog()
    log, used, _ = apply_enchanted_paint(
        member,
        choice="shop_item",
        item_key="heavy_armor",
        shop_catalog=catalog,
        show_rolls=False,
    )
    assert used is False
    assert any("cannot be painted" in line for line in log)


def test_berserkers_mushroom_pending_status():
    member = _member(inventory=["Berserker's Mushroom"])
    eat_berserkers_mushroom(member, "Berserker's Mushroom")
    assert BERSERKER_MUSHROOM_STATUS in member.statuses
    assert "Berserker's Mushroom" not in member.inventory


def test_climb_from_pit_with_rope():
    trapped = _member(character_id="trapped", name="Trapped", statuses=[])
    helper = _member(character_id="helper", name="Helper", inventory=[])
    mark_pit_trapped(trapped)
    rope_carrier = _member(character_id="rope", name="Rope", inventory=["Rope (50')"])
    session = _session([trapped, helper, rope_carrier])
    log = climb_from_pit(session, helper, trapped, session.party)
    assert "climbs out using the party's rope" in log[0]
    assert "Trapped in pit" not in trapped.statuses


def test_enchanted_paint_options_api():
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/api/rules/enchanted-paint-options")
    assert response.status_code == 200
    payload = response.json()
    assert payload["max_price_gp"] == 15
    assert payload["food_rations_max"] == 8
    keys = {item["key"] for item in payload["items"]}
    assert "shield" in keys
    assert "heavy_armor" not in keys
    resolved, log = resolve_special_treasure_items(
        ["Wand of Power (2d3 charges)"],
        roll_fn=lambda: 2,
    )
    assert resolved[0].startswith("Wand of Power (")
    assert any("Wand of Power charges" in line for line in log)
