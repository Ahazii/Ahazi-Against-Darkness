from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.schemas import Character, PartyMemberState
from .class_profiles import build_starting_inventory
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


@lru_cache
def _class_carry_baseline(class_id: str) -> tuple[int, int]:
    rules_path = Path(__file__).resolve().parents[3] / "data" / "rules" / "classes.json"
    classes = {item["id"]: item for item in json.loads(rules_path.read_text(encoding="utf-8"))}
    profile = classes.get(class_id.lower(), {})
    inventory = build_starting_inventory(class_id, list(profile.get("starting_inventory", [])))
    return weapon_carry_slots(inventory), count_carried_shields(inventory)


def carry_baseline(holder: InventoryHolder) -> tuple[int, int]:
    starting_weapon_slots = getattr(holder, "starting_weapon_slots", None)
    starting_shields = getattr(holder, "starting_shields", None)
    if starting_weapon_slots is not None and starting_shields is not None:
        return starting_weapon_slots, starting_shields
    class_id = getattr(holder, "class_id", "")
    return _class_carry_baseline(class_id) if class_id else (0, 0)


def snapshot_carry_baseline(member: PartyMemberState) -> None:
    member.starting_weapon_slots = weapon_carry_slots(member.inventory)
    member.starting_shields = count_carried_shields(member.inventory)


def max_weapon_carry(holder: InventoryHolder, *, servant_active: bool = False) -> int:
    baseline_weapons, _ = carry_baseline(holder)
    return baseline_weapons + effective_weapon_cap(servant_active=servant_active)


