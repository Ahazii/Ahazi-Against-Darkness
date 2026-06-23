from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.cavern_features import (
    boulder_surprise_triggers,
    cavern_blocks_pc_attack_explode,
    cavern_contamination_save_penalty,
    cavern_pc_ranged_attack_modifier,
    cavern_stealth_modifier,
    cleanse_cavern_water_contamination,
    echo_spell_repeats,
    wandering_check_triggers,
)
from app.engine.class_combat import save_modifier
from app.engine.dungeon_table_roller import SubtableOutcome
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


@pytest.fixture
def engine() -> RandomDungeonEngine:
    return RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")


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
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (8, [8]))

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


def test_cavern_contamination_penalizes_saves() -> None:
    hero = PartyMemberState(
        character_id="h1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=2,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[hero],
        map_state=MapState(current_tile_id="t", tiles=[]),
        created_at="now",
        updated_at="now",
        cavern_contaminated_character_ids=["h1"],
    )
    assert cavern_contamination_save_penalty(session, hero) == -1
    assert save_modifier(hero, session=session) == 1
    assert cleanse_cavern_water_contamination(session, "h1") is True
    assert save_modifier(hero, session=session) == 2


def test_cavern_water_pool_contamination_and_refresh(engine: RandomDungeonEngine, monkeypatch) -> None:
    tile = TileState(
        id="pool",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Pool",
        description="Pool",
        cavern_feature_key="water_pools",
    )
    hero = PartyMemberState(
        character_id="h1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        environment="caverns",
        party=[hero],
        map_state=MapState(current_tile_id="pool", tiles=[tile]),
        created_at="now",
        updated_at="now",
    )
    rolls = iter(["contaminated", "refreshing", "refreshing"])

    monkeypatch.setattr(
        engine.table_roller,
        "roll_caverns_water_pool",
        lambda: SubtableOutcome(next(rolls), "pool effect"),
    )

    engine.advance(session, "dip_water_pool", character_id="h1", show_rolls=False)
    assert "h1" in session.cavern_contaminated_character_ids
    assert save_modifier(hero, session=session) == -1

    engine.advance(session, "dip_water_pool", character_id="h1", show_rolls=False)
    assert hero.current_life == 4
    assert "h1" in session.cavern_water_pool_healed_character_ids

    engine.advance(session, "dip_water_pool", character_id="h1", show_rolls=False)
    assert hero.current_life == 4
    assert any("already benefited" in line for line in session.log)


def test_apply_cavern_special_feature_marks_water_pool_pending(engine: RandomDungeonEngine, monkeypatch) -> None:
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Cavern",
        description="Cavern",
        content_key="special_feature",
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        environment="caverns",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=4,
                max_life=4,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(current_tile_id="t", tiles=[tile]),
        created_at="now",
        updated_at="now",
    )
    monkeypatch.setattr(
        engine.table_roller,
        "roll_special_feature",
        lambda environment="dungeon": SubtableOutcome("water_pools", "Water pool."),
    )

    engine._apply_special_feature(session, tile, show_rolls=False, explain_math=False)

    assert tile.cavern_feature_key == "water_pools"
    assert tile.resolved is False
    assert "Water Pool" in tile.objects
    assert any("dip into it" in line.lower() for line in session.log)
