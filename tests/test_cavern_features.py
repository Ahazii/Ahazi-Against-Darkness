from __future__ import annotations

from pathlib import Path

from app.engine.cavern_features import (
    boulder_surprise_triggers,
    cavern_blocks_pc_attack_explode,
    cavern_pc_ranged_attack_modifier,
    cavern_stealth_modifier,
    echo_spell_repeats,
    wandering_check_triggers,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def echo_combat_session(*, enemies: list[EnemyState]) -> SessionState:
    wizard = PartyMemberState(
        character_id="wiz",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Lightning"],
    )
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        reaction_checked=True,
        party=[wizard],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Echo Room",
                    description="Room",
                    enemies=enemies,
                    cavern_feature_key="echo",
                )
            ],
            current_tile_id="tile",
        ),
        created_at="now",
        updated_at="now",
    )


def test_stalagmites_block_pc_attack_explode() -> None:
    assert cavern_blocks_pc_attack_explode("stalagmites") is True
    assert cavern_blocks_pc_attack_explode("echo") is False


def test_boulders_modify_ranged_attack_and_stealth() -> None:
    assert cavern_pc_ranged_attack_modifier("boulders", missile=True) == -1
    assert cavern_pc_ranged_attack_modifier("boulders", missile=False) == 0
    assert cavern_stealth_modifier("boulders") == 1
    assert cavern_stealth_modifier("echo") == -1


def test_echo_wandering_is_two_in_six(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.cavern_features.roll_d6", lambda: 2)
    triggered, roll = wandering_check_triggers("echo")
    assert triggered is True
    assert roll == 2


def test_boulder_surprise_requires_tagged_foe() -> None:
    triggered, _ = boulder_surprise_triggers(
        "boulders",
        [EnemyState(id="1", name="Bat", category="vermin", level=1, life=1, max_life=1, tags=[])],
    )
    assert triggered is False


def test_echo_spell_repeat_on_six(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.cavern_features.roll_d6", lambda: 6)
    repeat, roll = echo_spell_repeats("echo", echo_repeat=False)
    assert repeat is True
    assert roll == 6


def test_echo_spell_sets_pending_target_choice(monkeypatch) -> None:
    from app.engine import cavern_features, spells

    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    foes = [
        EnemyState(id="a", name="Ogre A", category="boss", level=5, life=6, max_life=6),
        EnemyState(id="b", name="Ogre B", category="boss", level=5, life=6, max_life=6),
    ]
    session = echo_combat_session(enemies=foes)
    session.party[0].spells = ["Infallible Missile"]
    monkeypatch.setattr(cavern_features, "roll_d6", lambda: 6)
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda level: (8, [8]))

    engine.advance(
        session,
        "cast_spell",
        character_id="wiz",
        spell_name="Infallible Missile",
        foe_id="a",
    )

    assert session.pending_echo_spell is not None
    assert session.pending_echo_spell.spell_name == "Infallible Missile"
    assert session.pending_echo_spell.target_foe_id == "a"
    assert any("choose targets" in line.lower() for line in session.log)
    assert next(foe for foe in session.map_state.tiles[0].enemies if foe.id == "b").life == 6

    engine.advance(session, "resolve_echo_spell", foe_id="b")
    assert session.pending_echo_spell is None
    assert next(foe for foe in session.map_state.tiles[0].enemies if foe.id == "b").life < 6
