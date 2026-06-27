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

COURTSHIP_DEMESNE_ADVENTURE_ID = "courtship-demesne"

COURTSHIP_WOO_RULES: dict[str, dict[str, Any]] = {
    "Giggling Gingers": {
        "dominant_blocked": True,
        "giving_penalty": 2,
        "seduce_reaction": True,
    },
    "Colleen of Lilies": {
        "giving_heals": 1,
        "withholding_life_loss": 1,
        "dominant_foe_level_delta": -1,
        "seduce_reaction": True,
    },
    "Dryads": {
        "withholding_fail_penalty": 1,
        "cannot_break_out": True,
        "seduce_reaction": True,
    },
    "Mistress of Black Lashes": {
        "withholding_life_loss": 1,
        "no_melancholy": True,
        "dominant_foe_level_delta": 1,
        "seduce_reaction": True,
    },
    "Maypole Dancers": {
        "giving_penalty_per_turn": 1,
        "seduce_reaction": True,
    },
    "Queen's Maids": {
        "withholding_life_loss_per_six": True,
        "seduce_reaction": True,
    },
    "Queen's Handmaidens": {
        "withholding_life_loss": 1,
        "seduce_reaction": True,
    },
    "Damsel of Teeming Roses": {
        "giving_life_or_madness": True,
        "dominant_foe_level_delta": 1,
        "seduce_reaction": True,
    },
    "Blue-Haired Queen of Flowers": {
        "dominant_foe_level_delta": 1,
        "seduce_reaction": True,
    },
    "Lorelei": {"seduce_reaction": True},
    "Naiads": {"seduce_reaction": True},
    "Princess of Tides": {"seduce_reaction": True},
    "Matron of Summer": {
        "no_melancholy": True,
        "passionate_stance_foe_level_delta": -1,
        "seduce_reaction": True,
    },
    "Lady of Lament": {
        "passionate_stance_foe_level_delta": -1,
        "seduce_reaction": True,
    },
}

COURTSHIP_WOO_SUCCESSES_REQUIRED = 3

COURTSHIP_PLANT_WOO_EXEMPT: frozenset[str] = frozenset(
    {
        "Strangling Seaweed",
        "Corrosive Shrub",
        "Giant Purple Pitcherplant",
        "Death Orchid",
        "Giant Sundew",
        "Venus Flytrap",
    }
)

COURTSHIP_FAITHFULNESS_KEYWORDS: tuple[str, ...] = ("KEEPSAKE", "ROSEBUD", "TRUELOVE")

