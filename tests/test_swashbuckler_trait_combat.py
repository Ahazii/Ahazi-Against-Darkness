from __future__ import annotations

from app.engine import combat
from app.engine.combat import CombatContext, resolve_combat_round
from app.engine.swashbuckler_traits import (
    activate_blade_dance,
    apply_swashbuckler_taunt,
    lucky_hat_reroll_defense,
    taunt_eligible_foe,
)
from app.schemas import EnemyState, PartyMemberState, SessionState


def swash(trait: str, *, level: int = 3) -> PartyMemberState:
    return PartyMemberState(
        character_id="sw",
        name="Dash",
        class_id="swashbuckler",
        class_name="Swashbuckler",
        class_traits=[trait],
        level=level,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
        inventory=["Hand weapon", "Light hand weapon", "Plumed/tricorn hat"],
        default_melee_weapon="Hand weapon",
        default_melee_weapon_secondary="Light hand weapon",
    )


def goblin(*, life: int = 4) -> EnemyState:
    return EnemyState(id="g1", name="Goblin", category="minions", level=4, life=life, max_life=life)


def wraith() -> EnemyState:
    return EnemyState(
        id="w1",
        name="Wraith",
        category="weird",
        level=5,
        life=5,
        max_life=5,
        tags=["undead", "unliving"],
    )


def vampire() -> EnemyState:
    return EnemyState(
        id="v1",
        name="Vampire",
        category="boss",
        level=6,
        life=6,
        max_life=6,
        tags=["undead"],
    )


def session(**overrides) -> SessionState:
    base = {
        "id": "sess",
        "party_id": "party",
        "adventure_id": "random",
        "adventure_type": "random",
        "mode": "combat",
        "party": [],
        "map_state": {"width": 20, "height": 20, "tiles": [], "current_tile_id": "t1"},
        "log": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return SessionState.model_validate(base)


def test_taunt_rejects_weird_but_allows_vampire() -> None:
    assert not taunt_eligible_foe(wraith())
    assert taunt_eligible_foe(vampire())


def test_taunt_queues_penalty_for_next_foe_turn() -> None:
    sess = session()
    hero = swash("Taunt")
    foe = goblin()
    logs = apply_swashbuckler_taunt(sess, hero, foe)
    assert any("mocks" in line for line in logs)
    assert sess.foe_taunt_pending[foe.id] == 1
    assert hero.character_id in sess.swashbuckler_taunt_used


def test_flourishing_strike_bonus_off_hand_after_main_hand_hit(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    hero = swash("Flourishing Strike")
    foe = goblin(life=8)
    sess = session(panache_points={})
    context = CombatContext(
        session=sess,
        flourishing_strike_attackers={"sw"},
        wielded_melee={"sw": "Hand weapon"},
    )
    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=False,
        party_attacked_immediately=True,
        encounter_round=0,
        context=context,
    )
    assert any("Flourishing Strike" in line for line in result.log)
    assert "sw" in sess.swashbuckler_flourishing_used


def test_riposte_counter_on_successful_defense(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6, 2]))
    hero = swash("Riposte")
    foe = goblin(life=8)
    sess = session()
    context = CombatContext(
        session=sess,
        riposte_attackers={"sw"},
        wielded_melee={"sw": "Hand weapon"},
    )
    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=False,
        foes_first=True,
        encounter_round=1,
        context=context,
    )
    assert any("Ripostes" in line for line in result.log)
    assert "sw" in sess.swashbuckler_riposte_used


def test_blade_dance_spends_panache_for_bonuses() -> None:
    sess = session(panache_points={"sw": 2})
    hero = swash("Blade Dance")
    logs = activate_blade_dance(sess, hero, panache_points=2)
    assert any("Blade Dances" in line for line in logs)
    assert sess.swashbuckler_blade_dance_bonus["sw"] == 2
    assert sess.panache_points["sw"] == 0


def test_lucky_hat_reroll_can_save_failed_defense(monkeypatch) -> None:
    rolls = iter([(1, [1]), (6, [6])])

    def fake_roll(level: int):
        return next(rolls)

    monkeypatch.setattr("app.engine.swashbuckler_traits.roll_exploding_for_level", fake_roll)
    sess = session()
    hero = swash("Lucky Hat")
    sess.pending_defense_reroll = {"character_id": "sw", "enemy_id": "g1", "level": 4, "kind": "defense"}
    sess.pending_defense_reroll_blocked_damage = {
        "character_id": "sw",
        "enemy_id": "g1",
        "enemy_name": "Goblin",
    }
    logs, succeeded = lucky_hat_reroll_defense(sess, hero, show_rolls=False)
    assert succeeded
    assert hero.current_life == 5
    assert "sw" in sess.swashbuckler_lucky_hat_used
