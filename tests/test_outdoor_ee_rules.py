from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.engine import combat, spells
from app.engine.class_abilities import resolve_social_save
from app.engine.combat import CombatContext, resolve_combat_round
from app.engine.random_dungeon import CLUES_FOR_SECRET_XP, RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _session(**kwargs) -> SessionState:
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
    )
    defaults = dict(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[tile], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def _druid(level: int = 3) -> PartyMemberState:
    return PartyMemberState(
        character_id="d1",
        name="Druid",
        class_id="druid",
        class_name="Druid",
        level=level,
        xp=0,
        gold=0,
        max_life=5,
        current_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        spells=["Alter Weather", "Lightning Strike"],
    )


def _illusionist(level: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id="i1",
        name="Mira",
        class_id="illusionist",
        class_name="Illusionist",
        level=level,
        xp=0,
        gold=0,
        max_life=4,
        current_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        inventory=[],
        spells=["Glamour Mask", "Illusionary Banquet"],
    )


def _foe() -> EnemyState:
    return EnemyState(id="e1", name="Orc", category="minions", life=2, max_life=2, level=2)


def test_alter_weather_sets_outcome_flag() -> None:
    druid = _druid()
    outcome = spells.resolve_spell_cast(
        "Alter Weather",
        druid,
        [druid],
        [_foe()],
        show_rolls=False,
        terrain="outdoor",
    )
    assert outcome.spell_consumed
    assert outcome.alter_weather_active


def test_lightning_strike_gets_weather_bonus() -> None:
    druid = _druid()
    foe = _foe()
    session_state = _session(party=[druid], alter_weather_active=True)
    with patch("app.engine.spells.roll_exploding_for_level", return_value=(4, [4])):
        outcome = spells.resolve_spell_cast(
            "Lightning Strike",
            druid,
            [druid],
            [foe],
            show_rolls=False,
            terrain="outdoor",
            session=session_state,
        )
    assert outcome.spell_consumed
    assert any("alter weather adds +1" in line.lower() for line in outcome.log)


def test_illusionary_banquet_caps_rations_at_seven() -> None:
    illusionist = _illusionist(level=6)
    outcome = spells.resolve_spell_cast(
        "Illusionary Banquet",
        illusionist,
        [illusionist],
        [],
        show_rolls=False,
    )
    assert outcome.banquet_rations == 7


def test_glamour_mask_grants_reroll_token() -> None:
    illusionist = _illusionist()
    outcome = spells.resolve_spell_cast(
        "Glamour Mask",
        illusionist,
        [illusionist],
        [],
        show_rolls=False,
    )
    assert outcome.glamour_mask_reroll_available
    assert outcome.glamour_mask_character_id == "i1"


def test_glamour_mask_rerolls_failed_social_save() -> None:
    illusionist = _illusionist()
    session = _session(
        party=[illusionist],
        glamour_mask_character_id="i1",
        glamour_mask_reroll_available=True,
    )
    rolls = iter([(2, [2]), (5, [5])])

    def fake_roll(level: int) -> tuple[int, list[int]]:
        return next(rolls)

    with patch("app.engine.class_abilities.roll_exploding_for_level", side_effect=fake_roll):
        ok, log = resolve_social_save(session, illusionist, 4, show_rolls=True, label="negotiate")
    assert ok
    assert not session.glamour_mask_reroll_available
    assert any("glamour mask reroll" in line.lower() for line in log)


def test_alter_weather_penalizes_ranged_attacks(monkeypatch) -> None:
    rolls = iter([(4, [4]), (5, [5])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: next(rolls))

    ranger = PartyMemberState(
        character_id="rng",
        name="Tracker",
        class_id="ranger",
        class_name="Ranger",
        level=4,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Bow", "Hand weapon"],
        default_missile_weapon="Bow",
    )
    foe = EnemyState(id="orc", name="Orc", category="minions", level=4, life=4, max_life=4)
    context = CombatContext(tile_type="room", outdoors=True, alter_weather_active=True)
    result = resolve_combat_round(
        [ranger],
        [foe],
        show_rolls=True,
        context=context,
        party_attacked_immediately=True,
        encounter_round=0,
    )
    assert any("alter weather hinders ranged attacks" in line.lower() for line in result.log)


def test_ranger_outdoor_sling_fires_twice(monkeypatch) -> None:
    rolls = iter([(4, [4]), (5, [5])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: next(rolls))

    ranger = PartyMemberState(
        character_id="rng",
        name="Tracker",
        class_id="ranger",
        class_name="Ranger",
        level=4,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Sling", "Hand weapon"],
        default_missile_weapon="Sling",
    )
    foe = EnemyState(id="orc", name="Orc", category="minions", level=4, life=4, max_life=4)
    context = CombatContext(tile_type="room", outdoors=True)
    result = resolve_combat_round(
        [ranger],
        [foe],
        show_rolls=True,
        context=context,
        party_attacked_immediately=True,
        encounter_round=0,
    )
    missile_lines = [line for line in result.log if "Missile roll:" in line and ranger.name in line]
    assert len(missile_lines) == 2
    assert any("outdoor sling" in line for line in result.log)


def test_entrance_tile_is_outdoor(monkeypatch) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())
    monkeypatch.setattr("app.engine.random_dungeon.roll_start_tile_key", lambda: "01")
    party = [
        PartyMemberState(
            character_id="h1",
            name="Hero",
            class_id="warrior",
            class_name="Warrior",
            level=1,
            xp=0,
            gold=0,
            max_life=8,
            current_life=8,
            attack_bonus=0,
            defense_bonus=0,
            save_bonus=0,
            marching_order=1,
        )
    ]
    session = engine.create_session("s1", "p1", party)
    entrance = next(tile for tile in session.map_state.tiles if tile.content_key == "entrance")
    assert entrance.terrain == "outdoor"


def test_captive_hideout_clue_cost_has_no_ranger_discount() -> None:
    assert CLUES_FOR_SECRET_XP == 3
