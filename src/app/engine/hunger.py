from __future__ import annotations

from ..schemas import PartyMemberState, SessionState

HUNGRY_STATUS = "Hungry"
HUNGER_INTERVAL = 24
FOOD_RATION_FEED_ROUNDS = 24


def feed_member_hunger(session: SessionState, member: PartyMemberState) -> None:
    session.hunger_rounds[member.character_id] = 0
    member.statuses = [status for status in member.statuses if status != HUNGRY_STATUS]


def consume_food_ration_from_member(member: PartyMemberState) -> tuple[bool, str | None]:
    for index, item in enumerate(member.inventory):
        if "food ration" in item.lower():
            member.inventory.pop(index)
            return True, item
    return False, None


def consume_food_ration_from_party(party: list[PartyMemberState]) -> tuple[bool, PartyMemberState | None, str | None]:
    for member in party:
        ok, item = consume_food_ration_from_member(member)
        if ok:
            return True, member, item
    return False, None, None


def eat_food_ration(
    session: SessionState,
    eater: PartyMemberState,
    party: list[PartyMemberState],
) -> list[str]:
    if eater.current_life <= 0:
        return [f"{eater.name} cannot eat."]
    ok, source, item = consume_food_ration_from_party(party)
    if not ok or item is None:
        return ["No Food ration is available."]
    feed_member_hunger(session, eater)
    if source and source.character_id != eater.character_id:
        return [f"{eater.name} eats a Food ration from {source.name}'s supplies (hunger reset)."]
    return [f"{eater.name} eats a Food ration (hunger reset)."]


def tick_party_hunger(session: SessionState, members: list[PartyMemberState], *, log: list[str] | None = None) -> None:
    for member in members:
        if member.current_life <= 0:
            continue
        character_id = member.character_id
        rounds = int(session.hunger_rounds.get(character_id, 0)) + 1
        session.hunger_rounds[character_id] = rounds
        if rounds >= HUNGER_INTERVAL and HUNGRY_STATUS not in member.statuses:
            member.statuses.append(HUNGRY_STATUS)
            if log is not None:
                log.append(f"{member.name} is Hungry (no food for {HUNGER_INTERVAL} rounds).")
        if rounds > HUNGER_INTERVAL and (rounds - HUNGER_INTERVAL) % HUNGER_INTERVAL == 0:
            member.current_life = max(0, member.current_life - 1)
            if log is not None:
                log.append(f"{member.name} loses 1 Life from hunger ({member.current_life}/{member.max_life}).")
