from __future__ import annotations

from typing import Callable, Literal

from ..schemas import PartyMemberState, SessionState
from .experience import tier_for_level
from .class_profiles import barbarian_rage_uses, halfling_luck_points
from .dice import roll_d6, roll_exploding_d6
from ..schemas import EnemyState, PartyMemberState, SessionState
from .class_combat import save_modifier

CombatAbilityChoice = Literal[
    "rage",
    "panache_attack",
    "panache_defense",
    "luck_attack",
    "luck_defense",
    "gnome_gadget",
    "flip_kick",
    "gladiator_parry",
    "bulwark_sacrifice",
    "double_kick",
]
ClassAbilityAction = Literal[
    "paladin_heal",
    "paladin_reroll_save",
    "paladin_summon_steed",
    "halfling_reroll_save",
    "halfling_luck_treasure",
    "acrobat_shift_position",
    "acrobat_distract",
    "acrobat_leap_harm",
    "acrobat_serpent_twist",
    "acrobat_evade",
    "gnome_smokescreen",
    "gnome_gadget_trap",
    "gnome_gadget_door",
    "mushroom_spore_cloud",
    "assassin_hide",
    "illusionist_distract",
]

FOOD_RATION_NAMES = ("food ration", "food rations")


def swashbuckler_panache_max(level: int) -> int:
    return level


def paladin_prayer_points(level: int) -> int:
    return level + 1


def _spent(session: SessionState, field: str, character_id: str) -> int:
    bucket = getattr(session, field)
    return int(bucket.get(character_id, 0))


def rage_uses_remaining(session: SessionState, member: PartyMemberState) -> int:
    if member.class_id.lower() != "barbarian":
        return 0
    return max(0, barbarian_rage_uses(member.level) - _spent(session, "rage_uses_spent", member.character_id))


def luck_points_remaining(session: SessionState, member: PartyMemberState) -> int:
    if member.class_id.lower() != "halfling":
        return 0
    return max(0, halfling_luck_points(member.level) - _spent(session, "luck_points_spent", member.character_id))


def panache_points(session: SessionState, member: PartyMemberState) -> int:
    if member.class_id.lower() != "swashbuckler":
        return 0
    return min(
        swashbuckler_panache_max(member.level),
        int(session.panache_points.get(member.character_id, 0)),
    )


def paladin_prayer_remaining(session: SessionState, member: PartyMemberState) -> int:
    if member.class_id.lower() != "paladin":
        return 0
    return max(0, paladin_prayer_points(member.level) - _spent(session, "paladin_prayer_spent", member.character_id))


def spend_rage_use(session: SessionState, member: PartyMemberState) -> bool:
    if rage_uses_remaining(session, member) <= 0:
        return False
    session.rage_uses_spent[member.character_id] = _spent(session, "rage_uses_spent", member.character_id) + 1
    return True


def spend_luck_point(session: SessionState, member: PartyMemberState) -> bool:
    if luck_points_remaining(session, member) <= 0:
        return False
    session.luck_points_spent[member.character_id] = _spent(session, "luck_points_spent", member.character_id) + 1
    return True


def spend_panache_point(session: SessionState, member: PartyMemberState) -> bool:
    current = panache_points(session, member)
    if current <= 0:
        return False
    session.panache_points[member.character_id] = current - 1
    return True


def spend_paladin_prayer(session: SessionState, member: PartyMemberState, count: int = 1) -> bool:
    if count <= 0 or paladin_prayer_remaining(session, member) < count:
        return False
    session.paladin_prayer_spent[member.character_id] = (
        _spent(session, "paladin_prayer_spent", member.character_id) + count
    )
    return True


def award_panache_kill(session: SessionState, member: PartyMemberState) -> str | None:
    if member.class_id.lower() != "swashbuckler":
        return None
    current = panache_points(session, member)
    maximum = swashbuckler_panache_max(member.level)
    if current >= maximum:
        return None
    session.panache_points[member.character_id] = current + 1
    return f"{member.name} gains Panache ({current + 1}/{maximum})."


def roll_rage_attack_d6() -> tuple[int, list[int]]:
    rolls = [roll_d6() for _ in range(3)]
    return max(rolls), rolls


def rage_damage_multiplier() -> int:
    return 2


