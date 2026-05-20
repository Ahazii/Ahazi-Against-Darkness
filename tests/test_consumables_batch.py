from __future__ import annotations

from pathlib import Path

from app.engine import spells
from app.engine.class_combat import attack_modifier, in_bear_form
from app.engine.consumables import throw_holy_water
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _session(**kwargs) -> SessionState:
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
    )
    defaults = dict(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_party_member()],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def _party_member(**overrides) -> PartyMemberState:
    base = {
        "character_id": "h1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 2,
        "xp": 0,
        "gold": 0,
        "max_life": 5,
        "current_life": 5,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
        "inventory": [],
        "spells": [],
        "statuses": [],
    }
    base.update(overrides)
    return PartyMemberState.model_validate(base)


def _skeleton() -> EnemyState:
    return EnemyState(
        id="s1",
        name="Skeleton",
        category="minions",
        level=3,
        life=1,
        max_life=1,
        tags=["undead"],
    )


def test_bear_form_uses_warrior_attack_modifier() -> None:
    druid = _party_member(class_id="druid", class_name="Druid", level=3, statuses=["Bear Form"])
    assert in_bear_form(druid)
    assert attack_modifier(druid, _skeleton()) == 3
    assert attack_modifier(_party_member(class_id="druid", class_name="Druid", level=3)) == 1


def test_bear_form_spell_sets_eight_life() -> None:
    druid = _party_member(class_id="druid", class_name="Druid", level=2, current_life=3, spells=["Bear Form"])
    outcome = spells.resolve_spell_cast("Bear Form", druid, [druid], [], show_rolls=False)
    assert outcome.bear_form
    assert outcome.bear_form_pre_life == 3
    assert druid.current_life == 8


def test_holy_water_hits_and_destroy_skeleton(monkeypatch) -> None:
    cleric = _party_member(class_id="cleric", class_name="Cleric", level=2, inventory=["Holy water vial"])
    skeleton = _skeleton()
    monkeypatch.setattr("app.engine.consumables.roll_exploding_d6", lambda: (6, [6]))
    log, hit = throw_holy_water(cleric, skeleton, show_rolls=False)
    assert hit
    assert skeleton.life == 0
    assert any("destroyed" in line.lower() for line in log)


def test_summoned_beast_takes_damage_from_foes(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_d6", lambda: (6, [6]))
    eng = engine()
    foe = EnemyState(id="g1", name="Goblin", category="minions", level=2, life=2, max_life=2)
    session = _session(
        mode="combat",
        map_state=MapState(
            tiles=[
                TileState(
                    id="t",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[foe],
                )
            ],
            current_tile_id="t",
        ),
        summoned_beast_life=5,
        summoned_beast_owner_id="h1",
    )
    eng._foes_strike_summoned_beast(session, session.map_state.tiles[0], show_rolls=False)
    assert session.summoned_beast_life == 4


def test_end_bear_form_applies_half_damage() -> None:
    eng = engine()
    druid = _party_member(class_id="druid", class_name="Druid", current_life=2, statuses=["Bear Form"])
    session = _session(
        party=[druid],
        bear_form_owner_id="h1",
        bear_form_start_life=8,
        bear_form_pre_life=4,
    )
    eng._end_bear_form(session)
    assert druid.current_life == 1
    assert session.bear_form_owner_id is None
