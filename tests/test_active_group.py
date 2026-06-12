"""Tests for active group switching — detached group navigation (EE p.105)."""
from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.split_party import active_tile_id, is_active_detached, set_active_group
from app.rules.repository import RulesRepository
from app.schemas import (
    DetachedGroupState,
    ExitState,
    MapState,
    PartyMemberState,
    SessionState,
    TileState,
)


def _rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def _engine() -> RandomDungeonEngine:
    root = Path(__file__).resolve().parents[1]
    return RandomDungeonEngine(_rules(), root / "assets")


def _member(cid: str, name: str, order: int, *, level: int = 3, life: int = 5) -> PartyMemberState:
    return PartyMemberState(
        character_id=cid,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=level,
        xp=0,
        gold=10,
        current_life=life,
        max_life=life,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=order,
    )


def _tile(tid: str, x: int = 0, y: int = 0, exits: list[ExitState] | None = None) -> TileState:
    return TileState(
        id=tid, x=x, y=y, tile_key="11", tile_type="room",
        title=f"Room {tid}", description="A room",
        exits=exits or [],
    )


def _exit(eid: str, direction: str, dest_id: str | None = None) -> ExitState:
    return ExitState(
        id=eid, direction=direction, kind="passage", status="open",
        destination_tile_id=dest_id,
    )


def _door_exit(eid: str, direction: str) -> ExitState:
    return ExitState(
        id=eid, direction=direction, kind="door", status="open", door_open=True,
    )


