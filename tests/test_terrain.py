from __future__ import annotations

from app.engine import spells
from app.engine.terrain import resolve_play_context
from app.schemas import EnemyState, PartyMemberState


def _druid() -> PartyMemberState:
    return PartyMemberState(
        character_id="d1",
        name="Druid",
        class_id="druid",
        class_name="Druid",
        level=3,
        xp=0,
        gold=0,
        max_life=5,
        current_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        spells=["Entangle", "Lightning Strike", "Forest Pathway"],
    )


def _foe() -> EnemyState:
    return EnemyState(id="e1", name="Orc", category="minions", life=2, max_life=2, level=2)


def test_entangle_blocked_indoors() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Entangle",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="indoor",
    )
    assert not outcome.spell_consumed
    assert any("forest" in line.lower() for line in outcome.log)


def test_entangle_works_in_forest() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Entangle",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="forest",
    )
    assert outcome.spell_consumed


def test_lightning_strike_blocked_indoors() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Lightning Strike",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="indoor",
    )
    assert not outcome.spell_consumed
    assert any("indoors" in line.lower() for line in outcome.log)


def test_lightning_strike_works_outdoors() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Lightning Strike",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="outdoor",
    )
    assert outcome.spell_consumed


def test_forest_pathway_requires_woodland() -> None:
    druid = _druid()
    blocked = spells.resolve_spell_cast(
        "Forest Pathway",
        druid,
        [druid],
        [],
        show_rolls=False,
        terrain="outdoor",
    )
    assert not blocked.spell_consumed

    allowed = spells.resolve_spell_cast(
        "Forest Pathway",
        druid,
        [druid],
        [],
        show_rolls=False,
        terrain="jungle",
    )
    assert allowed.spell_consumed


def test_resolve_play_context_entrance_outdoor() -> None:
    from app.schemas import MapState, SessionState, TileState

    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        environment="dungeon",
        terrain="outdoor",
    )
    session = SessionState(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[tile], current_tile_id="t1"),
        environment="dungeon",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    ctx = resolve_play_context(tile, session)
    assert ctx.environment == "dungeon"
    assert ctx.terrain == "outdoor"
    assert ctx.outdoors
    assert ctx.lightning_strike_ok
    assert not ctx.entangle_ok


def test_resolve_play_context_forest_biome() -> None:
    from app.schemas import MapState, SessionState, TileState

    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Wood",
        description="Wood",
        terrain="forest",
        environment="dungeon",
    )
    session = SessionState(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[tile], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        alter_weather_active=True,
    )
    ctx = resolve_play_context(tile, session)
    assert ctx.entangle_ok
    assert ctx.forest_pathway_ok
    assert ctx.weather_active
    assert ctx.alter_weather_ok


def test_play_context_as_dict_for_api() -> None:
    ctx = resolve_play_context(None, None, terrain="jungle", environment="caverns")
    payload = ctx.as_dict()
    assert payload["environment"] == "caverns"
    assert payload["terrain"] == "jungle"
    assert payload["forest_pathway_ok"] is True
