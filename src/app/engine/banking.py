from __future__ import annotations

from ..schemas import PartyMemberState, SessionState
from .inventory import MAX_CARRIED_GOLD


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
