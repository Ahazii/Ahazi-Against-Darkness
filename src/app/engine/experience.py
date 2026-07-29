from __future__ import annotations

from collections.abc import Callable
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
    advancement_auto_success_naturals,
    advancement_roll_spec,
    effective_action_tier_band,
    level_up_gate_reason,
    tier_band_name,
    training_from_member,
)
from .tier_skills import available_advancement_forks, advancement_fork_label, validate_advancement_choice
from .heroic_skill_effects import consume_training_focus_bonus

MINOR_CATEGORIES = {"vermin", "minions"}
MAJOR_CATEGORIES = {"weird", "boss"}
MINOR_ENCOUNTERS_FOR_XP = 10
ABYSS_MINION_ENCOUNTERS_FOR_XP = 5
CLUES_FOR_SECRET_XP = 3
FINAL_BOSS_ROLL_TARGET = 6
DEFAULT_UNLIMITED_MAP_ELEMENT_CAP = 60
MIN_UNLIMITED_MAP_ELEMENT_CAP = 1
MAX_UNLIMITED_MAP_ELEMENT_CAP = 999


def normalize_unlimited_map_element_cap(value: int | str | None, *, default: int = DEFAULT_UNLIMITED_MAP_ELEMENT_CAP) -> int:
    try:
        cap = int(value)
    except (TypeError, ValueError):
        cap = default
    return max(MIN_UNLIMITED_MAP_ELEMENT_CAP, min(MAX_UNLIMITED_MAP_ELEMENT_CAP, cap))


def unlimited_map_element_cap(session: SessionState) -> int | None:
    if session.map_bounds_mode != "unlimited":
        return None
    return normalize_unlimited_map_element_cap(session.unlimited_map_element_cap)


def map_elements_at_cap(session: SessionState) -> bool:
    cap = unlimited_map_element_cap(session)
    if cap is None:
        return False
    return len(session.map_state.tiles) >= cap


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


def is_abyss_minion_encounter(session: SessionState, defeated: list[EnemyState]) -> bool:
    """Return whether this is an Abyss minion encounter with its own XP tally."""
    if defeated and all(enemy.category == "minions" for enemy in defeated):
        from .abyss_tables import is_abyss_profile

        if not is_abyss_profile(session):
            return False
        return all("abyss" in {tag.lower() for tag in enemy.tags} for enemy in defeated)
    return False


def major_foes_defeated(defeated: list[EnemyState]) -> list[EnemyState]:
    return [enemy for enemy in defeated if enemy.category in MAJOR_CATEGORIES]


def defeated_mixed_major_minor(defeated: list[EnemyState]) -> bool:
    """EE Fiendish Foes p.180: major + minions/vermin on one tile."""
    if not defeated:
        return False
    has_major = any(enemy.category in MAJOR_CATEGORIES for enemy in defeated)
    has_minor = any(enemy.category in MINOR_CATEGORIES for enemy in defeated)
    return has_major and has_minor


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


def highest_character_level(party: list[PartyMemberState]) -> int:
    return max((member.level for member in party), default=1)


def grant_xp_credit(session: SessionState, amount: int, reason: str) -> None:
    """Apply a rules-earned XP credit to the active campaign-mode ledger."""
    if amount <= 0 or session.xp_system == "slow_and_sure":
        return
    if session.xp_system == "old_school":
        tier = tier_for_level(highest_character_level(session.party))
        points = tier * 100 * amount
        session.old_school_xp_tally += points
        session.log.append(f"{reason} Old School XP +{points} (tally {session.old_school_xp_tally}).")
        return
    if session.xp_system == "slower_advancement":
        session.slower_xp_bank += amount
        session.log.append(f"{reason} Banked {amount} XP ({session.slower_xp_bank} total).")
        return
    session.xp_rolls_pending += amount
    session.log.append(f"{reason} Earned {amount} XP roll(s). Assign from party sheets.")