def member_has_recoverable_class_ability(session: SessionState, member: PartyMemberState) -> bool:
    character_id = member.character_id
    class_id = member.class_id.lower()
    if class_id == "barbarian" and _spent(session, "rage_uses_spent", character_id) > 0:
        return True
    if class_id == "halfling" and _spent(session, "luck_points_spent", character_id) > 0:
        return True
    if class_id == "paladin" and _spent(session, "paladin_prayer_spent", character_id) > 0:
        return True
    if class_id == "acrobat" and _spent(session, "acrobat_tricks_spent", character_id) > 0:
        return True
    return False


def recover_class_ability(session: SessionState, member: PartyMemberState) -> str | None:
    character_id = member.character_id
    class_id = member.class_id.lower()
    if class_id == "barbarian":
        spent = _spent(session, "rage_uses_spent", character_id)
        if spent > 0:
            session.rage_uses_spent[character_id] = spent - 1
            remaining = rage_uses_remaining(session, member)
            return f"{member.name} recovers 1 rage attack ({remaining} remaining)."
    if class_id == "halfling":
        spent = _spent(session, "luck_points_spent", character_id)
        if spent > 0:
            session.luck_points_spent[character_id] = spent - 1
            remaining = luck_points_remaining(session, member)
            return f"{member.name} recovers 1 Luck point ({remaining} remaining)."
    if class_id == "paladin":
        spent = _spent(session, "paladin_prayer_spent", character_id)
        if spent > 0:
            session.paladin_prayer_spent[character_id] = spent - 1
            remaining = paladin_prayer_remaining(session, member)
            return f"{member.name} recovers 1 prayer point ({remaining} remaining)."
    if class_id == "acrobat":
        spent = _spent(session, "acrobat_tricks_spent", character_id)
        if spent > 0:
            session.acrobat_tricks_spent[character_id] = spent - 1
            remaining = acrobat_tricks_remaining(session, member)
            return f"{member.name} recovers 1 Trick point ({remaining} remaining)."
    return None


def paladin_heal(session: SessionState, paladin: PartyMemberState, target: PartyMemberState) -> list[str]:
    if paladin.class_id.lower() != "paladin":
        return ["Only a paladin may spend prayer points to heal."]
    if paladin.current_life <= 0:
        return [f"{paladin.name} cannot pray while fallen."]
    if target.current_life <= 0:
        return [f"{target.name} is fallen and cannot be healed this way."]
    if target.current_life >= target.max_life:
        return [f"{target.name} is already at full Life."]
    if not spend_paladin_prayer(session, paladin, 1):
        return [f"{paladin.name} has no prayer points remaining."]
    target.current_life += 1
    remaining = paladin_prayer_remaining(session, paladin)
    return [
        f"{paladin.name} spends 1 prayer point; {target.name} heals 1 Life "
        f"({target.current_life}/{target.max_life}, {remaining} prayer points left)."
    ]


def party_has_halfling(party: list[PartyMemberState]) -> bool:
    return any(member.class_id.lower() == "halfling" and member.current_life > 0 for member in party)


def count_food_rations(party: list[PartyMemberState]) -> int:
    total = 0
    for member in party:
        for item in member.inventory:
            if any(name in item.lower() for name in FOOD_RATION_NAMES):
                total += 1
    return total


def consume_food_rations(party: list[PartyMemberState], count: int) -> bool:
    if count <= 0:
        return True
    remaining = count
    for member in party:
        kept: list[str] = []
        for item in member.inventory:
            if remaining > 0 and any(name in item.lower() for name in FOOD_RATION_NAMES):
                remaining -= 1
                continue
            kept.append(item)
        member.inventory = kept
        if remaining <= 0:
            break
    return remaining == 0


def apply_nourishing_meal(
    session: SessionState,
    party: list[PartyMemberState],
    eater_ids: list[str],
) -> list[str]:
    if session.nourishing_meal_used:
        return ["Nourishing Meal has already been used this adventure."]
    if not party_has_halfling(party):
        return ["A living halfling is required to cook a Nourishing Meal."]
    eaters = [member for member in party if member.character_id in eater_ids and member.current_life > 0]
    if not eaters:
        return ["Choose at least one living ally to eat the Nourishing Meal."]
    if not consume_food_rations(party, len(eaters)):
        return [f"Not enough Food rations ({len(eaters)} needed, {count_food_rations(party)} available)."]
    session.nourishing_meal_used = True
    log: list[str] = [f"The halfling cooks a Nourishing Meal for {len(eaters)} ally/allies."]
    for member in eaters:
        if member.current_life < member.max_life:
            member.current_life += 1
            log.append(f"{member.name} eats well (+1 Life, now {member.current_life}/{member.max_life}).")
        else:
            log.append(f"{member.name} eats well (already at full Life).")
        if member.class_id.lower() == "halfling":
            log.append(f"{member.name} recovers 1 Madness from the hearty meal (track manually if using Madness rules).")
    return log


