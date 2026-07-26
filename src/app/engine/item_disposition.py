from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from ..schemas import ItemContainerState


class ItemDisposition(StrEnum):
    TRANSFER = "transfer"
    STORAGE = "storage"
    SALE = "sale"
    ORDINARY_LOSS = "ordinary_loss"
    DESTRUCTION = "destruction"
    SACRIFICE = "sacrifice"
    CONFISCATION = "confiscation"
    THEFT = "theft"


class InventoryHolder(Protocol):
    name: str
    inventory: list[str]
    item_containers: list[ItemContainerState]


@dataclass(frozen=True)
class ItemDispositionDecision:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class ItemDispositionResult:
    removed_item: str | None = None
    contained_items: tuple[str, ...] = ()
    blocked_reason: str = ""

    @property
    def removed(self) -> bool:
        return self.removed_item is not None


def item_disposition_decision(
    item_name: str,
    disposition: ItemDisposition,
) -> ItemDispositionDecision:
    from .star_object_curse import is_star_object_item

    if not is_star_object_item(item_name):
        return ItemDispositionDecision(allowed=True)
    if disposition == ItemDisposition.TRANSFER:
        reason = (
            "Bofto's cursed star-shaped object cannot be transferred, dropped, or given away. "
            "Only a carrier's death or Invisible Gremlins can move or remove it (TAG pp.30-31)."
        )
    elif disposition == ItemDisposition.STORAGE:
        reason = (
            "Bofto's cursed star-shaped object cannot be stored, banked, or placed in a magic locker. "
            "Only a carrier's death or Invisible Gremlins can move or remove it (TAG pp.30-31)."
        )
    elif disposition == ItemDisposition.SALE:
        reason = (
            "Bofto's cursed star-shaped object cannot be sold or discarded. "
            "Only Invisible Gremlins can break its curse (TAG p.30)."
        )
    else:
        reason = (
            "Bofto's cursed star-shaped object remains bound and is ineligible for ordinary "
            f"{disposition.value.replace('_', ' ')} (TAG pp.30-31)."
        )
    return ItemDispositionDecision(allowed=False, reason=reason)


def eligible_inventory_items(
    items: list[str],
    disposition: ItemDisposition = ItemDisposition.ORDINARY_LOSS,
) -> list[str]:
    return [
        item
        for item in items
        if item_disposition_decision(item, disposition).allowed
    ]


def remove_item_for_disposition(
    holder: InventoryHolder,
    *,
    disposition: ItemDisposition,
    item_name: str | None = None,
    inventory_index: int | None = None,
) -> ItemDispositionResult:
    if inventory_index is None:
        if not item_name:
            return ItemDispositionResult()
        try:
            inventory_index = holder.inventory.index(item_name)
        except ValueError:
            return ItemDispositionResult()
    if inventory_index < 0 or inventory_index >= len(holder.inventory):
        return ItemDispositionResult()

    selected_item = holder.inventory[inventory_index]
    decision = item_disposition_decision(selected_item, disposition)
    if not decision.allowed:
        return ItemDispositionResult(blocked_reason=decision.reason)

    from .item_containers import remove_inventory_item_with_contents

    removed, contents = remove_inventory_item_with_contents(
        holder,
        inventory_index=inventory_index,
    )
    return ItemDispositionResult(
        removed_item=removed,
        contained_items=tuple(contents),
    )
