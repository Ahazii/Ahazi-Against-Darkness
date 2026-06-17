from __future__ import annotations

import re
from collections.abc import Callable

from ..schemas import PartyMemberState
from .dice import roll_d6

MAGIC_ARMOR_BONUS_RE = re.compile(r"\+\s*(\d+)\s*defense", re.IGNORECASE)

FIENDISH_MAGIC_ARMOR_TYPES: dict[int, str] = {
    1: "Magic Shield (+{bonus} Defense)",
    2: "Magic Shield (+{bonus} Defense)",
    3: "Magic Light Armor (+{bonus} Defense)",
    4: "Magic Heavy Armor (+{bonus} Defense)",
    5: "Magic Heavy Armor (+{bonus} Defense)",
    6: "Ring of Protection (+{bonus} Defense)",
}


def is_magic_armor_placeholder(item: str) -> bool:
    lower = item.lower()
    return "magic armor" in lower and ("+1" in lower or "+2" in lower or "+1 or +2" in lower)


def is_magic_armor(item: str) -> bool:
    if is_magic_armor_placeholder(item):
        return True
    lower = item.lower()
    return ("magic " in lower or "ring of protection" in lower) and (
        "+1 defense" in lower or "+2 defense" in lower
    )


def magic_armor_defense_value(item: str) -> int:
    match = MAGIC_ARMOR_BONUS_RE.search(item)
    if match:
        return int(match.group(1))
    if "+2 defense" in item.lower():
        return 2
    return 1


def roll_fiendish_magic_armor_name(
    *,
    bonus: int,
    type_roll: int | None = None,
    roll_fn: Callable[[], int] | None = None,
) -> tuple[str, int]:
    roller = roll_fn or roll_d6
    value = type_roll if type_roll is not None else roller()
    value = max(1, min(6, value))
    template = FIENDISH_MAGIC_ARMOR_TYPES[value]
    return template.format(bonus=bonus), value


def resolve_magic_armor_placeholder(
    item: str,
    *,
    roll_fn: Callable[[], int] | None = None,
) -> tuple[str, int | None]:
    if not is_magic_armor_placeholder(item):
        return item, None
    roller = roll_fn or roll_d6
    bonus_roll = roller()
    bonus = 2 if bonus_roll >= 5 else 1
    type_roll = roller()
    name, rolled = roll_fiendish_magic_armor_name(bonus=bonus, type_roll=type_roll, roll_fn=roll_fn)
    return name, rolled


def _item_is_magic_body_armor(lower: str) -> bool:
    return any(token in lower for token in ("magic light armor", "magic heavy armor"))


def _item_is_magic_shield(lower: str) -> bool:
    return "magic shield" in lower


def _item_is_ring_of_protection(lower: str) -> bool:
    return "ring of protection" in lower


def magic_armor_defense_bonus(member: PartyMemberState, *, include_shield: bool = True) -> int:
    body_bonus = 0
    shield_bonus = 0
    ring_bonus = 0
    for item in member.inventory:
        lower = item.lower()
        if not is_magic_armor(item):
            continue
        value = magic_armor_defense_value(item)
        if _item_is_magic_body_armor(lower):
            body_bonus = max(body_bonus, value)
        elif include_shield and _item_is_magic_shield(lower):
            shield_bonus = max(shield_bonus, value)
        elif _item_is_ring_of_protection(lower):
            ring_bonus = max(ring_bonus, value)
    return body_bonus + shield_bonus + ring_bonus


def mundane_armor_defense_bonus(member: PartyMemberState, *, include_shield: bool = True) -> int:
    from .weapon_finishes import leafsteel_defense_bonus

    inventory = " ".join(item.lower() for item in member.inventory)
    has_magic_body = any(_item_is_magic_body_armor(item.lower()) for item in member.inventory if is_magic_armor(item))
    has_magic_shield = any(_item_is_magic_shield(item.lower()) for item in member.inventory if is_magic_armor(item))
    bonus = leafsteel_defense_bonus(member)
    if not has_magic_body and bonus == 0:
        if "heavy armor" in inventory:
            bonus += 2
        elif "light armor" in inventory:
            bonus += 1
    if include_shield and not has_magic_shield and "shield" in inventory:
        bonus += 1
    return bonus
