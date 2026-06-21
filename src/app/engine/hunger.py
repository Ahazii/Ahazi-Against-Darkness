from __future__ import annotations

from ..schemas import PartyMemberState, SessionState

HUNGRY_STATUS = "Hungry"
HUNGER_INTERVAL = 24
HUNGER_WARN_HOURS = 20
# Legacy alias — stored on session as hunger_rounds for save compatibility.
FOOD_RATION_FEED_HOURS = HUNGER_INTERVAL


def member_hunger_hours(session: SessionState, member: PartyMemberState) -> int:
    return int(session.hunger_rounds.get(member.character_id, 0))


def is_member_hungry(member: PartyMemberState) -> bool:
    return HUNGRY_STATUS in member.statuses


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
        return [f"{eater.name} eats a Food ration from {source.name}'s supplies (hunger timer reset)."]
    return [f"{eater.name} eats a Food ration (hunger timer reset)."]


def feed_hungry_heroes(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    character_ids: list[str] | None = None,
) -> list[str]:
    if character_ids is None:
        targets = [member for member in party if member.current_life > 0 and is_member_hungry(member)]
    else:
        id_set = set(character_ids)
        targets = [member for member in party if member.character_id in id_set and member.current_life > 0]
    if not targets:
        return ["No living heroes are selected to feed."]
    log: list[str] = []
    fed = 0
    for member in targets:
        ok, source, item = consume_food_ration_from_party(party)
        if not ok or item is None:
            if fed:
                log.append(f"Ran out of Food rations after feeding {fed} hero(es).")
            else:
                log.append("No Food ration is available.")
            break
        feed_member_hunger(session, member)
        fed += 1
        if source and source.character_id != member.character_id:
            log.append(
                f"{member.name} eats a Food ration from {source.name}'s supplies (hunger timer reset)."
            )
        else:
            log.append(f"{member.name} eats a Food ration (hunger timer reset).")
    if fed and len(targets) > fed:
        remaining = [member.name for member in targets[fed:]]
        log.append(f"Still unfed: {', '.join(remaining)}.")
    return log


def feed_all_living_heroes(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    living = [member for member in party if member.current_life > 0]
    if not living:
        return ["No living heroes to feed."]
    log: list[str] = []
    fed = 0
    for member in living:
        ok, source, item = consume_food_ration_from_party(party)
        if not ok or item is None:
            if fed:
                log.append(f"Ran out of Food rations after feeding {fed} hero(es).")
            else:
                log.append("No Food ration is available.")
            break
        feed_member_hunger(session, member)
        fed += 1
        if source and source.character_id != member.character_id:
            log.append(
                f"{member.name} eats a Food ration from {source.name}'s supplies (hunger timer reset)."
            )
        else:
            log.append(f"{member.name} eats a Food ration (hunger timer reset).")
    if fed and len(living) > fed:
        remaining = [member.name for member in living[fed:]]
        log.append(f"Could not feed everyone: {', '.join(remaining)} still need rations.")
    return log


def tick_party_hunger(session: SessionState, members: list[PartyMemberState], *, log: list[str] | None = None) -> None:
    for member in members:
        if member.current_life <= 0:
            continue
        character_id = member.character_id
        hours = member_hunger_hours(session, member) + 1
        session.hunger_rounds[character_id] = hours
        if hours == HUNGER_WARN_HOURS and log is not None:
            log.append(f"{member.name} will be Hungry soon ({hours}/{HUNGER_INTERVAL} hours without food).")
        if hours >= HUNGER_INTERVAL and HUNGRY_STATUS not in member.statuses:
            member.statuses.append(HUNGRY_STATUS)
            if log is not None:
                log.append(f"{member.name} is Hungry ({HUNGER_INTERVAL} hours without food).")
        if hours > HUNGER_INTERVAL and (hours - HUNGER_INTERVAL) % HUNGER_INTERVAL == 0:
            member.current_life = max(0, member.current_life - 1)
            if log is not None:
                log.append(f"{member.name} loses 1 Life from hunger ({member.current_life}/{member.max_life}).")
