"""TCOTFD p.8 — Wandering Alchemist expert skill eligibility."""

from __future__ import annotations

from typing import Any

from ..schemas import PartyMemberState
from .courtship_classes import is_wandering_alchemist
from .expert_skills import class_skill_codes, has_skill, learned_skill_ids, skill_allowed_for_member

WANDERING_ALCHEMIST_L1_SKILLS = frozenset(
    {
        "arcane_tanner",
        "create_holy_water",
        "poison_resistance",
        "protective_incense",
        "spore_alchemy",
    }
)

WANDERING_ALCHEMIST_EXCLUDED_HALFLING_SKILLS = frozenset(
    {
        "combat_acrobatics",
        "deadly_accuracy",
        "dead_shot",
        "knife_throwing",
    }
)


def _skill_id(skill: dict[str, Any]) -> str:
    return str(skill.get("id", "")).strip().lower()


def wandering_alchemist_halfling_skill(skill: dict[str, Any]) -> bool:
    skill_id = _skill_id(skill)
    if skill_id in WANDERING_ALCHEMIST_EXCLUDED_HALFLING_SKILLS:
        return False
    if skill_id in WANDERING_ALCHEMIST_L1_SKILLS:
        return False
    if skill.get("class_ids"):
        return False
    allowed = set(skill.get("classes") or [])
    return "H" in allowed


def wandering_alchemist_skill_min_level(member: PartyMemberState, skill: dict[str, Any]) -> int:
    skill_id = _skill_id(skill)
    if is_wandering_alchemist(member) and skill_id in WANDERING_ALCHEMIST_L1_SKILLS:
        return 1
    if is_wandering_alchemist(member) and wandering_alchemist_halfling_skill(skill):
        return int(skill.get("min_level", 5))
    return int(skill.get("min_level", 5))


def wandering_alchemist_skill_requires_expert_training(member: PartyMemberState, skill: dict[str, Any]) -> bool:
    skill_id = _skill_id(skill)
    if not is_wandering_alchemist(member):
        return True
    if skill_id in WANDERING_ALCHEMIST_L1_SKILLS:
        return False
    if wandering_alchemist_halfling_skill(skill):
        return True
    return True


def wandering_alchemist_skill_allowed(member: PartyMemberState, skill: dict[str, Any]) -> bool:
    if not is_wandering_alchemist(member):
        return skill_allowed_for_member(member, skill)
    skill_id = _skill_id(skill)
    if skill_id in WANDERING_ALCHEMIST_EXCLUDED_HALFLING_SKILLS:
        return False
    if skill_id in WANDERING_ALCHEMIST_L1_SKILLS:
        return True
    if wandering_alchemist_halfling_skill(skill):
        return True
    return skill_allowed_for_member(member, skill)


def eligible_wandering_alchemist_expert_skills(
    member: PartyMemberState, catalog: dict[str, Any]
) -> list[dict[str, Any]]:
    if not is_wandering_alchemist(member):
        return []
    learned = learned_skill_ids(member)
    eligible: list[dict[str, Any]] = []
    for skill in catalog.get("skills", []):
        skill_id = _skill_id(skill)
        if not skill_id or not wandering_alchemist_skill_allowed(member, skill):
            continue
        if member.level < wandering_alchemist_skill_min_level(member, skill):
            continue
        if wandering_alchemist_skill_requires_expert_training(member, skill) and not member.expert_trained:
            continue
        if skill_id in learned and not skill.get("repeatable"):
            continue
        eligible.append(skill)
    return eligible


def alchemist_has_eligible_expert_skills(member: PartyMemberState, catalog: dict[str, Any]) -> bool:
    return bool(eligible_wandering_alchemist_expert_skills(member, catalog))
