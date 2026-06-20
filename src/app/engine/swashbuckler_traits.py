from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_exploding_for_level
from .experience import tier_for_level
from .class_abilities import effective_foe_level, spend_panache_point
from .class_combat import defense_modifier
from .weapons import swashbuckler_dual_pair


def swashbuckler_trait(member: PartyMemberState) -> str | None:
    if member.class_id.lower() != "swashbuckler":
        return None
    traits = member.class_traits or []
    return traits[0] if traits else None


def has_swashbuckler_trait(member: PartyMemberState, trait_name: str) -> bool:
    return swashbuckler_trait(member) == trait_name


def member_wears_lucky_hat(member: PartyMemberState) -> bool:
    for item in member.inventory:
        lowered = item.lower()
        if "plumed" in lowered or "tricorn" in lowered:
            return True
    return False


def _trait_used(session: SessionState, field: str, character_id: str) -> bool:
    used = getattr(session, field, None) or []
    return character_id in used


def _mark_trait_used(session: SessionState, field: str, character_id: str) -> None:
    used = list(getattr(session, field, None) or [])
    if character_id not in used:
        used.append(character_id)
    setattr(session, field, used)


def mark_flourishing_used(session: SessionState, member: PartyMemberState) -> None:
    _mark_trait_used(session, "swashbuckler_flourishing_used", member.character_id)


def mark_riposte_used(session: SessionState, member: PartyMemberState) -> None:
    _mark_trait_used(session, "swashbuckler_riposte_used", member.character_id)


def flourishing_available(session: SessionState, member: PartyMemberState) -> bool:
    return has_swashbuckler_trait(member, "Flourishing Strike") and not _trait_used(
        session, "swashbuckler_flourishing_used", member.character_id
    )


def riposte_available(session: SessionState, member: PartyMemberState) -> bool:
    return has_swashbuckler_trait(member, "Riposte") and not _trait_used(
        session, "swashbuckler_riposte_used", member.character_id
    )


def taunt_available(session: SessionState, member: PartyMemberState) -> bool:
    return has_swashbuckler_trait(member, "Taunt") and not _trait_used(
        session, "swashbuckler_taunt_used", member.character_id
    )


def lucky_hat_available(session: SessionState, member: PartyMemberState) -> bool:
    return (
        has_swashbuckler_trait(member, "Lucky Hat")
        and member_wears_lucky_hat(member)
        and not _trait_used(session, "swashbuckler_lucky_hat_used", member.character_id)
    )


def blade_dance_available(session: SessionState, member: PartyMemberState) -> bool:
    return has_swashbuckler_trait(member, "Blade Dance") and not _trait_used(
        session, "swashbuckler_blade_dance_used", member.character_id
    )


def daring_escape_available(session: SessionState, member: PartyMemberState) -> bool:
    return has_swashbuckler_trait(member, "Daring Escape") and not _trait_used(
        session, "swashbuckler_daring_escape_used", member.character_id
    )


def taunt_eligible_foe(enemy: EnemyState) -> bool:
    name = enemy.name.lower()
    tags = {tag.lower() for tag in enemy.tags}
    if "vampire" in name or "vampire" in tags:
        return True
    if enemy.category == "weird":
        return False
    if "undead" in tags or "unliving" in tags:
        return False
    return True


def apply_swashbuckler_taunt(
    session: SessionState,
    swashbuckler: PartyMemberState,
    enemy: EnemyState,
) -> list[str]:
    if swashbuckler.class_id.lower() != "swashbuckler":
        return ["Only a swashbuckler may Taunt."]
    if not has_swashbuckler_trait(swashbuckler, "Taunt"):
        return [f"{swashbuckler.name} does not have the Taunt trait."]
    if not taunt_available(session, swashbuckler):
        return [f"{swashbuckler.name} has already Taunted this combat."]
    if not taunt_eligible_foe(enemy):
        return [f"Taunt does not affect {enemy.name}."]
    tier = tier_for_level(swashbuckler.level)
    pending = dict(session.foe_taunt_pending or {})
    pending[enemy.id] = tier
    session.foe_taunt_pending = pending
    _mark_trait_used(session, "swashbuckler_taunt_used", swashbuckler.character_id)
    effective = max(1, enemy.level - tier)
    return [
        f"{swashbuckler.name} mocks {enemy.name}; on its next turn it fights at effective L{effective} "
        f"(−{tier} from Taunt)."
    ]


