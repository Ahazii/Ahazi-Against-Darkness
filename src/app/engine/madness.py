from __future__ import annotations

from ..schemas import PartyMemberState, SessionState, PendingMadnessChoiceState
from .expert_skill_effects import has_skill


ENVENOMED_MELEE_STATUS = "Envenomed weapon (melee)"
ENVENOMED_MISSILE_STATUS = "Envenomed weapon (missile)"
PARANOID_STATUS = "Paranoid"


def madness_points(member: PartyMemberState) -> int:
    if member.madness > 0:
        return member.madness
    total = 0
    for status in member.statuses:
        lower = status.lower()
        if lower.startswith("madness"):
            digits = "".join(char for char in lower if char.isdigit())
            if digits:
                total += int(digits)
    return total


def madness_threshold(member: PartyMemberState) -> int:
    if member.class_id.lower() == "wizard":
        return member.level + 1
    return member.level


def is_paranoid(member: PartyMemberState) -> bool:
    return madness_points(member) >= 1 or any(
        status.lower().startswith("paranoid") for status in member.statuses
    )


def sync_paranoid_status(member: PartyMemberState) -> None:
    member.statuses = [status for status in member.statuses if not status.lower().startswith("paranoid")]
    if is_paranoid(member):
        member.statuses.append(PARANOID_STATUS)


def heal_madness(member: PartyMemberState, amount: int = 1) -> int:
    if amount <= 0:
        return 0
    current = madness_points(member)
    if current <= 0:
        member.madness = 0
        member.statuses = [status for status in member.statuses if not status.lower().startswith("madness")]
        sync_paranoid_status(member)
        return 0
    healed = min(amount, current)
    member.madness = max(0, current - healed)
    member.statuses = [status for status in member.statuses if not status.lower().startswith("madness")]
    if member.madness > 0:
        member.statuses.append(f"Madness {member.madness}")
    sync_paranoid_status(member)
    return healed


def _strong_will_blocks_first_madness(session: SessionState, member: PartyMemberState) -> bool:
    if not has_skill(member, "strong_will"):
        return False
    if member.character_id in session.strong_will_madness_ignored:
        return False
    session.strong_will_madness_ignored.append(member.character_id)
    return True


def apply_madness_gain(
    session: SessionState,
    member: PartyMemberState,
    *,
    source: str,
    show_rolls: bool = True,
    allow_damage_choice: bool = True,
) -> list[str]:
    log: list[str] = []
    if member.current_life <= 0:
        return log
    if _strong_will_blocks_first_madness(session, member):
        log.append(f"Effect: Strong Will ignores the first Madness point on {member.name} this adventure.")
        return log
    if allow_damage_choice and 1 <= member.level <= 4:
        session.pending_madness_choice = PendingMadnessChoiceState(
            character_id=member.character_id,
            source=source,
        )
        log.append(
            f"Event: {member.name} may take 2 damage instead of gaining 1 Madness from {source} "
            "(choose on the map panel)."
        )
        return log
    return _grant_madness(session, member, source=source, log=log)


def _grant_madness(
    session: SessionState,
    member: PartyMemberState,
    *,
    source: str,
    log: list[str],
) -> list[str]:
    member.madness = madness_points(member) + 1
    member.statuses = [status for status in member.statuses if not status.lower().startswith("madness")]
    member.statuses.append(f"Madness {member.madness}")
    sync_paranoid_status(member)
    log.append(f"Effect: {member.name} gains 1 Madness from {source} (total {member.madness}).")
    if is_paranoid(member) and member.madness == 1:
        log.append(f"Effect: {member.name} becomes paranoid and cannot exchange equipment.")
    insanity_log = check_insanity(session, member)
    log.extend(insanity_log)
    return log


