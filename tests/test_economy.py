from __future__ import annotations

from pathlib import Path

from app.engine.combat import CombatRound
from app.engine.experience import MINOR_ENCOUNTERS_FOR_XP
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def test_minor_encounter_tracks_toward_xp() -> None:
    eng = engine()
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    defeated = [
        EnemyState(id="1", name="Rat", category="vermin", level=2, life=0, max_life=1),
        EnemyState(id="2", name="Rat", category="vermin", level=2, life=0, max_life=1),
    ]
    for _ in range(MINOR_ENCOUNTERS_FOR_XP):
        eng._award_encounter_xp(session, defeated, show_rolls=False)
    assert session.xp_rolls_pending == 1
    assert session.minor_encounters_defeated == 0


def test_major_foe_grants_xp_roll() -> None:
    eng = engine()
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng._award_encounter_xp(
        session,
        [EnemyState(id="b", name="Ogre", category="boss", level=5, life=0, max_life=6)],
        show_rolls=False,
    )
    assert session.xp_rolls_pending == 1


def test_xp_roll_levels_up_on_six(monkeypatch) -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
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
    monkeypatch.setattr("app.engine.random_dungeon.perform_advancement_roll", lambda member_or_level, bonus=0, purpose="level_up": __import__("app.engine.dice", fromlist=["AdvancementRollResult"]).AdvancementRollResult(natural=6, total=6, sides=6, modifier=bonus))
    eng.advance(session, "xp_roll", character_id="h", advancement_fork="level_up")
    assert hero.level == 2
    assert hero.max_life == 8
    assert hero.current_life == 4
    assert session.xp_rolls_pending == 0


def test_expert_tier_xp_roll_levels_up(monkeypatch) -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Veteran",
        class_id="warrior",
        class_name="Warrior",
        level=6,
        xp=0,
        gold=0,
        current_life=8,
        max_life=12,
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
    from app.engine.dice import AdvancementRollResult

    monkeypatch.setattr(
        "app.engine.random_dungeon.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(natural=8, total=10, sides=8, modifier=2),
    )
    eng.advance(session, "xp_roll", character_id="h", advancement_fork="level_up")
    assert hero.level == 7
    assert session.xp_rolls_pending == 0


def test_buy_healing_costs_gold() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=20,
        current_life=2,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        healer_available=True,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "buy_healing", character_id="h")
    assert hero.current_life == 3
    assert hero.gold == 10


def test_old_school_xp_and_level_up() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        xp_system="old_school",
        old_school_xp_tally=300,
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "old_school_level_up", character_id="h")
    assert hero.level == 2
    assert session.old_school_xp_tally == 0


def test_slower_advancement_banks_xp() -> None:
    eng = engine()
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        xp_system="slower_advancement",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng._grant_xp_credit(session, 1, "Test:")
    assert session.slower_xp_bank == 1
    assert session.xp_rolls_pending == 0


def test_three_clues_stay_held_until_secret_revealed() -> None:
    eng = engine()
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    tile = session.map_state.tiles[0]
    for _ in range(3):
        eng._grant_clue(session, tile)
    assert session.xp_rolls_pending == 0
    assert session.clues_found == 3

    eng.advance(session, "reveal_secret_with_clues")
    assert session.xp_rolls_pending == 1
    assert session.clues_found == 0


def test_clues_can_teach_eligible_expert_spell() -> None:
    eng = engine()
    wizard = PartyMemberState(
        character_id="wiz",
        name="Magus",
        class_id="wizard",
        class_name="Wizard",
        level=5,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=[],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        clues_found=3,
        party=[wizard],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    eng.advance(session, "learn_spell_with_clues", character_id="wiz", expert_skill_id="healing_surge")

    assert session.clues_found == 0
    assert "healing_surge" in wizard.learned_expert_skills
    assert "Healing Surge" in wizard.spells


def test_clues_do_not_teach_missing_druid_catalog_spell() -> None:
    eng = engine()
    druid = PartyMemberState(
        character_id="d",
        name="Oak",
        class_id="druid",
        class_name="Druid",
        level=5,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=[],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        clues_found=3,
        party=[druid],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    eng.advance(session, "learn_spell_with_clues", character_id="d", expert_skill_id="healing_surge")

    assert session.clues_found == 3
    assert druid.learned_expert_skills == []
    assert any("druid expert-spell catalog" in line.lower() for line in session.log)
