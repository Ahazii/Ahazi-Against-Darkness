from __future__ import annotations

from app.engine.class_abilities import apply_nourishing_meal, luck_points_remaining, spend_luck_point
from app.engine.equipment_effects import AMULET_LUCK_STATUS, has_ten_foot_pole_in_inventories
from app.engine.equipment_shop import buy_equipment, sell_item
from app.engine.hunger import HUNGRY_STATUS, feed_member_hunger, tick_party_hunger
from app.engine.reactions import consume_fools_gold
from app.schemas import Character, PartyMemberState, SessionState


def _member(**kwargs) -> PartyMemberState:
    base = dict(
        character_id="h1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
        inventory=[],
    )
    base.update(kwargs)
    return PartyMemberState(**base)


def test_hunger_becomes_hungry_after_24_rounds() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member()],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        created_at="t",
        updated_at="t",
    )
    for _ in range(24):
        tick_party_hunger(session, session.party)
    assert HUNGRY_STATUS in session.party[0].statuses


def test_feeding_clears_hunger() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member(statuses=[HUNGRY_STATUS])],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        hunger_rounds={"h1": 30},
        created_at="t",
        updated_at="t",
    )
    feed_member_hunger(session, session.party[0])
    assert HUNGRY_STATUS not in session.party[0].statuses
    assert session.hunger_rounds["h1"] == 0


def test_amulet_luck_stacks_with_halfling() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member(class_id="halfling", class_name="Halfling", statuses=[AMULET_LUCK_STATUS])],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        created_at="t",
        updated_at="t",
    )
    assert luck_points_remaining(session, session.party[0]) >= 2


def test_fools_gold_consumed() -> None:
    party = [_member(inventory=["Fools' Gold"])]
    ok, message = consume_fools_gold(party)
    assert ok
    assert "Fools' Gold" not in party[0].inventory


def test_one_pole_per_party() -> None:
    assert has_ten_foot_pole_in_inventories([["10' pole"], []]) is True
    assert has_ten_foot_pole_in_inventories([["Bow"], ["Hand weapon"]]) is False
