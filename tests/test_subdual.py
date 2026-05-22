from __future__ import annotations

from app.engine.combat import resolve_combat_round
from app.engine.subdual import apply_subdual_damage, subdue_minor_foe
from app.schemas import EnemyState, PartyMemberState


def hero() -> PartyMemberState:
    return PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
    )


def ogre() -> EnemyState:
    return EnemyState(
        id="ogre",
        name="Ogre",
        category="boss",
        level=5,
        life=6,
        max_life=6,
        attacks=1,
    )


def goblin() -> EnemyState:
    return EnemyState(
        id="gob",
        name="Goblin",
        category="minions",
        level=3,
        life=1,
        max_life=1,
    )


def test_apply_subdual_damage_knocks_out_major_foe() -> None:
    foe = ogre()
    assert apply_subdual_damage(foe, 6) is True
    assert foe.life == 0
    assert foe.subdued is True


def test_subdual_combat_does_not_slay_minor_groups(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda level: (6, [6]))
    foe = goblin()
    result = resolve_combat_round([hero()], [foe], show_rolls=False, subdual=True)
    assert foe.subdued is True
    assert foe.life == 0
    assert any("subdues" in line.lower() for line in result.log)


def test_lethal_combat_still_slays_minions(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda level: (6, [6]))
    foe = goblin()
    resolve_combat_round([hero()], [foe], show_rolls=False, subdual=False)
    assert not foe.subdued
    assert foe.life <= 0


def test_subdue_minor_foe_sets_flag() -> None:
    foe = goblin()
    subdue_minor_foe(foe)
    assert foe.subdued is True
    assert foe.life == 0
