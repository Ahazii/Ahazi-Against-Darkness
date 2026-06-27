"""Lex the Cambion shop — soul tax on first item use (BoS entry 4, TCOTFD)."""

from __future__ import annotations

from ..schemas import PartyMemberState, SessionState
from .courtship_book_of_secrets import lex_shop_catalog
from .dice import roll_d6


def _lex_item_names() -> frozenset[str]:
    return frozenset(str(row.get("item", "")) for row in lex_shop_catalog())


def record_lex_grant(session: SessionState, member: PartyMemberState, item: str) -> None:
    token = f"{member.character_id}|{item}"
    if token not in session.courtship_lex_granted_items:
        session.courtship_lex_granted_items.append(token)


def is_lex_granted_item(session: SessionState, member: PartyMemberState, item: str) -> bool:
    token = f"{member.character_id}|{item}"
    return token in session.courtship_lex_granted_items


def apply_lex_soul_tax_if_needed(
    session: SessionState,
    member: PartyMemberState,
    item: str,
    *,
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
        return False
    session.log.append("Lex's item functions without further soul price this time (BoS entry 4, TCOTFD).")
    return True
