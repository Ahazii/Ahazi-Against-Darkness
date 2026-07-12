from __future__ import annotations

from app.engine.treasure_awards import abyss_group_treasure_roll_count, final_boss_summary_gold_cap
from app.schemas import EnemyState


def _enemy(name: str, tags: list[str]) -> EnemyState:
    return EnemyState(
        id=name.lower().replace(" ", "-"),
        name=name,
        category="minions",
        level=1,
        life=0,
        max_life=1,
        tags=tags,
    )


def test_abyss_group_treasure_rolls_do_not_scale_with_group_size() -> None:
    ratmen = [_enemy(f"Chaotic Ratmen {index}", ["abyss_treasure_rolls:2"]) for index in range(12)]
    for ratman in ratmen:
        ratman.name = "Chaotic Ratmen"

    assert abyss_group_treasure_roll_count(ratmen) == 2


def test_abyss_group_treasure_skips_a_no_treasure_leader() -> None:
    foes = [
        _enemy("Chaotic Ratmen", ["abyss_treasure_rolls:2"]),
        _enemy("Ratman Leader", ["abyss_treasure_rolls:2", "no_treasure"]),
    ]

    assert abyss_group_treasure_roll_count(foes) == 2


def test_final_boss_summary_gold_cap_uses_displayed_gp_total() -> None:
    assert final_boss_summary_gold_cap(
        is_final_boss=True,
        summary="Final Boss treasure: 330gp, Jewel",
    ) == 330
    assert final_boss_summary_gold_cap(is_final_boss=False, summary="Final Boss treasure: 330gp") is None
