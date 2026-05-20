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


def poison_status_level(member: PartyMemberState) -> int | None:
    for status in member.statuses:
        lower = status.lower()
        if lower.startswith("poisoned l"):
            try:
                return int(lower.split("l", 1)[1])
            except ValueError:
                continue
    return None


def apply_poison_status(member: PartyMemberState, foe_level: int) -> None:
    if poison_status_level(member) is None:
        member.statuses.append(f"Poisoned L{foe_level}")


def clear_poison_status(member: PartyMemberState) -> None:
    member.statuses = [status for status in member.statuses if not status.lower().startswith("poisoned")]


def mirror_image_count(member: PartyMemberState) -> int:
    for status in member.statuses:
        lower = status.lower()
        if lower.startswith("mirror image x"):
            try:
                return int(lower.split("x", 1)[1])
            except ValueError:
                continue
    return 0


def consume_mirror_image(member: PartyMemberState) -> bool:
    count = mirror_image_count(member)
    if count <= 0:
        return False
    remaining = count - 1
    updated: list[str] = []
    replaced = False
    for status in member.statuses:
        if not replaced and status.lower().startswith("mirror image x"):
            replaced = True
            if remaining > 0:
                updated.append(f"Mirror Image x{remaining}")
            continue
        updated.append(status)
    member.statuses = updated
    return True


def tick_poisoned_heroes(
    party: list[PartyMemberState],
    *,
    show_rolls: bool,
    explain_math: bool = False,
) -> list[str]:
    log: list[str] = []
    for member in party:
        if member.current_life <= 0:
            continue
        foe_level = poison_status_level(member)
        if foe_level is None:
            continue
        saved, poison_log = poison_save_succeeds(
            member,
            foe_level,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        log.extend(poison_log)
        if saved:
            clear_poison_status(member)
            log.append(f"{member.name} shakes off the poison.")
        else:
            member.current_life = max(0, member.current_life - 1)
            log.append(f"{member.name} takes 1 damage from lingering poison.")
            if member.current_life == 0:
                log.append(f"{member.name} falls.")
    return log


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
