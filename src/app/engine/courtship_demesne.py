"""Courtship of Flower Demons — Blossoms' Demesne exploration (TCOTFD)."""

from __future__ import annotations

import random
import re
import uuid
from typing import TYPE_CHECKING, Any

from ..schemas import EnemyState, PartyMemberState, SessionState, TileState
from .dice import roll_2d6, roll_d3, roll_d6, roll_formula
from .madness import apply_madness_gain

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

COURTSHIP_REGIONS = ("seaside", "riverside", "meadows", "woods", "mountain", "palace")
COURTSHIP_TABLE_BY_REGION = {
    region: f"courtship_{region}_encounter_table" for region in COURTSHIP_REGIONS
}
COURTSHIP_REGION_LABELS = {
    "seaside": "Seaside",
    "riverside": "Riverside",
    "meadows": "Meadows",
    "woods": "Woods",
    "mountain": "Mountain",
    "palace": "Queen's Garden Palace",
}


def _living_party(session: SessionState) -> list[PartyMemberState]:
    return [member for member in session.party if member.current_life > 0]


def _combat_tile(engine: RandomDungeonEngine, session: SessionState) -> TileState | None:
    tile_id = session.courtship_return_tile_id
    if not tile_id:
        return None
    return engine._tile_by_id(session, tile_id)


def _highest_melancholy(session: SessionState) -> int:
    if not session.courtship_melancholy:
        return 0
    return max(session.courtship_melancholy.values(), default=0)


def _melancholy_level(session: SessionState, member: PartyMemberState) -> int:
    return int(session.courtship_melancholy.get(member.character_id, 0))


def _gain_melancholy(session: SessionState, member: PartyMemberState, amount: int = 1) -> None:
    current = _melancholy_level(session, member)
    session.courtship_melancholy[member.character_id] = current + amount
    session.log.append(
        f"{member.name} gains {amount} Melancholy ({session.courtship_melancholy[member.character_id]} total, TCOTFD)."
    )


def _add_keyword(session: SessionState, keyword: str) -> None:
    normalized = keyword.strip().upper()
    if normalized not in session.courtship_keywords:
        session.courtship_keywords.append(normalized)
        session.log.append(f"Keyword marked: {normalized} (TCOTFD).")


def _has_keyword(session: SessionState, keyword: str) -> bool:
    return keyword.strip().upper() in session.courtship_keywords


def _parse_save_level(formula: str, hcl: int) -> int:
    formula = formula.strip().upper()
    match = re.match(r"^HCL\+(\d+)$", formula)
    if match:
        return hcl + int(match.group(1))
    if formula == "HCL":
        return hcl
    try:
        return int(formula)
    except ValueError:
        return hcl


def _harvest_save_bonus(member: PartyMemberState) -> int:
    class_id = member.class_id.lower()
    if class_id in {"halfling", "swashbuckler", "wandering_alchemist", "ranger", "druid"}:
        return member.level + 2
    if class_id == "elf":
        return 0
    return member.level


def _fd_style_save(
    member: PartyMemberState,
    level: int,
    *,
    label: str,
    show_rolls: bool,
    bonus: int = 0,
    swim: bool = False,
    allow_halfling_reroll: bool = True,
) -> tuple[bool, list[str]]:
    from .class_combat import save_modifier
    from .dice import roll_exploding_for_level

    modifier = save_modifier(member, trap=True, swim=swim) + bonus
    total, rolls = roll_exploding_for_level(member)
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier} vs {level}."
        )
    failed = rolls[0] == 1 or total + modifier < level
    if failed and allow_halfling_reroll and member.class_id.lower() == "halfling":
        total, rolls = roll_exploding_for_level(member)
        if show_rolls:
            log.append(
                f"Halfling reroll: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier}."
            )
        failed = rolls[0] == 1 or total + modifier < level
    log.append(f"{member.name} {'fails' if failed else 'passes'} the {label}.")
    return failed, log


