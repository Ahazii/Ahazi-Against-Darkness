from __future__ import annotations

from app.engine import combat
from app.engine.combat_modifiers import enemy_magic_resist_bonus, has_blade_poison, spell_mr_penetration_level, spell_target_level
from app.engine.spells import resolve_spell_cast
from app.schemas import EnemyState, PartyMemberState


def member(*, inventory: list[str] | None = None) -> PartyMemberState:
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
        inventory=inventory or [],
    )


def poison_spider() -> EnemyState:
    return EnemyState(
        id="spider",
        name="Spider",
        category="vermin",
        level=2,
        life=1,
        max_life=1,
        tags=["vermin", "poison"],
    )


def necromancer() -> EnemyState:
    return EnemyState(
        id="necro",
        name="Necromancer",
        category="boss",
        level=5,
        life=5,
        max_life=5,
        tags=["boss", "caster", "magic_resist"],
    )


def test_blade_poison_adds_damage_and_is_consumed(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: (6, [6]))
    hero = member(inventory=["Blade poison"])
    foe = EnemyState(id="gob", name="Goblin", category="minions", level=2, life=3, max_life=3)
    result = combat.resolve_combat_round([hero], [foe], show_rolls=False)
    assert foe.life < 3
    assert not has_blade_poison(hero)
    assert any("blade poison" in line.lower() for line in result.log)


def test_poison_foe_can_deal_extra_damage(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: (2, [2]))
    monkeypatch.setattr(combat, "poison_save_succeeds", lambda *args, **kwargs: (False, ["Poison save failed."]))
    hero = member()
    result = combat.resolve_combat_round([hero], [poison_spider()], show_rolls=False, foe_phase_only=True)
    assert hero.current_life <= 2
    assert any("poison" in line.lower() for line in result.log)


def test_magic_resist_raises_spell_target_level() -> None:
    foe = necromancer()
    assert enemy_magic_resist_bonus(foe) == 2
    assert spell_target_level(foe) == foe.level
    assert spell_mr_penetration_level(foe) == foe.level + 2


def test_fireball_uses_mr_two_step(monkeypatch) -> None:
    rolls = iter([(4, [4]), (4, [4])])
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda level: next(rolls))
    monkeypatch.setattr("app.engine.spells.roll_exploding_for_level", lambda level: next(rolls))
    caster = PartyMemberState(
        character_id="wiz",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=4,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Fireball"],
    )
    foe = necromancer()
    outcome = resolve_spell_cast("Fireball", caster, [caster], [foe], show_rolls=True)
    assert any("penetrate MR" in line for line in outcome.log)
    assert foe.life < foe.max_life
