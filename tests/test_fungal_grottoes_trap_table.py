from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.fungal_traps import (
    fungal_trap_save_bonus,
    is_fungal_spore_immune,
    shrieking_mushroom_chance_reduction,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def _roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def _engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _member(
    character_id: str = "hero-1",
    name: str = "Hero",
    *,
    class_id: str = "warrior",
    level: int = 4,
    current_life: int | None = None,
    max_life: int | None = None,
    marching_order: int = 1,
    inventory: list[str] | None = None,
    default_melee_weapon: str | None = None,
) -> PartyMemberState:
    life = current_life if current_life is not None else (max_life if max_life is not None else 5)
    cap = max_life if max_life is not None else life
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id=class_id,
        class_name=class_id.replace("_", " ").title(),
        level=level,
        max_life=cap,
        current_life=life,
        marching_order=marching_order,
        inventory=list(inventory or []),
        default_melee_weapon=default_melee_weapon,
        gold=0,
        xp=0,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )


@pytest.mark.parametrize(
    ("roll", "trap_key"),
    [
        (1, "sleep_spores"),
        (2, "spore_cloud"),
        (3, "slime_patch"),
        (4, "mycelium_snare"),
        (5, "shrieking_mushroom"),
        (6, "cordyceps_trap"),
    ],
)
def test_fungal_trap_table_roll_maps_to_pdf_trap_keys(roll: int, trap_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: roll)
    outcome = roller.roll_trap(4, show_rolls=False, explain_math=False, environment="fungal_grottoes")
    assert outcome.trap_key == trap_key


def test_fungal_trap_save_bonus_uses_half_level_for_warriors() -> None:
    warrior = _member(class_id="warrior", level=4)
    assert fungal_trap_save_bonus(warrior, "spore_cloud") == 2


def test_fungal_trap_save_bonus_uses_level_for_halfling() -> None:
    halfling = _member(class_id="halfling", level=4)
    assert fungal_trap_save_bonus(halfling, "cordyceps_trap") == 4


def test_mushroom_monk_immune_to_fungal_spore_traps() -> None:
    monk = _member(class_id="mushroom_monk")
    assert is_fungal_spore_immune(monk)


def test_sleep_spores_slays_party_when_all_vulnerable_pcs_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roller = _roller()
    party = [_member("a", "Ada"), _member("b", "Bryn")]
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    rolls = iter([(1, [1]), (1, [1]), (1, [1])])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: next(rolls))

    log = roller.resolve_trap("sleep_spores", 4, party, ["a", "b"], show_rolls=False, explain_math=False)

    assert party[0].current_life == 0
    assert party[1].current_life == 0
    assert any("party is slain" in line for line in log)


def test_spore_cloud_trap_skips_immune_pc(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    monk = _member("m", "Mora", class_id="mushroom_monk")
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])

    log = roller.resolve_trap("spore_cloud", 4, [monk], ["m"], show_rolls=False, explain_math=False)

    assert any("immune to the spore cloud" in line for line in log)


def test_shrieking_mushroom_druid_reduces_chance(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    druid = _member("d", "Dara", class_id="druid")
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 3)

    log = roller.resolve_trap("shrieking_mushroom", 4, [druid], ["d"], show_rolls=False, explain_math=False)

    assert any("2-in-6" in line for line in log)
    assert shrieking_mushroom_chance_reduction(druid) == 2


def test_cordyceps_trap_resolves_immediate_attack_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    roller = _roller()
    party = [_member("a", "Ada"), _member("b", "Bryn", current_life=2, max_life=4)]
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = roller.resolve_trap("cordyceps_trap", 4, party, ["a", "b"], show_rolls=False, explain_math=False)

    assert "Cordyceps infected (6 turns)" in party[0].statuses
    assert any("cordyceps-driven attack" in line for line in log)


def test_cordyceps_victim_rises_as_boss_after_trap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eng = _engine()
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        objects=["Trap"],
        trap_key="cordyceps_trap",
        trap_level=4,
        enemies=[],
    )
    fallen = _member("b", "Bryn", current_life=0, max_life=4)
    fallen.statuses.append("Cordyceps victim")
    infected = _member("a", "Ada")
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        environment="fungal_grottoes",
        party=[infected, fallen],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr(eng, "_begin_combat", lambda *args, **kwargs: None)

    eng._resolve_cordyceps_boss_rises(session, tile, show_rolls=False)

    assert len(tile.enemies) == 1
    assert tile.enemies[0].category == "boss"
    assert tile.enemies[0].level == fallen.level
    assert any("rises as an undead boss" in line for line in session.log)


def test_mycelium_snare_pending_flow_via_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _engine()
    hero = _member(inventory=["Sword", "Lantern"], default_melee_weapon="Sword")
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        objects=["Trap"],
        trap_key="mycelium_snare",
        trap_level=4,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        environment="fungal_grottoes",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.choice", lambda items: items[0])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    eng._resolve_trap(session, show_rolls=False, explain_math=False)

    assert session.pending_mycelium_snare is not None
    assert session.pending_mycelium_snare.character_id == hero.character_id
    assert tile.trap_resolved is False
    assert "Lantern" in hero.inventory

    eng._resolve_trap(session, show_rolls=False, explain_math=False, snare_item_name="Lantern")

    assert session.pending_mycelium_snare is None
    assert tile.trap_resolved is True
    assert "Lantern" not in hero.inventory
    assert "Sword" in hero.inventory
    assert any("Lantern is snatched away forever" in line for line in session.log)


def test_slime_patch_skip_turn_when_wanderers_arrive(monkeypatch: pytest.MonkeyPatch) -> None:
    eng = _engine()
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        enemies=[],
    )
    fallen = _member()
    fallen.statuses.append("Fallen prone (slime patch)")
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        environment="fungal_grottoes",
        party=[fallen],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    trap_log = ["Slime Patch triggers a 1-in-6 Wandering Monsters check."]
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    monkeypatch.setattr(eng, "_spawn_wandering_monsters", lambda *args, **kwargs: None)

    eng._resolve_environment_trap_wandering_follow_up(
        session,
        tile,
        trap_key="slime_patch",
        trap_log=trap_log,
        show_rolls=False,
    )

    assert any("Slime patch skip (1 turn)" in status for status in fallen.statuses)
