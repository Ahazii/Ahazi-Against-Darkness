from __future__ import annotations

from pathlib import Path

from app.engine.death_recovery import (
    RESURRECTION_COST_GP,
    accept_fallen_loss,
    deliver_carried_body_outside,
    start_carrying_body,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def hero(*, character_id: str, name: str, life: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=2,
        xp=0,
        gold=50,
        current_life=life,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon"],
    )


def session_with_fallen() -> SessionState:
    carrier = hero(character_id="carrier", name="Carrier")
    fallen = hero(character_id="fallen", name="Fallen", life=0)
    tile = TileState(
        id="tile",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        fallen_character_ids=["fallen"],
    )
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[carrier, fallen],
        map_state=MapState(tiles=[tile], current_tile_id="tile"),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def test_carry_body_moves_to_rearguard() -> None:
    session = session_with_fallen()
    tile = session.map_state.tiles[0]
    log = start_carrying_body(session, tile, "carrier", "fallen")
    assert session.carried_body_id == "fallen"
    assert session.body_carrier_id == "carrier"
    assert "fallen" not in tile.fallen_character_ids
    assert session.party[0].marching_order >= 3
    assert any("carries" in entry for entry in log)


def test_deliver_body_outside_redistributes_gear() -> None:
    session = session_with_fallen()
    tile = session.map_state.tiles[0]
    start_carrying_body(session, tile, "carrier", "fallen")
    fallen = session.party[1]
    fallen.gold = 20
    log = deliver_carried_body_outside(session)
    assert session.carried_body_id is None
    assert "fallen" in session.fallen_outside_character_ids
    assert session.party[0].gold > 50
    assert fallen.gold == 0
    assert any("outside" in entry.lower() for entry in log)


def test_resurrection_success(monkeypatch) -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = session_with_fallen()
    session.party[0].gold = RESURRECTION_COST_GP
    session.party[1].statuses = ["Fallen"]
    session.fallen_outside_character_ids = ["fallen"]
    monkeypatch.setattr("app.engine.death_recovery.roll_d6", lambda: 2)
    engine.advance(session, "attempt_resurrection", target_character_id="fallen")
    assert session.party[1].current_life == session.party[1].max_life
    assert "Fallen" not in session.party[1].statuses
    assert "fallen" not in session.fallen_outside_character_ids


def test_level_six_resurrection_is_automatic(monkeypatch) -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = session_with_fallen()
    session.party[0].gold = RESURRECTION_COST_GP
    session.party[1].level = 6
    session.party[1].max_life = 8
    session.fallen_outside_character_ids = ["fallen"]
    monkeypatch.setattr(
        "app.engine.death_recovery.roll_d6",
        lambda: (_ for _ in ()).throw(AssertionError("L6 resurrection should not roll")),
    )
    engine.advance(session, "attempt_resurrection", target_character_id="fallen")
    assert session.party[1].current_life == 8
    assert "fallen" not in session.fallen_outside_character_ids


def test_preserve_corpse_improves_resurrection_target(monkeypatch) -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = session_with_fallen()
    session.party[0].gold = RESURRECTION_COST_GP
    session.party[0].learned_heroic_skills = ["preserve_corpse"]
    session.fallen_outside_character_ids = ["fallen"]
    monkeypatch.setattr("app.engine.death_recovery.roll_d6", lambda: 3)
    engine.advance(session, "attempt_resurrection", target_character_id="fallen")
    assert session.party[1].current_life == session.party[1].max_life
    assert "fallen" not in session.fallen_outside_character_ids


def test_resurrection_can_use_home_bank_gold(monkeypatch) -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = session_with_fallen()
    session.party[0].gold = 0
    session.party[0].bank_gold = RESURRECTION_COST_GP
    session.fallen_outside_character_ids = ["fallen"]
    monkeypatch.setattr("app.engine.death_recovery.roll_d6", lambda: 2)
    engine.advance(session, "attempt_resurrection", target_character_id="fallen")
    assert session.party[0].bank_gold == 0
    assert session.party[1].current_life == session.party[1].max_life
    assert any("home bank" in entry for entry in session.log)


def test_holy_symbol_of_healing_pays_for_cleric_resurrection(monkeypatch) -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = session_with_fallen()
    fallen = session.party[1]
    fallen.class_id = "cleric"
    fallen.class_name = "Cleric"
    fallen.inventory = ["Hand weapon", "Holy symbol of healing"]
    fallen.gold = 0
    session.party[0].gold = 0
    start_carrying_body(session, session.map_state.tiles[0], "carrier", "fallen")
    log = deliver_carried_body_outside(session)
    assert fallen.inventory == ["Holy symbol of healing"]
    assert any("remains with the body" in entry for entry in log)

    monkeypatch.setattr("app.engine.death_recovery.roll_d6", lambda: 2)
    engine.advance(session, "attempt_resurrection", target_character_id="fallen")

    assert fallen.current_life == fallen.max_life
    assert "Holy symbol of healing" not in fallen.inventory
    assert session.party[0].gold == 0
    assert any("temple pays for the resurrection attempt" in entry for entry in session.log)


def test_accept_fallen_loss_marks_permanently_lost() -> None:
    session = session_with_fallen()
    session.fallen_outside_character_ids = ["fallen"]
    log = accept_fallen_loss(session, "fallen")
    assert "fallen" not in session.fallen_outside_character_ids
    assert "fallen" in session.permanently_lost_character_ids
    assert any("lost forever" in entry for entry in log)
