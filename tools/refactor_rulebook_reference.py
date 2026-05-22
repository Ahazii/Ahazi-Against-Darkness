"""Normalize rulebook_reference.json: rulebook sections, not per-feature rows."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF_PATH = ROOT / "data" / "rules" / "rulebook_reference.json"
CLASSES_PATH = ROOT / "data" / "rules" / "classes.json"

PARTIAL_IDS = {
    "expert_skills",
    "expert_spells",
    "druid",
}

NOT_IN_APP_IDS = {
    "split_party",
}

PARTIAL_SUMMARY_PREFIX = {
    "expert_skills": "Partial in app — ",
    "expert_spells": "Partial in app — ",
}


def class_status_map() -> dict[str, str]:
    raw = json.loads(CLASSES_PATH.read_text(encoding="utf-8"))
    profiles = raw if isinstance(raw, list) else raw.get("classes", [])
    mapping: dict[str, str] = {}
    for profile in profiles:
        class_id = str(profile.get("id", "")).strip().lower()
        status = str(profile.get("implementation_status", "starter")).strip().lower()
        if status in {"validated", "implemented"}:
            mapping[class_id] = "implemented"
        elif status in {"starter", "partial"}:
            mapping[class_id] = "partial"
        else:
            mapping[class_id] = "planned"
    return mapping


def normalize_reference() -> dict:
    data = json.loads(REF_PATH.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    class_map = class_status_map()

    cleaned: list[dict] = []
    for entry in entries:
        entry_id = str(entry.get("id", ""))
        if entry_id == "expert_skill_effects" or (
            entry_id.startswith("expert_skill_") and entry_id != "expert_skills"
        ):
            continue
        cleaned.append(entry)

    by_id = {str(e["id"]): e for e in cleaned if e.get("id")}

    by_id["expert_skills"] = {
        "id": "expert_skills",
        "title": "Expert Skills (Four Against the Abyss)",
        "category": "economy",
        "source_page": 14,
        "source": "Four Against the Abyss pp.14–23",
        "implementation_status": "partial",
        "keywords": [
            "expert",
            "skill",
            "abyss",
            "advancement",
            "level 5",
            "impervious",
            "sworn enemy",
        ],
        "summary": "Partial in app — L5+ heroes may learn expert skills instead of gaining a level on a successful advancement roll.",
        "body": (
            "Four Against the Abyss (pp.14–23): when a hero reaches Level 5+, a successful "
            "advancement roll may be spent to learn one expert skill instead of gaining +1 Level.\n\n"
            "Roll the tier advancement die with the Forsaken Depths modifier (Expert d8+2, Heroic d10+4, …). "
            "Success if the total exceeds current Level, or the natural die shows the high auto-success faces.\n\n"
            "Each skill is normally taken once per hero. Impervious may be learned again for a new monster type; "
            "Sworn Enemy and Impervious require choosing a foe keyword when learned.\n\n"
            "Skill names, class codes, mechanics, and engine wiring status are listed in the Rules tables panel "
            "(expert_skills_table and expert_skill_implementation_table) — not duplicated here.\n\n"
            "Tier training between adventures (Expert / Heroic / Legendary gates) is summarized under Tier Training; "
            "costs are in tier_training_costs_table."
        ),
    }

    if "expert_spells" not in by_id:
        by_id["expert_spells"] = {
            "id": "expert_spells",
            "title": "Expert Spells (Four Against the Abyss)",
            "category": "spells",
            "source_page": 24,
            "source": "Four Against the Abyss pp.24–25",
            "implementation_status": "planned",
            "keywords": ["expert", "spell", "wizard", "elf", "abyss"],
            "summary": "Planned in app — wizard and elf may learn expert spells via the L5+ advancement fork.",
            "body": (
                "Four Against the Abyss (pp.24–25): wizards and elves at Level 5+ may learn expert spells using "
                "the same advancement fork as expert skills. The spell is added to the hero's repertoire.\n\n"
                "See expert_spells_table in the Rules tables panel for the catalog and class eligibility."
            ),
        }

    if "tier_training" in by_id:
        entry = by_id["tier_training"]
        entry["implementation_status"] = "implemented"
        entry["source"] = "Forsaken Depths summary p.9"
        entry["summary"] = (
            "Between adventures, pay gold and/or banked XP to record Expert, Heroic, or Legendary tier training."
        )
        entry["body"] = (
            "Forsaken Depths tier entry (summary p.9) gates advancement into higher tiers. "
            "Use Tier training on the party sheet between adventures.\n\n"
            "Exact gold and banked-XP costs are in tier_training_costs_table (Rules tables panel)."
        )

    for entry_id in ("search_room", "surprise", "classical_xp"):
        entry = by_id.get(entry_id)
        if not entry:
            continue
        body = entry.get("body", "")
        for strip in (
            "\n\nExpert skills: Detective (clue finds), Stone Mastery (secret doors), and Intuition (general search) may treat a roll of 4 as 5 when applicable.",
            "\n\nExpert skill Danger Sense: a hero with the skill in rearguard positions (#3–4) prevents wandering corridor ambushes from surprising the party.",
            "\n\nL5+ fork on the party sheet: Level up or Learn expert skill/spell. Impervious and Sworn Enemy prompt for a monster type.",
        ):
            body = body.replace(strip, "")
        entry["body"] = body

    classical = by_id.get("classical_xp")
    if classical:
        classical["implementation_status"] = "implemented"
        classical["summary"] = "Basic tier d6 > Level; Expert tier (L5+) d8+2 > Level or natural 7–8."

    split = by_id.get("split_party")
    if split:
        split["implementation_status"] = "not_in_app"
        split["title"] = "Split Party"
        if split["summary"].startswith("Rulebook allows"):
            pass
        split["summary"] = "Not in app — rulebook allows detached groups with separate wandering checks."

    for entry in by_id.values():
        entry_id = str(entry.get("id", ""))
        if entry.get("implementation_status"):
            continue
        if entry_id in NOT_IN_APP_IDS:
            entry["implementation_status"] = "not_in_app"
        elif entry_id in PARTIAL_IDS:
            entry["implementation_status"] = "partial"
        elif entry.get("category") == "classes" and entry_id in class_map:
            entry["implementation_status"] = class_map[entry_id]
        else:
            entry["implementation_status"] = "implemented"

        prefix = PARTIAL_SUMMARY_PREFIX.get(entry_id)
        summary = str(entry.get("summary", ""))
        if prefix and not summary.lower().startswith("partial"):
            entry["summary"] = f"{prefix}{summary}"

    data["entries"] = sorted(by_id.values(), key=lambda item: (item.get("source_page") or 0, item.get("title", "")))
    return data


def main() -> None:
    data = normalize_reference()
    REF_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['entries'])} rulebook reference sections to {REF_PATH}")


if __name__ == "__main__":
    main()
