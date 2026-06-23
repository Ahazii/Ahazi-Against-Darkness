from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.cavern_traps import is_caverns_forester_class, is_mushroom_class
from app.engine.dungeon_table_roller import DungeonTableRoller
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
    level: int = 4,
    current_life: int = 5,
    max_life: int = 5,
    marching_order: int = 1,
    inventory: list[str] | None = None,
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id=class_id,
        class_name=class_id.replace("_", " ").title(),
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
        (1, "stalactite"),
        (2, "rockslide"),
        (3, "hidden_pit"),
        (4, "swinging_log"),
        (5, "toxic_mushrooms"),
        (6, "rolling_boulder"),
    ],
)
def test_caverns_trap_table_roll_maps_to_pdf_trap_keys(roll: int, trap_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: roll)
    outcome = roller.roll_trap(4, show_rolls=False, explain_math=False, environment="caverns")
    assert outcome.trap_key == trap_key


def test_stalactite_hits_random_pc_on_failed_save(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    party = [_member("a", "Ada"), _member("b", "Bryn", marching_order=2)]
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[1])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("stalactite", 5, party, ["a", "b"], show_rolls=False, explain_math=False)

    assert party[1].current_life == 4
    assert any("Bryn takes 1 damage from the stalactite" in entry for entry in log)


def test_rockslide_hits_all_pcs(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    party = [_member("a", "Ada"), _member("b", "Bryn", marching_order=2)]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("rockslide", 5, party, ["a", "b"], show_rolls=False, explain_math=False)

    assert party[0].current_life == 4
    assert party[1].current_life == 4
    assert sum("takes 1 damage from the rockslide" in entry for entry in log) == 2


def test_hidden_pit_traps_lead_and_marks_pit_status(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.engine.special_items import is_pit_trapped

    roller = _roller()
    lead = _member("a", "Ada", marching_order=1)
    rear = _member("b", "Bryn", marching_order=2)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    roller.resolve_trap("hidden_pit", 5, [lead, rear], ["a", "b"], show_rolls=False, explain_math=False)

    assert lead.current_life == 4
    assert rear.current_life == 5
    assert is_pit_trapped(lead)


def test_swinging_log_log_mentions_vine_bound_log(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    party = [_member("a", "Ada"), _member("b", "Bryn", marching_order=2)]
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    log = roller.resolve_trap("swinging_log", 4, party, ["a", "b"], show_rolls=False, explain_math=False)

    assert any("bound with vines" in entry for entry in log)


def test_hidden_pit_no_clue_option_when_lead_passes_save(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    lead = _member("a", "Ada", marching_order=1)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    log = roller.resolve_trap("hidden_pit", 4, [lead], ["a"], show_rolls=False, explain_math=False)

    assert lead.current_life == 5
    assert not any("trapped in the pit" in entry for entry in log)


def test_toxic_mushrooms_result_mentions_spores_patch() -> None:
    roller = _roller()
    row = roller.lookup_trap("toxic_mushrooms")
    assert row is not None
    assert "steps on a patch of mushrooms" in row["result"]
    assert "releasing toxic spores" in row["result"]


def test_mushroom_class_detection_covers_monk_and_supplement_ids() -> None:
    assert is_mushroom_class("mushroom_monk")
    assert is_mushroom_class("spore_mushroom_knight")
    assert not is_mushroom_class("druid")


@pytest.mark.parametrize("class_id", ["ranger", "druid", "wood_elf", "wilderness_scout", "conservationist"])
def test_caverns_forester_classes_include_outdoor_trackers(class_id: str) -> None:
    assert is_caverns_forester_class(class_id)


def test_toxic_mushrooms_ignore_trap_when_mushroom_leads(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    lead = _member("m", "Myc", class_id="mushroom_monk", marching_order=1)
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])

    log = roller.resolve_trap("toxic_mushrooms", 5, [lead], ["m"], show_rolls=False, explain_math=False)

    assert any("mushroom-class PC leads" in entry for entry in log)


def test_toxic_mushrooms_druid_gets_level_bonus_on_save(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    druid = _member("d", "Dara", class_id="druid", level=4)
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (5, [5]))

    log = roller.resolve_trap("toxic_mushrooms", 5, [druid], ["d"], show_rolls=False, explain_math=False)

    assert any("resists the toxic mushrooms" in entry for entry in log)
