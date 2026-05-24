from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import EnemyState, PartyMemberState, SessionState

if TYPE_CHECKING:
    from .weapons import WeaponProfile

TARGET_SKILLS = frozenset({"impervious", "sworn_enemy"})

SKILL_MECHANICS: dict[str, str] = {
    "acute_hearing": "Listen at a door (d6 6+): preview room content once per door; foes cannot surprise.",
    "arcane_tanner": "Craft phasing panther or dragon-skin garments between adventures from beast hides.",
    "berserk_fury": "Barbarian may use Rage attack one additional time per adventure.",
    "brawler": "Unarmed attacks are at −1 instead of −2.",
    "combat_acrobatics": "Swap marching-order position with an ally during combat (full turn, no attack).",
    "commanding_presence": "Front rank (positions 1–2): party +1 to saves vs fear/terror; hirelings +1 morale.",
    "continual_light": "Create a magical lantern on a holy symbol or coin; cleric may cast in combat (forfeit attack).",
    "create_holy_water": "Before each adventure, create one vial of holy water for 10 gp.",
    "culling_of_the_weak": "Once per encounter, first successful minion hit slays extra minions (1 per 2 points over level).",
    "danger_sense": "Rearguard (positions 3–4): wandering monsters do not surprise the party.",
    "deadly_accuracy": "Elf +1 with bow; halfling +1 with sling.",
    "dead_shot": "Once per encounter, reroll one failed ranged attack.",
    "deadly_strike": "Once per encounter, two-handed hit inflicts double wounds (declare before rolling).",
    "detective": "+1 on search rolls used to find clues only.",
    "double_attack": "Once per encounter, two melee hand-weapon attacks (same or different targets).",
    "dragonslayers_strike": "First attack vs a dragon each encounter: +1 to hit and double wounds if it hits.",
    "dying_action": "When reduced to 0 Life, make one Attack roll at +1 before falling.",
    "gladiator": "+1 Attack and Defense vs Chaos Champion / Trial of Champions fights.",
    "impervious": "+1 Defense vs chosen minion/vermin type (repeatable for new types).",
    "intuition": "Treat search roll 4 as 5 (not combinable with Detective).",
    "knife_throwing": "Throw a light slashing weapon as a ranged attack (−1); recover after encounter.",
    "lesser_necromancy": "Ritual on fallen ally: d8+L vs their level to reanimate as undead (half Life, no class abilities).",
    "negotiator": "Adjust monster reaction d6 by ±1 if it avoids Fight / Fight to the Death.",
    "orcslayer": "+1 Attack vs orcs.",
    "poison_resistance": "Once per poison save, reroll a failed save.",
    "protective_incense": "Once per encounter, +1 Defense vs demons/undead for self or ally.",
    "quick_footed": "+1 Defense when fleeing or withdrawing.",
    "scroll_maker": "Before each adventure, scribe one scroll (80 gp; spell the caster could use).",
    "shield_bash": "After an exploding Defense roll, free shield bash Attack at −1 vs that foe.",
    "spore_alchemy": "After defeating fungus foes, prepare one sleep-spore throw (Sleep effect).",
    "spot_weakness": "Exploding attack roll vs a boss inflicts +1 wound.",
    "stabbing_attack": "Two melee attacks per turn with a light hand weapon (e.g. dagger).",
    "stone_mastery": "Search roll 4 counts as 5 when finding secret doors only.",
    "strong_will": "+1 vs fear/terror saves; ignore the first Madness point each adventure.",
    "super_logic": "+1 to puzzle rolls.",
    "sworn_enemy": "+1 Attack vs chosen monster type; that type prefers targeting this hero.",
    "terrifying_savagery": "When this barbarian slays minions and triggers morale, foes roll at −1.",
    "turn_undead": "Once per encounter: d6 + ½L vs undead level; 1d6 flee on success.",
    "vampire_hunter": "+1 Attack vs vampires; may harm vampires without stakes or magic weapons.",
    "withstand_pain": "Once per encounter, ignore the first point of damage taken.",
    "whirlwind_of_steel": "Chain up to three minion kills at −1/−2; no exploding dice; once per encounter.",
}

IMPLEMENTATION_STATUS: dict[str, str] = {
    skill_id: "wired"
    for skill_id in SKILL_MECHANICS
}


def has_skill(member: PartyMemberState, skill_id: str) -> bool:
    needle = skill_id.strip().lower()
    for item in member.learned_expert_skills:
        if item.strip().lower().split(":", 1)[0] == needle:
            return True
    return False


