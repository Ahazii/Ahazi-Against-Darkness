"""Forsaken Depths Quest Table and Lady in Gray (FD p.54 / p.63)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import ActiveQuestState, SessionState, TileState
from .dice import roll_d6
from .forsaken_depths_items import grant_fd_magic_item_to_party, roll_fd_magic_item
from .forsaken_depths_map import is_fd_ruleset
from .class_abilities import resolve_social_save
from .scrolls import is_scroll_item

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
        quest.fd_quest_enemy_spawned = False
        if show_rolls:
            session.log.append(
                "Quest enemy: defeat a random Weird or Boss — ambush after 5 areas or spend 1 Clue now (FD p.54)."
            )
    elif key == "fd_lost_pages":
        quest.fd_quest_pages_found = 0
        quest.fd_quest_pages_required = 4
    elif key == "fd_three_items":
        quest.fd_quest_items_required = 3
        quest.fd_quest_items_turned_in = 0
        quest.fd_quest_inventory_snapshot = _inventory_snapshot(session)
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


def _inventory_snapshot(session: SessionState) -> dict[str, list[str]]:
    return {member.character_id: list(member.inventory) for member in session.party}


def _held_at_quest_accept(quest: ActiveQuestState, item_name: str) -> bool:
    snapshot = quest.fd_quest_inventory_snapshot or {}
    for items in snapshot.values():
        if item_name in items:
            return True
    return False


def _is_fd_quest_magic_item(item_name: str) -> bool:
    from .magic_armor import is_magic_armor
    from .magic_items import is_charged_magic_item
    from .magic_weapons import is_magic_weapon

    lower = item_name.lower()
    if is_magic_weapon(item_name) or is_magic_armor(item_name) or is_charged_magic_item(item_name):
        return True
    if "humming crystal" in lower:
        return True
    if lower.startswith("legendary "):
        return True
    return "magic " in lower and any(
        token in lower for token in ("armor", "wand", "ring", "weapon", "shield")
    )


def eligible_fd_quest_turn_in_items(session: SessionState, quest: ActiveQuestState) -> list[str]:
    if quest.key != "fd_three_items":
        return []
    eligible: list[str] = []
    for member in session.party:
        for item in member.inventory:
            if (
                item not in eligible
                and _is_fd_quest_magic_item(item)
                and not _held_at_quest_accept(quest, item)
            ):
                eligible.append(item)
    return eligible


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
    from .forsaken_depths_cyclopean_idol import roll_fd_cyclopean_idol

    tile_id = quest.tile_id
    tile = engine._tile_by_id(session, tile_id) if tile_id else None
    roll_fd_cyclopean_idol(
        engine,
        session,
        tile,
        show_rolls=show_rolls,
        count_pilgrimage=True,
    )
    return True


def tick_fd_quest_on_area_enter(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    quest = session.active_quest
    if quest is None or quest.key != "fd_defeat_enemy" or quest.fd_quest_enemy_defeated:
        return
    if quest.fd_quest_enemy_spawned or quest.fd_quest_areas_until_spawn <= 0:
        return
    quest.fd_quest_areas_until_spawn -= 1
    if quest.fd_quest_areas_until_spawn <= 0:
        spawn_fd_quest_enemy(engine, session, tile, show_rolls=show_rolls)


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
            if not _is_fd_quest_magic_item(item_name):
                session.log.append(f"{item_name} is not a magic item (FD p.54).")
                return False
            if _held_at_quest_accept(quest, item_name):
                session.log.append(
                    f"{item_name} was already in the party at quest accept — find a newly looted item (FD p.54)."
                )
                return False
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


def spawn_fd_quest_enemy(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> bool:
    quest = session.active_quest
    if (
        quest is None
        or quest.key != "fd_defeat_enemy"
        or quest.fd_quest_enemy_spawned
        or quest.fd_quest_enemy_defeated
    ):
        return False
    hcl = engine._highest_character_level(session.party)
    category = "boss" if roll_d6() >= 4 else "weird"
    table_key = "fd_boss_table" if category == "boss" else "fd_weird_table"
    row = engine.table_roller.lookup(table_key, roll_d6())
    if row is None:
        session.log.append("Quest enemy spawn failed — no table row.")
        return False
    spawned = engine._fd_spawn_from_table_row(session, row, hcl)
    if not spawned:
        session.log.append("Quest enemy spawn failed — bestiary row missing.")
        return False
    for enemy in spawned:
        if "fd_quest_enemy" not in enemy.tags:
            enemy.tags.append("fd_quest_enemy")
    tile.enemies.extend(spawned)
    tile.initial_enemy_count = len(tile.enemies)
    quest.fd_quest_enemy_spawned = True
    quest.fd_quest_enemy_kind = category
    name = row.get("name") or category
    if show_rolls:
        session.log.append(
            f"Quest enemy ambush: {name} ({category}, FD p.54). Defeat it and return to the Lady in Gray."
        )
    if session.mode == "exploration":
        engine._announce_encounter(session, tile, show_rolls=show_rolls)
    return True


def spawn_fd_quest_servitor(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> bool:
    quest = session.active_quest
    if quest is None or quest.key != "fd_servitor" or quest.fd_quest_servitor_found:
        return False
    hcl = engine._highest_character_level(session.party)
    template_name = quest.fd_quest_servitor_type or "Servitor"
    monsters = engine.rules.monsters()
    table = monsters.get("fd_minions") or []
    if not any(entry.get("name") == template_name for entry in table):
        template_name = table[0]["name"] if table else template_name
    spawned = engine._spawn_from_template_name(
        session,
        table_key="fd_minions",
        template_name=template_name,
        count=1,
        hcl=hcl,
        category="minions",
    )
    if not spawned:
        session.log.append(f"Quest servitor spawn failed for {template_name}.")
        return False
    for enemy in spawned:
        if "fd_quest_servitor" not in enemy.tags:
            enemy.tags.append("fd_quest_servitor")
    tile.enemies.extend(spawned)
    tile.initial_enemy_count = len(tile.enemies)
    if show_rolls:
        session.log.append(
            f"Escaped servitor located: {template_name}. Capture with Sleep or subdual attacks (FD p.54)."
        )
    if session.mode == "exploration" and tile.enemies:
        engine._announce_encounter(session, tile, show_rolls=show_rolls)
    return True


def spend_fd_quest_clue_for_enemy(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    quest = session.active_quest
    if quest is None or quest.key != "fd_defeat_enemy" or quest.fd_quest_enemy_defeated:
        session.log.append("No defeat-enemy Quest is tracking an ambush.")
        return False
    if quest.fd_quest_enemy_spawned:
        session.log.append("The quest enemy has already appeared.")
        return False
    if not engine._spend_clues(session, 1):
        session.log.append("Need 1 Clue to summon the quest enemy immediately (FD p.54).")
        return False
    tile = engine._current_tile(session)
    if tile is None:
        return False
    if show_rolls:
        session.log.append("1 Clue spent — the quest enemy ambushes now (FD p.54).")
    return spawn_fd_quest_enemy(engine, session, tile, show_rolls=show_rolls)


def spend_fd_quest_clues_for_servitor(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    quest = session.active_quest
    if quest is None or quest.key != "fd_servitor" or quest.fd_quest_servitor_found:
        session.log.append("No servitor Quest is tracking a search.")
        return False
    if quest.fd_quest_servitor_pending_room:
        session.log.append("The servitor will appear in the next room you enter.")
        return False
    if not engine._spend_clues(session, 2):
        session.log.append("Need 2 Clues to locate the servitor in the next room (FD p.54).")
        return False
    quest.fd_quest_servitor_pending_room = True
    if show_rolls:
        session.log.append(
            "2 Clues spent — the escaped servitor is in the next room you enter (FD p.54)."
        )
    return True


def maybe_spawn_fd_quest_servitor_in_lair(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    quest = session.active_quest
    if (
        quest is None
        or quest.key != "fd_servitor"
        or quest.fd_quest_servitor_found
        or quest.fd_quest_servitor_pending_room
    ):
        return
    if not is_fd_ruleset(session):
        return
    if roll_d6() != 1:
        return
    if show_rolls:
        session.log.append("Major Foe lair — 1-in-6: the escaped servitor is here (FD p.54).")
    spawn_fd_quest_servitor(engine, session, tile, show_rolls=show_rolls)


def fd_quest_on_new_tile_entered(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> None:
    quest = session.active_quest
    if quest is None or quest.key != "fd_servitor" or quest.fd_quest_servitor_found:
        return
    if not quest.fd_quest_servitor_pending_room:
        return
    quest.fd_quest_servitor_pending_room = False
    spawn_fd_quest_servitor(engine, session, tile, show_rolls=show_rolls)


def recover_fd_lost_page(
    engine: RandomDungeonEngine,
    session: SessionState,
    item_name: str | None,
    *,
    from_treasure: bool = False,
    show_rolls: bool = True,
) -> bool:
    quest = session.active_quest
    if quest is None or quest.key != "fd_lost_pages":
        session.log.append("No lost-pages Quest is tracking recovery.")
        return False
    if quest.fd_quest_pages_found >= quest.fd_quest_pages_required:
        session.log.append("All lost pages are already recovered.")
        return False
    if not item_name:
        session.log.append("Choose a scroll to count as a lost page.")
        return False
    tile = engine._current_tile(session)
    if tile is None:
        return False
    if from_treasure:
        if item_name not in tile.treasure_items:
            session.log.append(f"{item_name} is not in the staged treasure here.")
            return False
        if not is_scroll_item(item_name):
            session.log.append("Only scroll finds can count as lost pages (FD p.54).")
            return False
        tile.treasure_items.remove(item_name)
        if tile.treasure_summary:
            tile.treasure_summary = tile.treasure_summary.replace(item_name, "").strip(" ;")
    else:
        holder = next((m for m in session.party if item_name in m.inventory), None)
        if holder is None:
            session.log.append(f"No party member carries {item_name}.")
            return False
        if not is_scroll_item(item_name):
            session.log.append("Only scrolls can count as lost pages (FD p.54).")
            return False
        holder.inventory.remove(item_name)
    note_fd_quest_page_found(session, show_rolls=show_rolls)
    if show_rolls:
        session.log.append(f"Scroll counted as a lost page instead of loot ({item_name}, FD p.54).")
    return True


def update_fd_quest_on_combat_end(
    session: SessionState,
    defeated: list,
    *,
    show_rolls: bool = True,
) -> None:
    quest = session.active_quest
    if quest is None or not is_fd_ruleset(session):
        return
    for enemy in defeated:
        if "fd_quest_servitor" in enemy.tags and enemy.life <= 0 and enemy.subdued:
            quest.fd_quest_servitor_found = True
            if show_rolls:
                session.log.append(
                    f"Quest servitor {enemy.name} captured — return to the Lady in Gray (FD p.54)."
                )
        if "fd_quest_enemy" in enemy.tags and enemy.life <= 0 and not enemy.subdued:
            note_fd_quest_enemy_defeated(session, show_rolls=show_rolls)
