from __future__ import annotations

from pathlib import Path

from app.engine.dice import AdvancementRollResult
from app.engine.expert_skills import eligible_expert_skills, validate_expert_skill_choice
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _session(*, party: list[PartyMemberState], **kwargs) -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=party,
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        **kwargs,
    )


def test_warrior_eligible_expert_skills() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    catalog = RulesRepository(packaged, packaged / "_override").expert_skills()
    warrior = PartyMemberState(
        character_id="w",
        name="Tank",
        class_id="warrior",
        class_name="Warrior",
        level=6,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    skills = eligible_expert_skills(warrior, catalog)
    ids = {skill["id"] for skill in skills}
    assert "shield_bash" in ids
    assert "strong_will" not in ids


def test_learn_expert_skill_on_success(monkeypatch) -> None:
    eng = engine()
    warrior = PartyMemberState(
        character_id="w",
        name="Tank",
        class_id="warrior",
        class_name="Warrior",
        level=6,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
    )
    session = _session(party=[warrior], xp_rolls_pending=1)
    monkeypatch.setattr(
        "app.engine.random_dungeon.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(
            natural=8, total=10, sides=8, modifier=2, purpose=purpose
        ),
    )
    eng.advance(
        session,
        "xp_roll",
        character_id="w",
        advancement_fork="learn_expert_skill",
        expert_skill_id="shield_bash",
    )
    assert warrior.level == 6
    assert "shield_bash" in warrior.learned_expert_skills
    assert "Shield Bash" in warrior.abilities
    assert session.xp_rolls_pending == 0


def test_expert_skill_requires_choice_at_l5(monkeypatch) -> None:
    eng = engine()
    warrior = PartyMemberState(
        character_id="w",
        name="Tank",
        class_id="warrior",
        class_name="Warrior",
        level=6,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = _session(party=[warrior], xp_rolls_pending=1)
    eng.advance(session, "xp_roll", character_id="w")
    assert session.xp_rolls_pending == 1
    assert warrior.level == 6


def test_expert_skills_api_and_home_tables() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    catalog = client.get("/api/rules/expert-skills").json()
    assert len(catalog.get("skills", [])) >= 40
    payload = client.get("/api/rules/tables").json()
    assert payload["expert_skills_table"]
    assert payload["expert_spells_table"]
    assert payload["tier_training_costs_table"]


def test_validate_blocks_duplicate_skill() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    catalog = RulesRepository(packaged, packaged / "_override").expert_skills()
    warrior = PartyMemberState(
        character_id="w",
        name="Tank",
        class_id="warrior",
        class_name="Warrior",
        level=6,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        learned_expert_skills=["shield_bash"],
    )
    assert validate_expert_skill_choice(warrior, "shield_bash", catalog) is not None
