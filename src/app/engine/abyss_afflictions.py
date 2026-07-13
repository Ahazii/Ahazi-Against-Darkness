"""Four Against the Abyss disease and transformation lifecycle helpers."""

from __future__ import annotations

from uuid import uuid4

from ..schemas import EnemyState, PartyMemberState, SessionState, TileState
from .class_combat import save_modifier
from .dice import roll_die, roll_exploding_for_level
from .inventory import encumbrance_penalty


DARK_PLAGUE_STATUS = "Dark Plague"
# Kept only to clean up saves created by builds that incorrectly added immunity
# after a Dark Plague save or cure. Abyss pp.37 and 61 do not grant immunity.
DARK_PLAGUE_IMMUNITY_STATUS = "Dark Plague immunity"
LYCANTHROPY_EXPOSURE_STATUS = "Lycanthropy exposure"
LYCANTHROPY_STATUS = "Lycanthropy"
LYCANTHROPY_IMMUNITY_STATUS = "Lycanthropy immunity"
LYCANTHROPY_TRANSFORMED_STATUS = "Transformed into werewolf"
VAMPIRE_RISE_PENDING_STATUS = "Vampire-rise pending"


def _has_status(member: PartyMemberState, status: str) -> bool:
    return any(entry.strip().lower() == status.lower() for entry in member.statuses)


def _add_status(member: PartyMemberState, status: str) -> None:
    if not _has_status(member, status):
        member.statuses.append(status)


def has_dark_plague(member: PartyMemberState) -> bool:
    return _has_status(member, DARK_PLAGUE_STATUS)


def clear_legacy_dark_plague_immunity(member: PartyMemberState) -> bool:
    """Remove the immunity status accidentally introduced by older app builds."""
    before = len(member.statuses)
    member.statuses = [
        status
        for status in member.statuses
        if status.strip().lower() != DARK_PLAGUE_IMMUNITY_STATUS.lower()
    ]
    return len(member.statuses) != before


def cure_dark_plague(member: PartyMemberState) -> bool:
    before = len(member.statuses)
    member.statuses = [
        status for status in member.statuses if status.strip().lower() != DARK_PLAGUE_STATUS.lower()
    ]
    return len(member.statuses) != before


def _member_save(
    member: PartyMemberState,
    level: int,
    *,
    label: str,
    log: list[str],
    show_rolls: bool,
    session: SessionState | None = None,
    bonus: int = 0,
    poison: bool = False,
) -> tuple[bool, list[int], int]:
    total, rolls = roll_exploding_for_level(member, session=session, log=log)
    save_label = f"{label} disease" if any(token in label.lower() for token in ("plague", "lycanthropy")) else label
    modifier = (
        save_modifier(member, poison=poison, save_label=save_label, session=session)
        + encumbrance_penalty(member)
        + bonus
    )
    final_total = total + modifier
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(value) for value in rolls)} "
            f"+ {modifier} = {final_total} vs L{level}."
        )
    passed = rolls[0] != 1 and final_total >= level
    log.append(f"{member.name} {'passes' if passed else 'fails'} the {label}.")
    return passed, rolls, final_total


def dark_plague_save_bonus(member: PartyMemberState) -> int:
    return member.level // 2 if member.class_id.lower() == "halfling" else 0


def apply_dark_plague_exposure(
    member: PartyMemberState,
    *,
    session: SessionState,
    log: list[str],
    show_rolls: bool,
    source: str = "Dark Plague",
) -> bool:
    if has_dark_plague(member):
        log.append(f"{member.name} is already infected with the Dark Plague.")
        return False
    passed, _, _ = _member_save(
        member,
        10,
        label=source,
        log=log,
        show_rolls=show_rolls,
        session=session,
        bonus=dark_plague_save_bonus(member),
    )
    if passed:
        log.append(f"{member.name} resists the Dark Plague.")
        return False
    _add_status(member, DARK_PLAGUE_STATUS)
    log.append(f"Effect: {member.name} contracts the Dark Plague (Abyss p.37).")
    return True


