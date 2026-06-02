from __future__ import annotations

from typing import Any, Literal

from ..schemas import PartyMemberState
from .expert_skills import class_skill_codes
from .tier_advancement import AdvancementPurpose, effective_action_tier_band, training_from_member

SkillTier = Literal["expert", "heroic", "legendary"]

ADVANCEMENT_FORKS: dict[str, AdvancementPurpose] = {
    "level_up": "level_up",
    "learn_expert_skill": "learn_expert_skill",
    "learn_heroic_skill": "learn_heroic_skill",
    "learn_legendary_skill": "learn_legendary_skill",
}


def learned_tier_skill_ids(member, tier: SkillTier) -> set[str]:
    field = {
        "expert": "learned_expert_skills",
        "heroic": "learned_heroic_skills",
        "legendary": "learned_legendary_skills",
    }[tier]
    ids: set[str] = set()
    for item in getattr(member, field, []) or []:
        ids.add(str(item).strip().lower().split(":", 1)[0])
    return ids


def has_tier_skill(member, skill_id: str, tier: SkillTier | None = None) -> bool:
    needle = skill_id.strip().lower()
    tiers: tuple[SkillTier, ...] = (tier,) if tier else ("expert", "heroic", "legendary")
    return any(needle in learned_tier_skill_ids(member, band) for band in tiers)


def skill_allowed_for_member(member: PartyMemberState, skill: dict[str, Any]) -> bool:
    class_ids = skill.get("class_ids") or []
    if class_ids:
        return member.class_id.strip().lower() in {str(item).strip().lower() for item in class_ids}
    codes = class_skill_codes(member.class_id)
    if not codes:
        return False
    allowed = set(skill.get("classes") or [])
    return any(code in allowed for code in codes)


def eligible_tier_skills(member: PartyMemberState, catalog: dict[str, Any], tier: SkillTier) -> list[dict[str, Any]]:
    min_level = int(catalog.get("min_level_default", 10 if tier == "heroic" else 15))
    if member.level < min_level:
        return []
    training = training_from_member(member)
    band = effective_action_tier_band(member.level, training)
    if tier == "heroic" and band < 3:
        return []
    if tier == "legendary" and band < 4:
        return []
    learned = learned_tier_skill_ids(member, tier)
    eligible: list[dict[str, Any]] = []
    for skill in catalog.get("skills", []):
        skill_id = str(skill.get("id", "")).strip().lower()
        if not skill_id or not skill_allowed_for_member(member, skill):
            continue
        if skill_id in learned and not skill.get("repeatable"):
            continue
        if tier == "legendary":
            base_id = str(skill.get("upgrades", "")).strip().lower()
            if base_id and base_id not in learned_tier_skill_ids(member, "heroic"):
                continue
        eligible.append(skill)
    return eligible


def validate_tier_skill_choice(member: PartyMemberState, skill_id: str, catalog: dict[str, Any], tier: SkillTier) -> str | None:
    normalized = skill_id.strip().lower()
    min_level = int(catalog.get("min_level_default", 10 if tier == "heroic" else 15))
    if member.level < min_level:
        return f"{member.name} must reach Level {min_level} before learning {tier} skills."
    for skill in eligible_tier_skills(member, catalog, tier):
        if str(skill.get("id", "")).strip().lower() == normalized:
            return None
    return f"{skill_id} is not available for {member.name}."


def apply_tier_skill_learn(member: PartyMemberState, skill_id: str, catalog: dict[str, Any], tier: SkillTier) -> list[str]:
    normalized = skill_id.strip().lower()
    field = {
        "expert": "learned_expert_skills",
        "heroic": "learned_heroic_skills",
        "legendary": "learned_legendary_skills",
    }[tier]
    bucket = list(getattr(member, field, []) or [])
    for skill in catalog.get("skills", []):
        if str(skill.get("id", "")).strip().lower() != normalized:
            continue
        name = str(skill.get("name", skill_id))
        if normalized not in {item.split(":", 1)[0] for item in bucket} or skill.get("repeatable"):
            bucket.append(normalized)
            setattr(member, field, bucket)
        if name not in member.abilities:
            member.abilities.append(name)
        tier_label = tier.title()
        return [f"{member.name} learns {tier_label.lower()} skill {name}."]
    return [f"Unknown {tier} skill {skill_id}."]


