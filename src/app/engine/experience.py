from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState, SessionState
from .class_profiles import (
    available_level_up_spells,
    level_up_benefit_notes,
    level_up_grants_spell_slot,
    max_life_for_level,
    spell_slot_count,
)
from .dice import AdvancementRollResult, advancement_roll_succeeds, roll_advancement, roll_d6
from .tier_advancement import (
    AdvancementPurpose,
    TIER_ENTRY,
    advancement_auto_success_naturals,
    advancement_roll_spec,
    effective_action_tier_band,
    level_up_gate_reason,
    tier_band_name,
    training_from_member,
)

MINOR_CATEGORIES = {"vermin", "minions"}
MAJOR_CATEGORIES = {"weird", "boss"}
MINOR_ENCOUNTERS_FOR_XP = 10
CLUES_FOR_SECRET_XP = 3
FINAL_BOSS_ROLL_TARGET = 6
POTION_ITEM_NAMES = {"potion of healing", "potion of healing."}

CAMPAIGN_MODE_LABELS: dict[str, str] = {
    "classical": "Classical",
    "slow_and_sure": "Slow and Sure",
    "old_school": "Old School",
    "slower_advancement": "Slower Advancement",
}


def campaign_mode_label(mode: str) -> str:
    return CAMPAIGN_MODE_LABELS.get(mode, mode.replace("_", " ").title())


@dataclass
class LevelUpResult:
    log: list[str]
    spell_pick_pending: bool = False


