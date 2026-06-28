from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.adventurer_body import resolve_adventurer_body_loot
from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.equipment_shop import jewelry_bribe_counted_gp
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.special_items import equip_glittering_crystal, is_map_fragment
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState


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
        (1, None, None),
        (2, None, "Glittering Crystal"),
        (3, None, "Map Fragment"),
        (4, "caverns_adventurer_body", None),
        (5, None, "Miners' Ointment"),
        (6, None, "Miners' Amulet"),
    ],
)
def test_caverns_special_item_table_roll_outcomes(
    roll: int,
    choice_key: str | None,
    direct_item: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: roll)
    if roll == 1:
        monkeypatch.setattr("app.engine.dungeon_table_roller.roll_formula", lambda _f: 10)
    outcome = roller.roll_magic_treasure(
        environment="caverns",
        table_name="caverns_special_item_table",
    )
    if roll == 1:
        assert outcome.gold == 0
        assert outcome.items
        assert "13gp" in outcome.items[0]
        assert "13gp" in outcome.summary
        assert not outcome.gold
        return
    if choice_key:
        assert outcome.choice_key == choice_key
        assert not outcome.items
    else:
        assert outcome.choice_key is None
        assert outcome.items
        needle = direct_item.split()[-1].lower()
        assert any(needle in item.lower() for item in outcome.items)


def test_caverns_gem_roll_uses_3d6_plus_3_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_formula", lambda _f: 12)
    outcome = roller.roll_magic_treasure(
        environment="caverns",
        table_name="caverns_special_item_table",
    )
    assert outcome.gold == 0
    assert outcome.items
    assert "15gp" in outcome.items[0]


def test_caverns_adventurer_body_choice_resolves_gear_and_gems() -> None:
    roller = _roller()
    outcome = roller.resolve_environment_treasure_choice(
        "caverns_adventurer_body",
        "bow",
        environment="caverns",
    )
    assert "Bow" in outcome.items
    assert outcome.gold >= 10


def test_caverns_adventurer_body_chicken_blood_option() -> None:
    items, gold, _log, summary = resolve_adventurer_body_loot("caverns", "chicken_blood")
    assert "Jar of chicken blood" in items
    assert gold >= 10
    assert summary


def test_glittering_crystal_equips_as_light_source() -> None:
    member = _member(inventory=["Glittering Crystal"])
    log = equip_glittering_crystal(member)
    assert "Glittering Crystal" in member.statuses
    assert log


def test_map_fragment_counts_30gp_for_gem_bribe() -> None:
    catalog = RulesRepository(
        Path(__file__).resolve().parents[1] / "data" / "rules",
        Path(__file__).resolve().parents[1] / "data" / "rules" / "_override",
    ).equipment_shop()
    assert jewelry_bribe_counted_gp("Map Fragment", "warrior", catalog) == 30
    assert is_map_fragment("Map Fragment")


def test_map_fragment_bribe_accepts_fragment_as_gem() -> None:
    eng = _engine()
    party = [_member(inventory=["Map Fragment"])]
    from app.schemas import EnemyState, MapState, TileState

    enemies = [EnemyState(id="e", name="Cavemen", category="minions", level=2, life=1, max_life=1)]
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        environment="caverns",
        party=party,
        map_state=MapState(
            tiles=[
                TileState(
                    id="t",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=enemies,
                    initial_enemy_count=1,
                )
            ],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        mode="combat",
        reaction_pending=True,
        reaction_key="bribe_gem",
        reaction_bribe_foe_count=1,
    )

    eng.advance(
        session,
        "reaction_choice",
        reaction_choice="accept",
        character_id="hero-1",
        item_name="Map Fragment",
    )

    assert session.mode == "exploration"
    assert "Map Fragment" not in party[0].inventory
    assert any("Counted gem value for bribe: 30gp" in entry for entry in session.log)
