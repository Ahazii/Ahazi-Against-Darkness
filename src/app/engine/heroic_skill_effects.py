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
    "ambition": "+1 reaction adjustment on Fight / Fight to the Death outcomes.",
    "ballistic_training": "+1 ranged Attack with bows or slings.",
    "battle_training": "+1 melee Attack when fighting two or more foes.",
    "beast_leadership": "+1 reaction vs beast-tagged foes.",
    "boatman": "+½ Level on water-trap saves.",
    "carnage": "On minion kill, +1 Attack on your next attack this encounter.",
    "catfall": "Reduce fall-trap damage by Level.",
    "cleave": "On minion kill, one extra melee attack at −1 against another minion.",
    "copy_grimoire": "Once per adventure on Rest, copy one scroll spell into a wizard's spellbook.",
    "charge_breaker": "+1 Defense when exactly one foe attacks you in melee.",
    "deadly_stab": "+1 damage on dagger or knife hits.",
    "deep_strike": "+1 Attack vs foes at half Life or below.",
    "deep_wound": "+1 damage vs major foes on a successful hit.",
    "defensive_stance": "Declare before melee: +1 Defense this round.",
    "double_shot": "Once per encounter, two missile attacks (same or different targets).",
    "druidic_training": "+1 search in caverns or fungal grottoes.",
    "eldritch_aim": "+1 to spellcasting attack rolls.",
    "eldritch_force": "+1 spell damage on a successful connect.",
    "explosive_magic": "+1 damage on the first Fireball or Lightning each encounter.",
    "heroic_accuracy": "+1 Attack with chosen missile or melee weapon type.",
    "heroic_climber": "+1 secret-door search rolls.",
    "heroic_courage": "+1 vs fear/terror saves; ignore first failed fear save each adventure.",
    "heroic_dodge": "+1 Defense when targeted by a single foe.",
    "heroic_shield_bash": "After an exploding Defense, free shield bash at −1 (once per encounter).",
    "heroic_swimmer": "+Level on water-trap saves.",
    "heros_banquet": "Once per adventure on Rest, each wounded ally recovers 1 Life.",
    "heros_rest": "When Resting, each ally may recover 1 additional Life (once per adventure).",
    "knife_master": "+1 Attack with knives or daggers.",
    "mass_blessing": "Once per adventure, all allies +1 Attack for one combat round.",
    "master_strike": "Once per encounter, declare before rolling: successful melee hit inflicts +1 wound.",
    "preserve_corpse": "Fallen-ally resurrection rolls gain +1.",
    "prodigious_memory": "+1 search on previously visited tiles.",
    "protected_by_divine_forces": "+1 Defense vs undead and demons.",
    "protected_by_fate": "Once per adventure, survive a killing blow at 1 Life.",
    "restore": "Once per encounter, cleric heals an ally 1 Life (forfeit attacks).",
    "restore_mental_capacity": "Once per adventure, cure 1 Madness on an ally.",
    "song_of_elidra": "Once per adventure, +1 reaction for one check; heard on the same or adjacent map element.",
    "spite": "+1 Attack when below half Life.",
    "stable_mind": "+1 vs madness and mind-affecting saves.",
    "support_casting": "+1 ally-target spell connect rolls.",
    "training_focus": "Bank +1 on the next advancement roll this adventure.",
    "ward_of_protection": "Once per encounter, ward an ally +1 Defense.",
    "wrath_of_the_berserker": "When raging, minion kills may trigger an extra attack at −1.",
    "yogic_preservation": "Once per adventure, survive a killing blow at 1 Life.",
}

LEGENDARY_SKILL_MECHANICS: dict[str, str] = {
    "legendary_ballistic_training": "Improves Ballistic Training: +2 ranged Attack total.",
    "legendary_accuracy": "Improves Heroic Accuracy: +2 Attack with chosen weapon type.",
    "legendary_battle_training": "Improves Battle Training: +2 melee Attack when 2+ foes remain.",
    "legendary_beast_leadership": "Improves Beast Leadership: +2 reaction vs beasts.",
    "legendary_carnage": "Improves Carnage: +2 Attack on next attack after a minion kill.",
    "legendary_cleave": "Improves Cleave: two extra minion attacks at −1 after a minion kill.",
    "legendary_climber": "Improves Heroic Climber: +2 secret-door search.",
    "legendary_courage": "Improves Heroic Courage: auto-succeed first fear save each adventure.",
    "legendary_deep_strike": "Improves Deep Strike: +2 Attack vs wounded foes.",
    "legendary_deep_wound": "Improves Deep Wound: +2 damage vs major foes.",
    "legendary_dodge": "Improves Heroic Dodge: +2 Defense when targeted by one foe.",
    "legendary_eldritch_aim": "Improves Eldritch Aim: +2 to spellcasting attack rolls.",
    "legendary_memory": "Improves Prodigious Memory: +1 search on every tile.",
    "legendary_song_of_elidra": "Improves Song of Elidra: +2 reaction in the same/adjacent range.",
    "legendary_spite": "Improves Spite: +2 Attack when below half Life.",
    "legendary_stable_mind": "Improves Stable Mind: +2 vs madness and mind saves.",
    "legendary_swimmer": "Improves Heroic Swimmer: +2×Level on water-trap saves.",
    "legendary_training_focus": "Improves Training Focus: bank +2 on the next advancement roll.",
    "legendary_ward_of_protection": "Improves Ward of Protection: warded ally +2 Defense.",
    "legendary_wrath_of_the_berserker": "Improves Wrath: once per encounter, extra rage attack at no penalty.",
}

