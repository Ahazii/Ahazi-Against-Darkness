from __future__ import annotations

from pathlib import Path

from app.engine import combat
from app.engine.combat import resolve_combat_round
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def member(*, class_id: str = "wizard", attack_bonus: int = 0) -> PartyMemberState:
    return PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id=class_id,
        class_name=class_id.title(),
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=attack_bonus,
        defense_bonus=0,
        save_bonus=0,
    )


def enemy() -> EnemyState:
    return EnemyState(
        id="rat",
        name="Rat",
        category="vermin",
        level=3,
        life=1,
        max_life=1,
        attacks=1,
    )


def test_combat_round_can_trace_rolls_and_math(monkeypatch) -> None:
    outcomes = iter([(2, [2]), (1, [1])])
    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: next(outcomes))

    result = resolve_combat_round([member()], [enemy()], show_rolls=True, explain_math=True)

    assert any("Attack roll: Hero vs Rat: 2 + 0 = 2." in entry for entry in result.log)
    assert any("Attack math: need total >= enemy level 3 to hit." in entry for entry in result.log)
    assert any("Defense roll: Hero vs Rat: 1 + 0 = 1." in entry for entry in result.log)
    assert any("Defense math: need total > enemy level 3 to avoid damage." in entry for entry in result.log)
    assert result.party[0].current_life == 2


def test_random_engine_marks_fallen_hero_on_current_tile(monkeypatch) -> None:
    hero = member()
    hero.current_life = 1
    foe = enemy()
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[foe],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    outcomes = iter([(2, [2]), (1, [1])])
    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: next(outcomes))

    RandomDungeonEngine(rules=None, asset_dir=Path())._combat_round(session)

    tile = session.map_state.tiles[0]
    assert hero.character_id in tile.fallen_character_ids
    assert any("falls" in entry for entry in session.log)


def test_random_engine_records_defeated_enemies_on_current_tile(monkeypatch) -> None:
    hero = member(class_id="warrior")
    foe = enemy()
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[foe],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    monkeypatch.setattr(combat, "roll_exploding_d6", lambda: (6, [6]))

    RandomDungeonEngine(rules=None, asset_dir=Path())._combat_round(session)

    tile = session.map_state.tiles[0]
    assert [enemy.id for enemy in tile.defeated_enemies] == ["rat"]
    assert tile.enemies == []
    assert session.mode == "exploration"
