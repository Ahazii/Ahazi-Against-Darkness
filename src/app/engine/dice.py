from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .tier_advancement import (
    AdvancementPurpose,
    TierTraining,
    advancement_auto_success_naturals,
    advancement_roll_spec,
    effective_action_tier_band,
    level_tier_band,
    tier_die_sides_for_band,
    training_from_member,
)

if TYPE_CHECKING:
    from ..schemas import PartyMemberState


def roll_d6() -> int:
    return random.randint(1, 6)


def roll_d3() -> int:
    return random.randint(1, 3)


def roll_2d6() -> int:
    return roll_d6() + roll_d6()


def roll_tile_key() -> str:
    return f"{roll_d6()}{roll_d6()}"


def roll_start_tile_key() -> str:
    return f"0{roll_d6()}"


def tier_die_sides(level: int) -> int:
    """EE tier dice by hero level (Basic d6 … Epic d20)."""
    return tier_die_sides_for_band(level_tier_band(level))


def tier_die_sides_for_member(member: PartyMemberState) -> int:
    training = training_from_member(member)
    band = effective_action_tier_band(member.level, training)
    return tier_die_sides_for_band(band)


def tier_die_label(level: int) -> str:
    return f"d{tier_die_sides(level)}"


def explode_threshold(sides: int) -> int:
    """EE: d6→6, d8→7+, d10→8+, d12→9+, d20→10+."""
    if sides <= 6:
        return 6
    if sides == 8:
        return 7
    if sides == 10:
        return 8
    if sides == 12:
        return 9
    return 10


def roll_die(sides: int) -> int:
    return random.randint(1, max(1, sides))


def roll_exploding_die(sides: int) -> tuple[int, list[int]]:
    threshold = explode_threshold(sides)
    rolls = [roll_die(sides)]
    total = rolls[0]
    while rolls[-1] >= threshold:
        rolls.append(roll_die(sides))
        total += rolls[-1]
    return total, rolls


def roll_exploding_for_level(member_or_level: PartyMemberState | int) -> tuple[int, list[int]]:
    """Exploding action die: training tier when a PC is passed, level band when only level is known."""
    from ..schemas import PartyMemberState as _PartyMemberState

    if isinstance(member_or_level, _PartyMemberState):
        return roll_exploding_for_member(member_or_level)
    return roll_exploding_die(tier_die_sides(member_or_level))


def roll_exploding_for_member(member: PartyMemberState) -> tuple[int, list[int]]:
    return roll_exploding_die(tier_die_sides_for_member(member))


def roll_exploding_d6() -> tuple[int, list[int]]:
    return roll_exploding_die(6)


def roll_formula(formula: str) -> int:
    formula = formula.strip().lower().replace(" ", "")
    if formula.isdigit():
        return int(formula)
    if formula in {"d6", "1d6"}:
        return roll_d6()
    if formula in {"d3", "1d3"}:
        return roll_d3()

    match = re.fullmatch(r"(\d*)d([36])([+-]\d+)?", formula)
    if not match:
        raise ValueError(f"Unsupported dice formula: {formula}")
    count = int(match.group(1) or "1")
    sides = int(match.group(2))
    modifier = int(match.group(3) or "0")
    roller = roll_d6 if sides == 6 else roll_d3
    return sum(roller() for _ in range(count)) + modifier


@dataclass(frozen=True)
class AdvancementRollResult:
    natural: int
    total: int
    sides: int
    modifier: int = 0
    purpose: AdvancementPurpose = "level_up"
    tier_band: int = 1

    @property
    def die_label(self) -> str:
        if self.modifier:
            return f"d{self.sides}+{self.modifier}"
        return f"d{self.sides}"


def roll_advancement(
    level: int,
    *,
    training: TierTraining | None = None,
    member: PartyMemberState | None = None,
    purpose: AdvancementPurpose = "level_up",
    bonus: int = 0,
) -> AdvancementRollResult:
    if member is not None:
        training = training_from_member(member)
        level = member.level
    elif training is None:
        training = TierTraining()

    band = effective_action_tier_band(level, training)
    sides, modifier = advancement_roll_spec(level, training, purpose)
    natural = roll_die(sides)
    roll_mod = modifier + bonus
    return AdvancementRollResult(
        natural=natural,
        total=natural + roll_mod,
        sides=sides,
        modifier=roll_mod,
        purpose=purpose,
        tier_band=band,
    )


def advancement_roll_succeeds(result: AdvancementRollResult, level: int) -> bool:
    if result.natural in advancement_auto_success_naturals(result.sides):
        return True
    return result.total > level
