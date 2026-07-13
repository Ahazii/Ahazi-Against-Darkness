from __future__ import annotations

from collections.abc import Callable

from ..schemas import PartyMemberState, SessionState, TileState
from .class_abilities import bulwark_magical_healing_blocked
from .gem_items import remove_inventory_item


def use_healing_potion(session: SessionState, member: PartyMemberState, potion_name: str, *, tile: TileState | None, show_rolls: bool, citadel_blocks_healing: Callable[[SessionState, TileState | None], str | None], apply_soul_tax: Callable[[SessionState, PartyMemberState, str, bool], bool]) -> None:
    """Resolve a healing potion after the caller has selected an eligible user."""
    if blocked := citadel_blocks_healing(session, tile):
        session.log.append(blocked)
        return
    if blocked := bulwark_magical_healing_blocked(session, member):
        session.log.append(blocked)
        return
    if member.character_id in session.potion_used_character_ids:
        session.log.append(f"{member.name} already drank a Potion of Healing this adventure.")
        return
    if not apply_soul_tax(session, member, potion_name, show_rolls):
        return
    remove_inventory_item(member, potion_name)
    lost_life = member.max_life - member.current_life
    member.current_life = member.max_life
    session.potion_used_character_ids.append(member.character_id)
    if show_rolls:
        session.log.append(f"{member.name} drinks {potion_name} and restores {lost_life} Life ({member.current_life}/{member.max_life}).")
