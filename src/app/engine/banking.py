from __future__ import annotations

from dataclasses import dataclass

from ..schemas import PartyMemberState, SessionState
from .inventory import MAX_CARRIED_GOLD


@dataclass(frozen=True)
class OutsideFundsContribution:
    """A living hero's contribution from home-bank and carried funds."""

    name: str
    bank_gold: int
    carried_gold: int


def bank_access_member(session: SessionState, character_id: str | None) -> PartyMemberState | None:
    if session.mode != "exploration" or not session.camped_outside:
        session.log.append("The home bank is available only while camped outside the dungeon.")
        return None
    if not character_id:
        session.log.append("Choose a hero for the bank transaction.")
        return None
    member = next((item for item in session.party if item.character_id == character_id), None)
    if member is None:
        session.log.append("Choose a hero in the active party.")
        return None
    if member.current_life <= 0:
        session.log.append(f"{member.name} cannot use the bank while fallen.")
        return None
    return member


def deposit_bank_gold(session: SessionState, character_id: str | None, amount: int | None) -> None:
    member = bank_access_member(session, character_id)
    if member is None:
        return
    deposit = min(member.gold, amount or member.gold)
    if deposit <= 0:
        session.log.append(f"{member.name} has no carried gold to deposit.")
        return
    member.gold -= deposit
    member.bank_gold += deposit
    session.log.append(f"{member.name} deposits {deposit}gp in the home bank.")


def withdraw_bank_gold(session: SessionState, character_id: str | None, amount: int | None) -> None:
    member = bank_access_member(session, character_id)
    if member is None:
        return
    free_capacity = max(0, MAX_CARRIED_GOLD - member.gold)
    withdraw = min(member.bank_gold, amount or free_capacity, free_capacity)
    if withdraw <= 0:
        if member.bank_gold <= 0:
            session.log.append(f"{member.name} has no banked gold to withdraw.")
        else:
            session.log.append(f"{member.name} cannot carry more than {MAX_CARRIED_GOLD}gp in the dungeon.")
        return
    member.bank_gold -= withdraw
    member.gold += withdraw
    session.log.append(f"{member.name} withdraws {withdraw}gp from the home bank.")


def deposit_party_bank_gold(session: SessionState) -> None:
    if session.mode != "exploration" or not session.camped_outside:
        session.log.append("The home bank is available only while camped outside the dungeon.")
        return
    deposits: list[str] = []
    for member in sorted(session.party, key=lambda item: item.marching_order):
        if member.current_life <= 0 or member.gold <= 0:
            continue
        deposit = member.gold
        member.gold = 0
        member.bank_gold += deposit
        deposits.append(f"{member.name} {deposit}gp")
    if not deposits:
        session.log.append("No living party member has carried gold to deposit.")
        return
    session.log.append(f"Party deposits carried gold in the home bank: {', '.join(deposits)}.")


def outside_party_gold(session: SessionState) -> int:
    """Return funds available to living heroes while camped or between adventures."""
    return sum(member.gold + member.bank_gold for member in session.party if member.current_life > 0)


def take_outside_party_funds(
    session: SessionState,
    amount: int,
) -> tuple[bool, int, list[OutsideFundsContribution]]:
    """Take outside funds in marching order, using home-bank gold before carried gold."""
    available = outside_party_gold(session)
    if amount <= 0:
        return True, available, []
    if available < amount:
        return False, available, []
    remaining = amount
    contributions: list[OutsideFundsContribution] = []
    for member in sorted((item for item in session.party if item.current_life > 0), key=lambda item: item.marching_order):
        if remaining <= 0:
            break
        bank_take = min(member.bank_gold, remaining)
        if bank_take:
            member.bank_gold -= bank_take
            remaining -= bank_take
        carry_take = min(member.gold, remaining)
        if carry_take:
            member.gold -= carry_take
            remaining -= carry_take
        if bank_take or carry_take:
            contributions.append(
                OutsideFundsContribution(member.name, bank_gold=bank_take, carried_gold=carry_take)
            )
    return True, available, contributions


def spend_outside_party_gold(
    session: SessionState,
    amount: int,
    *,
    label: str,
) -> tuple[bool, list[str]]:
    """Spend shared outside funds with the established service-payment Narrative."""
    paid, _available, contributions = take_outside_party_funds(session, amount)
    if not paid:
        return False, []
    log: list[str] = []
    for contribution in contributions:
        if contribution.bank_gold:
            log.append(f"{contribution.name} pays {contribution.bank_gold}gp from home bank funds for {label}.")
        if contribution.carried_gold:
            log.append(f"{contribution.name} pays {contribution.carried_gold}gp carried outside for {label}.")
    return True, log
