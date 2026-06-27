"""Lex the Cambion shop — soul tax (BoS entry 4) and opposition curses (BoS entry 7, TCOTFD)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState
from .courtship_book_of_secrets import lex_shop_catalog
from .dice import roll_d6

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


def _lex_item_names() -> frozenset[str]:
    return frozenset(str(row.get("item", "")) for row in lex_shop_catalog())


def record_lex_grant(session: SessionState, member: PartyMemberState, item: str) -> None:
    token = f"{member.character_id}|{item}"
    if token not in session.courtship_lex_granted_items:
        session.courtship_lex_granted_items.append(token)


def is_lex_granted_item(session: SessionState, member: PartyMemberState, item: str) -> bool:
    token = f"{member.character_id}|{item}"
    return token in session.courtship_lex_granted_items


def register_lex_oath(session: SessionState, member: PartyMemberState) -> None:
    if member.character_id not in session.courtship_lex_oath_sworn:
        session.courtship_lex_oath_sworn.append(member.character_id)
    opponents = list(session.courtship_lex_opponents or [])
    if member.character_id in opponents:
        opponents.remove(member.character_id)
        session.courtship_lex_opponents = opponents


def register_lex_opponents(session: SessionState, character_ids: list[str]) -> None:
    sworn = set(session.courtship_lex_oath_sworn or [])
    opponents = list(session.courtship_lex_opponents or [])
    for character_id in character_ids:
        if character_id in sworn or character_id in opponents:
            continue
        opponents.append(character_id)
    session.courtship_lex_opponents = opponents


def apply_lex_opposition_curses(
    session: SessionState,
    *,
    engine: RandomDungeonEngine | None = None,
    show_rolls: bool = True,
) -> list[str]:
    """BoS entry 4 / 7 — Curse of Tamas Zeya for characters who oppose Lex."""
    from .courtship_book_of_secrets import apply_curse_of_tamas_zeya

    log: list[str] = []
    for character_id in list(session.courtship_lex_opponents or []):
        victim = next((member for member in session.party if member.character_id == character_id), None)
        if victim is None or victim.current_life <= 0:
            continue
        log.extend(apply_curse_of_tamas_zeya(session, victim, engine=engine, show_rolls=show_rolls))
    session.courtship_lex_opponents = []
    return log


def track_lex_combat_natural(
    session: SessionState,
    member: PartyMemberState,
    *,
    attack_natural: int | None = None,
    defense_natural: int | None = None,
    engine: RandomDungeonEngine | None = None,
    show_rolls: bool = True,
) -> list[str]:
    """BoS entry 7 — natural 6 on both Attack and Defense same turn curses the hero."""
    if not session.courtship_lex_combat_active:
        return []
    rolls = dict(session.courtship_lex_turn_rolls.get(member.character_id, {}))
    if attack_natural is not None:
        rolls["attack"] = attack_natural == 6
    if defense_natural is not None:
        rolls["defense"] = defense_natural == 6
    session.courtship_lex_turn_rolls[member.character_id] = rolls
    if rolls.get("attack") and rolls.get("defense"):
        from .courtship_book_of_secrets import apply_curse_of_tamas_zeya

        session.log.append(
            f"{member.name} rolls unmodified 6s on Attack and Defense — the Curse of Tamas Zeya (BoS entry 7, TCOTFD)."
        )
        return apply_curse_of_tamas_zeya(session, member, engine=engine, show_rolls=show_rolls)
    return []


def begin_lex_combat_turn(session: SessionState) -> None:
    if session.courtship_lex_combat_active:
        session.courtship_lex_turn_rolls = {}


def apply_lex_soul_tax_if_needed(
    session: SessionState,
    member: PartyMemberState,
    item: str,
    *,
    engine: RandomDungeonEngine | None = None,
    show_rolls: bool = True,
) -> bool:
    """Roll BoS entry 4 soul tax on first use of a Lex-bought item. Returns False if the hero dies."""
    if item not in _lex_item_names():
        return True
    if not is_lex_granted_item(session, member, item):
        return True
    tax_key = f"{member.character_id}|{item}"
    if tax_key in session.courtship_lex_soul_taxed:
        return True
    session.courtship_lex_soul_taxed.append(tax_key)
    roll = roll_d6()
    if show_rolls:
        session.log.append(
            f"Lex soul tax d6 = {roll} on first use of {item} (BoS entry 4, TCOTFD)."
        )
    if roll == 6:
        session.log.append(
            "The item works perfectly — an innocent dies in Norindaal and Lex devours their soul (BoS entry 4, TCOTFD)."
        )
        return True
    if roll == 1:
        member.current_life = 0
        session.log.append(
            f"{member.name} dies as Lex claims their soul for using his merchandise (BoS entry 4, TCOTFD)."
        )
        if session.courtship_lex_opponents:
            session.log.append("Lex strikes his opponents with the Curse of Tamas Zeya (BoS entry 16, TCOTFD).")
            apply_lex_opposition_curses(session, engine=engine, show_rolls=show_rolls)
        if session.courtship_demesne_active and engine is not None:
            from .courtship_demesne import _return_to_meadows_and_roll

            session.log.append("Return to the Meadows Encounter table and roll again (BoS entry 4, TCOTFD).")
            _return_to_meadows_and_roll(engine, session, show_rolls=show_rolls)
        return False
    session.log.append("Lex's item functions without further soul price this time (BoS entry 4, TCOTFD).")
    return True


def start_lex_cambion_combat(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    """BoS entry 7 — attack Lex the Cambion instead of trading (TCOTFD p.61)."""
    from .courtship_demesne import _combat_tile, _living_party, _return_to_meadows_and_roll, _spawn_courtship

    if not session.courtship_demesne_active:
        session.log.append("Lex the Cambion is only encountered in the Blossoms' Demesne.")
        return False
    tile = _combat_tile(engine, session)
    if tile is None:
        session.log.append("No Demesne tile is active for Lex the Cambion.")
        return False
    register_lex_opponents(session, [member.character_id for member in _living_party(session)])
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    session.courtship_lex_combat_active = True
    session.courtship_lex_turn_rolls = {}
    hcl = engine._highest_character_level(session.party)
    spawn = {
        "template": "Lex the Cambion",
        "count": "1",
        "category": "weird",
        "level_delta": 6,
        "life_delta": 3,
    }
    _spawn_courtship(engine, session, tile, spawn, hcl=hcl, show_rolls=show_rolls)
    if show_rolls:
        session.log.append("Lex the Cambion fights back — his insects and sleep attacks await (BoS entry 7, TCOTFD).")
    return True


def finish_lex_cambion_combat(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> None:
    if not session.courtship_lex_combat_active:
        return
    session.courtship_lex_combat_active = False
    session.courtship_lex_turn_rolls = {}
    if show_rolls:
        session.log.append("Lex withdraws — return to the Meadows Encounter table (BoS entry 7, TCOTFD).")
    from .courtship_demesne import _return_to_meadows_and_roll

    _return_to_meadows_and_roll(engine, session, show_rolls=show_rolls)
