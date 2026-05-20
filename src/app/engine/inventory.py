from __future__ import annotations

from typing import Protocol

from app.schemas import Character, PartyMemberState
from .weapons import _parse_weapon_item, prune_weapon_defaults, weapon_item_slots

MAX_CARRIED_GOLD = 200
MAX_CARRIED_SHIELDS = 2
MAX_CARRIED_WEAPONS = 3


class InventoryHolder(Protocol):
    name: str
    gold: int
    inventory: list[str]


def is_carried_shield(item: str) -> bool:
    return "shield" in item.lower()


def is_carried_weapon(item: str) -> bool:
    return _parse_weapon_item(item) is not None


def count_carried_shields(inventory: list[str]) -> int:
    return sum(1 for item in inventory if is_carried_shield(item))


def count_carried_weapons(inventory: list[str]) -> int:
    return weapon_carry_slots(inventory)


def weapon_carry_slots(inventory: list[str]) -> int:
    return sum(weapon_item_slots(item) for item in inventory if is_carried_weapon(item))


def is_over_encumbered(holder: InventoryHolder) -> bool:
    return (
        holder.gold > MAX_CARRIED_GOLD
        or count_carried_shields(holder.inventory) > MAX_CARRIED_SHIELDS
        or weapon_carry_slots(holder.inventory) > MAX_CARRIED_WEAPONS
    )


def encumbrance_penalty(holder: InventoryHolder) -> int:
    return -1 if is_over_encumbered(holder) else 0


def gold_capacity(holder: InventoryHolder) -> int:
    return max(0, MAX_CARRIED_GOLD - holder.gold)


def can_add_gold(holder: InventoryHolder, amount: int, *, enforce_carry_limit: bool = True) -> tuple[bool, str]:
    if amount <= 0:
        return True, ""
    if not enforce_carry_limit:
        return True, ""
    if amount > gold_capacity(holder):
        return False, (
            f"{holder.name} can carry at most {MAX_CARRIED_GOLD}gp "
            f"({gold_capacity(holder)}gp free)."
        )
    return True, ""


def can_add_item(holder: InventoryHolder, item: str) -> tuple[bool, str]:
    if is_carried_shield(item):
        if count_carried_shields(holder.inventory) >= MAX_CARRIED_SHIELDS:
            return False, f"{holder.name} already carries {MAX_CARRIED_SHIELDS} shield(s)."
    if is_carried_weapon(item):
        slots = weapon_item_slots(item)
        if weapon_carry_slots(holder.inventory) + slots > MAX_CARRIED_WEAPONS:
            return False, (
                f"{holder.name} has no room for another weapon "
                f"({MAX_CARRIED_WEAPONS} slots; two-handed weapons use 2)."
            )
    return True, ""


def distribute_gold_among(members: list[InventoryHolder], gold_total: int) -> tuple[int, list[str]]:
    remaining = gold_total
    payouts: list[str] = []
    if remaining <= 0 or not members:
        return remaining, payouts
    while remaining > 0:
        added_any = False
        for member in members:
            capacity = gold_capacity(member)
            if capacity <= 0:
                continue
            take = min(capacity, remaining)
            member.gold += take
            remaining -= take
            added_any = True
            if take:
                payouts.append(f"{member.name} +{take}gp")
            if remaining <= 0:
                break
        if not added_any:
            break
    return remaining, payouts


def distribute_items_among(members: list[InventoryHolder], items: list[str]) -> tuple[list[str], list[str]]:
    uncarried: list[str] = []
    placed: list[str] = []
    if not members:
        return list(items), placed
    for index, item in enumerate(items):
        assigned = False
        for offset in range(len(members)):
            member = members[(index + offset) % len(members)]
            ok, _ = can_add_item(member, item)
            if not ok:
                continue
            member.inventory.append(item)
            placed.append(item)
            assigned = True
            break
        if not assigned:
            uncarried.append(item)
    return uncarried, placed


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
    ok, message = can_add_item(target, item_name)
    if not ok:
        return False, message
    item = source.inventory.pop(index)
    target.inventory.append(item)
    if isinstance(source, PartyMemberState):
        prune_weapon_defaults(source)
    if isinstance(target, PartyMemberState):
        prune_weapon_defaults(target)
    return True, f"{source.name} gives {item} to {target.name}."


def transfer_gold_between(
    source: InventoryHolder,
    target: InventoryHolder,
    *,
    amount: int,
    enforce_carry_limit: bool = True,
) -> tuple[bool, str]:
    if amount <= 0:
        return False, "Transfer at least 1gp."
    if source.gold < amount:
        return False, f"{source.name} only has {source.gold}gp."
    ok, message = can_add_gold(target, amount, enforce_carry_limit=enforce_carry_limit)
    if not ok:
        return False, message
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
    return transfer_gold_between(source, target, amount=amount, enforce_carry_limit=False)
