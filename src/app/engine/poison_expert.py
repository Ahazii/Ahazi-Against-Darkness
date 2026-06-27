"""Poison Expert professional (Four Against the Abyss p.32)."""

from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_d8
from .madness import foe_immune_to_poison
from .weapon_finishes import (
    apply_weapon_finish,
    is_weapon_item_poisoned,
    member_wields_poisoned_weapon,
    strip_weapon_finishes,
)


def rogue_meets_poison_expert_requirement(member: PartyMemberState) -> bool:
    return member.class_id.lower() == "rogue" and (member.level or 1) >= 5


def apply_trained_poison_expert_coating(
    session: SessionState,
    provider: PartyMemberState,
    target: PartyMemberState,
    *,
    item_name: str | None,
) -> list[str]:
    from .courtship_professional_skills import member_has_trained_poison_expert

    if not member_has_trained_poison_expert(provider):
        return [f"{provider.name} is not trained as a poison expert (TCOTFD)."]
    if member_has_active_poison_source(target):
        return [f"{target.name} already has poison ready; only one dose at a time."]
    if not item_name or item_name not in target.inventory:
        return ["Choose a slashing weapon or one arrow from that hero's inventory."]
    lower = item_name.lower()
    if "arrow" in lower:
        coated = apply_weapon_finish(item_name, "poisoned")
        target.inventory = [coated if item == item_name else item for item in target.inventory]
        note = (
            f"{provider.name} coats {strip_weapon_finishes(item_name)} for {target.name} "
            "(+1 vs first minion, or boss level drop, TCOTFD)."
        )
    elif any(token in lower for token in ("sword", "scimitar", "dagger", "hand weapon", "light weapon", "slashing")):
        from .weapon_finishes import rename_inventory_weapon

        coated = apply_weapon_finish(item_name, "poisoned")
        melee, melee_secondary, missile = rename_inventory_weapon(
            target.inventory,
            item_name,
            coated,
            default_melee=target.default_melee_weapon,
            default_melee_secondary=target.default_melee_weapon_secondary,
            default_missile=target.default_missile_weapon,
        )
        target.default_melee_weapon = melee
        target.default_melee_weapon_secondary = melee_secondary
        target.default_missile_weapon = missile
        note = (
            f"{provider.name} envenoms {strip_weapon_finishes(item_name)} for {target.name} "
            "(+1 vs first minion, or boss level drop, TCOTFD)."
        )
    else:
        return ["Coat a slashing hand weapon or a single arrow."]
    return [note]


def member_has_pending_poison_expert(member: PartyMemberState, session: SessionState) -> bool:
    buffs = session.professional_buffs or {}
    return buffs.get("poison_expert_pending") and buffs.get("poison_expert_rogue_id") == member.character_id


def member_has_active_poison_source(member: PartyMemberState) -> bool:
    from .madness import envenomed_weapon_kind, poison_vial_items

    if envenomed_weapon_kind(member) is not None:
        return True
    if poison_vial_items(member):
        return True
    return any(is_weapon_item_poisoned(item) for item in member.inventory)


def apply_poison_expert_coating_inline(
    session: SessionState,
    member: PartyMemberState,
    *,
    item_name: str | None,
) -> list[str]:
    if not rogue_meets_poison_expert_requirement(member):
        return ["Poison Expert requires a rogue of Level 5 or higher."]
    if member_has_active_poison_source(member):
        return [f"{member.name} already has poison ready; only one dose at a time."]
    if not item_name or item_name not in member.inventory:
        return ["Choose a slashing weapon or one arrow from that rogue's inventory."]
    lower = item_name.lower()
    if "arrow" in lower:
        coated = apply_weapon_finish(item_name, "poisoned")
        member.inventory = [coated if item == item_name else item for item in member.inventory]
        note = f"Poison Expert coats {strip_weapon_finishes(item_name)} for {member.name} (+1 vs first minion, or boss level drop)."
    elif any(token in lower for token in ("sword", "scimitar", "dagger", "hand weapon", "light weapon", "slashing")):
        from .weapon_finishes import rename_inventory_weapon

        coated = apply_weapon_finish(item_name, "poisoned")
        melee, melee_secondary, missile = rename_inventory_weapon(
            member.inventory,
            item_name,
            coated,
            default_melee=member.default_melee_weapon,
            default_melee_secondary=member.default_melee_weapon_secondary,
            default_missile=member.default_missile_weapon,
        )
        member.default_melee_weapon = melee
        member.default_melee_weapon_secondary = melee_secondary
        member.default_missile_weapon = missile
        note = (
            f"Poison Expert envenoms {strip_weapon_finishes(item_name)} for {member.name} "
            "(+1 vs first minion, or boss level drop)."
        )
    else:
        return ["Coat a slashing hand weapon or a single arrow."]
    buffs = dict(session.professional_buffs or {})
    buffs.pop("poison_expert_pending", None)
    buffs.pop("poison_expert_rogue_id", None)
    session.professional_buffs = buffs
    return [note]


