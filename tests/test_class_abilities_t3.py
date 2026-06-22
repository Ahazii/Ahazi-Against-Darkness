from __future__ import annotations

from app.engine.class_abilities import (
    acrobat_evade,
    attempt_gnome_gadget_door,
    attempt_gnome_trap_disarm,
)
from app.schemas import PartyMemberState, SessionState


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


def _gnome() -> PartyMemberState:
    return PartyMemberState(
        character_id="g",
        name="Giz",
        class_id="gnome",
        class_name="Gnome",
        level=3,
        xp=0,
        gold=0,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )


def _acrobat() -> PartyMemberState:
    return PartyMemberState(
        character_id="a",
        name="Flip",
        class_id="acrobat",
        class_name="Acrobat",
        level=4,
        xp=0,
        gold=0,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=2,
        save_bonus=0,
    )


def test_acrobat_evade_marks_evasion(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.class_abilities.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    session = _session(mode="combat")
    acro = _acrobat()
    log = acrobat_evade(session, acro)
    assert acro.character_id in session.evasion_character_ids
    assert any("Evade" in line for line in log)


def test_gnome_gadget_door_spends_points(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.class_abilities.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    session = _session()
    gnome = _gnome()
    ok, log = attempt_gnome_gadget_door(session, gnome, 4, gadget_points=2, show_rolls=False)
    assert ok
    assert session.gnome_gadgets_spent[gnome.character_id] == 2
    assert any("opens the lock" in line for line in log)


def test_gnome_trap_disarm_with_bonus(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.class_abilities.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
    session = _session()
    gnome = _gnome()
    ok, log = attempt_gnome_trap_disarm(session, gnome, 5, gadget_points=1, show_rolls=False)
    assert ok
    assert any("disarms" in line.lower() for line in log)
