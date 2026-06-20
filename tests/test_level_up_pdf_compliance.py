"""EE p.117–118 Experience / level-up PDF row audit and tier-dice behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.engine.dice import explode_threshold, roll_exploding_for_level, tier_die_sides_for_member
from app.engine.experience import (
    MINOR_ENCOUNTERS_FOR_XP,
    apply_level_up,
    old_school_level_cost,
    old_school_xp_for_defeated,
    perform_advancement_roll,
)
from app.engine.tier_advancement import TierTraining, advancement_roll_spec, level_up_gate_reason
from app.schemas import EnemyState, PartyMemberState

ROOT = Path(__file__).resolve().parents[1]


def _rows(key: str) -> list[dict]:
    import json

    tables = json.loads((ROOT / "data" / "rules" / "dungeon_tables.json").read_text(encoding="utf-8"))
    return tables[key]


def _hero(level: int = 5, **flags) -> PartyMemberState:
    return PartyMemberState(
        character_id="h1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=level,
        xp=0,
        gold=0,
        current_life=level + 2,
        max_life=level + 2,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        **flags,
    )


def test_ee_p117_classical_xp_table_rows_match_pdf() -> None:
    rows = {row["roll"]: row for row in _rows("experience_classical_table")}
    assert set(rows) == {"minor", "secret", "major", "final_boss", "advance"}
    assert rows["minor"]["source_page"] == 117
    assert "10" in rows["minor"]["result"] and "minor" in rows["minor"]["result"].lower()
    assert "3 Clues" in rows["secret"]["result"]
    assert "Major Foe" in rows["major"]["result"]
    assert "Final Boss" in rows["final_boss"]["result"]
    assert "d6 > Level" in rows["advance"]["result"] or "d6 > hero Level" in rows["advance"]["result"]
    assert "d8+2" in rows["advance"]["result"]
    assert "Expert tier entry" in rows["advance"]["result"]


def test_ee_p117_slow_and_sure_row_matches_pdf() -> None:
    rows = _rows("experience_slow_sure_table")
    assert len(rows) == 1
    assert rows[0]["source_page"] == 117
    assert "end of a successful adventure" in rows[0]["result"].lower() or "end of any successful" in rows[0]["result"].lower()


def test_ee_p118_old_school_rows_match_pdf() -> None:
    rows = {row["roll"]: row for row in _rows("experience_old_school_table")}
    assert rows["minor"]["source_page"] == 118
    assert "Vermin" in rows["minor"]["result"] or "vermin" in rows["minor"]["result"].lower()
    assert "L×10" in rows["major"]["result"] or "L x10" in rows["major"]["result"].replace(" ", "")
    assert "gp" in rows["treasure"]["result"].lower()
    assert "(Tier+2)" in rows["advance"]["result"]


def test_ee_p118_slower_advancement_rows_match_pdf() -> None:
    rows = {row["roll"]: row for row in _rows("experience_slower_table")}
    assert rows["earn"]["source_page"] == 118
    assert rows["advance"]["source_page"] == 118
    assert "Classical" in rows["earn"]["result"]
    assert "target level" in rows["advance"]["result"].lower()


def test_level_up_adds_life_and_class_benefits_immediately() -> None:
    wizard = PartyMemberState(
        character_id="w",
        name="Mira",
        class_id="wizard",
        class_name="Wizard",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Fireball", "Sleep"],
    )
    result = apply_level_up(wizard)
    assert wizard.level == 4
    assert wizard.max_life == 6
    assert wizard.current_life == 5
    assert result.spell_pick_pending
    assert any("spell slot" in line.lower() for line in result.log)
    assert any("immediately" in line.lower() for line in result.log)


def test_expert_advancement_uses_d8_plus_two() -> None:
    member = _hero(6, expert_trained=True)
    sides, modifier = advancement_roll_spec(member.level, TierTraining(expert_trained=True), "level_up")
    assert sides == 8
    assert modifier == 2
    result = perform_advancement_roll(member)
    assert result.sides == 8
    assert result.modifier == 2


def test_untrained_l5_still_uses_basic_advancement_die() -> None:
    member = _hero(5, expert_trained=False)
    result = perform_advancement_roll(member)
    assert result.sides == 6
    assert result.modifier == 0


def test_action_die_uses_member_training_when_pc_passed() -> None:
    """Training tier gates action dice; L5 without Expert training stays on d6."""
    untrained = _hero(5, expert_trained=False)
    trained = _hero(5, expert_trained=True)
    with patch("app.engine.dice.roll_die", return_value=4):
        _, untrained_rolls = roll_exploding_for_level(untrained)
    with patch("app.engine.dice.roll_die", return_value=6):
        _, trained_rolls = roll_exploding_for_level(trained)
    assert all(1 <= value <= 6 for value in untrained_rolls)
    assert trained_rolls == [6]


def test_expert_trained_l5_uses_d8_action_die_not_level_band_alone() -> None:
    untrained = _hero(5, expert_trained=False)
    trained = _hero(5, expert_trained=True)
    assert tier_die_sides_for_member(untrained) == 6
    assert tier_die_sides_for_member(trained) == 8
    assert explode_threshold(8) == 7
    assert level_up_gate_reason(_hero(5), 6) is not None
    assert level_up_gate_reason(_hero(5, expert_trained=True), 6) is None


def test_old_school_cost_formula_tier_plus_two_times_100() -> None:
    assert old_school_level_cost(5) == 400
    assert old_school_level_cost(9) == 500


def test_old_school_major_foe_xp_formula() -> None:
    boss = EnemyState(id="b1", name="Boss", category="boss", level=6, life=0, max_life=8)
    assert old_school_xp_for_defeated([boss]) == 100


def test_minor_encounter_threshold_matches_pdf() -> None:
    assert MINOR_ENCOUNTERS_FOR_XP == 10
