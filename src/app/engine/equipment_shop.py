from __future__ import annotations

import re
from typing import Any

from app.schemas import Character

from .dice import roll_d6
from .weapons import _parse_weapon_item, prune_weapon_defaults

_CLASS_RULES: dict[str, dict[str, Any]] = {
    "warrior": {"light_armor": True, "heavy_armor": True, "shield": True, "light_weapon": True, "hand_weapon": True, "two_handed_weapon": True, "bow": True, "sling": True, "magic": True},
    "cleric": {"light_armor": True, "heavy_armor": True, "shield": True, "light_weapon": True, "hand_weapon": True, "two_handed_weapon": True, "bow": False, "sling": True, "magic": True},
    "rogue": {"light_armor": True, "heavy_armor": False, "shield": False, "light_weapon": True, "hand_weapon": False, "two_handed_weapon": False, "bow": False, "sling": False, "magic": True},
    "wizard": {"light_armor": False, "heavy_armor": False, "shield": False, "light_weapon": True, "hand_weapon": False, "two_handed_weapon": False, "bow": False, "sling": True, "magic": True},
    "barbarian": {"light_armor": True, "heavy_armor": False, "shield": True, "light_weapon": True, "hand_weapon": True, "two_handed_weapon": True, "bow": True, "sling": True, "magic": False, "holy_water": True},
    "ranger": {"light_armor": True, "heavy_armor": True, "shield": True, "light_weapon": True, "hand_weapon": True, "two_handed_weapon": True, "bow": True, "sling": True, "magic": True},
    "dwarf": {"light_armor": True, "heavy_armor": True, "shield": True, "light_weapon": True, "hand_weapon": True, "two_handed_weapon": True, "bow": True, "sling": True, "magic": True},
    "elf": {"light_armor": True, "heavy_armor": True, "shield": True, "light_weapon": True, "hand_weapon": True, "two_handed_weapon": False, "bow": True, "sling": False, "magic": True},
    "halfling": {"light_armor": True, "heavy_armor": False, "shield": False, "light_weapon": True, "hand_weapon": False, "two_handed_weapon": False, "bow": False, "sling": True, "magic": True},
    "druid": {"light_armor": False, "heavy_armor": False, "shield": False, "light_weapon": True, "hand_weapon": False, "two_handed_weapon": False, "bow": False, "sling": False, "magic": True},
    "illusionist": {"light_armor": False, "heavy_armor": False, "shield": False, "light_weapon": True, "hand_weapon": False, "two_handed_weapon": False, "bow": False, "sling": True, "magic": True},
}

_CATEGORY_TO_RULE_KEY = {
    "light_armor": "light_armor",
    "heavy_armor": "heavy_armor",
    "shield": "shield",
    "light_weapon": "light_weapon",
    "hand_weapon": "hand_weapon",
    "two_handed_weapon": "two_handed_weapon",
    "bow": "bow",
    "sling": "sling",
    "holy_water": "holy_water",
    "supply": None,
    "magic_scroll": "magic",
    "magic_potion": "magic",
}

_GEM_KEYWORDS = ("jewel", "gem", "jewelry", "jewellery")


def _class_rules(class_id: str) -> dict[str, Any]:
    return _CLASS_RULES.get(class_id.lower(), _CLASS_RULES["warrior"])


