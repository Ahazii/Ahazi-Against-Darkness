"""Track party Life loss for adventure-scoped effects (e.g. fountain p.153)."""

from __future__ import annotations

from ..schemas import PartyMemberState, SessionState


def record_character_life_loss(session: SessionState | None, character_id: str | None) -> None:
    if session is None or not character_id:
        return
    if character_id not in session.characters_who_lost_life:
        session.characters_who_lost_life.append(character_id)


def apply_party_life_loss(
    session: SessionState | None,
    member: PartyMemberState,
    amount: int,
    *,
    log: list[str] | None = None,
) -> int:
    if amount <= 0:
        return 0
    before = member.current_life
    member.current_life = max(0, member.current_life - amount)
    applied = before - member.current_life
    if applied > 0:
        record_character_life_loss(session, member.character_id)
        if session is not None:
            from .forsaken_depths_content import clear_fd_hallucination_on_damage

            clear_log = clear_fd_hallucination_on_damage(session, member)
            if log is not None:
                log.extend(clear_log)
            else:
                session.log.extend(clear_log)
    return applied
