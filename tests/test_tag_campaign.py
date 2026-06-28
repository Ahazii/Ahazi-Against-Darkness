from __future__ import annotations

from app.db import now_utc
from app.engine import tag_campaign
from app.engine.tag_campaign import (
    check_item_availability,
    default_campaign,
    look_for_clues,
    roll_hidden_treasure_trove_risk,
    roll_moneylender_follow_chance,
    roll_treasure_map_price,
    settlement_size_from_roll,
    settlement_service_rows,
    travel_to_new_settlement,
)
from app.schemas import Character


def _character(**overrides) -> Character:
    timestamp = now_utc()
    data = {
        "id": "hero-1",
        "name": "Sly Silas",
        "class_id": "rogue",
        "class_name": "Rogue",
        "level": 3,
        "gold": 20,
        "clues": 0,
        "max_life": 4,
        "current_life": 4,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    data.update(overrides)
    return Character(**data)


def test_tag_settlement_size_table() -> None:
    assert [settlement_size_from_roll(roll) for roll in range(1, 7)] == [-2, -1, 0, 1, 2, 3]


def test_tag_availability_success_surcharge_and_unavailable(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_size = 0

    rolls = iter([6, 5, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    success = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)
    surcharge = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)
    unavailable = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)

    assert success.outcome == "available"
    assert success.final_price_gp == 10
    assert surcharge.outcome == "surcharge"
    assert surcharge.final_price_gp == 12
    assert unavailable.outcome == "unavailable"
    assert unavailable.final_price_gp is None


def test_tag_look_for_clues_spends_bribe_and_uses_rogue_level(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character()
    rolls = iter([4, 3])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = look_for_clues(campaign, hero)

    assert hero.gold == 16
    assert hero.clues == 1
    assert entry.roll == 3
    assert entry.modifier == 3
    assert entry.total == 6


def test_tag_look_for_clues_natural_one_loses_existing_clue(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(clues=1)
    rolls = iter([2, 1])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = look_for_clues(campaign, hero)

    assert hero.gold == 18
    assert hero.clues == 0
    assert "lost 1 Clue" in entry.result_text


def test_tag_simple_travel_rolls_days_and_new_size(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_name = "Varian"
    rolls = iter([5, 2, 3, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = travel_to_new_settlement(campaign, destination_name="Diram")

    assert entry.from_settlement == "Varian"
    assert entry.to_settlement == "Diram"
    assert entry.days == 6
    assert entry.new_settlement_size == 2
    assert campaign.settlement_name == "Diram"
    assert campaign.settlement_size == 2
    assert campaign.days_passed == 6


def test_tag_hex_travel_logs_road_tithe_and_encounter_checks(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_name = "Varian"
    rolls = iter([6, 1, 3, 3, 4, 6, 6, 6])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = travel_to_new_settlement(campaign, destination_name="Diram", use_hex_map=True, pay_road_tithe=True)

    assert entry.new_settlement_size == 3
    assert entry.direction_roll == 1
    assert entry.distance_hexes == 8
    assert entry.road_roll == 18
    assert entry.road_exists is True
    assert entry.road_tithe_paid_gp == 3
    assert entry.encounter_checks == 3
    assert campaign.days_passed == 8


def test_tag_service_rows_gate_by_settlement_size_and_mark_availability() -> None:
    campaign = default_campaign()
    campaign.settlement_size = -1
    rows = {row["key"]: row for row in settlement_service_rows(campaign)}

    assert list(rows)[:18] == [
        "bank_account",
        "bank_inheritance",
        "magic_locker",
        "platinum_exchange",
        "hidden_treasure_trove",
        "resurrection_blessing_tags",
        "gems_jewelry_conversion",
        "bag_of_carrying",
        "ten_foot_pole",
        "lantern_hook",
        "very_nutritious_food",
        "poison_resistance_training",
        "martial_arts_training",
        "gambling_house",
        "treasure_maps",
        "moneylenders",
        "good_boots",
        "flammable_oil",
    ]
    assert rows["bank_account"]["status"] == "available"
    assert rows["magic_locker"]["status"] == "unavailable"
    assert rows["platinum_exchange"]["status"] == "church_only"
    assert rows["bag_of_carrying"]["availability_difficulty"] == 6
    assert rows["very_nutritious_food"]["availability_difficulty"] == 4
    assert rows["moneylenders"]["credit_limit_gp"] == 1800

    campaign.settlement_size = 3
    rows = {row["key"]: row for row in settlement_service_rows(campaign)}
    assert rows["magic_locker"]["status"] == "available"
    assert rows["platinum_exchange"]["status"] == "available"


def test_tag_hidden_treasure_trove_risk_roll(monkeypatch) -> None:
    campaign = default_campaign()
    rolls = iter([1, 2, 2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = roll_hidden_treasure_trove_risk(campaign)

    assert entry.action == "hidden_treasure_trove_risk"
    assert entry.total == 5
    assert "discovered and stolen" in entry.result_text


def test_tag_treasure_map_price_uses_exploding_sixes(monkeypatch) -> None:
    campaign = default_campaign()
    rolls = iter([6, 2, 1, 3, 4, 5])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = roll_treasure_map_price(campaign)

    assert entry.cost_gp == 21
    assert "6+2+1+3+4+5 = 21 gp" in entry.result_text


def test_tag_moneylender_follow_chance(monkeypatch) -> None:
    campaign = default_campaign()
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)

    entry = roll_moneylender_follow_chance(campaign, debt_gp=310)

    assert entry.total == 4
    assert "4-in-6 chance" in entry.result_text
    assert "enforcers follow" in entry.result_text
