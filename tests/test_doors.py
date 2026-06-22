from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller, attempt_open_door
from app.rules.repository import RulesRepository
from app.schemas import ExitState, PartyMemberState


@pytest.fixture
def roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def member(*, class_id: str, level: int = 3, gold: int = 0) -> PartyMemberState:
    return PartyMemberState(
        character_id=class_id,
        name=class_id.title(),
        class_id=class_id,
        class_name=class_id.title(),
        level=level,
        xp=0,
        gold=gold,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Light armor", "Shield", "Hand weapon", "Hand weapon", "Hand weapon"] if gold > 250 else [],
    )


def locked_exit(level: int = 3) -> ExitState:
    return ExitState(
        id="door",
        direction="north",
        kind="door",
        status="unexplored",
        door_type="locked",
        door_level=level,
        door_open=False,
    )


def fresh_door() -> ExitState:
    return ExitState(id="door", direction="west", kind="door", status="unexplored", door_open=False)


def trapped_door(level: int = 3) -> ExitState:
    return ExitState(
        id="door",
        direction="north",
        kind="door",
        status="unexplored",
        door_type="trap_door",
        door_level=level,
        door_open=False,
    )


def test_wizard_cannot_bash_locked_door(roller: DungeonTableRoller) -> None:
    opened, log = attempt_open_door(
        locked_exit(),
        member(class_id="wizard"),
        hcl=2,
        show_rolls=False,
        explain_math=False,
        roller=roller,
    )
    assert opened is False
    assert any("Rogue" in entry for entry in log)


def test_locked_door_applies_encumbrance_penalty(roller: DungeonTableRoller, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (2, [2]))
    overburdened = member(class_id="warrior", gold=250)
    fit = member(class_id="warrior")
    opened_enc, _ = attempt_open_door(
        locked_exit(level=5),
        overburdened,
        hcl=2,
        show_rolls=False,
        explain_math=False,
        roller=roller,
    )
    opened_fit, _ = attempt_open_door(
        locked_exit(level=5),
        fit,
        hcl=2,
        show_rolls=False,
        explain_math=False,
        roller=roller,
    )
    assert opened_fit is True
    assert opened_enc is False


def test_summary_door_log_omits_roll_and_duplicate_hint(roller: DungeonTableRoller, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_2d6", lambda: 4)
    opened, log = attempt_open_door(
        fresh_door(),
        member(class_id="warrior"),
        hcl=4,
        show_rolls=False,
        explain_math=False,
        roller=roller,
    )

    assert opened is False
    assert log == ["Door: Illusionary door (HCL 4).", "The illusion blocks the way."]


def test_verbose_door_log_includes_roll_and_single_hint(roller: DungeonTableRoller, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_2d6", lambda: 4)
    opened, log = attempt_open_door(
        fresh_door(),
        member(class_id="warrior"),
        hcl=4,
        show_rolls=True,
        explain_math=True,
        roller=roller,
    )

    assert opened is False
    assert log == [
        "Door roll: 2d6 = 4.",
        "Door: Illusionary door (HCL 4).",
        "Illusionary door (HCL 4). Spend 3 Clues, or an Illusionist spellcasting roll vs HCL 4.",
        "The illusion blocks the way until the party spends 3 Clues or an Illusionist dispels it.",
    ]


def test_non_rogue_trapped_door_resolves_trap(roller: DungeonTableRoller, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
    warrior = member(class_id="warrior")
    exit_state = trapped_door(level=3)

    opened, log = attempt_open_door(
        exit_state,
        warrior,
        hcl=2,
        show_rolls=False,
        explain_math=False,
        roller=roller,
        party=[warrior],
        marching_order=[warrior.character_id],
    )

    assert opened is True
    assert exit_state.door_open is True
    assert warrior.current_life < warrior.max_life
    assert "The door opens." in log
