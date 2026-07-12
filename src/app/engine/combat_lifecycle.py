from __future__ import annotations

from ..schemas import PartyMemberState, SessionState, TileState
from .split_party import combat_party


def merge_party_outcome(
    current_party: list[PartyMemberState],
    outcome_party: list[PartyMemberState],
) -> list[PartyMemberState]:
    """Preserve full-party order while accepting combat's updated participants."""
    outcome_by_id = {member.character_id: member for member in outcome_party}
    merged: list[PartyMemberState] = []
    for member in current_party:
        merged.append(outcome_by_id.pop(member.character_id, member))
    merged.extend(outcome_by_id.values())
    return sorted(merged, key=lambda member: member.marching_order)


def consume_sleeping_foe_attack_bonus(session: SessionState, tile: TileState) -> int:
    """Consume the first-round attack bonus granted by a sleeping-foe reaction."""
    fighters = combat_party(session, tile.id)
    bonus = session.reaction_sleep_attack_bonus or 2
    prefix = "Sleeping foe +"
    affected = [
        member
        for member in fighters
        if member.current_life > 0 and any(entry.startswith(prefix) for entry in member.statuses)
    ]
    if not affected:
        return 0
    for member in affected:
        member.statuses = [entry for entry in member.statuses if not entry.startswith(prefix)]
    session.reaction_sleep_attack_bonus = 0
    session.log.append(f"Effect: Sleeping foe reaction grants +{bonus} Attack for this first combat round.")
    return bonus
