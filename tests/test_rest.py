from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.rest import (
    consume_nail_bags,
    member_has_recoverable_ability,
    nailable_doors,
    recover_ability,
    rest_eligibility,
    tile_is_cleared,
    validate_rest_request,
)
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, ExitState, MapState, PartyMemberState, SessionState, TileState


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def dungeon_engine() -> RandomDungeonEngine:
    return RandomDungeonEngine(packaged_rules(), Path())


def hero(*, life: int = 2, max_life: int = 5, spells: list[str] | None = None) -> PartyMemberState:
    return PartyMemberState(
        character_id="h1",
        name="Hero",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=life,
        max_life=max_life,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=spells or ["Sleep"],
    )


def door_exit(*, direction: str = "north", destination: str = "adj") -> ExitState:
    return ExitState(
        id=f"exit-{direction}",
        direction=direction,
        kind="door",
        destination_tile_id=destination,
        status="blocked",
    )


def room_tile(*, tile_id: str = "room", enemies: list[EnemyState] | None = None, exits: list[ExitState] | None = None) -> TileState:
    return TileState(
        id=tile_id,
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        enemies=enemies or [],
        exits=exits or [door_exit()],
    )


def session_with(*, tile: TileState, party: list[PartyMemberState] | None = None, **kwargs) -> SessionState:
    adj = room_tile(tile_id="adj", exits=[door_exit(direction="south", destination=tile.id)])
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=party or [hero()],
        map_state=MapState(tiles=[tile, adj], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        **kwargs,
    )


def test_rest_requires_cleared_room_with_doors() -> None:
    tile = room_tile(enemies=[EnemyState(id="1", name="Rat", category="vermin", level=1, life=1, max_life=1)])
    session = session_with(tile=tile)
    ok, reason = rest_eligibility(session, tile)
    assert not ok
    assert "cleared" in reason.lower()


def test_rest_requires_cleared_adjacent_tiles() -> None:
    tile = room_tile()
    uncleared = room_tile(
        tile_id="adj",
        enemies=[EnemyState(id="1", name="Rat", category="vermin", level=1, life=1, max_life=1)],
        exits=[door_exit(direction="south", destination=tile.id)],
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[hero()],
        map_state=MapState(tiles=[tile, uncleared], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    ok, reason = rest_eligibility(session, tile)
    assert not ok
    assert "adjacent" in reason.lower()


def test_consume_nail_bags() -> None:
    member = hero()
    member.inventory = ["Bag of nails", "Bag of nails"]
    assert consume_nail_bags([member], 2)
    assert member.inventory == []


def test_recover_expended_spell() -> None:
    member = hero(max_life=5, life=5)
    session = session_with(tile=room_tile(), party=[member], expended_spells={"h1": ["Sleep"]})
    assert member_has_recoverable_ability(session, member)
    message = recover_ability(session, member)
    assert message is not None
    assert session.expended_spells["h1"] == []


def test_rest_with_foes_does_not_start_combat() -> None:
    eng = dungeon_engine()
    tile = room_tile(
        enemies=[EnemyState(id="1", name="Scorpions", category="vermin", level=4, life=1, max_life=1)],
    )
    session = session_with(tile=tile)
    eng.advance(session, "rest", rest_choices={"h1": "life"})
    assert session.mode == "exploration"
    assert any("cleared" in line.lower() for line in session.log)
    assert not any("Foes are still here" in line for line in session.log)


def test_rest_once_per_adventure() -> None:
    eng = dungeon_engine()
    tile = room_tile()
    session = session_with(tile=tile, rest_used=True)
    eng.advance(session, "rest", rest_choices={"h1": "life"})
    assert any("already rested" in line.lower() for line in session.log)


def test_rest_recovers_life_and_rolls_wanderers(monkeypatch: pytest.MonkeyPatch) -> None:
    eng = dungeon_engine()
    tile = room_tile()
    member = hero(life=2, max_life=5)
    session = session_with(tile=tile, party=[member])
    monkeypatch.setattr("app.engine.random_dungeon.wandering_roll_triggers", lambda: (False, 4))
    eng.advance(session, "rest", rest_choices={"h1": "life"})
    assert member.current_life == 3
    assert session.rest_used
    assert any("undisturbed" in line.lower() for line in session.log)


def test_rest_with_nails_sets_party_first_on_wanderers(monkeypatch: pytest.MonkeyPatch) -> None:
    eng = dungeon_engine()
    tile = room_tile()
    member = hero(life=2, max_life=5)
    member.inventory = ["Bag of nails"]
    session = session_with(tile=tile, party=[member])
    monkeypatch.setattr("app.engine.random_dungeon.wandering_roll_triggers", lambda: (True, 1))
    monkeypatch.setattr(
        "app.engine.random_dungeon.RandomDungeonEngine._roll_wandering_enemies",
        lambda self, session, category, hcl: [
            EnemyState(id="w1", name="Goblin", category="minions", level=2, life=1, max_life=1)
        ],
    )
    eng.advance(session, "rest", nail_doors=True, rest_choices={"h1": "life"})
    assert session.mode == "combat"
    assert session.party_attacked_immediately
    assert not session.foes_strike_first
    assert tile.exits[0].nailed_shut


def test_rest_without_nails_foes_strike_first(monkeypatch: pytest.MonkeyPatch) -> None:
    eng = dungeon_engine()
    tile = room_tile()
    member = hero(life=2, max_life=5)
    session = session_with(tile=tile, party=[member])
    monkeypatch.setattr("app.engine.random_dungeon.wandering_roll_triggers", lambda: (True, 1))
    monkeypatch.setattr(
        "app.engine.random_dungeon.RandomDungeonEngine._roll_wandering_enemies",
        lambda self, session, category, hcl: [
            EnemyState(id="w1", name="Goblin", category="minions", level=2, life=1, max_life=1)
        ],
    )
    eng.advance(session, "rest", nail_doors=False, rest_choices={"h1": "life"})
    assert session.mode == "combat"
    assert session.foes_strike_first


def test_tile_is_cleared() -> None:
    tile = room_tile(enemies=[EnemyState(id="1", name="Rat", category="vermin", level=1, life=0, max_life=1)])
    assert tile_is_cleared(tile)


def test_validate_rest_requires_nails_when_requested() -> None:
    tile = room_tile()
    session = session_with(tile=tile)
    ok, reason = validate_rest_request(session, tile, nail_doors=True, choices={"h1": "life"})
    assert not ok
    assert "nails" in reason.lower()
