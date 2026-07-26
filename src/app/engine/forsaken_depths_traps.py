"""Forsaken Depths traps and player-choice event consequences."""

from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState, TileState
from .class_combat import armor_defense_bonus, save_modifier
from .dice import roll_d6, roll_exploding_for_level
from .experience import tier_for_level
from .madness import _grant_madness
from .party_life import apply_party_life_loss

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


FD_SOULBOUND_PREFIX = "FD Soulbound:"


def _living_party(session: SessionState) -> list[PartyMemberState]:
    return [member for member in session.party if member.current_life > 0]


def _member(session: SessionState, character_id: str | None) -> PartyMemberState | None:
    if not character_id:
        return None
    return next((member for member in session.party if member.character_id == character_id), None)


def _ordered_living(session: SessionState) -> list[PartyMemberState]:
    return sorted(_living_party(session), key=lambda member: member.marching_order)


def _half_level(member: PartyMemberState) -> int:
    return max(1, member.level // 2)


def _fd_trap_modifier(member: PartyMemberState, trap_key: str) -> int:
    class_id = member.class_id.lower()
    modifier = _half_level(member) + save_modifier(member)
    if trap_key == "fd_magic_resistant_liquid":
        if class_id == "elf":
            modifier += 1
        if class_id == "wizard":
            modifier += member.level
    elif trap_key == "fd_oblivion_trapdoor":
        if class_id == "rogue":
            modifier += member.level
    elif trap_key == "fd_obsidian_disk":
        if class_id == "rogue":
            modifier += member.level
        modifier += armor_defense_bonus(member)
    return modifier


def _fd_save(
    session: SessionState,
    member: PartyMemberState,
    trap_level: int,
    trap_key: str,
    label: str,
    *,
    show_rolls: bool,
) -> tuple[bool, list[str]]:
    modifier = _fd_trap_modifier(member, trap_key)
    total, rolls = roll_exploding_for_level(member, session=session)
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier} vs L{trap_level}."
        )
    failed = rolls[0] == 1 or total + modifier < trap_level
    if failed and member.class_id.lower() == "halfling":
        best_total = total
        best_rolls = rolls
        rerolls = 2 if trap_key == "fd_disintegration_blast" else 1
        for index in range(rerolls):
            reroll_total, reroll_values = roll_exploding_for_level(member, session=session)
            if show_rolls:
                log.append(
                    f"Halfling trap reroll {index + 1}/{rerolls}: {member.name} rolls "
                    f"{' + '.join(str(value) for value in reroll_values)} + {modifier}."
                )
            if reroll_total > best_total:
                best_total = reroll_total
                best_rolls = reroll_values
        failed = best_rolls[0] == 1 or best_total + modifier < trap_level
    log.append(f"{member.name} {'fails' if failed else 'passes'} the {label}.")
    return failed, log


def _random_living(session: SessionState) -> PartyMemberState | None:
    living = _living_party(session)
    return random.choice(living) if living else None


def _permanent_magic_items(member: PartyMemberState) -> list[str]:
    from .item_disposition import ItemDisposition, eligible_inventory_items

    disposable = ("potion", "scroll", "food", "ration", "wine", "arrow", "bolt", "gem", "jewelry", "silk")
    magic_markers = (
        "magic",
        "legendary",
        "heroic",
        "ring",
        "wand",
        "staff",
        "mask of thar-tizan",
        "shield",
        "gauntlet",
        "robe",
        "crystal",
        "deepbane",
        "boat",
    )
    items: list[str] = []
    for item in member.inventory:
        lower = item.lower()
        if any(token in lower for token in disposable):
            continue
        if any(token in lower for token in magic_markers):
            items.append(item)
    return eligible_inventory_items(items, ItemDisposition.SACRIFICE)


def _add_status(member: PartyMemberState, status: str) -> None:
    if status not in member.statuses:
        member.statuses.append(status)


def _soulbound_tile_id(member: PartyMemberState) -> str | None:
    for status in member.statuses:
        if status.startswith(FD_SOULBOUND_PREFIX):
            return status.split(":", 1)[1].strip() or None
    return None


