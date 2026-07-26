from __future__ import annotations

import pytest

from app.engine.item_containers import add_bag_of_carrying
from app.engine.item_disposition import (
    ItemDisposition,
    eligible_inventory_items,
    item_disposition_decision,
    remove_item_for_disposition,
)
from app.engine.star_object_curse import STAR_OBJECT_ITEM
from app.schemas import PartyMemberState


def _member(inventory: list[str] | None = None) -> PartyMemberState:
    return PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=4,
        xp=0,
        gold=20,
        current_life=8,
        max_life=8,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        inventory=list(inventory or []),
    )


@pytest.mark.parametrize("disposition", list(ItemDisposition))
def test_bound_star_object_is_ineligible_for_every_ordinary_disposition(
    disposition: ItemDisposition,
) -> None:
    decision = item_disposition_decision(STAR_OBJECT_ITEM, disposition)

    assert decision.allowed is False
    assert "cannot" in decision.reason or "ineligible" in decision.reason
    assert "TAG" in decision.reason


def test_eligible_items_preserve_order_and_duplicates() -> None:
    items = [STAR_OBJECT_ITEM, "Sword", "Sword", "Potion of Healing"]

    assert eligible_inventory_items(items, ItemDisposition.DESTRUCTION) == [
        "Sword",
        "Sword",
        "Potion of Healing",
    ]


def test_disposition_removal_keeps_exact_bag_identity_and_reports_contents() -> None:
    member = _member()
    first = add_bag_of_carrying(member)
    second = add_bag_of_carrying(member)
    first.contents.append("Sword")
    second.contents.extend(["Potion of Healing", "Scroll of Blessing"])

    result = remove_item_for_disposition(
        member,
        disposition=ItemDisposition.THEFT,
        inventory_index=1,
    )

    assert result.removed_item == "Bag of Carrying"
    assert result.contained_items == ("Potion of Healing", "Scroll of Blessing")
    assert member.inventory == ["Bag of Carrying"]
    assert [container.id for container in member.item_containers] == [first.id]
    assert member.item_containers[0].contents == ["Sword"]


def test_blocked_disposition_does_not_mutate_inventory() -> None:
    member = _member([STAR_OBJECT_ITEM, "Sword"])

    result = remove_item_for_disposition(
        member,
        disposition=ItemDisposition.CONFISCATION,
        inventory_index=0,
    )

    assert result.removed is False
    assert "remains bound" in result.blocked_reason
    assert member.inventory == [STAR_OBJECT_ITEM, "Sword"]
