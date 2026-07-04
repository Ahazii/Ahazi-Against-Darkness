"""Forsaken Depths ruins procedures (FD p.56)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState, TileState
from .class_combat import save_modifier
from .dice import roll_d6, roll_exploding_for_level
from .experience import tier_for_level
from .madness import _grant_madness
from .party_life import apply_party_life_loss

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


FD_RUINS_PSYCHIC_IMMUNITY_STATUS = "FD Psychic Residue +3 Save"


def _machinery_modifier(member: PartyMemberState) -> int:
    class_id = member.class_id.lower()
    if class_id in {"gnome", "artificer"}:
        return member.level
    if class_id == "wizard":
        return max(1, member.level // 2)
    return 0


def _psychic_modifier(member: PartyMemberState) -> int:
    class_id = member.class_id.lower()
    bonus = 0
    if class_id in {"wizard", "demonologist", "witch_hunter"}:
        bonus = member.level
    else:
        bonus = max(1, member.level // 2)
    if FD_RUINS_PSYCHIC_IMMUNITY_STATUS in member.statuses:
        bonus += 3
    return bonus


def setup_ruins_complex_machinery(session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
    tile.content_key = "ruins_machinery"
    if "Complex Machinery" not in tile.objects:
        tile.objects.append("Complex Machinery")
    if show_rolls:
        session.log.append(
            "Ruins procedure: Complex Machinery. Each hero may try once on this first visit; "
            "success grants 1 Clue or d6 Food rations, failure deals Tier damage (FD p.56)."
        )


def resolve_ruins_complex_machinery(
    engine: RandomDungeonEngine,
    session: SessionState,
    character_id: str | None,
    *,
    reward_choice: str | None = None,
    show_rolls: bool = True,
) -> None:
    if session.mode != "exploration":
        session.log.append("Resolve Complex Machinery during exploration.")
        return
    tile = engine._current_tile(session)
    if tile.content_key != "ruins_machinery":
        session.log.append("There is no Complex Machinery to examine here (FD p.56).")
        return
    if tile.fd_ruins_machinery_resolved:
        session.log.append("The machinery has already yielded its Clue or danger in this room.")
        return
    if reward_choice not in {"clue", "food"}:
        session.log.append("Choose the Complex Machinery success reward first: 1 Clue or d6 Food rations (FD p.56).")
        return
    member = next((hero for hero in session.party if hero.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        session.log.append("Choose a living hero to examine the Complex Machinery.")
        return
    if character_id in tile.fd_ruins_machinery_attempted_character_ids:
        session.log.append(f"{member.name} has already tried to understand this machinery (FD p.56).")
        return
    tile.fd_ruins_machinery_attempted_character_ids.append(character_id)
    hcl = engine._highest_character_level(session.party)
    target = hcl + 2
    total, rolls = roll_exploding_for_level(member, session=session)
    modifier = _machinery_modifier(member)
    final_total = total + modifier
    if show_rolls:
        session.log.append(
            f"Complex Machinery: {member.name} rolls {' + '.join(str(value) for value in rolls)} + "
            f"{modifier} = {final_total} vs HCL+2 ({target}, FD p.56)."
        )
    if rolls[0] != 1 and final_total >= target:
        tile.fd_ruins_machinery_resolved = True
        if reward_choice == "food":
            rations = roll_d6()
            member.inventory.extend(["Food ration"] * rations)
            session.log.append(
                f"{member.name} understands the mechanism and finds {rations} Food ration(s) (d6, FD p.56)."
            )
        else:
            session.clues_found += 1
            member.clues += 1
            session.log.append(f"{member.name} understands the mechanism; the party gains 1 Clue (FD p.56).")
        return
    damage = tier_for_level(hcl)
    before = member.current_life
    applied = apply_party_life_loss(session, member, damage, log=session.log)
    session.log.append(
        f"{member.name} triggers the mechanism and takes {applied} Tier damage "
        f"({before}->{member.current_life}/{member.max_life}, FD p.56)."
    )
    if member.current_life <= 0:
        session.log.append(f"{member.name} falls.")


def resolve_ruins_psychic_residue(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    tile.content_key = "ruins_psychic_hall"
    if "Psychic Residue" not in tile.objects:
        tile.objects.append("Psychic Residue")
    target = hcl + 3
    pending: dict[str, str] = {}
    if show_rolls:
        session.log.append(
            "Ruins procedure: Psychic Residue. All heroes Save vs HCL+3 psychic assault; "
            "failures choose 3 damage, 1 Madness, or lose 2 spell slots (FD p.56)."
        )
    for member in session.party:
        if member.current_life <= 0:
            continue
        total, rolls = roll_exploding_for_level(member, session=session)
        modifier = _psychic_modifier(member) + save_modifier(member, save_label="Psychic Residue", session=session)
        final_total = total + modifier
        if show_rolls:
            session.log.append(
                f"Psychic Residue Save: {member.name} rolls {' + '.join(str(value) for value in rolls)} + "
                f"{modifier} = {final_total} vs HCL+3 ({target}, FD p.56)."
            )
        if rolls[0] != 1 and final_total >= target:
            if FD_RUINS_PSYCHIC_IMMUNITY_STATUS not in member.statuses:
                member.statuses.append(FD_RUINS_PSYCHIC_IMMUNITY_STATUS)
            session.log.append(f"{member.name} resists and gains +3 to further Psychic Residue Saves this adventure.")
            continue
        pending[member.character_id] = tile.id
        session.log.append(f"{member.name} fails; choose the Psychic Residue consequence on the room panel.")
    session.fd_ruins_psychic_pending.update(pending)


def resolve_ruins_psychic_choice(
    session: SessionState,
    character_id: str | None,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> None:
    if not character_id or character_id not in session.fd_ruins_psychic_pending:
        session.log.append("No Psychic Residue choice is pending for that hero.")
        return
    pending_tile_id = session.fd_ruins_psychic_pending.get(character_id)
    member = next((hero for hero in session.party if hero.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        session.fd_ruins_psychic_pending.pop(character_id, None)
        session.log.append("That hero can no longer resolve the Psychic Residue choice.")
        return
    if choice == "damage":
        before = member.current_life
        applied = apply_party_life_loss(session, member, 3, log=session.log)
        session.fd_ruins_psychic_pending.pop(character_id, None)
        session.log.append(
            f"Psychic Residue: {member.name} takes {applied} damage "
            f"({before}->{member.current_life}/{member.max_life}, FD p.56)."
        )
        if member.current_life <= 0:
            session.log.append(f"{member.name} falls.")
        return
    if choice == "madness":
        session.fd_ruins_psychic_pending.pop(character_id, None)
        session.log.extend(_grant_madness(session, member, source="Psychic Residue", log=[]))
        return
    if choice == "spell_slots":
        lost: list[str] = []
        for _ in range(2):
            if not member.spells:
                break
            lost.append(member.spells.pop())
        session.fd_ruins_psychic_pending.pop(character_id, None)
        if lost:
            session.log.append(f"Psychic Residue: {member.name} loses spell slot(s): {', '.join(lost)} (FD p.56).")
        else:
            session.log.append(f"Psychic Residue: {member.name} has no spell slots to lose; choose damage or Madness.")
            if pending_tile_id:
                session.fd_ruins_psychic_pending[character_id] = pending_tile_id
        return
    session.log.append("Choose 3 damage, 1 Madness, or lose 2 spell slots for Psychic Residue (FD p.56).")
