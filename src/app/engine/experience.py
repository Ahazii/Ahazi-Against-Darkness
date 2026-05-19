from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .dice import roll_d6

MINOR_CATEGORIES = {"vermin", "minions"}
MAJOR_CATEGORIES = {"weird", "boss"}
MINOR_ENCOUNTERS_FOR_XP = 10
CLUES_FOR_SECRET_XP = 3


def is_minor_encounter(defeated: list[EnemyState]) -> bool:
    if not defeated:
        return False
    return all(enemy.category in MINOR_CATEGORIES for enemy in defeated)


def major_foes_defeated(defeated: list[EnemyState]) -> list[EnemyState]:
    return [enemy for enemy in defeated if enemy.category in MAJOR_CATEGORIES]


def xp_roll_succeeds(roll: int, level: int) -> bool:
    return roll == 6 or roll > level


def apply_level_up(member: PartyMemberState) -> list[str]:
    member.level += 1
    member.max_life += 1
    member.current_life += 1
    log = [
        f"{member.name} advances to Level {member.level} "
        f"({member.current_life}/{member.max_life} Life)."
    ]
    if member.class_id.lower() in {"wizard", "elf", "illusionist", "druid"}:
        log.append(f"{member.name} gains a spell slot (add a spell on the character sheet).")
    return log
