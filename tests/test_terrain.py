from __future__ import annotations

from app.engine import spells
from app.schemas import EnemyState, PartyMemberState


def _druid() -> PartyMemberState:
    return PartyMemberState(
        character_id="d1",
        name="Druid",
        class_id="druid",
        class_name="Druid",
        level=3,
        xp=0,
        gold=0,
        max_life=5,
        current_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        spells=["Entangle", "Lightning Strike", "Forest Pathway"],
    )


def _foe() -> EnemyState:
    return EnemyState(id="e1", name="Orc", category="minions", life=2, max_life=2, level=2)


def test_entangle_blocked_indoors() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Entangle",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="indoor",
    )
    assert not outcome.spell_consumed
    assert any("forest" in line.lower() for line in outcome.log)


def test_entangle_works_in_forest() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Entangle",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="forest",
    )
    assert outcome.spell_consumed


def test_lightning_strike_blocked_indoors() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Lightning Strike",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="indoor",
    )
    assert not outcome.spell_consumed
    assert any("indoors" in line.lower() for line in outcome.log)


def test_lightning_strike_works_outdoors() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Lightning Strike",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="outdoor",
    )
    assert outcome.spell_consumed


def test_forest_pathway_requires_woodland() -> None:
    druid = _druid()
    blocked = spells.resolve_spell_cast(
        "Forest Pathway",
        druid,
        [druid],
        [],
        show_rolls=False,
        terrain="outdoor",
    )
    assert not blocked.spell_consumed

    allowed = spells.resolve_spell_cast(
        "Forest Pathway",
        druid,
        [druid],
        [],
        show_rolls=False,
        terrain="jungle",
    )
    assert allowed.spell_consumed
