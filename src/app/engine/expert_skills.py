from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..schemas import PartyMemberState

# Abyss class codes plus Expanded Edition archetype mappings.
CLASS_SKILL_CODES: dict[str, list[str]] = {
    "warrior": ["W"],
    "barbarian": ["B"],
    "cleric": ["C"],
    "rogue": ["R"],
    "wizard": ["Wi"],
    "elf": ["E"],
    "dwarf": ["D"],
    "halfling": ["H"],
    "swashbuckler": ["S"],
    "paladin": ["C", "W"],
    "druid": ["Wi", "C"],
    "illusionist": ["Wi"],
    "assassin": ["R"],
    "acrobat": ["H", "E"],
    "bulwark": ["W", "D"],
    "gnome": ["H", "Wi"],
    "kukla": ["H"],
    "mushroom_monk": ["H", "B"],
    "ranger": ["E", "H", "R"],
    "light_gladiator": ["W", "B"],
    "wandering_alchemist": ["H"],
    "satyr": ["B"],
    "conservationist": ["Wi", "C"],
    "demonologist": ["Wi"],
    "cambion": ["R", "C"],
    "succubus": ["R", "C"],
}


def expert_skills_catalog(raw: dict[str, Any]) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def class_skill_codes(class_id: str) -> list[str]:
    return list(CLASS_SKILL_CODES.get(class_id.strip().lower(), []))


def skill_allowed_for_member(member: PartyMemberState, skill: dict[str, Any]) -> bool:
    class_ids = skill.get("class_ids") or []
    if class_ids:
        return member.class_id.strip().lower() in {str(item).strip().lower() for item in class_ids}
    codes = class_skill_codes(member.class_id)
    if not codes:
        return False
    allowed = set(skill.get("classes") or [])
    return any(code in allowed for code in codes)


def learned_skill_ids(member) -> set[str]:
    ids: set[str] = set()
    for item in member.learned_expert_skills:
        text = item.strip().lower()
        ids.add(text.split(":", 1)[0])
    return ids


def has_skill(member: PartyMemberState, skill_id: str) -> bool:
    return skill_id.strip().lower() in learned_skill_ids(member)


