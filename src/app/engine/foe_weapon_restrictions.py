from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .equipment_effects import is_vampire
from .magic_weapons import is_magic_weapon
from .weapons import WeaponProfile
from .weapon_finishes import member_wields_silvered_weapon

WEAPON_ALLOW_PREFIX = "weapon_allow:"


def template_weapon_allow_tags(template: dict) -> list[str]:
    tags: list[str] = []
    for rule in template.get("special_rules", []):
        if str(rule.get("type", "")).lower() != "weapon_restriction":
            continue
        for allowed in rule.get("allowed", []):
            token = str(allowed).strip().lower()
            if token:
                tags.append(f"{WEAPON_ALLOW_PREFIX}{token}")
    return tags


def foe_weapon_allows(enemy: EnemyState) -> set[str]:
    allowed: set[str] = set()
    for tag in enemy.tags:
        lower = tag.lower()
        if lower.startswith(WEAPON_ALLOW_PREFIX):
            allowed.add(lower.removeprefix(WEAPON_ALLOW_PREFIX))
    return allowed


def weapon_hit_blocked_by_restriction(
    member: PartyMemberState,
    enemy: EnemyState,
    weapon: WeaponProfile | None,
    *,
    pending_damage: int,
) -> tuple[bool, str]:
    allowed = foe_weapon_allows(enemy)
    if not allowed:
        return False, ""
    if is_vampire(enemy):
        from .expert_skill_effects import has_skill

        if has_skill(member, "vampire_hunter"):
            return False, ""
    if "magic_weapons" in allowed and weapon is not None and is_magic_weapon(weapon.item):
        return False, ""
    if "silvered_weapons" in allowed and member_wields_silvered_weapon(member, weapon.item if weapon else None):
        return False, ""
    if "two_plus_damage_single_blow" in allowed and pending_damage >= 2:
        return False, ""
    weapon_name = weapon.item if weapon is not None else "unarmed strike"
    return (
        True,
        f"{enemy.name} is harmed only by magic or silvered weapons, spells, holy water, "
        f"or blows inflicting 2+ damage — {member.name}'s {weapon_name} has no effect.",
    )
