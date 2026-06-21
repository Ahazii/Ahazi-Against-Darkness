from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _member(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="h1",
        name="Hero",
        class_id="rogue",
        class_name="Rogue",
        level=5,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        expert_trained=True,
        learned_expert_skills=["negotiator"],
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def _session(**kwargs) -> SessionState:
    enemy = EnemyState(id="e1", name="Goblin", category="minions", level=1, life=2, max_life=2, tags=[])
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        enemies=[enemy],
    )
    defaults = dict(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        mode="combat",
        party=[_member()],
        map_state=MapState(tiles=[tile], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        reaction_pending=True,
        combat_round=0,
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def test_negotiator_pauses_for_nudge() -> None:
    engine = _engine()
    session = _session()
    with patch("app.engine.random_dungeon.roll_d6", return_value=3):
        engine.advance(session, "check_reaction")
    assert session.reaction_nudge_pending
    assert session.reaction_pre_adjust_roll == 3
    assert not session.reaction_checked
    assert any("Nudge" in line for line in session.log)


def test_negotiator_nudge_applies_adjustment() -> None:
    engine = _engine()
    session = _session()
    with patch("app.engine.random_dungeon.roll_d6", return_value=3):
        engine.advance(session, "check_reaction")
    engine.advance(session, "check_reaction", reaction_adjust=1)
    assert not session.reaction_nudge_pending
    assert session.reaction_checked
    assert any("Negotiator adjusts" in line for line in session.log)
