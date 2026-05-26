from __future__ import annotations

from app.engine.inventory import (
    MAX_CARRIED_GOLD,
    MAX_CARRIED_SHIELDS,
    MAX_CARRIED_WEAPONS,
    can_add_gold,
    can_add_item,
    distribute_gold_among,
    distribute_items_among,
    transfer_gold,
    transfer_inventory_item,
)
from app.schemas import PartyMemberState


def member(
    *,
    character_id: str,
    name: str,
    gold: int = 0,
    inventory: list[str] | None = None,
    starting_weapon_slots: int | None = None,
    starting_shields: int | None = None,
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
        inventory=list(inventory or []),
        starting_weapon_slots=starting_weapon_slots,
        starting_shields=starting_shields,
    )


def test_gold_capacity_blocks_transfer() -> None:
    rich = member(character_id="a", name="Rich", gold=50)
    full = member(character_id="b", name="Full", gold=MAX_CARRIED_GOLD)
    ok, message = transfer_gold(
        [rich, full],
        from_character_id="a",
        to_character_id="b",
        amount=1,
    )
    assert not ok
    assert "200gp" in message


def test_weapon_limit_blocks_transfer() -> None:
    giver = member(
        character_id="a",
        name="Giver",
        inventory=["Hand weapon", "Bow", "Dagger"],
        starting_weapon_slots=1,
        starting_shields=0,
    )
    receiver = member(
        character_id="b",
        name="Receiver",
        inventory=["Heavy weapon", "Mace", "Staff"],
        starting_weapon_slots=1,
        starting_shields=0,
    )
    ok, message = transfer_inventory_item(
        [giver, receiver],
        from_character_id="a",
        to_character_id="b",
        item_name="Hand weapon",
    )
    assert not ok
    assert "slots" in message.lower()


def test_shield_limit_blocks_transfer() -> None:
    giver = member(character_id="a", name="Giver", inventory=["Shield"])
    receiver = member(character_id="b", name="Receiver", inventory=["Shield", "Shield of Warning"])
    ok, message = transfer_inventory_item(
        [giver, receiver],
        from_character_id="a",
        to_character_id="b",
        item_name="Shield",
    )
    assert not ok
    assert str(MAX_CARRIED_SHIELDS) in message


def test_distribute_gold_leaves_overflow() -> None:
    alpha = member(character_id="a", name="Alpha", gold=MAX_CARRIED_GOLD)
    bravo = member(character_id="b", name="Bravo", gold=150)
    remaining, payouts = distribute_gold_among([alpha, bravo], 100)
    assert alpha.gold == MAX_CARRIED_GOLD
    assert bravo.gold == MAX_CARRIED_GOLD
    assert remaining == 50
    assert payouts


def test_distribute_gold_splits_evenly() -> None:
    heroes = [
        member(character_id="a", name="Alpha", gold=0),
        member(character_id="b", name="Bravo", gold=0),
        member(character_id="c", name="Charlie", gold=0),
        member(character_id="d", name="Delta", gold=0),
    ]
    remaining, payouts = distribute_gold_among(heroes, 100)
    assert remaining == 0
    assert [hero.gold for hero in heroes] == [25, 25, 25, 25]
    assert len(payouts) == 4


def test_distribute_items_respects_weapon_limits() -> None:
    carrier = member(
        character_id="a",
        name="Carrier",
        inventory=["Hand weapon", "Bow", "Dagger"],
        starting_weapon_slots=1,
        starting_shields=0,
    )
    uncarried, placed = distribute_items_among([carrier], ["Mace", "Potion of Healing"])
    assert placed == ["Potion of Healing"]
    assert uncarried == ["Mace"]
    assert "Mace" not in carrier.inventory


def test_can_add_item_allows_non_limited_gear() -> None:
    hero = member(character_id="a", name="Hero", inventory=["Hand weapon", "Bow", "Dagger"])
    ok, _ = can_add_item(hero, "Potion of Healing")
    assert ok


def test_two_handed_allows_fourth_weapon_slot_within_extra_allowance() -> None:
    carrier = member(
        character_id="a",
        name="Carrier",
        inventory=["Heavy weapon", "Hand weapon"],
        starting_weapon_slots=1,
        starting_shields=0,
    )
    ok, _ = can_add_item(carrier, "Dagger")
    assert ok


def test_two_handed_blocks_fifth_weapon_slot() -> None:
    carrier = member(
        character_id="a",
        name="Carrier",
        inventory=["Heavy weapon", "Hand weapon", "Dagger"],
        starting_weapon_slots=1,
        starting_shields=0,
    )
    ok, message = can_add_item(carrier, "Mace")
    assert not ok
    assert "weapon" in message.lower() or "slots" in message.lower()


def test_can_add_gold_at_limit() -> None:
    hero = member(character_id="a", name="Hero", gold=199)
    ok, _ = can_add_gold(hero, 1)
    assert ok
    ok, message = can_add_gold(hero, 2)
    assert not ok
    assert "200gp" in message
