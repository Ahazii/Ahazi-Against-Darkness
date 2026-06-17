from __future__ import annotations

import json
from pathlib import Path

from app.engine.combat import CombatContext, resolve_combat_round
from app.engine.monster_template_effects import (
    LIFE_DRAIN_NOT_HIT_TAG,
    apply_life_drain_after_party_turn,
    template_combat_tags,
)
from app.schemas import EnemyState, PartyMemberState


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
        inventory=["Hand weapon (silvered)"],
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


def _cavern_wraith() -> EnemyState:
    return EnemyState(
        id="wraith-1",
        name="Cavern Wraith",
        category="weird",
        level=6,
        life=6,
        max_life=6,
        tags=["undead", "spirit", LIFE_DRAIN_NOT_HIT_TAG],
    )


def test_template_combat_tags_from_cavern_wraith_template() -> None:
    monsters_path = Path(__file__).resolve().parents[1] / "data" / "rules" / "monsters.json"
    table = json.loads(monsters_path.read_text(encoding="utf-8"))["caverns_weird"]
    template = next(item for item in table if item["name"] == "Cavern Wraith")
    assert LIFE_DRAIN_NOT_HIT_TAG in template_combat_tags(template)


def test_life_drain_when_wraith_not_hit() -> None:
    hero = _hero()
    wraith = _cavern_wraith()
    context = CombatContext()
    log = apply_life_drain_after_party_turn([wraith], [hero], context=context, show_rolls=True)
    assert hero.current_life == 4
    assert any("life drain" in line.lower() for line in log)


def test_life_drain_skipped_when_wraith_was_hit() -> None:
    hero = _hero()
    wraith = _cavern_wraith()
    context = CombatContext()
    context.enemies_hit_this_round.add(wraith.id)
    log = apply_life_drain_after_party_turn([wraith], [hero], context=context, show_rolls=True)
    assert hero.current_life == 5
    assert any("was hit this round" in line for line in log)


def test_life_drain_runs_after_party_turn_when_attack_blocked(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda level: (6, [6]))
    hero = _hero(inventory=["Hand weapon"])
    wraith = _cavern_wraith()
    wraith.tags.extend(
        [
            "weapon_allow:magic_weapons",
            "weapon_allow:silvered_weapons",
            "weapon_allow:two_plus_damage_single_blow",
        ]
    )
    result = resolve_combat_round(
        [hero],
        [wraith],
        show_rolls=False,
        context=CombatContext(),
        party_phase_only=True,
    )
    assert hero.current_life == 4
    assert any("life drain" in line.lower() for line in result.log)
