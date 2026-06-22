from __future__ import annotations

from app.engine import combat
from app.engine.class_abilities import (
    apply_nourishing_meal,
    paladin_heal,
    rage_uses_remaining,
    roll_rage_attack_d6,
    spend_luck_point,
    spend_rage_use,
)
from app.engine.combat import CombatContext, resolve_combat_round, resolve_flee
from app.schemas import EnemyState, PartyMemberState, SessionState


def barbarian(level: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id="barb",
        name="Borg",
        class_id="barbarian",
        class_name="Barbarian",
        level=level,
        xp=0,
        gold=0,
        current_life=8,
        max_life=8,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon"],
    )


def halfling(level: int = 2) -> PartyMemberState:
    return PartyMemberState(
        character_id="half",
        name="Hobb",
        class_id="halfling",
        class_name="Halfling",
        level=level,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=1,
        save_bonus=2,
        inventory=["Sling"],
    )


def swashbuckler(level: int = 3) -> PartyMemberState:
    return PartyMemberState(
        character_id="swash",
        name="Dash",
        class_id="swashbuckler",
        class_name="Swashbuckler",
        level=level,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
        inventory=["Hand weapon", "Light hand weapon"],
    )


def paladin(level: int = 2) -> PartyMemberState:
    return PartyMemberState(
        character_id="pala",
        name="Grace",
        class_id="paladin",
        class_name="Paladin",
        level=level,
        xp=0,
        gold=0,
        current_life=6,
        max_life=6,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
    )


def goblin(*, life: int = 4) -> EnemyState:
    return EnemyState(id="g1", name="Goblin", category="minions", level=4, life=life, max_life=life)


def empty_session(**overrides) -> SessionState:
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


def test_rage_uses_scale_with_level() -> None:
    session = empty_session()
    hero = barbarian(4)
    assert rage_uses_remaining(session, hero) == 3
    assert spend_rage_use(session, hero)
    assert rage_uses_remaining(session, hero) == 2


def test_roll_rage_attack_d6_picks_best(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.class_abilities.roll_d6", lambda: 2)
    total, rolls = roll_rage_attack_d6()
    assert rolls == [2, 2, 2]
    assert total == 2


def test_rage_attack_doubles_damage(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.class_abilities.roll_rage_attack_d6", lambda: (5, [2, 5, 3]))
    session = empty_session()
    hero = barbarian(4)
    foe = goblin()

    def spend_rage(member: PartyMemberState) -> bool:
        return spend_rage_use(session, member)

    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=True,
        party_attacked_immediately=True,
        encounter_round=0,
        context=CombatContext(
            rage_attackers={"barb"},
            spend_rage=spend_rage,
        ),
    )
    assert any("double damage" in line.lower() for line in result.log)
    assert foe.life <= 0


def test_luck_flee_skips_parting_attacks(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
    session = empty_session()
    hero = halfling(2)
    foe = goblin(life=1)
    assert spend_luck_point(session, hero)
    result = resolve_flee([hero], [foe], show_rolls=True, skip_parting_attacks=True)
    assert hero.current_life == 4
    assert any("without parting" in line.lower() for line in result.log)


def test_panache_awarded_on_kill() -> None:
    session = empty_session(panache_points={})
    hero = swashbuckler(3)
    from app.engine.class_abilities import award_panache_kill

    message = award_panache_kill(session, hero)
    assert message
    assert session.panache_points.get("swash") == 1
    award_panache_kill(session, hero)
    assert session.panache_points.get("swash") == 2
    assert award_panache_kill(session, hero)
    assert session.panache_points.get("swash") == 3
    assert award_panache_kill(session, hero) is None


def test_paladin_heal_spends_prayer_point() -> None:
    session = empty_session()
    pal = paladin(2)
    ally = barbarian(4)
    ally.current_life = 3
    session.party = [pal, ally]
    messages = paladin_heal(session, pal, ally)
    assert ally.current_life == 4
    assert any("prayer point" in line.lower() for line in messages)


def test_nourishing_meal_consumes_rations() -> None:
    session = empty_session(nourishing_meal_used=False)
    cook = halfling(2)
    cook.inventory = ["Food rations", "Food rations"]
    ally = barbarian(4)
    ally.current_life = 3
    session.party = [cook, ally]
    log = apply_nourishing_meal(session, session.party, [cook.character_id, ally.character_id])
    assert session.nourishing_meal_used
    assert ally.current_life == 4
    assert any("Nourishing Meal" in line for line in log)
