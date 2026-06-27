"""Apothecary Cookbook brewing (TCOTFD p.79-98, Wandering Alchemist p.7-9)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..schemas import PartyMemberState, SessionState
from .courtship_apothecary import (
    PILLS_OF_VIRILE_MIGHT,
    note_virile_might_use,
    virile_might_breeding_save_bonus,
    virile_might_giving_roll_bonus,
)
from .courtship_classes import is_wandering_alchemist
from .dice import roll_d6

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

APOTHECARY_ITEM_TAG = "(Apothecary"


def _rules_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "rules" / "courtship_apothecary_recipes.json"


@lru_cache(maxsize=1)
def load_apothecary_recipes() -> list[dict[str, Any]]:
    data = json.loads(_rules_path().read_text(encoding="utf-8"))
    recipes = data.get("recipes", [])
    return [item for item in recipes if isinstance(item, dict)]


def recipe_by_key(key: str) -> dict[str, Any] | None:
    return next((recipe for recipe in load_apothecary_recipes() if recipe.get("key") == key), None)


def is_apothecary_brew_item(item: str) -> bool:
    return APOTHECARY_ITEM_TAG in item or item in {recipe.get("item", "") for recipe in load_apothecary_recipes()}


def member_has_mortar_and_pestle(member: PartyMemberState) -> bool:
    for item in member.inventory:
        lower = item.lower()
        if "mortar and pestle" in lower or ("mortar" in lower and "pestle" in lower):
            return True
    return False


def apothecary_brewer(session: SessionState) -> PartyMemberState | None:
    for member in session.party:
        if member.current_life <= 0:
            continue
        if is_wandering_alchemist(member) and member_has_mortar_and_pestle(member):
            return member
    return None


def apothecary_brew_available(session: SessionState) -> bool:
    if not session.courtship_enabled:
        return False
    if session.mode != "exploration":
        return False
    if session.courtship_woo_active:
        return False
    if session.courtship_apothecary_brew_locked:
        return False
    if session.courtship_demesne_active:
        return apothecary_brewer(session) is not None
    if session.camped_outside:
        return apothecary_brewer(session) is not None
    return False


def apothecary_brew_context_label(session: SessionState) -> str:
    if session.courtship_demesne_active:
        return "between Demesne encounters"
    if session.camped_outside:
        return "while camped outdoors"
    return "nowhere available"


def tag_settlement_apothecary_available(session: SessionState) -> bool:
    """TAG settlement apothecary when guild banking campaign mode is active."""
    return bool(session.tag_banking_enabled)


def try_outdoor_ingredient_forage(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    show_rolls: bool = True,
) -> list[str]:
    """Outdoor Norindaal foraging when a Wandering Alchemist is present (TCOTFD Apothecary scope)."""
    if not session.courtship_enabled or session.courtship_demesne_active:
        return []
    if session.camped_outside:
        return []
    brewer = apothecary_brewer(session)
    if brewer is None:
        return []
    roll = roll_d6()
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{brewer.name} searches for Apothecary ingredients outdoors: d6 = {roll} (TCOTFD)."
        )
    if roll < 4:
        return log
    brewer.inventory.append("Common ingredient")
    log.append(f"{brewer.name} forages a common ingredient in Norindaal (TCOTFD Apothecary).")
    return log


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace("'", "'").replace("�", "'")).strip()


def _ingredient_matches(item: str, spec: dict[str, Any]) -> bool:
    lower = _normalize_name(item)
    tier = str(spec.get("tier", "common")).lower()
    name = _normalize_name(str(spec.get("name", "")))

    if tier == "special":
        return "soul cube" in lower
    if tier == "mineral":
        if "mineral ingredient" in lower:
            return not name or name in lower or name == "mineral ingredient"
        return name in lower if name else "mineral" in lower
    if tier == "common":
        if "common ingredient" in lower and "uncommon" not in lower and "mineral" not in lower:
            return not name or name in lower or name == "common ingredient"
        return bool(name and name in lower)
    if tier == "uncommon":
        if "uncommon ingredient" in lower:
            return not name or name in lower or name == "uncommon ingredient"
        return bool(name and name in lower)
    if tier in {"rare", "demesne"}:
        return bool(name and name in lower)
    return bool(name and name in lower)


def _find_ingredient(party: list[PartyMemberState], spec: dict[str, Any]) -> tuple[PartyMemberState, int] | None:
    names = [str(spec.get("name", ""))]
    names.extend(str(item) for item in spec.get("alternates", []) if item)
    count = int(spec.get("count", 1) or 1)
    alt_count = int(spec.get("alt_count", count) or count)
    for alt_index, needle in enumerate(names):
        required = alt_count if alt_index else count
        needle_norm = _normalize_name(needle)
        trial = dict(spec)
        trial["name"] = needle_norm
        for _ in range(required):
            found: tuple[PartyMemberState, int] | None = None
            for member in party:
                for index, item in enumerate(member.inventory):
                    if _ingredient_matches(item, trial):
                        found = (member, index)
                        break
                if found:
                    break
            if found is None:
                break
        else:
            return found
    return None


def party_can_supply_ingredients(party: list[PartyMemberState], recipe: dict[str, Any]) -> bool:
    scratch: dict[str, list[tuple[PartyMemberState, int, str]]] = {}
    for spec in recipe.get("ingredients", []):
        if not isinstance(spec, dict):
            return False
        key = json.dumps(spec, sort_keys=True)
        copies = scratch.setdefault(key, [])
        count = int(spec.get("count", 1) or 1)
        names = [str(spec.get("name", ""))]
        names.extend(str(item) for item in spec.get("alternates", []) if item)
        matched = False
        for alt_index, needle in enumerate(names):
            required = int(spec.get("alt_count", count) or count) if alt_index else count
            trial = dict(spec)
            trial["name"] = needle
            for _ in range(required):
                hit: tuple[PartyMemberState, int] | None = None
                for member in party:
                    for index, item in enumerate(member.inventory):
                        token = (member.character_id, index)
                        if any(token == (m.character_id, i) for m, i, _ in copies):
                            continue
                        if _ingredient_matches(item, trial):
                            hit = (member, index)
                            break
                    if hit:
                        break
                if hit is None:
                    break
                member, index = hit
                copies.append((member, index, member.inventory[index]))
            else:
                matched = True
                break
        if not matched:
            return False
    return True


def _consume_recipe_ingredients(party: list[PartyMemberState], recipe: dict[str, Any], log: list[str]) -> bool:
    picks: list[tuple[PartyMemberState, int]] = []
    for spec in recipe.get("ingredients", []):
        if not isinstance(spec, dict):
            return False
        count = int(spec.get("count", 1) or 1)
        names = [str(spec.get("name", ""))]
        names.extend(str(item) for item in spec.get("alternates", []) if item)
        consumed = False
        for alt_index, needle in enumerate(names):
            required = int(spec.get("alt_count", count) or count) if alt_index else count
            trial = dict(spec)
            trial["name"] = needle
            alt_picks: list[tuple[PartyMemberState, int]] = []
            for _ in range(required):
                hit: tuple[PartyMemberState, int] | None = None
                for member in party:
                    for index, item in enumerate(member.inventory):
                        if (member, index) in picks or (member, index) in alt_picks:
                            continue
                        if _ingredient_matches(item, trial):
                            hit = (member, index)
                            break
                    if hit:
                        break
                if hit is None:
                    alt_picks = []
                    break
                alt_picks.append(hit)
            if alt_picks:
                picks.extend(alt_picks)
                consumed = True
                break
        if not consumed:
            return False
    by_member: dict[str, list[int]] = {}
    for member, index in picks:
        by_member.setdefault(member.character_id, []).append(index)
    for member in party:
        for index in sorted(by_member.get(member.character_id, []), reverse=True):
            item = member.inventory.pop(index)
            log.append(f"Consumed {item} for {recipe.get('name')} (TCOTFD).")
    return True


def _karmic_calcinator_doubles_duration(party: list[PartyMemberState]) -> bool:
    from .courtship_blossoms_items import karmic_calcinator_active

    return any(karmic_calcinator_active(member) for member in party)


def _apply_karmic_calcinator_depletion(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    show_rolls: bool,
) -> None:
    from .courtship_blossoms_items import (
        KARMIC_CALCINATOR,
        party_has_karmic_calcinator,
        roll_karmic_calcinator_depletion,
    )

    carrier = party_has_karmic_calcinator(party)
    if carrier is None:
        return
    if roll_karmic_calcinator_depletion(show_rolls=show_rolls, log=session.log):
        return
    for index, item in enumerate(carrier.inventory):
        if item.split(" (")[0].strip() == KARMIC_CALCINATOR:
            carrier.inventory.pop(index)
            break


def _format_brew_item(recipe: dict[str, Any], *, double_duration: bool) -> str:
    duration = str(recipe.get("duration", "1 encounter"))
    if double_duration and duration not in {"immediate", "permanent", "1 day", "1 adventure", "1 pregnancy"}:
        if duration.startswith("d"):
            duration = f"double {duration}"
        elif duration == "1 encounter":
            duration = "2 encounters"
        elif duration.endswith("encounters"):
            duration = f"double {duration}"
    return f"{recipe.get('item')} {APOTHECARY_ITEM_TAG}, {duration})"


def _brew_roll(brewer: PartyMemberState, difficulty: int) -> tuple[bool, int, int]:
    if difficulty <= 0:
        return True, 0, 0
    roll = roll_d6()
    total = roll + brewer.level
    return total >= difficulty, roll, total


def brew_apothecary_recipe(
    engine: RandomDungeonEngine,
    session: SessionState,
    recipe_key: str,
    *,
    show_rolls: bool = True,
) -> bool:
    if not apothecary_brew_available(session):
        session.log.append(
            f"Apothecary brewing is only available {apothecary_brew_context_label(session)} (TCOTFD p.8)."
        )
        return False
    brewer = apothecary_brewer(session)
    if brewer is None:
        session.log.append("A Wandering Alchemist with mortar and pestle must brew (TCOTFD p.7-9).")
        return False
    recipe = recipe_by_key(recipe_key)
    if recipe is None:
        session.log.append("Choose a valid Apothecary recipe (TCOTFD).")
        return False
    living = [member for member in session.party if member.current_life > 0]
    cost = int(recipe.get("cost_gp", 0) or 0)
    if brewer.gold < cost:
        session.log.append(f"{brewer.name} needs {cost}gp in materials for {recipe.get('name')} (TCOTFD).")
        return False
    if not party_can_supply_ingredients(living, recipe):
        session.log.append(f"Missing ingredients for {recipe.get('name')} (TCOTFD Apothecary Charts).")
        return False
    log: list[str] = []
    if not _consume_recipe_ingredients(living, recipe, log):
        session.log.append("Could not consume the required ingredients (TCOTFD).")
        return False
    brewer.gold -= cost
    difficulty = int(recipe.get("difficulty", 0) or 0)
    ok, roll, total = _brew_roll(brewer, difficulty)
    if show_rolls and difficulty > 0:
        session.log.append(
            f"{brewer.name} brews {recipe.get('name')}: d6={roll} + L{brewer.level} = {total} vs {difficulty} (TCOTFD p.8)."
        )
    session.log.extend(log)
    if not ok:
        if session.courtship_demesne_active:
            session.courtship_apothecary_brew_locked = True
            session.log.append(
                f"The brew fails — {brewer.name} cannot try again until after another Demesne encounter (TCOTFD p.8)."
            )
        else:
            session.log.append(
                f"The brew fails — {brewer.name} must move on from camp before trying again (TCOTFD p.8)."
            )
            session.courtship_apothecary_brew_locked = True
        return True
    double_duration = _karmic_calcinator_doubles_duration(living)
    if double_duration and show_rolls:
        session.log.append("Karmic Calcinator doubles the potion duration (TCOTFD p.69).")
        _apply_karmic_calcinator_depletion(session, living, show_rolls=show_rolls)
    item = _format_brew_item(recipe, double_duration=double_duration)
    brewer.inventory.append(item)
    session.log.append(f"{brewer.name} brews {item} (TCOTFD Apothecary Charts).")
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    return True


def unlock_apothecary_brew_after_encounter(session: SessionState) -> None:
    session.courtship_apothecary_brew_locked = False


def list_brewable_recipe_keys(session: SessionState) -> list[str]:
    if not apothecary_brew_available(session):
        return []
    living = [member for member in session.party if member.current_life > 0]
    brewer = apothecary_brewer(session)
    if brewer is None:
        return []
    keys: list[str] = []
    for recipe in load_apothecary_recipes():
        cost = int(recipe.get("cost_gp", 0) or 0)
        if brewer.gold < cost:
            continue
        if party_can_supply_ingredients(living, recipe):
            key = recipe.get("key")
            if isinstance(key, str):
                keys.append(key)
    return keys


def resolve_apothecary_brew_choice(
    engine: RandomDungeonEngine,
    session: SessionState,
    choice: str | None,
    *,
    show_rolls: bool = True,
) -> bool:
    if choice is None:
        session.courtship_pending_choice = "apothecary_brew"
        session.courtship_pending_choice_label = "Apothecary Cookbook"
        return False
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    return brew_apothecary_recipe(engine, session, choice, show_rolls=show_rolls)


def use_apothecary_brew(
    session: SessionState,
    member: PartyMemberState,
    item: str,
    *,
    show_rolls: bool = True,
) -> bool:
    """Use a portable Apothecary brew (any adventure). Returns True when handled."""
    if not is_apothecary_brew_item(item):
        return False
    base = item.split(APOTHECARY_ITEM_TAG)[0].strip()
    if base == PILLS_OF_VIRILE_MIGHT or "Pills of virile might" in base:
        if item not in member.inventory:
            session.log.append(f"{member.name} is not carrying {item}.")
            return True
        member.inventory.remove(item)
        member.inventory.append(PILLS_OF_VIRILE_MIGHT)
        note_virile_might_use(session, member)
        session.log.append(
            f"{member.name} takes Pills of virile might (+{virile_might_giving_roll_bonus(member) - virile_might_breeding_save_bonus(member)} "
            f"Giving, +{virile_might_breeding_save_bonus(member)} breeding saves this encounter, TCOTFD p.83)."
        )
        return True
    if "Pills of virile retention" in base:
        if item in member.inventory:
            member.inventory.remove(item)
        member.statuses.append("Apothecary: virile retention (+2 Withholding, +1 breeding, TCOTFD p.83)")
        session.log.append(f"{member.name} takes Pills of virile retention (TCOTFD p.83).")
        return True
    if item in member.inventory:
        member.inventory.remove(item)
    summary = next((recipe.get("summary", "") for recipe in load_apothecary_recipes() if recipe.get("item") == base), "")
    session.log.append(f"{member.name} uses {base}. {summary}".strip())
    return True
