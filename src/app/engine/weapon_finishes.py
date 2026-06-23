from __future__ import annotations

import re
from collections.abc import Callable

from ..schemas import PartyMemberState
from .dice import roll_d6
from .weapons import _parse_weapon_item

SILVERED_SUFFIX = "(silvered)"
GILDED_SUFFIX = "(gilded)"
POISONED_SUFFIX = "(poisoned)"

FIENDISH_WEAPON_CHOICES: dict[str, str] = {
    "light_weapon": "Light hand weapon",
    "hand_weapon": "Hand weapon",
    "two_handed_weapon": "Two-handed weapon",
    "bow": "Bow",
    "crossbow": "Crossbow",
    "sling": "Sling",
}

WEAPON_SERVICE_KEYS = frozenset({"silvering_light", "silvering_two_handed", "gilding"})
LEAFSTEEL_ARMOR_ITEM = "Leafsteel armor (3 adventures)"
LEAFSTEEL_ADVENTURES_RE = re.compile(r"leafsteel armor\s*\((\d+)\s*adventures?\)", re.IGNORECASE)


def strip_weapon_finishes(item: str) -> str:
    cleaned = item.strip()
    for suffix in (SILVERED_SUFFIX, GILDED_SUFFIX, POISONED_SUFFIX):
        if cleaned.lower().endswith(suffix):
            cleaned = cleaned[: -len(suffix)].rstrip()
    return cleaned


def is_weapon_item_silvered(item: str) -> bool:
    lower = item.lower()
    return SILVERED_SUFFIX in lower or "silver-coated" in lower


def is_weapon_item_gilded(item: str) -> bool:
    return GILDED_SUFFIX in item.lower()


def is_weapon_item_poisoned(item: str) -> bool:
    return POISONED_SUFFIX in item.lower()


def apply_weapon_finish(item: str, finish: str) -> str:
    base = strip_weapon_finishes(item)
    lower_finish = finish.lower()
    if lower_finish == "silvered":
        if is_weapon_item_gilded(base):
            base = strip_weapon_finishes(base)
        return f"{base} {SILVERED_SUFFIX}".strip()
    if lower_finish == "gilded":
        if is_weapon_item_silvered(base):
            base = strip_weapon_finishes(base)
        return f"{base} {GILDED_SUFFIX}".strip()
    if lower_finish == "poisoned":
        return f"{base} {POISONED_SUFFIX}".strip()
    return item


def weapon_is_two_handed(item: str) -> bool:
    profile = _parse_weapon_item(item)
    return bool(profile and (profile.two_handed or profile.two_slot))


def inventory_weapon_candidates(inventory: list[str]) -> list[str]:
    candidates: list[str] = []
    for item in inventory:
        if _parse_weapon_item(item) is None:
            continue
        lower = item.lower()
        if lower.startswith("magic ") or "+1 attack" in lower or "+2 attack" in lower:
            continue
        candidates.append(item)
    return candidates


def can_apply_weapon_service(shop_key: str, weapon_item: str) -> tuple[bool, str]:
    profile = _parse_weapon_item(weapon_item)
    if profile is None:
        return False, f"{weapon_item} is not a weapon."
    lower = weapon_item.lower()
    if lower.startswith("magic ") or "+1 attack" in lower or "+2 attack" in lower:
        return False, "Magic weapons cannot be silvered or gilded."
    two_handed = weapon_is_two_handed(weapon_item)
    if shop_key == "silvering_two_handed":
        if not two_handed:
            return False, "Two-handed silvering applies only to two-handed weapons or bows."
        return True, ""
    if shop_key == "silvering_light":
        if two_handed:
            return False, "Light/hand silvering applies only to one-slot weapons."
        return True, ""
    if shop_key == "gilding":
        return True, ""
    return False, "Unknown weapon service."


