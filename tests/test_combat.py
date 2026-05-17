from __future__ import annotations

from app.engine import combat
from app.engine.combat import resolve_combat_round
from app.schemas import EnemyState, PartyMemberState


def member() -> PartyMemberState:
    return PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )


def enemy() -> EnemyState:
    return EnemyState(
        id="rat",
        name="Rat",
        category="vermin",
        level=3,
        life=1,
        max_life=1,
        attacks=1,
    )


def test_combat_round_can_trace_rolls_and_math(monkeypatch) -> None:
    rolls = iter([2, 1])
    monkeypatch.setattr(combat, "roll_d6", lambda: next(rolls))

    result = resolve_combat_round([member()], [enemy()], show_rolls=True, explain_math=True)

    assert any("Attack roll: Hero vs Rat: d6 = 2." in entry for entry in result.log)
    assert any("Attack math: 2 + ATK 0 = 2" in entry for entry in result.log)
    assert any("Defense roll: Hero vs Rat: d6 = 1." in entry for entry in result.log)
    assert any("Defense math: 1 + DEF 0 = 1" in entry for entry in result.log)
    assert result.party[0].current_life == 2