def is_over_encumbered(holder: InventoryHolder, *, servant_active: bool = False) -> bool:
    baseline_weapons, baseline_shields = carry_baseline(holder)
    return (
        holder.gold > effective_gold_cap(holder, servant_active=servant_active)
        or count_carried_shields(holder.inventory) > baseline_shields
        or weapon_carry_slots(holder.inventory) > baseline_weapons
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
        weapon_cap = max_weapon_carry(holder, servant_active=servant_active)
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
    payout_totals: dict[str, int] = {}
    capped_names: list[str] = []

    def servant_for(member: InventoryHolder) -> bool:
        character_id = getattr(member, "character_id", None)
        return bool(character_id and character_id in owner_ids)

    def record_payout(member: InventoryHolder, amount: int) -> None:
        key = getattr(member, "character_id", None) or member.name
        payout_totals[key] = payout_totals.get(key, 0) + amount

    count = len(members)
    base_share = gold_total // count
    extra = gold_total % count
    shares = [base_share + (1 if index < extra else 0) for index in range(count)]

    pool = gold_total
    for member, share in zip(members, shares, strict=False):
        capacity = gold_capacity(member, servant_active=servant_for(member))
        if share > 0 and capacity <= 0:
            capped_names.append(member.name)
        give = min(share, capacity)
        if give > 0:
            member.gold += give
            pool -= give
            record_payout(member, give)

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
            record_payout(member, take)
            added_any = True
            if pool <= 0:
                break
        if not added_any:
            break
    for member in members:
        key = getattr(member, "character_id", None) or member.name
        amount = payout_totals.get(key, 0)
        if amount > 0:
            payouts.append(f"{member.name} +{amount}gp")
        elif member.name in capped_names:
            payouts.append(f"{member.name} +0gp (at {effective_gold_cap(member, servant_active=servant_for(member))}gp cap)")
    return pool, payouts


def spend_living_carried_gold(
    members: list[PartyMemberState],
    amount: int,
) -> tuple[bool, list[str]]:
    """Spend a shared amount from living heroes' carried gold in party order."""
    living = [member for member in members if member.current_life > 0]
    if sum(member.gold for member in living) < amount:
        return False, []
    remaining = amount
    paid: list[str] = []
    for member in living:
        take = min(member.gold, remaining)
        if take <= 0:
            continue
        member.gold -= take
        remaining -= take
        paid.append(f"{member.name} -{take}gp")
        if remaining <= 0:
            break
    return True, [f"Payment: {', '.join(paid)}."]


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
        candidates = [members[(index + offset) % len(members)] for offset in range(len(members))]
        if _parse_weapon_item(item) is not None:
            wielders: list[InventoryHolder] = []
            carriers: list[InventoryHolder] = []
            for member in candidates:
                ok, _ = can_add_item(member, item)
                if not ok:
                    continue
                if isinstance(member, PartyMemberState):
                    allowed, _ = can_member_wield_weapon(member, item)
                    if allowed:
                        wielders.append(member)
                    else:
                        carriers.append(member)
                else:
                    wielders.append(member)
            candidates = wielders or carriers
        for member in candidates:
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
    item_container_id: str | None = None,
) -> tuple[bool, str]:
    if not item_name or not item_name.strip():
        return False, "Choose an item to transfer."
    from .item_disposition import ItemDisposition, item_disposition_decision

    disposition = item_disposition_decision(item_name, ItemDisposition.TRANSFER)
    if not disposition.allowed:
        return False, disposition.reason
    from .tag_repeatable_services import SHOES_OF_FAST_WALK

    if item_name.strip().casefold() == SHOES_OF_FAST_WALK.casefold():
        from .equipment_shop import can_class_use_item

        allowed, reason = can_class_use_item(
            str(getattr(target, "class_id", "")),
            {"category": "magic_item", "magic": True},
        )
        if not allowed:
            return False, reason or f"{target.name} cannot use Shoes of Fast Walk."
    from .item_containers import bag_for_inventory_index, bag_inventory_index, is_bag_of_carrying

    if is_bag_of_carrying(item_name):
        from .scrolls import barbarian_cannot_use_magic

        if barbarian_cannot_use_magic(str(getattr(target, "class_id", ""))):
            return False, (
                f"{target.name} will not carry a Bag of Carrying because that character cannot use magic items "
                "(TAG p.13, Bag of Carrying)."
            )
        source_containers = getattr(source, "item_containers", None)
        target_containers = getattr(target, "item_containers", None)
        if source_containers is None or target_containers is None:
            return False, "Bag of Carrying contents are unavailable on this inventory holder."
        if item_container_id:
            index = bag_inventory_index(source, item_container_id)
            bag = next((item for item in source_containers if item.id == item_container_id), None)
        else:
            try:
                index = source.inventory.index(item_name)
            except ValueError:
                index = None
            bag = bag_for_inventory_index(source, index) if index is not None else None
        if index is None or bag is None:
            return False, f"{source.name} does not carry that Bag of Carrying."
        source.inventory.pop(index)
        source_containers.remove(bag)
        target.inventory.append(item_name)
        target_containers.append(bag)
        contents = f" with {len(bag.contents)} contained item(s)" if bag.contents else ""
        return True, f"{source.name} gives {item_name}{contents} to {target.name}."
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
    item_container_id: str | None = None,
) -> tuple[bool, str]:
    if from_character_id == to_character_id:
        return False, "Choose a different hero to receive the item."
    source = _living_member(party, from_character_id)
    if source is None:
        return False, "Choose a living hero to give from."
    target = _living_member(party, to_character_id)
    if target is None:
        return False, "Choose a living hero to receive the item."
    return transfer_item_between(
        source,
        target,
        item_name=item_name,
        item_container_id=item_container_id,
    )


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
    item_container_id: str | None = None,
) -> tuple[bool, str]:
    if source.id == target.id:
        return False, "Choose a different hero to receive the item."
    return transfer_item_between(
        source,
        target,
        item_name=item_name,
        item_container_id=item_container_id,
    )


def transfer_character_gold(
    source: Character,
    target: Character,
    *,
    amount: int,
) -> tuple[bool, str]:
    if source.id == target.id:
        return False, "Choose a different hero to receive the gold."
    return transfer_gold_between(source, target, amount=amount, enforce_carry_limit=False)
