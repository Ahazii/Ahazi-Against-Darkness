from __future__ import annotations

from app.engine.forsaken_depths_heroic_spells import (
    clear_eldritch_fist_on_cast,
    fd_boatman_luck_melee_bonus,
    fd_eldritch_fist_melee_bonus,
    heroic_spell_name_for_roll,
    try_resolve_fd_heroic_spell,
)
from app.engine.combat_modifiers import spellcasting_modifier
from app.engine.fd_teleport_enemy import tick_teleport_enemy_returns
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


def test_fire_of_truth_chaos_bonus_applies_to_hit_roll(monkeypatch) -> None:
    caster = _caster(spells=["Fire of Truth"])
    foe = _foe(name="Chaos Cultist", tags=["chaos"], life=2, max_life=2, level=8)
    captured: dict[str, int | str] = {}

    def fake_resolve_spell_effect(*args, **kwargs):
        captured["label"] = kwargs["label"]
        captured["modifier"] = kwargs["modifier_override"]
        return False, ["miss"], 0, []

    monkeypatch.setattr("app.engine.spells.resolve_spell_effect", fake_resolve_spell_effect)
    log: list[str] = []
    outcome = try_resolve_fd_heroic_spell(
        "fire_of_truth",
        "Fire of Truth",
        caster,
        [caster],
        [foe],
        log,
        target_foe_id="foe-1",
        show_rolls=False,
    )

    assert outcome is not None
    assert captured["label"] == "Fire of Truth"
    assert captured["modifier"] == spellcasting_modifier(caster) + 1
    assert "Fire of Truth gains +1 vs chaos creature Chaos Cultist (FD p.19)." in log
    assert "Fire of Truth misses" in log[-1]


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


def test_teleport_enemy_tracks_room_by_room_return(monkeypatch) -> None:
    caster = _caster(spells=["Teleport Enemy"])
    foe = _foe(tags=[], life=3, max_life=3)
    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [caster.model_dump(mode="json")],
            "map_state": {
                "width": 4,
                "height": 1,
                "current_tile_id": "t0",
                "tiles": [
                    {
                        "id": "t0",
                        "x": 0,
                        "y": 0,
                        "tile_key": "room",
                        "tile_type": "room",
                        "title": "Origin",
                        "description": "",
                        "exits": [
                            {
                                "id": "e0",
                                "direction": "east",
                                "kind": "passage",
                                "status": "open",
                                "door_open": True,
                                "destination_tile_id": "t1",
                            }
                        ],
                    },
                    {
                        "id": "t1",
                        "x": 1,
                        "y": 0,
                        "tile_key": "room",
                        "tile_type": "room",
                        "title": "Visited One",
                        "description": "",
                        "exits": [
                            {
                                "id": "e1",
                                "direction": "west",
                                "kind": "passage",
                                "status": "open",
                                "door_open": True,
                                "destination_tile_id": "t0",
                            }
                        ],
                    },
                ],
            },
            "visited_tile_ids": ["t0", "t1"],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )
    monkeypatch.setattr(
        "app.engine.forsaken_depths_heroic_spells.spell_hits",
        lambda *args, **kwargs: (True, ["hit"], 10, []),
    )
    monkeypatch.setattr("app.engine.forsaken_depths_heroic_spells.roll_d6", lambda: 1)
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
        session=session,
    )
    assert outcome is not None
    assert foe.life == 0
    assert len(session.fd_teleport_enemy_returns) == 1
    assert session.fd_teleport_enemy_returns[0].turns_remaining == 1

    tick_teleport_enemy_returns(session, reason="test turn")
    origin = next(tile for tile in session.map_state.tiles if tile.id == "t0")
    assert not session.fd_teleport_enemy_returns
    assert any(enemy.id == "foe-1" and enemy.life == 3 for enemy in origin.enemies)


