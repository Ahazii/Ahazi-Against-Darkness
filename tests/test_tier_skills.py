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
    assert payload["class_tricks_implementation_table"]
    assert payload["ee_class_trick_flags_table"]
    assert any("Battle Training" in row.get("skill", "") for row in payload["heroic_skills_table"])


def test_class_tricks_implementation_table_wired() -> None:
    from app.engine.tier_skills import CLASS_TRICKS_IMPLEMENTATION, class_tricks_implementation_rows

    rows = class_tricks_implementation_rows()
    assert len(rows) == len(CLASS_TRICKS_IMPLEMENTATION)
    wired = [row for row in rows if row.get("status") == "wired"]
    planned = [row for row in rows if row.get("status") == "planned"]
    assert len(wired) == 25
    assert len(planned) == 0
    assert all(row.get("status") == "wired" for row in wired)


def test_ee_class_trick_flags_table_separates_non_abyss_flags() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    payload = TestClient(app).get("/api/rules/tables").json()
    rows = payload["ee_class_trick_flags_table"]
    names = {row["flag"] for row in rows}
    assert names == {
        "Stealth Training",
        "Sacrifice Defense",
        "Sacrifice Shield",
        "Army of Dolls",
        "Divine Smite",
    }
    assert {row["source_page"] for row in rows} == {"26", "44", "55", "79"}


def test_all_heroic_and_legendary_skills_wired() -> None:
    from app.engine.heroic_skill_effects import (
        HEROIC_SKILL_MECHANICS,
        LEGENDARY_SKILL_MECHANICS,
        WIRED_HEROIC,
        WIRED_LEGENDARY,
        tier_skill_status,
    )

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    repo = RulesRepository(packaged, packaged / "_override")
    heroic_ids = {str(skill["id"]).strip().lower() for skill in repo.heroic_skills().get("skills", [])}
    legendary_ids = {str(skill["id"]).strip().lower() for skill in repo.legendary_skills().get("skills", [])}

    assert heroic_ids == set(HEROIC_SKILL_MECHANICS)
    assert legendary_ids == set(LEGENDARY_SKILL_MECHANICS)
    assert WIRED_HEROIC == set(HEROIC_SKILL_MECHANICS)
    assert WIRED_LEGENDARY == set(LEGENDARY_SKILL_MECHANICS)
    for skill_id in heroic_ids:
        assert tier_skill_status(skill_id, "heroic") == "wired"
    for skill_id in legendary_ids:
        assert tier_skill_status(skill_id, "legendary") == "wired"