def activate_blade_dance(
    session: SessionState,
    swashbuckler: PartyMemberState,
    *,
    panache_points: int,
) -> list[str]:
    if swashbuckler.class_id.lower() != "swashbuckler":
        return ["Only a swashbuckler may Blade Dance."]
    if not has_swashbuckler_trait(swashbuckler, "Blade Dance"):
        return [f"{swashbuckler.name} does not have the Blade Dance trait."]
    if not blade_dance_available(session, swashbuckler):
        return [f"{swashbuckler.name} has already Blade Danced this adventure."]
    if panache_points < 1:
        return ["Spend at least 1 Panache point for Blade Dance."]
    from .class_abilities import panache_points as current_panache

    available = current_panache(session, swashbuckler)
    if panache_points > available:
        return [f"{swashbuckler.name} has only {available} Panache point(s)."]
    for _ in range(panache_points):
        if not spend_panache_point(session, swashbuckler):
            return [f"{swashbuckler.name} could not spend Panache."]
    bonuses = dict(session.swashbuckler_blade_dance_bonus or {})
    bonuses[swashbuckler.character_id] = panache_points
    session.swashbuckler_blade_dance_bonus = bonuses
    session.swashbuckler_blade_dance_attack_spent = [
        cid for cid in (session.swashbuckler_blade_dance_attack_spent or []) if cid != swashbuckler.character_id
    ]
    _mark_trait_used(session, "swashbuckler_blade_dance_used", swashbuckler.character_id)
    return [
        f"{swashbuckler.name} Blade Dances, spending {panache_points} Panache "
        f"(+{panache_points} on the next Attack and Defense rolls)."
    ]


def blade_dance_attack_bonus(session: SessionState, member: PartyMemberState) -> int:
    bonus = int((session.swashbuckler_blade_dance_bonus or {}).get(member.character_id, 0))
    if bonus <= 0:
        return 0
    if member.character_id in (session.swashbuckler_blade_dance_attack_spent or []):
        return 0
    return bonus


def consume_blade_dance_attack_bonus(session: SessionState, member: PartyMemberState) -> int:
    bonus = blade_dance_attack_bonus(session, member)
    if bonus <= 0:
        return 0
    spent = list(session.swashbuckler_blade_dance_attack_spent or [])
    if member.character_id not in spent:
        spent.append(member.character_id)
    session.swashbuckler_blade_dance_attack_spent = spent
    return bonus


def blade_dance_defense_bonus(session: SessionState, member: PartyMemberState) -> int:
    bonus = int((session.swashbuckler_blade_dance_bonus or {}).get(member.character_id, 0))
    if bonus <= 0:
        return 0
    if member.character_id not in (session.swashbuckler_blade_dance_attack_spent or []):
        return 0
    return bonus


def consume_blade_dance_defense_bonus(session: SessionState, member: PartyMemberState) -> int:
    bonus = blade_dance_defense_bonus(session, member)
    if bonus <= 0:
        return 0
    remaining = dict(session.swashbuckler_blade_dance_bonus or {})
    remaining.pop(member.character_id, None)
    session.swashbuckler_blade_dance_bonus = remaining
    session.swashbuckler_blade_dance_attack_spent = [
        cid for cid in (session.swashbuckler_blade_dance_attack_spent or []) if cid != member.character_id
    ]
    return bonus


def clear_blade_dance_on_combat_end(session: SessionState) -> list[str]:
    logs: list[str] = []
    for character_id, bonus in list((session.swashbuckler_blade_dance_bonus or {}).items()):
        if character_id in (session.swashbuckler_blade_dance_attack_spent or []):
            member = next((item for item in session.party if item.character_id == character_id), None)
            name = member.name if member else "Swashbuckler"
            logs.append(
                f"{name}'s Blade Dance Defense bonus (+{bonus}) is lost — combat ended before the Defense roll."
            )
    if session.swashbuckler_blade_dance_bonus:
        session.swashbuckler_blade_dance_bonus = {}
    session.swashbuckler_blade_dance_attack_spent = []
    return logs


def daring_escape_attack_bonus(session: SessionState, attacker: PartyMemberState, foe: EnemyState) -> int:
    pending = (session.swashbuckler_daring_escape_bonus or {}).get(attacker.character_id)
    if not pending:
        return 0
    if str(pending.get("foe_id")) != foe.id:
        return 0
    return int(pending.get("bonus", 0))