def ability_status_line(session: SessionState, member: PartyMemberState) -> str | None:
    class_id = member.class_id.lower()
    if class_id == "barbarian":
        remaining = rage_uses_remaining(session, member)
        if remaining:
            return f"Rage attacks: {remaining}/{barbarian_rage_uses(member.level)}"
    if class_id == "halfling":
        remaining = luck_points_remaining(session, member)
        if remaining:
            return f"Luck: {remaining}/{halfling_luck_points(member.level)}"
    if class_id == "swashbuckler":
        current = panache_points(session, member)
        maximum = swashbuckler_panache_max(member.level)
        return f"Panache: {current}/{maximum}"
    if class_id == "acrobat":
        remaining = acrobat_tricks_remaining(session, member)
        if remaining:
            return f"Tricks: {remaining}/{acrobat_tricks_max(member.level)}"
    if class_id == "gnome":
        remaining = gnome_gadgets_remaining(session, member)
        if remaining:
            return f"Gadgets: {remaining}/{gnome_gadgets_max(member.level)}"
    if class_id == "mushroom_monk":
        remaining = mushroom_spore_uses_remaining(session, member)
        if remaining:
            return f"Spore uses: {remaining}/{tier_for_level(member.level)}"
    if class_id == "paladin":
        remaining = paladin_prayer_remaining(session, member)
        if remaining:
            return f"Prayer points: {remaining}/{paladin_prayer_points(member.level)}"
    if class_id == "light_gladiator":
        pending = session.gladiator_counter_pending.get(member.character_id)
        if pending:
            bonus = int(pending.get("bonus", 0))
            if bonus > 0:
                return f"Counter-strike ready (+{bonus})"
        if member.character_id not in session.gladiator_counter_used:
            return "Counter-strike available"
    return None


def make_kill_callback(session: SessionState, combat_log: list[str] | None = None) -> Callable[[str], None]:
    def on_kill(killer_id: str) -> None:
        killer = next((member for member in session.party if member.character_id == killer_id), None)
        if killer is None:
            return
        message = award_panache_kill(session, killer)
        if message:
            if combat_log is not None:
                combat_log.append(message)
            else:
                session.log.append(message)

    return on_kill


# --- Acrobat tricks (L+3; rest recovers Tier) ---


def acrobat_tricks_max(level: int) -> int:
    return level + 3


def acrobat_tricks_remaining(session: SessionState, member: PartyMemberState) -> int:
    if member.class_id.lower() != "acrobat":
        return 0
    spent = _spent(session, "acrobat_tricks_spent", member.character_id)
    return max(0, acrobat_tricks_max(member.level) - spent)


def spend_acrobat_trick(session: SessionState, member: PartyMemberState) -> bool:
    if acrobat_tricks_remaining(session, member) <= 0:
        return False
    session.acrobat_tricks_spent[member.character_id] = (
        _spent(session, "acrobat_tricks_spent", member.character_id) + 1
    )
    return True


def recover_acrobat_tricks_on_rest(session: SessionState, member: PartyMemberState) -> str | None:
    if member.class_id.lower() != "acrobat" or member.current_life <= 0:
        return None
    spent = _spent(session, "acrobat_tricks_spent", member.character_id)
    if spent <= 0:
        return None
    tier = tier_for_level(member.level)
    recovered = min(tier, spent)
    session.acrobat_tricks_spent[member.character_id] = spent - recovered
    remaining = acrobat_tricks_remaining(session, member)
    maximum = acrobat_tricks_max(member.level)
    return f"{member.name} recovers {recovered} Trick point(s) while resting ({remaining}/{maximum} remaining)."


def acrobat_shift_position(
    session: SessionState,
    acrobat: PartyMemberState,
    ally: PartyMemberState,
) -> list[str]:
    if acrobat.class_id.lower() != "acrobat":
        return ["Only an acrobat may use Shift Position."]
    if not spend_acrobat_trick(session, acrobat):
        return [f"{acrobat.name} has no Trick points remaining."]
    first, second = acrobat.marching_order, ally.marching_order
    acrobat.marching_order = second
    ally.marching_order = first
    return [
        f"{acrobat.name} spends 1 Trick point to swap places with {ally.name} "
        f"(#{acrobat.marching_order} and #{ally.marching_order})."
    ]


