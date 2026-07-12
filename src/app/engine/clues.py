from __future__ import annotations

from ..schemas import PartyMemberState, SessionState, TileState
from .experience import CLUES_FOR_SECRET_XP


def sync_clue_total(session: SessionState) -> bool:
    """Keep the session summary equal to Clues held by individual party members."""
    total = sum(max(0, member.clues) for member in session.party)
    changed = session.clues_found != total
    session.clues_found = total
    return changed


def default_clue_holder(
    session: SessionState, character_id: str | None = None
) -> PartyMemberState | None:
    """Choose a living requested holder, otherwise the first living party member."""
    if character_id:
        selected = next(
            (
                member
                for member in session.party
                if member.character_id == character_id and member.current_life > 0
            ),
            None,
        )
        if selected is not None:
            return selected
    living = [
        member
        for member in sorted(session.party, key=lambda item: item.marching_order)
        if member.current_life > 0
    ]
    if living:
        return living[0]
    return session.party[0] if session.party else None


def ensure_individual_clues(session: SessionState) -> bool:
    """Migrate a legacy pooled total to a holder, then refresh the session summary."""
    member_total = sum(max(0, member.clues) for member in session.party)
    if session.clues_found > member_total:
        holder = default_clue_holder(session)
        if holder is not None:
            holder.clues += session.clues_found - member_total
            return sync_clue_total(session) or True
    return sync_clue_total(session)


def grant_clue(
    session: SessionState,
    tile: TileState,
    *,
    character_id: str | None = None,
    add_object: bool = True,
    source: str = "finds",
) -> PartyMemberState | None:
    """Give one held Clue to an eligible hero and keep the party total synchronized."""
    if add_object and "Clue" not in tile.objects:
        tile.objects.append("Clue")
    holder = default_clue_holder(session, character_id)
    if holder is None:
        session.log.append("No hero is available to hold the Clue.")
        return None
    holder.clues += 1
    sync_clue_total(session)
    if source == "buys":
        session.log.append(
            f"{holder.name} buys 1 Clue ({holder.clues} carried; {session.clues_found} party total)."
        )
    else:
        session.log.append(
            f"{holder.name} finds 1 Clue ({holder.clues} carried; {session.clues_found} party total)."
        )
    if session.clues_found >= CLUES_FOR_SECRET_XP:
        session.log.append(
            f"{CLUES_FOR_SECRET_XP} Clues are available. Spend them deliberately on a Secret, "
            "an eligible spell, or a special clue use."
        )
    return holder


def grant_clue_to_member(session: SessionState, member: PartyMemberState, tile: TileState) -> None:
    """Give an explicitly chosen hero one Clue for a rule-owned effect."""
    member.clues += 1
    if "Clue" not in tile.objects:
        tile.objects.append("Clue")
    session.log.append(f"Effect: {member.name} gains 1 Clue (now {member.clues}).")


def spend_living_party_clues(session: SessionState, amount: int) -> tuple[bool, list[str]]:
    """Spend held Clues from living heroes in marching order and retain the party summary."""
    living = [member for member in session.party if member.current_life > 0]
    total = sum(member.clues for member in living)
    if total < amount:
        return False, [f"The party needs {amount} Clues but has {total}."]
    remaining = amount
    log: list[str] = []
    for member in sorted(living, key=lambda item: item.marching_order):
        take = min(member.clues, remaining)
        if take:
            member.clues -= take
            remaining -= take
            log.append(f"{member.name} spends {take} Clue(s).")
        if remaining <= 0:
            break
    session.clues_found = max(0, session.clues_found - amount)
    return True, log
