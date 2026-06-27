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

_ROOT = Path(__file__).resolve().parents[3] / "data" / "rules"
_CATALOG: dict[str, Any] | None = None


def _catalog() -> dict[str, Any]:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = json.loads((_ROOT / "courtship_book_of_secrets.json").read_text(encoding="utf-8"))
    return _CATALOG


def book_entry(entry: int | str) -> dict[str, Any] | None:
    return _catalog().get("entries", {}).get(str(entry))


def _blossoms_data() -> dict[str, Any]:
    table_path = _ROOT / "courtship_blossoms_tables.json"
    return json.loads(table_path.read_text(encoding="utf-8"))


def lex_shop_catalog() -> list[dict[str, Any]]:
    """Flattened Lex shop catalog (BoS entry 32, TCOTFD p.61)."""
    return list(_blossoms_data().get("courtship_lex_shop_table", []))


def lex_shop_item(key: str) -> dict[str, Any] | None:
    return next((row for row in lex_shop_catalog() if row.get("key") == key), None)


def roll_blossoms_magic_item(*, show_rolls: bool = True) -> tuple[str, list[str]]:
    """Roll TCOTFD Blossoms Magic Item table (d6, p.69)."""
    rows = _blossoms_data().get("courtship_blossoms_magic_item_table", [])
    roll = roll_d6()
    log: list[str] = []
    if show_rolls:
        log.append(f"Blossoms Magic Item table d6 = {roll} (TCOTFD p.69).")
    row = next((item for item in rows if str(item.get("roll")) == str(roll)), None)
    if row is None:
        return "Blossoms magic item", log
    item = str(row.get("item", "Blossoms magic item"))
    summary = str(row.get("summary", ""))
    if summary:
        log.append(summary)
    return item, log


