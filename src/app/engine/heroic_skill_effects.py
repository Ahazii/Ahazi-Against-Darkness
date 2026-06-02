from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_exploding_for_level
from .expert_skill_effects import encounter_spent, expert_save_bonus, mark_encounter_spent
from .inventory import is_carried_shield

if TYPE_CHECKING:
    from .weapons import WeaponProfile

SkillTier = Literal["heroic", "legendary"]

HEROIC_TARGET_SKILLS = frozenset({"heroic_accuracy"})

HEROIC_SKILL_MECHANICS: dict[str, str] = {
    "aggressive_stance": "Declare before melee: +1 Attack this round; −1 Defense until next round.",
    "ballistic_training": "+1 ranged Attack with bows or slings.",
    "battle_training": "+1 melee Attack when fighting two or more foes.",
    "carnage": "On minion kill, +1 Attack on your next attack this encounter.",
    "cleave": "On minion kill, one extra melee attack at −1 against another minion.",
    "deep_strike": "+1 Attack vs foes at half Life or below.",
    "deep_wound": "+1 damage vs major foes on a successful hit.",
    "defensive_stance": "Declare before melee: +1 Defense this round.",
    "eldritch_aim": "+1 to spellcasting attack rolls.",
    "heroic_accuracy": "+1 Attack with chosen missile or melee weapon type.",
    "heroic_courage": "+1 vs fear/terror saves; ignore first failed fear save each adventure.",
    "heroic_dodge": "+1 Defense when targeted by a single foe.",
    "heros_rest": "When Resting, each ally may recover 1 additional Life (once per adventure).",
    "knife_master": "+1 Attack with knives or daggers.",
    "master_strike": "Once per encounter, declare before rolling: successful melee hit inflicts +1 wound.",
    "spite": "+1 Attack when below half Life.",
    "stable_mind": "+1 vs madness and mind-affecting saves.",
    "training_focus": "Bank +1 on the next advancement roll this adventure.",
    "wrath_of_the_berserker": "When raging, minion kills may trigger an extra attack at −1.",
}

LEGENDARY_SKILL_MECHANICS: dict[str, str] = {
    "legendary_ballistic_training": "Improves Ballistic Training: +2 ranged Attack total.",
    "legendary_accuracy": "Improves Heroic Accuracy: +2 Attack with chosen weapon type.",
    "legendary_battle_training": "Improves Battle Training: +2 melee Attack when 2+ foes remain.",
    "legendary_carnage": "Improves Carnage: +2 Attack on next attack after a minion kill.",
    "legendary_cleave": "Improves Cleave: two extra minion attacks at −1 after a minion kill.",
    "legendary_courage": "Improves Heroic Courage: auto-succeed first fear save each adventure.",
    "legendary_deep_strike": "Improves Deep Strike: +2 Attack vs wounded foes.",
    "legendary_deep_wound": "Improves Deep Wound: +2 damage vs major foes.",
    "legendary_dodge": "Improves Heroic Dodge: +2 Defense when targeted by one foe.",
    "legendary_eldritch_aim": "Improves Eldritch Aim: +2 to spellcasting attack rolls.",
    "legendary_spite": "Improves Spite: +2 Attack when below half Life.",
    "legendary_stable_mind": "Improves Stable Mind: +2 vs madness and mind saves.",
    "legendary_training_focus": "Improves Training Focus: bank +2 on the next advancement roll.",
    "legendary_wrath_of_the_berserker": "Improves Wrath: once per encounter, extra rage attack at no penalty.",
}

WIRED_HEROIC = frozenset(
    {
        "aggressive_stance",
        "ballistic_training",
        "battle_training",
        "carnage",
        "cleave",
        "deep_strike",
        "deep_wound",
        "defensive_stance",
        "eldritch_aim",
        "heroic_accuracy",
        "heroic_courage",
        "heroic_dodge",
        "heros_rest",
        "knife_master",
        "master_strike",
        "spite",
        "stable_mind",
        "training_focus",
        "wrath_of_the_berserker",
    }
)
WIRED_LEGENDARY = frozenset(
    {
        "legendary_ballistic_training",
        "legendary_accuracy",
        "legendary_battle_training",
        "legendary_carnage",
        "legendary_cleave",
        "legendary_courage",
        "legendary_deep_strike",
        "legendary_deep_wound",
        "legendary_dodge",
        "legendary_eldritch_aim",
        "legendary_spite",
        "legendary_stable_mind",
        "legendary_training_focus",
        "legendary_wrath_of_the_berserker",
    }
)


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


