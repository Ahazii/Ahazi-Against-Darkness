from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import (
    DungeonTableRoller,
    _bear_trap_modifier,
    _caverns_trap_save_modifier,
    _trapdoor_modifier,
    door_opening_hint,
    parse_roll_range,
    resolve_gold_formula,
)
from app.engine.class_combat import attack_modifier, defense_modifier
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, PartyMemberState


@pytest.fixture
def roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def test_parse_roll_range() -> None:
    assert parse_roll_range("5-6") == (5, 6)
    assert parse_roll_range("12") == (12, 12)


def test_door_table_lookup(roller: DungeonTableRoller) -> None:
    row = roller.lookup("door_table", 11)
    assert row is not None
    assert row["door_type"] == "trap_door"


def test_door_opening_hint_covers_special_types() -> None:
    assert "lock-pick" in door_opening_hint("locked", door_level=5).lower()
    assert "fireball" in door_opening_hint("iron", door_level=6).lower()
    assert "spellcasting" in door_opening_hint("sealed", door_level=4).lower()
    assert "3 clues" in door_opening_hint("illusion", hcl=3).lower()


def test_trap_table_lookup_by_key(roller: DungeonTableRoller) -> None:
    row = roller.lookup_trap("falling_stone")
    assert row is not None
    assert row["damage"] == 2
    assert row["target"] == "rear"


def test_bear_trap_failure_applies_wound_penalties_until_life_recovered(monkeypatch, roller: DungeonTableRoller) -> None:
    hero = _member("a", "Ada", life=5)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("bear_trap", 4, [hero], ["a"], show_rolls=False, explain_math=False)

    assert hero.current_life == 4
    assert "Bear Trap Wound" in hero.statuses
    assert any("-2 vs bear traps/trapdoors" in entry for entry in log)
    rat = EnemyState(id="r", name="Rat", category="vermin", level=1, life=1, max_life=1)
    assert attack_modifier(hero, rat) == hero.level - 1
    assert defense_modifier(hero, rat) == -1
    assert _trapdoor_modifier(hero) == -2
    assert _bear_trap_modifier(hero) == -2

    hero.current_life = hero.max_life
    assert attack_modifier(hero, rat) == hero.level
    assert defense_modifier(hero, rat) == 0
    assert _trapdoor_modifier(hero) == 0
    assert _bear_trap_modifier(hero) == 0


def test_search_table_lookup(roller: DungeonTableRoller) -> None:
    assert roller.lookup_search(6).effect == "found_something"
    assert roller.lookup_search(2).effect == "nothing"


def _member(
    character_id: str,
    name: str,
    *,
    class_id: str = "warrior",
    life: int = 5,
    inventory: list[str] | None = None,
    default_melee_weapon: str | None = None,
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id=class_id,
        class_name=class_id.title(),
        level=1,
        xp=0,
        gold=0,
        current_life=life,
        max_life=life,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=list(inventory or []),
        default_melee_weapon=default_melee_weapon,
    )


def test_caverns_swinging_log_checks_marching_order_until_first_failure(monkeypatch, roller: DungeonTableRoller) -> None:
    party = [_member("a", "Ada"), _member("b", "Bryn"), _member("c", "Cato")]
    rolls = iter([(6, [6]), (1, [1]), (1, [1])])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: next(rolls))

    log = roller.resolve_trap("swinging_log", 5, party, ["a", "b", "c"], show_rolls=False, explain_math=False)

    assert party[0].current_life == 5
    assert party[1].current_life == 3
    assert party[2].current_life == 5
    assert any("Ada passes" in entry or "Ada resists" in entry for entry in log)
    assert any("Bryn takes 2 damage" in entry for entry in log)


def test_fungal_sleep_spores_trigger_then_all_poison_saves(monkeypatch, roller: DungeonTableRoller) -> None:
    party = [_member("a", "Ada"), _member("b", "Bryn"), _member("m", "Mora", class_id="mushroom_monk")]
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    rolls = iter([(1, [1]), (1, [1]), (6, [6])])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: next(rolls))

    log = roller.resolve_trap("sleep_spores", 4, party, ["a", "b", "m"], show_rolls=False, explain_math=False)

    assert "Asleep (sleep spores)" in party[0].statuses
    assert party[0].current_life > 0
    assert "Asleep (sleep spores)" not in party[1].statuses
    assert "Asleep (sleep spores)" not in party[2].statuses
    assert any("Mora is immune" in entry for entry in log)


