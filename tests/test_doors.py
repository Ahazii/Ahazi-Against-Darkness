from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller, attempt_open_door
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import ExitState, MapState, PartyMemberState, SessionState, TileState


@pytest.fixture
def roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


@pytest.fixture
def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(rules=RulesRepository(packaged, packaged / "_override"), asset_dir=Path())


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


@pytest.mark.parametrize(
    ("roll", "door_type", "treasure_bonus"),
    [
        (2, "sealed", 1),
        (3, "iron", 1),
        (4, "illusion", 0),
        (5, "locked", 0),
        (6, "locked", 0),
        (7, "unlocked", 0),
        (10, "unlocked", 0),
        (11, "trap_door", 0),
        (12, "lever", 0),
    ],
)
def test_roll_door_types_match_ee_p109(
    roller: DungeonTableRoller,
    monkeypatch,
    roll: int,
    door_type: str,
    treasure_bonus: int,
) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_2d6", lambda: roll)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 3)
    outcome = roller.roll_door(hcl=4)
    assert outcome.door_type == door_type
    assert outcome.treasure_bonus == treasure_bonus
    assert outcome.roll == roll


def test_roll_door_iron_level_is_hcl_plus_d6(roller: DungeonTableRoller, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_2d6", lambda: 3)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 5)
    outcome = roller.roll_door(hcl=2)
    assert outcome.door_type == "iron"
    assert outcome.door_level == 7


def test_warrior_cannot_bash_iron_door(roller: DungeonTableRoller) -> None:
    exit_state = ExitState(
        id="door",
        direction="east",
        kind="door",
        status="unexplored",
        door_type="iron",
        door_level=5,
        door_open=False,
    )
    opened, log = attempt_open_door(
        exit_state,
        member(class_id="warrior"),
        hcl=3,
        show_rolls=False,
        explain_math=False,
        roller=roller,
    )
    assert opened is False
    assert any("iron door" in line.lower() for line in log)


def test_rogue_lockpicks_iron_door(roller: DungeonTableRoller, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    exit_state = ExitState(
        id="door",
        direction="east",
        kind="door",
        status="unexplored",
        door_type="iron",
        door_level=3,
        door_open=False,
    )
    opened, log = attempt_open_door(
        exit_state,
        member(class_id="rogue", level=3),
        hcl=2,
        show_rolls=False,
        explain_math=False,
        roller=roller,
    )
    assert opened is True
    assert exit_state.door_open is True


def test_sealed_door_blocks_physical_open(roller: DungeonTableRoller) -> None:
    exit_state = ExitState(
        id="door",
        direction="south",
        kind="door",
        status="unexplored",
        door_type="sealed",
        door_level=3,
        door_open=False,
    )
    opened, log = attempt_open_door(
        exit_state,
        member(class_id="wizard"),
        hcl=3,
        show_rolls=False,
        explain_math=False,
        roller=roller,
    )
    assert opened is False
    assert any("sealed" in line.lower() for line in log)


def test_entry_treasure_bonus_from_door(engine: RandomDungeonEngine) -> None:
    tile = TileState(
        id="room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        exits=[
            ExitState(
                id="north-door",
                direction="north",
                kind="door",
                status="open",
                door_type="sealed",
                door_treasure_bonus=1,
                door_open=True,
            )
        ],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[member(class_id="warrior")],
        map_state=MapState(tiles=[tile], current_tile_id="room"),
        current_tile_entry_exit_id="north-door",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert engine._entry_treasure_bonus(session) == 1


def test_spend_clue_opens_lever_door(engine: RandomDungeonEngine) -> None:
    tile = TileState(
        id="room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        exits=[
            ExitState(
                id="lever-door",
                direction="west",
                kind="door",
                status="unexplored",
                door_type="lever",
                door_open=False,
            )
        ],
    )
    hero = member(class_id="rogue")
    hero.clues = 1
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="room"),
        clues_found=1,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    engine._spend_clues_on_door(session, "lever-door", show_rolls=False)
    assert tile.exits[0].door_open is True
    assert hero.clues == 0
    assert any("lever" in line for line in session.log)
