from __future__ import annotations

from pathlib import Path

from app.engine.split_party import (
    detach_heroes,
    mixed_encounter,
    present_party,
    reattach_heroes,
    split_enemy_groups,
    split_party_ranks,
    wandering_check_detached_groups,
)
from app.schemas import DetachedGroupState, EnemyState, MapState, PartyMemberState, SessionState, TileState


def _member(cid: str, name: str, order: int) -> PartyMemberState:
    return PartyMemberState(
        character_id=cid,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=order,
    )


def _session(*, party: list[PartyMemberState], current: str = "t1", tiles: list[TileState] | None = None) -> SessionState:
    tile_list = tiles or [
        TileState(id="t1", x=0, y=0, tile_key="11", tile_type="room", title="Room A", description="A"),
        TileState(id="t2", x=1, y=0, tile_key="12", tile_type="room", title="Room B", description="B"),
    ]
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        party=party,
        map_state=MapState(tiles=tile_list, current_tile_id=current),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_detach_and_present_party() -> None:
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2), _member("c", "Gamma", 3)]
    session = _session(party=party)
    logs = detach_heroes(session, ["b"], reason="guard")
    assert any("Beta" in line for line in logs)
    assert len(present_party(session, "t1")) == 2
    assert len(present_party(session, "t2")) == 2


def test_reattach_on_same_tile() -> None:
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2)]
    session = _session(party=party)
    detach_heroes(session, ["b"])
    logs = reattach_heroes(session, ["b"])
    assert any("rejoin" in line.lower() for line in logs)
    assert len(present_party(session)) == 2
    assert not session.detached_groups


def test_mixed_encounter_splits_ranks() -> None:
    party = [_member("a", "A", 1), _member("b", "B", 2), _member("c", "C", 3), _member("d", "D", 4)]
    enemies = [
        EnemyState(id="boss", name="Ogre", category="boss", level=6, life=8, max_life=8),
        EnemyState(id="m1", name="Goblin", category="minions", level=3, life=2, max_life=2),
    ]
    assert mixed_encounter(enemies)
    front, rear = split_party_ranks(party)
    major, minor = split_enemy_groups(enemies)
    assert len(front) == 2
    assert len(rear) == 2
    assert len(major) == 1
    assert len(minor) == 1


def test_detached_wandering_roll(monkeypatch) -> None:
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2)]
    session = _session(party=party)
    session.detached_groups = [DetachedGroupState(tile_id="t2", character_ids=["b"], reason="guard")]
    monkeypatch.setattr("app.engine.split_party.roll_d6", lambda: 1)
    triggered, logs = wandering_check_detached_groups(session, show_rolls=True, exclude_tile_id="t1")
    assert triggered == ["t2"]
    assert logs
