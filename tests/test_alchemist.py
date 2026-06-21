from __future__ import annotations

from unittest.mock import patch

from app.engine.alchemist_potions import (
    STATUS_GARLIC,
    STATUS_VIGOR,
    commission_alchemist,
    resolve_alchemist_on_dungeon_exit,
)
from app.schemas import AlchemistOrderState, MapState, PartyMemberState, SessionState, TileState


def _member(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="h1",
        name="Hero",
        class_id="wizard",
        class_name="Wizard",
        level=5,
        xp=0,
        gold=500,
        bank_gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        expert_trained=True,
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def _session(**kwargs) -> SessionState:
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
    )
    defaults = dict(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        party=[_member()],
        map_state=MapState(tiles=[tile], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        camped_outside=True,
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def test_commission_healing_potion_sets_order() -> None:
    session = _session()
    log = commission_alchemist(session, potion_id="potion_of_healing", character_id="h1")
    assert session.alchemist_order is not None
    assert session.alchemist_order.potion_id == "potion_of_healing"
    assert session.professional_services_used == 1
    assert session.party[0].gold == 500 - 60
    assert any("begins brewing" in line for line in log)


def test_blocks_second_alchemist_order() -> None:
    session = _session(
        alchemist_order=AlchemistOrderState(
            potion_id="potion_of_healing",
            potion_name="Potion of Healing",
            character_id="h1",
            difficulty=0,
            material_gp=10,
        )
    )
    log = commission_alchemist(session, potion_id="garlic_poultice", character_id="h1")
    assert any("already preparing" in line.lower() for line in log)


def test_resolve_automatic_potion_on_exit() -> None:
    session = _session()
    session.alchemist_order = AlchemistOrderState(
        potion_id="potion_of_healing",
        potion_name="Potion of Healing",
        character_id="h1",
        difficulty=0,
        material_gp=10,
    )
    log = resolve_alchemist_on_dungeon_exit(session, show_rolls=False)
    assert session.alchemist_order is None
    assert "Potion of Healing" in session.party[0].inventory
    assert any("receives" in line.lower() for line in log)


def test_resolve_failed_difficult_brew() -> None:
    session = _session()
    session.alchemist_order = AlchemistOrderState(
        potion_id="elfblood_ointment",
        potion_name="Elfblood Ointment",
        character_id="h1",
        difficulty=3,
        material_gp=35,
    )
    with patch("app.engine.alchemist_potions.roll_d6", return_value=2):
        log = resolve_alchemist_on_dungeon_exit(session, show_rolls=False)
    assert session.alchemist_order is None
    assert not any(STATUS_VIGOR in status for status in session.party[0].statuses)
    assert any("fails" in line.lower() for line in log)


def test_resolve_success_applies_status_buff() -> None:
    session = _session()
    session.alchemist_order = AlchemistOrderState(
        potion_id="garlic_poultice",
        potion_name="Garlic Poultice",
        character_id="h1",
        difficulty=0,
        material_gp=1,
    )
    resolve_alchemist_on_dungeon_exit(session, show_rolls=False)
    assert STATUS_GARLIC in session.party[0].statuses
