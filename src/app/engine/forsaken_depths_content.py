"""Forsaken Depths room content helpers: events, hallucinations, citadel, ruins."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ..schemas import SessionState, TileState
from .dice import roll_2d6, roll_d6, roll_d10, roll_formula
from .madness import apply_madness_gain, madness_points

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


def roll_fd_citadel(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState | None = None,
    *,
    show_rolls: bool = True,
) -> dict | None:
    roll = roll_d6()
    row = engine.table_roller.lookup("fd_citadel_table", roll)
    if row is None:
        return None
    key = row.get("key", f"citadel_{roll}")
    session.fd_citadel_type = key
    room_formula = str(row.get("room_count", "3d6"))
    if room_formula == "10+2d6":
        room_count = 10 + roll_formula("2d6")
    else:
        room_count = roll_formula(room_formula)
    session.fd_citadel_room_count = room_count
    if tile is not None:
        session.fd_citadel_entry_tile_id = tile.id
    name = row.get("name") or key.replace("_", " ").title()
    if show_rolls:
        session.log.append(
            f"Citadel roll: d6 = {roll} → {name} ({session.fd_citadel_room_count} rooms). "
            f"Map on a separate sheet (FD p.60)."
        )
        summary = row.get("summary") or row.get("result") or ""
        if summary:
            session.log.append(summary)
    return row


def apply_fd_hallucination(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    roll = roll_d6()
    row = engine.table_roller.lookup("fd_hallucination_table", roll)
    if row is None:
        session.log.append("Hallucination (FD p.55): no table row.")
        tile.resolved = True
        return
    name = row.get("name") or row.get("key") or f"roll {roll}"
    summary = row.get("summary") or row.get("result") or ""
    if show_rolls:
        session.log.append(f"Hallucination roll: d6 = {roll} → {name} (FD p.55). {summary}")
    key = row.get("key", "")
    living = [member for member in session.party if member.current_life > 0]
    if not living:
        tile.resolved = True
        return
    victim = random.choice(living)
    tier = max(1, (hcl + 2) // 3)
    if key in {"horrors_from_beyond", "revelations"}:
        before = madness_points(victim)
        session.log.extend(
            apply_madness_gain(
                session,
                victim,
                source=f"Hallucination: {name}",
                show_rolls=show_rolls,
            )
        )
        if key == "horrors_from_beyond" and madness_points(victim) == before:
            for _ in range(tier):
                session.log.extend(
                    apply_madness_gain(
                        session,
                        victim,
                        source="Horrors from Beyond",
                        show_rolls=show_rolls,
                    )
                )
        if key == "revelations":
            session.fd_hallucination_revelation_available = True
            session.log.append(
                f"{victim.name} may spend the Revelation benefit once this adventure (FD p.55)."
            )
    elif key == "surrounded_by_foes":
        session.log.append(
            f"{victim.name} hallucinates that allies are foes for d3+1 turns — resolve manually (FD p.55)."
        )
    elif key == "fingers_are_worms":
        session.log.append(f"{victim.name} drops held items and stares at their hands (FD p.55).")
    elif key == "no_danger_here":
        session.log.append(
            f"{victim.name} ignores the next danger source automatically (FD p.55)."
        )
    tile.resolved = True


FD_REVELATION_CHOICES: dict[str, str] = {
    "negate_ambush": "Negate an ambush (automatic success).",
    "auto_defend": "Automatically defend once.",
    "auto_save": "Automatically succeed on one Save.",
    "auto_search": "Automatically succeed on one search.",
    "preview_room": "Preview the next room's content before entering.",
}


def spend_fd_hallucination_revelation(
    session: SessionState,
    choice: str,
    *,
    show_rolls: bool = True,
) -> bool:
    from .forsaken_depths_revelation import spend_fd_hallucination_revelation as _spend

    return _spend(session, choice, show_rolls=show_rolls)


def apply_fd_event(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    event_key = tile.special_event_key
    if not event_key:
        return
    row = next(
        (
            item
            for item in engine.table_roller.tables.get("fd_event_table", [])
            if item.get("key") == event_key
        ),
        None,
    )
    name = row.get("name") if row else event_key
    summary = (row or {}).get("summary") or tile.special_event_summary or ""
    if show_rolls:
        session.log.append(f"Forsaken Depths Event: {name} (FD p.63). {summary}")

    if event_key == "lady_in_gray":
        from .forsaken_depths_quest import _fd_active_quest_count, offer_fd_lady_in_gray

        if _fd_active_quest_count(session) >= 2:
            session.log.append("The Lady in Gray waits while your Forsaken Depths Quests are unfinished.")
        elif session.lady_in_gray_refused:
            session.log.append("The Lady in Gray will not appear again this adventure.")
        else:
            from .forsaken_depths_quest import offer_fd_lady_in_gray

            offer_fd_lady_in_gray(session, tile, show_rolls=show_rolls)
    elif event_key == "winds_of_despair":
        for member in session.party:
            if member.current_life <= 0:
                continue
            if madness_points(member) < 3:
                session.log.extend(
                    apply_madness_gain(
                        session,
                        member,
                        source="Winds of Despair",
                        show_rolls=show_rolls,
                    )
                )
            else:
                member.current_life = max(0, member.current_life - 2)
                session.log.append(f"{member.name} loses 2 Life to the Winds of Despair (FD p.63).")
    elif event_key == "something_stirs":
        session.fd_stirs_in_darkness_remaining = 6
        session.log.append(
            "Something stirs in the Darkness — empty rooms may hold river encounters for the next 6 areas (FD p.63)."
        )
    elif event_key == "labyrinth_shifts":
        from .forsaken_depths_events import apply_fd_event_labyrinth_shift

        apply_fd_event_labyrinth_shift(engine, session, show_rolls=show_rolls)
    elif event_key == "flood":
        from .forsaken_depths_events import apply_fd_event_flood

        apply_fd_event_flood(engine, session, hcl=hcl, show_rolls=show_rolls)
    elif event_key == "earthquake":
        from .forsaken_depths_events import apply_fd_event_earthquake

        apply_fd_event_earthquake(session, hcl=hcl, show_rolls=show_rolls)
    elif event_key == "nightmare_mist":
        from .forsaken_depths_events import apply_fd_event_nightmare_mist

        apply_fd_event_nightmare_mist(engine, session, tile, hcl=hcl, show_rolls=show_rolls)
        tile.environment_event_resolved = True
        tile.resolved = True
        return
    elif event_key == "the_portal":
        from .forsaken_depths_events import offer_fd_event_portal

        offer_fd_event_portal(session, tile, show_rolls=show_rolls)
    elif event_key == "the_passage":
        roll_fd_citadel(engine, session, tile, show_rolls=show_rolls)
        if show_rolls and session.fd_citadel_type and session.fd_citadel_entry_tile_id == tile.id:
            session.log.append("The Passage opens a Citadel entrance here. Use Enter Citadel sheet when ready.")
        trap_chance = max(1, (hcl + 2) // 3)
        trap_roll = roll_d6()
        if show_rolls:
            session.log.append(
                f"The Passage trap chance: d6 = {trap_roll}; trap on {trap_chance}-in-6 (FD p.63)."
            )
        if trap_roll <= trap_chance:
            trap = engine.table_roller.roll_fd_trap(hcl, show_rolls=show_rolls, explain_math=False)
            tile.trap_key = trap.trap_key
            tile.trap_level = trap.trap_level
            if trap.summary not in tile.objects:
                tile.objects.append(trap.summary)
            session.log.append(f"The passage trap: {trap.summary}")
        elif show_rolls:
            session.log.append("The Passage is clear of corridor traps.")
    elif event_key == "hidden_treasure_chamber":
        weird_roll = roll_d6()
        sub_row = engine.table_roller.lookup_fd_subtable_row("fd_weird_table", weird_roll)
        if sub_row:
            spawned = engine._fd_spawn_from_table_row(session, sub_row, hcl)
            for enemy in spawned:
                enemy.life += 4
                if "fight_to_death" not in enemy.tags:
                    enemy.tags.append("fight_to_death")
            tile.enemies.extend(spawned)
            from .forsaken_depths_events import setup_fd_hidden_treasure_chamber

            setup_fd_hidden_treasure_chamber(engine, session, tile, hcl=hcl, show_rolls=show_rolls)
            if spawned and session.mode == "exploration":
                engine._announce_encounter(session, tile, show_rolls=show_rolls)

    tile.environment_event_resolved = True
    tile.resolved = True


def apply_ruins_room_content(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    roll = roll_2d6()
    row = engine.table_roller.lookup("fd_ruins_content_table", roll)
    if row is None:
        if show_rolls:
            session.log.append(f"Ruins content roll: 2d6 = {roll} — no row (FD p.56).")
        return
    name = row.get("name") or row.get("key") or f"roll {roll}"
    summary = row.get("summary") or row.get("result") or ""
    if show_rolls:
        session.log.append(f"Ruins content roll: 2d6 = {roll} → {name} (FD p.56). {summary}")
    key = row.get("key", "")
    subtable = row.get("subtable")
    if subtable:
        sub_roll = roll_d6()
        sub_row = engine.table_roller.lookup_fd_subtable_row(subtable, sub_roll)
        if sub_row:
            count_bonus = 2 if key == "ruins_more_servitors" else 0
            if count_bonus and sub_row.get("enemy_category") == "minions":
                sub_row = dict(sub_row)
                sub_row["count"] = "2d6+4"
            spawned = engine._fd_spawn_from_table_row(session, sub_row, hcl)
            tile.enemies.extend(spawned)
            if spawned and session.mode == "exploration":
                engine._announce_encounter(session, tile, show_rolls=show_rolls)
    elif key == "ruins_trap":
        trap = engine.table_roller.roll_fd_trap(hcl, show_rolls=show_rolls, explain_math=False)
        tile.trap_key = trap.trap_key
        tile.trap_level = trap.trap_level
        if trap.summary not in tile.objects:
            tile.objects.append(trap.summary)
        if tile.tile_type == "room" and roll_d6() <= 2:
            session.log.append("Ruins trap room: 2-in-6 chance of treasure after the trap (FD p.56).")
    elif key == "ruins_secret_passage":
        from .forsaken_depths_secret_passage import offer_fd_ruins_secret_passage

        offer_fd_ruins_secret_passage(session, tile, show_rolls=show_rolls)
    elif key == "ruins_event":
        event_roll = roll_d10()
        event_row = engine.table_roller.lookup("fd_event_table", event_roll)
        if event_row:
            tile.special_event_key = event_row.get("key")
            tile.special_event_summary = event_row.get("summary") or event_row.get("result")
            apply_fd_event(engine, session, tile, hcl=hcl, show_rolls=show_rolls)


def _fd_tile_is_empty(tile: TileState) -> bool:
    if tile.enemies:
        return False
    return tile.content_key in {"empty", "searchable", "fd_empty"}


def maybe_fd_stirs_on_tile_enter(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    if session.fd_stirs_in_darkness_remaining <= 0:
        return
    if tile.id in session.fd_stirs_processed_tile_ids:
        return
    session.fd_stirs_processed_tile_ids.append(tile.id)
    session.fd_stirs_in_darkness_remaining -= 1
    if not _fd_tile_is_empty(tile):
        return
    if roll_d6() > 3:
        if show_rolls:
            session.log.append(
                f"Something stirs in the Darkness — this empty area stays quiet "
                f"({session.fd_stirs_in_darkness_remaining} area(s) remain, FD p.63)."
            )
        return
    sub_roll = roll_d6()
    row = engine.table_roller.lookup_fd_subtable_row("fd_river_encounter_table", sub_roll)
    if row is None:
        return
    if show_rolls:
        session.log.append(
            f"Something stirs — river encounter d6={sub_roll}: {row.get('name', 'foes')} "
            f"({session.fd_stirs_in_darkness_remaining} area(s) remain, FD p.63)."
        )
    spawned = engine._fd_spawn_from_table_row(session, row, hcl)
    for enemy in spawned:
        if "surprise" not in enemy.tags and roll_d6() == 1:
            enemy.tags.append("surprise")
    tile.enemies.extend(spawned)
    if spawned and session.mode == "exploration":
        engine._announce_encounter(session, tile, show_rolls=show_rolls)
