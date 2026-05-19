from __future__ import annotations

from typing import Protocol

from app.schemas import Character, PartyMemberState


class InventoryHolder(Protocol):
    name: str
    gold: int
    inventory: list[str]


def transfer_item_between(
    source: InventoryHolder,
    target: InventoryHolder,
    *,
    item_name: str,
) -> tuple[bool, str]:
    if not item_name or not item_name.strip():
        return False, "Choose an item to transfer."
    try:
        index = source.inventory.index(item_name)
    except ValueError:
        return False, f"{source.name} does not carry {item_name}."
    item = source.inventory.pop(index)
    target.inventory.append(item)
    return True, f"{source.name} gives {item} to {target.name}."


def transfer_gold_between(
    source: InventoryHolder,
    target: InventoryHolder,
    *,
    amount: int,
) -> tuple[bool, str]:
    if amount <= 0:
        return False, "Transfer at least 1gp."
    if source.gold < amount:
        return False, f"{source.name} only has {source.gold}gp."
    source.gold -= amount
    target.gold += amount
    return True, f"{source.name} gives {amount}gp to {target.name}."


def _living_member(
    party: list[PartyMemberState], character_id: str
) -> PartyMemberState | None:
    member = next((item for item in party if item.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        return None
    return member


def transfer_inventory_item(
    party: list[PartyMemberState],
    *,
    from_character_id: str,
    to_character_id: str,
    item_name: str,
) -> tuple[bool, str]:
    if from_character_id == to_character_id:
        return False, "Choose a different hero to receive the item."
    source = _living_member(party, from_character_id)
    if source is None:
        return False, "Choose a living hero to give from."
    target = _living_member(party, to_character_id)
    if target is None:
        return False, "Choose a living hero to receive the item."
    return transfer_item_between(source, target, item_name=item_name)


def transfer_gold(
    party: list[PartyMemberState],
    *,
    from_character_id: str,
    to_character_id: str,
    amount: int,
) -> tuple[bool, str]:
    if from_character_id == to_character_id:
        return False, "Choose a different hero to receive the gold."
    source = _living_member(party, from_character_id)
    if source is None:
        return False, "Choose a living hero to give from."
    target = _living_member(party, to_character_id)
    if target is None:
        return False, "Choose a living hero to receive the gold."
    return transfer_gold_between(source, target, amount=amount)


def transfer_character_item(
    source: Character,
    target: Character,
    *,
    item_name: str,
) -> tuple[bool, str]:
    if source.id == target.id:
        return False, "Choose a different hero to receive the item."
    return transfer_item_between(source, target, item_name=item_name)


def transfer_character_gold(
    source: Character,
    target: Character,
    *,
    amount: int,
) -> tuple[bool, str]:
    if source.id == target.id:
        return False, "Choose a different hero to receive the gold."
    return transfer_gold_between(source, target, amount=amount)
