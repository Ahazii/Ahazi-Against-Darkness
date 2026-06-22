from __future__ import annotations

from unittest.mock import patch

from app.engine.poison_expert import (
    apply_poison_expert_boss_effect,
    apply_poison_expert_coating,
    poison_expert_attack_effects,
    rogue_meets_poison_expert_requirement,
)
from app.schemas import EnemyState, PartyMemberState, SessionState
from app.engine.weapon_finishes import is_weapon_item_poisoned


def _member(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="r1",
        name="Rogue",
        class_id="rogue",
        class_name="Rogue",
        level=5,
        xp=0,
        gold=200,
        bank_gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        inventory=["Scimitar"],
        expert_trained=True,
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def _session(**kwargs) -> SessionState:
    party = kwargs.pop("party", [_member()])
    data = dict(
        id="s1",
        party_id="p1",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=party,
        map_state={"width": 31, "height": 31, "tiles": [], "current_tile_id": "t1"},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        camped_outside=True,
    )
    data.update(kwargs)
    return SessionState.model_validate(data)


def test_rogue_meets_poison_expert_requirement() -> None:
    assert rogue_meets_poison_expert_requirement(_member(level=5))
    assert not rogue_meets_poison_expert_requirement(_member(level=4))
    assert not rogue_meets_poison_expert_requirement(_member(class_id="warrior", class_name="Warrior"))


def test_apply_poison_expert_coating_marks_weapon() -> None:
    rogue = _member()
    session = _session(
        professional_buffs={"poison_expert_pending": True, "poison_expert_rogue_id": rogue.character_id}
    )
    logs = apply_poison_expert_coating(session, item_name="Scimitar", character_id=rogue.character_id)
    assert any("envenoms Scimitar" in line for line in logs)
    coated_rogue = session.party[0]
    assert any(is_weapon_item_poisoned(item) for item in coated_rogue.inventory)
    assert not session.professional_buffs.get("poison_expert_pending")


def test_poison_expert_minion_attack_bonus() -> None:
    rogue = _member(inventory=["Scimitar (poisoned)"])
    enemy = EnemyState(
        id="m1",
        name="Orc",
        category="minions",
        level=3,
        life=1,
        max_life=1,
        attacks=1,
    )
    bonus, log = poison_expert_attack_effects(
        rogue,
        enemy,
        missile=False,
        weapon=None,
        weapon_item="Scimitar (poisoned)",
    )
    assert bonus == 1
    assert any("+1 Attack" in line for line in log)


def test_poison_expert_boss_level_drop_recalcs_stats() -> None:
    rogue = _member(level=5)
    boss = EnemyState(
        id="b1",
        name="Young Red Dragon",
        category="boss",
        level=6,
        life=8,
        max_life=8,
        attacks=2,
        tags=["dragon"],
    )
    bonus, log = poison_expert_attack_effects(
        rogue,
        boss,
        missile=False,
        weapon=None,
        weapon_item="Scimitar (poisoned)",
    )
    assert bonus == 0
    assert any("immune" in line.lower() for line in log)

    boss.tags = []
    with patch("app.engine.poison_expert.roll_d8", return_value=6):
        ok, log = apply_poison_expert_boss_effect(rogue, boss, roll_fn=lambda: 6)
    assert ok is True
    assert boss.level == 5
    assert boss.max_life < 8
    assert boss.life <= boss.max_life
    assert "poison_expert_reduced" in boss.tags
