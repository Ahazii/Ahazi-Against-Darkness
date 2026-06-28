"""Four Against the Abyss item effects."""

from __future__ import annotations

import re

from app.schemas import EnemyState, PartyMemberState

from .abyss_afflictions import cure_dark_plague, mark_dark_plague_immune


ABYSS_FIRE_BREATH_STATUS = "Abyss Fire Breathing"
ABYSS_ELVEN_BREAD_USED_STATUS = "Abyss Elven Bread used"


def _lower_items(member: PartyMemberState) -> list[str]:
    return [item.lower() for item in member.inventory]


def has_undead_protection_amulet(member: PartyMemberState) -> bool:
    return any("amulet of protection versus undead" in item for item in _lower_items(member))


def has_cross_against_vampires(member: PartyMemberState) -> bool:
    return any("cross against vampires" in item for item in _lower_items(member))


def has_brownie_ward(member: PartyMemberState) -> bool:
    return any("brownie ward" in item for item in _lower_items(member))


def abyss_defense_bonus(member: PartyMemberState, enemy: EnemyState | None) -> int:
    if enemy is None:
        return 0
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    bonus = 0
    if has_undead_protection_amulet(member) and ("undead" in tags or "undead" in name):
        bonus += 1
    if has_cross_against_vampires(member) and ("vampire" in tags or "vampire" in name):
        bonus += 2
    return bonus


def abyss_save_bonus(member: PartyMemberState, enemies: list[EnemyState] | None, save_label: str = "") -> int:
    label = save_label.lower()
    if not has_undead_protection_amulet(member):
        return 0
    if "undead" in label:
        return 1
    for enemy in enemies or []:
        tags = {tag.lower() for tag in enemy.tags}
        if "undead" in tags or "undead" in enemy.name.lower():
            return 1
    return 0


def abyss_magic_armor_bonus(member: PartyMemberState, *, include_shield: bool = True) -> int:
    body_bonus = 0
    shield_bonus = 0
    ring_bonus = 0
    for item in member.inventory:
        lower = item.lower()
        if "ring of defense" in lower:
            ring_bonus = max(ring_bonus, 1)
        elif include_shield and lower.strip() == "magic shield":
            shield_bonus = max(shield_bonus, 2)
        elif "elfin chain mail" in lower:
            body_bonus = max(body_bonus, 2)
        elif "suit of enchanted armor" in lower:
            body_bonus = max(body_bonus, 3)
    return body_bonus + shield_bonus + ring_bonus


def member_has_abyss_body_armor(member: PartyMemberState) -> bool:
    return any(
        "elfin chain mail" in item.lower() or "suit of enchanted armor" in item.lower()
        for item in member.inventory
    )


def member_has_abyss_magic_shield(member: PartyMemberState) -> bool:
    return any(item.lower().strip() == "magic shield" for item in member.inventory)


def abyss_weapon_attack_bonus(member: PartyMemberState | None, enemy: EnemyState | None, weapon_item: str | None) -> int:
    if member is None or not weapon_item or enemy is None:
        return 0
    lower = weapon_item.lower()
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    if "silver weapon" in lower and ("lycanthrope" in tags or "were" in tags or "were" in name):
        return 1
    return 0


def abyss_weapon_attack_note(member: PartyMemberState, enemy: EnemyState | None, weapon_item: str | None) -> str:
    if abyss_weapon_attack_bonus(member, enemy, weapon_item):
        return "Abyss silver weapon +1 vs lycanthrope"
    return ""


def baton_heal_on_kill(member: PartyMemberState, enemy: EnemyState, weapon_item: str | None) -> list[str]:
    if not weapon_item or "baton of righteousness" not in weapon_item.lower():
        return []
    if enemy.category not in {"boss", "weird"}:
        return []
    if member.current_life >= member.max_life:
        return [f"{member.name}'s Baton of Righteousness glows, but {member.name} is already at full Life."]
    member.current_life = min(member.max_life, member.current_life + 1)
    return [f"{member.name}'s Baton of Righteousness heals 1 Life ({member.current_life}/{member.max_life})."]


def consume_inventory_item(member: PartyMemberState, item_name: str) -> bool:
    if item_name in member.inventory:
        member.inventory.remove(item_name)
        return True
    return False


