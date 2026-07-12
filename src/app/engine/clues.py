from __future__ import annotations

from ..schemas import PartyMemberState, SessionState


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
