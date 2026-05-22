from __future__ import annotations

from app.engine.dice import (
    AdvancementRollResult,
    advancement_roll_succeeds,
    explode_threshold,
    roll_advancement,
    roll_exploding_die,
    roll_exploding_for_level,
    roll_exploding_for_member,
    tier_die_sides,
    tier_die_sides_for_member,
)
from app.engine.experience import advancement_succeeds, perform_advancement_roll
from app.engine.tier_advancement import (
    TierTraining,
    advancement_roll_spec,
    effective_action_tier_band,
    level_up_gate_reason,
)
from app.schemas import PartyMemberState


def _member(level: int, **flags: bool) -> PartyMemberState:
    return PartyMemberState(
        character_id="x",
        name="Hero",
        class_id="fighter",
        class_name="Fighter",
        level=level,
        xp=0,
        gold=1000,
        current_life=1,
        max_life=1,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        **flags,
    )


def test_tier_die_sides_by_level() -> None:
    assert tier_die_sides(1) == 6
    assert tier_die_sides(4) == 6
    assert tier_die_sides(5) == 8
    assert tier_die_sides(9) == 8
    assert tier_die_sides(10) == 10
    assert tier_die_sides(20) == 20


def test_explode_thresholds() -> None:
    assert explode_threshold(6) == 6
    assert explode_threshold(8) == 7
    assert explode_threshold(10) == 8


def test_roll_exploding_d8_can_chain() -> None:
    total, rolls = roll_exploding_die(8)
    assert len(rolls) >= 1
    assert total == sum(rolls)


def test_expert_tier_advancement_natural_eight_succeeds() -> None:
    result = AdvancementRollResult(natural=8, total=10, sides=8, modifier=2)
    assert advancement_roll_succeeds(result, 9)
    assert advancement_succeeds(result, 9)


def test_expert_tier_advancement_total_beats_level() -> None:
    result = AdvancementRollResult(natural=5, total=7, sides=8, modifier=2)
    assert advancement_roll_succeeds(result, 6)
    assert not advancement_roll_succeeds(result, 7)


def test_basic_tier_advancement_six_always_succeeds() -> None:
    result = AdvancementRollResult(natural=6, total=6, sides=6, modifier=0)
    assert advancement_roll_succeeds(result, 5)


def test_heroic_tier_advancement_at_level_eleven() -> None:
    member = _member(11, heroic_trained=True)
    sides, modifier = advancement_roll_spec(member.level, TierTraining(heroic_trained=True), "level_up")
    assert sides == 10
    assert modifier == 4
    result = AdvancementRollResult(natural=10, total=14, sides=10, modifier=4)
    assert advancement_roll_succeeds(result, 11)


def test_legendary_tier_advancement_at_level_sixteen() -> None:
    member = _member(16, heroic_trained=True, legendary_trained=True)
    sides, modifier = advancement_roll_spec(
        member.level,
        TierTraining(heroic_trained=True, legendary_trained=True),
        "level_up",
    )
    assert sides == 12
    assert modifier == 8


def test_heroic_l9_uses_d10_action_die() -> None:
    member = _member(9, expert_trained=True, heroic_trained=True)
    assert tier_die_sides_for_member(member) == 10
    assert effective_action_tier_band(member.level, TierTraining(expert_trained=True, heroic_trained=True)) == 3


def test_perform_advancement_roll_shape() -> None:
    member = _member(6, expert_trained=True)
    result = perform_advancement_roll(member)
    assert result.sides == 8
    assert result.modifier == 2
    assert result.total == result.natural + 2


def test_roll_exploding_for_level_uses_tier_die() -> None:
    _, rolls = roll_exploding_for_level(7)
    for value in rolls:
        assert 1 <= value <= 8


def test_level_up_gate_blocks_l9_without_heroic_training() -> None:
    member = _member(9, expert_trained=True)
    assert level_up_gate_reason(member, 10) is not None


def test_level_up_gate_allows_l9_with_heroic_training() -> None:
    member = _member(9, expert_trained=True, heroic_trained=True)
    assert level_up_gate_reason(member, 10) is None