def _session_with_detached(
    *,
    active_group_tile_id: str | None = None,
) -> SessionState:
    """Two tiles; heroes split: h1+h2 on t1 (main), h3+h4 detached on t2."""
    t1_exit = _exit("e1", "north", "t2")
    t2_exit = _exit("e2", "south", "t1")
    t1 = _tile("t1", exits=[t1_exit])
    t2 = _tile("t2", y=3, exits=[t2_exit])
    party = [
        _member("h1", "Halvar", 1),
        _member("h2", "Brynn", 2),
        _member("h3", "Sela", 3),
        _member("h4", "Drex", 4),
    ]
    session = SessionState(
        id="s1", party_id="p1", adventure_id="a1", adventure_type="random",
        mode="exploration", party=party,
        map_state=MapState(tiles=[t1, t2], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    session.detached_groups = [
        DetachedGroupState(tile_id="t2", character_ids=["h3", "h4"], reason="guard")
    ]
    if active_group_tile_id:
        session.active_group_tile_id = active_group_tile_id
    return session


# ---------------------------------------------------------------------------
# active_tile_id helper
# ---------------------------------------------------------------------------

def test_active_tile_id_defaults_to_current() -> None:
    session = _session_with_detached()
    assert active_tile_id(session) == "t1"


def test_active_tile_id_returns_detached_when_set() -> None:
    session = _session_with_detached(active_group_tile_id="t2")
    assert active_tile_id(session) == "t2"


def test_active_tile_id_resets_if_group_dissolved() -> None:
    session = _session_with_detached(active_group_tile_id="t2")
    session.detached_groups = []
    # Should fall back and clear the stale field
    result = active_tile_id(session)
    assert result == "t1"
    assert session.active_group_tile_id is None


def test_is_active_detached_false_when_main() -> None:
    session = _session_with_detached()
    assert not is_active_detached(session)


def test_is_active_detached_true_when_detached_active() -> None:
    session = _session_with_detached(active_group_tile_id="t2")
    assert is_active_detached(session)


# ---------------------------------------------------------------------------
# set_active_group
# ---------------------------------------------------------------------------

def test_set_active_group_switches_to_detached() -> None:
    session = _session_with_detached()
    log = set_active_group(session, "t2")
    assert session.active_group_tile_id == "t2"
    assert any("active" in line.lower() or "navigat" in line.lower() for line in log)


def test_set_active_group_clears_to_main() -> None:
    session = _session_with_detached(active_group_tile_id="t2")
    log = set_active_group(session, None)
    assert session.active_group_tile_id is None
    assert any("main" in line.lower() for line in log)


def test_set_active_group_blocked_in_combat() -> None:
    session = _session_with_detached()
    session.mode = "combat"
    log = set_active_group(session, "t2")
    assert session.active_group_tile_id is None
    assert any("exploration" in line.lower() for line in log)


def test_set_active_group_fails_for_unknown_tile() -> None:
    session = _session_with_detached()
    log = set_active_group(session, "t99")
    assert session.active_group_tile_id is None
    assert any("no detached" in line.lower() for line in log)


# ---------------------------------------------------------------------------
# Engine advance: set_active_group action
# ---------------------------------------------------------------------------

def test_advance_set_active_group() -> None:
    engine = _engine()
    session = _session_with_detached()
    engine.advance(session, action="set_active_group", detached_tile_id="t2")
    assert session.active_group_tile_id == "t2"
    assert any("active" in line.lower() or "navigat" in line.lower() for line in session.log)


def test_advance_set_active_group_to_main() -> None:
    engine = _engine()
    session = _session_with_detached(active_group_tile_id="t2")
    engine.advance(session, action="set_active_group", detached_tile_id=None)
    assert session.active_group_tile_id is None


# ---------------------------------------------------------------------------
# Engine advance: detached group moves (explore action)
# ---------------------------------------------------------------------------

def test_detached_group_moves_to_existing_tile() -> None:
    engine = _engine()
    session = _session_with_detached(active_group_tile_id="t2")
    # t2 has south exit back to t1
    engine.advance(session, action="explore", exit_id="e2")
    # Detached group should now be on t1 (same as main party)
    assert session.active_group_tile_id == "t1"
    group = next((g for g in session.detached_groups if "h3" in g.character_ids), None)
    assert group is not None
    assert group.tile_id == "t1"
    # Main party's tile must not change
    assert session.map_state.current_tile_id == "t1"
    assert any("detached" in line.lower() for line in session.log)


def test_main_party_tile_unchanged_when_detached_moves() -> None:
    engine = _engine()
    session = _session_with_detached(active_group_tile_id="t2")
    engine.advance(session, action="explore", exit_id="e2")
    assert session.map_state.current_tile_id == "t1"


def test_detached_group_cannot_use_dungeon_exit() -> None:
    engine = _engine()
    dungeon_exit = ExitState(id="de1", direction="west", kind="passage", status="open", dungeon_exit=True)
    t2 = _tile("t2", y=3, exits=[dungeon_exit])
    t1_exit = _exit("e1", "north", "t2")
    t1 = _tile("t1", exits=[t1_exit])
    session = SessionState(
        id="s1", party_id="p1", adventure_id="a1", adventure_type="random",
        mode="exploration",
        party=[_member("h1", "Halvar", 1), _member("h2", "Brynn", 2),
               _member("h3", "Sela", 3), _member("h4", "Drex", 4)],
        map_state=MapState(tiles=[t1, t2], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )
    session.detached_groups = [DetachedGroupState(tile_id="t2", character_ids=["h3", "h4"])]
    session.active_group_tile_id = "t2"
    engine.advance(session, action="explore", exit_id="de1")
    # Session should NOT complete and tile should not change
    assert session.mode != "complete"
    assert session.map_state.current_tile_id == "t1"
    assert any("cannot exit" in line.lower() or "independently" in line.lower() for line in session.log)


# ---------------------------------------------------------------------------
# Encounter when detached group enters a room with enemies
# ---------------------------------------------------------------------------

def test_detached_group_encounter_queued_as_detached_pending() -> None:
    from app.schemas import EnemyState
    engine = _engine()
    enemy = EnemyState(id="en1", name="Goblin", category="minions", level=1, life=2, max_life=2, attacks=1)
    # Three tiles: main at t1, detached at t2, enemy-filled t3 reachable from t2
    t2_to_t3 = _exit("ex23", "north", "t3")
    t3_to_t2 = _exit("ex32", "south", "t2")
    t1 = _tile("t1")
    t2 = _tile("t2", y=3, exits=[t2_to_t3])
    t3 = _tile("t3", y=6, exits=[t3_to_t2])
    t3.enemies = [enemy]
    session = SessionState(
        id="s1", party_id="p1", adventure_id="a1", adventure_type="random",
        mode="exploration",
        party=[_member("h1", "Halvar", 1), _member("h2", "Brynn", 2),
               _member("h3", "Sela", 3), _member("h4", "Drex", 4)],
        map_state=MapState(tiles=[t1, t2, t3], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )
    session.detached_groups = [DetachedGroupState(tile_id="t2", character_ids=["h3", "h4"])]
    session.active_group_tile_id = "t2"
    # Move detached group from t2 to t3 (which has enemies)
    engine.advance(session, action="explore", exit_id="ex23")
    assert "t3" in session.detached_wandering_pending
    assert session.mode == "exploration"  # Main party not in combat
    assert session.map_state.current_tile_id == "t1"


# ---------------------------------------------------------------------------
# Reattach resets active_group_tile_id
# ---------------------------------------------------------------------------

def test_reattach_resets_active_group() -> None:
    engine = _engine()
    session = _session_with_detached(active_group_tile_id="t2")
    # Move detached back to t1 so they can reattach
    group = session.detached_groups[0]
    group.tile_id = "t1"
    session.active_group_tile_id = None  # reset nav to main
    engine.advance(session, action="reattach_heroes")
    assert session.active_group_tile_id is None
    assert not session.detached_groups


# ---------------------------------------------------------------------------
# UI: active group functions present in app.js
# ---------------------------------------------------------------------------

def test_active_group_ui_functions_present() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "src" / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function activeTileId(" in app_js
    assert "function activeTile(" in app_js
    assert "function isActiveDetached(" in app_js
    assert "active-group-btn" in app_js
    assert "set_active_group" in app_js
    assert "Navigate" in app_js
