from __future__ import annotations

from itertools import cycle

from app.engine import combat
from app.engine.combat import CombatContext, resolve_combat_round
from app.engine.experience import tier_for_level
from app.engine.weapons import mushroom_monk_flurry_eligible
from app.schemas import EnemyState, PartyMemberState


def monk(*, level: int = 5, inventory: list[str] | None = None, default_melee: str | None = None) -> PartyMemberState:
    items = inventory if inventory is not None else ["Nunchaku"]
    return PartyMemberState(
        character_id="monk",
        name="Shiitake",
        class_id="mushroom_monk",
        class_name="Mushroom Monk",
        level=level,
        xp=0,
        gold=0,
        current_life=9,
        max_life=9,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=items,
        default_melee_weapon=default_melee if default_melee is not None else (items[0] if items else None),
    )


def orc(level: int = 4, life: int = 8) -> EnemyState:
    return EnemyState(
        id="orc",
        name="Orc",
        category="minions",
        level=level,
        life=life,
        max_life=life,
        attacks=1,
    )


def test_mushroom_monk_flurry_eligible_unarmed_and_nunchaku() -> None:
    assert mushroom_monk_flurry_eligible(monk(inventory=[], default_melee=None))
    assert mushroom_monk_flurry_eligible(monk(inventory=["Nunchaku"]))
    assert mushroom_monk_flurry_eligible(monk(inventory=["Throwing stars"]))
    assert not mushroom_monk_flurry_eligible(monk(inventory=["Staff"], default_melee="Staff"))


def test_mushroom_monk_flurry_resolves_tier_attacks(monkeypatch) -> None:
    tier = tier_for_level(5)
    rolls = cycle([(4, [4]), (1, [1])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: next(rolls))

    hero = monk(level=5)
    foe = orc(level=4, life=8)
    context = CombatContext(tile_type="room")

    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=True,
        context=context,
        party_phase_only=True,
    )

    attack_lines = [line for line in result.log if "Attack roll:" in line and hero.name in line]
    assert len(attack_lines) == tier
    assert any("Flurry of Blows" in line for line in result.log)


def test_mushroom_monk_staff_only_gets_one_attack(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: (6, [6]))

    hero = monk(level=5, inventory=["Staff"], default_melee="Staff")
    foe = orc(level=4, life=8)
    context = CombatContext(tile_type="room")

    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=True,
        context=context,
        party_phase_only=True,
    )

    attack_lines = [line for line in result.log if "Attack roll:" in line and hero.name in line]
    assert len(attack_lines) == 1
    assert not any("Flurry of Blows" in line for line in result.log)
