"""Standalone Blossoms' Demesne adventure entry (Adventures list + FD portal gateway)."""

from __future__ import annotations

from app.engine.courtship_demesne import COURTSHIP_DEMESNE_ADVENTURE_ID, leave_courtship_demesne
from tests.test_forsaken_depths_engine import _party_member, engine


def test_create_courtship_demesne_session_starts_at_seaside() -> None:
    eng = engine()
    session = eng.create_courtship_demesne_session(
        "demesne-standalone",
        "party-1",
        [_party_member()],
    )
    assert session.adventure_id == COURTSHIP_DEMESNE_ADVENTURE_ID
    assert session.courtship_enabled
    assert session.courtship_demesne_active
    assert session.courtship_demesne_region == "seaside"
    assert session.courtship_entry_source == "standalone"
    assert session.courtship_return_tile_id == session.map_state.current_tile_id
    assert session.mode == "exploration"


def test_standalone_flower_portal_completes_adventure() -> None:
    eng = engine()
    session = eng.create_courtship_demesne_session(
        "demesne-leave",
        "party-1",
        [_party_member()],
    )
    assert leave_courtship_demesne(eng, session, show_rolls=False)
    assert not session.courtship_demesne_active
    assert session.mode == "complete"
    assert any("Blossoms' Demesne" in line for line in session.summary)


def test_flower_portal_leave_returns_to_norindaal_tile() -> None:
    eng = engine()
    session = eng.create_session(
        "fp-leave",
        "party-1",
        [_party_member()],
        ruleset="ee",
        courtship_enabled=True,
    )
    tile = eng._current_tile(session)
    assert tile is not None
    tile.terrain = "lake"
    session.courtship_demesne_active = True
    session.courtship_demesne_region = "riverside"
    session.courtship_entry_source = "flower_portal"
    session.courtship_return_tile_id = tile.id
    assert leave_courtship_demesne(eng, session, show_rolls=False)
    assert not session.courtship_demesne_active
    assert session.map_state.current_tile_id == tile.id
    assert session.mode == "exploration"


def test_fd_portal_leave_returns_to_depths() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-portal-leave",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    tile = session.map_state.tiles[0]
    session.courtship_demesne_active = True
    session.courtship_demesne_region = "seaside"
    session.courtship_return_tile_id = tile.id
    session.courtship_entry_source = "fd_portal"
    session.map_state.current_tile_id = tile.id

    assert leave_courtship_demesne(eng, session, show_rolls=False)
    assert not session.courtship_demesne_active
    assert session.mode == "exploration"
    assert session.map_state.current_tile_id == tile.id
