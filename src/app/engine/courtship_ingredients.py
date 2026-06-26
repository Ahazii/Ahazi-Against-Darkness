"""Demesne ingredient inventory helpers (TCOTFD Apothecary appendix)."""

from __future__ import annotations

from ..schemas import PartyMemberState

# TCOTFD p.77–78 — rare ingredients (not foraged; worth 5d6×10 gp each).
RARE_INGREDIENT_NAMES: tuple[str, ...] = (
    "Blasphemous One's heart",
    "Blooded roses",
    "Bloodmaw's tongue",
    "Blue regal hairs",
    "Bodak's heart",
    "Chaos dragon's cloaca",
    "Chaos ghoul queen's bladder",
    "Chest monster's glands",
    "Clockward Keeper's quintessence",
    "Colleen's ambergris",
    "Cracked heart of Lament",
    "Broken heart of Lament",
    "Death orchid petals",
    "Demonic Zombie Unicorn's horn",
    "Drottning's hippocampus",
    "Enraptured heart",
    "Flayed fay skin",
    "Ghoul fangs",
    "Giant's toes",
    "Grave shifter's knuckles",
    "Infected sharkmen's bladder",
    "Lictor's brain",
    "Lolly",
    "Luck dragon's nerves",
    "Luminescent heptahedron's jelly",
    "Man-tiger of Thraa's guts",
    "Milk of tenderness",
    "Mind screamer's pharynx",
    "Mirage drake's appendix",
    "Pandalatra's feather",
    "Psionic brain cannon's hypothalamus",
    "Purple dragon's stomach",
    "Salamandrine oracle's sternum",
    "Sea princess' eggs",
    "Seamen's brew",
    "Shokoti's tongue",
    "Skull of Darran Dur",
    "Tears of solace",
    "Tentacled brain's stem",
    "Time feeder's pineal gland",
    "Void monster's nodules",
    "Void Walker's claws",
    "Werewolf fangs",
    "Xichtul's jawbones",
)


def is_demesne_ingredient_item(item: str) -> bool:
    lower = item.lower()
    if "ingredient" in lower:
        return True
    return any(name.lower() in lower for name in RARE_INGREDIENT_NAMES)


def is_rare_ingredient_item(item: str) -> bool:
    lower = item.lower()
    if lower.startswith("rare ingredient"):
        return True
    return any(name.lower() in lower for name in RARE_INGREDIENT_NAMES)


def format_common_ingredient(label: str = "Common ingredient") -> str:
    return label


def format_uncommon_ingredient(label: str = "Uncommon ingredient") -> str:
    return label


def format_rare_ingredient(name: str | None = None, *, value_gp: int | None = None) -> str:
    if name:
        base = name if name in RARE_INGREDIENT_NAMES else f"Rare ingredient ({name})"
    else:
        base = "Rare ingredient"
    if value_gp is not None:
        return f"{base} ({int(value_gp)}gp)"
    return base


def party_ingredient_items(
    party: list[PartyMemberState],
    *,
    rare_only: bool = False,
) -> list[tuple[PartyMemberState, int, str]]:
    predicate = is_rare_ingredient_item if rare_only else is_demesne_ingredient_item
    found: list[tuple[PartyMemberState, int, str]] = []
    for member in party:
        for index, item in enumerate(member.inventory):
            if predicate(item):
                found.append((member, index, item))
    return found


def remove_inventory_at(member: PartyMemberState, index: int) -> str | None:
    if 0 <= index < len(member.inventory):
        return member.inventory.pop(index)
    return None


def consume_party_ingredients(
    party: list[PartyMemberState],
    count: int,
    *,
    rare_only: bool = False,
) -> list[str]:
    """Remove up to ``count`` ingredients from party inventories; return removed names."""
    removed: list[str] = []
    while len(removed) < count:
        candidates = party_ingredient_items(party, rare_only=rare_only)
        if not candidates:
            break
        member, index, item = candidates[0]
        if remove_inventory_at(member, index) is not None:
            removed.append(item)
    return removed


def spoil_random_ingredients(
    party: list[PartyMemberState],
    count: int,
) -> list[str]:
    """Remove ``count`` random Demesne ingredients from the party."""
    import random

    candidates = party_ingredient_items(party, rare_only=False)
    if not candidates:
        return []
    random.shuffle(candidates)
    spoiled: list[str] = []
    # Pop highest indices first per member to keep indices stable.
    by_member: dict[str, list[tuple[int, str]]] = {}
    for member, index, item in candidates[:count]:
        by_member.setdefault(member.character_id, []).append((index, item))
    for member in party:
        entries = sorted(by_member.get(member.character_id, []), key=lambda row: row[0], reverse=True)
        for index, item in entries:
            if remove_inventory_at(member, index) is not None:
                spoiled.append(item)
    return spoiled
