from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AdvancementPurpose = Literal[
    "level_up",
    "learn_expert_skill",
    "learn_heroic_skill",
    "learn_legendary_skill",
]

# Forsaken Depths summary table (p.9) + Abyss expert entry (500 gp or 1 XP).
TIER_ENTRY = {
    "expert": {"min_level": 5, "gold": 500, "xp": 0, "xp_alt": 1},
    "heroic": {"min_level": 9, "gold": 1000, "xp": 2, "requires": "expert"},
    "legendary": {"min_level": 14, "gold": 2000, "xp": 3, "requires": "heroic"},
    "epic": {"min_level": 19, "gold": 4000, "xp": 5, "requires": "legendary"},
}

# (tier_band, purpose) -> (die_sides, modifier)
_ADVANCEMENT_ROLLS: dict[tuple[int, AdvancementPurpose], tuple[int, int]] = {
    (1, "level_up"): (6, 0),
    (2, "level_up"): (8, 2),
    (2, "learn_expert_skill"): (8, 2),
    (3, "level_up"): (10, 4),
    (3, "learn_expert_skill"): (10, 5),
    (3, "learn_heroic_skill"): (10, 4),
    (4, "level_up"): (12, 8),
    (4, "learn_expert_skill"): (12, 10),
    (4, "learn_heroic_skill"): (12, 9),
    (4, "learn_legendary_skill"): (12, 8),
    (5, "level_up"): (20, 10),
    (5, "learn_expert_skill"): (20, 13),
    (5, "learn_heroic_skill"): (20, 12),
    (5, "learn_legendary_skill"): (20, 11),
}

_BAND_DIE_SIDES = {1: 6, 2: 8, 3: 10, 4: 12, 5: 20}


@dataclass(frozen=True)
class TierTraining:
    expert_trained: bool = False
    heroic_trained: bool = False
    legendary_trained: bool = False
    epic_trained: bool = False


def level_tier_band(level: int) -> int:
    level = max(1, level)
    if level <= 4:
        return 1
    if level <= 9:
        return 2
    if level <= 14:
        return 3
    if level <= 19:
        return 4
    return 5


def tier_die_sides_for_band(band: int) -> int:
    return _BAND_DIE_SIDES.get(max(1, min(5, band)), 6)


def training_from_member(member) -> TierTraining:
    """Read tier flags; infer trained tiers for legacy heroes already past gates."""
    level = max(1, getattr(member, "level", 1))
    expert = bool(getattr(member, "expert_trained", False)) or level >= 5
    heroic = bool(getattr(member, "heroic_trained", False)) or level >= 10
    legendary = bool(getattr(member, "legendary_trained", False)) or level >= 15
    epic = bool(getattr(member, "epic_trained", False)) or level >= 20
    return TierTraining(
        expert_trained=expert,
        heroic_trained=heroic,
        legendary_trained=legendary,
        epic_trained=epic,
    )


def effective_action_tier_band(level: int, training: TierTraining) -> int:
    """Action/advancement tier from level and training flags (Heroic L9 uses d10)."""
    floor = 1
    if training.expert_trained:
        floor = max(floor, 2)
    if training.heroic_trained:
        floor = max(floor, 3)
    if training.legendary_trained:
        floor = max(floor, 4)
    if training.epic_trained:
        floor = max(floor, 5)
    return max(level_tier_band(level), floor)


def advancement_roll_spec(
    level: int,
    training: TierTraining,
    purpose: AdvancementPurpose = "level_up",
) -> tuple[int, int]:
    band = effective_action_tier_band(level, training)
    if purpose != "level_up" and (band, purpose) not in _ADVANCEMENT_ROLLS:
        raise ValueError(f"{purpose} is not available at tier band {band}.")
    sides, modifier = _ADVANCEMENT_ROLLS.get((band, purpose), _ADVANCEMENT_ROLLS[(band, "level_up")])
    return sides, modifier


def advancement_auto_success_naturals(sides: int) -> frozenset[int]:
    if sides <= 6:
        return frozenset({6})
    if sides == 8:
        return frozenset({7, 8})
    if sides == 10:
        return frozenset({9, 10})
    if sides == 12:
        return frozenset({11, 12})
    return frozenset({19, 20})


def tier_band_name(band: int) -> str:
    return {1: "Basic", 2: "Expert", 3: "Heroic", 4: "Legendary", 5: "Epic"}.get(band, "Basic")


def level_up_gate_reason(member, target_level: int) -> str | None:
    training = training_from_member(member)
    if target_level >= 10 and not training.heroic_trained and getattr(member, "level", 0) < 10:
        return (
            f"{member.name} needs Heroic training (1000 gp + 2 banked XP) before reaching Level 10."
        )
    if target_level >= 15 and not training.legendary_trained and getattr(member, "level", 0) < 15:
        return (
            f"{member.name} needs Legendary training (2000 gp + 3 banked XP) before reaching Level 15."
        )
    if target_level >= 20 and not training.epic_trained and getattr(member, "level", 0) < 20:
        return (
            f"{member.name} needs Epic training (4000 gp + 5 banked XP) before reaching Level 20."
        )
    return None


def tier_training_label(member) -> str:
    training = training_from_member(member)
    parts: list[str] = []
    if training.expert_trained:
        parts.append("Expert")
    if training.heroic_trained:
        parts.append("Heroic")
    if training.legendary_trained:
        parts.append("Legendary")
    if training.epic_trained:
        parts.append("Epic")
    return ", ".join(parts) if parts else "Basic"