COURTSHIP_COMBAT_BOS_ENTRIES: dict[str, int] = {
    "Blue-Haired Queen of Flowers": 20,
    "Matron of Summer": 23,
    "Maypole Dancers": 24,
    "Giggling Gingers": 26,
    "Colleen of Lilies": 28,
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


def _remove_keyword(session: SessionState, keyword: str) -> None:
    normalized = keyword.strip().upper()
    if normalized in session.courtship_keywords:
        session.courtship_keywords.remove(normalized)


def _truelove_member(session: SessionState) -> PartyMemberState | None:
    if not session.courtship_truelove_character_id:
        return None
    return next(
        (member for member in session.party if member.character_id == session.courtship_truelove_character_id),
        None,
    )


def _break_truelove_faith(
    session: SessionState,
    member: PartyMemberState,
    *,
    reason: str,
    broken_heart: bool = False,
    show_rolls: bool = True,
) -> None:
    removed = [key for key in COURTSHIP_FAITHFULNESS_KEYWORDS if _has_keyword(session, key)]
    for key in removed:
        _remove_keyword(session, key)
    session.courtship_truelove_character_id = None
    session.courtship_lady_keepsake_bonus = 0
    if broken_heart:
        session.courtship_lady_heart_broken = True
    if show_rolls:
        if removed:
            session.log.append(
                f"{member.name} loses {', '.join(removed)} — the Lady of Lament's jealous love ({reason}, BoS entry 9, TCOTFD)."
            )
        if broken_heart:
            session.log.append(
                "Her cracked heart of Lament becomes a broken heart of Lament (BoS entry 9, TCOTFD)."
            )


def _maybe_apply_truelove_infidelity(
    session: SessionState,
    speaker: PartyMemberState,
    template: str,
    category: str,
    *,
    show_rolls: bool = True,
) -> bool:
    if session.courtship_truelove_character_id != speaker.character_id:
        return False
    if template == "Lady of Lament":
        return False
    if template in COURTSHIP_PLANT_WOO_EXEMPT:
        return False
    if category not in {"minions", "boss"}:
        return False
    _break_truelove_faith(
        session,
        speaker,
        reason="wooing another Maiden or Lady",
        broken_heart=True,
        show_rolls=show_rolls,
    )
    return True


def _spawn_lady_lament_doubles(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    hcl: int,
    show_rolls: bool,
) -> None:
    doubles = engine._spawn_from_template_name(
        session,
        table_key="courtship_demons",
        template_name="Lady of Lament (illusion)",
        count=2,
        hcl=hcl,
        category="minions",
    )
    if not doubles:
        return
    for enemy in doubles:
        enemy.level = max(1, hcl + 5)
        enemy.life = enemy.max_life = 1
    tile.enemies.extend(doubles)
    session.courtship_lady_doubles_active = True
    if show_rolls:
        session.log.append(
            "The Lady of Lament conjures two illusion doubles — her lover must please all three "
            "(BoS entry 21, TCOTFD)."
        )


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
    from .courtship_combat import apply_courtship_spawn_adjustments

    apply_courtship_spawn_adjustments(
        session,
        tile.enemies,
        hcl=hcl,
        show_rolls=show_rolls,
    )
    bos_entry = COURTSHIP_COMBAT_BOS_ENTRIES.get(template)
    if bos_entry is not None:
        session.courtship_combat_entry = bos_entry
    if template == "Mirror Demon":
        session.courtship_mirror_first_hit_pending = True
    if template == "Queen's Handmaidens":
        session.courtship_handmaiden_blur_active = True
        session.courtship_handmaiden_blur_cancelled = False
    if template == "Matron of Summer":
        session.courtship_matron_slain = False
        session.courtship_matron_respawned = False
    if template == "Lady of Lament":
        session.courtship_lady_doubles_active = False
        _spawn_lady_lament_doubles(engine, session, tile, hcl=hcl, show_rolls=show_rolls)
    if show_rolls:
        session.log.append(
            f"Demesne encounter: {count}× {template} appear ({COURTSHIP_REGION_LABELS.get(session.courtship_demesne_region or '', 'Demesne')}, TCOTFD)."
        )
    wooable = spawn.get("wooable", True) and category in {"minions", "boss"}
    from .courtship_pandora import pandora_blocks_wooing, pandora_forces_fight_to_death, prepare_pandora_fight

    if wooable and pandora_blocks_wooing(session, template):
        prepare_pandora_fight(session, tile.enemies)
        if show_rolls:
            session.log.append(
                f"PANDORA: {template} fights to the death — wooing is impossible (BoS entry 2, TCOTFD)."
            )
        if session.mode == "exploration" and tile.enemies:
            engine._announce_encounter(session, tile, show_rolls=show_rolls)
        return
    if wooable and tile.enemies:
        session.courtship_pending_choice = "woo_or_fight"
        session.courtship_pending_choice_label = template
        if show_rolls:
            session.log.append("Choose Woo or Fight before combat begins (TCOTFD).")
        return
    if session.mode == "exploration" and tile.enemies:
        engine._announce_encounter(session, tile, show_rolls=show_rolls)


def tile_at_water_landscape(
    session: SessionState,
    tile: TileState | None,
    engine: RandomDungeonEngine | None = None,
) -> bool:
    """Large body of water — terrain, map adjacency, FD river bank, or Demesne Seaside/Riverside (TCOTFD p.27)."""
    from .terrain import resolve_water_landscape

    ok, _reason = resolve_water_landscape(session, tile, engine)
    return ok


def flower_portal_water_failure_message(
    session: SessionState,
    tile: TileState | None,
    engine: RandomDungeonEngine | None = None,
) -> str:
    from .terrain import resolve_water_landscape, water_landscape_failure_message

    _ok, reason = resolve_water_landscape(session, tile, engine)
    return water_landscape_failure_message(reason)


def enter_courtship_via_flower_portal(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> bool:
    """Flower Portal into the Demesne from Norindaal — 1 soul cube, water required (TCOTFD p.27)."""
    if not session.courtship_enabled:
        session.log.append("Courtship of Flower Demons is disabled for this adventure.")
        return False
    if session.courtship_demesne_active:
        session.log.append("The party is already in the Blossoms' Demesne.")
        return False
    if not tile_at_water_landscape(session, tile, engine):
        session.log.append(flower_portal_water_failure_message(session, tile, engine))
        return False
    session.courtship_demesne_active = True
    session.courtship_demesne_region = "seaside"
    session.courtship_entry_source = "flower_portal"
    session.courtship_return_tile_id = tile.id
    session.courtship_pending_pathways = None
    session.courtship_encounter_reroll_spent = False
    if show_rolls:
        session.log.append(
            "Flower Portal opens onto the Seaside of the Blossoms' Demesne (TCOTFD p.27 / BoS entry 1). "
            "Roll Demesne encounters; cast Flower Portal from Seaside or Riverside to return."
        )
    return True


def enter_courtship_demesne(
    engine: RandomDungeonEngine,
    session: SessionState,
    portal_tile: TileState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_enabled:
        session.log.append("Courtship of Flower Demons is disabled for this adventure.")
        return False
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
    session.courtship_entry_source = "fd_portal"
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
    if session.courtship_demesne_region not in {"seaside", "riverside"}:
        session.log.append(
            "Flower Portal home is only available from the Seaside or Riverside (TCOTFD / Book of Secrets entry 1)."
        )
        return False
    tile = _combat_tile(engine, session)
    session.courtship_demesne_active = False
    session.courtship_demesne_region = None
    session.courtship_pending_pathways = None
    session.courtship_encounter_reroll_spent = False
    entry_source = session.courtship_entry_source
    if entry_source is None and session.adventure_id == COURTSHIP_DEMESNE_ADVENTURE_ID:
        entry_source = "standalone"
    elif entry_source is None:
        entry_source = "fd_portal"
    if entry_source in {"fd_portal", "flower_portal"}:
        session.courtship_entry_source = None
        if tile is not None:
            session.map_state.current_tile_id = tile.id
        if show_rolls:
            label = "Norindaal" if entry_source == "flower_portal" else "the Forsaken Depths"
            session.log.append(
                f"The party casts Flower Portal and returns to {label} "
                f"({'at ' + tile.title if tile else 'return tile'}, TCOTFD)."
            )
        return True
    if entry_source == "standalone":
        if show_rolls:
            session.log.append(
                "The party casts Flower Portal and returns to the mortal world (TCOTFD / Book of Secrets entry 1)."
            )
        engine._complete_dungeon(session)
        if session.mode == "complete":
            survivors = [member for member in session.party if member.current_life > 0]
            session.summary = [
                "Completed a visit to the Blossoms' Demesne (Courtship of Flower Demons).",
                f"{len(survivors)} of {len(session.party)} party members returned safely.",
                "Between adventures, surviving heroes fully heal and keep treasure already recorded on their sheets.",
            ]
        return session.mode == "complete"
    session.courtship_entry_source = None
    if tile is not None:
        session.map_state.current_tile_id = tile.id
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


def _return_to_meadows_and_roll(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    """BoS entries 8/30 footer — return to the Meadows Encounter table and roll again."""
    session.courtship_demesne_region = "meadows"
    session.log.append("Return to the Meadows Encounter table and roll again (TCOTFD).")
    return roll_courtship_encounter(engine, session, show_rolls=show_rolls)


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
    from .courtship_apothecary_brew import unlock_apothecary_brew_after_encounter

    unlock_apothecary_brew_after_encounter(session)
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
        session.courtship_pathway_secret_trail = bool(row.get("clue_secret_trail"))
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
        from .courtship_book_of_secrets import apply_book_of_secrets_entry

        entry = int(row.get("entry", 0))
        session.log.extend(
            apply_book_of_secrets_entry(
                session,
                entry,
                _living_party(session),
                show_rolls=show_rolls,
                engine=engine,
            )
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
                from .courtship_ingredients import format_common_ingredient, format_uncommon_ingredient

                if reward == "mineral_ingredients":
                    item = "Mineral ingredient"
                elif reward == "meadow_ingredients":
                    item = format_uncommon_ingredient()
                else:
                    item = format_common_ingredient()
                member.inventory.append(item)
                session.log.append(f"{member.name} harvests {item} (TCOTFD).")
                from .courtship_blossoms_items import offer_shovel_substitute

                tier = "uncommon" if reward == "meadow_ingredients" or "uncommon" in item.lower() else "common"
                offer_shovel_substitute(session, item, tier=tier)
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
        if _has_keyword(session, "TRUELOVE") and _has_keyword(session, "PANDORA"):
            from .courtship_book_of_secrets import apply_book_of_secrets_entry

            session.log.extend(
                apply_book_of_secrets_entry(
                    session,
                    11,
                    _living_party(session),
                    show_rolls=show_rolls,
                    engine=engine,
                )
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
        from .courtship_book_of_secrets import apply_book_of_secrets_entry

        session.log.extend(
            apply_book_of_secrets_entry(
                session,
                31,
                _living_party(session),
                show_rolls=show_rolls,
                engine=engine,
            )
        )
        return
    if effect == "lady_of_lament":
        tile = _combat_tile(engine, session)
        if tile is None:
            session.log.append("No Demesne tile is active for the Lady of Lament.")
            return
        hcl = engine._highest_character_level(session.party)
        _spawn_courtship(
            engine,
            session,
            tile,
            {
                "template": "Lady of Lament",
                "count": "1",
                "category": "boss",
                "level_delta": 5,
                "life_delta": 2,
            },
            hcl=hcl,
            show_rolls=show_rolls,
        )
        if _has_keyword(session, "TRUELOVE"):
            session.log.append("The Lady of Lament recognizes her faithful lover (TCOTFD).")
        elif _has_keyword(session, "KEEPSAKE"):
            session.log.append(
                "Present the Keepsake before wooing for +3 on Giving rolls (BoS entry 21, TCOTFD)."
            )
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
        session.courtship_pending_choice = "occlith"
        session.courtship_pending_choice_label = "The Occlith"
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
            from .courtship_book_of_secrets import apply_book_of_secrets_entry

            session.log.extend(
                apply_book_of_secrets_entry(
                    session,
                    15,
                    _living_party(session),
                    show_rolls=show_rolls,
                    engine=engine,
                )
            )
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
            from .courtship_book_of_secrets import apply_book_of_secrets_entry

            session.log.extend(
                apply_book_of_secrets_entry(
                    session,
                    12,
                    _living_party(session),
                    show_rolls=show_rolls,
                    engine=engine,
                )
            )
        else:
            _grant_party_clues(engine, session, tile, 1, show_rolls=show_rolls)
            session.log.append("Strange Follies failed — re-roll on the Palace table (TCOTFD).")
        return
    if effect == "queens_locked_vault":
        from .courtship_book_of_secrets import apply_book_of_secrets_entry

        if _has_keyword(session, "ACERBIC"):
            session.log.extend(
                apply_book_of_secrets_entry(
                    session,
                    3,
                    _living_party(session),
                    show_rolls=show_rolls,
                    engine=engine,
                )
            )
        elif _has_keyword(session, "TRUELOVE"):
            session.log.extend(
                apply_book_of_secrets_entry(
                    session,
                    12,
                    _living_party(session),
                    show_rolls=show_rolls,
                    engine=engine,
                )
            )
        else:
            session.log.append("The silver-chained vault cannot be opened without ACERBIC or TRUELOVE (TCOTFD).")
        for member in _living_party(session):
            _melancholy_check(session, member, show_rolls=show_rolls)
        return
    if effect == "unique_reroll":
        if row.get("key") == "lex_the_cambion":
            from .courtship_book_of_secrets import apply_book_of_secrets_entry

            session.log.extend(
                apply_book_of_secrets_entry(
                    session,
                    32,
                    _living_party(session),
                    show_rolls=show_rolls,
                    engine=engine,
                )
            )
        return
    summary = row.get("summary") or row.get("name") or effect
    session.log.append(f"{summary} (TCOTFD).")


def _clear_courtship_woo(session: SessionState) -> None:
    session.courtship_woo_active = False
    session.courtship_woo_template = None
    session.courtship_woo_category = None
    session.courtship_woo_giving_penalty = 0
    session.courtship_woo_withholding_penalty = 0
    session.courtship_woo_dominant_blocked = False
    session.courtship_woo_dominant_stance = False
    session.courtship_woo_passionate_stance = False
    session.courtship_woo_successes = 0
    session.courtship_woo_speaker_id = None
    session.courtship_damsel_penalty_pending = False
    session.courtship_damsel_penalty_mode = None
    session.courtship_lady_keepsake_bonus = 0
    session.courtship_libidinal_character_id = None
    session.courtship_libidinal_reroll_available = False
    if session.courtship_virile_might_character_id:
        member = next(
            (item for item in session.party if item.character_id == session.courtship_virile_might_character_id),
            None,
        )
        if member is not None:
            from .courtship_apothecary import consume_virile_might_pills

            if consume_virile_might_pills(member):
                session.log.append(f"{member.name}'s Pills of virile might are spent (TCOTFD p.83).")
        session.courtship_virile_might_character_id = None


def resolve_courtship_libidinal_reroll(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_woo_active:
        session.log.append("Libidinal Enhancement applies during wooing (TCOTFD p.27).")
        return False
    if not session.courtship_libidinal_reroll_available:
        session.log.append("No Libidinal Enhancement re-roll remains (TCOTFD p.27).")
        return False
    speaker = _courtship_woo_speaker(session, engine)
    if speaker is None:
        return False
    if session.courtship_libidinal_character_id and speaker.character_id != session.courtship_libidinal_character_id:
        session.log.append("Only the Libidinal Enhancement target may re-roll Giving (TCOTFD p.27).")
        return False
    speaker.current_life = max(0, speaker.current_life - 1)
    session.courtship_libidinal_reroll_available = False
    session.log.append(
        f"{speaker.name} spends 1 Life for a Libidinal Enhancement re-roll ({speaker.current_life}/{speaker.max_life}, TCOTFD p.27)."
    )
    return resolve_courtship_woo_giving(engine, session, show_rolls=show_rolls)


def _remove_party_item(session: SessionState, needle: str) -> bool:
    lowered = needle.lower()
    for member in session.party:
        for index, item in enumerate(member.inventory):
            if lowered in item.lower():
                member.inventory.pop(index)
                return True
    return False


def update_courtship_on_combat_end(
    engine: RandomDungeonEngine,
    session: SessionState,
    defeated: list[EnemyState],
    *,
    show_rolls: bool = True,
) -> None:
    if not session.courtship_demesne_active:
        return
    for enemy in defeated:
        if enemy.name != "Lady of Lament" or enemy.subdued:
            continue
        member = engine._member_by_marching_order(session, 1)
        if member and session.courtship_matron_head_quest_active:
            member.inventory.append("Lady of Lament's head")
            if show_rolls:
                session.log.append(
                    f"{member.name} claims the Lady of Lament's head for the Matron's quest (BoS entry 8, TCOTFD)."
                )
        session.courtship_demesne_region = "woods"
        if show_rolls:
            session.log.append("Return to the Woods Encounter table (BoS entry 21, TCOTFD).")


def _woo_rules(template: str) -> dict[str, Any]:
    return COURTSHIP_WOO_RULES.get(template, {})


def _start_courtship_woo(
    engine: RandomDungeonEngine,
    session: SessionState,
    template: str,
    category: str,
    *,
    show_rolls: bool,
) -> bool:
    speaker = engine._member_by_marching_order(session, 1)
    if speaker is None:
        return False
    if _maybe_apply_truelove_infidelity(session, speaker, template, category, show_rolls=show_rolls):
        if show_rolls:
            session.log.append("The wooing continues without the Lady's favor (TCOTFD).")
    if template == "Lady of Lament" and speaker.class_id.lower() == "satyr":
        session.log.append("The Lady of Lament loathes satyrs and refuses their advances (BoS entry 21, TCOTFD).")
        return False
    rules = _woo_rules(template)
    session.courtship_woo_active = True
    session.courtship_woo_template = template
    session.courtship_woo_category = category
    session.courtship_woo_speaker_id = speaker.character_id
    session.courtship_woo_dominant_blocked = bool(rules.get("dominant_blocked"))
    session.courtship_woo_dominant_stance = False
    session.courtship_woo_passionate_stance = False
    session.courtship_woo_giving_penalty = 0
    session.courtship_woo_withholding_penalty = 0
    session.courtship_woo_successes = 0
    if template == "Matron of Summer":
        from .courtship_book_of_secrets import apply_matron_wooing_effects

        session.log.extend(
            apply_matron_wooing_effects(session, session.party, show_rolls=show_rolls)
        )
        session.log.append("The Matron's lovers suffer no Melancholy during this wooing (BoS entry 30, TCOTFD).")
    if show_rolls:
        session.log.append(
            f"{speaker.name} begins wooing {template} — use Giving or Withholding rolls "
            f"({COURTSHIP_WOO_SUCCESSES_REQUIRED} successful Giving rolls win peacefully, TCOTFD)."
        )
        if session.courtship_woo_dominant_blocked:
            session.log.append("Their incessant giggling prevents a dominant stance (TCOTFD).")
        if template == "Matron of Summer":
            session.log.append(
                "Passionate stance subtracts 1 from the Matron's level on social rolls (BoS entry 30, TCOTFD)."
            )
        if template == "Lady of Lament":
            session.log.append(
                "Romantic stance subtracts 1 from the Lady's level on social rolls (BoS entry 21, TCOTFD)."
            )
        if template == "Lady of Lament" and session.courtship_lady_doubles_active:
            session.log.append(
                "Three Ladies demand simultaneous pleasure — each successful Giving roll must satisfy all three "
                "(BoS entry 21, TCOTFD)."
            )
    return True


def _courtship_woo_foe_level(session: SessionState, hcl: int) -> int:
    level = hcl
    rules = _woo_rules(session.courtship_woo_template or "")
    if session.courtship_woo_passionate_stance:
        level += int(rules.get("passionate_stance_foe_level_delta", 0))
    if session.courtship_woo_dominant_stance and not session.courtship_woo_dominant_blocked:
        level += int(rules.get("dominant_foe_level_delta", 0))
    return max(1, level)


def _courtship_woo_speaker(session: SessionState, engine: RandomDungeonEngine) -> PartyMemberState | None:
    if session.courtship_woo_speaker_id:
        member = next(
            (item for item in session.party if item.character_id == session.courtship_woo_speaker_id),
            None,
        )
        if member and member.current_life > 0:
            return member
    return engine._member_by_marching_order(session, 1)


def resolve_courtship_woo_giving(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    dominant_stance: bool = False,
    passionate_stance: bool = False,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_woo_active:
        session.log.append("No courtship wooing is in progress.")
        return False
    tile = _combat_tile(engine, session)
    speaker = _courtship_woo_speaker(session, engine)
    if speaker is None or tile is None:
        return False
    from .courtship_blossoms_items import talisman_blocks_giving

    if talisman_blocks_giving(speaker):
        session.log.append(
            f"{speaker.name} cannot make Giving rolls while wearing the Talisman of Impotence (TCOTFD p.69)."
        )
        return False
    template = session.courtship_woo_template or "flower demons"
    rules = _woo_rules(template)
    if passionate_stance:
        session.courtship_woo_passionate_stance = True
    if dominant_stance and not session.courtship_woo_dominant_blocked:
        session.courtship_woo_dominant_stance = True
    elif dominant_stance:
        session.log.append("A dominant stance is impossible here (TCOTFD).")
    hcl = engine._highest_character_level(session.party)
    penalty = session.courtship_woo_giving_penalty + int(rules.get("giving_penalty", 0))
    penalty = max(0, penalty - int(session.courtship_lady_keepsake_bonus))
    if rules.get("giving_penalty_per_turn"):
        penalty += session.courtship_woo_successes * int(rules["giving_penalty_per_turn"])
    foe_level = _courtship_woo_foe_level(session, hcl)
    if show_rolls and session.courtship_woo_passionate_stance:
        session.log.append(f"Passionate stance — {template} defends as level {foe_level} (TCOTFD).")
    from .class_abilities import resolve_social_save
    from .courtship_apothecary import (
        note_virile_might_use,
        virile_might_breeding_save_bonus,
        virile_might_giving_bonus,
        virile_might_giving_roll_bonus,
        virile_retention_breeding_bonus,
        virile_retention_withholding_bonus,
    )

    giving_bonus = virile_might_giving_roll_bonus(speaker)
    if giving_bonus:
        note_virile_might_use(session, speaker)
        if show_rolls:
            session.log.append(
                f"{speaker.name} gains +{virile_might_giving_bonus(speaker)} Giving and "
                f"+{virile_might_breeding_save_bonus(speaker)} breeding save from Pills of virile might (TCOTFD p.83)."
            )

    ok, social_log = resolve_social_save(
        session,
        speaker,
        foe_level,
        show_rolls=show_rolls,
        label=f"Giving roll vs {template}",
        bonus=-penalty + giving_bonus,
    )
    session.log.extend(social_log)
    if ok:
        session.courtship_woo_successes += 1
        if rules.get("giving_heals"):
            speaker.current_life = min(speaker.max_life, speaker.current_life + int(rules["giving_heals"]))
            session.log.append(f"{speaker.name} regains {rules['giving_heals']} Life from the courtship (TCOTFD).")
        if rules.get("giving_life_or_madness"):
            session.courtship_damsel_penalty_pending = True
            session.courtship_damsel_penalty_mode = None
            session.log.append(
                "Damsel of Teeming Roses — choose Life loss or Madness for the next Withholding failure (TCOTFD)."
            )
        session.log.append(
            f"Successful Giving roll ({session.courtship_woo_successes}/{COURTSHIP_WOO_SUCCESSES_REQUIRED}, TCOTFD)."
        )
        if session.courtship_woo_successes >= COURTSHIP_WOO_SUCCESSES_REQUIRED:
            _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
            session.log.append(f"Peaceful wooing of {template} succeeds — combat avoided (TCOTFD).")
            if template == "Matron of Summer":
                from .courtship_book_of_secrets import apply_book_of_secrets_entry

                session.log.extend(
                    apply_book_of_secrets_entry(
                        session, 8, session.party, show_rolls=show_rolls, engine=engine
                    )
                )
            if template == "Lady of Lament":
                from .courtship_book_of_secrets import apply_lady_lament_truelove

                session.log.extend(
                    apply_lady_lament_truelove(session, speaker, show_rolls=show_rolls)
                )
                session.courtship_demesne_region = "woods"
                session.log.append("Roll on the Woods Encounter table when you leave her side (BoS entry 9, TCOTFD).")
            tile.enemies.clear()
            tile.initial_enemy_count = 0
            _clear_courtship_woo(session)
            if template == "Matron of Summer":
                _return_to_meadows_and_roll(engine, session, show_rolls=show_rolls)
        return True
    session.log.append(f"Giving roll fails — {template} grows impatient (TCOTFD).")
    return True


def resolve_courtship_woo_withholding(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    dominant_stance: bool = False,
    passionate_stance: bool = False,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_woo_active:
        session.log.append("No courtship wooing is in progress.")
        return False
    speaker = _courtship_woo_speaker(session, engine)
    if speaker is None:
        return False
    template = session.courtship_woo_template or "flower demons"
    rules = _woo_rules(template)
    if passionate_stance:
        session.courtship_woo_passionate_stance = True
    if dominant_stance and not session.courtship_woo_dominant_blocked:
        session.courtship_woo_dominant_stance = True
    hcl = engine._highest_character_level(session.party)
    penalty = session.courtship_woo_withholding_penalty
    foe_level = _courtship_woo_foe_level(session, hcl)
    if show_rolls and session.courtship_woo_passionate_stance:
        session.log.append(f"Passionate stance — {template} defends as level {foe_level} (TCOTFD).")
    from .class_abilities import resolve_social_save
    from .courtship_apothecary import (
        note_virile_might_use,
        virile_might_breeding_save_bonus,
        virile_retention_breeding_bonus,
        virile_retention_withholding_bonus,
    )

    withholding_bonus = virile_retention_withholding_bonus(speaker)
    breeding_bonus = virile_might_breeding_save_bonus(speaker) + virile_retention_breeding_bonus(speaker)
    if virile_might_breeding_save_bonus(speaker):
        note_virile_might_use(session, speaker)
        if show_rolls:
            session.log.append(
                f"{speaker.name} gains +{virile_might_breeding_save_bonus(speaker)} breeding save from Pills of virile might (TCOTFD p.83)."
            )
    elif withholding_bonus or virile_retention_breeding_bonus(speaker):
        if show_rolls:
            session.log.append(
                f"{speaker.name} gains +{withholding_bonus} Withholding and "
                f"+{virile_retention_breeding_bonus(speaker)} breeding save from Pills of virile retention (TCOTFD p.83)."
            )

    ok, social_log = resolve_social_save(
        session,
        speaker,
        foe_level,
        show_rolls=show_rolls,
        label=f"Withholding roll vs {template}",
        bonus=-penalty + withholding_bonus + breeding_bonus,
    )
    session.log.extend(social_log)
    if ok:
        session.log.append(f"Withholding roll succeeds (TCOTFD).")
        return True
    if rules.get("withholding_fail_penalty"):
        session.courtship_woo_withholding_penalty += int(rules["withholding_fail_penalty"])
        session.log.append(
            f"Failed Withholding — cumulative −{session.courtship_woo_withholding_penalty} to future Withholding (TCOTFD)."
        )
    if rules.get("giving_life_or_madness") and session.courtship_damsel_penalty_mode:
        mode = session.courtship_damsel_penalty_mode
        session.courtship_damsel_penalty_mode = None
        session.courtship_damsel_penalty_pending = False
        if mode == "madness":
            session.log.extend(apply_madness_gain(session, speaker, source="Damsel of Teeming Roses"))
        else:
            speaker.current_life = max(0, speaker.current_life - 1)
            session.log.append(f"{speaker.name} loses 1 Life from failed Withholding (TCOTFD).")
    elif rules.get("withholding_life_loss"):
        speaker.current_life = max(0, speaker.current_life - int(rules["withholding_life_loss"]))
        session.log.append(f"{speaker.name} loses {rules['withholding_life_loss']} Life (TCOTFD).")
    elif rules.get("withholding_life_loss_per_six"):
        total = social_log[-1] if social_log else ""
        loss = max(1, (session.courtship_woo_withholding_penalty + 6) // 6)
        speaker.current_life = max(0, speaker.current_life - loss)
        session.log.append(f"{speaker.name} loses {loss} Life from failed Withholding (TCOTFD).")
    if not rules.get("no_melancholy"):
        _melancholy_check(session, speaker, show_rolls=show_rolls)
    session.log.append(f"Withholding roll fails (TCOTFD).")
    return True


def _maybe_queue_seduce_reaction(session: SessionState, template: str) -> bool:
    from .courtship_pandora import pandora_forces_fight_to_death

    if pandora_forces_fight_to_death(session, template):
        session.log.append(
            f"PANDORA: {template} fights to the death — seduction is impossible (BoS entry 2, TCOTFD)."
        )
        return False
    if _woo_rules(template).get("seduce_reaction"):
        session.courtship_pending_choice = "seduce_or_fight"
        session.courtship_pending_choice_label = template
        session.log.append(f"{template} may seduce or fight — roll Demesne reaction (d6, TCOTFD).")
        return True
    return False


def resolve_courtship_fight_encounter(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if session.courtship_pending_choice != "woo_or_fight":
        session.log.append("No Demesne woo-or-fight choice is pending.")
        return False
    tile = _combat_tile(engine, session)
    label = session.courtship_pending_choice_label or "flower demons"
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    _clear_courtship_woo(session)
    if tile is None or not tile.enemies:
        session.log.append("The Demesne encounter has already departed.")
        return False
    if show_rolls:
        session.log.append("The party chooses to fight (TCOTFD).")
    from .courtship_pandora import pandora_forces_fight_to_death, prepare_pandora_fight

    if pandora_forces_fight_to_death(session, label):
        prepare_pandora_fight(session, tile.enemies)
    elif _maybe_queue_seduce_reaction(session, label):
        return True
    if session.mode == "exploration":
        engine._announce_encounter(session, tile, show_rolls=show_rolls)
    return True


def resolve_courtship_woo_encounter(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if session.courtship_pending_choice != "woo_or_fight":
        session.log.append("No Demesne woo-or-fight choice is pending.")
        return False
    label = session.courtship_pending_choice_label or "flower demons"
    from .courtship_pandora import pandora_blocks_wooing

    if pandora_blocks_wooing(session, label):
        session.log.append(f"PANDORA: {label} refuses all wooing (BoS entry 2, TCOTFD).")
        return resolve_courtship_fight_encounter(engine, session, show_rolls=show_rolls)
    category = "minions"
    tile = _combat_tile(engine, session)
    if tile and tile.enemies:
        category = tile.enemies[0].category or category
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    if tile is None:
        return False
    return _start_courtship_woo(engine, session, label, category, show_rolls=show_rolls)


def resolve_courtship_woo_abort_fight(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_woo_active:
        session.log.append("No courtship wooing is in progress.")
        return False
    template = session.courtship_woo_template or "flower demons"
    tile = _combat_tile(engine, session)
    _clear_courtship_woo(session)
    if show_rolls:
        session.log.append(f"Wooing ends — {template} will fight (TCOTFD).")
    if tile is None or not tile.enemies:
        return False
    if _maybe_queue_seduce_reaction(session, template):
        return True
    if session.mode == "exploration":
        engine._announce_encounter(session, tile, show_rolls=show_rolls)
    return True


def resolve_courtship_seduce_reaction(
    engine: RandomDungeonEngine,
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    if session.courtship_pending_choice != "seduce_or_fight":
        session.log.append("No seduce-or-fight reaction is pending.")
        return False
    template = session.courtship_pending_choice_label or "flower demons"
    tile = _combat_tile(engine, session)
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    if tile is None or not tile.enemies:
        session.log.append("The Demesne encounter has already departed.")
        return False
    if choice == "fight":
        if show_rolls:
            session.log.append(f"{template} fights to the death (TCOTFD).")
        from .courtship_pandora import prepare_pandora_fight, pandora_forces_fight_to_death

        if pandora_forces_fight_to_death(session, template):
            prepare_pandora_fight(session, tile.enemies)
        if session.mode == "exploration":
            engine._announce_encounter(session, tile, show_rolls=show_rolls)
        return True
    roll = roll_d6()
    from .courtship_pandora import pandora_reaction_penalty

    penalty = pandora_reaction_penalty(session, template)
    effective = roll + penalty
    if show_rolls:
        session.log.append(
            f"Demesne reaction d6 = {roll}"
            + (f" + {penalty} PANDORA = {effective}" if penalty else "")
            + " (1–6 seduce, 7+ fight, TCOTFD)."
        )
    if effective >= 7:
        session.log.append(f"{template} fights to the death (TCOTFD).")
        from .courtship_pandora import prepare_pandora_fight, pandora_forces_fight_to_death

        if pandora_forces_fight_to_death(session, template):
            prepare_pandora_fight(session, tile.enemies)
        if session.mode == "exploration":
            engine._announce_encounter(session, tile, show_rolls=show_rolls)
        return True
    speaker = engine._member_by_marching_order(session, 1)
    if speaker is None:
        return False
    hcl = engine._highest_character_level(session.party)
    from .class_abilities import resolve_social_save
    from .courtship_apothecary import note_virile_might_use, virile_might_breeding_save_bonus

    breeding_bonus = virile_might_breeding_save_bonus(speaker)
    if breeding_bonus:
        note_virile_might_use(session, speaker)
        if show_rolls:
            session.log.append(
                f"{speaker.name} gains +{breeding_bonus} breeding save from Pills of virile might (TCOTFD p.83)."
            )

    ok, social_log = resolve_social_save(
        session,
        speaker,
        hcl,
        show_rolls=show_rolls,
        label=f"seduction by {template}",
        bonus=breeding_bonus,
    )
    session.log.extend(social_log)
    if ok:
        _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
        session.log.append(f"{template} seduces peacefully — gain d3 Clues (TCOTFD).")
        if template == "Mistress of Black Lashes" and roll <= 2:
            session.courtship_pending_choice = "mistress_quest_ingredients"
            session.courtship_pending_choice_label = "Mistress of Black Lashes"
            session.log.append(
                "The Mistress quests for 3 rare ingredients — deliver when ready (TCOTFD p.65)."
            )
        tile.enemies.clear()
        tile.initial_enemy_count = 0
        return True
    session.log.append(f"Seduction fails — {template} attacks (TCOTFD).")
    if session.mode == "exploration":
        engine._announce_encounter(session, tile, show_rolls=show_rolls)
    return True


def resolve_courtship_occlith_choice(
    engine: RandomDungeonEngine,
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    if session.courtship_pending_choice != "occlith":
        session.log.append("The Occlith is not awaiting a choice.")
        return False
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    tile = _combat_tile(engine, session)
    hcl = engine._highest_character_level(session.party)
    if choice == "parley":
        _grant_party_clues(engine, session, tile, roll_d3(), show_rolls=show_rolls)
        session.log.append("Occlith parley — Book of Secrets entry 6; gain d3 Clues (TCOTFD).")
        return True
    if choice == "attack" and tile is not None:
        spawned = engine._spawn_from_template_name(
            session,
            table_key="courtship_demons",
            template_name="Occlith",
            count=1,
            hcl=hcl,
            category="weird",
        )
        if spawned:
            tile.enemies.extend(spawned)
            tile.initial_enemy_count = len(tile.enemies)
            session.log.append("The Occlith attacks — Book of Secrets entry 5 (TCOTFD).")
            if session.mode == "exploration":
                engine._announce_encounter(session, tile, show_rolls=show_rolls)
        else:
            session.log.append("Occlith bestiary entry missing — resolve Book of Secrets entry 5 manually.")
        return True
    session.log.append("Choose attack or parley with the Occlith.")
    return False


def resolve_courtship_lady_of_lament_choice(
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    if session.courtship_pending_choice != "lady_of_lament":
        session.log.append("The Lady of Lament is not awaiting a choice.")
        return False
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    if choice == "keepsake" and _has_keyword(session, "KEEPSAKE"):
        session.courtship_lady_keepsake_bonus = 3
        if show_rolls:
            session.log.append(
                "Keepsake presented — +3 on Giving rolls vs the Lady of Lament this encounter (TCOTFD)."
            )
        return True
    if show_rolls:
        session.log.append("The Lady of Lament fades without further incident (TCOTFD).")
    return True


def apply_lady_keepsake_bonus(session: SessionState, *, show_rolls: bool = True) -> bool:
    if not _has_keyword(session, "KEEPSAKE"):
        session.log.append("Need the KEEPSAKE keyword to present the token (TCOTFD).")
        return False
    session.courtship_lady_keepsake_bonus = 3
    if show_rolls:
        session.log.append(
            "Keepsake presented — +3 on Giving rolls vs the Lady of Lament this encounter (TCOTFD)."
        )
    return True


def spend_courtship_secret_trail_clue(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_pathway_secret_trail:
        session.log.append("No secret trail is offered on this pathway.")
        return False
    if not engine._spend_clues(session, 1):
        session.log.append("Need 1 Clue for the secret trail (BoS entry 13, TCOTFD).")
        return False
    tile = _combat_tile(engine, session)
    _grant_party_clues(engine, session, tile, 2, show_rolls=show_rolls)
    session.courtship_pathway_secret_trail = False
    if show_rolls:
        session.log.append("Secret trail — spend 1 Clue, gain 2 Clues net (BoS entry 13, TCOTFD).")
    return True


def resolve_courtship_damsel_penalty(
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.courtship_damsel_penalty_pending:
        session.log.append("No Damsel penalty choice is pending.")
        return False
    if choice not in {"life", "madness"}:
        session.log.append("Choose Life loss or Madness for the next Withholding failure (TCOTFD).")
        return False
    session.courtship_damsel_penalty_mode = choice  # type: ignore[assignment]
    session.courtship_damsel_penalty_pending = False
    label = "1 Life" if choice == "life" else "1 Madness"
    if show_rolls:
        session.log.append(
            f"Damsel of Teeming Roses — next failed Withholding costs {label} (TCOTFD)."
        )
    return True


def resolve_courtship_book_choice(
    engine: RandomDungeonEngine,
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    from .courtship_book_of_secrets import resolve_courtship_book_choice as _resolve

    return _resolve(engine, session, choice, show_rolls=show_rolls)