WIRED_HEROIC = frozenset(HEROIC_SKILL_MECHANICS)
WIRED_LEGENDARY = frozenset(LEGENDARY_SKILL_MECHANICS)


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
    madness_source: str | None = None,
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
    from .secrets import secret_save_bonus

    modifier += secret_save_bonus(member, session, save_label=label)
    total, rolls = roll_exploding_for_level(member)
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
        from .madness import apply_madness_gain

        source = madness_source or f"a failed {label} save"
        log.extend(
            apply_madness_gain(
                session,
                member,
                source=source,
                show_rolls=show_rolls,
            )
        )
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
    melee_attacks_on_target: int = 1,
    enemy: EnemyState | None = None,
    session: SessionState | None = None,
) -> int:
    bonus = 0
    if single_attacker:
        if has_legendary_skill(member, "legendary_dodge"):
            bonus += 2
        elif has_heroic_skill(member, "heroic_dodge"):
            bonus += 1
    if melee_attacks_on_target == 1 and has_heroic_skill(member, "charge_breaker"):
        bonus += 1
    if enemy is not None and has_heroic_skill(member, "protected_by_divine_forces"):
        from .expert_skill_effects import _is_demon, _is_undead

        if _is_undead(enemy) or _is_demon(enemy):
            bonus += 1
    if session is not None:
        bonus += ward_defense_bonus(session, member)
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


FALL_TRAP_KEYS = frozenset({"falling_stone", "trapdoor", "rockslide", "stalactite", "hidden_pit"})
WATER_TRAP_KEYWORDS = frozenset({"water", "flood", "drown", "drowning"})


def is_fall_trap(trap_key: str, label: str = "") -> bool:
    key = trap_key.strip().lower()
    if key in FALL_TRAP_KEYS:
        return True
    combined = f"{key} {label}".lower()
    return "fall" in combined or "pit" in combined or "rockslide" in combined or "stalactite" in combined


def is_water_trap(trap_key: str, label: str = "") -> bool:
    combined = f"{trap_key} {label}".lower()
    return any(token in combined for token in WATER_TRAP_KEYWORDS)


def deadly_stab_extra_damage(
    member: PartyMemberState,
    weapon: "WeaponProfile | None",
    *,
    missile: bool,
) -> tuple[int, list[str]]:
    if missile or not has_heroic_skill(member, "deadly_stab"):
        return 0, []
    name = (weapon.item if weapon else "").lower()
    if not any(token in name for token in ("knife", "dagger")):
        return 0, []
    return 1, [f"{member.name}'s Deadly Stab adds 1 damage."]


def eldritch_force_extra_damage(member: PartyMemberState) -> int:
    return 1 if has_heroic_skill(member, "eldritch_force") else 0


def explosive_magic_extra_damage(session: SessionState, member: PartyMemberState, spell_key: str) -> tuple[int, list[str]]:
    if not has_heroic_skill(member, "explosive_magic"):
        return 0, []
    normalized = spell_key.strip().lower().replace(" ", "_")
    if normalized not in {"fireball", "fire_ball", "lightning", "lightning_strike"}:
        return 0, []
    flag = f"explosive_magic_{normalized}"
    if encounter_spent(session, member.character_id, flag):
        return 0, []
    mark_encounter_spent(session, member.character_id, flag)
    return 1, [f"{member.name}'s Explosive Magic adds 1 damage."]


def support_casting_bonus(caster: PartyMemberState, target: PartyMemberState | None) -> int:
    if target is None or target.character_id == caster.character_id:
        return 0
    if has_heroic_skill(caster, "support_casting"):
        return 1
    return 0


