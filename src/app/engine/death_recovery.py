from __future__ import annotations

from ..schemas import PartyMemberState, PendingFallenTransferState, SessionState, TileState
from .clues import sync_clue_total
from .dice import roll_d6
from .inventory import distribute_gold_among, distribute_items_among, has_illusionary_servant


RESURRECTION_COST_GP = 1000
HOLY_SYMBOL_OF_HEALING = "holy symbol of healing"


def living_party(party: list[PartyMemberState]) -> list[PartyMemberState]:
    return [member for member in party if member.current_life > 0]


def fallen_on_tile(tile: TileState, party: list[PartyMemberState]) -> list[PartyMemberState]:
    ids = set(tile.fallen_character_ids or [])
    return [member for member in party if member.character_id in ids and member.current_life <= 0]


def assign_carrier_to_rearguard(carrier: PartyMemberState, party: list[PartyMemberState]) -> None:
    living = living_party(party)
    occupied = {member.marching_order for member in living if member.character_id != carrier.character_id}
    for position in (4, 3):
        if position not in occupied:
            carrier.marching_order = position
            return
    carrier.marching_order = 4


def start_carrying_body(
    session: SessionState,
    tile: TileState,
    carrier_id: str,
    fallen_id: str,
) -> list[str]:
    log: list[str] = []
    if session.mode != "exploration":
        log.append("Bodies can only be carried during exploration.")
        return log
    if session.carried_body_id:
        log.append("Someone is already carrying a fallen comrade.")
        return log
    carrier = next((member for member in session.party if member.character_id == carrier_id), None)
    fallen = next((member for member in session.party if member.character_id == fallen_id), None)
    if carrier is None or carrier.current_life <= 0:
        log.append("Choose a living hero to carry the body.")
        return log
    if fallen is None or fallen.current_life > 0:
        log.append("That hero is not fallen.")
        return log
    if fallen_id not in (tile.fallen_character_ids or []):
        log.append(f"{fallen.name} is not on this map element.")
        return log
    tile.fallen_character_ids = [item for item in tile.fallen_character_ids if item != fallen_id]
    session.body_carrier_id = carrier_id
    session.carried_body_id = fallen_id
    assign_carrier_to_rearguard(carrier, session.party)
    log.append(
        f"{carrier.name} carries {fallen.name}'s body (rearguard; no Defense rolls while carrying)."
    )
    return log


def drop_carried_body(session: SessionState, tile: TileState) -> list[str]:
    log: list[str] = []
    if not session.carried_body_id:
        log.append("No body is being carried.")
        return log
    fallen = next((member for member in session.party if member.character_id == session.carried_body_id), None)
    if fallen is None:
        session.body_carrier_id = None
        session.carried_body_id = None
        log.append("The carried body is no longer with the party.")
        return log
    if fallen.character_id not in tile.fallen_character_ids:
        tile.fallen_character_ids.append(fallen.character_id)
    session.body_carrier_id = None
    session.carried_body_id = None
    log.append(f"{fallen.name}'s body is set down here.")
    return log


def deliver_carried_body_outside(
    session: SessionState,
    *,
    servant_owner_ids: set[str] | None = None,
) -> list[str]:
    log: list[str] = []
    if not session.carried_body_id:
        return log
    fallen = next((member for member in session.party if member.character_id == session.carried_body_id), None)
    carrier = next(
        (member for member in session.party if member.character_id == session.body_carrier_id),
        None,
    )
    if fallen is None:
        session.body_carrier_id = None
        session.carried_body_id = None
        return log
    survivors = living_party(session.party)
    if fallen.gold:
        remaining, payouts = distribute_gold_among(
            survivors,
            fallen.gold,
            servant_owner_ids=servant_owner_ids or set(),
        )
        fallen.gold = remaining
        if payouts:
            log.append(f"Gear from {fallen.name}: gold redistributed ({', '.join(payouts)}).")
    retained_for_temple: list[str] = []
    transferable_inventory = list(fallen.inventory)
    if fallen.class_id.lower() == "cleric":
        retained_for_temple = [
            item for item in transferable_inventory if HOLY_SYMBOL_OF_HEALING in item.lower()
        ]
        transferable_inventory = [
            item for item in transferable_inventory if HOLY_SYMBOL_OF_HEALING not in item.lower()
        ]
    if transferable_inventory:
        uncarried, placed = distribute_items_among(survivors, transferable_inventory)
        fallen.inventory = uncarried
        if retained_for_temple:
            fallen.inventory.extend(retained_for_temple)
            log.append(f"{fallen.name}'s Holy symbol of healing remains with the body for the cleric's temple.")
        if placed:
            log.append(f"Items from {fallen.name} redistributed: {', '.join(placed)}.")
        if uncarried:
            log.append(f"Could not carry all of {fallen.name}'s gear: {', '.join(uncarried)}.")
    elif retained_for_temple:
        fallen.inventory = retained_for_temple
        log.append(f"{fallen.name}'s Holy symbol of healing remains with the body for the cleric's temple.")
    carrier_name = carrier.name if carrier else "The party"
    log.append(
        f"{carrier_name} leaves {fallen.name}'s body just outside the dungeon. "
        f"Spend {RESURRECTION_COST_GP}gp for a resurrection ritual "
        "(d6 <= Level; L6+ automatic) to return at full Life, or continue the adventure."
    )
    if fallen.character_id not in session.fallen_outside_character_ids:
        session.fallen_outside_character_ids.append(fallen.character_id)
    session.body_carrier_id = None
    session.carried_body_id = None
    return log


