from __future__ import annotations

from app.db import now_utc
from app.engine import tag_campaign
from app.engine.tag_campaign import check_item_availability, default_campaign, look_for_clues, settlement_size_from_roll
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