def _clear_soulbound(member: PartyMemberState) -> None:
    member.statuses = [status for status in member.statuses if not status.startswith(FD_SOULBOUND_PREFIX)]


def pending_fd_player_choice(session: SessionState) -> bool:
    return bool(
        session.fd_winds_of_despair_pending
        or session.fd_disintegration_pending
        or session.fd_soulbinding_pending
        or session.fd_ruins_psychic_pending
    )


def pending_fd_player_choice_label(session: SessionState) -> str:
    if session.fd_disintegration_pending:
        return "Resolve the Disintegration Blast choice before continuing."
    if session.fd_winds_of_despair_pending:
        return "Resolve Winds of Despair choices before continuing."
    if session.fd_soulbinding_pending:
        return "Resolve Soulbinding consequences before continuing."
    if session.fd_ruins_psychic_pending:
        return "Resolve Psychic Residue choices before continuing."
    return "Resolve the pending Forsaken Depths choice before continuing."


def resolve_fd_trap(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool,
) -> tuple[list[str], bool]:
    trap_key = tile.trap_key or ""
    trap_level = tile.trap_level or engine._highest_character_level(session.party)
    hcl = engine._highest_character_level(session.party)
    log: list[str] = []
    if trap_key == "fd_magic_resistant_liquid":
        target = _random_living(session)
        if target is None:
            return ["There is no one left to trigger the trap."], False
        failed, save_log = _fd_save(session, target, trap_level, trap_key, "Magic Resistant Liquid Save", show_rolls=show_rolls)
        log.extend(save_log)
        if failed:
            _add_status(target, "FD Magic Resistant Liquid (no spells/prayers, 6 rooms)")
            log.append(f"{target.name} is splashed: no spells, prayers, scroll casts, or magic-item casts for six rooms (FD p.58).")
        return log, False
    if trap_key == "fd_oblivion_trapdoor":
        ordered = _ordered_living(session)
        if not ordered:
            return ["There is no one left to trigger the trap."], False
        lead = ordered[0]
        failed, save_log = _fd_save(session, lead, trap_level, trap_key, "Oblivion Trapdoor Save", show_rolls=show_rolls)
        log.extend(save_log)
        if not failed:
            return log, False
        applied = apply_party_life_loss(session, lead, 1, log=log)
        log.append(f"{lead.name} falls into the trapdoor and takes {applied} damage (FD p.58).")
        rememberers: list[str] = []
        for ally in ordered[1:]:
            ally_failed, ally_log = _fd_save(session, ally, trap_level, trap_key, "Remember fallen ally", show_rolls=show_rolls)
            log.extend(ally_log)
            if not ally_failed:
                rememberers.append(ally.name)
        if rememberers:
            log.append(f"{', '.join(rememberers)} remember {lead.name} and help them out of the trapdoor (FD p.58).")
        else:
            lead.current_life = 0
            lead.inventory = []
            log.append(f"No one remembers {lead.name}; the oblivion magic erases them and their equipment forever (FD p.58).")
        return log, False
    if trap_key == "fd_obsidian_disk":
        for member in _living_party(session):
            failed, save_log = _fd_save(session, member, trap_level, trap_key, "Obsidian Disk Save", show_rolls=show_rolls)
            log.extend(save_log)
            if failed:
                damage = tier_for_level(hcl) + 2
                applied = apply_party_life_loss(session, member, damage, log=log)
                log.append(f"{member.name} takes {applied} damage from the Obsidian Disk (FD p.58).")
        pieces = roll_d6()
        tile.treasure_items.extend([f"Obsidian masterwork knife ({index + 1})" for index in range(pieces)])
        tile.treasure_claimed = False
        log.append(f"The disk shatters into {pieces} piece(s), each usable as a brittle masterwork knife worth 10 gp (FD p.58).")
        return log, False
    if trap_key == "fd_beast_cage":
        ordered = _ordered_living(session)
        if not ordered:
            return ["There is no one left to trigger the trap."], False
        lead = ordered[0]
        failed, save_log = _fd_save(session, lead, trap_level, trap_key, "Beast Cage Save", show_rolls=show_rolls)
        log.extend(save_log)
        if failed:
            sub_roll = roll_d6()
            sub_row = engine.table_roller.lookup_fd_subtable_row("fd_weird_table", sub_roll)
            if sub_row:
                spawned = engine._fd_spawn_from_table_row(session, sub_row, hcl)
                for enemy in spawned:
                    if "surprise" not in enemy.tags:
                        enemy.tags.append("surprise")
                    if "no_treasure" not in enemy.tags:
                        enemy.tags.append("no_treasure")
                tile.enemies.extend(spawned)
                log.append(f"Beast Cage: {sub_row.get('name', 'Weird Monster')} attacks with surprise and no treasure (FD p.58).")
        return log, False
    if trap_key == "fd_soulbinding_trap":
        ordered = _ordered_living(session)
        if not ordered:
            return ["There is no one left to trigger the trap."], False
        rear = ordered[-1]
        failed, save_log = _fd_save(session, rear, trap_level, trap_key, "Soulbinding Trap Save", show_rolls=show_rolls)
        log.extend(save_log)
        if failed:
            if rear.class_id.lower() in {"kukla", "construct", "golem", "eldritch_puppet"}:
                log.append(f"{rear.name} is artificial and immune to the Soulbinding Trap (FD p.58).")
            else:
                _add_status(rear, f"{FD_SOULBOUND_PREFIX} {tile.id}")
                log.append(
                    f"{rear.name} is soulbound to this room. Away from it, choose 1 Life loss or 1 Madness for each area moved (FD p.58)."
                )
        return log, False
    if trap_key == "fd_disintegration_blast":
        target = _random_living(session)
        if target is None:
            return ["There is no one left to trigger the trap."], False
        failed, save_log = _fd_save(session, target, trap_level, trap_key, "Disintegration Blast Save", show_rolls=show_rolls)
        log.extend(save_log)
        if failed:
            items = _permanent_magic_items(target)
            if items:
                session.fd_disintegration_pending = {
                    "tile_id": tile.id,
                    "character_id": target.character_id,
                    "items": items,
                }
                log.append(
                    f"{target.name} may sacrifice one permanent magic item instead of being incinerated (FD p.58)."
                )
                return log, True
            target.current_life = 0
            _add_status(target, "Incinerated (no resurrection)")
            log.append(f"{target.name} is incinerated and may not be resurrected (FD p.58).")
        return log, False
    return engine.table_roller.resolve_trap(
        trap_key,
        trap_level,
        session.party,
        engine._marching_order_ids(session),
        show_rolls=show_rolls,
        explain_math=False,
        session=session,
    ).log, False


