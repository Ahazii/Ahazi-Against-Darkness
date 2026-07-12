from __future__ import annotations

from app.engine.treasure_awards import (
    abyss_group_treasure_roll_count,
    apply_secret_door_treasure_doubling,
    final_boss_summary_gold_cap,
    merge_treasure_outcomes,
)
from app.engine.dungeon_table_roller import TreasureOutcome
from app.schemas import EnemyState, TileState


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


def test_secret_door_treasure_doubling_applies_once_and_recognises_legacy_summary() -> None:
    tile = TileState(
        id="secret",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Secret room",
        description="",
        treasure_doubled=True,
        treasure_gold=50,
        treasure_summary="Treasure: 50gp",
    )

    assert apply_secret_door_treasure_doubling(tile) is True
    assert tile.treasure_gold == 100
    assert apply_secret_door_treasure_doubling(tile) is False
    assert tile.treasure_gold == 100

    legacy = tile.model_copy(update={"treasure_doubling_applied": False})
    assert apply_secret_door_treasure_doubling(legacy) is False
    assert legacy.treasure_gold == 100


def test_merge_treasure_outcomes_preserves_each_roll() -> None:
    merged = merge_treasure_outcomes(
        [
            TreasureOutcome("First", 10, ["Gem"], ["roll one"]),
            TreasureOutcome("Second", 20, ["Scroll"], ["roll two"]),
        ]
    )

    assert (merged.summary, merged.gold, merged.items, merged.log) == (
        "First; Second",
        30,
        ["Gem", "Scroll"],
        ["roll one", "roll two"],
    )