def rename_inventory_weapon(
    inventory: list[str],
    old_name: str,
    new_name: str,
    *,
    default_melee: str | None = None,
    default_melee_secondary: str | None = None,
    default_missile: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    if old_name not in inventory:
        raise ValueError(f"{old_name} is not in inventory.")
    index = inventory.index(old_name)
    inventory[index] = new_name
    melee = default_melee
    melee_secondary = default_melee_secondary
    missile = default_missile
    if melee == old_name:
        melee = new_name
    if melee_secondary == old_name:
        melee_secondary = new_name
    if missile == old_name:
        missile = new_name
    return melee, melee_secondary, missile


def apply_weapon_service_to_inventory(
    inventory: list[str],
    shop_key: str,
    weapon_item: str,
    *,
    default_melee: str | None = None,
    default_melee_secondary: str | None = None,
    default_missile: str | None = None,
    owner_name: str = "Hero",
) -> tuple[bool, str, str | None, str | None, str | None]:
    allowed, message = can_apply_weapon_service(shop_key, weapon_item)
    if not allowed:
        return False, message, default_melee, default_melee_secondary, default_missile
    finish = "silvered" if shop_key.startswith("silvering") else "gilded"
    if finish == "silvered" and is_weapon_item_silvered(weapon_item):
        return False, f"{weapon_item} is already silvered.", default_melee, default_melee_secondary, default_missile
    if finish == "gilded" and is_weapon_item_gilded(weapon_item):
        return False, f"{weapon_item} is already gilded.", default_melee, default_melee_secondary, default_missile
    new_name = apply_weapon_finish(weapon_item, finish)
    melee, melee_secondary, missile = rename_inventory_weapon(
        inventory,
        weapon_item,
        new_name,
        default_melee=default_melee,
        default_melee_secondary=default_melee_secondary,
        default_missile=default_missile,
    )
    label = "silvered" if finish == "silvered" else "gilded"
    return (
        True,
        f"{owner_name}'s {strip_weapon_finishes(weapon_item)} is now {label} ({new_name}).",
        melee,
        melee_secondary,
        missile,
    )


def apply_weapon_service_to_character(character, shop_key: str, weapon_item: str) -> tuple[bool, str]:
    ok, message, melee, melee_secondary, missile = apply_weapon_service_to_inventory(
        character.inventory,
        shop_key,
        weapon_item,
        default_melee=character.default_melee_weapon,
        default_melee_secondary=character.default_melee_weapon_secondary,
        default_missile=character.default_missile_weapon,
        owner_name=character.name,
    )
    if not ok:
        return False, message
    character.default_melee_weapon = melee
    character.default_melee_weapon_secondary = melee_secondary
    character.default_missile_weapon = missile
    return True, message


def apply_weapon_service_to_member(member: PartyMemberState, shop_key: str, weapon_item: str) -> tuple[bool, str]:
    ok, message, melee, melee_secondary, missile = apply_weapon_service_to_inventory(
        member.inventory,
        shop_key,
        weapon_item,
        default_melee=member.default_melee_weapon,
        default_melee_secondary=member.default_melee_weapon_secondary,
        default_missile=member.default_missile_weapon,
        owner_name=member.name,
    )
    if not ok:
        return False, message
    member.default_melee_weapon = melee
    member.default_melee_weapon_secondary = melee_secondary
    member.default_missile_weapon = missile
    return True, message


def roll_two_in_six(*, roll_fn: Callable[[], int] | None = None) -> tuple[bool, int, list[str]]:
    roller = roll_fn or roll_d6
    value = roller()
    success = value <= 2
    note = "silvered" if success else "not silvered"
    return success, value, [f"Silvered weapon chance: d6 = {value} ({note})."]


def build_fiendish_treasure_weapon(pick: str, *, silvered: bool) -> tuple[str, list[str]]:
    base = FIENDISH_WEAPON_CHOICES.get(pick)
    if base is None:
        return "", [f"Unknown fiendish weapon choice: {pick}."]
    if silvered:
        return apply_weapon_finish(base, "silvered"), []
    return base, []


def weapon_finish_resale_bonus(item: str) -> int:
    profile = _parse_weapon_item(item)
    if profile is None:
        return 0
    two_handed = weapon_is_two_handed(item)
    bonus = 0
    if is_weapon_item_silvered(item):
        bonus += 40 if two_handed else 20
    if is_weapon_item_gilded(item):
        bonus += 50 if two_handed else 25
    return bonus


def member_wields_silvered_weapon(member: PartyMemberState | None, weapon_item: str | None) -> bool:
    if member is None:
        return False
    if any("silvered weapons" in status.lower() for status in member.statuses):
        return True
    return bool(weapon_item and is_weapon_item_silvered(weapon_item))


def member_wields_gilded_weapon(member: PartyMemberState | None, weapon_item: str | None) -> bool:
    if member is None:
        return False
    if any("gilded weapons" in status.lower() for status in member.statuses):
        return True
    return bool(weapon_item and is_weapon_item_gilded(weapon_item))


def member_wields_poisoned_weapon(member: PartyMemberState | None, weapon_item: str | None) -> bool:
    if member is None:
        return False
    return bool(weapon_item and is_weapon_item_poisoned(weapon_item))


def is_leafsteel_armor(item: str) -> bool:
    return "leafsteel armor" in item.lower()


def leafsteel_adventures_remaining(item: str) -> int | None:
    match = LEAFSTEEL_ADVENTURES_RE.search(item)
    if match:
        return int(match.group(1))
    if item.strip().lower() == "leafsteel armor":
        return 3
    return None


def format_leafsteel_armor(adventures_remaining: int = 3) -> str:
    remaining = max(0, adventures_remaining)
    return f"Leafsteel armor ({remaining} adventures)"


def tick_leafsteel_after_adventure(member: PartyMemberState) -> list[str]:
    log: list[str] = []
    updated: list[str] = []
    for item in member.inventory:
        if not is_leafsteel_armor(item):
            updated.append(item)
            continue
        remaining = leafsteel_adventures_remaining(item)
        if remaining is None:
            updated.append(item)
            continue
        next_remaining = remaining - 1
        if next_remaining <= 0:
            log.append(f"{member.name}'s Leafsteel armor decays after three adventures and is discarded.")
            continue
        updated.append(format_leafsteel_armor(next_remaining))
        log.append(f"{member.name}'s Leafsteel armor has {next_remaining} adventure(s) remaining.")
    member.inventory = updated
    if member.default_melee_weapon and member.default_melee_weapon not in member.inventory:
        member.default_melee_weapon = None
    if member.default_melee_weapon_secondary and member.default_melee_weapon_secondary not in member.inventory:
        member.default_melee_weapon_secondary = None
    if member.default_missile_weapon and member.default_missile_weapon not in member.inventory:
        member.default_missile_weapon = None
    return log


def leafsteel_defense_bonus(member: PartyMemberState) -> int:
    if any(is_leafsteel_armor(item) for item in member.inventory):
        return 2
    return 0


def leafsteel_counts_as_light_armor(member: PartyMemberState) -> bool:
    return any(is_leafsteel_armor(item) for item in member.inventory)
