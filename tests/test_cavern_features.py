from __future__ import annotations

from app.engine.cavern_features import (
    boulder_surprise_triggers,
    cavern_blocks_pc_attack_explode,
    cavern_pc_ranged_attack_modifier,
    cavern_stealth_modifier,
    echo_spell_repeats,
    wandering_check_triggers,
)
from app.schemas import EnemyState


def test_stalagmites_block_pc_attack_explode() -> None:
    assert cavern_blocks_pc_attack_explode("stalagmites") is True
    assert cavern_blocks_pc_attack_explode("echo") is False


def test_boulders_modify_ranged_attack_and_stealth() -> None:
    assert cavern_pc_ranged_attack_modifier("boulders", missile=True) == -1
    assert cavern_pc_ranged_attack_modifier("boulders", missile=False) == 0
    assert cavern_stealth_modifier("boulders") == 1
    assert cavern_stealth_modifier("echo") == -1


def test_echo_wandering_is_two_in_six(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.cavern_features.roll_d6", lambda: 2)
    triggered, roll = wandering_check_triggers("echo")
    assert triggered is True
    assert roll == 2


def test_boulder_surprise_requires_tagged_foe() -> None:
    triggered, _ = boulder_surprise_triggers(
        "boulders",
        [EnemyState(id="1", name="Bat", category="vermin", level=1, life=1, max_life=1, tags=[])],
    )
    assert triggered is False


def test_echo_spell_repeat_on_six(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.cavern_features.roll_d6", lambda: 6)
    repeat, roll = echo_spell_repeats("echo", echo_repeat=False)
    assert repeat is True
    assert roll == 6
