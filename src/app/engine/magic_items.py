from __future__ import annotations

import re
from dataclasses import dataclass

from .spells import normalize_spell_name

CHARGE_SUFFIX = re.compile(r"\(\s*(\d+)\s*charges?\s*\)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ChargedMagicItem:
    item_name: str
    base_label: str
    spell_name: str
    charges: int


def charged_magic_item_use_error(item: str, class_id: str) -> str | None:
    parsed = parse_charged_magic_item(item)
    if parsed is None:
        return f"{item} cannot be used to cast spells."
    normalized_class = class_id.strip().lower()
    normalized_item = parsed.base_label.strip().lower()
    if normalized_item == "wand of sleep" and normalized_class not in {"wizard", "illusionist", "elf"}:
        return "Wand of Sleep may only be used by wizards, illusionists, and elves."
    if normalized_item == "fireball staff" and normalized_class != "wizard":
        return "Fireball Staff may only be used by wizards."
    return None


def _spell_from_base_label(base: str) -> str | None:
    text = base.strip()
    if not text:
        return None
    wand = re.match(r"^wand\s+of\s+(.+)$", text, re.IGNORECASE)
    if wand:
        return wand.group(1).strip()
    staff_of = re.match(r"^staff\s+of\s+(.+)$", text, re.IGNORECASE)
    if staff_of:
        return staff_of.group(1).strip()
    named_staff = re.match(r"^(.+?)\s+staff$", text, re.IGNORECASE)
    if named_staff:
        return named_staff.group(1).strip()
    return None


def parse_charged_magic_item(item: str) -> ChargedMagicItem | None:
    text = item.strip()
    match = CHARGE_SUFFIX.search(text)
    if not match:
        return None
    charges = int(match.group(1))
    if charges < 1:
        return None
    base = text[: match.start()].strip()
    spell = _spell_from_base_label(base)
    if not spell:
        return None
    return ChargedMagicItem(item_name=text, base_label=base, spell_name=spell, charges=charges)


def is_charged_magic_item(item: str) -> bool:
    return parse_charged_magic_item(item) is not None


def magic_item_matches_spell(item: str, spell_name: str) -> bool:
    parsed = parse_charged_magic_item(item)
    if not parsed:
        return False
    return normalize_spell_name(parsed.spell_name) == normalize_spell_name(spell_name)


def find_magic_item(inventory: list[str], spell_name: str) -> str | None:
    for item in inventory:
        if magic_item_matches_spell(item, spell_name):
            return item
    return None


def find_magic_item_by_name(inventory: list[str], item_name: str) -> str | None:
    if item_name in inventory and is_charged_magic_item(item_name):
        return item_name
    return None


def consume_magic_item_charge(item: str) -> str | None:
    parsed = parse_charged_magic_item(item)
    if not parsed:
        return None
    remaining = parsed.charges - 1
    if remaining <= 0:
        return None
    charge_word = "charge" if remaining == 1 else "charges"
    return f"{parsed.base_label} ({remaining} {charge_word})"