def test_fungal_mycelium_snare_removes_chosen_held_object(monkeypatch, roller: DungeonTableRoller) -> None:
    hero = _member("a", "Ada", inventory=["Sword", "Shield"], default_melee_weapon="Sword")
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    pending = roller.resolve_trap("mycelium_snare", 4, [hero], ["a"], show_rolls=False, explain_math=False)
    assert pending.pending_mycelium_snare_character_id == "a"
    assert any("choose which held object" in entry for entry in pending)
    assert "Shield" in hero.inventory

    result = roller.resolve_trap(
        "mycelium_snare",
        4,
        [hero],
        ["a"],
        show_rolls=False,
        explain_math=False,
        snare_item_name="Shield",
    )
    assert result.pending_mycelium_snare_character_id is None
    assert "Shield" not in hero.inventory
    assert "Sword" in hero.inventory
    assert any("Shield is snatched away forever" in entry for entry in result)


def test_fungal_shrieking_mushroom_uses_pdf_chance_modifiers(monkeypatch, roller: DungeonTableRoller) -> None:
    rogue = _member("r", "Rill", class_id="rogue")
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 4)

    log = roller.resolve_trap("shrieking_mushroom", 4, [rogue], ["r"], show_rolls=False, explain_math=False)

    assert any("3-in-6" in entry for entry in log)
    assert any("avoids disturbing" in entry for entry in log)


def test_fungal_cordyceps_marks_infected_pc_and_names_target(monkeypatch, roller: DungeonTableRoller) -> None:
    party = [_member("a", "Ada"), _member("b", "Bryn", life=2)]
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("cordyceps_trap", 4, party, ["a", "b"], show_rolls=False, explain_math=False)

    assert "Cordyceps infected (6 turns)" in party[0].statuses
    assert any("must attack Bryn" in entry for entry in log)


def test_caverns_rolling_boulder_can_come_from_back(monkeypatch, roller: DungeonTableRoller) -> None:
    party = [_member("a", "Ada"), _member("b", "Bryn"), _member("c", "Cato")]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap(
        "rolling_boulder",
        4,
        party,
        ["a", "b", "c"],
        show_rolls=False,
        explain_math=False,
        boulder_origin="back",
    )

    assert party[0].current_life == 5
    assert party[1].current_life == 5
    assert party[2].current_life == 3
    assert any("comes from the back" in entry for entry in log)


def test_caverns_trap_save_modifiers_match_pdf_classes() -> None:
    warrior = _member("w", "Wren", class_id="warrior")
    warrior.level = 5
    rogue = _member("r", "Rill", class_id="rogue")
    rogue.level = 5
    gnome = _member("g", "Gim", class_id="gnome")
    gnome.level = 5
    dwarf = _member("d", "Dorn", class_id="dwarf")
    dwarf.level = 5
    forester = _member("f", "Fern", class_id="forester")
    forester.level = 5

    assert _caverns_trap_save_modifier(warrior, "rolling_boulder") == 2
    assert _caverns_trap_save_modifier(rogue, "rolling_boulder") == 5
    assert _caverns_trap_save_modifier(gnome, "rockslide") == 5
    assert _caverns_trap_save_modifier(dwarf, "rockslide") == 5
    assert _caverns_trap_save_modifier(forester, "toxic_mushrooms") == 5


def test_caverns_halfling_rerolls_failed_rolling_boulder_save(monkeypatch, roller: DungeonTableRoller) -> None:
    halfling = _member("h", "Hob", class_id="halfling", life=5)
    halfling.level = 4
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    rolls = iter([(1, [1]), (6, [6])])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: next(rolls))

    log = roller.resolve_trap(
        "rolling_boulder",
        5,
        [halfling],
        ["h"],
        show_rolls=True,
        explain_math=False,
        boulder_origin="front",
    )

    assert halfling.current_life == 5
    assert any("Caverns halfling reroll" in entry for entry in log)


def test_toxic_mushrooms_apply_save_penalty_and_mushroom_monk_immunity(monkeypatch, roller: DungeonTableRoller) -> None:
    hero = _member("a", "Ada", life=5)
    monk = _member("m", "Mora", class_id="mushroom_monk", life=5)
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("toxic_mushrooms", 5, [hero], ["a"], show_rolls=False, explain_math=False)
    assert "Toxic Spores (-1 Saves, 6 rooms)" in hero.statuses
    assert any("-1 on all Saves for 6 rooms" in entry for entry in log)

    log = roller.resolve_trap("toxic_mushrooms", 5, [monk], ["m"], show_rolls=False, explain_math=False)
    assert "Toxic Spores (-1 Saves, 6 rooms)" not in monk.statuses
    assert any("toxic mushrooms are ignored" in entry or "immune" in entry for entry in log)
