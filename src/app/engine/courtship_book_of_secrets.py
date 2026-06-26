"""Courtship Book of Secrets entry handlers (TCOTFD)."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_d3, roll_d6, roll_formula

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

_ROOT = Path(__file__).resolve().parents[2] / "data" / "rules"
_CATALOG: dict[str, Any] | None = None


def _catalog() -> dict[str, Any]:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = json.loads((_ROOT / "courtship_book_of_secrets.json").read_text(encoding="utf-8"))
    return _CATALOG


def book_entry(entry: int | str) -> dict[str, Any] | None:
    return _catalog().get("entries", {}).get(str(entry))


def apply_book_of_secrets_entry(
    session: SessionState,
    entry: int,
    party: list[PartyMemberState],
    *,
    show_rolls: bool = True,
    choice: str | None = None,
    engine: RandomDungeonEngine | None = None,
) -> list[str]:
    row = book_entry(entry)
    if row is None:
        session.log.append(f"Book of Secrets entry {entry} is not catalogued.")
        return []
    effect = row.get("effect", "")
    log: list[str] = []
    if show_rolls:
        log.append(f"Book of Secrets entry {entry}: {row.get('name', effect)} (TCOTFD).")

    if effect == "leave_demesne":
        if engine is not None:
            from .courtship_demesne import leave_courtship_demesne

            leave_courtship_demesne(engine, session, show_rolls=show_rolls)
        return log

    if effect == "queens_vault_acerbic":
        session.courtship_pending_choice = "queens_vault"
        session.courtship_pending_choice_label = "Break silver lock (ACERBIC)"
        log.append("Use Break Vault Lock on the Demesne panel (TCOTFD).")
        return log

    if effect == "queens_vault_open":
        session.courtship_pending_choice = "queens_vault"
        session.courtship_pending_choice_label = "Open with TRUELOVE"
        log.append("Use Open Queen's Vault on the Demesne panel (TCOTFD).")
        return log

    if effect == "matron_reward":
        from .courtship_demesne import _grant_party_clues

        if engine is not None:
            tile = engine._tile_by_id(session, session.courtship_return_tile_id or "")
            _grant_party_clues(engine, session, tile, roll_d3() + 1, show_rolls=show_rolls)
        log.append("Gain a Blossoms spell scroll (TCOTFD).")
        return log

    if effect == "truelove_pandora_harvest":
        from .courtship_demesne import _grant_party_clues

        if engine is not None:
            tile = engine._tile_by_id(session, session.courtship_return_tile_id or "")
            _grant_party_clues(engine, session, tile, roll_d3() + 2, show_rolls=show_rolls)
        return log

    if effect == "secret_trail":
        from .courtship_demesne import spend_courtship_secret_trail_clue

        if engine is not None:
            spend_courtship_secret_trail_clue(engine, session, show_rolls=show_rolls)
        return log

    if effect == "hidden_pathway":
        session.courtship_pending_pathways = ["riverside"]
        log.append("Hidden pathway to Riverside discovered (TCOTFD).")
        return log

    if effect == "frost_roses_keepsake":
        for member in party:
            if member.current_life <= 0:
                continue
            heal = roll_d6()
            member.current_life = min(member.max_life, member.current_life + heal)
            log.append(f"{member.name} heals {heal} Life from the Keepsake (TCOTFD).")
        return log

    if effect == "mark_acerbic":
        from .courtship_demesne import _add_keyword

        _add_keyword(session, "ACERBIC")
        return log

    if effect == "mirror_demon_first_hit":
        roll = roll_d6()
        if show_rolls:
            log.append(f"Mirror reflection d6 = {roll} (TCOTFD).")
        victim = next((m for m in party if m.current_life > 0), None)
        if victim is None:
            return log
        if roll <= 3:
            if victim.inventory:
                lost = victim.inventory.pop(random.randrange(len(victim.inventory)))
                log.append(f"{victim.name} loses {lost} to the mirror (TCOTFD).")
        else:
            from .courtship_demesne import _grant_party_clues

            if engine is not None:
                tile = engine._tile_by_id(session, session.courtship_return_tile_id or "")
                _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
        return log

    if effect == "lady_of_lament":
        session.courtship_pending_choice = "lady_of_lament"
        session.courtship_pending_choice_label = "Lady of Lament"
        return log

    if effect == "disturbing_altar":
        session.courtship_pending_choice = "disturbing_altar"
        session.courtship_pending_choice_label = "Disturbing Altar"
        log.append("Choose: gain d3 Clues or 1 Madness (TCOTFD).")
        return log

    if effect == "ominous_omen":
        if "ominous_omen" not in session.courtship_uniques_seen:
            session.courtship_uniques_seen.append("ominous_omen")
            for member in party:
                if member.current_life > 0:
                    from .courtship_demesne import _gain_melancholy

                    _gain_melancholy(session, member, 1)
            log.append("Ominous Omen — the party gains Melancholy (TCOTFD).")
        else:
            from .courtship_demesne import _grant_party_clues

            if engine is not None:
                tile = engine._tile_by_id(session, session.courtship_return_tile_id or "")
                _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
        return log

    if effect == "lex_cambion_shop":
        session.courtship_pending_choice = "lex_cambion"
        session.courtship_pending_choice_label = "Lex the Cambion"
        log.append("Trade with Lex — soul cube or 100gp (TCOTFD).")
        return log

    if effect == "maze_lost":
        session.courtship_pending_choice = "maze_lost"
        session.courtship_pending_choice_label = "Maze of Wondrous Awe"
        log.append("Spend 1 Clue to escape the maze or gain 1 Melancholy (TCOTFD).")
        return log

    if effect == "matron_wooing":
        session.courtship_pending_choice = "matron_wooing"
        session.courtship_pending_choice_label = "Matron of Summer"
        log.append("Present 3 rare ingredients to the Matron (TCOTFD).")
        return log

    session.log.extend(log)
    session.log.append(row.get("summary", ""))
    return log


def apply_book_of_secrets_combat_entry(
    session: SessionState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    entry: int,
    *,
    show_rolls: bool,
) -> list[str]:
    row = book_entry(entry)
    if row is None:
        return []
    effect = row.get("effect", "")
    log: list[str] = []
    if effect == "combat_start_mesmerize":
        level = int(row.get("save_level", 4))
        from .courtship_combat import COURTSHIP_ATTACK_PENALTY, COURTSHIP_CANNOT_FLEE, _mesmerize_save

        for member in [m for m in party if m.current_life > 0]:
            ok, save_log = _mesmerize_save(member, level, label=row.get("name", "mesmerize"), show_rolls=show_rolls)
            log.extend(save_log)
            if not ok:
                member.statuses.append(COURTSHIP_ATTACK_PENALTY)
        if entry == 24:
            for member in party:
                if member.current_life > 0:
                    member.statuses.append(COURTSHIP_CANNOT_FLEE)
            log.append("Maypole Dancers — the party cannot flee this encounter (TCOTFD).")
    elif effect == "matron_combat":
        session.courtship_matron_slain = False
        log.append("Matron of Summer lashes the front rank each round (TCOTFD).")
    session.log.extend(log)
    return log


def resolve_courtship_book_choice(
    engine: RandomDungeonEngine,
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    pending = session.courtship_pending_choice
    if pending == "disturbing_altar":
        session.courtship_pending_choice = None
        session.courtship_pending_choice_label = None
        if choice == "madness":
            victim = engine._member_by_marching_order(session, 1)
            if victim:
                from .madness import apply_madness_gain

                session.log.extend(apply_madness_gain(session, victim, source="Disturbing Altar"))
        else:
            from .courtship_demesne import _grant_party_clues

            tile = engine._tile_by_id(session, session.courtship_return_tile_id or "")
            _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
        return True
    if pending == "queens_vault":
        session.courtship_pending_choice = None
        session.courtship_pending_choice_label = None
        if choice == "acerbic":
            session.log.append("ACERBIC acid breaks the silver lock (BoS entry 3, TCOTFD).")
        gold = roll_formula("d6") * 10
        member = engine._member_by_marching_order(session, 1)
        if member:
            from .gem_items import format_gem_item

            member.inventory.append(format_gem_item(gold))
            session.log.append(f"Queen's Locked Vault: {member.name} gains Gem ({gold}gp) (TCOTFD).")
        return True
    if pending == "lex_cambion":
        session.courtship_pending_choice = None
        session.courtship_pending_choice_label = None
        member = engine._member_by_marching_order(session, 1)
        if member is None:
            return False
        if choice == "soul_cube":
            idx = next((i for i, item in enumerate(member.inventory) if "soul cube" in item.lower()), None)
            if idx is None:
                session.log.append("Need a soul cube to trade with Lex (TCOTFD).")
                return False
            member.inventory.pop(idx)
        elif choice == "gold":
            if member.gold < 100:
                session.log.append("Need 100gp to trade with Lex (TCOTFD).")
                return False
            member.gold -= 100
        else:
            session.log.append("Choose soul cube or 100gp for Lex the Cambion.")
            return False
        roll = roll_d6()
        session.log.append(f"Lex offers Blossoms magic item table d6 = {roll} (TCOTFD).")
        return True
    if pending == "maze_lost":
        session.courtship_pending_choice = None
        session.courtship_pending_choice_label = None
        if choice == "clue":
            if not engine._spend_clues(session, 1):
                session.log.append("Need 1 Clue to escape the maze (TCOTFD).")
                return False
            session.log.append("The maze releases the party (BoS entry 33, TCOTFD).")
        else:
            from .courtship_demesne import _gain_melancholy

            for member in session.party:
                if member.current_life > 0:
                    _gain_melancholy(session, member, 1)
        return True
    if pending == "matron_wooing":
        session.courtship_pending_choice = None
        session.courtship_pending_choice_label = None
        from .courtship_demesne import _add_keyword

        _add_keyword(session, "TRUELOVE")
        session.log.append("The Matron accepts three rare ingredients — gain TRUELOVE (TCOTFD).")
        return True
    return False
