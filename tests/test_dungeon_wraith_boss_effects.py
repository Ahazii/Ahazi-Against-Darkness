from __future__ import annotations

import json
from pathlib import Path

from app.engine.combat import CombatContext, resolve_combat_round
from app.engine.monster_template_effects import (
    apply_encounter_start_effects,
    apply_on_hit_effects,
    template_encounter_start_effects,
    template_on_hit_effects,
)
from app.engine.special_items import light_source_defense_bonus, member_has_lantern
from app.schemas import EnemyState, PartyMemberState, SessionState


def _hero(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=4,
        max_life=5,
        current_life=5,
        marching_order=1,
        inventory=["Lantern"],
        statuses=[],
        spells=[],
        learned_expert_skills=[],
        gold=0,
        clues=0,
        xp=0,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _session() -> SessionState:
    hero = _hero()
    return SessionState(
        id="session-1",
        party_id="party-1",
        adventure_id="adv-1",
        adventure_type="random",
        party=[hero],
        map_state={"current_tile_id": "tile-1", "tiles": []},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _dungeon_wraith_template() -> dict:
    monsters_path = Path(__file__).resolve().parents[1] / "data" / "rules" / "monsters.json"
    table = json.loads(monsters_path.read_text(encoding="utf-8"))["fiendish_foes_boss"]
    return next(item for item in table if item["name"] == "Wraith")


def _dungeon_wraith(**overrides) -> EnemyState:
    template = _dungeon_wraith_template()
    base = dict(
        id="wraith-boss",
        name="Wraith",
        category="weird",
        level=8,
        life=6,
        max_life=6,
        tags=["boss", "undead"],
        on_hit_effects=template_on_hit_effects(template),
        encounter_start_effects=template_encounter_start_effects(template),
    )
    base.update(overrides)
    return EnemyState(**base)


def test_wraith_template_effects_copied_from_monsters_json() -> None:
    template = _dungeon_wraith_template()
    assert template_encounter_start_effects(template)[0]["type"] == "extinguish_lanterns"
    assert template_on_hit_effects(template)[0]["type"] == "level_drain"


def test_extinguish_lanterns_on_encounter_start(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.engine.monster_template_effects.chance_roll_succeeds",
        lambda chance, roll=None: (True, 1, 2, 6),
    )
    hero = _hero()
    session = _session()
    wraith = _dungeon_wraith()
    log = apply_encounter_start_effects([wraith], [hero], session, show_rolls=True)
    assert session.combat_lanterns_extinguished is True
    assert member_has_lantern(hero, session=session) is False
    assert any("extinguished" in line.lower() for line in log)


def test_extinguish_lanterns_blocks_light_defense_bonus() -> None:
    hero = _hero()
    session = _session()
    session.combat_lanterns_extinguished = True
    morlock = EnemyState(
        id="morlock-1",
        name="Morlock",
        category="humanoid",
        level=3,
        life=3,
        max_life=3,
        tags=["light_averse"],
    )
    assert light_source_defense_bonus(hero, morlock, session=session) == 0


def test_level_drain_on_hit_when_save_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.engine.monster_template_effects.roll_exploding_for_level",
        lambda *args, **kwargs: (1, [1]),
    )
    hero = _hero(level=4)
    wraith = _dungeon_wraith()
    context = CombatContext(session=_session())
    log = apply_on_hit_effects(wraith, hero, context=context, show_rolls=True)
    assert hero.level == 3
    assert any("level drain" in line.lower() or "level drops" in line.lower() for line in log)


def test_encounter_start_runs_on_first_combat_round(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.engine.monster_template_effects.chance_roll_succeeds",
        lambda chance, roll=None: (True, 1, 2, 6),
    )
    hero = _hero()
    wraith = _dungeon_wraith()
    session = _session()
    context = CombatContext(session=session)
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda *args, **kwargs: (99, [6]))
    result = resolve_combat_round(
        [hero],
        [wraith],
        show_rolls=True,
        context=context,
        foes_strike_first=True,
        encounter_round=0,
    )
    assert session.combat_lanterns_extinguished is True
    assert any("extinguish" in line.lower() for line in result.log)
