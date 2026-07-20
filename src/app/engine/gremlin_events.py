from __future__ import annotations

from collections.abc import Callable

from ..schemas import PartyMemberState, SessionState
from .dice import roll_d6
from .equipment_effects import scroll_protected_by_tube
from .magic_weapons import is_magic_weapon
from .star_object_curse import (
    is_star_object_item,
    reconcile_star_object_carrier,
    remove_star_object,
    star_object_carrier,
)


def has_gremlin_repellant(member: PartyMemberState) -> bool:
    return any("gremlin repellant" in item.lower() for item in member.inventory)


def party_has_gremlin_repellant(party: list[PartyMemberState]) -> bool:
    return any(has_gremlin_repellant(member) for member in party if member.current_life > 0)


def consume_gremlin_repellant(party: list[PartyMemberState]) -> tuple[bool, str | None]:
    for member in party:
        for index, item in enumerate(member.inventory):
            if "gremlin repellant" in item.lower():
                member.inventory.pop(index)
                return True, item
    return False, None


def gremlin_protection_active(session: SessionState, party: list[PartyMemberState]) -> bool:
    if session.gremlin_wm_protection_pending:
        return True
    return party_has_gremlin_repellant(party)


def consume_gremlin_protection(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    log: list[str] = []
    if session.gremlin_wm_protection_pending:
        session.gremlin_wm_protection_pending = False
        log.append("Miners' Ointment wards off the gremlins.")
        return log
    consumed, item = consume_gremlin_repellant(party)
    if consumed:
        log.append(f"The party's {item} keeps the invisible gremlins away.")
    return log


def _is_scroll(item: str) -> bool:
    lower = item.lower()
    if "scroll tube" in lower:
        return False
    return lower.startswith("scroll") or "prism of" in lower or "bark of" in lower


def _is_potion(item: str) -> bool:
    return "potion" in item.lower() or "vial" in item.lower()


def _is_weapon_item(item: str) -> bool:
    lower = item.lower()
    if is_magic_weapon(item):
        return True
    return any(token in lower for token in ("weapon", "bow", "crossbow", "dagger", "sword", "mace", "club"))


def _is_gem(item: str) -> bool:
    lower = item.lower()
    return "gem" in lower or "jewel" in lower


def _stealable_items(member: PartyMemberState) -> list[tuple[str, str]]:
    buckets: list[tuple[str, str]] = []
    for item in member.inventory:
        lower = item.lower()
        if "gremlin repellant" in lower or is_star_object_item(item):
            continue
        if is_magic_weapon(item) or ("magic " in lower and ("armor" in lower or "wand" in lower or "ring" in lower)):
            buckets.append(("magic_items", item))
        elif _is_scroll(item):
            if scroll_protected_by_tube(member, item):
                continue
            buckets.append(("scrolls", item))
        elif _is_potion(item):
            buckets.append(("potions", item))
        elif _is_weapon_item(item):
            buckets.append(("weapons", item))
        elif _is_gem(item):
            buckets.append(("gems", item))
    return buckets


def resolve_invisible_gremlins(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    roll_fn: Callable[[], int] | None = None,
    star_object_choice: str | None = None,
) -> list[str]:
    log = ["Invisible Gremlins are an event, not a Foe."]
    living = [member for member in party if member.current_life > 0]
    if not living:
        return log + ["There is no gear left to steal."]
    reconcile_star_object_carrier(session)
    carrier = star_object_carrier(session)
    if carrier is not None:
        if star_object_choice not in {"release", "keep"}:
            session.tag_star_object_gremlin_choice_pending = True
            return log + [
                f"{carrier.name} may let the Invisible Gremlins take Bofto's cursed star-shaped object. "
                "Choose Let them take it to break the curse, or Keep it to resolve the normal theft event "
                "(TAG p.30)."
            ]
        session.tag_star_object_gremlin_choice_pending = False
        if star_object_choice == "release":
            remove_star_object(session)
            return log + [
                f"{carrier.name} lets the Invisible Gremlins take Bofto's star-shaped object. "
                "The curse is broken; Gremlin protection is not used (TAG p.30)."
            ]
        log.append(f"{carrier.name} keeps the cursed star-shaped object; the normal Gremlin event continues.")
    else:
        session.tag_star_object_gremlin_choice_pending = False
    if gremlin_protection_active(session, party):
        log.extend(consume_gremlin_protection(session, party))
        return log

    count = (roll_fn or roll_d6)() + 3
    if count <= 0:
        count = 1
    log.append(f"Invisible Gremlins steal {count} item(s).")

    priority = ("magic_items", "scrolls", "potions", "weapons", "gems")
    stolen = 0
    for _ in range(count):
        stolen_item: str | None = None
        for bucket in priority:
            for member in living:
                for item_bucket, item in _stealable_items(member):
                    if item_bucket == bucket:
                        member.inventory = [inv for inv in member.inventory if inv != item]
                        stolen_item = item
                        log.append(f"{member.name} loses {item}.")
                        stolen += 1
                        break
                if stolen_item:
                    break
            if stolen_item:
                break
        if stolen_item is None:
            for member in living:
                if member.gold >= 10:
                    member.gold -= 10
                    stolen += 1
                    log.append(f"{member.name} loses 10gp to the gremlins.")
                    break
            else:
                break

    if stolen and not any(member.inventory or member.gold for member in living):
        session.clues_found += 1
        log.append("The gremlins steal everything and leave a thank-you note (1 Clue).")
    return log
