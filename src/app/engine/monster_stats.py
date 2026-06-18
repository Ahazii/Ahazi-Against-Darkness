from __future__ import annotations

import re

from .dice import roll_formula

_LIFE_FORMULA = re.compile(r"^HCL(?:\+(\d+))?$", re.IGNORECASE)
_TIER_LIFE_FORMULA = re.compile(r"^Tier\+(\d+)$", re.IGNORECASE)
_TIER_ATTACK_FORMULA = re.compile(r"^Tier\+(\d+)$", re.IGNORECASE)


def hcl_to_tier(hcl: int) -> int:
    return max(1, (hcl + 2) // 3)


def parse_monster_life(value: object, hcl: int) -> int:
    if isinstance(value, int):
        return max(1, value)
    text = str(value).strip()
    match = _LIFE_FORMULA.match(text)
    if match:
        return max(1, hcl + int(match.group(1) or 0))
    match = _TIER_LIFE_FORMULA.match(text)
    if match:
        return max(1, hcl_to_tier(hcl) + int(match.group(1)))
    try:
        return max(1, int(text))
    except ValueError:
        return max(1, hcl)


def parse_monster_attacks(value: object, hcl: int) -> int:
    if isinstance(value, int):
        return max(0, value)
    text = str(value).strip()
    match = _TIER_ATTACK_FORMULA.match(text)
    if match:
        return max(1, hcl_to_tier(hcl) + int(match.group(1)))
    try:
        return max(1, roll_formula(text))
    except ValueError:
        pass
    try:
        return max(1, int(text))
    except ValueError:
        return 1