def apply_foe_distraction(
    session: SessionState,
    actor: PartyMemberState,
    enemy: EnemyState,
    *,
    source: str,
) -> list[str]:
    if enemy.category in {"vermin", "weird", "boss"}:
        return [f"{source} does not affect {enemy.name} ({enemy.category})."]
    tier = tier_for_level(actor.level)
    current = session.foe_level_penalties.get(enemy.id, 0)
    if current >= tier:
        return [f"{enemy.name} is already distracted as much as {source} allows."]
    session.foe_level_penalties[enemy.id] = max(current, tier)
    effective = max(1, enemy.level - session.foe_level_penalties[enemy.id])
    return [
        f"{actor.name} spends effort on {source}; {enemy.name} fights at effective L{effective} "
        f"(−{session.foe_level_penalties[enemy.id]} for this encounter)."
    ]


def acrobat_distract(session: SessionState, acrobat: PartyMemberState, enemy: EnemyState) -> list[str]:
    if acrobat.class_id.lower() != "acrobat":
        return ["Only an acrobat may use Distract."]
    if not spend_acrobat_trick(session, acrobat):
        return [f"{acrobat.name} has no Trick points remaining."]
    return apply_foe_distraction(session, acrobat, enemy, source="Distract")


def illusionist_distract(session: SessionState, caster: PartyMemberState, enemy: EnemyState) -> list[str]:
    if caster.class_id.lower() != "illusionist":
        return ["Only an illusionist may use Distracting Lights."]
    if enemy.category in {"vermin", "weird", "boss"} or "undead" in enemy.tags or "artificial" in enemy.tags:
        return [f"Distracting Lights cannot affect {enemy.name}."]
    tier = tier_for_level(caster.level)
    if session.foe_level_penalties.get(enemy.id, 0) >= tier:
        return [f"{enemy.name} is already distracted this encounter."]
    total, rolls = roll_exploding_d6()
    modifier = caster.level
    final_total = total + modifier
    if final_total < enemy.level:
        return [
            f"Distracting Lights fail: d6 {' + '.join(str(value) for value in rolls)} + {modifier} "
            f"= {final_total} vs L{enemy.level}. Cannot retry this encounter."
        ]
    return apply_foe_distraction(session, caster, enemy, source="Distracting Lights")


def acrobat_leap_out_of_harm(session: SessionState, acrobat: PartyMemberState) -> list[str]:
    pending = session.pending_save_reroll
    if not pending or pending.get("character_id") != acrobat.character_id:
        return ["No failed Save is pending for this hero."]
    if pending.get("magical"):
        return ["Leap out of Harm cannot reroll magical dangers."]
    if not spend_acrobat_trick(session, acrobat):
        return [f"{acrobat.name} has no Trick points remaining."]
    level = int(pending["level"])
    total, rolls = roll_exploding_d6()
    modifier = save_modifier(acrobat)
    final_total = total + modifier
    session.pending_save_reroll = None
    log = [
        f"{acrobat.name} spends 1 Trick point — Leap out of Harm: "
        f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{level}."
    ]
    if final_total >= level:
        log.append("The rerolled Save succeeds!")
    else:
        log.append("The rerolled Save still fails.")
    return log


def acrobat_serpent_twist(session: SessionState, acrobat: PartyMemberState) -> list[str]:
    if not spend_acrobat_trick(session, acrobat):
        return [f"{acrobat.name} has no Trick points remaining."]
    session.skip_parting_flee = True
    return [
        f"{acrobat.name} uses Serpent Twist to slip free (1 Trick point). "
        "The party may flee without parting blows this round."
    ]


# --- Gnome gadgets (L+6 per adventure) ---


def gnome_gadgets_max(level: int) -> int:
    return level + 6


def gnome_gadgets_remaining(session: SessionState, member: PartyMemberState) -> int:
    if member.class_id.lower() != "gnome":
        return 0
    spent = _spent(session, "gnome_gadgets_spent", member.character_id)
    return max(0, gnome_gadgets_max(member.level) - spent)


