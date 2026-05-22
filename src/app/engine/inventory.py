from __future__ import annotations

from typing import Protocol

from app.schemas import Character, PartyMemberState
from .magic_weapons import can_member_wield_weapon
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


def has_illusionary_servant(session: object | None, character_id: str | None) -> bool:
    if session is None or not character_id:
        return False
    return bool(
        getattr(session, "illusionary_servant_active", False)
        and getattr(session, "illusionary_servant_owner_id", None) == character_id
    )


def effective_gold_cap(holder: InventoryHolder, *, servant_active: bool = False) -> int:
    return MAX_CARRIED_GOLD + (MAX_CARRIED_GOLD if servant_active else 0)


def effective_weapon_cap(*, servant_active: bool = False) -> int:
    return MAX_CARRIED_WEAPONS + (MAX_CARRIED_WEAPONS if servant_active else 0)


def is_over_encumbered(holder: InventoryHolder, *, servant_active: bool = False) -> bool:
    return (
        holder.gold > effective_gold_cap(holder, servant_active=servant_active)
        or count_carried_shields(holder.inventory) > MAX_CARRIED_SHIELDS
        or weapon_carry_slots(holder.inventory) > effective_weapon_cap(servant_active=servant_active)
    )


def encumbrance_penalty(holder: InventoryHolder, *, servant_active: bool = False) -> int:
    return -1 if is_over_encumbered(holder, servant_active=servant_active) else 0


def gold_capacity(holder: InventoryHolder, *, servant_active: bool = False) -> int:
    return max(0, effective_gold_cap(holder, servant_active=servant_active) - holder.gold)


def can_add_gold(holder: InventoryHolder, amount: int, *, enforce_carry_limit: bool = True, servant_active: bool = False) -> tuple[bool, str]:
    if amount <= 0:
        return True, ""
    if not enforce_carry_limit:
        return True, ""
    cap = effective_gold_cap(holder, servant_active=servant_active)
    if holder.gold + amount > cap:
        return False, (
            f"{holder.name} can carry at most {cap}gp "
            f"({gold_capacity(holder, servant_active=servant_active)}gp free)."
        )
    return True, ""


def can_add_item(holder: InventoryHolder, item: str, *, servant_active: bool = False) -> tuple[bool, str]:
    if is_carried_shield(item):
        if count_carried_shields(holder.inventory) >= MAX_CARRIED_SHIELDS:
            return False, f"{holder.name} already carries {MAX_CARRIED_SHIELDS} shield(s)."
    if is_carried_weapon(item):
        slots = weapon_item_slots(item)
        weapon_cap = effective_weapon_cap(servant_active=servant_active)
        if weapon_carry_slots(holder.inventory) + slots > weapon_cap:
            return False, (
                f"{holder.name} has no room for another weapon "
                f"({weapon_cap} slots; two-handed weapons use 2)."
            )
    return True, ""


def distribute_gold_among(
    members: list[InventoryHolder],
    gold_total: int,
    *,
    servant_owner_ids: set[str] | None = None,
) -> tuple[int, list[str]]:
    payouts: list[str] = []
    if gold_total <= 0 or not members:
        return gold_total, payouts

    owner_ids = servant_owner_ids or set()

    def servant_for(member: InventoryHolder) -> bool:
        character_id = getattr(member, "character_id", None)
        return bool(character_id and character_id in owner_ids)

    count = len(members)
    base_share = gold_total // count
    extra = gold_total % count
    shares = [base_share + (1 if index < extra else 0) for index in range(count)]

    pool = gold_total
    for member, share in zip(members, shares, strict=False):
        give = min(share, gold_capacity(member, servant_active=servant_for(member)))
        if give > 0:
            member.gold += give
            pool -= give
            payouts.append(f"{member.name} +{give}gp")

    while pool > 0:
        added_any = False
        for member in members:
            capacity = gold_capacity(member, servant_active=servant_for(member))
            if capacity <= 0:
                continue
            take = min(capacity, pool)
            if take <= 0:
                continue
            member.gold += take
            pool -= take
            payouts.append(f"{member.name} +{take}gp")
            added_any = True
            if pool <= 0:
                break
        if not added_any:
            break
    return pool, payouts


def bandages_in_inventory(member: InventoryHolder) -> list[str]:
    return [item for item in member.inventory if "bandage" in item.lower()]


def can_receive_bandage(member: InventoryHolder) -> tuple[bool, str]:
    current_life = getattr(member, "current_life", 0)
    max_life = getattr(member, "max_life", current_life)
    if current_life <= 0:
        return False, "Fallen heroes cannot be bandaged."
    if current_life >= max_life:
        return False, f"{member.name} is already at full Life."
    class_id = getattr(member, "class_id", "").lower()
    if class_id == "kukla":
        return False, "Bandages cannot repair a kukla."
    return True, ""


def can_apply_bandage(member: InventoryHolder, *, bandage_used_character_ids: set[str] | None = None) -> tuple[bool, str]:
    if getattr(member, "current_life", 0) <= 0:
        return False, "Fallen heroes cannot apply bandages."
    class_id = getattr(member, "class_id", "").lower()
    if class_id == "kukla":
        return False, "Bandages cannot repair a kukla."
    used = bandage_used_character_ids or set()
    character_id = getattr(member, "character_id", None)
    if character_id and character_id in used:
        return False, f"{member.name} already used a bandage this adventure."
    if not bandages_in_inventory(member):
        return False, f"{member.name} has no bandages."
    return True, ""


def can_use_bandage(member: InventoryHolder, *, bandage_used_character_ids: set[str] | None = None) -> tuple[bool, str]:
    ok, message = can_apply_bandage(member, bandage_used_character_ids=bandage_used_character_ids)
    if not ok:
        return ok, message
    return can_receive_bandage(member)


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
            if isinstance(member, PartyMemberState) and _parse_weapon_item(item) is not None:
                allowed, _ = can_member_wield_weapon(member, item)
                if not allowed:
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
