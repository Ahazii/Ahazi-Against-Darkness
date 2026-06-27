"""TCOTFD class pass — playable classes and Courtship modifiers."""

from __future__ import annotations

from unittest.mock import patch

from app.engine.courtship_classes import (
    can_spend_luck_on_woo,
    conservationist_allowed_spell,
    conservationist_forbidden_spell_attempt,
    conservationist_spell_slot_count,
    courtship_woo_giving_bonus,
    courtship_woo_withholding_bonus,
    flower_portal_casts_remaining,
    hidden_pathway_eligible,
    is_wandering_alchemist,
    madness_save_level_bonus,
    note_flower_portal_cast,
    party_has_hidden_pathway_guide,
    satyr_auto_fails_mesmerize,
)
from app.engine.courtship_book_of_secrets import apply_curse_of_tamas_zeya, book_entry
from app.engine.class_abilities import resolve_social_save
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


def test_bos_entry_16_catalogued() -> None:
    row = book_entry(16)
    assert row is not None
    assert row["effect"] == "curse_tamas_zeya"


def test_bos_lex_and_pandora_entries_catalogued() -> None:
    for entry in (2, 4, 5, 6, 7):
        row = book_entry(entry)
        assert row is not None, f"BoS entry {entry} missing"
        assert row.get("effect")


def test_curse_of_tamas_zeya_removes_character_and_gear() -> None:
    eng = engine()
    victim = _party_member()
    victim.inventory.append("Spellbook")
    victim.gold = 50
    warrior = _party_member()
    warrior.character_id = "warrior-2"
    session = eng.create_courtship_demesne_session("curse", "party-1", [victim, warrior])
    apply_curse_of_tamas_zeya(session, victim, show_rolls=False)
    assert victim.character_id not in {member.character_id for member in session.party}
    assert victim.character_id in session.permanently_lost_character_ids
    assert not victim.inventory
    assert victim.gold == 0


def test_conservationist_forbidden_spell_triggers_curse() -> None:
    eng = engine()
    conservationist = _party_member()
    conservationist.class_id = "conservationist"
    session = eng.create_session("curse-spell", "party-1", [conservationist])
    allowed, _ = conservationist_forbidden_spell_attempt(
        session, conservationist, "Fireball", engine=eng, show_rolls=False
    )
    assert not allowed
    assert conservationist.character_id not in {member.character_id for member in session.party}


def test_wandering_alchemist_innate_flower_portal_once_per_adventure() -> None:
    alchemist = _party_member()
    alchemist.class_id = "wandering_alchemist"
    alchemist.level = 5
    eng = engine()
    session = eng.create_session("fp-limit", "party-1", [alchemist])
    assert flower_portal_casts_remaining(session, alchemist) == 1
    note_flower_portal_cast(session, alchemist, from_scroll=False)
    assert flower_portal_casts_remaining(session, alchemist) == 0
    note_flower_portal_cast(session, alchemist, from_scroll=True)
    assert flower_portal_casts_remaining(session, alchemist) == 0


def test_halfling_luck_on_woo_reroll(monkeypatch) -> None:
    halfling = _party_member()
    halfling.class_id = "halfling"
    halfling.level = 3
    session = engine().create_session("woo-luck", "party-1", [halfling])
    rolls = iter([(2, [2]), (6, [6])])
    monkeypatch.setattr("app.engine.class_abilities.roll_exploding_for_level", lambda _m: next(rolls))
    ok, log = resolve_social_save(
        session,
        halfling,
        5,
        show_rolls=False,
        label="Giving roll",
        use_luck=True,
    )
    assert ok
    assert can_spend_luck_on_woo(halfling)
    assert session.luck_points_spent.get(halfling.character_id) == 1
    assert any("Luck reroll" in line for line in log)
