from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .class_combat import save_modifier
from .dice import roll_exploding_d6


def enemy_has_poison(enemy: EnemyState) -> bool:
    return "poison" in {tag.lower() for tag in enemy.tags}


def enemy_has_magic_resistance(enemy: EnemyState) -> bool:
    return enemy_magic_resist_bonus(enemy) > 0


def enemy_magic_resist_bonus(enemy: EnemyState) -> int:
    tags = {tag.lower() for tag in enemy.tags}
    bonus = 0
    if "magic_resist" in tags:
        bonus += 1
    if "caster" in tags:
        bonus += 1
    if "dragon" in tags:
        bonus += 1
    return bonus


def spell_target_level(enemy: EnemyState) -> int:
    """Base foe level for the spell connect roll (p.97 step 1)."""
    return enemy.level


def spell_mr_penetration_level(enemy: EnemyState) -> int:
    """Level + MR tiers for the penetration roll (p.97 step 2)."""
    return enemy.level + enemy_magic_resist_bonus(enemy)


SPELLCASTER_CLASS_IDS = frozenset({"wizard", "elf", "illusionist", "druid", "cleric"})


def is_spellcaster(member: PartyMemberState) -> bool:
    return member.class_id.lower() in SPELLCASTER_CLASS_IDS


def spellcasting_modifier(member: PartyMemberState) -> int:
    if is_spellcaster(member):
        return member.level
    return 0


def resolve_spell_effect(
    caster: PartyMemberState,
    enemy: EnemyState,
    *,
    show_rolls: bool,
    label: str,
    modifier_override: int | None = None,
) -> tuple[bool, list[str], int]:
    """Two-step magic resistance (Expanded Edition p.97): connect, then penetrate MR."""
    log: list[str] = []
    modifier = (
        spellcasting_modifier(caster) if modifier_override is None else modifier_override
    )
    total, rolls = roll_exploding_d6()
    final_total = total + modifier
    if show_rolls:
        log.append(
            f"{label} (connect): {caster.name} rolls {' + '.join(str(value) for value in rolls)} + "
            f"{modifier} = {final_total} vs L{enemy.level}."
        )
    if final_total < enemy.level:
        log.append(f"{label} fails to connect with {enemy.name}.")
        return False, log, final_total

    mr = enemy_magic_resist_bonus(enemy)
    if mr <= 0:
        return True, log, final_total

    pen_total, pen_rolls = roll_exploding_d6()
    pen_final = pen_total + modifier
    pen_level = spell_mr_penetration_level(enemy)
    if show_rolls:
        log.append(
            f"{label} (penetrate MR +{mr}): {' + '.join(str(value) for value in pen_rolls)} + "
            f"{modifier} = {pen_final} vs L{pen_level}."
        )
    if pen_final >= pen_level:
        return True, log, final_total
    log.append(f"{enemy.name}'s magic resistance shrugs off the {label.lower()}.")
    return False, log, final_total


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
