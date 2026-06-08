from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def member(*, character_id: str = "h", name: str = "Hero", gold: int = 0, bank_gold: int = 0) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=gold,
        bank_gold=bank_gold,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )


def session_with_party(*, party: list[PartyMemberState], camped: bool = True) -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        camped_outside=camped,
        party=party,
        map_state=MapState(
            tiles=[
                TileState(
                    id="entrance",
                    x=0,
                    y=0,
                    tile_key="01",
                    tile_type="room",
                    title="Entrance",
                    description="Entrance",
                    content_key="entrance",
                )
            ],
            current_tile_id="entrance",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_deposit_party_bank_gold_moves_all_carried_gold() -> None:
    eng = engine()
    first = member(character_id="a", name="Alpha", gold=120, bank_gold=30)
    second = member(character_id="b", name="Bravo", gold=80, bank_gold=0)
    session = session_with_party(party=[first, second])

    eng.advance(session, "deposit_party_bank_gold")

    assert first.gold == 0
    assert first.bank_gold == 150
    assert second.gold == 0
    assert second.bank_gold == 80
    assert any("Party deposits" in entry for entry in session.log)


def test_withdraw_bank_gold_respects_carry_limit() -> None:
    eng = engine()
    hero = member(gold=150, bank_gold=100)
    session = session_with_party(party=[hero])

    eng.advance(session, "withdraw_bank_gold", character_id="h", gold_amount=100)

    assert hero.gold == 200
    assert hero.bank_gold == 50
    assert any("withdraws 50gp" in entry for entry in session.log)


def test_bank_is_unavailable_inside_dungeon() -> None:
    eng = engine()
    hero = member(gold=50, bank_gold=100)
    session = session_with_party(party=[hero], camped=False)

    eng.advance(session, "deposit_bank_gold", character_id="h")
    eng.advance(session, "withdraw_bank_gold", character_id="h")

    assert hero.gold == 50
    assert hero.bank_gold == 100
    assert sum("available only while camped outside" in entry for entry in session.log) == 2
