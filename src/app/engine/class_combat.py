from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState


MARTIAL_ATTACK_CLASSES = {"warrior", "barbarian", "dwarf", "elf", "ranger"}
PARTIAL_ATTACK_CLASSES = {"cleric", "rogue"}
HIGH_DEFENSE_CLASSES = {"rogue"}


def attack_modifier(member: PartyMemberState, enemy: EnemyState | None = None) -> int:
    class_id = member.class_id.lower()
    if class_id in MARTIAL_ATTACK_CLASSES:
        return member.level
    if class_id == "cleric" and enemy and "undead" in enemy.tags:
        return member.level
    if class_id == "rogue" and enemy and enemy.life <= 1 and enemy.category in {"vermin", "minions"}:
        return member.level
    if class_id in PARTIAL_ATTACK_CLASSES:
        return member.level // 2
    return member.attack_bonus


def defense_modifier(member: PartyMemberState, enemy: EnemyState | None = None) -> int:
    class_id = member.class_id.lower()
    if class_id in HIGH_DEFENSE_CLASSES:
        return member.level
    if class_id == "halfling" and enemy and _is_giant_like(enemy):
        return member.level
    if class_id == "dwarf" and enemy and _is_giant_like(enemy):
        return 1
    return member.defense_bonus


def armor_defense_bonus(member: PartyMemberState, *, include_shield: bool = True) -> int:
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


def _is_giant_like(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    keywords = {"giant", "troll", "ogre", "brute", "boss"}
    return bool(tags.intersection(keywords)) or enemy.category == "boss"