def _melancholy_check(session: SessionState, member: PartyMemberState, *, show_rolls: bool) -> None:
    melancholy = _melancholy_level(session, member)
    roll = roll_d6()
    if show_rolls:
        session.log.append(
            f"Melancholy check: {member.name} rolls d6 = {roll} vs Melancholy {melancholy} (TCOTFD)."
        )
    if roll <= melancholy:
        _gain_melancholy(session, member, 1)


def _grant_party_clues(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState | None,
    amount: int,
    *,
    show_rolls: bool,
) -> None:
    for _ in range(max(0, amount)):
        if tile is not None:
            engine._grant_clue(session, tile, add_object=False)
        else:
            holder = engine._default_clue_holder(session)
            if holder:
                holder.clues += 1
                engine._sync_clue_total(session)
                if show_rolls:
                    session.log.append(f"{holder.name} gains 1 Clue (party total {session.clues_found}).")


def _spawn_courtship(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    spawn: dict[str, Any],
    *,
    hcl: int,
    show_rolls: bool,
) -> None:
    template = spawn["template"]
    count_formula = spawn.get("count", "1")
    count = max(1, roll_formula(str(count_formula)))
    category = spawn.get("category", "minions")
    enemies = engine._spawn_from_template_name(
        session,
        table_key="courtship_demons",
        template_name=template,
        count=count,
        hcl=hcl,
        category=category,
    )
    if not enemies:
        session.log.append(f"Courtship bestiary missing: {template}.")
        return
    level_delta = int(spawn.get("level_delta", 0))
    life_delta = spawn.get("life_delta")
    fixed_life = spawn.get("fixed_life")
    for enemy in enemies:
        if level_delta:
            enemy.level = max(1, hcl + level_delta)
        if fixed_life is not None:
            enemy.life = enemy.max_life = int(fixed_life)
        elif life_delta is not None:
            enemy.life = enemy.max_life = max(1, hcl + int(life_delta))
    tile.enemies.extend(enemies)
    tile.initial_enemy_count = len(tile.enemies)
    tile.content_key = f"courtship_{category}"
    if show_rolls:
        session.log.append(
            f"Demesne encounter: {count}× {template} appear ({COURTSHIP_REGION_LABELS.get(session.courtship_demesne_region or '', 'Demesne')}, TCOTFD)."
        )
    if session.mode == "exploration" and tile.enemies:
        engine._announce_encounter(session, tile, show_rolls=show_rolls)


def enter_courtship_demesne(
    engine: RandomDungeonEngine,
    session: SessionState,
    portal_tile: TileState,
    *,
    show_rolls: bool = True,
) -> bool:
    if session.courtship_demesne_active:
        session.log.append("The party is already exploring the Blossoms' Demesne.")
        return False
    for member in _living_party(session):
        member.current_life = max(0, member.current_life - 1)
        if show_rolls:
            session.log.append(
                f"{member.name} crosses to the Demesne and takes 1 Life "
                f"({member.current_life}/{member.max_life}, TCOTFD / FD p.63)."
            )
    session.courtship_demesne_active = True
    session.courtship_demesne_region = "seaside"
    session.courtship_return_tile_id = portal_tile.id
    session.courtship_pending_pathways = None
    session.courtship_encounter_reroll_spent = False
    portal_tile.fd_portal_available = False
    session.fd_portal_tile_id = None
    if show_rolls:
        session.log.append(
            "The Portal opens onto the Seaside of the Blossoms' Demesne (Courtship of Flower Demons). "
            "Roll encounters here; return home via Flower Portal from Seaside (TCOTFD p.62)."
        )
    return True


