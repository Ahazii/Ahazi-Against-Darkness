from __future__ import annotations

from collections.abc import Callable

from .dice import roll_formula
from .dungeon_table_roller import EnvironmentKind

ADVENTURER_BODY_GEAR: dict[str, str] = {
    "heavy_armor": "Heavy armor",
    "lantern": "Lantern",
    "two_handed_weapon": "Two-handed weapon",
    "bow": "Bow",
    "crossbow": "Crossbow",
    "blessing_scroll": "Scroll of Blessing",
    "chicken_blood": "Jar of chicken blood",
}


def adventurer_body_gear_item(pick: str) -> str | None:
    return ADVENTURER_BODY_GEAR.get(pick)


def resolve_adventurer_body_loot(
    variant: str,
    pick: str,
    *,
    environment: EnvironmentKind = "dungeon",
    roll_random_spell_loot: Callable[[EnvironmentKind], tuple[str, list[str]]] | None = None,
) -> tuple[list[str], int, list[str], str]:
    log: list[str] = []
    items: list[str] = []
    gold = 0
    gem_items: list[str] = []
    gear = adventurer_body_gear_item(pick)
    if pick == "random_scroll":
        if roll_random_spell_loot is None:
            return [], 0, ["Random scroll roll unavailable."], ""
        gear, spell_log = roll_random_spell_loot(environment)
        log.extend(spell_log)
    elif not gear:
        return [], 0, [f"Unknown Adventurer's Dead Body gear choice: {pick}."], ""

    if variant == "fungal":
        rations = roll_formula("2d6")
        gold = roll_formula("2d6")
        items.extend(["Rope", f"Food rations ({rations})"])
        log.append(f"Adventurer's backpack: Rope, {rations} Food rations, {gold}gp.")
    elif variant == "caverns":
        gems = roll_formula("d6")
        gold = gems * 10
        from .gem_items import format_gem_item

        gem_items = [format_gem_item(10) for _ in range(gems)]
        log.append(f"Adventurer's pouch: {gems} gem(s) worth {gold}gp total.")
    else:
        return [], 0, [f"Unknown Adventurer's Dead Body variant: {variant}."], ""

    items.append(gear)
    if variant == "caverns":
        items = gem_items + items
    summary = f"Found Adventurer's Dead Body loot: {gear}."
    return items, gold, log, summary