def resolve_fd_disintegration_choice(
    session: SessionState,
    choice: str | None,
    item_name: str | None,
    *,
    show_rolls: bool = True,
) -> None:
    pending = dict(session.fd_disintegration_pending or {})
    member = _member(session, str(pending.get("character_id") or ""))
    if member is None or member.current_life <= 0:
        session.fd_disintegration_pending = {}
        session.log.append("No living hero has a Disintegration Blast choice pending.")
        return
    if choice == "sacrifice_item":
        choices = list(pending.get("items") or [])
        if not item_name or item_name not in choices or item_name not in member.inventory:
            session.log.append(f"Choose a permanent magic item to sacrifice: {', '.join(choices)}.")
            return
        from .item_disposition import ItemDisposition, remove_item_for_disposition

        removed = remove_item_for_disposition(
            member,
            disposition=ItemDisposition.SACRIFICE,
            item_name=item_name,
        )
        if not removed.removed:
            session.log.append(removed.blocked_reason or f"{member.name} no longer carries {item_name}.")
            return
        damage = tier_for_level(member.level) + 1
        applied = apply_party_life_loss(session, member, damage, log=session.log)
        session.fd_disintegration_pending = {}
        session.log.append(f"{member.name}'s {item_name} disintegrates; concussion deals {applied} damage (FD p.58).")
        return
    if choice == "incinerate":
        member.current_life = 0
        _add_status(member, "Incinerated (no resurrection)")
        session.fd_disintegration_pending = {}
        session.log.append(f"{member.name} is incinerated and may not be resurrected (FD p.58).")
        return
    session.log.append("Choose whether to sacrifice a permanent magic item or accept incineration.")


