"""Apothecary Cookbook brewing (TCOTFD p.7-9, p.79-98)."""

from __future__ import annotations

from unittest.mock import patch

from app.engine.courtship_apothecary import virile_retention_withholding_bonus
from app.engine.courtship_apothecary_brew import (
    APOTHECARY_ITEM_TAG,
    apothecary_brew_available,
    brew_apothecary_recipe,
    list_brewable_recipe_keys,
    party_can_supply_ingredients,
    resolve_apothecary_brew_choice,
    unlock_apothecary_brew_after_encounter,
    use_apothecary_brew,
)
from app.engine.courtship_blossoms_items import KARMIC_CALCINATOR
from app.engine.courtship_demesne import roll_courtship_encounter
from tests.test_forsaken_depths_engine import _party_member, engine


def _alchemist(**overrides):
    member = _party_member(**overrides)
    member.class_id = "wandering_alchemist"
    if "Mortar and pestle" not in member.inventory:
        member.inventory.append("Mortar and pestle")
    member.gold = max(member.gold, 50)
    return member


def test_apothecary_brew_requires_wandering_alchemist() -> None:
    session = engine().create_courtship_demesne_session("brew-gate", "party-1", [_party_member()])
    assert not apothecary_brew_available(session)
    session = engine().create_courtship_demesne_session("brew-ok", "party-1", [_alchemist()])
    assert apothecary_brew_available(session)
    session.courtship_woo_active = True
    assert not apothecary_brew_available(session)


def test_brew_formula_of_humidity_consumes_ingredients() -> None:
    eng = engine()
    brewer = _alchemist()
    brewer.inventory.extend(["yeast", "yucca"])
    session = eng.create_courtship_demesne_session("brew-success", "party-1", [brewer])
    gold_before = brewer.gold
    assert brew_apothecary_recipe(eng, session, "formula_of_humidity", show_rolls=False)
    brewed = next(item for item in brewer.inventory if APOTHECARY_ITEM_TAG in item)
    assert "Formula of humidity" in brewed
    assert "yeast" not in brewer.inventory
    assert "yucca" not in brewer.inventory
    assert brewer.gold == gold_before - 10


def test_brew_failure_locks_until_next_encounter() -> None:
    eng = engine()
    brewer = _alchemist()
    brewer.inventory.extend(["ginseng", "adonis vernalis", "oyster oil"])
    session = eng.create_courtship_demesne_session("brew-fail", "party-1", [brewer])
    with patch("app.engine.courtship_apothecary_brew._brew_roll", return_value=(False, 1, 2)):
        assert brew_apothecary_recipe(eng, session, "pills_of_virile_retention", show_rolls=False)
    assert session.courtship_apothecary_brew_locked
    assert not apothecary_brew_available(session)
    unlock_apothecary_brew_after_encounter(session)
    assert apothecary_brew_available(session)


def test_resolve_brew_choice_opens_recipe_picker() -> None:
    eng = engine()
    session = eng.create_courtship_demesne_session("brew-pick", "party-1", [_alchemist()])
    assert not resolve_apothecary_brew_choice(eng, session, None, show_rolls=False)
    assert session.courtship_pending_choice == "apothecary_brew"


def test_use_virile_retention_grants_withholding_bonus() -> None:
    member = _party_member()
    session = engine().create_courtship_demesne_session("retention", "party-1", [member])
    item = f"Pills of virile retention {APOTHECARY_ITEM_TAG}, 1 encounter)"
    member.inventory.append(item)
    assert use_apothecary_brew(session, member, item, show_rolls=False)
    assert virile_retention_withholding_bonus(member) == 2


def test_karmic_calcinator_doubles_brew_duration() -> None:
    eng = engine()
    brewer = _alchemist()
    brewer.inventory.extend(["ginseng", "adonis vernalis", "oyster oil", KARMIC_CALCINATOR])
    session = eng.create_courtship_demesne_session("calcinator", "party-1", [brewer])
    with patch("app.engine.courtship_apothecary_brew.roll_d6", return_value=6):
        assert brew_apothecary_recipe(eng, session, "pills_of_virile_retention", show_rolls=False)
    brewed = next(item for item in brewer.inventory if APOTHECARY_ITEM_TAG in item)
    assert "2 encounters" in brewed


def test_party_can_supply_ingredients_with_generic_common() -> None:
    brewer = _alchemist()
    brewer.inventory.extend(["Common ingredient", "Common ingredient"])
    recipe = {
        "ingredients": [
            {"tier": "common", "name": "yeast", "count": 1},
            {"tier": "common", "name": "yucca", "count": 1},
        ]
    }
    assert not party_can_supply_ingredients([brewer], recipe)
    brewer.inventory = ["Mortar and pestle", "yeast", "yucca"]
    assert party_can_supply_ingredients([brewer], recipe)
    assert "formula_of_humidity" in list_brewable_recipe_keys(
        engine().create_courtship_demesne_session("keys", "party-1", [brewer])
    )


def test_roll_encounter_unlocks_brew_lock() -> None:
    eng = engine()
    session = eng.create_courtship_demesne_session("unlock", "party-1", [_alchemist()])
    session.courtship_apothecary_brew_locked = True
    with patch("app.engine.courtship_demesne.roll_2d6", return_value=7):
        with patch("app.engine.courtship_demesne.apply_courtship_encounter"):
            roll_courtship_encounter(eng, session, show_rolls=False)
    assert not session.courtship_apothecary_brew_locked
