"""TCOTFD class pass — playable classes and Courtship modifiers."""

from __future__ import annotations

from unittest.mock import patch

from app.engine.courtship_classes import (
    conservationist_allowed_spell,
    conservationist_spell_slot_count,
    courtship_woo_giving_bonus,
    courtship_woo_withholding_bonus,
    hidden_pathway_eligible,
    is_wandering_alchemist,
    madness_save_level_bonus,
    party_has_hidden_pathway_guide,
    satyr_auto_fails_mesmerize,
)
from app.engine.courtship_combat import _mesmerize_save
from app.engine.courtship_demesne import apply_courtship_encounter
from app.engine.class_combat import defense_modifier, save_modifier
from app.schemas import PartyMemberState
from tests.test_forsaken_depths_engine import _party_member, engine


def test_satyr_woo_and_defense_bonuses() -> None:
    satyr = _party_member()
    satyr.class_id = "satyr"
    satyr.level = 4
    assert courtship_woo_giving_bonus(satyr) == 8
    assert courtship_woo_withholding_bonus(satyr) == 8
    assert defense_modifier(satyr) == 4


def test_rogue_withholding_includes_greed_bonus() -> None:
    rogue = _party_member()
    rogue.class_id = "rogue"
    rogue.level = 5
    assert courtship_woo_giving_bonus(rogue) == 2
    assert courtship_woo_withholding_bonus(rogue) == 7


def test_wandering_alchemist_saves_as_halfling() -> None:
    alchemist = _party_member()
    alchemist.class_id = "wandering_alchemist"
    alchemist.level = 3
    assert is_wandering_alchemist(alchemist)
    assert save_modifier(alchemist, poison=True) == alchemist.level


def test_conservationist_spell_rules() -> None:
    assert conservationist_allowed_spell("Blessing")
    assert conservationist_allowed_spell("Flower Portal")
    assert not conservationist_allowed_spell("Fireball")
    assert not conservationist_allowed_spell("Sleep")
    assert conservationist_spell_slot_count(5) == 8


def test_hidden_pathway_classes() -> None:
    paladin = _party_member()
    paladin.class_id = "paladin"
    cambion = _party_member()
    cambion.class_id = "cambion"
    warrior = _party_member()
    warrior.class_id = "warrior"
    assert hidden_pathway_eligible(paladin)
    assert hidden_pathway_eligible(cambion)
    assert not hidden_pathway_eligible(warrior)
    assert party_has_hidden_pathway_guide([paladin, warrior])


def test_satyr_fails_mesmerize_vs_ladies() -> None:
    satyr = _party_member()
    satyr.class_id = "satyr"
    assert satyr_auto_fails_mesmerize("mesmerize by Matron of Summer")
    ok, log = _mesmerize_save(satyr, 4, label="mesmerize by Lady of Lament", show_rolls=False)
    assert not ok
    assert any("satyr" in line.lower() for line in log)


def test_cambion_madness_save_bonus() -> None:
    cambion = _party_member()
    cambion.class_id = "cambion"
    cambion.level = 6
    assert madness_save_level_bonus(cambion) == 6


def test_hidden_pathway_encounter_adds_riverside_for_paladin() -> None:
    eng = engine()
    session = eng.create_courtship_demesne_session("pathway", "party-1", [_party_member()])
    paladin = session.party[0]
    paladin.class_id = "paladin"
    row = {
        "key": "hidden_pathway",
        "name": "Hidden Pathway",
        "effect": "pathway",
        "pathways": ["seaside", "palace"],
    }
    apply_courtship_encounter(eng, session, row, show_rolls=False)
    assert "riverside" in (session.courtship_pending_pathways or [])


def test_wandering_alchemist_ingredient_reroll_on_harvest() -> None:
    eng = engine()
    alchemist = _party_member()
    alchemist.class_id = "wandering_alchemist"
    alchemist.level = 5
    session = eng.create_courtship_demesne_session("harvest", "party-1", [alchemist])
    row = {
        "effect": "harvest",
        "save_level": "HCL",
        "reward": "common_ingredients",
    }
    with patch("app.engine.courtship_demesne._fd_style_save", return_value=(False, [])):
        with patch("app.engine.courtship_ingredients.format_common_ingredient", side_effect=["Common ingredient", "Common ingredient (yucca)"]):
            apply_courtship_encounter(eng, session, row, show_rolls=False)
    assert any("Common ingredient (yucca)" in item for item in alchemist.inventory)
    assert any("re-rolls" in line for line in session.log)
