from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import ExitState, MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def test_dungeon_exit_with_fallen_retreats() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        exits=[
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            )
        ],
    )
    deep = TileState(
        id="deep",
        x=0,
        y=1,
        tile_key="11",
        tile_type="room",
        title="Deep",
        description="Deep",
        fallen_character_ids=["h2"],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Alive",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            ),
            PartyMemberState(
                character_id="h2",
                name="Fallen",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=0,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Magic sword"],
            ),
        ],
        map_state=MapState(tiles=[entrance, deep], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "explore", exit_id="out")
    assert session.mode == "exploration"
    assert session.camped_outside is True
    assert session.map_state.current_tile_id == "ent"
    assert len(session.map_state.tiles) == 2


def test_dungeon_exit_without_fallen_completes() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        exits=[
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            )
        ],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Alive",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            ),
        ],
        map_state=MapState(tiles=[entrance], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "explore", exit_id="out")
    assert session.mode == "complete"
    assert session.camped_outside is False