def available_advancement_forks(member: PartyMemberState) -> list[str]:
    forks = ["level_up"]
    training = training_from_member(member)
    band = effective_action_tier_band(member.level, training)
    if member.level >= 5:
        forks.append("learn_expert_skill")
    if member.level >= 10 and band >= 3:
        forks.append("learn_heroic_skill")
    if member.level >= 15 and band >= 4:
        forks.append("learn_legendary_skill")
    return forks


def advancement_fork_label(fork: str) -> str:
    return {
        "level_up": "Level-up",
        "learn_expert_skill": "Expert skill",
        "learn_heroic_skill": "Heroic skill",
        "learn_legendary_skill": "Legendary skill",
    }.get(fork, fork.replace("_", " ").title())


def tier_skills_table_rows(catalog: dict[str, Any], tier: SkillTier) -> list[dict[str, str]]:
    from .heroic_skill_effects import LEGENDARY_SKILL_MECHANICS, HEROIC_SKILL_MECHANICS, tier_skill_status

    codes = catalog.get("class_codes", {})
    mechanics = HEROIC_SKILL_MECHANICS if tier == "heroic" else LEGENDARY_SKILL_MECHANICS
    rows: list[dict[str, str]] = []
    for skill in catalog.get("skills", []):
        skill_id = str(skill.get("id", "")).strip().lower()
        class_names = ", ".join(str(codes.get(code, code)) for code in skill.get("classes", []))
        rows.append(
            {
                "skill": str(skill.get("name", "")),
                "classes": class_names,
                "category": str(skill.get("category", "")),
                "mechanic": mechanics.get(skill_id, ""),
                "status": tier_skill_status(skill_id, tier),
                "upgrades": str(skill.get("upgrades", "")),
            }
        )
    return rows


CLASS_TRICKS_IMPLEMENTATION: list[dict[str, str]] = [
    {"tier": "2", "class": "Acrobat", "ability": "Shift Position / Distract / Evade / Double Kick", "status": "wired"},
    {"tier": "2", "class": "Assassin", "ability": "Hide in Shadows", "status": "wired"},
    {"tier": "2", "class": "Illusionist", "ability": "Distract (all minions)", "status": "wired"},
    {"tier": "2", "class": "Gnome", "ability": "Smokescreen / gadget door / trap bonus", "status": "wired"},
    {"tier": "2", "class": "Mushroom monk", "ability": "Spore cloud", "status": "wired"},
    {"tier": "2", "class": "Paladin", "ability": "Summon Steed", "status": "wired"},
    {"tier": "3", "class": "Acrobat", "ability": "Graceful Move", "status": "wired", "mechanic": "Bank a social Save reroll (Lady in White impress check)."},
    {"tier": "3", "class": "Mushroom monk", "ability": "Hyphae communion", "status": "wired", "mechanic": "+1 on the next Search on this tile."},
    {"tier": "3", "class": "Kukla", "ability": "Army of Dolls", "status": "wired", "mechanic": "Deploy doll; per-round attack at −1 each combat round."},
    {"tier": "3", "class": "Bulwark", "ability": "Sacrifice Defense", "status": "wired", "mechanic": "Intercept ally hit with your Defense roll."},
    {"tier": "3", "class": "Bulwark", "ability": "Sacrifice Shield", "status": "wired", "mechanic": "Negate one hit; forfeit shield until fight ends."},
    {"tier": "4", "class": "Paladin", "ability": "Divine Smite", "status": "wired", "mechanic": "Once/adventure +3 Life vs one major foe on successful hit."},
]


def class_tricks_implementation_rows() -> list[dict[str, str]]:
    return [dict(row) for row in CLASS_TRICKS_IMPLEMENTATION]