def tick_dark_plague_on_room_entry(
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool,
) -> list[str]:
    log: list[str] = []
    living = [member for member in session.party if member.current_life > 0]
    infected = [member for member in living if has_dark_plague(member)]
    if not infected:
        return log
    for member in infected:
        roll = roll_die(8)
        if show_rolls:
            log.append(f"Dark Plague: {member.name} rolls d8 = {roll} on entering {tile.title}.")
        if roll == 1:
            member.current_life = max(0, member.current_life - 1)
            log.append(f"Effect: {member.name} loses 1 Life to the Dark Plague ({member.current_life}/{member.max_life}).")
            if member.current_life <= 0:
                log.append(f"{member.name} falls.")
    carriers = [member for member in session.party if member.current_life > 0 and has_dark_plague(member)]
    if not carriers:
        return log
    for member in session.party:
        if member.current_life <= 0 or has_dark_plague(member):
            continue
        apply_dark_plague_exposure(
            member,
            session=session,
            log=log,
            show_rolls=show_rolls,
            source="Dark Plague spread",
        )
    return log


def apply_blessing_to_dark_plague(
    caster: PartyMemberState,
    target: PartyMemberState,
    *,
    log: list[str],
    show_rolls: bool,
    session: SessionState | None = None,
) -> bool | None:
    if not has_dark_plague(target):
        return None
    total, rolls = roll_exploding_for_level(caster, session=session, log=log)
    final_total = total + caster.level
    if show_rolls:
        log.append(
            f"Dark Plague Blessing: {caster.name} rolls {' + '.join(str(value) for value in rolls)} "
            f"+ L{caster.level} = {final_total} (need 10+)."
        )
    if rolls[0] != 1 and final_total >= 10:
        cure_dark_plague(target)
        log.append(f"Blessing cures the Dark Plague from {target.name}.")
        return True
    else:
        log.append(f"Blessing fails to cure the Dark Plague from {target.name}; the prayer is spent.")
        return False


def mark_lycanthropy_exposure(member: PartyMemberState) -> None:
    _add_status(member, LYCANTHROPY_EXPOSURE_STATUS)


def has_lycanthropy(member: PartyMemberState) -> bool:
    return _has_status(member, LYCANTHROPY_STATUS)


def is_lycanthropy_immune(member: PartyMemberState) -> bool:
    return _has_status(member, LYCANTHROPY_IMMUNITY_STATUS)


def _remove_lycanthropy_exposure(member: PartyMemberState) -> None:
    member.statuses = [
        status
        for status in member.statuses
        if not status.strip().lower().startswith(LYCANTHROPY_EXPOSURE_STATUS.lower())
    ]


def _lycanthropy_save_bonus(member: PartyMemberState) -> int:
    return member.level // 2 if member.class_id.lower() in {"elf", "halfling"} else 0


def _drop_lycanthropy_forbidden_items(member: PartyMemberState, tile: TileState) -> list[str]:
    dropped: list[str] = []
    kept: list[str] = []
    for item in member.inventory:
        lower = item.lower()
        silver = "silver" in lower or "jewelry" in lower or "jewellery" in lower
        lantern = "lantern" in lower and "oil" not in lower
        if silver or lantern:
            dropped.append(item)
        else:
            kept.append(item)
    if dropped:
        member.inventory = kept
        tile.treasure_items.extend(dropped)
    return dropped


def resolve_lycanthropy_exposures(
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool,
) -> list[str]:
    log: list[str] = []
    for member in session.party:
        if not any(status.lower().startswith("lycanthropy exposure") for status in member.statuses):
            continue
        _remove_lycanthropy_exposure(member)
        if member.current_life <= 0:
            continue
        if is_lycanthropy_immune(member):
            log.append(f"{member.name} is immune to lycanthropy.")
            continue
        passed, _, _ = _member_save(
            member,
            5,
            label="Lycanthropy infection",
            log=log,
            show_rolls=show_rolls,
            session=session,
            bonus=_lycanthropy_save_bonus(member),
        )
        if passed:
            continue
        _add_status(member, LYCANTHROPY_STATUS)
        log.append(f"Effect: {member.name} contracts Lycanthropy (Abyss p.39).")
        dropped = _drop_lycanthropy_forbidden_items(member, tile)
        if dropped:
            log.append(f"{member.name} drops forbidden item(s): {', '.join(dropped)}.")
    log.extend(check_lycanthropy_transformations(session, tile, show_rolls=show_rolls))
    return log


