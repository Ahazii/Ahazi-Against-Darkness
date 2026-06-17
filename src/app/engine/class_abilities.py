from __future__ import annotations

from typing import Callable, Literal

from ..schemas import PartyMemberState, SessionState
from .experience import tier_for_level
from .class_profiles import barbarian_rage_uses, halfling_luck_points
from .expert_skill_effects import effective_barbarian_rage_uses
from .dice import roll_d6, roll_exploding_for_level, tier_die_label
from ..schemas import EnemyState, PartyMemberState, SessionState
from .class_combat import save_modifier
from .weapons import mushroom_monk_flurry_eligible

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
    "acrobat_knife_throw",
    "illusionist_knife_throw",
    "illusionist_continual_light",
]
ClassAbilityAction = Literal[
    "paladin_heal",
    "paladin_reroll_save",
    "paladin_summon_steed",
    "halfling_reroll_save",
    "halfling_luck_treasure",
    "halfling_luck_search",
    "acrobat_shift_position",
    "acrobat_distract",
    "acrobat_leap_harm",
    "acrobat_serpent_twist",
    "acrobat_evade",
    "gnome_smokescreen",
    "gnome_gadget_trap",
    "gnome_gadget_door",
    "gnome_gadget_free",
    "mushroom_spore_cloud",
    "assassin_hide",
    "illusionist_distract",
    "illusionist_continual_light",
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
    return max(
        0,
        effective_barbarian_rage_uses(member.level, member)
        - _spent(session, "rage_uses_spent", member.character_id),
    )


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


def bulwark_magical_healing_blocked(session: SessionState, target: PartyMemberState) -> str | None:
    if target.class_id.lower() != "bulwark":
        return None
    if target.current_life <= 1:
        return None
    others_wounded = any(
        member.current_life > 0
        and member.current_life < member.max_life
        and member.class_id.lower() != "bulwark"
        for member in session.party
    )
    if others_wounded:
        return (
            f"{target.name} cannot receive magical healing while other heroes are wounded "
            "(bulwark Limited Healing — bandages still work; at 1 Life the bulwark may be prioritized)."
        )
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
    blocked = bulwark_magical_healing_blocked(session, target)
    if blocked:
        return [blocked]
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
            from .madness import heal_madness

            healed = heal_madness(member, 1)
            if healed:
                log.append(f"{member.name} recovers {healed} Madness from the hearty meal.")
    return log


def ability_status_line(session: SessionState, member: PartyMemberState) -> str | None:
    class_id = member.class_id.lower()
    if class_id == "barbarian":
        remaining = rage_uses_remaining(session, member)
        if remaining:
            return f"Rage attacks: {remaining}/{effective_barbarian_rage_uses(member.level, member)}"
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
        tier = tier_for_level(member.level)
        wielded = (session.wielded_melee_weapons or {}).get(member.character_id) or member.default_melee_weapon
        flurry = mushroom_monk_flurry_eligible(member, wielded=wielded)
        parts: list[str] = []
        if flurry:
            parts.append(f"Flurry: {tier} attack(s) (unarmed/nunchaku/stars)")
        if remaining:
            parts.append(f"Spore uses: {remaining}/{tier}")
        return " · ".join(parts) if parts else None
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


def illusionist_distract(
    session: SessionState,
    caster: PartyMemberState,
    enemy: EnemyState,
    *,
    all_enemies: list[EnemyState] | None = None,
) -> list[str]:
    if caster.class_id.lower() != "illusionist":
        return ["Only an illusionist may use Distracting Lights."]
    if enemy.category in {"vermin", "weird", "boss"} or "undead" in enemy.tags or "artificial" in enemy.tags:
        return [f"Distracting Lights cannot affect {enemy.name}."]
    tier = tier_for_level(caster.level)
    if session.foe_level_penalties.get(enemy.id, 0) >= tier and enemy.category != "minions":
        return [f"{enemy.name} is already distracted this encounter."]
    total, rolls = roll_exploding_for_level(caster.level)
    modifier = caster.level
    final_total = total + modifier
    if final_total < enemy.level:
        return [
            f"Distracting Lights fail: {tier_die_label(caster.level)} {' + '.join(str(value) for value in rolls)} + {modifier} "
            f"= {final_total} vs L{enemy.level}. Cannot retry this encounter."
        ]
    if enemy.category == "minions":
        pool = all_enemies or [enemy]
        minions = [foe for foe in pool if foe.category == "minions" and foe.life > 0]
        logs: list[str] = []
        for minion in minions:
            if session.foe_level_penalties.get(minion.id, 0) >= tier:
                continue
            logs.extend(apply_foe_distraction(session, caster, minion, source="Distracting Lights"))
        if logs:
            return logs
        return [f"The minion group is already distracted this encounter."]
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
    total, rolls = roll_exploding_for_level(acrobat.level)
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
    target_foe_id: str | None = None,
) -> list[str]:
    if assassin.class_id.lower() != "assassin":
        return ["Only an assassin may hide in shadows."]
    if session.assassin_hidden_id:
        return ["An assassin is already hidden."]
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return ["No foes to hide from."]
    foe_level = max(enemy.level for enemy in living)
    modifier = assassin.level
    total, rolls = roll_exploding_for_level(assassin.level)
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
    mark = next((enemy for enemy in living if enemy.id == target_foe_id), living[0])
    session.assassin_mark_enemy_id = mark.id
    log.append(
        f"{assassin.name} melts into the shadows. Next attack vs {mark.name} inflicts triple damage if it hits."
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
    total, rolls = roll_exploding_for_level(member.level)
    modifier = int(pending.get("modifier", save_modifier(member)))
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
    total, rolls = roll_exploding_for_level(gnome.level)
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
    total, rolls = roll_exploding_for_level(gnome.level)
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


def acrobat_graceful_move(session: SessionState, acrobat: PartyMemberState) -> list[str]:
    if acrobat.class_id.lower() != "acrobat":
        return ["Only an acrobat may use Graceful Move."]
    if not spend_acrobat_trick(session, acrobat):
        return [f"{acrobat.name} has no Trick points remaining."]
    session.graceful_save_reroll_id = acrobat.character_id
    return [
        f"{acrobat.name} spends 1 Trick point on Graceful Move — may reroll the next failed social Save."
    ]


HYPHAE_CHOICES = frozenset({"search", "clue", "secret_door", "secret_passage"})


def mushroom_hyphae_communion(
    session: SessionState,
    monk: PartyMemberState,
    *,
    environment: str,
    choice: str = "search",
) -> tuple[list[str], str | None]:
    if monk.class_id.lower() != "mushroom_monk":
        return ["Only a mushroom monk may commune with hyphae."], None
    if monk.character_id in session.hyphae_used:
        return [f"{monk.name} already used Hyphae this adventure."], None
    if environment not in {"fungal_grottoes", "wilderness"}:
        return ["Hyphae communion requires fungal grottoes or wilderness."], None
    effect = choice if choice in HYPHAE_CHOICES else "search"
    session.hyphae_used.append(monk.character_id)
    log = [f"{monk.name} sends hyphae into the ground (1 turn)."]
    if effect == "search":
        session.hyphae_search_bonus_id = monk.character_id
        log.append("The next Search on this tile gains +1.")
        return log, None
    if effect == "clue":
        monk.clues += 1
        session.clues_found = sum(max(0, member.clues) for member in session.party)
        log.append(
            f"The mycelium whispers a Clue to {monk.name} "
            f"({monk.clues} carried; {session.clues_found} party total)."
        )
        return log, None
    if effect == "secret_door":
        log.append("Hyphae map a hidden door on this tile.")
        return log, "secret_door"
    log.append("Hyphae trace a secret passage from this tile.")
    return log, "secret_passage"


def foe_is_mounted(enemy: EnemyState) -> bool:
    text = f"{enemy.name} {(enemy.description or '')}".lower()
    return any(token in text for token in ("mounted", "rider", "cavalry", " boar ", "horseman", "horse-back"))


def paladin_mounted_attack_bonus(session: SessionState, paladin: PartyMemberState, *, outdoors: bool, target: EnemyState) -> int:
    if paladin.class_id.lower() != "paladin":
        return 0
    if session.paladin_steed_active_id != paladin.character_id:
        return 0
    if not outdoors or foe_is_mounted(target):
        return 0
    return 1


def paladin_summon_steed(session: SessionState, paladin: PartyMemberState) -> list[str]:
    if paladin.class_id.lower() != "paladin":
        return ["Only a paladin may summon a steed."]
    if session.mode == "combat":
        return ["Cannot summon a steed during combat."]
    if not spend_paladin_prayer(session, paladin, 1):
        return [f"{paladin.name} has no prayer points remaining."]
    session.paladin_steed_active_id = paladin.character_id
    return [
        f"{paladin.name} spends 1 prayer point to summon a steed for one day "
        "(outdoors only — mounted attacks vs non-mounted foes at +1)."
    ]


def caster_has_free_spell_slot(session: SessionState, member: PartyMemberState) -> bool:
    from .class_profiles import spell_slot_count

    max_slots = spell_slot_count(member.class_id.lower(), member.level)
    if max_slots is None:
        return False
    used = len(session.expended_spells.get(member.character_id, []))
    return used < max_slots


def spend_caster_spell_slot(session: SessionState, member: PartyMemberState, *, label: str = "spell slot") -> bool:
    if not caster_has_free_spell_slot(session, member):
        return False
    expended = list(session.expended_spells.get(member.character_id, []))
    expended.append(label)
    session.expended_spells[member.character_id] = expended
    return True


def illusionist_continual_light(session: SessionState, illusionist: PartyMemberState) -> list[str]:
    if illusionist.class_id.lower() != "illusionist":
        return ["Only an illusionist may cast Continual Light."]
    if illusionist.current_life <= 0:
        return [f"{illusionist.name} cannot cast while fallen."]
    session.continual_light_owner_id = illusionist.character_id
    if "Continual Light" not in illusionist.statuses:
        illusionist.statuses.append("Continual Light")
    return [
        f"{illusionist.name} casts Continual Light on a worn item — hands-free light until separated or fallen."
    ]


def member_has_lockpicks(member: PartyMemberState) -> bool:
    return any("lockpick" in item.lower() or "lock-pick" in item.lower() for item in member.inventory)


def lockpick_door_bonus(member: PartyMemberState) -> int:
    class_id = member.class_id.lower()
    if class_id == "rogue":
        return member.level
    if class_id == "kukla":
        return member.level // 2
    return 0


def gnome_gadget_free_prisoner(
    session: SessionState,
    gnome: PartyMemberState,
    target: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    if gnome.class_id.lower() != "gnome":
        return ["Only a gnome may use gadgets to free prisoners."]
    if target.character_id == gnome.character_id:
        return ["A gnome cannot free themselves with this gadget."]
    if target.current_life <= 0:
        return [f"{target.name} is fallen and cannot be freed this way."]
    if not spend_gnome_gadgets(session, gnome, 1):
        return [f"{gnome.name} has no gadget points remaining."]
    level = 6
    modifier = gnome.level + save_modifier(gnome)
    total, rolls = roll_exploding_for_level(gnome.level)
    final_total = total + modifier
    log: list[str] = [f"{gnome.name} spends 1 gadget point to free {target.name} from restraints (1 turn)."]
    if show_rolls:
        log.append(
            f"Gadget free attempt: {' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{level}."
        )
    if rolls[0] == 1:
        log.append("The restraints are beyond the gnome's gadgets.")
        return log
    if final_total >= level:
        target.statuses = [item for item in target.statuses if item.lower() not in {"restrained", "chained", "bound"}]
        log.append(f"{gnome.name} frees {target.name} from restraints.")
        return log
    log.append(f"{gnome.name} fails to free {target.name} — may try again next turn.")
    return log


def kukla_deploy_dolls(session: SessionState, kukla: PartyMemberState) -> list[str]:
    from .expert_skill_effects import has_skill

    if kukla.class_id.lower() != "kukla":
        return ["Only a kukla may deploy dolls."]
    if not has_skill(kukla, "army_of_dolls"):
        return [f"{kukla.name} has not learned Army of Dolls."]
    if kukla.character_id in session.army_of_dolls_deployed:
        return [f"{kukla.name} already deployed dolls this adventure."]
    session.army_of_dolls_deployed.append(kukla.character_id)
    session.kukla_doll_active.append(kukla.character_id)
    return [
        f"{kukla.name} deploys a fighting doll (L1 minion ally, −1 Attack each combat round this adventure)."
    ]


def kukla_doll_round_attacks(
    session: SessionState,
    kukla: PartyMemberState,
    target,
    *,
    show_rolls: bool = True,
) -> list[str]:
    from .combat import attack_hits

    if kukla.character_id not in session.kukla_doll_active:
        return []
    if kukla.current_life <= 0 or target is None or target.life <= 0:
        return []
    total, rolls = roll_exploding_for_level(1)
    modifier = -1
    final_total = total + modifier
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{kukla.name}'s doll attacks {target.name}: "
            f"{' + '.join(str(value) for value in rolls)} − 1 = {final_total} vs L{target.level}."
        )
    if attack_hits(final_total, target.level):
        target.life = max(0, target.life - 1)
        log.append(f"The fighting doll hits {target.name} for 1 damage.")
        if target.life <= 0:
            log.append(f"{target.name} is defeated.")
    else:
        log.append(f"The fighting doll misses {target.name}.")
    return log


def _inventory_has_ring(member: PartyMemberState, color: str) -> bool:
    needle = f"{color} ring"
    return any(needle in item.lower() for item in member.inventory)


def _consume_ring(member: PartyMemberState, color: str) -> bool:
    needle = f"{color} ring"
    for index, item in enumerate(member.inventory):
        if needle in item.lower():
            member.inventory.pop(index)
            return True
    return False


def kukla_green_ring_revive(
    session: SessionState,
    actor: PartyMemberState,
    target: PartyMemberState,
    tile,
    *,
    show_rolls: bool = True,
) -> list[str]:
    if target.class_id.lower() != "kukla":
        return ["The green ring revives only a fallen kukla."]
    if target.current_life > 0:
        return [f"{target.name} is not fallen."]
    if target.character_id not in (tile.fallen_character_ids or []):
        return ["The kukla must be fallen on this tile."]
    ring_holder = target if _inventory_has_ring(target, "green") else actor
    if not _inventory_has_ring(ring_holder, "green"):
        return ["No green ring is available (check the kukla's inventory)."]
    if not _consume_ring(ring_holder, "green"):
        return ["No green ring is available (check the kukla's inventory)."]
    target.current_life = max(1, target.max_life // 2)
    target.statuses = [status for status in target.statuses if status.lower() not in {"fallen", "dead"}]
    tile.fallen_character_ids = [
        cid for cid in (tile.fallen_character_ids or []) if cid != target.character_id
    ]
    log = [
        f"{actor.name} uses the green ring's fluid — {target.name} is restored with {target.current_life} Life."
    ]
    if show_rolls:
        log.append("Green ring consumed (one use per ring).")
    return log


def kukla_red_ring_poison(
    session: SessionState,
    actor: PartyMemberState,
    target,
    *,
    show_rolls: bool = True,
) -> list[str]:
    if actor.class_id.lower() != "kukla":
        return ["Only a kukla may use the red ring poison."]
    if target is None or target.life <= 0:
        return ["Choose a living foe to poison."]
    if not _inventory_has_ring(actor, "red"):
        return [f"{actor.name} no longer carries the red ring."]
    if not _consume_ring(actor, "red"):
        return [f"{actor.name} no longer carries the red ring."]
    poison_level = max(8, actor.level + 2)
    total, rolls = roll_exploding_for_level(target.level)
    log = [f"{actor.name} slips the red ring's poison to {target.name}."]
    if show_rolls:
        log.append(
            f"Ingestive poison Save: {target.name} rolls "
            f"{' + '.join(str(value) for value in rolls)} = {total} vs L{poison_level}."
        )
    if total >= poison_level:
        log.append(f"{target.name} resists the poison.")
        return log
    target.life = max(0, target.life - 2)
    if "poisoned" not in [tag.lower() for tag in target.tags]:
        target.tags.append("poisoned")
    log.append(f"{target.name} takes 2 damage and is poisoned.")
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
    return log


def _kukla_compartment_ration_count(member: PartyMemberState) -> int:
    return sum(1 for item in member.kukla_compartment_items if "ration" in item.lower())


def _kukla_compartment_small_count(member: PartyMemberState) -> int:
    return sum(
        1
        for item in member.kukla_compartment_items
        if "ration" not in item.lower() and "gem" not in item.lower() and "jewel" not in item.lower()
    )


def kukla_compartment_stash(
    member: PartyMemberState,
    item_name: str,
    *,
    gold_amount: int | None = None,
) -> list[str]:
    if member.class_id.lower() != "kukla":
        return ["Only a kukla has a secret torso compartment."]
    if member.current_life <= 0:
        return [f"{member.name} cannot use the secret compartment while fallen."]
    if gold_amount is not None and gold_amount > 0:
        if gold_amount > member.gold:
            return [f"{member.name} does not carry that much gold."]
        remaining = 100 - member.kukla_compartment_gold
        if gold_amount > remaining:
            return [f"The compartment holds at most 100gp in coins ({remaining}gp space left)."]
        member.gold -= gold_amount
        member.kukla_compartment_gold += gold_amount
        return [f"{member.name} hides {gold_amount}gp in the secret compartment."]
    if not item_name:
        return ["Choose an item to stash."]
    if item_name not in member.inventory:
        return [f"{member.name} does not carry {item_name}."]
    lower = item_name.lower()
    if "gem" in lower or "jewel" in lower:
        member.inventory.remove(item_name)
        member.kukla_compartment_items.append(item_name)
        return [f"{member.name} hides {item_name} in the secret compartment."]
    if "ration" in lower:
        if _kukla_compartment_ration_count(member) >= 5:
            return ["The compartment already holds 5 food rations."]
        member.inventory.remove(item_name)
        member.kukla_compartment_items.append(item_name)
        return [f"{member.name} hides {item_name} in the secret compartment."]
    if _kukla_compartment_small_count(member) >= 10:
        return ["The compartment already holds 10 small items."]
    member.inventory.remove(item_name)
    member.kukla_compartment_items.append(item_name)
    return [f"{member.name} hides {item_name} in the secret compartment (theft-proof while alive)."]


def kukla_compartment_retrieve(member: PartyMemberState, item_name: str) -> list[str]:
    if member.class_id.lower() != "kukla":
        return ["Only a kukla has a secret torso compartment."]
    if not item_name:
        return ["Choose an item to retrieve."]
    if item_name not in member.kukla_compartment_items:
        return [f"The compartment does not contain {item_name}."]
    member.kukla_compartment_items.remove(item_name)
    member.inventory.append(item_name)
    return [f"{member.name} retrieves {item_name} from the secret compartment."]


def kukla_compartment_retrieve_gold(member: PartyMemberState, gold_amount: int) -> list[str]:
    if member.class_id.lower() != "kukla":
        return ["Only a kukla has a secret torso compartment."]
    if gold_amount <= 0 or gold_amount > member.kukla_compartment_gold:
        return ["Choose a valid gold amount from the compartment."]
    member.kukla_compartment_gold -= gold_amount
    member.gold += gold_amount
    return [f"{member.name} retrieves {gold_amount}gp from the secret compartment."]


def resolve_social_save(
    session: SessionState,
    member: PartyMemberState,
    level: int,
    *,
    show_rolls: bool = True,
    label: str = "social",
) -> tuple[bool, list[str]]:
    from .class_combat import save_modifier

    log: list[str] = []
    modifier = save_modifier(member)
    total, rolls = roll_exploding_for_level(member.level)
    final_total = total + modifier

    def roll_line(prefix: str) -> None:
        if not show_rolls:
            return
        detail = f" {' + '.join(str(value) for value in rolls)}"
        if modifier:
            detail += f" + {modifier}"
        log.append(f"{prefix}: {member.name} rolls{detail} = {final_total} vs L{level}.")

    roll_line(f"{label.title()} Save")
    succeeded = rolls[0] != 1 and final_total >= level
    if succeeded:
        log.append(f"{member.name} succeeds.")
        return True, log

    if session.graceful_save_reroll_id == member.character_id:
        session.graceful_save_reroll_id = None
        total, rolls = roll_exploding_for_level(member.level)
        final_total = total + modifier
        roll_line("Graceful Move reroll")
        if rolls[0] != 1 and final_total >= level:
            log.append(f"{member.name} impresses with Graceful Move.")
            return True, log
        log.append(f"{member.name} still fails the {label} Save.")

    log.append(f"{member.name} fails the {label} Save.")
    return False, log
