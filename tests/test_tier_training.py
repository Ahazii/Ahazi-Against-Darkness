from __future__ import annotations

from pathlib import Path

from app.engine.experience import spend_classical_training_xp
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def test_spend_classical_training_xp_uses_assigned_rolls_before_party_rolls() -> None:
    hero = PartyMemberState(
        character_id="h",
        name="Adept",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        xp=1,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        xp_rolls_pending=2,
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    ok, log, assigned_spent, party_spent = spend_classical_training_xp(session, hero, 2)

    assert ok is True
    assert (assigned_spent, party_spent) == (1, 1)
    assert hero.xp == 0
    assert session.xp_rolls_pending == 1
    assert log == [
        "Adept spends 1 assigned XP roll(s).",
        "Adept spends 1 pending party XP roll(s).",
    ]


def test_enter_expert_tier_with_gold() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Adept",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        xp=0,
        gold=600,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "enter_tier_training", character_id="h", tier_training="expert")
    assert hero.expert_trained
    assert hero.gold == 100


def test_enter_expert_tier_with_banked_xp_roll() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Adept",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        xp_rolls_pending=1,
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(
        session,
        "enter_tier_training",
        character_id="h",
        tier_training="expert",
        use_xp_for_tier=True,
    )
    assert hero.expert_trained
    assert session.xp_rolls_pending == 0
    assert hero.level == 5


def test_enter_heroic_tier_requires_xp_and_gold() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Champion",
        class_id="warrior",
        class_name="Warrior",
        level=9,
        xp=0,
        gold=0,
        current_life=12,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
    )
    payer = PartyMemberState(
        character_id="p",
        name="Patron",
        class_id="warrior",
        class_name="Warrior",
        level=9,
        xp=0,
        gold=2000,
        current_life=12,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
    )
    session = SessionState(
        id="s",
        party_id="pid",
        adventure_id="a",
        adventure_type="random",
        xp_rolls_pending=2,
        party=[hero, payer],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "enter_tier_training", character_id="h", tier_training="heroic")
    assert hero.heroic_trained
    assert session.xp_rolls_pending == 0
    assert payer.gold == 1000


def test_enter_heroic_tier_can_use_home_bank_gold() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Champion",
        class_id="warrior",
        class_name="Warrior",
        level=9,
        xp=0,
        gold=0,
        bank_gold=1000,
        current_life=12,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
    )
    session = SessionState(
        id="s",
        party_id="pid",
        adventure_id="a",
        adventure_type="random",
        xp_rolls_pending=2,
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "enter_tier_training", character_id="h", tier_training="heroic")
    assert hero.heroic_trained
    assert hero.bank_gold == 0
    assert any("home bank" in entry for entry in session.log)


def test_enter_epic_tier_requires_xp_and_gold() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Paragon",
        class_id="warrior",
        class_name="Warrior",
        level=19,
        xp=0,
        gold=5000,
        current_life=20,
        max_life=20,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
        heroic_trained=True,
        legendary_trained=True,
    )
    session = SessionState(
        id="s",
        party_id="pid",
        adventure_id="a",
        adventure_type="random",
        xp_rolls_pending=5,
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "enter_tier_training", character_id="h", tier_training="epic")
    assert hero.epic_trained
    assert session.xp_rolls_pending == 0
    assert hero.gold == 1000
