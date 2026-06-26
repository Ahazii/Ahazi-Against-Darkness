"""Forsaken Depths Cyclopean Idol table (FD p.52)."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState, TileState
from .dice import roll_d3, roll_d6, roll_formula

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

HEROIC_SPELLS = [
    "Blessing",
    "Chaos Teleport",
    "Destroy Unliving",
    "Escape",
    "Fireball",
    "Fly",
    "Heal",
    "Invisibility",
    "Lightning",
    "Mass Teleport",
    "Protection",
    "Sleep",
    "Stone to Flesh",
    "Teleport",
    "Wall of Stone",
]


def _living_party(session: SessionState) -> list[PartyMemberState]:
    return [member for member in session.party if member.current_life > 0]


def _idol_roll(session: SessionState) -> int:
    roll = roll_d6()
    if session.fd_idol_walking_flee_shift:
        roll = min(6, roll + 1)
        session.fd_idol_walking_flee_shift = False
        session.log.append("Walking Idol fled earlier — shift next idol roll +1 (FD p.52).")
    return roll


def roll_fd_cyclopean_idol(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState | None,
    *,
    hcl: int | None = None,
    show_rolls: bool = True,
    count_pilgrimage: bool = False,
) -> dict | None:
    if hcl is None:
        hcl = engine._highest_character_level(session.party)
    roll = _idol_roll(session)
    row = engine.table_roller.lookup("fd_cyclopean_idol_table", roll)
    if row is None:
        session.log.append(f"Cyclopean Idol d6 = {roll} — no table row (FD p.52).")
        return None
    name = row.get("name") or f"roll {roll}"
    summary = row.get("summary") or row.get("result") or ""
    if show_rolls:
        session.log.append(f"Cyclopean Idol: d6 = {roll} → {name}. {summary}")
    if count_pilgrimage:
        quest = session.active_quest
        if quest and quest.key == "fd_pilgrimage":
            quest.fd_quest_idol_visits += 1
            session.log.append(
                f"Pilgrimage progress: {quest.fd_quest_idol_visits}/{quest.fd_quest_idol_visits_required} idols (FD p.54)."
            )
    apply_fd_cyclopean_idol_outcome(engine, session, tile, row, hcl=hcl, show_rolls=show_rolls)
    if tile is not None:
        tile.fd_cyclopean_idol_resolved = True
    return row


def apply_fd_cyclopean_idol_outcome(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState | None,
    row: dict,
    *,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    key = row.get("key", "")
    if key == "climb_for_gems":
        _climb_for_gems(session, hcl=hcl, show_rolls=show_rolls)
    elif key == "walking_idol":
        if tile is not None:
            _spawn_walking_idol(engine, session, tile, hcl=hcl, show_rolls=show_rolls)
    elif key == "secret_door":
        session.fd_idol_pending_choice = "secret_clue"
        session.log.append(
            "Pedestal secret door — spend 1 Clue or Search to open a d6+3 room Forsaken Ruins side sheet (FD p.52)."
        )
    elif key == "life_sap":
        _life_sap(engine, session, tile, show_rolls=show_rolls)
    elif key == "lady_in_black":
        session.fd_idol_pending_choice = "lady_sacrifice"
        session.log.append(
            "Lady in Black — sacrifice a Heroic magic item for 1 Clue, or accept her cursed quest (FD p.52)."
        )
    elif key == "heroic_spell_relief":
        spell = random.choice(HEROIC_SPELLS)
        session.fd_idol_heroic_spell = spell
        session.fd_idol_pending_choice = "heroic_learn"
        session.log.append(
            f"Heroic spell bas-relief: {spell} is etched on the pedestal — spend an XP roll to learn it (FD p.52)."
        )


def resolve_fd_idol_choice(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState | None,
    choice: str | None,
    *,
    item_name: str | None = None,
    show_rolls: bool = True,
) -> bool:
    pending = session.fd_idol_pending_choice
    if not pending:
        session.log.append("No Cyclopean Idol choice is pending.")
        return False
    hcl = engine._highest_character_level(session.party)
    if pending == "secret_clue":
        if choice == "secret_clue":
            if not engine._spend_clues(session, 1):
                session.log.append("Need 1 Clue to open the pedestal secret door (FD p.52).")
                return False
            session.fd_idol_pending_choice = None
            return _open_idol_secret_door(engine, session, tile, show_rolls=show_rolls)
        if choice == "secret_search":
            session.fd_idol_pending_choice = None
            if tile is None:
                return False
            engine._search(session, search_choice="secret_door", show_rolls=show_rolls)
            if tile.hidden_treasure_alarm_pending or "Secret door" in " ".join(tile.objects).lower():
                return _open_idol_secret_door(engine, session, tile, show_rolls=show_rolls)
            session.log.append("Search did not reveal the pedestal secret door (FD p.52).")
            return False
    if pending == "lady_sacrifice":
        if choice == "lady_sacrifice":
            member = _living_party(session)[0] if _living_party(session) else None
            if member is None or not item_name:
                session.log.append("Choose a Heroic item to sacrifice to the Lady in Black.")
                return False
            matched = next((item for item in member.inventory if item_name.lower() in item.lower()), None)
            if matched is None:
                session.log.append(f"{member.name} does not carry {item_name}.")
                return False
            member.inventory.remove(matched)
            session.fd_idol_pending_choice = None
            if tile is not None:
                engine._grant_clue(session, tile, character_id=member.character_id)
            session.log.append(f"{member.name} sacrifices {matched} for 1 Clue (FD p.52).")
            return True
        if choice == "lady_curse":
            session.fd_idol_pending_choice = None
            session.fd_lady_in_black_cursed = True
            session.log.append(
                "Lady in Black cursed quest accepted — defeat a Weird or Boss before adventure end or suffer doom (FD p.52)."
            )
            return True
    if pending == "heroic_learn":
        if choice == "heroic_learn":
            member = _living_party(session)[0] if _living_party(session) else None
            spell = session.fd_idol_heroic_spell or "Heroic spell"
            session.fd_idol_pending_choice = None
            session.fd_idol_heroic_spell = None
            if member is None:
                return False
            if session.xp_rolls_pending < 1:
                session.log.append(f"Need 1 XP roll to learn {spell} from the bas-relief (FD p.52).")
                return False
            session.xp_rolls_pending -= 1
            if spell not in member.spells:
                member.spells.append(spell)
            session.log.append(f"{member.name} learns {spell} from the Cyclopean Idol (FD p.52).")
            return True
    session.log.append("Unknown Cyclopean Idol choice.")
    return False


def note_walking_idol_fled(session: SessionState, *, show_rolls: bool = True) -> None:
    session.fd_idol_walking_flee_shift = True
    if show_rolls:
        session.log.append("The Walking Idol flees — shift your next Cyclopean Idol roll +1 (FD p.52).")


def _climb_for_gems(session: SessionState, *, hcl: int, show_rolls: bool) -> None:
    from .forsaken_depths_events import _fd_save_vs_level

    level = hcl + 1
    for member in _living_party(session):
        failed, logs = _fd_save_vs_level(member, level, label="Climb for Gems", show_rolls=show_rolls)
        session.log.extend(logs)
        if failed:
            continue
        if roll_d6() <= 3:
            gems = roll_d3()
            gold = sum(roll_formula("d6") * 20 for _ in range(gems))
            member.gold += gold
            session.log.append(f"{member.name} finds {gems} gem(s) worth {gold} gp in the idol's head (FD p.52).")
        elif show_rolls:
            session.log.append(f"{member.name} reaches the head but finds no gems (3-in-6 miss, FD p.52).")


def _life_sap(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState | None,
    *,
    show_rolls: bool,
) -> None:
    for member in _living_party(session):
        member.current_life = max(0, member.current_life - 1)
        session.log.append(
            f"{member.name} loses 1 Life to the idol's sap ({member.current_life}/{member.max_life}, FD p.52)."
        )
        if roll_d6() == 1 and tile is not None:
            engine._grant_clue(session, tile, character_id=member.character_id, add_object=False)


def _spawn_walking_idol(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool,
) -> None:
    spawned = engine._spawn_from_template_name(
        session,
        table_key="fd_weird",
        template_name="Walking Idol",
        count=1,
        hcl=hcl,
        category="weird",
    )
    if not spawned:
        session.log.append("Walking Idol missing from bestiary (FD p.52).")
        return
    tile.enemies.extend(spawned)
    tile.initial_enemy_count = len(tile.enemies)
    tile.content_key = "fd_weird"
    if "Walking Idol" not in tile.objects:
        tile.objects.append("Walking Idol")
    if show_rolls:
        session.log.append("Walking Idol animates and attacks to the death (FD p.52).")
    if session.mode == "exploration":
        engine._announce_encounter(session, tile, show_rolls=show_rolls)


def _open_idol_secret_door(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState | None,
    *,
    show_rolls: bool,
) -> bool:
    if tile is None:
        session.log.append("No tile for the pedestal secret door.")
        return False
    from .dice import roll_d6
    from .forsaken_depths_side_sheet import enter_fd_side_sheet

    rooms = roll_d6() + 3
    if show_rolls:
        session.log.append(f"The pedestal opens into forsaken ruins ({rooms} rooms, FD p.52).")
    return enter_fd_side_sheet(
        engine,
        session,
        tile,
        kind="ruins",
        room_budget=rooms,
        force=True,
        show_rolls=show_rolls,
    )
