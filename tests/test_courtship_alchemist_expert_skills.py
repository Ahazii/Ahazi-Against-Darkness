"""Wandering Alchemist L1 and halfling expert skill eligibility (TCOTFD p.8-9)."""

from __future__ import annotations

from app.engine.courtship_alchemist_expert_skills import eligible_wandering_alchemist_expert_skills
from app.engine.expert_skills import validate_expert_skill_choice
from app.engine.tier_skills import available_advancement_forks
from tests.test_forsaken_depths_engine import _party_member, engine


def _alchemist(**overrides):
    member = _party_member()
    member.class_id = "wandering_alchemist"
    for key, value in overrides.items():
        setattr(member, key, value)
    return member


def test_l1_expert_skills_without_expert_training() -> None:
    eng = engine()
    catalog = eng.rules.expert_skills()
    member = _alchemist(level=1, expert_trained=False)
    eligible = eligible_wandering_alchemist_expert_skills(member, catalog)
    ids = {skill["id"] for skill in eligible}
    assert "arcane_tanner" in ids
    assert "create_holy_water" in ids
    assert "spore_alchemy" in ids
    assert validate_expert_skill_choice(member, "arcane_tanner", catalog) is None
    assert "learn_expert_skill" in available_advancement_forks(member)


def test_halfling_expert_skills_require_expert_training() -> None:
    catalog = engine().rules.expert_skills()
    member = _alchemist(level=6, expert_trained=False)
    eligible = eligible_wandering_alchemist_expert_skills(member, catalog)
    assert not any(skill["id"] == "negotiator" for skill in eligible)
    member.expert_trained = True
    eligible = eligible_wandering_alchemist_expert_skills(member, catalog)
    assert any(skill["id"] == "negotiator" for skill in eligible)
    assert not any(skill["id"] == "dead_shot" for skill in eligible)


def test_excluded_halfling_skills_blocked() -> None:
    catalog = engine().rules.expert_skills()
    member = _alchemist(level=6, expert_trained=True)
    assert validate_expert_skill_choice(member, "dead_shot", catalog) is not None
    assert validate_expert_skill_choice(member, "negotiator", catalog) is None