def eligible_expert_skills(member: PartyMemberState, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    from .courtship_alchemist_expert_skills import eligible_wandering_alchemist_expert_skills
    from .courtship_classes import is_wandering_alchemist

    if is_wandering_alchemist(member):
        return eligible_wandering_alchemist_expert_skills(member, catalog)

    min_level = int(catalog.get("min_level_default", 5))
    if member.level < min_level:
        return []
    if not member.expert_trained:
        return []
    learned = learned_skill_ids(member)
    eligible: list[dict[str, Any]] = []
    for skill in catalog.get("skills", []):
        skill_id = str(skill.get("id", "")).strip().lower()
        if not skill_id or not skill_allowed_for_member(member, skill):
            continue
        skill_min = int(skill.get("min_level", catalog.get("min_level_default", 5)))
        if member.level < skill_min:
            continue
        if skill_id in learned and not skill.get("repeatable"):
            continue
        eligible.append(skill)
    return eligible


def member_can_learn_expert_skills(member: PartyMemberState, catalog: dict[str, Any]) -> bool:
    from .courtship_classes import is_wandering_alchemist

    if is_wandering_alchemist(member):
        return bool(eligible_expert_skills(member, catalog))
    return member.level >= int(catalog.get("min_level_default", 5)) and member.expert_trained


def eligible_expert_spells(member: PartyMemberState, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    if not member.expert_trained:
        return []
    codes = class_skill_codes(member.class_id)
    if not any(code in {"Wi", "E"} for code in codes):
        return []
    learned = learned_skill_ids(member)
    eligible: list[dict[str, Any]] = []
    for spell in catalog.get("expert_spells", []):
        spell_id = str(spell.get("id", "")).strip().lower()
        if not spell_id:
            continue
        min_level = int(spell.get("min_level", catalog.get("min_level_default", 5)))
        if member.level < min_level:
            continue
        allowed = set(spell.get("classes") or [])
        if not any(code in allowed for code in codes):
            continue
        if spell_id in learned:
            continue
        eligible.append({**spell, "kind": "expert_spell"})
    return eligible


def validate_expert_skill_choice(
    member: PartyMemberState,
    skill_id: str,
    catalog: dict[str, Any],
) -> str | None:
    normalized = skill_id.strip().lower()
    from .courtship_alchemist_expert_skills import wandering_alchemist_skill_requires_expert_training
    from .courtship_classes import is_wandering_alchemist

    if is_wandering_alchemist(member):
        for skill in eligible_expert_skills(member, catalog):
            if str(skill.get("id", "")).strip().lower() == normalized:
                return None
        if not member.expert_trained and any(
            wandering_alchemist_skill_requires_expert_training(member, skill)
            for skill in catalog.get("skills", [])
            if str(skill.get("id", "")).strip().lower() == normalized
        ):
            return f"{member.name} needs Expert training before learning that expert skill."
        return f"{skill_id} is not available for {member.name}."
    if member.level < int(catalog.get("min_level_default", 5)):
        return f"{member.name} must reach Level 5 before learning expert skills."
    if not member.expert_trained:
        return f"{member.name} needs Expert training before learning expert skills or spells."
    for skill in eligible_expert_skills(member, catalog):
        if str(skill.get("id", "")).strip().lower() == normalized:
            return None
    for spell in eligible_expert_spells(member, catalog):
        if str(spell.get("id", "")).strip().lower() == normalized:
            return None
    return f"{skill_id} is not available for {member.name}."


def apply_expert_skill_learn(
    member: PartyMemberState,
    skill_id: str,
    catalog: dict[str, Any],
    *,
    target: str | None = None,
) -> list[str]:
    from .expert_skill_effects import TARGET_SKILLS, normalize_skill_entry

    normalized = skill_id.strip().lower()
    if normalized in TARGET_SKILLS and not (target or "").strip():
        return [f"Choose a monster type for {normalized.replace('_', ' ').title()}."]
    if normalized in TARGET_SKILLS:
        targets = dict(member.expert_skill_targets or {})
        targets[normalized] = (target or "").strip().lower()
        member.expert_skill_targets = targets
    for skill in catalog.get("skills", []):
        if str(skill.get("id", "")).strip().lower() != normalized:
            continue
        name = str(skill.get("name", skill_id))
        entry = normalize_skill_entry(normalized, target if skill.get("repeatable") or normalized in TARGET_SKILLS else None)
        if entry.split(":", 1)[0] not in learned_skill_ids(member) or skill.get("repeatable"):
            member.learned_expert_skills.append(entry)
        label = name
        if normalized in TARGET_SKILLS and target:
            label = f"{name} ({target.strip()})"
        if label not in member.abilities:
            member.abilities.append(label)
        note = " (repeatable — new monster type)" if skill.get("repeatable") else ""
        return [f"{member.name} learns expert skill {label}{note}."]
    for spell in catalog.get("expert_spells", []):
        if str(spell.get("id", "")).strip().lower() != normalized:
            continue
        name = str(spell.get("name", skill_id))
        member.learned_expert_skills.append(normalized)
        if name not in member.spells:
            member.spells.append(name)
        return [f"{member.name} learns expert spell {name} (added to repertoire)."]
    return [f"Unknown expert skill {skill_id}."]


EXPERT_SPELL_MECHANICS: dict[str, str] = {
    "healing_surge": "Heal 2 Life to all allies except the caster; vampires lose 2 Life.",
    "infallible_missile": "Deal 1 Life damage with an auto-hit missile; exploding d6 chains. Level 8+ creates two missiles.",
    "lifeforce_control": "Transfer Life: caster loses X Life; ally heals X or vampire foe loses X.",
    "mass_teleport": "Teleport chosen allies to any visited room; caster pays 1 Life per ally moved.",
    "aura_of_terror": "Morale d6 ≤3 makes a boss or minion group flee; undead, final bosses, and fear foes are immune.",
    "reverse_gaze": "Block gaze on the caster; d8 + level vs foe level may reflect gaze (Medusa petrifies).",
}


def attach_skill_summaries(
    catalog: dict[str, Any],
    *,
    mechanics: dict[str, str],
    spell_mechanics: dict[str, str] | None = None,
) -> dict[str, Any]:
    enriched = deepcopy(catalog)
    for skill in enriched.get("skills", []):
        skill_id = str(skill.get("id", "")).strip().lower()
        skill["summary"] = mechanics.get(skill_id, "")
    if spell_mechanics:
        for spell in enriched.get("expert_spells", []):
            spell_id = str(spell.get("id", "")).strip().lower()
            spell["summary"] = spell_mechanics.get(spell_id, "")
    return enriched


def expert_skills_catalog_with_summaries(catalog: dict[str, Any]) -> dict[str, Any]:
    from .expert_skill_effects import SKILL_MECHANICS

    return attach_skill_summaries(
        catalog,
        mechanics=SKILL_MECHANICS,
        spell_mechanics=EXPERT_SPELL_MECHANICS,
    )


def expert_skills_table_rows(catalog: dict[str, Any]) -> list[dict[str, str]]:
    from .expert_skill_effects import SKILL_MECHANICS, IMPLEMENTATION_STATUS

    codes = catalog.get("class_codes", {})
    rows: list[dict[str, str]] = []
    for skill in catalog.get("skills", []):
        skill_id = str(skill.get("id", "")).strip().lower()
        class_names = ", ".join(str(codes.get(code, code)) for code in skill.get("classes", []))
        rows.append(
            {
                "skill": str(skill.get("name", "")),
                "classes": class_names,
                "category": str(skill.get("category", "")),
                "mechanic": SKILL_MECHANICS.get(skill_id, ""),
                "status": IMPLEMENTATION_STATUS.get(skill_id, "planned"),
                "source_page": str(skill.get("source_page", "")),
            }
        )
    return rows


def expert_spells_table_rows(catalog: dict[str, Any]) -> list[dict[str, str]]:
    codes = catalog.get("class_codes", {})
    rows: list[dict[str, str]] = []
    for spell in catalog.get("expert_spells", []):
        spell_id = str(spell.get("id", "")).strip().lower()
        class_names = ", ".join(str(codes.get(code, code)) for code in spell.get("classes", []))
        rows.append(
            {
                "spell": str(spell.get("name", "")),
                "classes": class_names,
                "min_level": str(spell.get("min_level", 5)),
                "result": EXPERT_SPELL_MECHANICS.get(spell_id, ""),
                "implementation": "yes",
                "source_page": str(spell.get("source_page", "")),
            }
        )
    return rows
