from __future__ import annotations

import re

from ..schemas import PartyMemberState
from .spells import normalize_spell_name

SKALITOS_SPELLS = (
    "Disperse Vermin",
    "Blessing",
    "Escape",
    "Lightning",
    "Fireball",
    "Sleep",
)

SCROLL_PATTERN = re.compile(
    r"^(?:(?:scroll|bark|prism)\s*(?:of|:)\s*)|^(?:druid\s+bark|illusionist\s+prism)\s*(?:of|:)\s*",
    re.IGNORECASE,
)

SKALITOS_PAGES_PATTERN = re.compile(r"\((\d+)\s+pages?\)", re.IGNORECASE)


def is_scroll_item(item: str) -> bool:
    lowered = item.strip().lower()
    if not lowered:
        return False
    if lowered.startswith("scroll"):
        return True
    if lowered.startswith("bark:") or lowered.startswith("bark of"):
        return True
    if lowered.startswith("prism:") or lowered.startswith("prism of"):
        return True
    if lowered.startswith("druid bark") or lowered.startswith("illusionist prism"):
        return True
    return False


def scroll_spell_name(item: str) -> str | None:
    text = item.strip()
    if not is_scroll_item(text):
        return None
    cleaned = SCROLL_PATTERN.sub("", text, count=1).strip()
    if not cleaned:
        return None
    return cleaned


def scroll_matches_spell(item: str, spell_name: str) -> bool:
    parsed = scroll_spell_name(item)
    if not parsed:
        return False
    return normalize_spell_name(parsed) == normalize_spell_name(spell_name)


def find_scroll_item(inventory: list[str], spell_name: str) -> str | None:
    for item in inventory:
        if scroll_matches_spell(item, spell_name):
            return item
    return None


def skalitos_pages(item: str) -> int | None:
    lower = item.strip().lower()
    if "book of skalitos" not in lower:
        return None
    match = SKALITOS_PAGES_PATTERN.search(item)
    if match:
        return max(0, int(match.group(1)))
    if "six wizard spell scrolls" in lower or "unused" in lower:
        return 6
    return 6


def is_skalitos_book(item: str) -> bool:
    pages = skalitos_pages(item)
    return pages is not None and pages > 0


def skalitos_spell_allowed(spell_name: str) -> bool:
    normalized = normalize_spell_name(spell_name)
    return any(normalize_spell_name(spell) == normalized for spell in SKALITOS_SPELLS)


def find_skalitos_book(inventory: list[str], spell_name: str) -> str | None:
    if not skalitos_spell_allowed(spell_name):
        return None
    for item in inventory:
        if is_skalitos_book(item):
            return item
    return None


def consume_skalitos_page(item: str) -> str | None:
    pages = skalitos_pages(item)
    if pages is None:
        return None
    remaining = pages - 1
    if remaining <= 0:
        return None
    page_word = "page" if remaining == 1 else "pages"
    return f"Book of Skalitos ({remaining} {page_word})"


def scroll_casting_modifier(member: PartyMemberState) -> int:
    class_id = member.class_id.lower()
    if class_id in {"wizard", "elf", "illusionist", "druid", "cleric"}:
        return member.level
    return 1


def barbarian_cannot_use_magic(class_id: str) -> bool:
    """Rulebook p.12: barbarians may not use magic items, scrolls, or potions."""
    return class_id.lower() == "barbarian"


def barbarian_cannot_use_scrolls(class_id: str) -> bool:
    return barbarian_cannot_use_magic(class_id)
