from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from ..schemas import ItemContainerState, PartyMemberState


BAG_OF_CARRYING = "Bag of Carrying"


class ContainerHolder(Protocol):
    name: str
    inventory: list[str]
    item_containers: list[ItemContainerState]


def is_bag_of_carrying(item_name: str) -> bool:
    return str(item_name or "").strip().lower() == BAG_OF_CARRYING.lower()


def add_bag_of_carrying(holder: ContainerHolder) -> ItemContainerState:
    container = ItemContainerState(id=uuid4().hex)
    holder.inventory.append(BAG_OF_CARRYING)
    holder.item_containers.append(container)
    return container


def item_container(holder: ContainerHolder, container_id: str | None) -> ItemContainerState | None:
    if not container_id:
        return None
    return next((container for container in holder.item_containers if container.id == container_id), None)


def bag_for_inventory_index(holder: ContainerHolder, inventory_index: int) -> ItemContainerState | None:
    if inventory_index < 0 or inventory_index >= len(holder.inventory):
        return None
    if not is_bag_of_carrying(holder.inventory[inventory_index]):
        return None
    bag_position = sum(
        1
        for item in holder.inventory[: inventory_index + 1]
        if is_bag_of_carrying(item)
    ) - 1
    bags = [container for container in holder.item_containers if container.kind == "bag_of_carrying"]
    return bags[bag_position] if 0 <= bag_position < len(bags) else None


def bag_inventory_index(holder: ContainerHolder, container_id: str) -> int | None:
    bags = [container for container in holder.item_containers if container.kind == "bag_of_carrying"]
    bag_position = next((index for index, bag in enumerate(bags) if bag.id == container_id), None)
    if bag_position is None:
        return None
    seen = -1
    for index, item in enumerate(holder.inventory):
        if not is_bag_of_carrying(item):
            continue
        seen += 1
        if seen == bag_position:
            return index
    return None


def remove_inventory_item_with_contents(
    holder: ContainerHolder,
    *,
    item_name: str | None = None,
    inventory_index: int | None = None,
) -> tuple[str | None, list[str]]:
    """Remove one loose item and discard any contents belonging to that exact container."""
    if inventory_index is None:
        if not item_name:
            return None, []
        try:
            inventory_index = holder.inventory.index(item_name)
        except ValueError:
            return None, []
    if inventory_index < 0 or inventory_index >= len(holder.inventory):
        return None, []
    bag = bag_for_inventory_index(holder, inventory_index)
    removed = holder.inventory.pop(inventory_index)
    contents: list[str] = []
    if bag is not None:
        contents = list(bag.contents)
        holder.item_containers.remove(bag)
    if isinstance(holder, PartyMemberState):
        from .weapons import prune_weapon_defaults

        prune_weapon_defaults(holder)
    return removed, contents


def contained_loss_suffix(contents: list[str]) -> str:
    if not contents:
        return ""
    return f" and everything inside ({', '.join(contents)})"


def put_item_in_bag(
    holder: ContainerHolder,
    *,
    container_id: str | None,
    item_name: str | None,
) -> tuple[bool, str]:
    from .star_object_curse import is_star_object_item
    from .weapons import prune_weapon_defaults

    bag = item_container(holder, container_id)
    if bag is None:
        return False, "Choose a Bag of Carrying."
    if not item_name:
        return False, "Choose a loose item to put in the Bag of Carrying."
    if is_star_object_item(item_name):
        return False, (
            "Bofto's cursed star-shaped object cannot be stored. Only a carrier's death or "
            "Invisible Gremlins can move or remove it (TAG pp.30-31)."
        )
    if is_bag_of_carrying(item_name):
        return False, "A Bag of Carrying must remain a top-level container; bags cannot be nested."
    try:
        index = holder.inventory.index(item_name)
    except ValueError:
        return False, f"{holder.name} does not carry {item_name} loose."
    bag.contents.append(holder.inventory.pop(index))
    if isinstance(holder, PartyMemberState):
        prune_weapon_defaults(holder)
    return True, f"{holder.name} puts {item_name} in {bag.name}."


def take_item_from_bag(
    holder: ContainerHolder,
    *,
    container_id: str | None,
    item_name: str | None,
) -> tuple[bool, str]:
    from .inventory import can_add_item

    bag = item_container(holder, container_id)
    if bag is None:
        return False, "Choose a Bag of Carrying."
    if not item_name:
        return False, "Choose an item to take out of the Bag of Carrying."
    try:
        index = bag.contents.index(item_name)
    except ValueError:
        return False, f"{bag.name} does not contain {item_name}."
    ok, message = can_add_item(holder, item_name)
    if not ok:
        return False, message
    holder.inventory.append(bag.contents.pop(index))
    return True, f"{holder.name} takes {item_name} out of {bag.name}."