def skill_target(member: PartyMemberState, skill_id: str) -> str | None:
    key = skill_id.strip().lower()
    target = (member.expert_skill_targets or {}).get(key)
    if target:
        return target.strip().lower()
    for entry in member.learned_expert_skills:
        if entry.lower().startswith(f"{key}:"):
            return entry.split(":", 1)[1].strip().lower()
    return None


def normalize_skill_entry(skill_id: str, target: str | None = None) -> str:
    normalized = skill_id.strip().lower()
    if target and normalized in TARGET_SKILLS:
        return f"{normalized}:{target.strip().lower()}"
    return normalized


def foe_matches_keyword(enemy: EnemyState, keyword: str) -> bool:
    needle = keyword.strip().lower()
    if not needle:
        return False
    name = enemy.name.lower()
    tags = {tag.lower() for tag in enemy.tags}
    return needle in name or any(needle in tag for tag in tags)


def _is_vampire(enemy: EnemyState) -> bool:
    return foe_matches_keyword(enemy, "vampire")


def _is_dragon(enemy: EnemyState) -> bool:
    return foe_matches_keyword(enemy, "dragon")


def _is_orc(enemy: EnemyState) -> bool:
    return foe_matches_keyword(enemy, "orc")


def _is_undead(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    return "undead" in tags or "skeleton" in enemy.name.lower() or "zombie" in enemy.name.lower()


def _is_demon(enemy: EnemyState) -> bool:
    return foe_matches_keyword(enemy, "demon") or foe_matches_keyword(enemy, "devil")


def gladiator_fight(enemies: list[EnemyState]) -> bool:
    return any(
        "chaos champion" in enemy.name.lower() or "trial" in enemy.name.lower()
        for enemy in enemies
    )


def reset_expert_encounter(session: SessionState) -> None:
    session.expert_encounter_spent = {}
    session.expert_protective_incense_target = None


def encounter_spent(session: SessionState, character_id: str, flag: str) -> bool:
    return flag in (session.expert_encounter_spent or {}).get(character_id, [])


def mark_encounter_spent(session: SessionState, character_id: str, flag: str) -> None:
    spent = dict(session.expert_encounter_spent or {})
    flags = list(spent.get(character_id, []))
    if flag not in flags:
        flags.append(flag)
    spent[character_id] = flags
    session.expert_encounter_spent = spent


def party_has_skill(party: list[PartyMemberState], skill_id: str) -> bool:
    return any(has_skill(member, skill_id) for member in party if member.current_life > 0)


def rearguard_has_danger_sense(party: list[PartyMemberState]) -> bool:
    for member in party:
        if member.current_life <= 0 or not has_skill(member, "danger_sense"):
            continue
        if member.marching_order >= 3:
            return True
    return False


def front_rank_has_commanding_presence(party: list[PartyMemberState]) -> bool:
    for member in party:
        if member.current_life <= 0 or not has_skill(member, "commanding_presence"):
            continue
        if member.marching_order <= 2:
            return True
    return False


def expert_attack_bonus(
    member: PartyMemberState,
    enemy: EnemyState,
    session: SessionState,
    *,
    missile: bool = False,
    weapon: WeaponProfile | None = None,
    gladiator_match: bool = False,
) -> int:
    bonus = 0
    if has_skill(member, "orcslayer") and _is_orc(enemy):
        bonus += 1
    if has_skill(member, "vampire_hunter") and _is_vampire(enemy):
        bonus += 1
    target = skill_target(member, "sworn_enemy")
    if target and foe_matches_keyword(enemy, target):
        bonus += 1
    if missile and has_skill(member, "deadly_accuracy"):
        class_id = member.class_id.lower()
        weapon_name = (weapon.item if weapon else member.default_missile_weapon or "").lower()
        if class_id == "elf" and "bow" in weapon_name:
            bonus += 1
        if class_id == "halfling" and "sling" in weapon_name:
            bonus += 1
    if gladiator_match and has_skill(member, "gladiator"):
        bonus += 1
    if (
        has_skill(member, "dragonslayers_strike")
        and _is_dragon(enemy)
        and not encounter_spent(session, member.character_id, "dragonslayers_strike")
    ):
        bonus += 1
    return bonus


def expert_defense_bonus(
    member: PartyMemberState,
    enemy: EnemyState | None,
    session: SessionState,
    *,
    withdrawing: bool = False,
    gladiator_match: bool = False,
) -> int:
    bonus = 0
    if withdrawing and has_skill(member, "quick_footed"):
        bonus += 1
    if enemy is not None:
        target = skill_target(member, "impervious")
        if target and foe_matches_keyword(enemy, target):
            bonus += 1
        protected = session.expert_protective_incense_target
        if (
            protected == member.character_id
            and not encounter_spent(session, member.character_id, "protective_incense")
            and (_is_undead(enemy) or _is_demon(enemy))
        ):
            bonus += 1
    if gladiator_match and has_skill(member, "gladiator"):
        bonus += 1
    if wears_arcane_garment(member, dragon=True) and _is_dragon(enemy):
        bonus += 1
    return bonus


def expert_save_bonus(
    member: PartyMemberState,
    party: list[PartyMemberState] | None = None,
    *,
    fear: bool = False,
) -> int:
    bonus = 0
    if fear:
        if has_skill(member, "strong_will"):
            bonus += 1
        if party and front_rank_has_commanding_presence(party):
            bonus += 1
    return bonus


def unarmed_attack_penalty(member: PartyMemberState) -> int:
    if has_skill(member, "brawler"):
        return -1
    if member.class_id.lower() == "mushroom_monk":
        from .weapons import mushroom_monk_unarmed_penalty

        return mushroom_monk_unarmed_penalty(member)
    return -2


def effective_barbarian_rage_uses(level: int, member: PartyMemberState) -> int:
    from .class_profiles import barbarian_rage_uses

    uses = barbarian_rage_uses(level)
    if has_skill(member, "berserk_fury"):
        uses += 1
    return uses


def adjust_incoming_damage(
    session: SessionState,
    member: PartyMemberState,
    damage: int,
) -> tuple[int, list[str]]:
    if damage <= 0:
        return damage, []
    if has_skill(member, "withstand_pain") and not encounter_spent(
        session, member.character_id, "withstand_pain"
    ):
        mark_encounter_spent(session, member.character_id, "withstand_pain")
        reduced = max(0, damage - 1)
        if reduced < damage:
            return reduced, [f"{member.name}'s Withstand Pain ignores 1 damage ({reduced} taken)."]
    return damage, []


def culling_extra_minion_kills(total: int, foe_level: int) -> int:
    margin = total - foe_level
    if margin <= 0:
        return 0
    return margin // 2


def spot_weakness_extra_damage(rolls: list[int], enemy: EnemyState) -> int:
    if enemy.category not in {"boss", "weird"} and "final_boss" not in enemy.tags:
        return 0
    sides = max(rolls) if rolls else 6
    threshold = 6 if sides <= 6 else sides - 1
    if len(rolls) > 1 or (rolls and rolls[0] >= threshold):
        return 1
    return 0


def deadly_strike_multiplier(member: PartyMemberState, session: SessionState, active: bool) -> int:
    if not active or not has_skill(member, "deadly_strike"):
        return 1
    if encounter_spent(session, member.character_id, "deadly_strike"):
        return 1
    mark_encounter_spent(session, member.character_id, "deadly_strike")
    return 2


def dragonslayer_damage_multiplier(
    member: PartyMemberState,
    session: SessionState,
    enemy: EnemyState,
) -> int:
    if not has_skill(member, "dragonslayers_strike") or not _is_dragon(enemy):
        return 1
    if encounter_spent(session, member.character_id, "dragonslayers_strike"):
        return 1
    mark_encounter_spent(session, member.character_id, "dragonslayers_strike")
    return 2


def stabbing_attack_follow_up(member: PartyMemberState, weapon: WeaponProfile | None) -> bool:
    return bool(weapon and weapon.light and has_skill(member, "stabbing_attack"))


def light_hand_weapon(weapon: WeaponProfile | None) -> bool:
    return bool(weapon and weapon.light and weapon.kind == "melee")


def sworn_enemy_target_preference(
    party: list[PartyMemberState],
    enemy: EnemyState,
) -> PartyMemberState | None:
    for member in party:
        if member.current_life <= 0:
            continue
        target = skill_target(member, "sworn_enemy")
        if target and foe_matches_keyword(enemy, target):
            return member
    return None


def adjust_reaction_roll(
    party: list[PartyMemberState],
    roll: int,
    adjustment: int,
) -> tuple[int, list[str]]:
    if adjustment == 0 or not any(has_skill(member, "negotiator") for member in party):
        return roll, []
    adjusted = max(1, min(6, roll + adjustment))
    direction = "+1" if adjustment > 0 else "-1"
    return adjusted, [f"Negotiator adjusts the reaction roll {direction} ({roll} -> {adjusted})."]


def expert_morale_modifier(session: SessionState, party: list[PartyMemberState]) -> int:
    if not any(has_skill(member, "terrifying_savagery") for member in party):
        return 0
    if not encounter_spent(session, "_party", "terrifying_savagery"):
        mark_encounter_spent(session, "_party", "terrifying_savagery")
        return -1
    return 0


def adjust_search_roll(
    party: list[PartyMemberState],
    roll: int,
    *,
    choice: str | None,
) -> tuple[int, list[str]]:
    notes: list[str] = []
    adjusted = roll
    if roll == 4:
        if choice == "clue" and any(has_skill(m, "detective") for m in party):
            adjusted = 5
            notes.append("Detective: search 4 counts as 5 for clues.")
        elif choice == "secret_door" and any(has_skill(m, "stone_mastery") for m in party):
            adjusted = 5
            notes.append("Stone Mastery: search 4 counts as 5 for secret doors.")
        elif choice not in {"clue", "secret_door"} and any(has_skill(m, "intuition") for m in party):
            if not any(has_skill(m, "detective") for m in party):
                adjusted = 5
                notes.append("Intuition: search 4 counts as 5.")
    return adjusted, notes


def member_carries_shield(member: PartyMemberState) -> bool:
    from .inventory import count_carried_shields

    return count_carried_shields(member.inventory) > 0


def expert_puzzle_bonus(party: list[PartyMemberState]) -> int:
    return 1 if party_has_skill(party, "super_logic") else 0


def knife_throw_weapon(member: PartyMemberState) -> str | None:
    from .weapons import weapon_profile

    for item in member.inventory:
        profile = weapon_profile(item)
        if profile and profile.light and profile.slashing and profile.kind == "melee":
            return item
    return None


def wears_arcane_garment(member: PartyMemberState, *, dragon: bool = False, phasing: bool = False) -> bool:
    for item in member.inventory:
        lower = item.lower()
        if dragon and "dragon-skin" in lower:
            return True
        if phasing and "phasing panther" in lower:
            return True
    return False


def prepare_adventure_expert_items(party: list[PartyMemberState], log: list[str]) -> None:
    for member in party:
        if has_skill(member, "create_holy_water") and member.class_id.lower() == "cleric":
            if member.gold >= 10:
                member.gold -= 10
                member.inventory.append("Holy Water")
                log.append(f"{member.name} creates Holy Water before the adventure (10gp).")
        if has_skill(member, "scroll_maker") and member.class_id.lower() in {
            "wizard",
            "elf",
            "illusionist",
            "druid",
        }:
            spells = [spell for spell in (member.spells or []) if spell.strip()]
            if member.gold >= 80 and spells:
                spell = spells[0]
                member.gold -= 80
                member.inventory.append(f"Scroll of {spell}")
                log.append(f"{member.name} scribes Scroll of {spell} before the adventure (80gp).")
        for hide, garment in (
            ("Panther Hide", "Phasing Panther Garment"),
            ("Dragon Hide", "Dragon-Skin Garment"),
        ):
            if has_skill(member, "arcane_tanner") and hide in member.inventory:
                member.inventory.remove(hide)
                member.inventory.append(garment)
                log.append(f"{member.name} crafts {garment} from {hide} (Arcane Tanner).")


def grant_spore_doses_after_combat(
    session: SessionState,
    party: list[PartyMemberState],
    defeated: list[EnemyState],
) -> list[str]:
    fungus_slain = any(
        "fungus" in {tag.lower() for tag in enemy.tags}
        or "mushroom" in enemy.name.lower()
        for enemy in defeated
    )
    if not fungus_slain:
        return []
    notes: list[str] = []
    doses = dict(session.expert_spore_doses or {})
    for member in party:
        if member.current_life <= 0 or not has_skill(member, "spore_alchemy"):
            continue
        doses[member.character_id] = doses.get(member.character_id, 0) + 1
        notes.append(f"{member.name} prepares a sleep spore (Spore Alchemy).")
    session.expert_spore_doses = doses
    return notes


def expert_skill_implementation_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for skill_id, mechanic in SKILL_MECHANICS.items():
        name = skill_id.replace("_", " ").title()
        rows.append(
            {
                "skill": name,
                "mechanic": mechanic,
                "status": IMPLEMENTATION_STATUS.get(skill_id, "planned"),
            }
        )
    return rows