def ward_defense_bonus(session: SessionState, member: PartyMemberState) -> int:
    warder_id = session.ward_of_protection_targets.get(member.character_id)
    if not warder_id:
        return 0
    warder = next((item for item in session.party if item.character_id == warder_id), None)
    if warder is None or warder.current_life <= 0:
        return 0
    if has_legendary_skill(warder, "legendary_ward_of_protection"):
        return 2
    if has_heroic_skill(warder, "ward_of_protection"):
        return 1
    return 0


def mass_blessing_attack_bonus(session: SessionState, combat_round: int) -> int:
    if session.mass_blessing_active_round != combat_round:
        return 0
    return 1


def apply_mass_blessing(session: SessionState, member: PartyMemberState, combat_round: int) -> list[str]:
    if not has_heroic_skill(member, "mass_blessing"):
        return [f"{member.name} does not know Mass Blessing."]
    if session.mass_blessing_used:
        return ["Mass Blessing was already used this adventure."]
    session.mass_blessing_used = True
    session.mass_blessing_active_round = combat_round
    return [f"{member.name} invokes Mass Blessing — all allies gain +1 Attack this round."]


def apply_restore_healing(
    session: SessionState,
    cleric: PartyMemberState,
    ally: PartyMemberState,
) -> list[str]:
    if not has_heroic_skill(cleric, "restore"):
        return [f"{cleric.name} does not know Restore."]
    if cleric.class_id.lower() != "cleric":
        return ["Restore requires a cleric."]
    if encounter_spent(session, cleric.character_id, "restore"):
        return [f"{cleric.name} already used Restore this encounter."]
    if ally.current_life <= 0:
        return [f"{ally.name} cannot be restored while fallen."]
    if ally.current_life >= ally.max_life:
        return [f"{ally.name} is already at full Life."]
    mark_encounter_spent(session, cleric.character_id, "restore")
    ally.current_life += 1
    return [
        f"{cleric.name} forfeits attacks to Restore {ally.name} "
        f"(+1 Life; now {ally.current_life}/{ally.max_life})."
    ]


def try_survive_killing_blow(
    session: SessionState,
    member: PartyMemberState,
    log: list[str],
) -> bool:
    """If a hero would fall to 0 Life, some skills leave them at 1 Life once per adventure."""
    if member.current_life > 0:
        return False
    if has_heroic_skill(member, "protected_by_fate") and member.character_id not in session.protected_by_fate_used:
        session.protected_by_fate_used.append(member.character_id)
        member.current_life = 1
        log.append(f"{member.name} is Protected by Fate — survives at 1 Life.")
        return True
    if has_heroic_skill(member, "yogic_preservation") and member.character_id not in session.yogic_preservation_used:
        session.yogic_preservation_used.append(member.character_id)
        member.current_life = 1
        log.append(f"{member.name} endures through Yogic Preservation — survives at 1 Life.")
        return True
    return False


def party_has_heros_banquet(party: list[PartyMemberState]) -> bool:
    return any(has_heroic_skill(member, "heros_banquet") for member in party if member.current_life > 0)