def offer_winds_of_despair_choices(session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
    pending: dict[str, str] = {}
    for member in _living_party(session):
        pending[member.character_id] = tile.id
    session.fd_winds_of_despair_pending.update(pending)
    if show_rolls:
        session.log.append("Winds of Despair: each living hero must choose 1 Madness or 2 Life loss (FD p.63).")


def resolve_fd_winds_choice(
    session: SessionState,
    character_id: str | None,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> None:
    if not character_id or character_id not in session.fd_winds_of_despair_pending:
        session.log.append("No Winds of Despair choice is pending for that hero.")
        return
    member = _member(session, character_id)
    if member is None or member.current_life <= 0:
        session.fd_winds_of_despair_pending.pop(character_id, None)
        session.log.append("That hero can no longer resolve Winds of Despair.")
        return
    if choice == "life":
        applied = apply_party_life_loss(session, member, 2, log=session.log)
        session.fd_winds_of_despair_pending.pop(character_id, None)
        session.log.append(f"Winds of Despair: {member.name} loses {applied} Life (FD p.63).")
        return
    if choice == "madness":
        session.fd_winds_of_despair_pending.pop(character_id, None)
        session.log.extend(_grant_madness(session, member, source="Winds of Despair", log=[]))
        return
    session.log.append("Choose 1 Madness or 2 Life loss for Winds of Despair (FD p.63).")


def check_fd_soulbinding_on_area_enter(session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
    for member in _living_party(session):
        next_statuses: list[str] = []
        for status in member.statuses:
            match = re.match(r"FD Magic Resistant Liquid .*?(\d+) rooms?", status)
            if not match:
                next_statuses.append(status)
                continue
            remaining = max(0, int(match.group(1)) - 1)
            if remaining > 0:
                next_statuses.append(f"FD Magic Resistant Liquid (no spells/prayers, {remaining} rooms)")
            elif show_rolls:
                session.log.append(f"{member.name}'s magic resistant liquid has worn off (FD p.58).")
        member.statuses = next_statuses
    for member in _living_party(session):
        origin = _soulbound_tile_id(member)
        if not origin or origin == tile.id:
            continue
        if session.fd_soulbinding_pending.get(member.character_id) == tile.id:
            continue
        session.fd_soulbinding_pending[member.character_id] = tile.id
        if show_rolls:
            session.log.append(
                f"Soulbinding: {member.name} is away from their bound room; choose 1 Life loss or 1 Madness (FD p.58)."
            )


def resolve_fd_soulbinding_choice(
    session: SessionState,
    character_id: str | None,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> None:
    if not character_id or character_id not in session.fd_soulbinding_pending:
        session.log.append("No Soulbinding choice is pending for that hero.")
        return
    member = _member(session, character_id)
    if member is None or member.current_life <= 0:
        session.fd_soulbinding_pending.pop(character_id, None)
        session.log.append("That hero can no longer resolve Soulbinding.")
        return
    if choice == "life":
        applied = apply_party_life_loss(session, member, 1, log=session.log)
        session.fd_soulbinding_pending.pop(character_id, None)
        session.log.append(f"Soulbinding: {member.name} loses {applied} Life (FD p.58).")
        return
    if choice == "madness":
        session.fd_soulbinding_pending.pop(character_id, None)
        session.log.extend(_grant_madness(session, member, source="Soulbinding Trap", log=[]))
        return
    session.log.append("Choose 1 Life loss or 1 Madness for Soulbinding (FD p.58).")


def clear_fd_soulbinding_with_blessing(session: SessionState, member: PartyMemberState) -> list[str]:
    before = list(member.statuses)
    member.statuses = [status for status in member.statuses if not status.startswith(FD_SOULBOUND_PREFIX)]
    removed = len(before) - len(member.statuses)
    if not removed:
        return []
    session.fd_soulbinding_pending.pop(member.character_id, None)
    return [f"Blessing frees {member.name} from Soulbinding (FD p.58)."]