def apply_poison_expert_coating(
    session: SessionState,
    *,
    item_name: str | None,
    character_id: str | None = None,
) -> list[str]:
    buffs = session.professional_buffs or {}
    if not buffs.get("poison_expert_pending"):
        return ["No Poison Expert coating is pending."]
    rogue_id = buffs.get("poison_expert_rogue_id")
    member = next((hero for hero in session.party if hero.character_id == rogue_id), None)
    if member is None:
        member = next((hero for hero in session.party if hero.character_id == character_id), None)
    if member is None:
        return ["Choose the rogue who hired the Poison Expert."]
    return apply_poison_expert_coating_inline(session, member, item_name=item_name)


def clear_poisoned_weapon(member: PartyMemberState, weapon_item: str | None) -> None:
    if not weapon_item:
        return
    if weapon_item not in member.inventory:
        return
    base = strip_weapon_finishes(weapon_item)
    member.inventory = [base if item == weapon_item else item for item in member.inventory]
    if member.default_melee_weapon == weapon_item:
        member.default_melee_weapon = base
    if member.default_melee_weapon_secondary == weapon_item:
        member.default_melee_weapon_secondary = base
    if member.default_missile_weapon == weapon_item:
        member.default_missile_weapon = base


def recalc_enemy_stats_for_level(enemy: EnemyState, new_level: int) -> None:
    """Scale life and attacks when a foe's level drops mid-encounter."""
    if new_level >= enemy.level:
        return
    old_level = max(1, enemy.level)
    new_level = max(1, new_level)
    ratio = new_level / old_level
    enemy.level = new_level
    new_max_life = max(1, round(enemy.max_life * ratio))
    enemy.max_life = new_max_life
    enemy.life = max(1, min(enemy.life, new_max_life))
    if enemy.life > new_max_life:
        enemy.life = new_max_life
    if enemy.attacks > 1:
        enemy.attacks = max(1, round(enemy.attacks * ratio))


def apply_poison_expert_boss_effect(
    member: PartyMemberState,
    enemy: EnemyState,
    *,
    roll_fn=None,
) -> tuple[bool, list[str]]:
    if enemy.category != "boss":
        return False, []
    if foe_immune_to_poison(enemy):
        return False, [f"{enemy.name} is immune to poison."]
    if enemy.level <= 1:
        return False, [f"{enemy.name} is already at minimum level."]
    if "poison_expert_reduced" in {tag.lower() for tag in enemy.tags}:
        return False, [f"{enemy.name} is already weakened by expert poison."]
    roller = roll_d8 if roll_fn is None else roll_fn
    roll = roller()
    total = roll + member.level
    log = [
        f"Poison Expert vs boss: {member.name} rolls d8 + L = {roll} + {member.level} = {total} vs L{enemy.level}."
    ]
    if total < enemy.level:
        log.append("The poison fails to weaken the boss.")
        return False, log
    old_level = enemy.level
    recalc_enemy_stats_for_level(enemy, old_level - 1)
    enemy.tags.append("poison_expert_reduced")
    log.append(
        f"Poison weakens {enemy.name} to L{enemy.level} ({enemy.life}/{enemy.max_life} Life, "
        f"{enemy.attacks} attack(s)) for this encounter."
    )
    return True, log


def poison_expert_attack_effects(
    member: PartyMemberState,
    target: EnemyState,
    *,
    missile: bool,
    weapon,
    weapon_item: str | None,
) -> tuple[int, list[str]]:
    from .weapon_finishes import member_wields_poisoned_weapon

    if not member_wields_poisoned_weapon(member, weapon_item):
        return 0, []
    if foe_immune_to_poison(target):
        return 0, [f"{target.name} is immune to poison; the expert coating has no effect."]
    if target.category == "minions":
        if missile:
            if weapon is None or not getattr(weapon, "missile", False):
                return 0, []
        else:
            if weapon is not None and getattr(weapon, "crushing", False):
                return 0, [f"{member.name}'s crushing weapon cannot use poison."]
            if weapon is not None and not getattr(weapon, "slashing", False):
                return 0, []
        return 1, [f"{member.name}'s poisoned weapon adds +1 Attack vs {target.name}."]
    if target.category == "boss":
        _, boss_log = apply_poison_expert_boss_effect(member, target)
        return 0, boss_log
    return 0, [f"The poison has no effect on {target.name} ({target.category})."]
