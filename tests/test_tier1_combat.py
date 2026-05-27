from __future__ import annotations

import json
from pathlib import Path

from app.engine import combat, spells
from app.engine.combat import (
    CombatContext,
    enemy_has_regeneration,
    resolve_combat_round,
    resolve_flee,
)
from app.engine.combat_modifiers import (
    enemy_magic_resist_bonus,
    resolve_spell_effect,
    spell_mr_penetration_level,
    spell_target_level,
)
from app.engine.reactions import resolve_reaction_source
from app.schemas import EnemyState, PartyMemberState


def wizard(level: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id="wiz",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=level,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Fireball"],
    )


def necromancer(*, life: int = 5) -> EnemyState:
    return EnemyState(
        id="necro",
        name="Necromancer",
        category="boss",
        level=5,
        life=life,
        max_life=life,
        tags=["boss", "caster", "magic_resist"],
    )


def troll(*, life: int = 4, max_life: int = 7) -> EnemyState:
    return EnemyState(
        id="troll",
        name="Troll",
        category="boss",
        level=6,
        life=life,
        max_life=max_life,
        attacks=1,
        tags=["boss", "regeneration"],
    )


def test_mr_two_step_connect_then_penetration(monkeypatch) -> None:
    rolls = iter([(6, [6]), (2, [2])])
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda level: next(rolls))
    foe = necromancer()
    assert enemy_magic_resist_bonus(foe) == 2
    assert spell_target_level(foe) == 5
    assert spell_mr_penetration_level(foe) == 7
    hit, log, _ = resolve_spell_effect(wizard(), foe, show_rolls=True, label="Sleep")
    assert hit is False
    assert any("connect" in line.lower() for line in log)
    assert any("penetrate mr" in line.lower() for line in log)


def test_mr_two_step_succeeds_when_penetration_hits(monkeypatch) -> None:
    rolls = iter([(6, [6]), (6, [6])])
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda level: next(rolls))
    hit, log, _ = resolve_spell_effect(wizard(), necromancer(), show_rolls=True, label="Sleep")
    assert hit is True
    assert any("penetrate mr" in line.lower() for line in log)


def test_troll_regenerates_each_foe_round(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: (6, [6]))
    hero = PartyMemberState(
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
        inventory=["Hand weapon"],
    )
    beast = troll()
    assert enemy_has_regeneration(beast)
    result = resolve_combat_round(
        [hero],
        [beast],
        show_rolls=True,
        foe_phase_only=True,
        context=CombatContext(),
    )
    assert any("regenerates" in line.lower() for line in result.log)
    assert beast.life >= 4


def test_troll_regen_suppressed_by_fire() -> None:
    beast = troll()
    beast.life = 3
    combat.suppress_enemy_regeneration(beast)
    log: list[str] = []
    combat.tick_enemy_regeneration(beast, log, show_rolls=True)
    assert beast.life == 3
    assert any("cannot regenerate" in line.lower() for line in log)
    assert not beast.regen_suppressed
    log.clear()
    combat.tick_enemy_regeneration(beast, log, show_rolls=True)
    assert beast.life == 4
    assert any("regenerates" in line.lower() for line in log)


def test_troll_regen_suppressed_by_acid_damage() -> None:
    beast = troll()
    beast.life = 3
    combat.apply_enemy_damage(beast, 1, damage_kind="acid")
    assert beast.life == 2
    log: list[str] = []
    combat.tick_enemy_regeneration(beast, log, show_rolls=True)
    assert beast.life == 2
    assert any("cannot regenerate" in line.lower() for line in log)


def test_fireball_suppresses_troll_regeneration(monkeypatch) -> None:
    from app.engine import spells

    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda level: (6, [6]))
    caster = PartyMemberState(
        character_id="wiz",
        name="Marius",
        class_id="wizard",
        class_name="Wizard",
        level=5,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Fireball"],
    )
    beast = troll(life=6, max_life=7)
    spells.resolve_spell_cast("Fireball", caster, [caster], [beast], show_rolls=False)
    assert beast.life < 6
    assert beast.regen_suppressed
    log: list[str] = []
    combat.tick_enemy_regeneration(beast, log, show_rolls=True)
    assert beast.life < 7
    assert any("cannot regenerate" in line.lower() for line in log)


def test_lightning_suppresses_troll_regeneration(monkeypatch) -> None:
    from app.engine import spells

    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda level: (6, [6]))
    caster = PartyMemberState(
        character_id="wiz",
        name="Marius",
        class_id="wizard",
        class_name="Wizard",
        level=5,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Lightning"],
    )
    beast = troll(life=6, max_life=7)
    spells.resolve_spell_cast("Lightning", caster, [caster], [beast], show_rolls=False)
    assert beast.life < 6
    assert beast.regen_suppressed


def test_illusionary_fog_skips_foe_ranged(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: (6, [6]))
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
    kobold = EnemyState(
        id="kobold",
        name="Kobold Scout",
        category="minions",
        level=3,
        life=3,
        max_life=3,
        tags=["ranged", "javelin"],
    )
    result = resolve_combat_round(
        [hero],
        [kobold],
        show_rolls=True,
        party_attacked_immediately=True,
        encounter_round=0,
        context=CombatContext(illusionary_fog_active=True),
        missile_used=set(),
    )
    assert any("illusionary fog suspends" in line.lower() for line in result.log)
    assert all("foe ranged:" not in line.lower() for line in result.log)


def test_illusionary_fog_grants_flee_defense_bonus(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: (2, [2]))
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
    )
    foe = EnemyState(id="g", name="Goblin", category="minions", level=3, life=1, max_life=1)
    result = resolve_flee([hero], [foe], show_rolls=True, context=CombatContext(illusionary_fog_active=True))
    assert hero.current_life == 4
    assert any("defends" in line.lower() for line in result.log)


def test_illusionary_sword_ticks_down(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: (1, [1]))
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="illusionist",
        class_name="Illusionist",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon"],
        statuses=["Illusionary Sword (2 turns)"],
    )
    foe = EnemyState(id="g", name="Goblin", category="minions", level=3, life=3, max_life=3)
    resolve_combat_round([hero], [foe], show_rolls=False, context=CombatContext())
    assert any("Illusionary Sword (1 turns)" in status for status in hero.statuses)


def test_per_foe_reaction_tables_cover_bestiary() -> None:
    monsters_path = Path(__file__).resolve().parents[1] / "data" / "rules" / "monsters.json"
    reaction_tables = json.loads(monsters_path.read_text(encoding="utf-8"))["reaction_tables"]
    names = [
        "Slime Crawlers",
        "Iron Eater",
        "Living Statue",
        "Ooze",
        "Wight",
        "Chaos Champion",
        "Troll",
        "Necromancer",
    ]
    for name in names:
        source = resolve_reaction_source(
            [EnemyState(id="x", name=name, category="boss", level=5, life=5, max_life=5)],
            reaction_tables,
        )
        assert source.inline_rows, f"missing reaction table for {name}"


def test_illusionary_servant_flag(monkeypatch) -> None:
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda level: (6, [6]))
    caster = PartyMemberState(
        character_id="illus",
        name="Illusionist",
        class_id="illusionist",
        class_name="Illusionist",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Illusionary Servant"],
    )
    outcome = spells.resolve_spell_cast(
        "Illusionary Servant",
        caster,
        [caster],
        [],
        show_rolls=False,
        terrain="indoor",
    )
    assert outcome.illusionary_servant is True
