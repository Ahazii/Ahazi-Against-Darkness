from __future__ import annotations

from app.engine import combat
from app.engine.combat_modifiers import (
    envenomed_weapon_kind,
    enemy_magic_resist_bonus,
    has_blade_poison,
    resolve_spell_effect,
    spell_mr_penetration_level,
    spell_target_level,
)
from app.engine.madness import apply_envenom_weapon
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


def test_envenomed_weapon_adds_attack_and_is_consumed(monkeypatch) -> None:
    from app.schemas import SessionState, MapState, TileState

    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (2, [2]))
    hero = member(inventory=["Blade poison"])
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="now",
        updated_at="now",
    )
    apply_envenom_weapon(session, hero, "melee")
    foe = EnemyState(id="gob", name="Goblin", category="minions", level=2, life=3, max_life=3)
    result = combat.resolve_combat_round([hero], [foe], show_rolls=False)
    assert foe.life < 3
    assert envenomed_weapon_kind(hero) is None
    assert not has_blade_poison(hero)
    assert any("envenomed weapon adds +1 attack" in line.lower() for line in result.log)


def test_poison_foe_can_deal_extra_damage(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (2, [2]))
    monkeypatch.setattr(combat, "poison_save_succeeds", lambda *args, **kwargs: (False, ["Poison save failed."]))
    hero = member()
    spider = poison_spider()
    result = combat.resolve_combat_round([hero], [spider], show_rolls=False, foe_phase_only=True)
    assert hero.current_life <= 2
    assert f"Event: {spider.name}'s poison threatens {hero.name}." in result.log
    assert f"Effect: {spider.name} poisons {hero.name}." in result.log
    assert f"Effect: {hero.name} takes 1 extra damage from {spider.name}'s poison." in result.log
    assert f"Effect: {hero.name} is poisoned (L{spider.level})." in result.log


def test_poison_foe_resisted_log_names_target_and_foe(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (2, [2]))
    monkeypatch.setattr(combat, "poison_save_succeeds", lambda *args, **kwargs: (True, ["Poison save passed."]))
    hero = member()
    spider = poison_spider()

    result = combat.resolve_combat_round([hero], [spider], show_rolls=False, foe_phase_only=True)

    assert f"Event: {spider.name}'s poison threatens {hero.name}." in result.log
    assert f"{hero.name} resists {spider.name}'s poison." in result.log
    assert not any(status.lower().startswith("poisoned") for status in hero.statuses)


def test_magic_resist_raises_spell_target_level() -> None:
    foe = necromancer()
    assert enemy_magic_resist_bonus(foe) == 2
    assert spell_target_level(foe) == foe.level
    assert spell_mr_penetration_level(foe) == foe.level + 2


def test_spell_connect_failure_logs_roll(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (2, [2]))
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
    ogre = EnemyState(id="ogre", name="Ogre", category="boss", level=8, life=6, max_life=6)
    hit, log, total, _ = resolve_spell_effect(caster, ogre, show_rolls=False, label="Fireball")
    assert not hit
    assert total == 6
    assert any("rolled 6 vs L8" in line for line in log)
    assert not any("needed L8" in line for line in log)


def test_fireball_uses_mr_two_step(monkeypatch) -> None:
    rolls = iter([(4, [4]), (4, [4])])
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: next(rolls))
    monkeypatch.setattr("app.engine.spells.roll_exploding_for_level", lambda *args, **kwargs: next(rolls))
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
