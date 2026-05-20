from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def session_with(member: PartyMemberState, *, mode: str = "exploration") -> SessionState:
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode=mode,
        party=[member],
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


def test_use_bandage_heals_out_of_combat() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=2,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Bandage"],
    )
    session = session_with(hero)
    engine.advance(session, "use_bandage", character_id="hero")
    assert hero.current_life == 3
    assert "Bandage" not in hero.inventory
    assert "hero" in session.bandage_used_character_ids


def test_bandage_blocked_in_combat() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=2,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Bandage"],
    )
    foe = EnemyState(id="rat", name="Rat", category="vermin", level=3, life=1, max_life=1)
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
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    engine.advance(session, "use_bandage", character_id="hero")
    assert hero.current_life == 2
    assert "Bandage" in hero.inventory
    assert any("during combat" in entry.lower() for entry in session.log)


def test_kukla_cannot_use_bandage() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    kukla = PartyMemberState(
        character_id="kukla",
        name="Doll",
        class_id="kukla",
        class_name="Kukla",
        level=1,
        xp=0,
        gold=0,
        current_life=2,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Bandage"],
    )
    session = session_with(kukla)
    engine.advance(session, "use_bandage", character_id="kukla")
    assert kukla.current_life == 2
    assert any("kukla" in entry.lower() for entry in session.log)