def apply_heros_banquet_bonus(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    if session.heros_banquet_used or not party_has_heros_banquet(party):
        return []
    session.heros_banquet_used = True
    log: list[str] = ["Hero's Banquet: wounded allies recover 1 Life."]
    for member in party:
        if member.current_life <= 0 or member.current_life >= member.max_life:
            continue
        member.current_life += 1
        log.append(f"{member.name} gains 1 Life ({member.current_life}/{member.max_life}).")
    return log


def apply_copy_grimoire_on_rest(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    from .spells import normalize_spell_name

    log: list[str] = []
    for member in party:
        if member.current_life <= 0 or not has_heroic_skill(member, "copy_grimoire"):
            continue
        if member.class_id.lower() != "wizard":
            continue
        if member.character_id in session.copy_grimoire_used:
            continue
        scroll_spell: str | None = None
        scroll_item: str | None = None
        for item in member.inventory:
            lower = item.lower()
            if not lower.startswith("scroll of "):
                continue
            spell = item.split("of ", 1)[1].strip()
            if not spell:
                continue
            if any(normalize_spell_name(existing) == normalize_spell_name(spell) for existing in member.spells):
                continue
            scroll_spell = spell
            scroll_item = item
            break
        if scroll_spell is None or scroll_item is None:
            continue
        session.copy_grimoire_used.append(member.character_id)
        member.spells.append(scroll_spell)
        member.inventory = [item for item in member.inventory if item != scroll_item]
        log.append(f"Copy Grimoire: {member.name} transcribes {scroll_spell} into the spellbook.")
    return log


def preserve_corpse_resurrection_bonus(party: list[PartyMemberState]) -> int:
    return 1 if any(has_heroic_skill(member, "preserve_corpse") for member in party if member.current_life > 0) else 0


def trap_save_bonus(member: PartyMemberState, trap_key: str, label: str = "") -> int:
    if not is_water_trap(trap_key, label):
        return 0
    bonus = 0
    if has_heroic_skill(member, "boatman"):
        bonus += member.level // 2
    if has_legendary_skill(member, "legendary_swimmer"):
        bonus += member.level * 2
    elif has_heroic_skill(member, "heroic_swimmer"):
        bonus += member.level
    return bonus


def trap_damage_after_reduction(member: PartyMemberState, trap_key: str, label: str, damage: int) -> tuple[int, list[str]]:
    if not is_fall_trap(trap_key, label) or not has_heroic_skill(member, "catfall"):
        return damage, []
    reduced = max(0, damage - member.level)
    if reduced < damage:
        return reduced, [f"{member.name}'s Catfall reduces trap damage by {member.level} ({damage} -> {reduced})."]
    return damage, []


def druidic_training_search_bonus(environment: str) -> int:
    if environment in {"caverns", "fungal_grottoes"}:
        return 1
    return 0


def heroic_climber_search_bonus(member: PartyMemberState, choice: str | None) -> int:
    if choice not in {"secret_door", "secret_passage"}:
        return 0
    if has_legendary_skill(member, "legendary_climber"):
        return 2
    if has_heroic_skill(member, "heroic_climber"):
        return 1
    return 0


def prodigious_memory_search_bonus(session: SessionState, party: list[PartyMemberState], tile_id: str) -> tuple[int, list[str]]:
    if has_legendary_skill_in_party(party, "legendary_memory"):
        return 1, ["Legendary Memory: +1 search."]
    if tile_id not in session.visited_tile_ids:
        return 0, []
    if any(has_heroic_skill(member, "prodigious_memory") for member in party if member.current_life > 0):
        return 1, ["Prodigious Memory: +1 search on a revisited tile."]
    return 0, []


def has_legendary_skill_in_party(party: list[PartyMemberState], skill_id: str) -> bool:
    return any(has_legendary_skill(member, skill_id) for member in party if member.current_life > 0)


def mark_tile_visited(session: SessionState, tile_id: str) -> None:
    if tile_id not in session.visited_tile_ids:
        session.visited_tile_ids.append(tile_id)


def apply_song_of_elidra(session: SessionState, party: list[PartyMemberState]) -> tuple[int, list[str]]:
    if session.song_of_elidra_used:
        return 0, []
    bonus = 0
    singer_names: list[str] = []
    notes: list[str] = []
    for member in party:
        if member.current_life <= 0:
            continue
        if has_legendary_skill(member, "legendary_song_of_elidra"):
            bonus = max(bonus, 2)
            singer_names.append(member.name)
        elif has_heroic_skill(member, "song_of_elidra"):
            bonus = max(bonus, 1)
            singer_names.append(member.name)
    if bonus <= 0:
        return 0, []
    session.song_of_elidra_used = True
    heard_by = ", ".join(member.name for member in party if member.current_life > 0)
    singer_label = ", ".join(singer_names) if singer_names else "Song of Elidra"
    notes.append(f"{singer_label}'s Song of Elidra raises the party reaction by +{bonus} (heard by {heard_by}).")
    return bonus, notes


def beast_leadership_reaction_bonus(party: list[PartyMemberState], enemies: list[EnemyState]) -> tuple[int, list[str]]:
    if not any(_foe_is_beast(enemy) for enemy in enemies):
        return 0, []
    bonus = 0
    for member in party:
        if member.current_life <= 0:
            continue
        if has_legendary_skill(member, "legendary_beast_leadership"):
            bonus = max(bonus, 2)
        elif has_heroic_skill(member, "beast_leadership"):
            bonus = max(bonus, 1)
    if bonus <= 0:
        return 0, []
    return bonus, [f"Beast Leadership adjusts reaction by +{bonus} vs beasts."]


def _foe_is_beast(enemy: EnemyState) -> bool:
    from .expert_skill_effects import foe_matches_keyword

    return foe_matches_keyword(enemy, "beast") or "beast" in {tag.lower() for tag in enemy.tags}


def restore_mental_capacity(
    session: SessionState,
    member: PartyMemberState,
    target: PartyMemberState,
) -> list[str]:
    if not has_heroic_skill(member, "restore_mental_capacity"):
        return [f"{member.name} does not know Restore Mental Capacity."]
    if session.restore_mental_capacity_used:
        return ["Restore Mental Capacity was already used this adventure."]
    from .madness import heal_madness, madness_points

    if madness_points(target) <= 0:
        return [f"{target.name} has no Madness to cure."]
    session.restore_mental_capacity_used = True
    healed = heal_madness(target, 1)
    return [f"{member.name} restores {target.name}'s mental capacity ({healed} Madness removed)."]
