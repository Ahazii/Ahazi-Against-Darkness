from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.engine.experience import award_classical_progress, defeated_mixed_major_minor
from app.engine.fiendish_foes import template_never_wandering
from app.engine.monster_template_effects import (
    apply_blood_drain_after_foe_turn,
    apply_encounter_start_effects,
    apply_first_turn_special_attacks,
    apply_random_power_effects,
    mark_stirge_blood_drain,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, PartyMemberState, SessionState, TileState

ROOT = Path(__file__).resolve().parents[1]


def _hero(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        max_life=6,
        current_life=6,
        marching_order=1,
        inventory=[],
        statuses=[],
        spells=[],
        learned_expert_skills=[],
        gold=0,
        clues=0,
        xp=0,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _enemy(**overrides) -> EnemyState:
    base = dict(
        id="e1",
        name="Fiendish Chaos Lord",
        category="boss",
        level=6,
        life=5,
        max_life=5,
        tags=["random_power:evil_eye"],
    )
    base.update(overrides)
    return EnemyState(**base)


def _session(party: list[PartyMemberState]) -> SessionState:
    return SessionState(
        id="s1",
        party_id="p1",
        adventure_id="random",
        adventure_type="random",
        party=party,
        map_state={"current_tile_id": "t1", "tiles": []},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_defeated_mixed_major_minor_pdf_p180() -> None:
    mixed = [
        EnemyState(id="a", name="Boss", category="boss", level=5, life=0, max_life=5),
        EnemyState(id="b", name="Minions", category="minions", level=4, life=0, max_life=1),
    ]
    assert defeated_mixed_major_minor(mixed)
    assert not defeated_mixed_major_minor([mixed[1]])


def test_award_classical_progress_mixed_grants_two_rolls_pdf_p180() -> None:
    defeated = [
        EnemyState(id="a", name="Boss", category="boss", level=5, life=0, max_life=5),
        EnemyState(id="b", name="Minions", category="minions", level=4, life=0, max_life=1),
    ]
    result = award_classical_progress(
        minor_encounters_defeated=0,
        clues_found=0,
        defeated=defeated,
        final_boss_killed=False,
    )
    assert result.classical_rolls == 2
    assert any("2 XP rolls" in line for line in result.log)


def test_template_never_wandering_covers_mantlebeast_and_dragon() -> None:
    monsters = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override").monsters()
    dragon = next(m for m in monsters["fiendish_foes_boss"] if m["name"] == "Young Red Dragon")
    mantle = next(m for m in monsters["fiendish_foes_weird"] if m["name"] == "Lurking Mantlebeast")
    assert template_never_wandering(dragon)
    assert template_never_wandering(mantle)


def test_wandering_table_excludes_mantlebeast_and_dragon() -> None:
    monsters = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override").monsters()
    weird_eligible = [t for t in monsters["fiendish_foes_weird"] if not template_never_wandering(t)]
    boss_eligible = [t for t in monsters["fiendish_foes_boss"] if not template_never_wandering(t)]
    assert not any(m["name"] == "Lurking Mantlebeast" for m in weird_eligible)
    assert not any(m["name"] == "Young Red Dragon" for m in boss_eligible)


def test_roll_enemy_wandering_empty_when_all_templates_excluded() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    party = [_hero(level=5), _hero(character_id="hero-2", level=5)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_enabled=True)
    with patch("app.engine.random_dungeon.template_never_wandering", return_value=True):
        assert engine._roll_enemy(session, "weird", hcl=5, wandering=True) == []


def test_mixed_treasure_uses_major_rolls_only_pdf_p180() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    party = [_hero(level=5), _hero(character_id="hero-2", level=5)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_enabled=True)
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="1",
        tile_type="room",
        title="Room",
        description="",
        resolved=True,
        defeated_enemies=[
            EnemyState(id="b", name="Fiendish Chaos Lord", category="boss", level=6, life=0, max_life=7),
            EnemyState(id="m", name="Chaos Slavers", category="minions", level=5, life=0, max_life=1),
        ],
    )
    session.map_state.tiles = [tile]
    session.map_state.current_tile_id = "t1"
    count = engine._treasure_roll_count_for_tile(session, tile)
    assert count == 3
    assert any("Minor foe treasure suppressed" in line for line in session.log)


def test_chaos_lord_evil_eye_applies_defense_penalty() -> None:
    hero = _hero()
    session = _session([hero])
    lord = _enemy(tags=["random_power:evil_eye"])
    with patch("app.engine.monster_template_effects.roll_exploding_for_level", lambda *args, **kwargs: (1, [1])):
        log = apply_random_power_effects([lord], [hero], session, show_rolls=False)
    assert any("evil eye" in line.lower() for line in log)
    assert any("defense penalty (evil eye)" in status.lower() for status in hero.statuses)


def test_young_red_dragon_fire_breath_first_turn() -> None:
    monsters = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override").monsters()
    template = next(m for m in monsters["fiendish_foes_boss"] if m["name"] == "Young Red Dragon")
    hero = _hero(current_life=6)
    session = _session([hero])
    dragon = EnemyState(
        id="d1",
        name="Young Red Dragon",
        category="boss",
        level=11,
        life=8,
        max_life=8,
        special_attacks=list(template["special_attacks"]),
    )
    with patch("app.engine.monster_template_effects.roll_exploding_for_level", lambda *args, **kwargs: (1, [1])), patch(
        "app.engine.monster_template_effects.roll_d3", return_value=2
    ):
        log = apply_first_turn_special_attacks([dragon], [hero], session, show_rolls=False)
    assert hero.current_life == 4
    assert any("fire breath" in line.lower() for line in log)


def test_stirge_blood_drain_after_foe_turn() -> None:
    hero = _hero(current_life=5, statuses=["Stirge blood drain"])
    stirge = EnemyState(
        id="s1",
        name="Stirges",
        category="vermin",
        level=6,
        life=1,
        max_life=1,
        per_turn_effects=[{"type": "blood_drain", "damage": 1}],
    )
    log = apply_blood_drain_after_foe_turn([stirge], [hero], show_rolls=False)
    assert hero.current_life == 4
    assert any("blood drain" in line.lower() for line in log)


def test_chaos_slavers_preset_trap_before_fight() -> None:
    monsters = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override").monsters()
    template = next(m for m in monsters["fiendish_foes_minions"] if m["name"] == "Chaos Slavers")
    hero = _hero(class_id="warrior", marching_order=1)
    session = _session([hero])
    slavers = EnemyState(
        id="c1",
        name="Chaos Slavers",
        category="minions",
        level=5,
        life=1,
        max_life=1,
        encounter_start_effects=list(template["encounter_start_effects"]),
    )
    with patch("app.engine.monster_template_effects.roll_exploding_for_level", lambda *args, **kwargs: (1, [1])):
        log = apply_encounter_start_effects([slavers], [hero], session, show_rolls=False)
    assert hero.current_life == 5 or "Bear Trap Wound" in hero.statuses or any("bear trap" in line.lower() for line in log)
    assert any("preset bear trap" in line.lower() for line in log)


def test_mark_stirge_blood_drain_on_hit() -> None:
    hero = _hero()
    stirge = EnemyState(
        id="s1",
        name="Stirges",
        category="vermin",
        level=6,
        life=1,
        max_life=1,
        per_turn_effects=[{"type": "blood_drain"}],
    )
    mark_stirge_blood_drain(hero, stirge)
    assert "Stirge blood drain" in hero.statuses
