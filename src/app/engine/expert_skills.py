from __future__ import annotations

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
}


def expert_skills_catalog(raw: dict[str, Any]) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def class_skill_codes(class_id: str) -> list[str]:
    return list(CLASS_SKILL_CODES.get(class_id.strip().lower(), []))


def skill_allowed_for_member(member: PartyMemberState, skill: dict[str, Any]) -> bool:
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
    min_level = int(catalog.get("min_level_default", 5))
    if member.level < min_level:
        return []
    learned = learned_skill_ids(member)
    eligible: list[dict[str, Any]] = []
    for skill in catalog.get("skills", []):
        skill_id = str(skill.get("id", "")).strip().lower()
        if not skill_id or not skill_allowed_for_member(member, skill):
            continue
        if skill_id in learned and not skill.get("repeatable"):
            continue
        eligible.append(skill)
    return eligible


def eligible_expert_spells(member: PartyMemberState, catalog: dict[str, Any]) -> list[dict[str, Any]]:
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
    if member.level < int(catalog.get("min_level_default", 5)):
        return f"{member.name} must reach Level 5 before learning expert skills."
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
            }
        )
    return rows


def expert_spells_table_rows(catalog: dict[str, Any]) -> list[dict[str, str]]:
    codes = catalog.get("class_codes", {})
    rows: list[dict[str, str]] = []
    for spell in catalog.get("expert_spells", []):
        class_names = ", ".join(str(codes.get(code, code)) for code in spell.get("classes", []))
        rows.append(
            {
                "spell": str(spell.get("name", "")),
                "classes": class_names,
                "min_level": str(spell.get("min_level", 5)),
            }
        )
    return rows
