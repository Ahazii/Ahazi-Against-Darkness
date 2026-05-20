from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def member(*, character_id: str, name: str, marching_order: int) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
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
        marching_order=marching_order,
    )


def exploration_session(party: list[PartyMemberState]) -> SessionState:
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=party,
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
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def test_set_marching_order_swaps_positions() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    party = [
        member(character_id="a", name="Alpha", marching_order=1),
        member(character_id="b", name="Bravo", marching_order=2),
        member(character_id="c", name="Charlie", marching_order=3),
        member(character_id="d", name="Delta", marching_order=4),
    ]
    session = exploration_session(party)
    engine.advance(session, "set_marching_order", character_id="d", marching_order=1)
    by_id = {item.character_id: item.marching_order for item in session.party}
    assert by_id["d"] == 1
    assert by_id["a"] == 4
    assert any("Delta moves from #4 to #1" in entry for entry in session.log)


def test_set_marching_order_blocked_in_combat() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    party = [member(character_id="a", name="Alpha", marching_order=1)]
    session = exploration_session(party)
    session.mode = "combat"
    session.map_state.tiles[0].enemies = [
        EnemyState(id="foe", name="Rat", category="vermin", level=1, life=1, max_life=1, attacks=1)
    ]
    engine.advance(session, "set_marching_order", character_id="a", marching_order=2)
    assert session.party[0].marching_order == 1
    assert any("during combat" in entry.lower() for entry in session.log)
