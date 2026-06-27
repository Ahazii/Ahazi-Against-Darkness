from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..schemas import PartyMemberState
from .dice import roll_d6

if TYPE_CHECKING:
    from .weapons import WeaponProfile

MAGIC_WEAPON_TYPES: dict[int, str] = {
    1: "Magic Club (Light weapon, +1 Attack)",
    2: "Magic Dagger (Light weapon, +1 Attack)",
    3: "Magic Mace (Hand weapon, +1 Attack)",
    4: "Magic Sword (Hand weapon, +1 Attack)",
    5: "Magic Greatsword (Heavy weapon, +1 Attack)",
    6: "Magic Bow (Bow, +1 Attack)",
}

FIENDISH_MAGIC_WEAPON_TYPES: dict[int, tuple[str, str]] = {
    1: ("Magic Dagger (Light weapon", "slashing"),
    2: ("Magic Mace (Hand weapon", "crushing"),
    3: ("Magic Sword (Hand weapon", "slashing"),
    4: ("Magic Sword (Hand weapon", "slashing"),
    5: ("Magic Greatsword (Heavy weapon", "crushing"),
    6: ("Magic Greatsword (Heavy weapon", "slashing"),
}

BASE_WEAPON_PRICE_GP: dict[str, int] = {
    "light_weapon": 5,
    "hand_weapon": 6,
    "two_handed_weapon": 15,
    "bow": 15,
}


def is_magic_weapon_placeholder(item: str) -> bool:
    lower = item.lower()
    return "magic weapon" in lower and ("+1" in lower or "+2" in lower)


def is_magic_weapon(item: str) -> bool:
    if is_magic_weapon_placeholder(item):
        return True
    lower = item.lower()
    if "magic shovel" in lower:
        return True
    return lower.startswith("magic ") and ("+1 attack" in lower or "+2 attack" in lower)


def magic_weapon_attack_bonus(item: str) -> int:
    if not is_magic_weapon(item):
        return 0
    if "+2 attack" in item.lower():
        return 2
    return 1


def roll_magic_weapon_name(*, roll: int | None = None, roll_fn: Callable[[], int] | None = None) -> tuple[str, int]:
    roller = roll_fn or roll_d6
    value = roll if roll is not None else roller()
    value = max(1, min(6, value))
    return MAGIC_WEAPON_TYPES[value], value


def roll_fiendish_magic_weapon_name(
    *,
    bonus: int,
    type_roll: int | None = None,
    roll_fn: Callable[[], int] | None = None,
) -> tuple[str, int]:
    roller = roll_fn or roll_d6
    value = type_roll if type_roll is not None else roller()
    value = max(1, min(6, value))
    label, _kind = FIENDISH_MAGIC_WEAPON_TYPES[value]
    return f"{label}, +{bonus} Attack)", value


def resolve_magic_weapon_placeholder(
    item: str,
    *,
    roll: int | None = None,
    roll_fn: Callable[[], int] | None = None,
) -> tuple[str, int | None]:
    if not is_magic_weapon_placeholder(item):
        return item, None
    lower = item.lower()
    if "+1 or +2" in lower:
        roller = roll_fn or roll_d6
        bonus_roll = roll if roll is not None else roller()
        bonus = 2 if bonus_roll >= 5 else 1
        type_roll = roller()
        name, rolled = roll_fiendish_magic_weapon_name(bonus=bonus, type_roll=type_roll, roll_fn=roll_fn)
        return name, rolled
    name, rolled = roll_magic_weapon_name(roll=roll, roll_fn=roll_fn)
    return name, rolled


def resolve_treasure_item_list(
    items: list[str],
    *,
    roll_fn: Callable[[], int] | None = None,
) -> tuple[list[str], list[str]]:
    from .magic_armor import resolve_magic_armor_placeholder

    log: list[str] = []
    resolved: list[str] = []
    for item in items:
        if is_magic_weapon_placeholder(item):
            if "+1 or +2" in item.lower():
                roller = roll_fn or roll_d6
                bonus_roll = roller()
                bonus = 2 if bonus_roll >= 5 else 1
                type_roll = roller()
                name, _ = roll_fiendish_magic_weapon_name(bonus=bonus, type_roll=type_roll, roll_fn=roll_fn)
                log.append(
                    f"Fiendish magic weapon: bonus d6 = {bonus_roll} (+{bonus}); type d6 = {type_roll} -> {name}."
                )
            else:
                name, rolled = resolve_magic_weapon_placeholder(item, roll_fn=roll_fn)
                log.append(f"Magic weapon type: d6 = {rolled} -> {name}.")
            resolved.append(name)
        elif "magic armor" in item.lower():
            from .magic_armor import is_magic_armor_placeholder, resolve_magic_armor_placeholder

            if is_magic_armor_placeholder(item):
                name, rolled = resolve_magic_armor_placeholder(item, roll_fn=roll_fn)
                log.append(f"Fiendish magic armor type d6 = {rolled} -> {name}.")
                resolved.append(name)
            else:
                resolved.append(item)
        else:
            resolved.append(item)
    return resolved, log


def weapon_shop_category(profile: WeaponProfile) -> str:
    if profile.kind == "missile":
        return "bow" if "bow" in profile.item.lower() else "sling"
    if profile.two_handed:
        return "two_handed_weapon"
    if profile.light:
        return "light_weapon"
    return "hand_weapon"


def magic_weapon_resale_gp(item: str) -> int | None:
    if not is_magic_weapon(item) or is_magic_weapon_placeholder(item):
        return None
    from .weapons import _parse_weapon_item

    profile = _parse_weapon_item(item)
    if profile is None:
        return None
    base = BASE_WEAPON_PRICE_GP.get(weapon_shop_category(profile), 6)
    return 100 + 2 * base


def can_member_wield_weapon(member: PartyMemberState, item: str) -> tuple[bool, str]:
    from .equipment_shop import can_class_use_item
    from .weapons import _parse_weapon_item

    profile = _parse_weapon_item(item)
    if profile is None:
        return True, ""
    allowed, message = can_class_use_item(
        member.class_id,
        {"category": weapon_shop_category(profile), "magic": is_magic_weapon(item)},
    )
    return allowed, message
