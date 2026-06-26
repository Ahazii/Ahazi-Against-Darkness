"""Forsaken Depths Quest Table and Lady in Gray (FD p.54 / p.63)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import ActiveQuestState, SessionState, TileState
from .dice import roll_d6
from .forsaken_depths_items import grant_fd_magic_item_to_party, roll_fd_magic_item
from .forsaken_depths_map import is_fd_ruleset
from .class_abilities import resolve_social_save

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


def offer_fd_lady_in_gray(session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
    tile.fd_lady_in_gray_available = True
    if show_rolls:
        session.log.append(
            "The Lady in Gray offers a Quest — accept to roll on the Forsaken Depths Quest Table (FD p.54)."
        )


def refuse_fd_lady_in_gray(session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
    session.lady_in_gray_refused = True
    tile.fd_lady_in_gray_available = False
    if show_rolls:
        session.log.append("The Lady in Gray departs and will not return this adventure (FD p.63).")


def accept_fd_quest(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if session.mode != "exploration":
        session.log.append("Accept a Quest during exploration.")
        return False
    tile = engine._current_tile(session)
    if not tile.fd_lady_in_gray_available:
        session.log.append("The Lady in Gray is not here.")
        return False
    if session.active_quest is not None:
        session.log.append("A Quest is already in progress.")
        return False
    speaker = engine._member_by_marching_order(session, 1)
    if speaker is None:
        session.log.append("No hero is available to speak with the Lady in Gray.")
        return False
    hcl = engine._highest_character_level(session.party)
    ok, social_log = resolve_social_save(
        session,
        speaker,
        hcl,
        show_rolls=show_rolls,
        label="impress the Lady in Gray",
    )
    session.log.extend(social_log)
    if not ok:
        session.log.append("The Lady in Gray withdraws without offering a Quest.")
        return False
    roll = roll_d6()
    if show_rolls:
        session.log.append(f"Forsaken Depths Quest roll: d6 = {roll} (FD p.54).")
    row = engine.table_roller.lookup("fd_quest_table", roll)
    if row is None:
        session.log.append("FD Quest table lookup failed.")
        return False
    quest = _quest_from_fd_row(engine, session, row, tile_id=tile.id, hcl=hcl, show_rolls=show_rolls)
    session.active_quest = quest
    tile.fd_lady_in_gray_available = False
    session.log.append(f"Quest accepted: {quest.description}")
    _log_fd_quest_guidance(session, quest)
    return True


def _quest_from_fd_row(
    engine: RandomDungeonEngine,
    session: SessionState,
    row: dict,
    *,
    tile_id: str,
    hcl: int,
    show_rolls: bool,
) -> ActiveQuestState:
    key = row.get("key", "")
    description = row.get("result") or row.get("summary") or key
    quest = ActiveQuestState(tile_id=tile_id, key=key, description=description)
    if key == "fd_servitor":
        sub_roll = roll_d6()
        sub_row = engine.table_roller.lookup_fd_subtable_row("fd_minions_table", sub_roll)
        quest.fd_quest_servitor_type = (sub_row or {}).get("name", "Servitor")
        if show_rolls:
            session.log.append(f"Escaped servitor: {quest.fd_quest_servitor_type} (minions d6 = {sub_roll}).")
    elif key == "fd_defeat_enemy":
        quest.fd_quest_areas_until_spawn = 5
        quest.fd_quest_enemy_kind = "weird"
        if show_rolls:
            session.log.append(
                "Quest enemy: defeat a random Weird or Boss — appears after 5 areas or when you spend 1 Clue (FD p.54)."
            )
    elif key == "fd_lost_pages":
        quest.fd_quest_pages_found = 0
        quest.fd_quest_pages_required = 4
    elif key == "fd_three_items":
        quest.fd_quest_items_required = 3
        quest.fd_quest_items_turned_in = 0
    elif key == "fd_pilgrimage":
        quest.fd_quest_idol_visits = 0
        quest.fd_quest_idol_visits_required = 3
    elif key == "fd_dark_pits":
        pits_roll = roll_d6()
        quest.fd_quest_dark_pits_rooms = pits_roll + 3
        if show_rolls:
            session.log.append(
                f"Dark Pits quest: generate {quest.fd_quest_dark_pits_rooms} rooms (d6+3 = {pits_roll}+3) on a side sheet (FD p.54)."
            )
    return quest


def _log_fd_quest_guidance(session: SessionState, quest: ActiveQuestState) -> None:
    if quest.key == "fd_servitor":
        session.log.append(
            "Progress: spend 2 Clues to find the servitor in the next room, or 1-in-6 in a Major Foe lair; "
            "capture with Sleep or non-lethal melee at -1 (FD p.54)."
        )
    elif quest.key == "fd_defeat_enemy":
        session.log.append(
            f"Progress: {quest.fd_quest_areas_until_spawn} areas until the quest enemy ambushes, "
            "or spend 1 Clue for immediate encounter (FD p.54)."
        )
    elif quest.key == "fd_lost_pages":
        session.log.append(
            f"Progress: {quest.fd_quest_pages_found}/{quest.fd_quest_pages_required} lost pages "
            "(choose a scroll find as a page, FD p.54)."
        )
    elif quest.key == "fd_three_items":
        session.log.append(
            f"Progress: turn in {quest.fd_quest_items_turned_in}/{quest.fd_quest_items_required} newly found magic items "
            "different from gear you held at quest accept (FD p.54)."
        )
    elif quest.key == "fd_pilgrimage":
        session.log.append(
            f"Progress: {quest.fd_quest_idol_visits}/{quest.fd_quest_idol_visits_required} Cyclopean Idols visited "
            "(roll fd_cyclopean_idol_table each visit, FD p.54)."
        )
    elif quest.key == "fd_dark_pits":
        session.log.append(
            f"Progress: enter the Dark Pits side sheet ({quest.fd_quest_dark_pits_rooms} rooms), clear all occupants (FD p.54)."
        )


def claim_fd_quest_reward(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
    reward_choice: str | None = None,
) -> bool:
    quest = session.active_quest
    if quest is None or quest.reward_claimed:
        session.log.append("No FD Quest reward is ready to claim.")
        return False
    tile = engine._current_tile(session)
    if tile.id != quest.tile_id:
        session.log.append("Return to the Lady in Gray's tile to claim the Quest reward.")
        return False
    ready, reason = _fd_quest_ready(session, quest)
    if not ready:
        session.log.append(reason or "Quest not complete.")
        return False
    hcl = engine._highest_character_level(session.party)
    if quest.key == "fd_three_items":
        session.clues_found += 3
        session.xp_rolls_pending += 1
        session.log.append("Quest reward: 3 Clues and 1 pending XP roll (FD p.54).")
    elif quest.key == "fd_pilgrimage":
        if reward_choice == "heroic_item":
            item, log = roll_fd_magic_item(engine, session, hcl=hcl, show_rolls=show_rolls)
            session.log.extend(log)
            holder = next((m for m in session.party if m.current_life > 0), session.party[0])
            grant_fd_magic_item_to_party(engine, session, holder, item, show_rolls=show_rolls)
            session.log.append(f"Pilgrimage reward: {item} (FD p.54).")
        else:
            session.xp_rolls_pending += len([m for m in session.party if m.current_life > 0])
            session.log.append("Pilgrimage reward: 1 pending XP roll for each living hero (FD p.54).")
    elif quest.key == "fd_dark_pits":
        session.xp_rolls_pending += 1
        session.log.append(
            "Dark Pits reward: 1 pending XP roll and a scroll with a spell of your choice (log spell on party sheet, FD p.54)."
        )
    else:
        session.xp_rolls_pending += 1
        item, log = roll_fd_magic_item(engine, session, hcl=hcl, show_rolls=show_rolls)
        session.log.extend(log)
        holder = next((m for m in session.party if m.current_life > 0), session.party[0])
        grant_fd_magic_item_to_party(engine, session, holder, item, show_rolls=show_rolls)
        session.log.append(f"Quest reward: 1 XP roll and {item} (FD p.54).")
    quest.completed = True
    quest.reward_claimed = True
    session.active_quest = None
    return True


def _fd_quest_ready(session: SessionState, quest: ActiveQuestState) -> tuple[bool, str]:
    if quest.key == "fd_servitor":
        return quest.fd_quest_servitor_found, "Bring the captured servitor back to the Lady in Gray."
    if quest.key == "fd_defeat_enemy":
        return quest.fd_quest_enemy_defeated, "Defeat the quest enemy and return here."
    if quest.key == "fd_lost_pages":
        ok = quest.fd_quest_pages_found >= quest.fd_quest_pages_required
        return ok, f"Find {quest.fd_quest_pages_required} lost pages ({quest.fd_quest_pages_found} so far)."
    if quest.key == "fd_three_items":
        ok = quest.fd_quest_items_turned_in >= quest.fd_quest_items_required
        return ok, f"Turn in {quest.fd_quest_items_required} new magic items ({quest.fd_quest_items_turned_in} so far)."
    if quest.key == "fd_pilgrimage":
        ok = quest.fd_quest_idol_visits >= quest.fd_quest_idol_visits_required
        return ok, f"Visit {quest.fd_quest_idol_visits_required} idols ({quest.fd_quest_idol_visits} so far)."
    if quest.key == "fd_dark_pits":
        return quest.fd_quest_dark_pits_cleared, "Clear the Dark Pits side dungeon and return."
    return quest.completed, "Quest not complete."


def report_fd_idol_visit(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    quest = session.active_quest
    if quest is None or quest.key != "fd_pilgrimage":
        session.log.append("No Pilgrimage quest is tracking idol visits.")
        return False
    roll = roll_d6()
    row = engine.table_roller.lookup("fd_cyclopean_idol_table", roll)
    name = (row or {}).get("name") or f"roll {roll}"
    summary = (row or {}).get("summary") or (row or {}).get("result") or ""
    quest.fd_quest_idol_visits += 1
    session.log.append(
        f"Cyclopean Idol visit {quest.fd_quest_idol_visits}/{quest.fd_quest_idol_visits_required}: "
        f"d6 = {roll} → {name}. {summary} (FD p.52)."
    )
    if row and row.get("key") == "walking_idol":
        session.log.append("Walking Idol — spawn and resolve combat manually if needed (FD p.52).")
    return True


def tick_fd_quest_on_area_enter(session: SessionState, *, show_rolls: bool = True) -> None:
    quest = session.active_quest
    if quest is None or quest.key != "fd_defeat_enemy" or quest.fd_quest_enemy_defeated:
        return
    if quest.fd_quest_areas_until_spawn <= 0:
        return
    quest.fd_quest_areas_until_spawn -= 1
    if quest.fd_quest_areas_until_spawn <= 0 and show_rolls:
        session.log.append(
            "Quest enemy ambush — spawn and resolve the designated Weird or Boss (FD p.54)."
        )


def note_fd_quest_enemy_defeated(session: SessionState, *, show_rolls: bool = True) -> None:
    quest = session.active_quest
    if quest is None or quest.key != "fd_defeat_enemy" or quest.fd_quest_enemy_defeated:
        return
    quest.fd_quest_enemy_defeated = True
    if show_rolls:
        session.log.append("Quest enemy defeated — return to the Lady in Gray (FD p.54).")


def note_fd_quest_page_found(session: SessionState, *, show_rolls: bool = True) -> bool:
    quest = session.active_quest
    if quest is None or quest.key != "fd_lost_pages":
        return False
    if quest.fd_quest_pages_found >= quest.fd_quest_pages_required:
        return False
    quest.fd_quest_pages_found += 1
    if show_rolls:
        session.log.append(
            f"Lost page recovered ({quest.fd_quest_pages_found}/{quest.fd_quest_pages_required}, FD p.54)."
        )
    return True


def turn_in_fd_quest_item(
    engine: RandomDungeonEngine,
    session: SessionState,
    item_name: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    quest = session.active_quest
    if quest is None or quest.key != "fd_three_items":
        session.log.append("No three-items Quest is tracking turn-ins.")
        return False
    if not item_name:
        session.log.append("Choose a newly found magic item to turn in.")
        return False
    if quest.fd_quest_items_turned_in >= quest.fd_quest_items_required:
        session.log.append("All three quest items are already turned in.")
        return False
    tile = engine._current_tile(session)
    if tile.id != quest.tile_id:
        session.log.append("Return to the Lady in Gray to turn in magic items.")
        return False
    for member in session.party:
        if item_name in member.inventory:
            member.inventory.remove(item_name)
            quest.fd_quest_items_turned_in += 1
            if show_rolls:
                session.log.append(
                    f"Quest turn-in: {item_name} ({quest.fd_quest_items_turned_in}/"
                    f"{quest.fd_quest_items_required}, FD p.54)."
                )
            return True
    session.log.append(f"No party member carries {item_name}.")
    return False
