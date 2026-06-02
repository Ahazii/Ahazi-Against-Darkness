from __future__ import annotations

from pathlib import Path

from app.engine.dice import AdvancementRollResult
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.tier_skills import apply_tier_skill_learn, eligible_tier_skills
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


def test_heroic_skill_eligibility_requires_level_and_training() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    repo = RulesRepository(packaged, packaged / "_override")
    catalog = repo.heroic_skills()
    warrior = PartyMemberState(
        character_id="w",
        name="Veteran",
        class_id="warrior",
        class_name="Warrior",
        level=10,
        xp=0,
        gold=0,
        current_life=12,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
        heroic_trained=True,
    )
    skills = eligible_tier_skills(warrior, catalog, "heroic")
    assert any(skill["id"] == "battle_training" for skill in skills)


def test_learn_heroic_skill_on_success(monkeypatch) -> None:
    eng = engine()
    warrior = PartyMemberState(
        character_id="w",
        name="Veteran",
        class_id="warrior",
        class_name="Warrior",
        level=10,
        xp=0,
        gold=0,
        current_life=12,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
        heroic_trained=True,
    )
    session = _session(party=[warrior], xp_rolls_pending=1, xp_system="classical")
    monkeypatch.setattr(
        "app.engine.random_dungeon.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(
            natural=10, total=14, sides=10, modifier=4, purpose=purpose
        ),
    )
    eng.advance(
        session,
        "xp_roll",
        character_id="w",
        advancement_fork="learn_heroic_skill",
        heroic_skill_id="battle_training",
    )
    assert "battle_training" in warrior.learned_heroic_skills
    assert warrior.level == 10


def test_legendary_skill_requires_heroic_base() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    repo = RulesRepository(packaged, packaged / "_override")
    catalog = repo.legendary_skills()
    warrior = PartyMemberState(
        character_id="w",
        name="Legend",
        class_id="warrior",
        class_name="Warrior",
        level=15,
        xp=0,
        gold=0,
        current_life=16,
        max_life=16,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
        heroic_trained=True,
        legendary_trained=True,
        learned_heroic_skills=["battle_training"],
    )
    skills = eligible_tier_skills(warrior, catalog, "legendary")
    assert any(skill["id"] == "legendary_battle_training" for skill in skills)


def test_apply_tier_skill_learn_appends_name() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    repo = RulesRepository(packaged, packaged / "_override")
    member = PartyMemberState(
        character_id="w",
        name="Veteran",
        class_id="warrior",
        class_name="Warrior",
        level=10,
        xp=0,
        gold=0,
        current_life=12,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    log = apply_tier_skill_learn(member, "heroic_courage", repo.heroic_skills(), "heroic")
    assert "Heroic Courage" in log[0]
    assert "heroic_courage" in member.learned_heroic_skills


def test_tables_api_includes_heroic_and_legendary() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = client.get("/api/rules/tables").json()
    assert payload["heroic_skills_table"]
    assert payload["legendary_skills_table"]
    assert any("Battle Training" in row.get("skill", "") for row in payload["heroic_skills_table"])
