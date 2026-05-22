from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState


def in_bear_form(member: PartyMemberState) -> bool:
    return any(status.strip().lower() == "bear form" for status in member.statuses)


MARTIAL_ATTACK_CLASSES = {"warrior", "barbarian", "dwarf", "elf", "ranger", "paladin", "assassin", "kukla"}
PARTIAL_ATTACK_CLASSES = {"cleric", "rogue", "acrobat", "bulwark", "druid", "illusionist", "swashbuckler", "gnome", "mushroom_monk", "light_gladiator"}
HIGH_DEFENSE_CLASSES = {"rogue", "acrobat"}


def attack_modifier(
    member: PartyMemberState,
    enemy: EnemyState | None = None,
    *,
    half_level: bool = False,
) -> int:
    if in_bear_form(member):
        return member.level
    class_id = member.class_id.lower()
    if class_id == "light_gladiator":
        bonus = member.level // 2
    elif class_id == "ranger":
        bonus = member.level // 2 if half_level else member.level
    elif class_id in MARTIAL_ATTACK_CLASSES:
        bonus = member.level
    elif class_id == "cleric" and enemy and "undead" in enemy.tags:
        bonus = member.level
    elif class_id == "rogue" and enemy and enemy.life <= 1 and enemy.category in {"vermin", "minions"}:
        bonus = member.level
    elif class_id in PARTIAL_ATTACK_CLASSES:
        bonus = member.level // 2
    else:
        bonus = member.attack_bonus

    if enemy and class_id == "dwarf" and _foe_matches(enemy, {"goblin", "kobold"}):
        bonus += 1
    if enemy and class_id == "elf" and _foe_matches(enemy, {"orc"}):
        bonus += 1
    return bonus


def light_gladiator_weapon_bonus(member: PartyMemberState, weapon_light: bool) -> int:
    if member.class_id.lower() != "light_gladiator":
        return attack_modifier(member)
    if weapon_light:
        return member.level // 2
    return 0


def defense_modifier(member: PartyMemberState, enemy: EnemyState | None = None) -> int:
    class_id = member.class_id.lower()
    if class_id == "light_gladiator":
        return member.level // 2
    if class_id in HIGH_DEFENSE_CLASSES:
        return member.level
    if class_id == "halfling" and enemy and _is_giant_like(enemy):
        return member.level
    if class_id == "dwarf" and enemy and _is_giant_like(enemy):
        return 1
    return member.defense_bonus


def armor_defense_bonus(member: PartyMemberState, *, include_shield: bool = True) -> int:
    if in_bear_form(member):
        return 0
    inventory = " ".join(item.lower() for item in member.inventory)
    bonus = 0
    if "heavy armor" in inventory:
        bonus += 2
    elif "light armor" in inventory:
        bonus += 1
    if include_shield and "shield" in inventory:
        bonus += 1
    return bonus


def save_modifier(member: PartyMemberState, *, trap: bool = False, poison: bool = False) -> int:
    class_id = member.class_id.lower()
    if trap and class_id == "rogue":
        return member.level
    if poison and class_id in {"barbarian", "halfling"}:
        return member.level
    if class_id in {"barbarian", "halfling"} and trap:
        return member.level
    return member.save_bonus


def is_hated_by_foes(member: PartyMemberState, enemies: list[EnemyState]) -> bool:
    class_id = member.class_id.lower()
    if class_id == "dwarf" and any(_foe_matches(enemy, {"goblin", "kobold", "troll"}) for enemy in enemies):
        return True
    if class_id == "elf" and any(_foe_matches(enemy, {"orc"}) for enemy in enemies):
        return True
    if class_id == "cleric" and any("undead" in enemy.tags for enemy in enemies):
        return True
    return False


def _foe_matches(enemy: EnemyState, keywords: set[str]) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return bool(keywords.intersection(tags)) or any(keyword in name for keyword in keywords)


def _is_giant_like(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    keywords = {"giant", "troll", "ogre", "brute", "boss"}
    return bool(tags.intersection(keywords)) or enemy.category == "boss"
