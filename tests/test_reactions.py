from __future__ import annotations

from pathlib import Path

from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.reactions import build_reaction_outcome, reaction_table_for_enemies
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def combat_session(*, enemies: list[EnemyState], party_gold: int = 100) -> SessionState:
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=party_gold,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        reaction_pending=True,
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=enemies,
                    initial_enemy_count=len(enemies),
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def test_reaction_table_selection() -> None:
    assert reaction_table_for_enemies([EnemyState(id="1", name="Rat", category="vermin", level=2, life=1, max_life=1)]) == "vermin_reaction_table"
    assert reaction_table_for_enemies([EnemyState(id="2", name="Goblin", category="minions", level=3, life=1, max_life=1)]) == "minion_reaction_table"
    assert reaction_table_for_enemies([EnemyState(id="3", name="Dragon", category="boss", level=8, life=8, max_life=8)]) == "major_reaction_table"


def test_bribe_gold_scales_with_foes() -> None:
    row = {"key": "bribe", "result": "Pay up.", "gold_per_foe": 5}
    outcome = build_reaction_outcome(row, hcl=3, foe_count=4)
    assert outcome.bribe_gold == 20


def test_check_reaction_peaceful_ends_combat(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)]
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    monkeypatch.setattr(
        engine.table_roller,
        "roll_reaction",
        lambda table_name, roll: {"key": "peaceful", "result": "The goblins ignore you."},
    )
    engine.advance(session, "check_reaction")
    assert session.mode == "exploration"
    assert any("peacefully" in entry.lower() for entry in session.log)


def test_pay_bribe_deducts_gold(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)],
        party_gold=20,
    )
    session.reaction_checked = True
    session.reaction_key = "bribe"
    session.reaction_bribe_gold = 15
    engine.advance(session, "pay_bribe", pay_bribe=True)
    assert session.mode == "exploration"
    assert session.party[0].gold == 5


def test_basic_spells_table_has_six_entries() -> None:
    roller = DungeonTableRoller.from_rules(packaged_rules())
    for roll in range(1, 7):
        row = roller.lookup("basic_spells_table", roll)
        assert row is not None
        assert row["spell"]