def collect_party_gold(party: list[PartyMemberState], amount: int) -> tuple[bool, list[str]]:
    log: list[str] = []
    if amount <= 0:
        return True, log
    total = sum(member.gold + member.bank_gold for member in party if member.current_life > 0)
    if total < amount:
        log.append(f"The party needs {amount}gp but only has {total}gp among survivors and home bank funds.")
        return False, log
    remaining = amount
    for member in sorted(living_party(party), key=lambda item: item.marching_order):
        if remaining <= 0:
            break
        bank_take = min(member.bank_gold, remaining)
        if bank_take:
            member.bank_gold -= bank_take
            remaining -= bank_take
            log.append(f"{member.name} contributes {bank_take}gp from home bank funds toward the ritual.")
        if remaining <= 0:
            break
        carry_take = min(member.gold, remaining)
        if carry_take:
            member.gold -= carry_take
            remaining -= carry_take
            log.append(f"{member.name} contributes {carry_take}gp carried outside toward the ritual.")
    return True, log


def _remove_fallen_outside(session: SessionState, fallen_id: str) -> None:
    session.fallen_outside_character_ids = [
        item for item in session.fallen_outside_character_ids if item != fallen_id
    ]


def _clear_death_statuses(member: PartyMemberState) -> None:
    member.statuses = [
        status for status in member.statuses if status.strip().lower() not in {"fallen", "dead"}
    ]


def attempt_resurrection(
    session: SessionState,
    fallen_id: str | None,
    *,
    show_rolls: bool = True,
) -> list[str]:
    from .heroic_skill_effects import preserve_corpse_resurrection_bonus

    log: list[str] = []
    if fallen_id is None:
        log.append("Choose a fallen hero to resurrect.")
        return log
    if fallen_id not in session.fallen_outside_character_ids:
        log.append("That hero's body must be brought outside the dungeon first.")
        return log
    if fallen_id in session.permanently_lost_character_ids:
        log.append("That hero cannot be resurrected (Lady in Black oracle curse or prior burial, FD p.52).")
        return log
    fallen = next((member for member in session.party if member.character_id == fallen_id), None)
    if fallen is None or fallen.current_life > 0:
        log.append("That hero is not awaiting resurrection.")
        return log
    from .abyss_afflictions import has_vampire_rise_pending

    if has_vampire_rise_pending(fallen):
        log.append(
            f"{fallen.name} was slain by vampire level drain and cannot be resurrected until the sire vampire is destroyed."
        )
        return log
    holy_symbol_index = next(
        (
            index
            for index, item in enumerate(fallen.inventory)
            if HOLY_SYMBOL_OF_HEALING in item.lower()
        ),
        None,
    )
    church_pays = fallen.class_id.lower() == "cleric" and holy_symbol_index is not None
    if church_pays:
        symbol = fallen.inventory.pop(holy_symbol_index)
        log.append(
            f"{fallen.name}'s {symbol} is delivered with the body; the cleric's temple pays for the resurrection attempt."
        )
    else:
        paid, pay_log = collect_party_gold(session.party, RESURRECTION_COST_GP)
        log.extend(pay_log)
        if not paid:
            return log
    automatic_success = fallen.level >= 6
    bonus = preserve_corpse_resurrection_bonus(session.party)
    roll = None if automatic_success else roll_d6()
    target = fallen.level + bonus
    if show_rolls and automatic_success:
        log.append(f"Resurrection ritual: {fallen.name} is L{fallen.level}, so the ritual succeeds automatically.")
    elif show_rolls and roll is not None:
        bonus_note = f" + {bonus} Preserve Corpse" if bonus else ""
        log.append(f"Resurrection ritual: d6 = {roll} (need <= L{fallen.level}{bonus_note}).")
    if automatic_success or (roll is not None and roll <= target):
        fallen.current_life = fallen.max_life
        _clear_death_statuses(fallen)
        _remove_fallen_outside(session, fallen_id)
        from .milestones import record_resurrection

        log.extend(record_resurrection(fallen))
        log.append(f"The ritual succeeds. {fallen.name} returns at full Life and rejoins the adventure.")
    else:
        _remove_fallen_outside(session, fallen_id)
        if fallen_id not in session.permanently_lost_character_ids:
            session.permanently_lost_character_ids.append(fallen_id)
        log.append(
            f"The ritual fails. {fallen.name} is lost forever — choose a new 1st-level hero between adventures."
        )
    return log


