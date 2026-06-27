"""Apothecary brew helpers for Courtship (TCOTFD Apothecary Charts)."""

from __future__ import annotations

from ..schemas import PartyMemberState, SessionState

PILLS_OF_VIRILE_MIGHT = "Pills of virile might"
VIRILE_MIGHT_BREEDING_SAVE_BONUS = 1
VIRILE_MIGHT_GIVING_BONUS = 2


def is_pills_of_virile_might(item: str) -> bool:
    return "pills of virile might" in item.lower()


def member_carries_virile_might_pills(member: PartyMemberState) -> bool:
    return any(is_pills_of_virile_might(item) for item in member.inventory)


def virile_might_breeding_save_bonus(member: PartyMemberState) -> int:
    """+1 to breeding saves (Giving, Withholding, seduction) for one wooing encounter (TCOTFD p.83)."""
    return VIRILE_MIGHT_BREEDING_SAVE_BONUS if member_carries_virile_might_pills(member) else 0


def virile_might_giving_bonus(member: PartyMemberState) -> int:
    return VIRILE_MIGHT_GIVING_BONUS if member_carries_virile_might_pills(member) else 0


def virile_might_giving_roll_bonus(member: PartyMemberState) -> int:
    return virile_might_giving_bonus(member) + virile_might_breeding_save_bonus(member)


def virile_retention_withholding_bonus(member: PartyMemberState) -> int:
    if member_carries_virile_might_pills(member):
        return 0
    return 2 if any("virile retention" in status.lower() for status in member.statuses) else 0


def virile_retention_breeding_bonus(member: PartyMemberState) -> int:
    if member_carries_virile_might_pills(member):
        return 0
    return VIRILE_MIGHT_BREEDING_SAVE_BONUS if any("virile retention" in status.lower() for status in member.statuses) else 0


def note_virile_might_use(session: SessionState, member: PartyMemberState) -> None:
    if member_carries_virile_might_pills(member):
        session.courtship_virile_might_character_id = member.character_id


def consume_virile_might_pills(member: PartyMemberState) -> bool:
    for index, item in enumerate(member.inventory):
        if is_pills_of_virile_might(item):
            member.inventory.pop(index)
            return True
    return False


def apply_libidinal_virile_conjunction(
    session: SessionState,
    target: PartyMemberState,
    *,
    show_rolls: bool,
) -> bool:
    """Libidinal Enhancement + Pills of virile might — L5 poison save or d6 Life (TCOTFD p.27 / p.83)."""
    if not member_carries_virile_might_pills(target):
        return True
    from .class_combat import save_modifier
    from .dice import roll_d6, roll_exploding_for_level

    modifier = save_modifier(target, poison=True, session=session)
    total, rolls = roll_exploding_for_level(target)
    if show_rolls:
        session.log.append(
            f"Libidinal Enhancement + Pills of virile might: {target.name} rolls "
            f"{' + '.join(str(v) for v in rolls)} + {modifier} vs L5 poison (TCOTFD p.27)."
        )
    ok = rolls[0] != 1 and total + modifier >= 5
    if ok:
        session.log.append(f"{target.name} withstands the strain (TCOTFD p.27).")
        return True
    damage = roll_d6()
    target.current_life = max(0, target.current_life - damage)
    session.log.append(
        f"{target.name} suffers a heart attack for {damage} Life "
        f"({target.current_life}/{target.max_life}, TCOTFD p.27)."
    )
    return True
