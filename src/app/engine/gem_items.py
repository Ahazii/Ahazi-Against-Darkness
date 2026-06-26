"""Gem/jewelry inventory items — value is encoded in the item name as ``(Ngp)``."""

from __future__ import annotations

import re

from ..schemas import PartyMemberState

def materialize_treasure_gem_items(items: list[str], log: list[str] | None = None) -> list[str]:
    """Materialize procedural gem/jewelry placeholders into ``Gem (Ngp)`` inventory items."""
    from .dice import roll_formula

    out: list[str] = []
    for item in items:
        match = _GEM_ITEM_FORMULA_RE.match(item.strip())
        if match:
            dice_part = match.group(2)
            multiplier = int(match.group(3))
            value = roll_formula(dice_part) * multiplier
            gem = format_gem_item(value)
            if log is not None:
                log.append(f"Treasure gem roll ({dice_part}×{multiplier}) = {value}gp → {gem}.")
            out.append(gem)
        elif item.strip().lower() in {"magic treasure", "jewelry", "gem"}:
            continue
        else:
            out.append(item)
    return out


_GEM_ITEM_FORMULA_RE = re.compile(
    r"^(Gem|Jewelry|Small\s+gemstone)\s*\((\d+d\d+(?:\+\d+)?)\s*[x×]\s*(\d+)\s*gp\)$",
    re.IGNORECASE,
)
_GEM_VALUE_RE = re.compile(r"(\d+)\s*gp", re.IGNORECASE)
_GEM_KEYWORDS = ("gem", "jewel", "jewelry", "jewellery", "ruby", "sapphire", "emerald", "diamond", "pearl")

# Treasure formulas that can produce gem/jewelry items worth 200+ gp (max shown).
GEM_SOURCES_200GP_PLUS = [
    {"source": "EE treasure (dungeon roll 6+)", "formula": "2d6×20 jewelry", "min_gp": 40, "max_gp": 240},
    {"source": "Rare ingredient (TCOTFD)", "formula": "5d6×10", "min_gp": 50, "max_gp": 300, "note": "ingredient, not a pocket gem"},
    {"source": "Apothecary rare tier (TCOTFD)", "formula": "200 gp per rare element", "min_gp": 200, "max_gp": None},
]

FURNACE_AMULET_MIN_GEM_GP = 200


def is_gem_or_jewelry_item(item: str) -> bool:
    lower = item.lower()
    return any(keyword in lower for keyword in _GEM_KEYWORDS)


def gem_item_value_gp(item: str) -> int:
    """Parse resale value from item name, e.g. ``Gem (250gp)`` → 250. Generic ``Gem`` → 0."""
    if not is_gem_or_jewelry_item(item):
        return 0
    match = _GEM_VALUE_RE.search(item)
    if match:
        return int(match.group(1))
    return 0


def format_gem_item(value_gp: int, *, kind: str = "Gem") -> str:
    return f"{kind} ({int(value_gp)}gp)"


def format_jewelry_item(value_gp: int) -> str:
    return format_gem_item(value_gp, kind="Jewelry")


def party_gem_items(
    party: list[PartyMemberState],
    *,
    min_value_gp: int = 0,
) -> list[tuple[PartyMemberState, int, str]]:
    """Return (member, inventory_index, item_name) for gems/jewelry meeting min value."""
    found: list[tuple[PartyMemberState, int, str]] = []
    for member in party:
        for index, item in enumerate(member.inventory):
            value = gem_item_value_gp(item)
            if value >= min_value_gp:
                found.append((member, index, item))
    return found


def remove_inventory_item(member: PartyMemberState, item_name: str) -> bool:
    for index, item in enumerate(member.inventory):
        if item == item_name:
            member.inventory.pop(index)
            return True
    return False