def _selected_item(member: PartyMemberState, item_name: str | None, predicate) -> str | None:
    if item_name and item_name in member.inventory and predicate(item_name):
        return item_name
    return next((item for item in member.inventory if predicate(item)), None)


def is_elven_bread(item: str) -> bool:
    return "elven bread" in item.lower()


def is_blessed_horseshoe(item: str) -> bool:
    return "blessed horseshoe" in item.lower()


def is_parchment_of_banishing(item: str) -> bool:
    return "parchment of banishing" in item.lower()


def is_medallion_of_snake_charming(item: str) -> bool:
    return "medallion of snake charming" in item.lower()


def is_philter_of_fire_breathing(item: str) -> bool:
    return "philter of fire breathing" in item.lower()


def is_ring_of_three_wishes(item: str) -> bool:
    return "ring of three wishes" in item.lower()


def ring_wish_count(item: str) -> int:
    match = re.search(r"\((\d+)\s*wishes?\)", item, flags=re.IGNORECASE)
    if match:
        return max(0, int(match.group(1)))
    return 1


def consume_ring_wish(member: PartyMemberState, item_name: str) -> str | None:
    wishes = ring_wish_count(item_name)
    if wishes <= 0 or item_name not in member.inventory:
        return None
    member.inventory.remove(item_name)
    if wishes > 1:
        updated = f"Ring of Three Wishes ({wishes - 1} {'wish' if wishes - 1 == 1 else 'wishes'})"
        member.inventory.append(updated)
        return updated
    return None


def use_elven_bread(member: PartyMemberState, item_name: str | None = None) -> list[str]:
    if ABYSS_ELVEN_BREAD_USED_STATUS in member.statuses:
        return [f"{member.name} has already benefited from Elven Bread this game."]
    bread = _selected_item(member, item_name, is_elven_bread)
    if bread is None:
        return [f"{member.name} has no Elven Bread."]
    consume_inventory_item(member, bread)
    member.statuses.append(ABYSS_ELVEN_BREAD_USED_STATUS)
    if any("dark plague" in status.lower() for status in member.statuses):
        cure_dark_plague(member)
        return [f"{member.name} eats {bread}; Dark Plague is removed and they are immune this adventure."]
    mark_dark_plague_immune(member)
    amount = 3 if member.class_id.lower() == "elf" else 1
    before = member.current_life
    member.current_life = min(member.max_life, member.current_life + amount)
    healed = member.current_life - before
    return [f"{member.name} eats {bread} and heals {healed} Life ({member.current_life}/{member.max_life})."]


def use_blessed_horseshoe(member: PartyMemberState, item_name: str | None = None) -> list[str]:
    horseshoe = _selected_item(member, item_name, is_blessed_horseshoe)
    if horseshoe is None:
        return [f"{member.name} has no Blessed Horseshoe."]
    consume_inventory_item(member, horseshoe)
    if "Blessed Horseshoe reroll" not in member.statuses:
        member.statuses.append("Blessed Horseshoe reroll")
    return [f"{member.name} invokes {horseshoe}; the next failed die roll may be treated as rerolled."]


def use_philter_of_fire_breathing(member: PartyMemberState, item_name: str | None = None) -> list[str]:
    philter = _selected_item(member, item_name, is_philter_of_fire_breathing)
    if philter is None:
        return [f"{member.name} has no Philter of Fire Breathing."]
    consume_inventory_item(member, philter)
    if ABYSS_FIRE_BREATH_STATUS not in member.statuses:
        member.statuses.append(ABYSS_FIRE_BREATH_STATUS)
    return [
        f"{member.name} drinks {philter}; this encounter grants dragon-fire immunity and one breath attack."
    ]


def consume_fire_breath_status(member: PartyMemberState) -> None:
    member.statuses = [status for status in member.statuses if status != ABYSS_FIRE_BREATH_STATUS]


def has_fire_breath_status(member: PartyMemberState) -> bool:
    return ABYSS_FIRE_BREATH_STATUS in member.statuses


def target_is_snake_or_lizardman_minion(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return enemy.category == "minions" and (
        "snake" in tags or "lizardman" in tags or "lizardmen" in tags or "snake" in name or "lizard" in name
    )


def target_is_undead_or_demon(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "undead" in tags or "demon" in tags or "undead" in name or "demon" in name or "vampire" in name