def consume_daring_escape_attack_bonus(session: SessionState, attacker: PartyMemberState) -> None:
    pending = dict(session.swashbuckler_daring_escape_bonus or {})
    pending.pop(attacker.character_id, None)
    session.swashbuckler_daring_escape_bonus = pending


def apply_daring_escape(
    session: SessionState,
    swashbuckler: PartyMemberState,
    *,
    ally: PartyMemberState,
    foe: EnemyState,
) -> list[str]:
    if not daring_escape_available(session, swashbuckler):
        return [f"{swashbuckler.name} has already used Daring Escape this adventure."]
    _mark_trait_used(session, "swashbuckler_daring_escape_used", swashbuckler.character_id)
    session.skip_parting_flee = True
    bonuses = dict(session.swashbuckler_daring_escape_bonus or {})
    bonuses[ally.character_id] = {"foe_id": foe.id, "bonus": 1}
    session.swashbuckler_daring_escape_bonus = bonuses
    return [
        f"{swashbuckler.name} makes a daring escape; {ally.name} gains +1 on the next attack vs {foe.name}."
    ]


def destroy_lucky_hat(member: PartyMemberState) -> str | None:
    for index, item in enumerate(member.inventory):
        lowered = item.lower()
        if "plumed" in lowered or "tricorn" in lowered:
            member.inventory.pop(index)
            return item
    return None


def apply_lucky_hat_blocked_damage(session: SessionState, log: list[str] | None = None) -> None:
    blocked = session.pending_defense_reroll_blocked_damage
    if not blocked:
        return
    member = next(
        (item for item in session.party if item.character_id == blocked.get("character_id")),
        None,
    )
    if member is None or member.current_life <= 0:
        session.pending_defense_reroll_blocked_damage = None
        return
    enemy_name = str(blocked.get("enemy_name", "the foe"))
    member.current_life = max(0, member.current_life - 1)
    message = f"{member.name} takes 1 damage from {enemy_name}."
    session.pending_defense_reroll_blocked_damage = None
    if log is not None:
        log.append(message)
    else:
        session.log.append(message)


def lucky_hat_reroll_defense(
    session: SessionState,
    swashbuckler: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> tuple[bool, list[str]]:
    pending = session.pending_defense_reroll
    if not pending or pending.get("character_id") != swashbuckler.character_id:
        return False, ["No failed Defense roll is pending for Lucky Hat."]
    if not lucky_hat_available(session, swashbuckler):
        return False, [f"{swashbuckler.name} cannot use Lucky Hat."]
    level = int(pending["level"])
    enemy_id = str(pending.get("enemy_id", ""))
    total, rolls = roll_exploding_for_level(swashbuckler)
    modifier = defense_modifier(swashbuckler) + 1
    final_total = total + modifier
    _mark_trait_used(session, "swashbuckler_lucky_hat_used", swashbuckler.character_id)
    session.pending_defense_reroll = None
    log = [
        f"{swashbuckler.name} tips their hat — Lucky Hat reroll: "
        f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{level}."
    ]
    if rolls[0] == 1:
        removed = destroy_lucky_hat(swashbuckler)
        if removed:
            log.append(f"Natural 1 — {removed} is ruined!")
        else:
            log.append("Natural 1 — the lucky hat is ruined!")
    from .combat import defense_succeeds

    succeeded = defense_succeeds(final_total, level, natural=rolls[0])
    if succeeded:
        log.append("The rerolled Defense succeeds!")
        session.pending_defense_reroll_blocked_damage = None
    else:
        log.append("The rerolled Defense still fails.")
        apply_lucky_hat_blocked_damage(session, log)
    return succeeded, log


def effective_foe_level_with_taunt(
    enemy: EnemyState,
    penalties: dict[str, int],
    taunt_penalties: dict[str, int] | None = None,
) -> int:
    penalty = penalties.get(enemy.id, 0) + int((taunt_penalties or {}).get(enemy.id, 0))
    return max(1, enemy.level - penalty)


def reset_swashbuckler_combat_flags(session: SessionState) -> None:
    session.swashbuckler_flourishing_used = []
    session.swashbuckler_riposte_used = []
    session.swashbuckler_taunt_used = []
    session.foe_taunt_pending = {}
    session.foe_taunt_active = {}
    session.pending_defense_reroll = None
    session.pending_defense_reroll_blocked_damage = None


def off_hand_weapon(member: PartyMemberState) -> str | None:
    pair = swashbuckler_dual_pair(member)
    if not pair:
        return None
    return pair[1]