def _shop_items(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    return list(catalog.get("items", []))


def _item_by_key(catalog: dict[str, Any], key: str) -> dict[str, Any] | None:
    normalized = key.strip().lower()
    for item in _shop_items(catalog):
        if item.get("key", "").lower() == normalized:
            return item
    return None


def _sell_lookup(catalog: dict[str, Any], item_name: str) -> dict[str, Any] | None:
    trimmed = item_name.strip()
    lower = trimmed.lower()
    for entry in _shop_items(catalog):
        if entry.get("name", "").lower() == lower:
            return entry
        for alias in entry.get("sell_aliases", []):
            if alias.lower() == lower:
                return entry
    return None


def _resale_override(catalog: dict[str, Any], item_name: str) -> int | None:
    lower = item_name.lower()
    for row in catalog.get("resale_overrides", []):
        if row.get("match", "").lower() in lower:
            return int(row["resale_gp"])
    return None


def can_class_use_item(class_id: str, shop_item: dict[str, Any]) -> tuple[bool, str]:
    rules = _class_rules(class_id)
    category = shop_item.get("category", "")
    if category == "holy_water":
        if rules.get("holy_water") or rules.get("magic", True):
            return True, ""
        return False, f"{class_id.title()}s may not buy holy water in this build."
    if shop_item.get("magic"):
        if not rules.get("magic", True):
            return False, "Barbarians may not buy magic items, scrolls, or potions."
    rule_key = _CATEGORY_TO_RULE_KEY.get(category)
    if rule_key is None:
        return True, ""
    if not rules.get(rule_key, False):
        return False, f"{class_id.title()}s may not use this type of equipment."
    return True, ""


def list_shop_for_class(catalog: dict[str, Any], class_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _shop_items(catalog):
        allowed, _ = can_class_use_item(class_id, item)
        rows.append(
            {
                "key": item["key"],
                "name": item["name"],
                "price_gp": item["price_gp"],
                "sell_gp": item["price_gp"] // 2,
                "category": item.get("category"),
                "magic": bool(item.get("magic")),
                "allowed": allowed,
            }
        )
    return rows


def buy_equipment(
    character: Character,
    catalog: dict[str, Any],
    *,
    item_key: str,
) -> tuple[bool, str]:
    shop_item = _item_by_key(catalog, item_key)
    if shop_item is None:
        return False, "Unknown shop item."
    allowed, message = can_class_use_item(character.class_id, shop_item)
    if not allowed:
        return False, message
    price = int(shop_item["price_gp"])
    if character.gold < price:
        return False, f"{character.name} needs {price}gp (has {character.gold}gp)."
    item_name = shop_item["name"]
    character.gold -= price
    character.inventory.append(item_name)
    prune_weapon_defaults(character)
    return True, f"{character.name} buys {item_name} for {price}gp."


def _spell_count_in_item(item_name: str) -> int:
    lower = item_name.lower()
    charge_match = re.search(r"(\d+)\s*charge", lower)
    if charge_match:
        return max(1, int(charge_match.group(1)))
    if "scroll" in lower and ("six" in lower or "6 " in lower):
        return 6
    if any(word in lower for word in ("wand", "scroll", "staff", "stave")):
        return 1
    return 0


def _is_gem_or_jewelry(item_name: str) -> bool:
    lower = item_name.lower()
    return any(keyword in lower for keyword in _GEM_KEYWORDS)


def _is_magic_loot(item_name: str) -> bool:
    lower = item_name.lower()
    magic_markers = (
        "magic",
        "enchanted",
        "wand",
        "scroll",
        "staff",
        "stave",
        "ring",
        "potion",
        "symbol of healing",
        "arrow of slaying",
        "book of",
    )
    return any(marker in lower for marker in magic_markers)


def _payout_for_loot(
    character: Character,
    catalog: dict[str, Any],
    item_name: str,
) -> tuple[int, str]:
    override = _resale_override(catalog, item_name)
    if override is not None:
        payout = override
        note = "listed magic resale"
        if _is_gem_or_jewelry(item_name) and character.class_id.lower() == "dwarf":
            payout = int(payout * 1.2)
            note = "listed resale (+20% dwarf gem bonus)"
        return payout, note

    shop_match = _sell_lookup(catalog, item_name)
    if shop_match is not None:
        payout = int(shop_match["price_gp"]) // 2
        note = "half list price"
        if shop_match.get("magic"):
            lower = item_name.lower()
            if "potion" in lower or "ring" in lower:
                payout = 50
                note = "potion/ring magic resale"
            elif any(word in lower for word in ("wand", "scroll", "staff", "stave")):
                payout = max(100, _spell_count_in_item(item_name) * 100)
                note = "100gp per spell/charge"
        return payout, note

    lower = item_name.lower()
    if "potion" in lower or ("ring" in lower and "warning" not in lower):
        return 50, "potion/ring magic resale"
    if any(word in lower for word in ("wand", "scroll", "staff", "stave")):
        return max(100, _spell_count_in_item(item_name) * 100), "100gp per spell/charge"

    if _is_gem_or_jewelry(item_name) or _is_magic_loot(item_name):
        payout = roll_d6() * roll_d6()
        note = "d6×d6 magic/gem resale"
        if character.class_id.lower() == "dwarf" and _is_gem_or_jewelry(item_name):
            payout = int(payout * 1.2)
            note = "d6×d6 gem resale (+20% dwarf)"
        return payout, note

    if _parse_weapon_item(item_name) is not None:
        inferred = _sell_lookup(catalog, item_name)
        return (int(inferred["price_gp"]) // 2 if inferred else 3), "standard gear resale"

    return roll_d6() * roll_d6(), "d6×d6 miscellaneous loot"


def sell_item(
    character: Character,
    catalog: dict[str, Any],
    *,
    item_name: str,
) -> tuple[bool, str, int]:
    trimmed = item_name.strip()
    if not trimmed:
        return False, "Choose an item to sell.", 0
    try:
        index = character.inventory.index(trimmed)
    except ValueError:
        return False, f"{character.name} does not carry {trimmed}.", 0

    payout, note = _payout_for_loot(character, catalog, trimmed)
    character.inventory.pop(index)
    character.gold += payout
    prune_weapon_defaults(character)
    return True, f"{character.name} sells {trimmed} for {payout}gp ({note}).", payout


def sell_quote(
    character: Character,
    catalog: dict[str, Any],
    *,
    item_name: str,
) -> dict[str, Any]:
    trimmed = item_name.strip()
    if not trimmed:
        return {"item_name": "", "quote_gp": None, "kind": "none", "note": ""}
    if trimmed not in character.inventory:
        return {"item_name": trimmed, "quote_gp": None, "kind": "none", "note": "Not in inventory."}

    override = _resale_override(catalog, trimmed)
    if override is not None:
        payout = override
        if _is_gem_or_jewelry(trimmed) and character.class_id.lower() == "dwarf":
            payout = int(payout * 1.2)
        return {"item_name": trimmed, "quote_gp": payout, "kind": "fixed", "note": "Known magic resale value."}

    shop_match = _sell_lookup(catalog, trimmed)
    if shop_match is not None:
        payout = int(shop_match["price_gp"]) // 2
        if shop_match.get("magic"):
            lower = trimmed.lower()
            if "potion" in lower or "ring" in lower:
                payout = 50
            elif any(word in lower for word in ("wand", "scroll", "staff", "stave")):
                payout = max(100, _spell_count_in_item(trimmed) * 100)
        return {"item_name": trimmed, "quote_gp": payout, "kind": "equipment", "note": "Half list price."}

    lower = trimmed.lower()
    if "potion" in lower or ("ring" in lower and "warning" not in lower):
        return {"item_name": trimmed, "quote_gp": 50, "kind": "magic", "note": "Potion or ring (p.19)."}
    if any(word in lower for word in ("wand", "scroll", "staff", "stave")):
        spells = max(1, _spell_count_in_item(trimmed))
        return {"item_name": trimmed, "quote_gp": spells * 100, "kind": "magic", "note": "100gp per spell/charge (p.19)."}
    if _is_gem_or_jewelry(trimmed):
        note = "Gem/jewelry: d6×d6 gp"
        if character.class_id.lower() == "dwarf":
            note += " (+20% for dwarves)"
        return {"item_name": trimmed, "quote_gp": None, "kind": "roll", "note": note}
    if _is_magic_loot(trimmed):
        return {"item_name": trimmed, "quote_gp": None, "kind": "roll", "note": "Other magic: d6×d6 gp (p.19)."}
    if _parse_weapon_item(trimmed) is not None:
        inferred = _sell_lookup(catalog, trimmed)
        payout = int(inferred["price_gp"]) // 2 if inferred else 3
        return {"item_name": trimmed, "quote_gp": payout, "kind": "equipment", "note": "Standard gear resale."}
    return {"item_name": trimmed, "quote_gp": None, "kind": "roll", "note": "Miscellaneous loot: d6×d6 gp."}
