from __future__ import annotations

from app.engine import combat
from app.engine.combat import CombatContext, resolve_combat_round
from app.engine.weapons import light_gladiator_dual_pair, ranger_dual_wield_pair
from app.schemas import EnemyState, PartyMemberState


def ranger(level: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id="rng",
        name="Tracker",
        class_id="ranger",
        class_name="Ranger",
        level=level,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon", "Hand weapon"],
    )


def gladiator(level: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id="gla",
        name="Blade",
        class_id="light_gladiator",
        class_name="Light Gladiator",
        level=level,
        xp=0,
        gold=0,
        current_life=9,
        max_life=9,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Light hand weapon", "Light hand weapon"],
    )


def orc(level: int = 4, life: int = 4) -> EnemyState:
    return EnemyState(
        id="orc",
        name="Orc",
        category="minions",
        level=level,
        life=life,
        max_life=life,
        attacks=1,
    )


def test_ranger_dual_wield_pair_detects_two_hand_weapons() -> None:
    assert ranger_dual_wield_pair(ranger()) == ("Hand weapon", "Hand weapon")


def test_light_gladiator_dual_pair_detects_two_light_weapons() -> None:
    assert light_gladiator_dual_pair(gladiator()) == ("Light hand weapon", "Light hand weapon")


def test_ranger_dual_wield_resolves_two_attacks(monkeypatch) -> None:
    rolls = iter([(4, [4]), (5, [5])])
    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: next(rolls))

    hero = ranger(4)
    foe = orc(level=4, life=4)
    context = CombatContext(tile_type="room", outdoors=False)

    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=True,
        context=context,
    )

    assert foe.life < 4
    attack_lines = [line for line in result.log if "Attack roll:" in line and hero.name in line]
    assert len(attack_lines) == 2
    assert any("dual wield" in line for line in result.log)


def test_ranger_outdoor_bow_fires_twice(monkeypatch) -> None:
    rolls = iter([(4, [4]), (5, [5])])
    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: next(rolls))

    hero = ranger(4)
    hero.inventory = ["Bow", "Hand weapon"]
    hero.default_missile_weapon = "Bow"
    foe = orc(level=4, life=4)
    context = CombatContext(tile_type="room", outdoors=True)

    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=True,
        context=context,
        party_attacked_immediately=True,
        encounter_round=0,
    )

    missile_lines = [line for line in result.log if "Missile roll:" in line and hero.name in line]
    assert len(missile_lines) == 2
    assert any("outdoor bow" in line for line in result.log)


def test_light_gladiator_parry_skips_attacks_and_adds_defense(monkeypatch) -> None:
    attack_rolls = iter([(6, [6]), (6, [6])])
    defense_rolls = iter([(6, [6, 6])])
    monkeypatch.setattr(
        combat,
        "roll_exploding_d6",
        lambda: next(defense_rolls) if defense_rolls else next(attack_rolls),
    )

    hero = gladiator(4)
    foe = orc(level=3, life=4)
    context = CombatContext(tile_type="room", parrying_character_ids={hero.character_id})

    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=True,
        context=context,
    )

    assert not any("Attack roll:" in line and hero.name in line for line in result.log)
    assert any("parries instead of attacking" in line for line in result.log)
    assert hero.current_life == hero.max_life


def test_light_gladiator_counter_strike_banks_and_applies(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: (1, [1]))

    hero = gladiator(4)
    foe = orc(level=8, life=6)
    context = CombatContext(tile_type="room")

    round_one = resolve_combat_round([hero], [foe], show_rolls=True, context=context)
    assert not any("counter-strike" in line.lower() for line in round_one.log)

    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: (12, [6, 6]))
    round_one_defense = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=True,
        context=context,
        foe_phase_only=True,
    )
    assert any("counter-strike" in line.lower() for line in round_one_defense.log)
    pending = context.gladiator_counter_pending.get(hero.character_id)
    assert pending and pending["enemy_id"] == foe.id and int(pending["bonus"]) > 0

    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: (4, [4]))
    round_two = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=True,
        context=context,
        party_phase_only=True,
    )
    assert any("counter-strike" in line.lower() for line in round_two.log)
    assert hero.character_id in context.gladiator_counter_used