def tier_for_level(level: int) -> int:
    return max(1, (level - 1) // 4 + 1)


def is_minor_encounter(defeated: list[EnemyState]) -> bool:
    if not defeated:
        return False
    return all(enemy.category in MINOR_CATEGORIES for enemy in defeated)


def major_foes_defeated(defeated: list[EnemyState]) -> list[EnemyState]:
    return [enemy for enemy in defeated if enemy.category in MAJOR_CATEGORIES]


def xp_roll_succeeds(roll: int, level: int, *, bonus: int = 0) -> bool:
    if level >= 5:
        return roll >= 7 or roll + 2 + bonus > level
    return roll == 6 or roll + bonus > level


def perform_advancement_roll(
    member_or_level: PartyMemberState | int,
    *,
    bonus: int = 0,
    purpose: AdvancementPurpose = "level_up",
) -> AdvancementRollResult:
    if isinstance(member_or_level, PartyMemberState):
        return roll_advancement(
            member_or_level.level,
            member=member_or_level,
            purpose=purpose,
            bonus=bonus,
        )
    return roll_advancement(member_or_level, purpose=purpose, bonus=bonus)


def advancement_roll_explain(member: PartyMemberState) -> str:
    training = training_from_member(member)
    band = effective_action_tier_band(member.level, training)
    sides, modifier = advancement_roll_spec(member.level, training, "level_up")
    naturals = sorted(advancement_auto_success_naturals(sides))
    die_label = f"d{sides}+{modifier}" if modifier else f"d{sides}"
    if len(naturals) == 1:
        nat_text = f"natural {naturals[0]} on the d{sides}"
    else:
        nat_text = f"natural {naturals[0]}–{naturals[-1]} on the d{sides}"
    return (
        f"{tier_band_name(band)} tier: need {die_label} > Level {member.level}, "
        f"or {nat_text}, to advance."
    )


def tier_entry_requirements(tier: str) -> dict:
    if tier not in TIER_ENTRY:
        raise ValueError(f"Unknown tier: {tier}")
    return TIER_ENTRY[tier]


def tier_entry_blocked_reason(member: PartyMemberState, tier: str) -> str | None:
    spec = tier_entry_requirements(tier)
    training = training_from_member(member)
    if member.current_life <= 0:
        return f"{member.name} must be alive to train."
    if member.level < spec["min_level"]:
        return f"{member.name} must reach Level {spec['min_level']} before {tier.title()} training."
    if tier == "expert" and member.expert_trained:
        return f"{member.name} already has Expert training."
    if tier == "heroic":
        if not training.expert_trained:
            return f"{member.name} needs Expert training before Heroic training."
        if member.heroic_trained:
            return f"{member.name} already has Heroic training."
    if tier == "legendary":
        if not training.heroic_trained:
            return f"{member.name} needs Heroic training before Legendary training."
        if member.legendary_trained:
            return f"{member.name} already has Legendary training."
    return None


def advancement_succeeds(result: AdvancementRollResult, level: int) -> bool:
    return advancement_roll_succeeds(result, level)


def allowed_spell_name(class_id: str, spell_name: str) -> str:
    allowed = {spell.lower(): spell for spell in available_level_up_spells(class_id)}
    normalized = spell_name.strip().lower().replace("_", " ")
    return allowed.get(normalized, spell_name.strip())


def apply_level_up(member: PartyMemberState, *, new_spell: str | None = None) -> LevelUpResult:
    old_level = member.level
    member.level += 1
    member.max_life = max_life_for_level(member.class_id, member.level)
    member.current_life = min(member.max_life, member.current_life + 1)

    log = [
        f"{member.name} advances to Level {member.level} "
        f"({member.current_life}/{member.max_life} Life)."
    ]
    log.extend(level_up_benefit_notes(member.class_id, member.level))

    spell_pick_pending = False
    if level_up_grants_spell_slot(member.class_id):
        target_slots = spell_slot_count(member.class_id, member.level) or len(member.spells)
        slots_to_add = max(0, target_slots - len(member.spells))
        if slots_to_add <= 0:
            log.append(f"{member.name} already has {len(member.spells)} prepared spell(s).")
        elif new_spell:
            member.spells.append(allowed_spell_name(member.class_id, new_spell))
            log.append(f"{member.name} prepares {member.spells[-1]} in the new spell slot.")
        else:
            spell_pick_pending = True
            choices = ", ".join(available_level_up_spells(member.class_id))
            log.append(
                f"{member.name} gains a spell slot — choose a spell to prepare "
                f"({choices})."
            )

    if old_level < member.level:
        log.append("Class level bonuses apply immediately for the rest of this adventure.")
    return LevelUpResult(log, spell_pick_pending=spell_pick_pending)


def assign_level_up_spell(member: PartyMemberState, spell_name: str) -> list[str]:
    allowed = {spell.lower(): spell for spell in available_level_up_spells(member.class_id)}
    normalized = spell_name.strip().lower().replace("_", " ")
    canonical = allowed.get(normalized)
    if canonical is None:
        return [f"{spell_name} is not on this class spell list."]
    target_slots = spell_slot_count(member.class_id, member.level)
    if target_slots is None:
        return [f"{member.name} does not use spell slots."]
    if len(member.spells) >= target_slots:
        return [f"{member.name} already has {len(member.spells)}/{target_slots} spell slots filled."]
    member.spells.append(canonical)
    return [f"{member.name} prepares {canonical} in the new spell slot."]


def old_school_xp_for_defeated(defeated: list[EnemyState]) -> int:
    total = 0
    for enemy in defeated:
        if enemy.category in MAJOR_CATEGORIES:
            total += enemy.level * 10 + enemy.max_life * 5
        elif enemy.category == "vermin":
            total += max(0, enemy.level // 2)
        else:
            total += enemy.level
    return total


def old_school_level_cost(level: int) -> int:
    return (tier_for_level(level) + 2) * 100


def dungeon_has_final_boss(session: SessionState) -> bool:
    if session.final_boss_defeated or session.final_boss_designated:
        return True
    for tile in session.map_state.tiles:
        enemies = list(tile.enemies) + list(tile.defeated_enemies or [])
        for enemy in enemies:
            if "final_boss" in enemy.tags:
                return True
    return False


def mark_final_boss_candidate(
    enemies: list[EnemyState],
    *,
    major_foes_encountered: int,
    show_rolls: bool,
) -> tuple[list[str], EnemyState | None]:
    log: list[str] = []
    majors = [enemy for enemy in enemies if enemy.category in MAJOR_CATEGORIES and enemy.life > 0]
    if not majors:
        return log, None
    roll = roll_d6()
    target = roll + major_foes_encountered
    if show_rolls:
        log.append(
            f"Final Boss check: d6 = {roll} + {major_foes_encountered} major foes met = {target} (need {FINAL_BOSS_ROLL_TARGET}+)."
        )
    if target < FINAL_BOSS_ROLL_TARGET:
        return log, None
    boss = majors[0]
    boss.life += 1
    boss.max_life += 1
    boss.attacks += 1
    if "final_boss" not in boss.tags:
        boss.tags.append("final_boss")
    log.append(f"{boss.name} is the dungeon Final Boss (+1 Life, +1 attack, fights to the death).")
    return log, boss


def apply_final_boss_treasure_bonus(gold: int) -> int:
    return max(gold * 3, 100)


@dataclass
class XpAwardResult:
    log: list[str]
    classical_rolls: int = 0
    old_school_points: int = 0
    slower_bank_points: int = 0


def award_classical_progress(
    *,
    minor_encounters_defeated: int,
    clues_found: int,
    defeated: list[EnemyState],
    final_boss_killed: bool,
) -> XpAwardResult:
    log: list[str] = []
    rolls = 0
    minors = minor_encounters_defeated
    clues = clues_found

    majors = major_foes_defeated(defeated)
    for enemy in majors:
        rolls += 1
        log.append(f"Defeated {enemy.name} (Major Foe): earned 1 XP roll.")
        if any(tag == "final_boss" for tag in enemy.tags):
            rolls += 1
            log.append("Final Boss slain: earned 1 additional XP roll.")

    if majors:
        return XpAwardResult(log, classical_rolls=rolls)

    if not is_minor_encounter(defeated):
        return XpAwardResult(log)

    minors += 1
    if minors >= MINOR_ENCOUNTERS_FOR_XP:
        minors -= MINOR_ENCOUNTERS_FOR_XP
        rolls += 1
        log.append(
            f"Earned 1 XP roll ({MINOR_ENCOUNTERS_FOR_XP} minor encounters). Assign it from party sheets."
        )
    else:
        log.append(
            f"Minor encounter cleared ({minors}/{MINOR_ENCOUNTERS_FOR_XP} toward next XP roll)."
        )

    return XpAwardResult(log, classical_rolls=rolls)


def is_potion_item(item: str) -> bool:
    return "potion" in item.strip().lower()


def potion_kind(item: str) -> str:
    lower = item.strip().lower()
    if "healing" in lower:
        return "healing"
    if "sleep" in lower:
        return "sleep"
    return "other"


def usable_potions_in_inventory(member: PartyMemberState) -> list[str]:
    return [item for item in member.inventory if is_potion_item(item)]


def potion_in_inventory(member: PartyMemberState) -> str | None:
    for item in member.inventory:
        if item.strip().lower() in POTION_ITEM_NAMES or item.lower().startswith("potion of healing"):
            return item
    return None
