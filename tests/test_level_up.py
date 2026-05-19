from __future__ import annotations

from pathlib import Path

from app.engine.class_profiles import max_life_for_level, spell_slot_count
from app.engine.experience import apply_level_up, assign_level_up_spell
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
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
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
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
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
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
    eng.advance(session, "xp_roll", character_id="w")
    assert session.level_up_spell_pending_character_id == "w"
    eng.advance(session, "xp_roll", character_id="w")
    assert session.xp_rolls_pending == 1
    assert wizard.level == 2