def check_lycanthropy_transformations(
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool,
) -> list[str]:
    log: list[str] = []
    for member in session.party:
        if (
            member.current_life <= 0
            or not has_lycanthropy(member)
            or _has_status(member, LYCANTHROPY_TRANSFORMED_STATUS)
            or member.madness <= member.level
        ):
            continue
        _add_status(member, LYCANTHROPY_TRANSFORMED_STATUS)
        member.current_life = 0
        enemy = EnemyState(
            id=f"were-{member.character_id}-{uuid4().hex[:8]}",
            name=f"{member.name} the Werewolf",
            category="boss",
            level=6,
            life=5,
            max_life=5,
            attacks=2,
            tags=["abyss", "werecreature", "lycanthrope", "former_party_member"],
        )
        tile.enemies.append(enemy)
        if member.character_id not in tile.fallen_character_ids:
            tile.fallen_character_ids.append(member.character_id)
        log.append(
            f"{member.name}'s Madness exceeds Level and they transform into a werewolf "
            "(L6 boss, 5 Life, 2 attacks)."
        )
    return log


def treat_lycanthropy_at_monastery(
    session: SessionState,
    member: PartyMemberState | None,
    *,
    show_rolls: bool,
) -> list[str]:
    log: list[str] = []
    if not session.camped_outside or session.mode != "exploration":
        return ["Lycanthropy treatment requires leaving the dungeon and reaching the monastery from camp."]
    if member is None or member.current_life <= 0:
        return ["Choose a living hero with Lycanthropy for monastery treatment."]
    if not has_lycanthropy(member):
        return [f"{member.name} does not have Lycanthropy."]
    cost = 400
    total_gold = member.gold + member.bank_gold
    if total_gold < cost:
        return [f"{member.name} needs {cost}gp for monastery lycanthropy treatment but has {total_gold}gp."]
    bank_take = min(member.bank_gold, cost)
    member.bank_gold -= bank_take
    remaining = cost - bank_take
    if remaining:
        member.gold -= remaining
    if bank_take:
        log.append(f"{member.name} pays {bank_take}gp from home bank funds for lycanthropy treatment.")
    if remaining:
        log.append(f"{member.name} pays {remaining}gp carried outside for lycanthropy treatment.")
    passed, rolls, _ = _member_save(
        member,
        5,
        label="Lycanthropy treatment",
        log=log,
        show_rolls=show_rolls,
        session=session,
        bonus=_lycanthropy_save_bonus(member) + 1,
    )
    if rolls[0] == 1:
        member.current_life = 0
        log.append(f"The treatment poison kills {member.name}; resurrection will not remove Lycanthropy.")
        return log
    if passed:
        member.statuses = [
            status for status in member.statuses if status.strip().lower() != LYCANTHROPY_STATUS.lower()
        ]
        log.append(f"{member.name} is cured of Lycanthropy.")
        if len(rolls) > 1:
            _add_status(member, LYCANTHROPY_IMMUNITY_STATUS)
            log.append(f"{member.name} is now immune to further lycanthropy infection.")
    else:
        log.append(f"{member.name} remains infected; another 400gp treatment may be attempted.")
    return log


def mark_vampire_rise_pending(member: PartyMemberState) -> None:
    _add_status(member, VAMPIRE_RISE_PENDING_STATUS)


def has_vampire_rise_pending(member: PartyMemberState) -> bool:
    return _has_status(member, VAMPIRE_RISE_PENDING_STATUS)
