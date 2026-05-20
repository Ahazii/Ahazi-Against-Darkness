from __future__ import annotations

from app.engine import combat
from app.engine.combat import (
    CombatContext,
    enemy_can_fire_ranged,
    initiative_phases,
    resolve_combat_round,
)
from app.schemas import EnemyState, PartyMemberState


def archer() -> PartyMemberState:
    return PartyMemberState(
        character_id="archer",
        name="Archer",
        class_id="ranger",
        class_name="Ranger",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=2,
        inventory=["Bow", "Hand weapon"],
        default_melee_weapon="Hand weapon",
        default_missile_weapon="Bow",
    )


def javelin_kobold() -> EnemyState:
    return EnemyState(
        id="kobold",
        name="Kobold Scout",
        category="minions",
        level=3,
        life=1,
        max_life=1,
        tags=["ranged", "javelin"],
    )


def test_initiative_phases_attack_immediately() -> None:
    phases = initiative_phases(
        encounter_round=0,
        party_surprised=False,
        party_attacked_immediately=True,
        foes_strike_first=False,
    )
    assert phases == ["pc_ranged", "foe_ranged", "pc_melee", "foe_melee"]


def test_initiative_phases_reactions_first() -> None:
    phases = initiative_phases(
        encounter_round=0,
        party_surprised=False,
        party_attacked_immediately=False,
        foes_strike_first=False,
    )
    assert phases == ["foe_ranged", "pc_melee", "foe_melee"]


def test_initiative_phases_surprised() -> None:
    phases = initiative_phases(
        encounter_round=0,
        party_surprised=True,
        party_attacked_immediately=False,
        foes_strike_first=False,
    )
    assert phases == ["foe_ranged", "pc_ranged", "foe_melee", "pc_melee"]


def test_missile_then_unarmed_same_round(monkeypatch) -> None:
    rolls = iter([(6, [6]), (6, [6]), (1, [1])])
    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: next(rolls, (1, [1])))
    hero = archer()
    context = CombatContext(wielded_melee={"archer": "Hand weapon"})
    result = resolve_combat_round(
        [hero],
        [EnemyState(id="g", name="Goblin", category="minions", level=3, life=3, max_life=3)],
        show_rolls=True,
        party_attacked_immediately=True,
        encounter_round=0,
        context=context,
        missile_used=set(),
    )
    assert any("Opening missile volley" in line for line in result.log)
    assert any("fights unarmed (-2)" in line for line in result.log)
    assert any("unarmed -2" in line for line in result.log)


def test_foe_ranged_skips_melee_draw(monkeypatch) -> None:
    rolls = iter([(1, [1]), (1, [1]), (1, [1])])
    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: next(rolls, (1, [1])))
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon"],
    )
    tough_kobold = javelin_kobold()
    tough_kobold.life = 5
    tough_kobold.max_life = 5
    result = resolve_combat_round(
        [hero],
        [tough_kobold],
        show_rolls=True,
        party_attacked_immediately=True,
        encounter_round=0,
        missile_used=set(),
    )
    assert enemy_can_fire_ranged(tough_kobold)
    assert any("Foe ranged phase" in line for line in result.log)
    assert any("spends the turn drawing a melee weapon" in line for line in result.log)