def accuracy_weapon_target(member: PartyMemberState) -> str | None:
    target = (member.expert_skill_targets or {}).get("heroic_accuracy")
    return target.strip().lower() if target else None


def weapon_matches_accuracy(member: PartyMemberState, weapon: WeaponProfile | None, *, missile: bool) -> bool:
    target = accuracy_weapon_target(member)
    if not target:
        return False
    if weapon is None:
        name = (member.default_missile_weapon if missile else "").lower()
    else:
        name = weapon.item.lower()
    if target in {"melee", "missile", "ranged"}:
        if target == "melee":
            return weapon is not None and weapon.kind == "melee"
        return missile or (weapon is not None and weapon.kind == "missile")
    return target in name


def party_has_heros_rest(party: list[PartyMemberState]) -> bool:
    return any(has_heroic_skill(member, "heros_rest") for member in party if member.current_life > 0)


def heroic_courage_bonus(member: PartyMemberState) -> int:
    bonus = 0
    if has_heroic_skill(member, "heroic_courage"):
        bonus += 1
    if has_legendary_skill(member, "legendary_courage"):
        bonus += 1
    return bonus


def stable_mind_save_bonus(member: PartyMemberState) -> int:
    bonus = 0
    if has_heroic_skill(member, "stable_mind"):
        bonus += 1
    if has_legendary_skill(member, "legendary_stable_mind"):
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