def apply_queens_vault_betrayal(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    """BoS entry 3 — vault intrusion enrages the queen's court (TCOTFD p.49)."""
    from .courtship_demesne import _add_keyword, _break_truelove_faith, _living_party, _truelove_member

    log: list[str] = []
    if show_rolls:
        log.append("Book of Secrets entry 3: the queen's forbidden vault (TCOTFD).")
    for member in _living_party(session):
        from .courtship_classes import madness_save_level_bonus
        from .madness import apply_madness_gain, madness_points

        roll = roll_d6()
        threshold = madness_points(member) + madness_save_level_bonus(member)
        if show_rolls:
            log.append(
                f"Vault horror: {member.name} rolls d6 = {roll} vs Madness {threshold} (TCOTFD)."
            )
        if roll <= threshold:
            log.extend(apply_madness_gain(session, member, source="Queen's vault"))
        elif member.level < 6:
            from .courtship_demesne import _fd_style_save

            failed, save_log = _fd_style_save(
                member,
                4,
                label="Vault fear save",
                show_rolls=show_rolls,
                bonus=-(member.level // 2 if member.class_id.lower() == "wizard" else 0),
            )
            log.extend(save_log)
            if failed:
                member.current_life = max(0, member.current_life - 1)
                log.append(f"{member.name} loses 1 Life to vault terror (TCOTFD).")
    lover = _truelove_member(session)
    if lover is not None:
        _break_truelove_faith(
            session,
            lover,
            reason="opening the queen's locked vault",
            broken_heart=True,
            show_rolls=show_rolls,
        )
    _add_keyword(session, "PANDORA")
    session.courtship_melancholy = {member.character_id: 0 for member in _living_party(session)}
    session.courtship_vault_combat_no_flee = True
    log.append(
        "The demonworld turns hostile — mark PANDORA; +6 Reaction penalty and fight-to-the-death "
        "from flower demons (BoS entry 2, TCOTFD)."
    )
    tile = engine._tile_by_id(session, session.courtship_return_tile_id or "")
    if tile is not None and session.courtship_demesne_region == "palace":
        hcl = engine._highest_character_level(session.party)
        queen = engine._spawn_from_template_name(
            session,
            table_key="courtship_demons",
            template_name="Blue-Haired Queen of Flowers",
            count=1,
            hcl=hcl,
            category="boss",
        )
        handmaidens = engine._spawn_from_template_name(
            session,
            table_key="courtship_demons",
            template_name="Queen's Handmaidens",
            count=roll_formula("d3+3"),
            hcl=hcl,
            category="minions",
        )
        spawned = queen + handmaidens
        if spawned:
            from .courtship_combat import apply_courtship_spawn_adjustments

            apply_courtship_spawn_adjustments(session, spawned, hcl=hcl, show_rolls=show_rolls)
            tile.enemies = spawned
            tile.initial_enemy_count = len(spawned)
            session.courtship_combat_entry = 20
            log.append("The Blue-Haired Queen and her Handmaidens attack to the death (TCOTFD).")
            if session.mode == "exploration":
                engine._announce_encounter(session, tile, show_rolls=show_rolls)
    return log


def apply_lady_lament_truelove(
    session: SessionState,
    speaker: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    """BoS entry 9 — TRUELOVE keyword for the character who pleased her (TCOTFD p.52)."""
    log: list[str] = []
    if show_rolls:
        log.append("Book of Secrets entry 9: Lady of Lament TRUELOVE (TCOTFD).")
    if speaker.class_id.lower() == "satyr":
        log.append("Satyrs cannot be the Lady's one true love (BoS entry 9, TCOTFD).")
        return log
    from .courtship_demesne import _add_keyword

    _add_keyword(session, "TRUELOVE")
    session.courtship_truelove_character_id = speaker.character_id
    log.append(
        f"{speaker.name} marks TRUELOVE — remain faithful or lose Keepsake, Rosebud, and Truelove (TCOTFD)."
    )
    log.append("She forbids opening the queen's locked vault (BoS entry 9, TCOTFD).")
    return log


def _grant_blossoms_spell_scroll(
    member: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    rows = _blossoms_data().get("courtship_blossoms_spell_scrolls_table", [])
    roll = roll_d6()
    log: list[str] = []
    if show_rolls:
        log.append(f"Blossoms spell scroll d6 = {roll} (TCOTFD).")
    row = next((item for item in rows if str(item.get("roll")) == str(roll)), None)
    item = str(row.get("item", "Blossoms spell scroll")) if row else "Blossoms spell scroll"
    member.inventory.append(item)
    log.append(f"{member.name} gains {item} (TCOTFD).")
    return log


def _apply_epic_reward_row(
    engine: RandomDungeonEngine,
    session: SessionState,
    row: dict[str, Any],
    member: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    from .quests import epic_reward_item

    log: list[str] = []
    reward_text = epic_reward_item(row)
    key = row.get("key", "")
    log.append(f"Epic reward: {reward_text}")
    if key == "gold_of_kerrak_dar":
        from .random_dungeon import KERRAK_DAR_STATUS

        if KERRAK_DAR_STATUS not in member.statuses:
            member.statuses.append(KERRAK_DAR_STATUS)
    elif key == "enchanted_weapon":
        from .random_dungeon import ENCHANTED_WEAPON_STATUS

        if ENCHANTED_WEAPON_STATUS not in member.statuses:
            member.statuses.append(ENCHANTED_WEAPON_STATUS)
    else:
        if key == "book_of_skalitos":
            item_label = "Book of Skalitos (6 pages)"
        elif key == "arrow_of_slaying":
            target_name = engine._roll_epic_major_foe_target_name(session) or "Major Foe"
            item_label = f"Arrow of Slaying (target: {target_name})"
            log.append(f"Arrow of Slaying target rolled: {target_name}.")
        else:
            item_label = reward_text.split(".")[0]
        member.inventory.append(item_label)
        log.append(f"{item_label} added to {member.name}'s inventory.")
    return log


def apply_matron_wooing_effects(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    show_rolls: bool = True,
) -> list[str]:
    """BoS entry 30 — Matron wooing unearthly pleasures (TCOTFD p.61)."""
    log: list[str] = []
    if show_rolls:
        log.append("Book of Secrets entry 30: Matron of Summer wooing (TCOTFD).")
    for member in party:
        if member.current_life <= 0:
            continue
        first_visit = member.character_id not in session.courtship_matron_pleasures_applied
        if first_visit:
            member.max_life += 1
            member.current_life = min(member.max_life, member.current_life + 1)
            log.append(f"{member.name} gains +1 permanent Life from the Matron (first visit, TCOTFD).")
            session.courtship_matron_pleasures_applied.append(member.character_id)
            from .madness import apply_madness_gain

            times = 2 if member.class_id.lower() == "elf" else 1
            for _ in range(times):
                log.extend(apply_madness_gain(session, member, source="Matron of Summer"))
        elif show_rolls:
            log.append(f"{member.name} has already tasted the Matron's pleasures (TCOTFD).")
    return log


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

    if effect == "queens_vault_warning":
        session.courtship_pending_choice = "queens_vault"
        session.courtship_pending_choice_label = "Queen's Locked Vault"
        log.append(
            "Your TRUELOVE forbade this vault — heed her warning or break the lock with ACERBIC (BoS entry 12, TCOTFD)."
        )
        return log

    if effect == "matron_reward":
        from .courtship_demesne import _grant_party_clues

        session.courtship_matron_head_quest_active = True
        log.append(
            "The Matron of Summer asks you to bring the Lady of Lament's head — "
            "reward your choice on Epic Rewards or Blossoms Magic Items (BoS entry 8, TCOTFD)."
        )
        if engine is not None:
            tile = engine._tile_by_id(session, session.courtship_return_tile_id or "")
            _grant_party_clues(engine, session, tile, roll_d3() + 1, show_rolls=show_rolls)
        member = next((m for m in party if m.current_life > 0), None)
        if member is not None:
            log.extend(_grant_blossoms_spell_scroll(member, show_rolls=show_rolls))
        return log

    if effect == "lady_lament_truelove":
        speaker = next(
            (
                member
                for member in party
                if member.character_id == session.courtship_woo_speaker_id and member.current_life > 0
            ),
            next((member for member in party if member.current_life > 0), None),
        )
        if speaker is not None:
            log.extend(apply_lady_lament_truelove(session, speaker, show_rolls=show_rolls))
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
        from .courtship_classes import party_has_hidden_pathway_guide

        if not party_has_hidden_pathway_guide(party):
            log.append("Only a cleric, paladin, cambion, or succubus can find the hidden Riverside shortcut (BoS entry 14).")
            return log
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
        log.append(
            "Trade with Lex — pay 300gp + oath or a soul cube, then pick any three magic items "
            "from the Blossoms or 4AD tables (BoS entry 32, TCOTFD)."
        )
        return log

    if effect == "maze_lost":
        session.courtship_pending_choice = "maze_lost"
        session.courtship_pending_choice_label = "Maze of Wondrous Awe"
        log.append("Spend 1 Clue to escape the maze or gain 1 Melancholy (TCOTFD).")
        return log

    if effect == "matron_wooing":
        log.extend(apply_matron_wooing_effects(session, party, show_rolls=show_rolls))
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
        if entry == 28:
            log.append(
                "Colleen of Lilies — mesmerize save each round or skip your next attack (BoS entry 28, TCOTFD)."
            )
            session.log.extend(log)
            return log
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
    if pending == "bountiful_harvest":
        member = next(
            (item for item in session.party if item.character_id == session.courtship_pending_choice_label),
            engine._member_by_marching_order(session, 1),
        )
        if member is None:
            return False
        from .courtship_blossoms_spells import resolve_bountiful_harvest_choice

        return resolve_bountiful_harvest_choice(session, member, choice, show_rolls=show_rolls)
    if pending == "aetheric_conversion":
        from .courtship_blossoms_spells import resolve_aetheric_conversion_choice

        return resolve_aetheric_conversion_choice(engine, session, choice, show_rolls=show_rolls)
    if pending == "song_of_charm":
        from .courtship_blossoms_spells import resolve_song_of_charm_choice

        return resolve_song_of_charm_choice(session, choice)
    if pending == "flower_portal_destination":
        from .courtship_blossoms_spells import resolve_flower_portal_destination_choice

        return resolve_flower_portal_destination_choice(engine, session, choice, show_rolls=show_rolls)
    if pending == "shovel_substitute":
        member = engine._member_by_marching_order(session, 1)
        if member is None:
            return False
        from .courtship_blossoms_items import resolve_shovel_substitute

        return resolve_shovel_substitute(session, member, choice)
    if (
        choice == "deliver"
        and pending == "woo_or_fight"
        and session.courtship_pending_choice_label == "Matron of Summer"
    ):
        session.courtship_pending_choice = "matron_head_deliver"
        pending = "matron_head_deliver"
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
        if choice == "heed":
            session.log.append(
                "The party heeds the Lady of Lament's warning and leaves the vault sealed (BoS entry 12, TCOTFD)."
            )
            return True
        if choice == "acerbic":
            session.log.append("ACERBIC acid sears through the silver lock (BoS entry 3, TCOTFD).")
            session.log.extend(apply_queens_vault_betrayal(engine, session, show_rolls=show_rolls))
            return True
        session.log.append("Choose Heed Warning or Break lock (ACERBIC) at the Queen's vault (TCOTFD).")
        session.courtship_pending_choice = "queens_vault"
        session.courtship_pending_choice_label = "Queen's Locked Vault"
        return False
    if pending == "lex_cambion":
        member = engine._member_by_marching_order(session, 1)
        if member is None:
            return False
        if session.courtship_lex_picks_remaining > 0:
            session.log.append("Finish picking Lex shop items before paying again (TCOTFD).")
            return False
        if choice == "soul_cube":
            idx = next((i for i, item in enumerate(member.inventory) if "soul cube" in item.lower()), None)
            if idx is None:
                session.log.append("Need a soul cube to trade with Lex (TCOTFD).")
                return False
            member.inventory.pop(idx)
            session.log.append(f"{member.name} trades a soul cube to Lex (TCOTFD).")
        elif choice in {"gold", "buy"}:
            if member.gold < 300:
                session.log.append("Need 300gp to buy from Lex the Cambion (BoS entry 32, TCOTFD).")
                return False
            member.gold -= 300
            session.log.append(
                f"{member.name} swears the oath of Tamas Zeya and pays Lex 300gp (TCOTFD)."
            )
        else:
            session.log.append("Choose Buy (300gp) or trade a soul cube with Lex the Cambion.")
            return False
        session.courtship_lex_picks_remaining = 3
        session.courtship_lex_picks_taken = []
        session.courtship_pending_choice = "lex_cambion_pick"
        session.courtship_pending_choice_label = "Lex the Cambion — pick 3 items"
        session.log.append("Pick any three items from Lex's catalog (BoS entry 32, TCOTFD).")
        return True
    if pending == "lex_cambion_pick":
        member = engine._member_by_marching_order(session, 1)
        if member is None:
            return False
        if session.courtship_lex_picks_remaining <= 0:
            session.courtship_pending_choice = None
            session.courtship_pending_choice_label = None
            return True
        row = lex_shop_item(choice or "")
        if row is None:
            session.log.append("Choose a catalog item from Lex's shop (TCOTFD).")
            return False
        key = str(row.get("key", ""))
        if key in session.courtship_lex_picks_taken:
            session.log.append("Lex will not sell the same item twice in one visit (TCOTFD).")
            return False
        item = str(row.get("item", "Magic item"))
        from .courtship_blossoms_items import is_blossoms_magic_item, prepare_blossoms_magic_item

        if is_blossoms_magic_item(item):
            item = prepare_blossoms_magic_item(item)
        member.inventory.append(item)
        session.courtship_lex_picks_taken.append(key)
        session.courtship_lex_picks_remaining -= 1
        from .courtship_lex import record_lex_grant

        record_lex_grant(session, member, item)
        session.log.append(f"{member.name} receives {item} from Lex ({row.get('source', 'TCOTFD')}).")
        if session.courtship_lex_picks_remaining <= 0:
            session.courtship_pending_choice = None
            session.courtship_pending_choice_label = None
            session.log.append("Lex's transaction is complete (BoS entry 32, TCOTFD).")
        return True
    if pending == "matron_head_reward":
        member = engine._member_by_marching_order(session, 1)
        if member is None:
            return False
        session.courtship_pending_choice = None
        session.courtship_pending_choice_label = None
        if choice == "epic":
            reward_roll = roll_d6()
            if show_rolls:
                session.log.append(f"Matron's reward — Epic Rewards d6 = {reward_roll} (BoS entry 8, TCOTFD).")
            row = engine.table_roller.lookup("epic_rewards_table", reward_roll)
            if row is None:
                session.log.append("Epic Rewards table lookup failed.")
                return False
            session.log.extend(_apply_epic_reward_row(engine, session, row, member, show_rolls=show_rolls))
            return True
        row = next(
            (item for item in _blossoms_data().get("courtship_blossoms_magic_item_table", []) if str(item.get("roll")) == str(choice)),
            None,
        )
        if row is None:
            session.log.append("Choose Epic Reward roll or a Blossoms Magic Item (BoS entry 8, TCOTFD).")
            session.courtship_pending_choice = "matron_head_reward"
            session.courtship_pending_choice_label = "Matron's quest reward"
            return False
        item = str(row.get("item", "Blossoms magic item"))
        from .courtship_blossoms_items import prepare_blossoms_magic_item

        prepared = prepare_blossoms_magic_item(item)
        member.inventory.append(prepared)
        session.log.append(f"{member.name} receives {prepared} from the Matron (BoS entry 8, TCOTFD).")
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
    if pending == "mistress_quest_ingredients":
        if choice != "deliver":
            return False
        from .courtship_ingredients import consume_party_ingredients, party_ingredient_items

        if len(party_ingredient_items(session.party, rare_only=True)) < 3:
            session.log.append("Need 3 rare ingredients for the Mistress quest (TCOTFD p.65).")
            return False
        session.courtship_pending_choice = None
        session.courtship_pending_choice_label = None
        removed = consume_party_ingredients(session.party, 3, rare_only=True)
        session.log.append(
            f"The Mistress of Black Lashes accepts {', '.join(removed)} — quest fulfilled (TCOTFD)."
        )
        from .courtship_demesne import _grant_party_clues

        tile = engine._tile_by_id(session, session.courtship_return_tile_id or "")
        _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
        return True
    if pending == "matron_head_deliver":
        from .courtship_demesne import _party_has_item, _remove_party_item

        if choice != "deliver":
            return False
        if not session.courtship_matron_head_quest_active:
            session.log.append("The Matron is not awaiting the Lady's head (TCOTFD).")
            return False
        if not _party_has_item(session, "Lady of Lament's head"):
            session.log.append("Need the Lady of Lament's head to complete the Matron's quest (BoS entry 8, TCOTFD).")
            return False
        _remove_party_item(session, "Lady of Lament's head")
        session.courtship_matron_head_quest_active = False
        session.courtship_pending_choice = "matron_head_reward"
        session.courtship_pending_choice_label = "Matron's quest reward"
        session.log.append(
            "The Matron accepts the head — choose Epic Rewards (d6 roll) or one Blossoms Magic Item (BoS entry 8, TCOTFD)."
        )
        return True
    return False
