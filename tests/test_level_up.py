from __future__ import annotations

from pathlib import Path

from app.engine.class_profiles import max_life_for_level, spell_slot_count
from app.engine.dice import AdvancementRollResult
from app.engine.experience import (
    apply_level_up,
    apply_classical_xp_roll,
    apply_old_school_level_up,
    apply_slower_advancement,
    assign_level_up_spell,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _session(*, party: list[PartyMemberState], **kwargs) -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=party,
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        **kwargs,
    )


def test_max_life_for_level_uses_class_offset() -> None:
    assert max_life_for_level("warrior", 1) == 7
    assert max_life_for_level("warrior", 2) == 8
    assert max_life_for_level("wizard", 1) == 3
    assert max_life_for_level("wizard", 3) == 5


def test_apply_old_school_level_up_spends_tally_and_uses_completion_callback() -> None:
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = _session(party=[hero], xp_system="old_school", old_school_xp_tally=300)
    completed: list[str] = []

    apply_old_school_level_up(
        session,
        hero.character_id,
        can_assign_level_up=lambda _session, _character_id: True,
        complete_level_up=lambda _session, member: completed.append(member.character_id),
        show_rolls=True,
    )

    assert completed == [hero.character_id]
    assert session.old_school_xp_tally == 0
    assert "Old School XP spent: 300 (tally 0)." in session.log


def test_apply_slower_advancement_spends_minimum_bank_and_calls_success(monkeypatch) -> None:
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = _session(party=[hero], xp_system="slower_advancement", slower_xp_bank=2)
    monkeypatch.setattr(
        "app.engine.experience.perform_advancement_roll",
        lambda *_args, **_kwargs: AdvancementRollResult(natural=6, total=6, sides=6, modifier=0),
    )
    completed: list[tuple[str, str]] = []

    apply_slower_advancement(
        session,
        hero.character_id,
        xp_spent=None,
        show_rolls=True,
        explain_math=False,
        advancement_fork="level_up",
        expert_skill_id=None,
        expert_skill_target=None,
        heroic_skill_id=None,
        legendary_skill_id=None,
        heroic_skill_target=None,
        expert_catalog=[],
        heroic_catalog=[],
        legendary_catalog=[],
        can_assign_level_up=lambda _session, _character_id: True,
        apply_success=lambda member, fork: completed.append((member.character_id, fork)),
    )

    assert session.slower_xp_bank == 0
    assert completed == [(hero.character_id, "level_up")]
    assert any("Hero" in line and "2 XP banked" in line for line in session.log)


def test_apply_classical_xp_roll_spends_pending_roll_and_calls_success(monkeypatch) -> None:
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = _session(party=[hero], xp_rolls_pending=1)
    monkeypatch.setattr(
        "app.engine.experience.perform_advancement_roll",
        lambda *_args, **_kwargs: AdvancementRollResult(natural=6, total=6, sides=6, modifier=0),
    )
    completed: list[tuple[str, str]] = []

    apply_classical_xp_roll(
        session,
        hero.character_id,
        show_rolls=True,
        explain_math=False,
        advancement_fork="level_up",
        expert_skill_id=None,
        expert_skill_target=None,
        heroic_skill_id=None,
        legendary_skill_id=None,
        heroic_skill_target=None,
        expert_catalog=[],
        heroic_catalog=[],
        legendary_catalog=[],
        can_assign_level_up=lambda _session, _character_id: True,
        apply_success=lambda member, fork: completed.append((member.character_id, fork)),
    )

    assert session.xp_rolls_pending == 0
    assert completed == [(hero.character_id, "level_up")]
    assert any("Hero" in line and "roll" in line.lower() for line in session.log)


def test_wizard_level_up_pending_spell_pick() -> None:
    wizard = PartyMemberState(
        character_id="w",
        name="Myst",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Blessing", "Escape"],
    )
    result = apply_level_up(wizard)
    assert wizard.level == 2
    assert wizard.max_life == max_life_for_level("wizard", 2)
    assert wizard.current_life == 4
    assert spell_slot_count("wizard", 2) == 4
    assert len(wizard.spells) == 2
    assert result.spell_pick_pending is True


def test_assign_level_up_spell_fills_slot() -> None:
    wizard = PartyMemberState(
        character_id="w",
        name="Myst",
        class_id="wizard",
        class_name="Wizard",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Blessing", "Escape"],
    )
    log = assign_level_up_spell(wizard, "fireball")
    assert wizard.spells == ["Blessing", "Escape", "Fireball"]
    assert any("Fireball" in line for line in log)