def leave_courtship_demesne(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_demesne_active:
        session.log.append("The party is not in the Demesne.")
        return False
    if session.courtship_demesne_region != "seaside":
        session.log.append(
            "Flower Portal home is only available from the Seaside (TCOTFD / Book of Secrets entry 1)."
        )
        return False
    tile = _combat_tile(engine, session)
    session.courtship_demesne_active = False
    session.courtship_demesne_region = None
    session.courtship_pending_pathways = None
    session.courtship_encounter_reroll_spent = False
    if show_rolls:
        session.log.append(
            "The party casts Flower Portal and returns to the Forsaken Depths "
            f"({'at ' + tile.title if tile else 'portal tile'}, TCOTFD)."
        )
    return True


def _lookup_row(engine: RandomDungeonEngine, region: str, roll: int) -> dict | None:
    table_key = COURTSHIP_TABLE_BY_REGION.get(region)
    if not table_key:
        return None
    return engine.table_roller.lookup(table_key, roll)


def _resolve_unique(session: SessionState, key: str, row: dict) -> dict:
    if key in session.courtship_uniques_seen:
        reroll_as = row.get("reroll_as")
        if reroll_as:
            session.log.append(f"Unique {row.get('name')} already seen — treat as {reroll_as} (TCOTFD).")
            for candidate in _table_rows_for_region(session.courtship_demesne_region or "seaside"):
                if candidate.get("key") == reroll_as:
                    return candidate
        if row.get("reroll"):
            session.log.append(f"Unique {row.get('name')} — roll the encounter table again (TCOTFD).")
            return {}
    session.courtship_uniques_seen.append(key)
    return row


def _table_rows_for_region(region: str) -> list[dict]:
    from ..rules.repository import RulesRepository
    from pathlib import Path

    packaged = Path(__file__).resolve().parents[2] / "data" / "rules"
    tables = RulesRepository(packaged, packaged / "_override").dungeon_tables()
    return list(tables.get(COURTSHIP_TABLE_BY_REGION.get(region, ""), []))


def roll_courtship_encounter(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_demesne_active:
        session.log.append("Roll Demesne encounters only while exploring the Blossoms' Demesne.")
        return False
    if session.courtship_pending_pathways:
        session.log.append("Choose a pathway before rolling a new encounter.")
        return False
    region = session.courtship_demesne_region or "seaside"
    roll = roll_2d6()
    row = _lookup_row(engine, region, roll)
    if row is None:
        session.log.append(f"No encounter row for {region} roll {roll}.")
        return False
    session.courtship_encounter_reroll_spent = False
    if show_rolls:
        session.log.append(
            f"{COURTSHIP_REGION_LABELS[region]} encounter: 2d6 = {roll} → {row.get('name')} (TCOTFD)."
        )
    key = str(row.get("key") or "")
    row = _resolve_unique(session, key, row)
    if not row:
        return roll_courtship_encounter(engine, session, show_rolls=show_rolls)
    apply_courtship_encounter(engine, session, row, show_rolls=show_rolls)
    return True


def spend_courtship_encounter_clue(
    engine: RandomDungeonEngine,
    session: SessionState,
    shift: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_demesne_active:
        return False
    if session.courtship_encounter_reroll_spent:
        session.log.append("Already spent a Clue on this encounter roll (TCOTFD).")
        return False
    cap = _highest_melancholy(session)
    if cap < 1:
        session.log.append("Need Melancholy to spend extra Clues shifting encounters (TCOTFD).")
        return False
    if not engine._spend_clues(session, 1):
        session.log.append("Need 1 Clue to re-roll or shift the encounter (TCOTFD).")
        return False
    session.courtship_encounter_reroll_spent = True
    region = session.courtship_demesne_region or "seaside"
    if shift in {"up", "down"}:
        roll = roll_2d6() + (1 if shift == "up" else -1)
        roll = max(2, min(12, roll))
        row = _lookup_row(engine, region, roll)
        if show_rolls:
            session.log.append(f"Clue spent — shifted encounter to 2d6 = {roll} (TCOTFD).")
    else:
        if show_rolls:
            session.log.append("Clue spent — re-rolling encounter (TCOTFD).")
        return roll_courtship_encounter(engine, session, show_rolls=show_rolls)
    if row:
        apply_courtship_encounter(engine, session, row, show_rolls=show_rolls)
    return True


def choose_courtship_pathway(
    session: SessionState,
    destination: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_demesne_active or not session.courtship_pending_pathways:
        session.log.append("No pathway is awaiting a destination choice.")
        return False
    normalized = (destination or "").strip().lower()
    if normalized not in session.courtship_pending_pathways:
        options = ", ".join(session.courtship_pending_pathways)
        session.log.append(f"Choose one of: {options}.")
        return False
    session.courtship_demesne_region = normalized  # type: ignore[assignment]
    session.courtship_pending_pathways = None
    if show_rolls:
        session.log.append(
            f"The party travels to {COURTSHIP_REGION_LABELS.get(normalized, normalized)} (TCOTFD)."
        )
    return True


def apply_courtship_encounter(
    engine: RandomDungeonEngine,
    session: SessionState,
    row: dict,
    *,
    show_rolls: bool = True,
) -> None:
    effect = row.get("effect", "")
    hcl = engine._highest_character_level(session.party)
    tile = _combat_tile(engine, session)
    if effect == "spawn" and tile is not None:
        _spawn_courtship(engine, session, tile, row["spawn"], hcl=hcl, show_rolls=show_rolls)
        return
    if effect == "pathway":
        session.courtship_pending_pathways = list(row.get("pathways") or [])
        labels = ", ".join(COURTSHIP_REGION_LABELS.get(p, p) for p in session.courtship_pending_pathways)
        session.log.append(f"Pathway found — travel to {labels}, or stay (TCOTFD).")
        if row.get("clue_secret_trail") and show_rolls:
            session.log.append("Spend 1 Clue for a secret trail (Book of Secrets entry 13, TCOTFD).")
        return
    if effect == "clues":
        amount = roll_formula(str(row.get("formula", "d3")))
        _grant_party_clues(engine, session, tile, amount, show_rolls=show_rolls)
        return
    if effect == "melancholy_gain":
        for member in _living_party(session):
            if row.get("elf_madness") and member.class_id.lower() == "elf":
                session.log.extend(
                    apply_madness_gain(session, member, source=str(row.get("name", "Demesne")))
                )
            else:
                _gain_melancholy(session, member, int(row.get("amount", 1)))
        return
    if effect == "melancholy_check":
        for member in _living_party(session):
            _melancholy_check(session, member, show_rolls=show_rolls)
        return
    if effect == "keyword":
        _add_keyword(session, str(row.get("keyword", "")))
        return
    if effect == "book_secret":
        session.log.append(
            f"Book of Secrets entry {row.get('entry')} — resolve that supplement text (TCOTFD)."
        )
        return
    if effect == "unique_clues":
        amount = roll_formula(str(row.get("formula", "d6")))
        _grant_party_clues(engine, session, tile, amount, show_rolls=show_rolls)
        return
    if effect == "heal_melancholy":
        heal = roll_formula(str(row.get("heal", "d6")))
        for member in _living_party(session):
            before = member.current_life
            member.current_life = min(member.max_life, member.current_life + heal)
            gained = member.current_life - before
            if gained:
                session.log.append(f"{member.name} drinks and heals {gained} Life (TCOTFD).")
            _gain_melancholy(session, member, int(row.get("melancholy", 1)))
        return
    if effect == "strangling_seaweed":
        targets = random.sample(_living_party(session), min(roll_d3(), len(_living_party(session))))
        for member in targets:
            level = hcl + roll_d3()
            bonus = 0
            if member.class_id.lower() in {"halfling", "druid"}:
                bonus += 1
            if member.class_id.lower() in {"rogue", "swashbuckler"}:
                bonus += member.level
            failed, logs = _fd_style_save(member, level, label="Strangling Seaweed", show_rolls=show_rolls, bonus=bonus)
            session.log.extend(logs)
            if failed:
                damage = roll_d3()
                member.current_life = max(0, member.current_life - damage)
                session.log.append(f"{member.name} loses {damage} Life to the seaweed.")
        return
    if effect == "harvest":
        save_level = _parse_save_level(str(row.get("save_level", "HCL+4")), hcl)
        any_fail = False
        for member in _living_party(session):
            failed, logs = _fd_style_save(
                member,
                save_level,
                label="Harvest save",
                show_rolls=show_rolls,
                bonus=_harvest_save_bonus(member),
            )
            session.log.extend(logs)
            if failed:
                any_fail = True
                continue
            reward = row.get("reward", "")
            if reward == "pearls":
                pearls = roll_d3()
                gold = roll_formula("2d6") * pearls
                member.gold += gold
                session.log.append(f"{member.name} harvests {pearls} pearl(s) worth {gold} gp.")
            elif reward in {"ingredients", "common_ingredients", "meadow_ingredients", "mineral_ingredients"}:
                session.log.append(f"{member.name} harvests Demesne ingredients (TCOTFD).")
            else:
                session.log.append(f"{member.name} succeeds the harvest (TCOTFD).")
        if any_fail and tile is not None:
            fail_spawn = row.get("fail_spawn")
            if fail_spawn:
                _spawn_courtship(
                    engine,
                    session,
                    tile,
                    {"template": fail_spawn, "count": row.get("fail_count", "d6"), "category": "minions", "level_delta": 2},
                    hcl=hcl,
                    show_rolls=show_rolls,
                )
        return
    if effect == "harvest_pathway":
        _grant_party_clues(engine, session, tile, 1, show_rolls=show_rolls)
        apply_courtship_encounter(engine, session, {**row, "effect": "harvest"}, show_rolls=show_rolls)
        session.courtship_pending_pathways = list(row.get("pathways") or [])
        labels = ", ".join(COURTSHIP_REGION_LABELS.get(p, p) for p in session.courtship_pending_pathways)
        session.log.append(f"May return to {labels} or keep exploring the Mountain (TCOTFD).")
        return
    if effect == "search_clues":
        target = int(row.get("target", 5))
        roll = roll_d6()
        bonus = 0
        if row.get("stone_mastery"):
            bonus += 1
        if show_rolls:
            session.log.append(f"Search roll d6 = {roll} + {bonus} (target {target}+, TCOTFD).")
        if roll + bonus >= target:
            amount = roll_formula(str(row.get("success", "d3")))
        else:
            amount = int(row.get("fail", 1))
        _grant_party_clues(engine, session, tile, amount, show_rolls=show_rolls)
        return
    if effect == "ominous_omen":
        if "ominous_omen" not in session.courtship_uniques_seen:
            session.courtship_uniques_seen.append("ominous_omen")
            session.log.append("Ominous Omen — Book of Secrets entry 31 (TCOTFD).")
        else:
            _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
        return
    if effect == "lady_of_lament":
        if _has_keyword(session, "KEEPSAKE"):
            session.log.append("Lady of Lament recognizes the Keepsake — Book of Secrets entry 21 (TCOTFD).")
        else:
            session.log.append("Lady of Lament — reactions depend on KEEPSAKE / TRUELOVE keywords (TCOTFD).")
        return
    if effect == "agility_save":
        level = int(row.get("level", 4))
        for member in _living_party(session):
            bonus = 0
            class_id = member.class_id.lower()
            if class_id in {"halfling", "elf"}:
                bonus += 1
            if class_id == "rogue":
                bonus += member.level
            if class_id == "dwarf" or "heavy armor" in " ".join(member.inventory).lower():
                bonus -= 1
            failed, logs = _fd_style_save(member, level, label="Agility save", show_rolls=show_rolls, bonus=bonus)
            session.log.extend(logs)
            if failed:
                damage = roll_formula(str(row.get("damage", "d6")))
                member.current_life = max(0, member.current_life - damage)
                session.log.append(f"{member.name} suffers {damage} wounds from the fall.")
        return
    if effect == "rockslide":
        save_level = _parse_save_level(str(row.get("save_level", "HCL+2")), hcl)
        for member in _living_party(session):
            failed, logs = _fd_style_save(member, save_level, label="Rockslide Defense", show_rolls=show_rolls, bonus=0)
            session.log.extend(logs)
            if failed and member.inventory:
                lost = min(len(member.inventory), roll_d3())
                for _ in range(lost):
                    member.inventory.pop(random.randrange(len(member.inventory)))
                session.log.append(f"{member.name} loses {lost} item(s) dodging the rockslide.")
        return
    if effect == "acid_spring":
        if _has_keyword(session, "OCCLITH"):
            _add_keyword(session, str(row.get("keyword", "ACERBIC")))
            session.log.append("Occlith keyword — harvest acid safely (TCOTFD entry 17).")
            return
        save_level = _parse_save_level(str(row.get("save_level", "HCL+5")), hcl)
        member = _living_party(session)[0] if _living_party(session) else None
        if member is None:
            return
        failed, logs = _fd_style_save(member, save_level, label="Acid spring poison", show_rolls=show_rolls, bonus=0)
        session.log.extend(logs)
        if failed:
            damage = roll_d6()
            member.current_life = max(0, member.current_life - damage)
            session.log.append(f"{member.name} suffers {damage} acid damage.")
        else:
            _add_keyword(session, str(row.get("keyword", "ACERBIC")))
        return
    if effect == "occlith":
        session.log.append("The Occlith — attack (Book of Secrets entry 5) or parley (entry 6, TCOTFD).")
        return
    if effect == "fear_save":
        level = int(row.get("level", 5))
        for member in _living_party(session):
            failed, logs = _fd_style_save(member, level, label="Fear save", show_rolls=show_rolls)
            session.log.extend(logs)
            if failed:
                session.log.extend(
                    apply_madness_gain(session, member, source="Haunting Vision")
                )
        return
    if effect == "frost_roses":
        for member in _living_party(session):
            if member.level <= 5:
                continue
            from .madness import madness_points

            madness = madness_points(member)
            roll = roll_d6()
            if roll < madness:
                heal = roll_d3()
                member.current_life = min(member.max_life, member.current_life + heal)
                session.log.append(f"{member.name} recovers {heal} Life and loses 1 Madness (TCOTFD).")
                member.madness = max(0, madness - 1)
            else:
                session.log.extend(
                    apply_madness_gain(session, member, source="Frost Roses")
                )
                if member.class_id.lower() == "elf":
                    session.log.extend(
                        apply_madness_gain(session, member, source="Frost Roses (elf)", allow_damage_choice=False)
                    )
        if _has_keyword(session, "KEEPSAKE"):
            session.log.append("Keepsake keyword — Book of Secrets entry 15 (TCOTFD).")
        return
    if effect == "ballroom":
        save_level = _parse_save_level(str(row.get("save_level", "HCL+5")), hcl)
        member = _living_party(session)[0] if _living_party(session) else None
        if member is None:
            return
        failed, logs = _fd_style_save(member, save_level, label="Ballroom save", show_rolls=show_rolls)
        session.log.extend(logs)
        if failed:
            _grant_party_clues(engine, session, tile, 1, show_rolls=show_rolls)
            for wooer in _living_party(session):
                _melancholy_check(session, wooer, show_rolls=show_rolls)
        else:
            _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
        return
    if effect == "strange_follies":
        roll = roll_d6() + (1 if any(m.class_id.lower() == "dwarf" for m in session.party) else 0)
        if roll >= 5:
            _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
            session.log.append("Strange Follies — Queen's Locked Vault (Book of Secrets entry 12, TCOTFD).")
        else:
            _grant_party_clues(engine, session, tile, 1, show_rolls=show_rolls)
            session.log.append("Strange Follies failed — re-roll on the Palace table (TCOTFD).")
        return
    if effect == "queens_locked_vault":
        if _has_keyword(session, "ACERBIC"):
            session.log.append("ACERBIC keyword — break the silver lock (Book of Secrets entry 3, TCOTFD).")
        elif _has_keyword(session, "TRUELOVE"):
            session.log.append("TRUELOVE keyword — open the vault (Book of Secrets entry 12, TCOTFD).")
        else:
            session.log.append("The silver-chained vault cannot be opened without ACERBIC or TRUELOVE (TCOTFD).")
        for member in _living_party(session):
            _melancholy_check(session, member, show_rolls=show_rolls)
        return
    if effect == "unique_reroll":
        return
    summary = row.get("summary") or row.get("name") or effect
    session.log.append(f"{summary} (TCOTFD).")
