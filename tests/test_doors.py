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
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda level: (2, [2]))
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
