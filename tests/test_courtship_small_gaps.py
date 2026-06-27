"""Small Courtship gaps — virile might breeding saves and Flower Portal water validation."""

from __future__ import annotations

import uuid

from app.engine.courtship_apothecary import (
    virile_might_breeding_save_bonus,
    virile_might_giving_roll_bonus,
)
from app.engine.courtship_blossoms_spells import flower_portal_destinations, resolve_flower_portal
from app.engine.courtship_demesne import resolve_courtship_woo_withholding
from app.engine.terrain import resolve_water_landscape
from app.schemas import ExitState, TileState
from tests.test_forsaken_depths_engine import _party_member, engine


def test_virile_might_breeding_and_giving_bonuses() -> None:
    member = _party_member()
    assert virile_might_breeding_save_bonus(member) == 0
    assert virile_might_giving_roll_bonus(member) == 0
    member.inventory.append("Pills of virile might")
    assert virile_might_breeding_save_bonus(member) == 1
    assert virile_might_giving_roll_bonus(member) == 3


def test_water_adjacent_neighbor_tile_allows_flower_portal() -> None:
    eng = engine()
    session = eng.create_session("water-adj", "party-1", [_party_member()], courtship_enabled=True)
    current = eng._current_tile(session)
    assert current is not None
    current.terrain = "outdoor"
    lake = TileState(
        id=uuid.uuid4().hex,
        x=1,
        y=0,
        tile_key="05",
        tile_type="corridor",
        title="Lake shore",
        description="Lake shore",
        terrain="lake",
        exits=[
            ExitState(
                direction="west",
                kind="passage",
                x=0,
                y=0,
                span=1,
                destination_tile_id=current.id,
            )
        ],
    )
    current.exits.append(
        ExitState(
            direction="east",
            kind="passage",
            x=0,
            y=0,
            span=1,
            destination_tile_id=lake.id,
        )
    )
    session.map_state.tiles.append(lake)
    ok, reason = resolve_water_landscape(session, current, eng)
    assert ok
    assert reason == "adjacent_water_terrain"
    assert "enter_demesne" in flower_portal_destinations(session, current, eng)


def test_indoor_tile_without_water_blocks_flower_portal_enter() -> None:
    eng = engine()
    session = eng.create_session("no-water", "party-1", [_party_member()], courtship_enabled=True)
    tile = eng._current_tile(session)
    assert tile is not None
    tile.terrain = "indoor"
    ok, reason = resolve_water_landscape(session, tile, eng)
    assert not ok
    assert reason == "no_water"
    assert not resolve_flower_portal(
        eng,
        session,
        session.party[0],
        tile,
        destination="enter_demesne",
        show_rolls=False,
        from_scroll=True,
    )


def test_fd_river_bank_counts_as_water_adjacent() -> None:
    eng = engine()
    session = eng.create_session(
        "river-bank",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    tile = eng._current_tile(session)
    assert tile is not None
    tile.terrain = "indoor"
    tile.walkable = ["12"]
    tile.footprint_width = 2
    tile.footprint_height = 1
    ok, reason = resolve_water_landscape(session, tile, eng)
    assert ok
    assert reason == "fd_river_bank"


def test_virile_might_withholding_gets_breeding_bonus() -> None:
    eng = engine()
    member = _party_member()
    member.inventory.append("Pills of virile might")
    session = eng.create_courtship_demesne_session("withhold", "party-1", [member])
    session.courtship_woo_active = True
    session.courtship_woo_speaker_id = member.character_id
    session.courtship_woo_template = "Giggling Gingers"
    from unittest.mock import patch

    with patch("app.engine.class_abilities.roll_exploding_for_level", return_value=(10, [5, 5])):
        resolve_courtship_woo_withholding(eng, session, show_rolls=False)
    assert session.courtship_virile_might_character_id == member.character_id
