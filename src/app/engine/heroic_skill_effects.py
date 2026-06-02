from __future__ import annotations

from typing import Literal

from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_exploding_for_level
from .expert_skill_effects import encounter_spent, expert_save_bonus, mark_encounter_spent
from .inventory import is_carried_shield

SkillTier = Literal["heroic", "legendary"]

HEROIC_SKILL_MECHANICS: dict[str, str] = {
    "aggressive_stance": "Declare before melee: +1 Attack this round; −1 Defense until next round.",
    "ballistic_training": "+1 ranged Attack with bows or slings.",
    "battle_training": "+1 melee Attack when fighting two or more foes.",
    "heroic_accuracy": "+1 Attack with chosen missile or melee weapon type.",
    "heroic_courage": "+1 vs fear/terror saves; ignore first failed fear save each adventure.",
    "heroic_dodge": "+1 Defense when targeted by a single foe.",
    "heros_rest": "When Resting, each ally may recover 1 additional Life (once per adventure).",
    "master_strike": "Once per encounter, a successful melee hit inflicts +1 wound.",
    "training_focus": "Bank +1 on the next advancement roll this adventure.",
    "wrath_of_the_berserker": "When raging, minion kills may trigger an extra attack at −1.",
}

LEGENDARY_SKILL_MECHANICS: dict[str, str] = {
    "legendary_ballistic_training": "Improves Ballistic Training: +2 ranged Attack total.",
    "legendary_accuracy": "Improves Heroic Accuracy: +2 Attack with chosen weapon type.",
    "legendary_courage": "Improves Heroic Courage: auto-succeed first fear save each adventure.",
    "legendary_dodge": "Improves Heroic Dodge: +2 Defense when targeted by one foe.",
    "legendary_wrath_of_the_berserker": "Improves Wrath: extra rage attack at no penalty once per encounter.",
}

WIRED_HEROIC = frozenset(
    {
        "battle_training",
        "ballistic_training",
        "heroic_courage",
        "heroic_dodge",
        "heros_rest",
        "master_strike",
    }
)
WIRED_LEGENDARY = frozenset({"legendary_ballistic_training", "legendary_courage", "legendary_dodge"})


def tier_skill_status(skill_id: str, tier: SkillTier) -> str:
    normalized = skill_id.strip().lower()
    if tier == "heroic":
        return "wired" if normalized in WIRED_HEROIC else "catalog"
    return "wired" if normalized in WIRED_LEGENDARY else "catalog"


def has_heroic_skill(member: PartyMemberState, skill_id: str) -> bool:
    needle = skill_id.strip().lower()
    for item in member.learned_heroic_skills:
        if item.strip().lower().split(":", 1)[0] == needle:
            return True
    return False


def has_legendary_skill(member: PartyMemberState, skill_id: str) -> bool:
    needle = skill_id.strip().lower()
    for item in member.learned_legendary_skills:
        if item.strip().lower().split(":", 1)[0] == needle:
            return True
    return False


def party_has_heros_rest(party: list[PartyMemberState]) -> bool:
    return any(has_heroic_skill(member, "heros_rest") for member in party if member.current_life > 0)


def heroic_courage_bonus(member: PartyMemberState) -> int:
    bonus = 0
    if has_heroic_skill(member, "heroic_courage"):
        bonus += 1
    if has_legendary_skill(member, "legendary_courage"):
        bonus += 1
    return bonus


def fear_save_bonus(member: PartyMemberState, party: list[PartyMemberState] | None = None) -> int:
    return expert_save_bonus(member, party, fear=True) + heroic_courage_bonus(member)


def legendary_courage_auto(session: SessionState, member: PartyMemberState) -> bool:
    if not has_legendary_skill(member, "legendary_courage"):
        return False
    if member.character_id in session.legendary_courage_used:
        return False
    session.legendary_courage_used.append(member.character_id)
    return True


def heroic_courage_ignore_failure(session: SessionState, member: PartyMemberState) -> bool:
    if not has_heroic_skill(member, "heroic_courage"):
        return False
    if member.character_id in session.heroic_courage_used:
        return False
    session.heroic_courage_used.append(member.character_id)
    return True