def record_minor_encounter_progress(
    session: SessionState,
    count: int,
    *,
    reason: str = "Minor encounter",
    show_rolls: bool = True,
) -> None:
    """Record non-combat procedures that explicitly count as minor encounters."""
    if count <= 0 or session.xp_system in {"slow_and_sure", "old_school"}:
        return
    for _ in range(count):
        session.minor_encounters_defeated += 1
        progress = session.minor_encounters_defeated
        if show_rolls:
            session.log.append(
                f"{reason}: minor encounter progress {progress}/{MINOR_ENCOUNTERS_FOR_XP}."
            )
        if progress >= MINOR_ENCOUNTERS_FOR_XP:
            session.minor_encounters_defeated -= MINOR_ENCOUNTERS_FOR_XP
            grant_xp_credit(
                session,
                1,
                f"{MINOR_ENCOUNTERS_FOR_XP} minor encounters:",
            )


def award_encounter_xp(session: SessionState, defeated: list[EnemyState], *, show_rolls: bool) -> None:
    """Award encounter XP according to the active campaign mode and foe mix."""
    if not defeated:
        return
    star_slayers = [
        enemy
        for enemy in defeated
        if enemy.name == "Star-Slayer from Beyond"
        or "star_slayer" in {str(tag).lower() for tag in enemy.tags}
    ]
    if star_slayers:
        if any("final_boss" in {str(tag).lower() for tag in enemy.tags} for enemy in star_slayers):
            session.final_boss_defeated = True
        grant_xp_credit(
            session,
            2,
            "Defeated Star-Slayer from Beyond (TAG p.31; exactly two XP rolls):",
        )
        return
    if session.xp_system == "slow_and_sure":
        return
    if session.xp_system == "old_school":
        points = old_school_xp_for_defeated(defeated)
        if points:
            session.old_school_xp_tally += points
            session.log.append(f"Old School XP +{points} (tally {session.old_school_xp_tally}).")
        return

    majors = major_foes_defeated(defeated)
    if majors and defeated_mixed_major_minor(defeated):
        names = ", ".join(enemy.name for enemy in majors)
        grant_xp_credit(session, 2, f"Mixed major+minions encounter ({names}; EE p.180):")
        if any("final_boss" in enemy.tags for enemy in majors):
            session.final_boss_defeated = True
            grant_xp_credit(session, 1, "Final Boss slain:")
    else:
        for enemy in majors:
            grant_xp_credit(session, 1, f"Defeated {enemy.name} (Major Foe):")
            if "final_boss" in enemy.tags:
                session.final_boss_defeated = True
                grant_xp_credit(session, 1, "Final Boss slain:")
    if majors:
        return
    if not is_minor_encounter(defeated):
        return
    if is_abyss_minion_encounter(session, defeated):
        session.abyss_minion_encounters_defeated += 1
        progress = session.abyss_minion_encounters_defeated
        target = ABYSS_MINION_ENCOUNTERS_FOR_XP
        label = "Abyss minion"
    else:
        record_minor_encounter_progress(
            session,
            1,
            reason="Minor encounter cleared",
            show_rolls=show_rolls,
        )
        return
    if show_rolls:
        session.log.append(
            f"{label.title()} encounter cleared ({progress}/{target} toward next XP credit)."
        )
    if progress >= target:
        if label == "Abyss minion":
            session.abyss_minion_encounters_defeated -= target
        else:
            session.minor_encounters_defeated -= target
        grant_xp_credit(session, 1, f"{target} {label} encounters:")


def old_school_level_cost(level: int) -> int:
    return (tier_for_level(level) + 2) * 100