def spend_gnome_gadgets(session: SessionState, member: PartyMemberState, count: int = 1) -> bool:
    if count <= 0 or gnome_gadgets_remaining(session, member) < count:
        return False
    session.gnome_gadgets_spent[member.character_id] = (
        _spent(session, "gnome_gadgets_spent", member.character_id) + count
    )
    return True


def gnome_smokescreen(session: SessionState, gnome: PartyMemberState) -> list[str]:
    if gnome.class_id.lower() != "gnome":
        return ["Only a gnome may deploy a smokescreen."]
    if not spend_gnome_gadgets(session, gnome, 1):
        return [f"{gnome.name} has no gadget points remaining."]
    session.gnome_smokescreen_ready = True
    session.skip_parting_flee = True
    return [
        f"{gnome.name} readies a smokescreen bomb (1 gadget point). "
        "The next flee skips parting attacks."
    ]


# --- Mushroom monk spores ---


def mushroom_spore_uses_remaining(session: SessionState, member: PartyMemberState) -> int:
    if member.class_id.lower() != "mushroom_monk":
        return 0
    tier = tier_for_level(member.level)
    used = _spent(session, "mushroom_spore_uses", member.character_id)
    return max(0, tier - used)


def mushroom_spore_cloud(
    session: SessionState,
    monk: PartyMemberState,
    enemies: list[EnemyState],
) -> list[str]:
    if monk.class_id.lower() != "mushroom_monk":
        return ["Only a mushroom monk may spray spores."]
    if mushroom_spore_uses_remaining(session, monk) <= 0:
        return [f"{monk.name} has no spore uses remaining this adventure."]
    living = [enemy for enemy in enemies if enemy.life > 0]
    minors = [
        enemy
        for enemy in living
        if enemy.category in {"vermin", "minions"}
        and "fungal" not in " ".join(enemy.tags).lower()
        and "undead" not in enemy.tags
    ]
    if not minors:
        return ["No eligible minor foes are here to affect."]
    session.mushroom_spore_uses[monk.character_id] = (
        _spent(session, "mushroom_spore_uses", monk.character_id) + 1
    )
    log = [f"{monk.name} sprays spores (1 turn; {mushroom_spore_uses_remaining(session, monk)} uses left)."]
    for enemy in minors:
        current = session.foe_level_penalties.get(enemy.id, 0)
        session.foe_level_penalties[enemy.id] = max(current, 1)
        effective = max(1, enemy.level - session.foe_level_penalties[enemy.id])
        log.append(f"{enemy.name} fights at effective L{effective} (−1 from spores).")
    return log


# --- Assassin hide ---


def assassin_hide(
    session: SessionState,
    assassin: PartyMemberState,
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
) -> list[str]:
    if assassin.class_id.lower() != "assassin":
        return ["Only an assassin may hide in shadows."]
    if session.assassin_hidden_id:
        return ["An assassin is already hidden."]
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return ["No foes to hide from."]
    foe_level = max(enemy.level for enemy in living)
    total, rolls = roll_exploding_d6()
    modifier = assassin.level
    final_total = total + modifier
    log: list[str] = []
    if show_rolls:
        log.append(
            f"Hide in Shadows: {assassin.name} rolls {' + '.join(str(value) for value in rolls)} "
            f"+ {modifier} = {final_total} vs L{foe_level}."
        )
    if final_total < foe_level:
        log.append("Stealth fails — a foe strikes before you can hide!")
        session.foes_strike_first = True
        session.reaction_pending = False
        return log
    session.assassin_hidden_id = assassin.character_id
    session.assassin_mark_enemy_id = living[0].id
    log.append(
        f"{assassin.name} melts into the shadows. Next attack vs {living[0].name} inflicts triple damage if it hits."
    )
    return log


def clear_assassin_mark(session: SessionState) -> None:
    session.assassin_hidden_id = None
    session.assassin_mark_enemy_id = None


