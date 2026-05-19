from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .class_combat import save_modifier
from .dice import roll_exploding_d6


def enemy_has_poison(enemy: EnemyState) -> bool:
    return "poison" in {tag.lower() for tag in enemy.tags}


def enemy_magic_resist_bonus(enemy: EnemyState) -> int:
    tags = {tag.lower() for tag in enemy.tags}
    if "magic_resist" in tags or "caster" in tags:
        return 1
    return 0


def spell_target_level(enemy: EnemyState) -> int:
    return enemy.level + enemy_magic_resist_bonus(enemy)


def has_blade_poison(member: PartyMemberState) -> bool:
    return any("blade poison" in item.lower() for item in member.inventory)


def consume_blade_poison(member: PartyMemberState) -> None:
    for index, item in enumerate(member.inventory):
        if "blade poison" in item.lower():
            member.inventory.pop(index)
            return


def poison_save_succeeds(
    member: PartyMemberState,
    foe_level: int,
    *,
    show_rolls: bool,
    explain_math: bool = False,
) -> tuple[bool, list[str]]:
    total, rolls = roll_exploding_d6()
    modifier = save_modifier(member, poison=True)
    final_total = total + modifier
    log: list[str] = []
    if show_rolls:
        log.append(
            f"Poison save: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier} = "
            f"{final_total} vs L{foe_level}."
        )
    if explain_math:
        log.append(f"Poison save math: need total >= foe level {foe_level} (natural 1 fails).")
    if rolls[0] == 1:
        return False, log
    return final_total >= foe_level, log
