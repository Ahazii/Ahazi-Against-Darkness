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
    )
    receiver = member(
        character_id="b",
        name="Receiver",
        inventory=["Heavy weapon", "Mace", "Staff"],
    )
    ok, message = transfer_inventory_item(
        [giver, receiver],
        from_character_id="a",
        to_character_id="b",
        item_name="Hand weapon",
    )
    assert not ok
    assert str(MAX_CARRIED_WEAPONS) in message


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


def test_distribute_items_respects_weapon_limits() -> None:
    carrier = member(character_id="a", name="Carrier", inventory=["Hand weapon", "Bow", "Dagger"])
    uncarried, placed = distribute_items_among([carrier], ["Mace", "Potion of Healing"])
    assert placed == ["Potion of Healing"]
    assert uncarried == ["Mace"]
    assert "Mace" not in carrier.inventory


def test_can_add_item_allows_non_limited_gear() -> None:
    hero = member(character_id="a", name="Hero", inventory=["Hand weapon", "Bow", "Dagger"])
    ok, _ = can_add_item(hero, "Potion of Healing")
    assert ok


def test_two_handed_blocks_fourth_weapon_slot() -> None:
    carrier = member(
        character_id="a",
        name="Carrier",
        inventory=["Heavy weapon", "Hand weapon"],
    )
    ok, message = can_add_item(carrier, "Dagger")
    assert not ok
    assert "weapon slots" in message.lower() or "two-handed" in message.lower()


def test_can_add_gold_at_limit() -> None:
    hero = member(character_id="a", name="Hero", gold=199)
    ok, _ = can_add_gold(hero, 1)
    assert ok
    ok, message = can_add_gold(hero, 2)
    assert not ok
    assert "200gp" in message