def resolve_fear_save(
    session: SessionState,
    member: PartyMemberState,
    level: int,
    *,
    party: list[PartyMemberState] | None = None,
    show_rolls: bool = True,
    label: str = "fear",
) -> tuple[bool, list[str]]:
    log: list[str] = []
    if member.class_id.lower() == "paladin":
        log.append(f"{member.name} is immune to {label}.")
        return True, log
    if legendary_courage_auto(session, member):
        log.append(f"{member.name} stands firm ({label}; Legendary Courage).")
        return True, log
    modifier = member.level if member.class_id.lower() == "cleric" else 0
    modifier += fear_save_bonus(member, party)
    total, rolls = roll_exploding_for_level(member.level)
    final_total = total + modifier
    if show_rolls:
        detail = f" {' + '.join(str(value) for value in rolls)}"
        if modifier:
            detail += f" + {modifier}"
        log.append(f"{member.name} {label} Save vs L{level}:{detail} = {final_total}.")
    if rolls[0] == 1 or final_total < level:
        if heroic_courage_ignore_failure(session, member):
            log.append(f"{member.name} steels their will (Heroic Courage).")
            return True, log
        return False, log
    log.append(f"{member.name} shrugs off the {label}.")
    return True, log


def heroic_attack_bonus(
    member: PartyMemberState,
    *,
    missile: bool,
    living_foe_count: int,
) -> int:
    bonus = 0
    if missile:
        if has_legendary_skill(member, "legendary_ballistic_training"):
            bonus += 2
        elif has_heroic_skill(member, "ballistic_training"):
            bonus += 1
    elif living_foe_count >= 2 and has_heroic_skill(member, "battle_training"):
        bonus += 1
    return bonus


def heroic_defense_bonus(member: PartyMemberState, *, single_attacker: bool) -> int:
    if not single_attacker:
        return 0
    if has_legendary_skill(member, "legendary_dodge"):
        return 2
    if has_heroic_skill(member, "heroic_dodge"):
        return 1
    return 0


def master_strike_extra_damage(
    member: PartyMemberState,
    session: SessionState | None,
    *,
    missile: bool,
) -> tuple[int, list[str]]:
    if missile or session is None or not has_heroic_skill(member, "master_strike"):
        return 0, []
    if encounter_spent(session, member.character_id, "master_strike"):
        return 0, []
    mark_encounter_spent(session, member.character_id, "master_strike")
    return 1, [f"{member.name} follows through with Master Strike (+1 wound)."]


def apply_heroes_rest_bonus(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    if session.heroes_rest_used or not party_has_heros_rest(party):
        return []
    session.heroes_rest_used = True
    log: list[str] = []
    for member in party:
        if member.current_life <= 0 or member.current_life >= member.max_life:
            continue
        member.current_life += 1
        log.append(f"Hero's Rest: {member.name} recovers 1 additional Life.")
    return log


def forfeit_carried_shield(member: PartyMemberState) -> str | None:
    for index, item in enumerate(member.inventory):
        if is_carried_shield(item):
            return member.inventory.pop(index)
    return None


def try_sacrifice_shield(
    context,
    target: PartyMemberState,
    log: list[str],
) -> bool:
    """Negate one hit when Sacrifice Shield is declared. Returns True if absorbed."""
    if target.character_id not in context.sacrifice_shield_users:
        return False
    if target.character_id in context.sacrifice_shield_used:
        return False
    from .expert_skill_effects import has_skill

    if not has_skill(target, "sacrifice_shield") or not is_carried_shield_in_inventory(target):
        return False
    context.sacrifice_shield_used.add(target.character_id)
    session = context.session
    if session is not None:
        if target.character_id not in session.sacrifice_shield_used:
            session.sacrifice_shield_used.append(target.character_id)
        shield = forfeit_carried_shield(target)
        if shield:
            session.forfeited_shields[target.character_id] = shield
    log.append(f"{target.name} uses Sacrifice Shield — the blow is absorbed (shield forfeited).")
    return True


def is_carried_shield_in_inventory(member: PartyMemberState) -> bool:
    return any(is_carried_shield(item) for item in member.inventory)


def restore_forfeited_shields(session: SessionState) -> list[str]:
    log: list[str] = []
    for character_id, shield in list(session.forfeited_shields.items()):
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is not None and shield and shield not in member.inventory:
            member.inventory.append(shield)
            log.append(f"{member.name} recovers their {shield}.")
    session.forfeited_shields.clear()
    return log
