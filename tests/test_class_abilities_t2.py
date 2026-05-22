from __future__ import annotations

from app.engine.class_abilities import (
    acrobat_distract,
    acrobat_shift_position,
    acrobat_tricks_remaining,
    gnome_smokescreen,
    mushroom_spore_cloud,
    recover_acrobat_tricks_on_rest,
    spend_acrobat_trick,
)
from app.engine.experience import tier_for_level
from app.schemas import EnemyState, PartyMemberState, SessionState


def _session(**overrides) -> SessionState:
    base = {
        "id": "s",
        "party_id": "p",
        "adventure_id": "random",
        "adventure_type": "random",
        "mode": "exploration",
        "party": [],
        "map_state": {"width": 10, "height": 10, "tiles": [], "current_tile_id": "t"},
        "log": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return SessionState.model_validate(base)


def _acrobat(level: int = 5) -> PartyMemberState:
    return PartyMemberState(
        character_id="acro",
        name="Flip",
        class_id="acrobat",
        class_name="Acrobat",
        level=level,
        xp=0,
        gold=0,
        current_life=8,
        max_life=8,
        attack_bonus=0,
        defense_bonus=2,
        save_bonus=0,
        marching_order=1,
    )


def _ally() -> PartyMemberState:
    return PartyMemberState(
        character_id="ally",
        name="Buddy",
        class_id="warrior",
        class_name="Warrior",
        level=2,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=2,
    )


def test_acrobat_shift_swaps_marching_order() -> None:
    session = _session()
    acro = _acrobat()
    ally = _ally()
    session.party = [acro, ally]
    assert acrobat_tricks_remaining(session, acro) == 8
    log = acrobat_shift_position(session, acro, ally)
    assert acro.marching_order == 2
    assert ally.marching_order == 1
    assert acrobat_tricks_remaining(session, acro) == 7
    assert any("swap" in line.lower() for line in log)


def test_acrobat_distract_reduces_foe_level() -> None:
    session = _session(mode="combat")
    acro = _acrobat(5)
    foe = EnemyState(id="f1", name="Orc", category="minions", level=5, life=3, max_life=3)
    log = acrobat_distract(session, acro, foe)
    assert session.foe_level_penalties["f1"] == tier_for_level(5)
    assert any("Distract" in line for line in log)


def test_acrobat_rest_recovers_tier_tricks() -> None:
    session = _session()
    acro = _acrobat(5)
    session.party = [acro]
    for _ in range(3):
        spend_acrobat_trick(session, acro)
    note = recover_acrobat_tricks_on_rest(session, acro)
    assert note
    assert acrobat_tricks_remaining(session, acro) == 7


def test_gnome_smokescreen_enables_clean_flee() -> None:
    session = _session()
    gnome = PartyMemberState(
        character_id="g",
        name="Giz",
        class_id="gnome",
        class_name="Gnome",
        level=3,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    log = gnome_smokescreen(session, gnome)
    assert session.skip_parting_flee
    assert any("smokescreen" in line.lower() for line in log)


def test_mushroom_spore_cloud_debuffs_minors() -> None:
    session = _session()
    monk = PartyMemberState(
        character_id="m",
        name="Spore",
        class_id="mushroom_monk",
        class_name="Mushroom Monk",
        level=4,
        xp=0,
        gold=0,
        current_life=6,
        max_life=6,
        attack_bonus=0,
        defense_bonus=1,
        save_bonus=0,
    )
    foes = [
        EnemyState(id="v", name="Rat", category="vermin", level=2, life=1, max_life=1),
        EnemyState(id="b", name="Boss", category="boss", level=6, life=6, max_life=6),
    ]
    log = mushroom_spore_cloud(session, monk, foes)
    assert session.foe_level_penalties.get("v") == 1
    assert "b" not in session.foe_level_penalties
    assert any("spores" in line.lower() for line in log)
