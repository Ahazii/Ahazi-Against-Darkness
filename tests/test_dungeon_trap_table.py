from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.class_combat import defense_modifier
from app.engine.dungeon_table_roller import DungeonTableRoller, _trapdoor_modifier
from app.rules.repository import RulesRepository
from app.schemas import PartyMemberState


def _roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def _member(
    character_id: str = "hero-1",
    name: str = "Hero",
    *,
    class_id: str = "warrior",
    level: int = 1,
    current_life: int = 5,
    max_life: int = 5,
    marching_order: int = 1,
    inventory: list[str] | None = None,
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id=class_id,
        class_name=class_id.title(),
        level=level,
        max_life=max_life,
        current_life=current_life,
        marching_order=marching_order,
        inventory=list(inventory or []),
        gold=0,
        xp=0,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )


@pytest.mark.parametrize(
    ("roll", "trap_key"),
    [
        (1, "dart"),
        (2, "poison_gas"),
        (3, "trapdoor"),
        (4, "bear_trap"),
        (5, "spears"),
        (6, "falling_stone"),
    ],
)
def test_dungeon_trap_table_roll_maps_to_pdf_trap_keys(roll: int, trap_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: roll)
    outcome = roller.roll_trap(4, show_rolls=False, explain_math=False, environment="dungeon")
    assert outcome.trap_key == trap_key


def test_dart_trap_hits_random_pc_on_failed_defense(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    party = [_member("a", "Ada"), _member("b", "Bryn", marching_order=2)]
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[1])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("dart", 5, party, ["a", "b"], show_rolls=False, explain_math=False)

    assert party[1].current_life == 4
    assert any("Bryn takes 1 damage from the dart" in entry for entry in log)


def test_poison_gas_trap_hits_all_pcs(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    party = [_member("a", "Ada"), _member("b", "Bryn", marching_order=2)]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("poison_gas", 5, party, ["a", "b"], show_rolls=False, explain_math=False)

    assert party[0].current_life == 4
    assert party[1].current_life == 4
    assert sum("takes 1 damage from the poison gas" in entry for entry in log) == 2


def test_poison_gas_halfling_adds_level_to_save(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    halfling = _member("h", "Hilda", class_id="halfling", level=3)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))

    log = roller.resolve_trap("poison_gas", 5, [halfling], ["h"], show_rolls=False, explain_math=False)

    assert halfling.current_life == 5
    assert any("resists the poison gas" in entry for entry in log)


def test_trapdoor_only_targets_lead_pc(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    lead = _member("a", "Ada", inventory=["heavy armor"])
    rear = _member("b", "Bryn", marching_order=2)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("trapdoor", 5, [lead, rear], ["a", "b"], show_rolls=False, explain_math=False)

    assert lead.current_life == 4
    assert rear.current_life == 5
    assert _trapdoor_modifier(lead) == -2
    assert any("Ada takes 1 damage from the trapdoor" in entry for entry in log)


def test_spears_trap_targets_two_random_pcs(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    party = [_member("a", "Ada"), _member("b", "Bryn", marching_order=2), _member("c", "Cato", marching_order=3)]
    picks = iter([party[0], party[2]])
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.sample", lambda items, count: [next(picks), next(picks)])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("spears", 5, party, ["a", "b", "c"], show_rolls=False, explain_math=False)

    assert party[0].current_life == 4
    assert party[1].current_life == 5
    assert party[2].current_life == 4
    assert sum("takes 1 damage from the spears" in entry for entry in log) == 2


def test_falling_stone_targets_position_four_and_ignores_shield(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    rear = _member(
        "d",
        "Dara",
        marching_order=4,
        inventory=["Shield", "light armor"],
    )
    party = [
        _member("a", "Ada"),
        _member("b", "Bryn", marching_order=2),
        _member("c", "Cato", marching_order=3),
        rear,
    ]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("falling_stone", 5, party, ["a", "b", "c", "d"], show_rolls=False, explain_math=False)

    assert rear.current_life == 3
    assert party[0].current_life == 5
    assert any("Dara takes 2 damage from the falling stone" in entry for entry in log)
    row = roller.lookup_trap("falling_stone")
    assert row is not None
    assert row["shield_applies"] is False


def test_falling_stone_shield_does_not_help_defense(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    rear = _member("d", "Dara", marching_order=4, inventory=["Shield"])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (5, [5]))

    roller.resolve_trap("falling_stone", 4, [rear], ["d"], show_rolls=False, explain_math=False)

    assert rear.current_life == 5
    assert defense_modifier(rear) >= 0
