from __future__ import annotations

from pathlib import Path

from app.engine.madness import (
    apply_madness_gain,
    heal_madness_on_dungeon_exit,
    is_paranoid,
    madness_points,
    resolve_madness_choice,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def session_with_hero(*, level: int = 3, class_id: str = "warrior") -> SessionState:
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id=class_id,
        class_name=class_id.title(),
        level=level,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
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
                )
            ],
            current_tile_id="tile",
        ),
        created_at="now",
        updated_at="now",
    )


def test_ghost_failure_grants_madness(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    monkeypatch.setattr(
        "app.engine.heroic_skill_effects.resolve_fear_save",
        lambda *args, **kwargs: (False, []),
    )
    session = session_with_hero(level=5)
    engine._resolve_ghost_event(session, show_rolls=False)
    assert madness_points(session.party[0]) == 1
    assert is_paranoid(session.party[0])


def test_low_level_hero_can_take_damage_instead_of_madness() -> None:
    session = session_with_hero(level=2)
    member = session.party[0]
    apply_madness_gain(session, member, source="the ghost", show_rolls=False)
    assert session.pending_madness_choice is not None
    resolve_madness_choice(session, character_id="hero", choice="damage")
    assert madness_points(member) == 0
    assert member.current_life == 2


def test_wizard_insanity_threshold_is_level_plus_one() -> None:
    session = session_with_hero(level=2, class_id="wizard")
    member = session.party[0]
    member.madness = 3
    apply_madness_gain(session, member, source="shock", show_rolls=False, allow_damage_choice=False)
    assert member.current_life == 0
    assert madness_points(member) == 0


def test_exit_heals_one_madness_once_after_major_foe() -> None:
    session = session_with_hero()
    session.major_foes_encountered = 1
    session.party[0].madness = 2
    log = heal_madness_on_dungeon_exit(session)
    assert madness_points(session.party[0]) == 1
    assert session.madness_exit_healed
    assert log
    assert not heal_madness_on_dungeon_exit(session)