def resolve_madness_choice(
    session: SessionState,
    *,
    character_id: str | None,
    choice: str | None,
) -> None:
    pending = session.pending_madness_choice
    if not pending:
        session.log.append("No Madness choice is pending.")
        return
    if pending.character_id != character_id:
        session.log.append("Choose the hero facing the Madness choice.")
        return
    member = next((hero for hero in session.party if hero.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        session.pending_madness_choice = None
        session.log.append("That hero cannot resolve the Madness choice.")
        return
    source = pending.source or "the ordeal"
    if choice == "damage":
        session.pending_madness_choice = None
        member.current_life = max(0, member.current_life - 2)
        session.log.append(f"Effect: {member.name} takes 2 damage instead of gaining Madness from {source}.")
        if member.current_life <= 0:
            session.log.append(f"{member.name} falls from the trauma.")
        return
    if choice == "madness":
        session.pending_madness_choice = None
        session.log.extend(_grant_madness(session, member, source=source, log=[]))
        return
    session.log.append("Choose whether to take 2 damage or gain 1 Madness.")


def check_insanity(session: SessionState, member: PartyMemberState) -> list[str]:
    total = madness_points(member)
    if total <= madness_threshold(member):
        return []
    session.log.append(
        f"Effect: {member.name}'s Madness ({total}) exceeds Level {madness_threshold(member)} "
        "and flees into the dark, cackling madly, never to be seen again."
    )
    member.current_life = 0
    member.madness = 0
    member.statuses = [status for status in member.statuses if not status.lower().startswith(("madness", "paranoid"))]
    from .hirelings import notify_hireling_morale_casualty

    return notify_hireling_morale_casualty(session, reason=f"{member.name} lost sanity")


def heal_madness_on_dungeon_exit(session: SessionState) -> list[str]:
    if session.madness_exit_healed:
        return []
    if session.major_foes_encountered < 1:
        return []
    session.madness_exit_healed = True
    log: list[str] = []
    for member in session.party:
        if member.current_life <= 0:
            continue
        healed = heal_madness(member, 1)
        if healed:
            log.append(f"Effect: {member.name} recovers 1 Madness after leaving the dungeon.")
    return log


def poison_vial_items(member: PartyMemberState) -> list[str]:
    return [
        item
        for item in member.inventory
        if "poison" in item.lower() and "potion" not in item.lower()
    ]


def envenomed_weapon_kind(member: PartyMemberState) -> str | None:
    if ENVENOMED_MELEE_STATUS in member.statuses:
        return "melee"
    if ENVENOMED_MISSILE_STATUS in member.statuses:
        return "missile"
    return None


def clear_envenomed_weapon(member: PartyMemberState) -> None:
    member.statuses = [
        status
        for status in member.statuses
        if status not in {ENVENOMED_MELEE_STATUS, ENVENOMED_MISSILE_STATUS}
    ]


def apply_envenom_weapon(session: SessionState, member: PartyMemberState, weapon_kind: str) -> list[str]:
    if weapon_kind not in {"melee", "missile"}:
        return ["Choose a slashing melee weapon or missile weapon to envenom."]
    vials = poison_vial_items(member)
    if not vials:
        return ["No poison vial is available to envenom a weapon."]
    if envenomed_weapon_kind(member) is not None:
        return [f"{member.name} already has an envenomed weapon."]
    member.inventory.remove(vials[0])
    clear_envenomed_weapon(member)
    status = ENVENOMED_MISSILE_STATUS if weapon_kind == "missile" else ENVENOMED_MELEE_STATUS
    member.statuses.append(status)
    label = "missile" if weapon_kind == "missile" else "slashing melee"
    return [f"Effect: {member.name} envenoms a {label} weapon (+1 Attack vs the first foe this fight)."]


def foe_immune_to_poison(enemy) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    if tags.intersection(
        {
            "undead",
            "demon",
            "blob",
            "automation",
            "automatons",
            "mold",
            "fungi",
            "fungus",
            "elemental",
            "construct",
            "clockwork",
            "artificial",
            "living_statue",
            "poison_immune",
            "immune_poison",
        }
    ):
        return True
    if "living statue" in name or "statue" in tags:
        return True
    return False