def foe_is_wounded(enemy: EnemyState) -> bool:
    return enemy.life <= max(1, enemy.max_life // 2)


def foe_is_major(enemy: EnemyState) -> bool:
    return enemy.category in {"weird", "boss"}


def member_below_half_life(member: PartyMemberState) -> bool:
    return member.current_life <= max(1, member.max_life // 2)


def heroic_attack_bonus(
    member: PartyMemberState,
    *,
    missile: bool,
    living_foe_count: int,
    weapon: WeaponProfile | None = None,
    target: EnemyState | None = None,
    aggressive_stance: bool = False,
    carnage_bonus: int = 0,
) -> int:
    bonus = carnage_bonus
    if missile:
        if has_legendary_skill(member, "legendary_ballistic_training"):
            bonus += 2
        elif has_heroic_skill(member, "ballistic_training"):
            bonus += 1
    else:
        if living_foe_count >= 2:
            if has_legendary_skill(member, "legendary_battle_training"):
                bonus += 2
            elif has_heroic_skill(member, "battle_training"):
                bonus += 1
        if aggressive_stance and not missile:
            bonus += 1
    if weapon_matches_accuracy(member, weapon, missile=missile):
        if has_legendary_skill(member, "legendary_accuracy"):
            bonus += 2
        elif has_heroic_skill(member, "heroic_accuracy"):
            bonus += 1
    if weapon is not None and not missile:
        name = weapon.item.lower()
        if has_heroic_skill(member, "knife_master") and any(token in name for token in ("knife", "dagger")):
            bonus += 1
    if target is not None and foe_is_wounded(target):
        if has_legendary_skill(member, "legendary_deep_strike"):
            bonus += 2
        elif has_heroic_skill(member, "deep_strike"):
            bonus += 1
    if member_below_half_life(member):
        if has_legendary_skill(member, "legendary_spite"):
            bonus += 2
        elif has_heroic_skill(member, "spite"):
            bonus += 1
    return bonus


def heroic_defense_bonus(
    member: PartyMemberState,
    *,
    single_attacker: bool,
    defensive_stance: bool = False,
    aggressive_stance_penalty: bool = False,
) -> int:
    bonus = 0
    if single_attacker:
        if has_legendary_skill(member, "legendary_dodge"):
            bonus += 2
        elif has_heroic_skill(member, "heroic_dodge"):
            bonus += 1
    if defensive_stance:
        bonus += 1
    if aggressive_stance_penalty:
        bonus -= 1
    return bonus


def eldritch_aim_bonus(member: PartyMemberState) -> int:
    if has_legendary_skill(member, "legendary_eldritch_aim"):
        return 2
    if has_heroic_skill(member, "eldritch_aim"):
        return 1
    return 0


def deep_wound_extra_damage(member: PartyMemberState, target: EnemyState) -> tuple[int, list[str]]:
    if not foe_is_major(target):
        return 0, []
    if has_legendary_skill(member, "legendary_deep_wound"):
        return 2, [f"{member.name}'s Deep Wound adds 2 damage."]
    if has_heroic_skill(member, "deep_wound"):
        return 1, [f"{member.name}'s Deep Wound adds 1 damage."]
    return 0, []


def master_strike_extra_damage(
    member: PartyMemberState,
    session: SessionState | None,
    *,
    missile: bool,
    declared: bool,
) -> tuple[int, list[str]]:
    if missile or session is None or not declared or not has_heroic_skill(member, "master_strike"):
        return 0, []
    if encounter_spent(session, member.character_id, "master_strike"):
        return 0, []
    mark_encounter_spent(session, member.character_id, "master_strike")
    return 1, [f"{member.name} follows through with Master Strike (+1 wound)."]


def consume_carnage_bonus(session: SessionState, character_id: str) -> int:
    return int(session.heroic_carnage_bonus.pop(character_id, 0))


def grant_carnage_bonus(session: SessionState, member: PartyMemberState) -> list[str]:
    if has_legendary_skill(member, "legendary_carnage"):
        session.heroic_carnage_bonus[member.character_id] = 2
        return [f"{member.name} feeds on Carnage (+2 on next attack)."]
    if has_heroic_skill(member, "carnage"):
        session.heroic_carnage_bonus[member.character_id] = 1
        return [f"{member.name} feeds on Carnage (+1 on next attack)."]
    return []


def cleave_follow_up_count(member: PartyMemberState) -> int:
    if has_legendary_skill(member, "legendary_cleave"):
        return 2
    if has_heroic_skill(member, "cleave"):
        return 1
    return 0


def wrath_follow_up_penalty(session: SessionState, member: PartyMemberState, raging: bool) -> int | None:
    if not raging:
        return None
    if has_legendary_skill(member, "legendary_wrath_of_the_berserker"):
        if not encounter_spent(session, member.character_id, "legendary_wrath_of_the_berserker"):
            mark_encounter_spent(session, member.character_id, "legendary_wrath_of_the_berserker")
            return 0
    if has_heroic_skill(member, "wrath_of_the_berserker"):
        return -1
    return None


def training_focus_bonus_amount(member: PartyMemberState) -> int:
    if has_legendary_skill(member, "legendary_training_focus"):
        return 2
    if has_heroic_skill(member, "training_focus"):
        return 1
    return 0


def bank_training_focus(session: SessionState, member: PartyMemberState) -> list[str]:
    amount = training_focus_bonus_amount(member)
    if amount <= 0:
        return [f"{member.name} does not know Training Focus."]
    if member.character_id in session.training_focus_bonus:
        return [f"{member.name} already has Training Focus banked (+{session.training_focus_bonus[member.character_id]})."]
    session.training_focus_bonus[member.character_id] = amount
    label = "Legendary Training Focus" if amount > 1 else "Training Focus"
    return [f"{member.name} banks {label} (+{amount} on the next advancement roll)."]


def consume_training_focus_bonus(session: SessionState, character_id: str) -> int:
    return int(session.training_focus_bonus.pop(character_id, 0))


def rotate_aggressive_stance_penalty(session: SessionState, declared_attackers: set[str]) -> None:
    session.aggressive_stance_penalty = sorted(declared_attackers)


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