def apply_old_school_level_up(
    session: SessionState,
    character_id: str | None,
    *,
    can_assign_level_up: Callable[[SessionState, str], bool],
    complete_level_up: Callable[[SessionState, PartyMemberState], None],
    show_rolls: bool,
) -> None:
    """Spend Old School XP on the next eligible living hero's level-up transaction."""
    if session.level_up_spell_pending_character_id:
        session.log.append("Finish the pending spell choice before leveling again.")
        return
    if session.xp_system != "old_school":
        session.log.append("Old School leveling is not active for this adventure.")
        return
    member = next((item for item in session.party if item.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        session.log.append("Choose a living hero to advance.")
        return
    if not can_assign_level_up(session, character_id or ""):
        session.log.append("Another hero must level next (same PC cannot level twice in a row).")
        return
    cost = old_school_level_cost(member.level)
    if session.old_school_xp_tally < cost:
        session.log.append(f"Need {cost} XP (tally {session.old_school_xp_tally}).")
        return
    session.old_school_xp_tally -= cost
    complete_level_up(session, member)
    if show_rolls:
        session.log.append(f"Old School XP spent: {cost} (tally {session.old_school_xp_tally}).")


def apply_slower_advancement(
    session: SessionState,
    character_id: str | None,
    *,
    xp_spent: int | None,
    show_rolls: bool,
    explain_math: bool,
    advancement_fork: str | None,
    expert_skill_id: str | None,
    expert_skill_target: str | None,
    heroic_skill_id: str | None,
    legendary_skill_id: str | None,
    heroic_skill_target: str | None,
    expert_catalog: list[dict],
    heroic_catalog: list[dict],
    legendary_catalog: list[dict],
    can_assign_level_up: Callable[[SessionState, str], bool],
    apply_success: Callable[[PartyMemberState, str], None],
) -> None:
    """Spend Slower Advancement XP and resolve the selected advancement fork."""
    if session.level_up_spell_pending_character_id:
        session.log.append("Finish the pending spell choice before spending more banked XP.")
        return
    if session.xp_system != "slower_advancement":
        session.log.append("Slower Advancement is not active for this adventure.")
        return
    member = next((item for item in session.party if item.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        session.log.append("Choose a living hero to advance.")
        return
    if not can_assign_level_up(session, character_id or ""):
        session.log.append("Another hero must level next (same PC cannot level twice in a row).")
        return
    target_level = member.level + 1
    minimum = target_level
    spent = xp_spent if xp_spent is not None else minimum
    if spent < minimum:
        session.log.append(f"Spend at least {minimum} banked XP to try for Level {target_level}.")
        return
    if session.slower_xp_bank < spent:
        session.log.append(f"Need {spent} banked XP (have {session.slower_xp_bank}).")
        return

    fork = advancement_fork or "level_up"
    blocked = validate_advancement_choice(
        member,
        fork,
        expert_catalog=expert_catalog,
        heroic_catalog=heroic_catalog,
        legendary_catalog=legendary_catalog,
        expert_skill_id=expert_skill_id,
        expert_skill_target=expert_skill_target,
        heroic_skill_id=heroic_skill_id,
        legendary_skill_id=legendary_skill_id,
        heroic_skill_target=heroic_skill_target,
    )
    if blocked:
        session.log.append(blocked)
        return

    purpose = {
        "level_up": "level_up",
        "learn_expert_skill": "learn_expert_skill",
        "learn_heroic_skill": "learn_heroic_skill",
        "learn_legendary_skill": "learn_legendary_skill",
    }[fork]
    session.slower_xp_bank -= spent
    bonus = spent - minimum
    focus_bonus = consume_training_focus_bonus(session, member.character_id)
    bonus += focus_bonus
    result = perform_advancement_roll(member, bonus=bonus, purpose=purpose)
    if focus_bonus:
        session.log.append(f"{member.name} applies Training Focus (+{focus_bonus}).")
    if show_rolls:
        session.log.append(
            f"Slower {advancement_fork_label(fork).lower()} for {member.name}: {spent} XP banked, "
            f"{result.die_label} = {result.natural}"
            + (f" + {result.modifier} = {result.total}" if result.modifier else "")
            + f" vs Level {member.level}."
        )
    if explain_math:
        session.log.append(advancement_roll_explain(member))
    if advancement_succeeds(result, member.level):
        apply_success(member, fork)
    elif fork == "level_up":
        session.log.append(f"{member.name} fails to advance (needs > {member.level} with bonus).")
    else:
        session.log.append(
            f"{member.name} fails to learn the {advancement_fork_label(fork).lower()} "
            f"(needs > {member.level} with bonus)."
        )


def apply_classical_xp_roll(
    session: SessionState,
    character_id: str | None,
    *,
    show_rolls: bool,
    explain_math: bool,
    advancement_fork: str | None,
    expert_skill_id: str | None,
    expert_skill_target: str | None,
    heroic_skill_id: str | None,
    legendary_skill_id: str | None,
    heroic_skill_target: str | None,
    expert_catalog: list[dict],
    heroic_catalog: list[dict],
    legendary_catalog: list[dict],
    can_assign_level_up: Callable[[SessionState, str], bool],
    apply_success: Callable[[PartyMemberState, str], None],
) -> None:
    """Spend one pending Classical XP roll on a validated advancement fork."""
    if session.level_up_spell_pending_character_id:
        pending = next(
            (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
            None,
        )
        name = pending.name if pending else "the hero"
        session.log.append(f"Choose a spell for {name} before spending another XP roll.")
        return
    if session.mode == "combat":
        session.log.append("XP rolls wait until combat ends.")
        return
    if session.xp_system != "classical":
        session.log.append(f"Use the {campaign_mode_label(session.xp_system)} advancement action instead.")
        return
    if session.xp_rolls_pending <= 0:
        session.log.append("No XP rolls are available.")
        return
    member = next((item for item in session.party if item.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        session.log.append("Choose a living hero for the XP roll.")
        return
    if not can_assign_level_up(session, character_id or ""):
        session.log.append("Another hero must take the next level (same PC cannot level twice in a row).")
        return

    allowed = available_advancement_forks(member)
    fork = advancement_fork or (allowed[0] if len(allowed) == 1 else None)
    blocked = validate_advancement_choice(
        member,
        fork or "",
        expert_catalog=expert_catalog,
        heroic_catalog=heroic_catalog,
        legendary_catalog=legendary_catalog,
        expert_skill_id=expert_skill_id,
        expert_skill_target=expert_skill_target,
        heroic_skill_id=heroic_skill_id,
        legendary_skill_id=legendary_skill_id,
        heroic_skill_target=heroic_skill_target,
    )
    if fork is None or blocked:
        session.log.append(blocked or f"Choose {', '.join(advancement_fork_label(item) for item in allowed)}.")
        return

    purpose = {
        "level_up": "level_up",
        "learn_expert_skill": "learn_expert_skill",
        "learn_heroic_skill": "learn_heroic_skill",
        "learn_legendary_skill": "learn_legendary_skill",
    }[fork]
    session.xp_rolls_pending -= 1
    focus_bonus = consume_training_focus_bonus(session, member.character_id)
    result = perform_advancement_roll(member, purpose=purpose, bonus=focus_bonus)
    if focus_bonus:
        session.log.append(f"{member.name} applies Training Focus (+{focus_bonus}).")
    if show_rolls:
        session.log.append(
            f"{advancement_fork_label(fork)} roll for {member.name}: {result.die_label} = {result.natural}"
            + (f" + {result.modifier} = {result.total}" if result.modifier else "")
            + f" vs Level {member.level}."
        )
    if explain_math:
        session.log.append(advancement_roll_explain(member))
    if advancement_succeeds(result, member.level):
        apply_success(member, fork)
    elif fork == "level_up":
        session.log.append(f"{member.name} fails to advance (needs > {member.level}).")
    else:
        session.log.append(
            f"{member.name} fails to learn the {advancement_fork_label(fork).lower()} (needs > {member.level})."
        )


def bank_classical_xp_roll(session: SessionState, character_id: str | None) -> None:
    """Move one pending Classical XP roll onto a selected living hero."""
    if session.level_up_spell_pending_character_id:
        pending = next(
            (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
            None,
        )
        name = pending.name if pending else "the hero"
        session.log.append(f"Choose a spell for {name} before banking another XP roll.")
        return
    if session.mode == "combat":
        session.log.append("XP rolls wait until combat ends.")
        return
    if session.xp_system != "classical":
        session.log.append(f"Use the {campaign_mode_label(session.xp_system)} advancement action instead.")
        return
    if session.xp_rolls_pending <= 0:
        session.log.append("No pending XP rolls are available to bank.")
        return
    member = next((item for item in session.party if item.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        session.log.append("Choose a living hero to bank the XP roll.")
        return
    session.xp_rolls_pending -= 1
    member.xp += 1
    session.log.append(f"{member.name} banks 1 XP roll for later advancement ({member.xp} banked).")


def spend_banked_classical_xp(
    session: SessionState,
    character_id: str | None,
    *,
    show_rolls: bool,
    explain_math: bool,
    advancement_fork: str | None,
    expert_skill_id: str | None,
    expert_skill_target: str | None,
    heroic_skill_id: str | None,
    legendary_skill_id: str | None,
    heroic_skill_target: str | None,
    expert_catalog: list[dict],
    heroic_catalog: list[dict],
    legendary_catalog: list[dict],
    can_assign_level_up: Callable[[SessionState, str], bool],
    apply_success: Callable[[PartyMemberState, str], None],
) -> None:
    """Spend one hero-owned Classical XP roll on a validated advancement fork."""
    if session.level_up_spell_pending_character_id:
        pending = next(
            (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
            None,
        )
        name = pending.name if pending else "the hero"
        session.log.append(f"Choose a spell for {name} before spending banked XP.")
        return
    if session.mode == "combat":
        session.log.append("Banked XP spending waits until combat ends.")
        return
    if session.xp_system != "classical":
        session.log.append(f"Use the {campaign_mode_label(session.xp_system)} advancement action instead.")
        return
    member = next((item for item in session.party if item.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        session.log.append("Choose a living hero to spend banked XP.")
        return
    if member.xp <= 0:
        session.log.append(f"{member.name} has no banked XP rolls.")
        return

    allowed = available_advancement_forks(member)
    fork = advancement_fork or (allowed[0] if len(allowed) == 1 else None)
    blocked = validate_advancement_choice(
        member,
        fork or "",
        expert_catalog=expert_catalog,
        heroic_catalog=heroic_catalog,
        legendary_catalog=legendary_catalog,
        expert_skill_id=expert_skill_id,
        expert_skill_target=expert_skill_target,
        heroic_skill_id=heroic_skill_id,
        legendary_skill_id=legendary_skill_id,
        heroic_skill_target=heroic_skill_target,
    )
    if fork is None or blocked:
        session.log.append(blocked or f"Choose {', '.join(advancement_fork_label(item) for item in allowed)}.")
        return
    if fork == "level_up" and not can_assign_level_up(session, character_id or ""):
        session.log.append("Another hero must take the next level (same PC cannot level twice in a row).")
        return

    purpose = {
        "level_up": "level_up",
        "learn_expert_skill": "learn_expert_skill",
        "learn_heroic_skill": "learn_heroic_skill",
        "learn_legendary_skill": "learn_legendary_skill",
    }[fork]
    member.xp -= 1
    focus_bonus = consume_training_focus_bonus(session, member.character_id)
    result = perform_advancement_roll(member, purpose=purpose, bonus=focus_bonus)
    if focus_bonus:
        session.log.append(f"{member.name} applies Training Focus (+{focus_bonus}).")
    if show_rolls:
        session.log.append(
            f"Banked {advancement_fork_label(fork).lower()} roll for {member.name}: {result.die_label} = {result.natural}"
            + (f" + {result.modifier} = {result.total}" if result.modifier else "")
            + f" vs Level {member.level}."
        )
    if explain_math:
        session.log.append(advancement_roll_explain(member))
    if advancement_succeeds(result, member.level):
        apply_success(member, fork)
    elif fork == "level_up":
        session.log.append(f"{member.name} fails to advance (needs > {member.level}).")
    else:
        session.log.append(
            f"{member.name} fails to learn the {advancement_fork_label(fork).lower()} (needs > {member.level})."
        )


def spend_classical_training_xp(
    session: SessionState,
    member: PartyMemberState,
    amount: int,
) -> tuple[bool, list[str], int, int]:
    """Spend a hero's assigned XP rolls before drawing from the party's pending rolls."""
    if amount <= 0:
        return True, [], 0, 0
    available = member.xp + session.xp_rolls_pending
    if available < amount:
        return False, [], 0, 0
    remaining = amount
    log: list[str] = []
    banked_take = min(member.xp, remaining)
    if banked_take:
        member.xp -= banked_take
        remaining -= banked_take
        log.append(f"{member.name} spends {banked_take} assigned XP roll(s).")
    if remaining:
        session.xp_rolls_pending -= remaining
        log.append(f"{member.name} spends {remaining} pending party XP roll(s).")
    return True, log, banked_take, remaining


def dungeon_has_final_boss(session: SessionState) -> bool:
    if session.final_boss_defeated or session.final_boss_designated:
        return True
    for tile in session.map_state.tiles:
        enemies = list(tile.enemies) + list(tile.defeated_enemies or [])
        for enemy in enemies:
            if "final_boss" in enemy.tags:
                return True
    return False


def _designate_final_boss(boss: EnemyState) -> None:
    boss.life += 1
    boss.max_life += 1
    boss.attacks += 1
    if "final_boss" not in boss.tags:
        boss.tags.append("final_boss")


def force_final_boss_designation(
    enemies: list[EnemyState],
    *,
    reason: str,
) -> tuple[list[str], EnemyState | None]:
    log: list[str] = [reason]
    majors = [
        enemy
        for enemy in enemies
        if enemy.category in MAJOR_CATEGORIES
        and enemy.life > 0
        and "wandering_spawn" not in enemy.tags
    ]
    if not majors:
        log.append("No living major foe is present to become the Final Boss.")
        return log, None
    boss = majors[0]
    _designate_final_boss(boss)
    log.append(f"{boss.name} is the dungeon Final Boss (+1 Life, +1 attack, fights to the death).")
    return log, boss


def mark_final_boss_candidate(
    enemies: list[EnemyState],
    *,
    major_foes_encountered: int,
    show_rolls: bool,
) -> tuple[list[str], EnemyState | None]:
    log: list[str] = []
    majors = [
        enemy
        for enemy in enemies
        if enemy.category in MAJOR_CATEGORIES
        and enemy.life > 0
        and "wandering_spawn" not in enemy.tags
    ]
    if not majors:
        return log, None
    roll = roll_d6()
    target = roll + major_foes_encountered
    roll_detail = f"d6 = {roll}" if show_rolls else "d6"
    log.append(
        f"Final Boss check: {roll_detail} + {major_foes_encountered} major foes met = {target} "
        f"(need {FINAL_BOSS_ROLL_TARGET}+)."
    )
    if target < FINAL_BOSS_ROLL_TARGET:
        log.append("No Final Boss designation this encounter.")
        return log, None
    boss = majors[0]
    _designate_final_boss(boss)
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
    if majors and defeated_mixed_major_minor(defeated):
        rolls += 2
        names = ", ".join(enemy.name for enemy in majors)
        log.append(
            f"Mixed major+minions encounter cleared ({names}): earned 2 XP rolls (EE p.180)."
        )
        if any(tag == "final_boss" for enemy in majors for tag in enemy.tags):
            rolls += 1
            log.append("Final Boss slain: earned 1 additional XP roll.")
        return XpAwardResult(log, classical_rolls=rolls)
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
