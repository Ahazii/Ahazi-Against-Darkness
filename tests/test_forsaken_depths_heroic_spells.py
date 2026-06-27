from __future__ import annotations

from app.engine.forsaken_depths_heroic_spells import (
    clear_eldritch_fist_on_cast,
    fd_boatman_luck_melee_bonus,
    fd_eldritch_fist_melee_bonus,
    heroic_spell_name_for_roll,
    try_resolve_fd_heroic_spell,
)
from app.engine.spells import normalize_spell_name
from app.schemas import EnemyState, PartyMemberState, SessionState


def _caster(**overrides) -> PartyMemberState:
    payload = {
        "character_id": "wiz-1",
        "name": "Caster",
        "class_id": "wizard",
        "class_name": "Wizard",
        "level": 12,
        "max_life": 14,
        "current_life": 14,
        "gold": 0,
        "xp": 0,
        "inventory": [],
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "spells": ["Fire of Truth"],
        "marching_order": 1,
    }
    payload.update(overrides)
    return PartyMemberState.model_validate(payload)


def _foe(**overrides) -> EnemyState:
    payload = {
        "id": "foe-1",
        "name": "Chaos Troll",
        "level": 5,
        "life": 8,
        "max_life": 8,
        "category": "weird",
        "tags": ["chaos"],
    }
    payload.update(overrides)
    return EnemyState.model_validate(payload)


def test_heroic_spell_table_rolls_match_pdf() -> None:
    assert heroic_spell_name_for_roll(1) == "Boatman's Luck"
    assert heroic_spell_name_for_roll(4) == "Fire of Truth"
    assert heroic_spell_name_for_roll(6) == "Mass Invisibility"


def test_boatmans_luck_requires_river_boat() -> None:
    caster = _caster(spells=["Boatman's Luck"])
    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [caster],
            "map_state": {"width": 1, "height": 1, "tiles": [], "current_tile_id": "t0"},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "tile_catalog": "forsaken_depths",
            "fd_travel_mode": "foot",
        }
    )
    log: list[str] = []
    outcome = try_resolve_fd_heroic_spell(
        "boatmans_luck",
        "Boatman's Luck",
        caster,
        [caster],
        [],
        log,
        session=session,
    )
    assert outcome is not None
    assert outcome.spell_consumed is False
    assert session.fd_boatman_luck_active is False


def test_boatmans_luck_sets_flags_on_river_boat() -> None:
    caster = _caster(spells=["Boatman's Luck"], level=12)
    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [caster],
            "map_state": {"width": 1, "height": 1, "tiles": [], "current_tile_id": "t0"},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "tile_catalog": "forsaken_depths_rivers",
            "fd_travel_mode": "boat",
            "fd_boat_status": "ok",
        }
    )
    log: list[str] = []
    outcome = try_resolve_fd_heroic_spell(
        "boatmans_luck",
        "Boatman's Luck",
        caster,
        [caster],
        [],
        log,
        session=session,
    )
    assert outcome is not None
    assert outcome.spell_consumed is True
    assert session.fd_boatman_luck_active is True
    assert session.fd_boat_fireproof is True
    assert session.fd_boatman_luck_combat_tier == 3


def test_fire_of_truth_rejects_unliving(monkeypatch) -> None:
    caster = _caster(spells=["Fire of Truth"])
    foe = _foe(name="Skeleton", category="undead", tags=["undead"])
    log: list[str] = []
    outcome = try_resolve_fd_heroic_spell(
        "fire_of_truth",
        "Fire of Truth",
        caster,
        [caster],
        [foe],
        log,
        target_foe_id="foe-1",
    )
    assert outcome is not None
    assert outcome.spell_consumed is True
    assert foe.life == 8


def test_teleport_enemy_removes_foe_on_hit(monkeypatch) -> None:
    caster = _caster(spells=["Teleport Enemy"])
    foe = _foe(tags=[])
    monkeypatch.setattr(
        "app.engine.forsaken_depths_heroic_spells.spell_hits",
        lambda *args, **kwargs: (True, ["hit"], 10, []),
    )
    monkeypatch.setattr("app.engine.forsaken_depths_heroic_spells.roll_d6", lambda: 4)
    log: list[str] = []
    outcome = try_resolve_fd_heroic_spell(
        "teleport_enemy",
        "Teleport Enemy",
        caster,
        [caster],
        [foe],
        log,
        target_foe_id="foe-1",
        show_rolls=False,
    )
    assert outcome is not None
    assert outcome.spell_consumed is True
    assert foe.life == 0
    assert "fd_teleported_away" in foe.tags


def test_eldritch_fist_hold_and_clear() -> None:
    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [],
            "map_state": {"width": 1, "height": 1, "tiles": [], "current_tile_id": "t0"},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "fd_eldritch_fist_held_foe_id": "foe-1",
            "fd_eldritch_fist_tier": 3,
        }
    )
    assert fd_eldritch_fist_melee_bonus(session, "foe-1") == 3
    assert fd_eldritch_fist_melee_bonus(session, "foe-2") == 0
    logs = clear_eldritch_fist_on_cast(session, "wiz-1")
    assert logs
    assert session.fd_eldritch_fist_held_foe_id is None


def test_boatman_luck_combat_bonus_consumed_on_river() -> None:
    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [],
            "map_state": {"width": 1, "height": 1, "tiles": [], "current_tile_id": "t0"},
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "tile_catalog": "forsaken_depths_rivers",
            "fd_boatman_luck_combat_tier": 5,
        }
    )
    bonus, _ = fd_boatman_luck_melee_bonus(session)
    assert bonus == 5
    assert session.fd_boatman_luck_combat_tier == 0
    assert fd_boatman_luck_melee_bonus(session)[0] == 0


def test_mass_blessing_blocks_elf_learning() -> None:
    elf = _caster(class_id="elf", class_name="Elf", spells=["Mass Blessing"])
    cleric = _caster(character_id="clr-1", class_id="cleric", class_name="Cleric")
    log: list[str] = []
    outcome = try_resolve_fd_heroic_spell(
        normalize_spell_name("Mass Blessing"),
        "Mass Blessing",
        elf,
        [elf, cleric],
        [],
        log,
    )
    assert outcome is not None
    assert outcome.spell_consumed is False