def accept_fallen_loss(session: SessionState, fallen_id: str | None) -> list[str]:
    log: list[str] = []
    if fallen_id is None:
        log.append("Choose a fallen hero to lay to rest.")
        return log
    if fallen_id not in session.fallen_outside_character_ids:
        log.append("That hero's body must be brought outside the dungeon first.")
        return log
    fallen = next((member for member in session.party if member.character_id == fallen_id), None)
    if fallen is None or fallen.current_life > 0:
        log.append("That hero is not awaiting burial.")
        return log
    _remove_fallen_outside(session, fallen_id)
    if fallen_id not in session.permanently_lost_character_ids:
        session.permanently_lost_character_ids.append(fallen_id)
    log.append(
        f"{fallen.name} is given a proper burial and is lost forever — choose a new 1st-level hero between adventures."
    )
    return log


def queue_fallen_transfer(session: SessionState) -> None:
    """Queue held Clues or Secrets for inheritance when a party member falls."""
    pending = session.pending_fallen_transfer
    if pending is not None:
        source = next((member for member in session.party if member.character_id == pending.from_character_id), None)
        if source is None or source.current_life > 0:
            session.pending_fallen_transfer = None
        elif pending.kind == "clues" and source.clues <= 0:
            session.pending_fallen_transfer = None
        elif pending.kind == "secrets" and not source.secrets:
            session.pending_fallen_transfer = None
    if session.pending_fallen_transfer is not None or not any(member.current_life > 0 for member in session.party):
        return
    clue_source = next((member for member in session.party if member.current_life <= 0 and member.clues > 0), None)
    if clue_source is not None:
        session.pending_fallen_transfer = PendingFallenTransferState(
            from_character_id=clue_source.character_id,
            kind="clues",
        )
        return
    secret_source = next((member for member in session.party if member.current_life <= 0 and member.secrets), None)
    if secret_source is not None:
        session.pending_fallen_transfer = PendingFallenTransferState(
            from_character_id=secret_source.character_id,
            kind="secrets",
        )


def resolve_fallen_transfer(
    session: SessionState,
    *,
    to_character_id: str | None,
    kind: str | None,
) -> None:
    """Transfer a fallen member's held Clues or Secrets to a selected living hero."""
    pending = session.pending_fallen_transfer
    if pending is None:
        session.log.append("No fallen hero transfer is pending.")
        return
    source = next((member for member in session.party if member.character_id == pending.from_character_id), None)
    if source is None or source.current_life > 0:
        session.pending_fallen_transfer = None
        session.log.append("That fallen transfer is no longer needed.")
        return
    if kind and kind != pending.kind:
        session.log.append("Transfer kind does not match the pending inheritance.")
        return
    target = next(
        (member for member in session.party if member.character_id == to_character_id and member.current_life > 0),
        None,
    )
    if target is None:
        session.log.append("Choose a living hero to inherit from the fallen hero.")
        return
    if pending.kind == "clues":
        moved = max(0, source.clues)
        source.clues = 0
        target.clues += moved
        sync_clue_total(session)
        session.log.append(f"{target.name} inherits {moved} Clue(s) from fallen {source.name}.")
    else:
        moved = list(source.secrets)
        source.secrets = []
        target.secrets.extend(moved)
        session.log.append(f"{target.name} inherits {len(moved)} Secret(s) from fallen {source.name}.")
    session.pending_fallen_transfer = None
    queue_fallen_transfer(session)


def steal_from_unattended_bodies(
    session: SessionState,
    fallen_ids: list[str],
    *,
    show_rolls: bool,
) -> None:
    """Apply the standard unattended-body theft check to fallen heroes' gear."""
    for character_id in fallen_ids:
        member = next((item for item in session.party if item.character_id == character_id), None)
        if member is None or not member.inventory:
            continue
        roll = roll_d6()
        if roll >= 6:
            if show_rolls:
                session.log.append(f"No theft from {member.name}'s body (d6 = {roll}).")
            continue
        stolen = member.inventory.pop(0)
        if show_rolls:
            session.log.append(
                f"Loot stolen from {member.name}'s unattended body: {stolen} (d6 = {roll}, need 6 to avoid)."
            )
        else:
            session.log.append(f"Loot stolen from {member.name}'s unattended body: {stolen}.")