def test_teleport_enemy_rolls_reaction_when_crossing_occupied_room(monkeypatch) -> None:
    foe = _foe(id="teleported", tags=[], life=3, max_life=3)
    occupant = _foe(id="guard", name="Goblin Guard", category="minions", life=1, max_life=1, level=3)
    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [_caster().model_dump(mode="json")],
            "map_state": {
                "width": 3,
                "height": 1,
                "current_tile_id": "t0",
                "tiles": [
                    {
                        "id": "t0",
                        "x": 0,
                        "y": 0,
                        "tile_key": "room",
                        "tile_type": "room",
                        "title": "Origin",
                        "description": "",
                        "exits": [
                            {
                                "id": "e0",
                                "direction": "east",
                                "kind": "passage",
                                "status": "open",
                                "door_open": True,
                                "destination_tile_id": "t1",
                            }
                        ],
                    },
                    {
                        "id": "t1",
                        "x": 1,
                        "y": 0,
                        "tile_key": "room",
                        "tile_type": "room",
                        "title": "Guard Room",
                        "description": "",
                        "enemies": [occupant.model_dump(mode="json")],
                        "exits": [
                            {
                                "id": "e1w",
                                "direction": "west",
                                "kind": "passage",
                                "status": "open",
                                "door_open": True,
                                "destination_tile_id": "t0",
                            },
                            {
                                "id": "e1e",
                                "direction": "east",
                                "kind": "passage",
                                "status": "open",
                                "door_open": True,
                                "destination_tile_id": "t2",
                            },
                        ],
                    },
                    {
                        "id": "t2",
                        "x": 2,
                        "y": 0,
                        "tile_key": "room",
                        "tile_type": "room",
                        "title": "Far Room",
                        "description": "",
                        "exits": [
                            {
                                "id": "e2",
                                "direction": "west",
                                "kind": "passage",
                                "status": "open",
                                "door_open": True,
                                "destination_tile_id": "t1",
                            }
                        ],
                    },
                ],
            },
            "visited_tile_ids": ["t0", "t1", "t2"],
            "fd_teleport_enemy_returns": [
                {
                    "enemy": foe.model_dump(mode="json"),
                    "origin_tile_id": "t0",
                    "current_tile_id": "t2",
                    "route_tile_ids": ["t2", "t1", "t0"],
                    "turns_remaining": 2,
                }
            ],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )

    monkeypatch.setattr("app.engine.fd_teleport_enemy.roll_d6", lambda: 5)

    tick_teleport_enemy_returns(
        session,
        reason="test turn",
        roll_reaction=lambda _table, _roll: {
            "key": "fight",
            "result": "The minions attack!",
            "foes_first": True,
        },
    )

    assert session.fd_teleport_enemy_returns[0].current_tile_id == "t1"
    assert any("occupied-room reaction" in line for line in session.log)
    assert any("The minions attack!" in line for line in session.log)
    assert any("resolve that monster clash" in line for line in session.log)


def test_mass_blessing_removes_selected_hireling_status() -> None:
    caster = _caster(
        class_id="cleric",
        class_name="Cleric",
        spells=["Mass Blessing"],
        current_life=14,
    )
    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "party": [caster.model_dump(mode="json")],
            "map_state": {"width": 1, "height": 1, "tiles": [], "current_tile_id": "t0"},
            "hirelings": [
                {
                    "id": "h1",
                    "retainer_type": "bodyguard",
                    "name": "Dora Shield",
                    "life": 2,
                    "max_life": 2,
                    "marching_order": 5,
                    "statuses": ["Cursed", "Lantern lit"],
                }
            ],
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )
    log: list[str] = []
    outcome = try_resolve_fd_heroic_spell(
        "mass_blessing",
        "Mass Blessing",
        caster,
        [caster],
        [],
        log,
        session=session,
        mass_blessing_target_ids=["hero:wiz-1", "hireling:h1"],
        mass_blessing_condition_choices={"hireling:h1": ["status:Cursed"]},
    )
    assert outcome is not None
    assert outcome.spell_consumed is True
    assert caster.current_life == 12
    assert session.hirelings[0].statuses == ["Lantern lit"]


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
