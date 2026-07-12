from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..schemas import SessionState, TileState
from .equipment_effects import enforce_single_pole_carrier
from .special_items import equip_glittering_crystal, is_glittering_crystal
from .treasure_awards import distribute_claimed_treasure


@dataclass(frozen=True)
class TreasureClaimCallbacks:
    spawn_wandering_monsters: Callable[[SessionState, TileState], None]
    apply_hidden_complication: Callable[[SessionState, TileState, str, int], None]
    highest_character_level: Callable[[list], int]
    final_boss_gold_cap: Callable[[TileState], int | None]
    servant_owner_ids: Callable[[SessionState], set[str]]
    record_item_acquired: Callable[[object, str], list[str]]
    fire_imported_treasure_trigger: Callable[[SessionState, TileState], None]
    roll_d6: Callable[[], int]


def claim_treasure(session: SessionState, tile: TileState, *, callbacks: TreasureClaimCallbacks) -> None:
    """Validate, distribute, and record treasure from the current map element."""
    if tile.pending_treasure_choice:
        session.log.append("Choose the treasure outcome before claiming.")
        return
    if tile.fd_jackpot_wandering_on_claim:
        tile.fd_jackpot_wandering_on_claim = False
        wander_roll = callbacks.roll_d6()
        session.log.append(
            f"Jackpot looting: d6 = {wander_roll} — 4-in-6 wandering monsters while looting (FD p.62)."
        )
        if wander_roll >= 4:
            callbacks.spawn_wandering_monsters(session, tile)
            if session.mode != "exploration":
                return
    if tile.hidden_treasure_complication_effect_pending:
        effect = tile.hidden_treasure_complication_effect_pending
        callbacks.apply_hidden_complication(session, tile, effect, callbacks.highest_character_level(session.party))
        if tile.hidden_treasure_alarm_pending or any(enemy.life > 0 for enemy in tile.enemies):
            return
    if tile.trap_key and not tile.trap_resolved:
        session.log.append("Resolve the trap before claiming treasure.")
        return
    if tile.treasure_claimed:
        session.log.append("Treasure has already been claimed here.")
        return
    if tile.deal_treasure_forbidden:
        session.log.append("Treasure here is forbidden by Deal with a Foe.")
        return
    if not tile.treasure_gold and not tile.treasure_items:
        session.log.append(tile.treasure_summary or "There is no treasure here.")
        return
    survivors = sorted((member for member in session.party if member.current_life > 0), key=lambda member: member.marching_order)
    if not survivors:
        session.log.append("There is no one left to carry treasure.")
        return
    gold_total = tile.treasure_gold
    gold_cap = callbacks.final_boss_gold_cap(tile)
    if gold_cap is not None and gold_total > gold_cap:
        session.log.append(f"Final Boss treasure corrected from {gold_total}gp to {gold_cap}gp to match the recorded treasure.")
        gold_total = gold_cap
        tile.treasure_gold = gold_cap
    distribution = distribute_claimed_treasure(survivors, gold_total=gold_total, items=list(tile.treasure_items), servant_owner_ids=callbacks.servant_owner_ids(session))
    item_recipients: list[str] = []
    for member in survivors:
        for item in distribution.assigned_items.get(member.character_id, []):
            item_recipients.append(f"{member.name} receives {item}")
            session.log.extend(callbacks.record_item_acquired(member, item))
    if session.xp_system == "old_school" and gold_total:
        session.old_school_xp_tally += gold_total
        session.log.append(f"Old School XP +{gold_total} from treasure (tally {session.old_school_xp_tally}).")
    tile.treasure_gold = distribution.remaining_gold
    tile.treasure_items = distribution.uncarried_items
    tile.treasure_claimed = distribution.remaining_gold <= 0 and not distribution.uncarried_items
    summary = tile.treasure_summary or "Treasure"
    session.log.append(f"Treasure {'claimed' if tile.treasure_claimed else 'partially claimed'}: {summary}")
    if distribution.payouts:
        session.log.append(f"Gold split: {', '.join(distribution.payouts)}.")
    if distribution.remaining_gold:
        session.log.append(f"{distribution.remaining_gold}gp left behind (each hero carries at most 200gp).")
    if distribution.placed_items:
        item_list = "; ".join(item_recipients) if item_recipients else ", ".join(distribution.placed_items)
        session.log.append(f"Items assigned: {item_list}.")
    for member in survivors:
        if any(is_glittering_crystal(item) for item in member.inventory) and "Glittering Crystal" not in member.statuses:
            session.log.extend(equip_glittering_crystal(member))
    if distribution.uncarried_items:
        session.log.append(f"Could not carry: {', '.join(distribution.uncarried_items)} (weapon/shield limits or no free carrier).")
    session.log.extend(enforce_single_pole_carrier(session.party, session=session))
    if tile.treasure_claimed:
        tile.objects = [item for item in tile.objects if "treasure" not in item.lower()]
    if session.adventure_type == "imported":
        callbacks.fire_imported_treasure_trigger(session, tile)
