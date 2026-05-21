from __future__ import annotations

from typing import Callable, Literal

from ..schemas import PartyMemberState, SessionState
from .class_profiles import barbarian_rage_uses, halfling_luck_points
from .dice import roll_d6

CombatAbilityChoice = Literal["rage", "panache_attack", "panache_defense", "luck_attack"]
ClassAbilityAction = Literal["paladin_heal", "paladin_reroll_save", "paladin_summon_steed"]

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
    if class_id == "paladin":
        remaining = paladin_prayer_remaining(session, member)
        if remaining:
            return f"Prayer points: {remaining}/{paladin_prayer_points(member.level)}"
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