def reroll_failed_save_with_luck(
    session: SessionState,
    member: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> tuple[list[str], bool]:
    pending = session.pending_save_reroll
    if not pending or pending.get("character_id") != member.character_id:
        return ["No failed Save is pending for this hero."], False
    if member.class_id.lower() == "halfling":
        if not spend_luck_point(session, member):
            return [f"{member.name} has no Luck points remaining."], False
        spend_label = "1 Luck point"
    elif member.class_id.lower() == "paladin":
        if not spend_paladin_prayer(session, member, 1):
            return [f"{member.name} has no prayer points remaining."], False
        spend_label = "1 prayer point"
    else:
        return ["This hero cannot reroll the pending Save."], False
    level = int(pending["level"])
    total, rolls = roll_exploding_d6()
    modifier = save_modifier(member)
    final_total = total + modifier
    log: list[str] = []
    if show_rolls:
        log.append(
            f"Save reroll ({spend_label}): {member.name} rolls "
            f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{level}."
        )
    session.pending_save_reroll = None
    succeeded = final_total >= level
    if succeeded:
        log.append("The rerolled Save succeeds!")
    else:
        log.append("The rerolled Save still fails.")
    return log, succeeded


def effective_foe_level(enemy: EnemyState, penalties: dict[str, int]) -> int:
    penalty = penalties.get(enemy.id, 0)
    return max(1, enemy.level - penalty)


def gnome_trap_disarm_modifier(gnome: PartyMemberState, gadget_points: int = 0) -> int:
    """Gadgeteer +L on trap disarm; spent gadgets add +1 each."""
    if gnome.class_id.lower() != "gnome":
        return 0
    return gnome.level * 2 + max(0, gadget_points)


def attempt_gnome_trap_disarm(
    session: SessionState,
    gnome: PartyMemberState,
    trap_level: int,
    *,
    gadget_points: int = 0,
    show_rolls: bool = True,
) -> tuple[bool, list[str]]:
    if gnome.class_id.lower() != "gnome":
        return False, ["Only a gnome may use gadgets to disarm traps."]
    if gadget_points > 0 and not spend_gnome_gadgets(session, gnome, gadget_points):
        return False, [f"{gnome.name} has insufficient gadget points ({gadget_points} needed)."]
    total, rolls = roll_exploding_d6()
    modifier = gnome_trap_disarm_modifier(gnome, gadget_points)
    final_total = total + modifier
    log: list[str] = []
    if show_rolls:
        spend_note = f" ({gadget_points} gadget point(s))" if gadget_points else ""
        log.append(
            f"Gnome disarm{spend_note}: {gnome.name} rolls "
            f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{trap_level}."
        )
    if rolls[0] == 1:
        log.append("Natural 1 — the trap is triggered.")
        return False, log
    if final_total >= trap_level:
        log.append(f"{gnome.name} disarms the trap with a gadget.")
        return True, log
    log.append(f"{gnome.name} fails to disarm the trap.")
    return False, log


def attempt_gnome_gadget_door(
    session: SessionState,
    gnome: PartyMemberState,
    door_level: int,
    *,
    gadget_points: int,
    show_rolls: bool = True,
) -> tuple[bool, list[str]]:
    if gnome.class_id.lower() != "gnome":
        return False, ["Only a gnome may spend gadgets on locks."]
    if gadget_points < 1:
        return False, ["Spend at least 1 gadget point."]
    if not spend_gnome_gadgets(session, gnome, gadget_points):
        return False, [f"{gnome.name} has insufficient gadget points."]
    total, rolls = roll_exploding_d6()
    modifier = gnome.level + gadget_points
    final_total = total + modifier
    level = max(1, door_level or 6)
    log: list[str] = []
    if show_rolls:
        log.append(
            f"Gnome lock gadget: {gnome.name} rolls "
            f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{level}."
        )
    if rolls[0] == 1:
        log.append("Natural 1 — the mechanism jams noisily.")
        return False, log
    if final_total >= level:
        log.append(f"{gnome.name} opens the lock with a gadget.")
        return True, log
    log.append("The lock holds.")
    return False, log


def acrobat_evade(session: SessionState, acrobat: PartyMemberState) -> list[str]:
    if acrobat.class_id.lower() != "acrobat":
        return ["Only an acrobat may Evade."]
    if not spend_acrobat_trick(session, acrobat):
        return [f"{acrobat.name} has no Trick points remaining."]
    session.evasion_character_ids.append(acrobat.character_id)
    return [
        f"{acrobat.name} spends 1 Trick point to Evade — foes cannot reach them in melee this round."
    ]


def open_lever_door_with_gnome_gadget(session: SessionState, gnome: PartyMemberState) -> list[str]:
    if gnome.class_id.lower() != "gnome":
        return ["Only a gnome may trip a lever with a gadget."]
    if not spend_gnome_gadgets(session, gnome, 1):
        return [f"{gnome.name} has no gadget points remaining."]
    return [f"{gnome.name} spends 1 gadget point; the lever mechanism releases."]
