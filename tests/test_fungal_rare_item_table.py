from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.fungal_rare_items import (
    RED_DEATH_DAMAGE_ITEM,
    XICTHUL_CAP_ITEM,
    morel_crusher_morale_total,
    template_morale_modifier,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def _engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _member(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=2,
        max_life=4,
        current_life=4,
        marching_order=1,
        inventory=[],
        gold=0,
        xp=0,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


@pytest.mark.parametrize(
    ("roll", "choice_key", "direct_item"),
    [
        (1, "fungal_gem_or_leafsteel", None),
        (2, None, "xicthul"),
        (3, "fungal_red_death", None),
        (4, "fungal_adventurer_body", None),
        (5, None, "white angel mushroom"),
        (6, None, "morel crusher"),
    ],
)
def test_fungal_rare_item_table_roll_outcomes(
    roll: int,
    choice_key: str | None,
    direct_item: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: roll)
    if roll == 5:
        monkeypatch.setattr("app.engine.fungal_rare_items.roll_formula", lambda _f: 3)
    outcome = roller.roll_magic_treasure(
        environment="fungal_grottoes",
        table_name="fungal_grottoes_rare_item_table",
    )
    if choice_key:
        assert outcome.choice_key == choice_key
        assert not outcome.items
    else:
        assert outcome.choice_key is None
        assert outcome.items
        assert any(direct_item in item.lower() for item in outcome.items)


def test_fungal_gem_choice_uses_2d6_plus_2_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_formula", lambda _f: 7)
    outcome = roller.resolve_environment_treasure_choice("fungal_gem_or_leafsteel", "gem")
    assert outcome.gold == 0
    assert outcome.items
    assert "9gp" in outcome.items[0]
    assert "9gp" in outcome.summary


def test_fungal_leafsteel_choice_grants_armor() -> None:
    roller = _roller()
    outcome = roller.resolve_environment_treasure_choice("fungal_gem_or_leafsteel", "leafsteel")
    assert outcome.items
    assert "leafsteel" in outcome.items[0].lower()


def test_trap_rare_item_event_grants_fungal_rare_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eng = _engine()
    tile = TileState(
        id="event",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Event",
        description="Event",
        content_key="special_event",
        objects=["Special Event"],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        environment="fungal_grottoes",
        party=[_member()],
        map_state=MapState(tiles=[tile], current_tile_id="event"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    from app.engine.dungeon_table_roller import SubtableOutcome

    monkeypatch.setattr(
        eng.table_roller,
        "roll_special_event",
        lambda **kwargs: SubtableOutcome("trap_rare_item", "Trap then rare item."),
    )
    monkeypatch.setattr(
        eng.table_roller,
        "roll_trap",
        lambda hcl, *, show_rolls, explain_math, environment: type(
            "TrapOutcome",
            (),
            {"trap_key": "sleep_spores", "trap_level": 2, "summary": "Sleep Spores trap"},
        )(),
    )
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 2)

    eng._apply_special_event(session, tile, show_rolls=False, explain_math=False)

    assert tile.trap_key == "sleep_spores"
    assert tile.treasure_items == [XICTHUL_CAP_ITEM]
    assert tile.environment_event_resolved


def test_morel_crusher_morale_uses_foe_modifier() -> None:
    assert morel_crusher_morale_total(4, morale_modifier=0) == 3
    assert morel_crusher_morale_total(4, morale_modifier=1) == 4
    assert template_morale_modifier({"morale_modifier": -1}) == -1


def test_morel_crusher_respects_positive_morale_modifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eng = _engine()
    hero = _member(inventory=["Morel Crusher"])
    foe = EnemyState(
        id="f1",
        name="Moldspawn",
        category="minions",
        level=3,
        life=2,
        max_life=2,
        tags=["minions", "mushroom"],
    )
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        enemies=[foe],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        reaction_checked=True,
        reaction_key="fight",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 4)
    monkeypatch.setattr(
        eng,
        "_monster_template_for_enemy",
        lambda enemy: {"morale_modifier": 1},
    )

    eng.advance(
        session,
        "use_mushroom",
        character_id=hero.character_id,
        item_name="Morel Crusher",
        foe_id="f1",
        show_rolls=True,
    )

    assert foe.life == 2
    assert any("Morale modifier" in line for line in session.log)
    assert any("resists" in line for line in session.log)


def test_morel_crusher_frightens_with_low_roll_and_modifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eng = _engine()
    hero = _member(inventory=["Morel Crusher"])
    foe = EnemyState(id="f1", name="Brute", category="weird", level=4, life=3, max_life=3)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        enemies=[foe],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        reaction_checked=True,
        reaction_key="fight",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 4)
    monkeypatch.setattr(eng, "_monster_template_for_enemy", lambda enemy: {"morale_modifier": 0})

    eng.advance(
        session,
        "use_mushroom",
        character_id=hero.character_id,
        item_name="Morel Crusher",
        foe_id="f1",
        show_rolls=True,
    )

    assert foe.life == 0
    assert "Morel Crusher" not in hero.inventory