def test_wizard_level_up_can_prepare_duplicate_basic_spell() -> None:
    wizard = PartyMemberState(
        character_id="w",
        name="Myst",
        class_id="wizard",
        class_name="Wizard",
        level=4,
        xp=0,
        gold=0,
        current_life=6,
        max_life=6,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Fireball", "Lightning", "Sleep", "Blessing", "Escape", "Protection"],
    )
    result = apply_level_up(wizard)
    assert wizard.level == 5
    assert spell_slot_count("wizard", 5) == 7
    assert result.spell_pick_pending is True

    log = assign_level_up_spell(wizard, "fireball")
    assert wizard.spells.count("Fireball") == 2
    assert len(wizard.spells) == 7
    assert any("Fireball" in line for line in log)


def test_cleric_level_up_has_no_spell_slot() -> None:
    cleric = PartyMemberState(
        character_id="c",
        name="Faith",
        class_id="cleric",
        class_name="Cleric",
        level=1,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    result = apply_level_up(cleric)
    assert cleric.level == 2
    assert result.spell_pick_pending is False
    assert spell_slot_count("cleric", 2) is None


def test_xp_roll_with_spell_name(monkeypatch) -> None:
    eng = engine()
    wizard = PartyMemberState(
        character_id="w",
        name="Myst",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Blessing", "Escape"],
    )
    session = _session(party=[wizard], xp_rolls_pending=1)
    monkeypatch.setattr(
        "app.engine.experience.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(natural=6, total=6, sides=6, modifier=bonus),
    )
    eng.advance(session, "xp_roll", character_id="w", spell_name="Lightning")
    assert wizard.level == 2
    assert wizard.spells == ["Blessing", "Escape", "Lightning"]
    assert session.level_up_spell_pending_character_id is None


def test_pick_level_up_spell_action(monkeypatch) -> None:
    eng = engine()
    wizard = PartyMemberState(
        character_id="w",
        name="Myst",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Blessing", "Escape"],
    )
    session = _session(party=[wizard], xp_rolls_pending=1)
    monkeypatch.setattr(
        "app.engine.experience.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(natural=6, total=6, sides=6, modifier=bonus),
    )
    eng.advance(session, "xp_roll", character_id="w")
    assert session.level_up_spell_pending_character_id == "w"
    eng.advance(session, "pick_level_up_spell", character_id="w", spell_name="Sleep")
    assert wizard.spells == ["Blessing", "Escape", "Sleep"]
    assert session.level_up_spell_pending_character_id is None


def test_xp_roll_blocked_while_spell_pending(monkeypatch) -> None:
    eng = engine()
    wizard = PartyMemberState(
        character_id="w",
        name="Myst",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Blessing", "Escape"],
    )
    session = _session(party=[wizard], xp_rolls_pending=2)
    monkeypatch.setattr(
        "app.engine.experience.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(natural=6, total=6, sides=6, modifier=bonus),
    )
    eng.advance(session, "xp_roll", character_id="w")
    assert session.level_up_spell_pending_character_id == "w"
    eng.advance(session, "xp_roll", character_id="w")
    assert session.xp_rolls_pending == 1
    assert wizard.level == 2


def test_level_five_needs_expert_training_before_advancing(monkeypatch) -> None:
    eng = engine()
    warrior = PartyMemberState(
        character_id="w",
        name="Adept",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        xp=0,
        gold=0,
        current_life=8,
        max_life=11,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = _session(party=[warrior], xp_rolls_pending=1)
    monkeypatch.setattr(
        "app.engine.experience.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(
            natural=8, total=10, sides=8, modifier=2, purpose=purpose
        ),
    )
    eng.advance(session, "xp_roll", character_id="w", advancement_fork="level_up")
    assert warrior.level == 5
    assert session.xp_rolls_pending == 1
    assert any("Expert training" in line for line in session.log)


def test_pending_xp_roll_can_be_banked_to_character() -> None:
    eng = engine()
    warrior = PartyMemberState(
        character_id="w",
        name="Adept",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = _session(party=[warrior], xp_rolls_pending=1)
    eng.advance(session, "bank_xp_roll", character_id="w")
    assert session.xp_rolls_pending == 0
    assert warrior.xp == 1
    assert any("banks 1 XP roll" in line for line in session.log)


def test_character_banked_xp_roll_can_be_spent_later(monkeypatch) -> None:
    eng = engine()
    warrior = PartyMemberState(
        character_id="w",
        name="Adept",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=1,
        gold=0,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = _session(party=[warrior], xp_rolls_pending=0)
    monkeypatch.setattr(
        "app.engine.experience.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(
            natural=6, total=6, sides=6, modifier=bonus, purpose=purpose
        ),
    )
    eng.advance(session, "spend_banked_xp", character_id="w", advancement_fork="level_up")
    assert warrior.xp == 0
    assert warrior.level == 4
