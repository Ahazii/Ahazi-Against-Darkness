"""Fungal grottoes trap helpers (EE p.166)."""

from __future__ import annotations

import re

from ..schemas import PartyMemberState

FUNGAL_TRAP_KEYS = frozenset(
    {
        "sleep_spores",
        "spore_cloud",
        "slime_patch",
        "mycelium_snare",
        "shrieking_mushroom",
        "cordyceps_trap",
    }
)

SHRIEKING_MUSHROOM_FORESTER_CLASSES = frozenset({"ranger", "druid"})

CORDYCEPS_INFECTED_PREFIX = "Cordyceps infected"
CORDYCEPS_VICTIM_STATUS = "Cordyceps victim"
SLIME_PATCH_SKIP_STATUS = "Slime patch skip (1 turn)"

MYCELIUM_SNARE_HELD_KEYWORDS = (
    "shield",
    "lantern",
    "torch",
    "bow",
    "crossbow",
    "weapon",
    "dagger",
    "sword",
    "axe",
    "staff",
    "rod",
    "wand",
    "mace",
    "hammer",
    "spear",
    "sling",
    "nunchaku",
    "sai",
    "bo",
    "hand",
    "light",
)


def mycelium_snare_held_objects(member: PartyMemberState) -> list[str]:
    """Objects the snared PC may choose to lose (PDF p.166: shield, weapon, lantern, etc.)."""
    choices: list[str] = []
    seen: set[str] = set()
    for attr in ("default_melee_weapon", "default_missile_weapon", "default_melee_weapon_secondary"):
        item = getattr(member, attr, None)
        if item and item not in seen:
            choices.append(item)
            seen.add(item)
    for item in member.inventory:
        if item in seen:
            continue
        lower = item.lower()
        if any(keyword in lower for keyword in MYCELIUM_SNARE_HELD_KEYWORDS):
            choices.append(item)
            seen.add(item)
    return choices


def resolve_mycelium_snare_item_choice(choices: list[str], item_name: str) -> str | None:
    if item_name in choices:
        return item_name
    lowered = item_name.strip().lower()
    for choice in choices:
        if choice.lower() == lowered:
            return choice
    return None


def lose_mycelium_snare_object(member: PartyMemberState, item_name: str) -> str:
    for attr in ("default_melee_weapon", "default_missile_weapon", "default_melee_weapon_secondary"):
        if getattr(member, attr, None) == item_name:
            setattr(member, attr, None)
    try:
        member.inventory.remove(item_name)
    except ValueError:
        pass
    return item_name


def is_fungal_spore_immune(member: PartyMemberState) -> bool:
    class_id = member.class_id.lower()
    return class_id == "mushroom_monk" or any(
        tag in class_id for tag in ("undead", "elemental", "construct", "artificial")
    )


def fungal_trap_save_bonus(member: PartyMemberState, trap_key: str) -> int | None:
    """PDF p.166 save bonuses; None means use generic trap/poison saves."""
    if trap_key not in {"sleep_spores", "spore_cloud", "cordyceps_trap"}:
        return None
    class_id = member.class_id.lower()
    if class_id in {"halfling", "barbarian"}:
        return member.level
    return member.level // 2


def shrieking_mushroom_chance_reduction(member: PartyMemberState) -> int:
    class_id = member.class_id.lower()
    reduction = 0
    if class_id == "halfling" or class_id in SHRIEKING_MUSHROOM_FORESTER_CLASSES:
        reduction = max(reduction, 2)
    if class_id in {"rogue", "assassin"}:
        reduction = max(reduction, 1)
    return reduction


def cordyceps_infected_turns(member: PartyMemberState) -> int | None:
    for status in member.statuses:
        lower = status.lower()
        if not lower.startswith(CORDYCEPS_INFECTED_PREFIX.lower()):
            continue
        match = re.search(r"(\d+)\s+turns?", status, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 6
    return None


def tick_cordyceps_infection(member: PartyMemberState) -> bool:
    """Decrement cordyceps turns; return True when the infection expires."""
    updated: list[str] = []
    expired = False
    for status in member.statuses:
        lower = status.lower()
        if not lower.startswith(CORDYCEPS_INFECTED_PREFIX.lower()):
            updated.append(status)
            continue
        match = re.search(r"(\d+)\s+turns?", status, re.IGNORECASE)
        turns = int(match.group(1)) if match else 6
        remaining = turns - 1
        if remaining > 0:
            updated.append(f"{CORDYCEPS_INFECTED_PREFIX} ({remaining} turns)")
        else:
            expired = True
    member.statuses = updated
    return expired


def clear_cordyceps_infection(member: PartyMemberState) -> bool:
    before = len(member.statuses)
    member.statuses = [
        status
        for status in member.statuses
        if not status.lower().startswith(CORDYCEPS_INFECTED_PREFIX.lower())
    ]
    return len(member.statuses) < before


def resolve_cordyceps_mind_control_attack(
    infected: PartyMemberState,
    target: PartyMemberState,
    *,
    show_rolls: bool,
    explain_math: bool,
) -> tuple[list[str], bool]:
    from .class_combat import armor_defense_bonus, defense_modifier
    from .combat import defense_succeeds
    from .dice import roll_exploding_for_level

    total, rolls = roll_exploding_for_level(target)
    modifier = defense_modifier(target, None) + armor_defense_bonus(target)
    final_total = total + modifier
    attack_level = infected.level
    log: list[str] = []
    if show_rolls:
        log.append(
            f"Cordyceps attack: {infected.name} (L{attack_level}) forces {target.name} to defend: "
            f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total}."
        )
    if explain_math:
        log.append(f"Cordyceps defense math: need total > {attack_level} to avoid damage.")
    if defense_succeeds(final_total, attack_level, natural=rolls[0]):
        log.append(f"{target.name} defends against {infected.name}'s cordyceps-driven attack.")
        return log, False
    target.current_life = max(0, target.current_life - 1)
    log.append(f"{target.name} takes 1 Life from {infected.name}'s cordyceps-driven attack.")
    killed = target.current_life == 0
    if killed:
        log.append(f"{target.name} falls.")
        if CORDYCEPS_VICTIM_STATUS not in target.statuses:
            target.statuses.append(CORDYCEPS_VICTIM_STATUS)
    return log, killed


def cordyceps_boss_life(hcl: int) -> int:
    from .monster_stats import hcl_to_tier

    return max(1, hcl_to_tier(hcl) + 1)
