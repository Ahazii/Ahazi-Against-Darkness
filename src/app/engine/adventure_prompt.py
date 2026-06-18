from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schemas import AdventurePromptParameters
from .adventure_allowlists import build_adventure_allowlists, build_boss_spawn_names
from ..rules.repository import RulesRepository

LENGTH_ROOM_HINTS = {
    "short": "6–8 rooms",
    "medium": "10–14 rooms",
    "long": "16–20 rooms",
}

DIFFICULTY_HINTS = {
    "easy": "lighter encounters, fewer foes per room, lower-level threats",
    "standard": "balanced threat for the recommended party level",
    "hard": "denser encounters, tougher foe mixes, occasional trap pressure",
}


def _packaged_adventures_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "adventures"


def load_allowlists_payload(repo: RulesRepository) -> dict[str, Any]:
    path = _packaged_adventures_dir() / "allowlists.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return build_adventure_allowlists(repo)


def load_example_manifest() -> dict[str, Any]:
    path = _packaged_adventures_dir() / "examples" / "crypt-of-whispers" / "adventure.json"
    return json.loads(path.read_text(encoding="utf-8"))


def adventure_prompt_defaults(repo: RulesRepository) -> dict[str, Any]:
    bosses = build_boss_spawn_names(repo)
    default_boss = "Wraith" if "Wraith" in bosses else (bosses[0] if bosses else "Young Dragon")
    return {
        "parameters": AdventurePromptParameters(
            theme="undead crypt",
            difficulty="standard",
            length="medium",
            style="grim",
            environment="dungeon",
            boss_type=default_boss,
            party_level_min=2,
            party_level_max=4,
        ).model_dump(),
        "boss_options": bosses,
        "length_room_hints": LENGTH_ROOM_HINTS,
        "difficulty_hints": DIFFICULTY_HINTS,
    }


def validate_prompt_parameters(
    parameters: AdventurePromptParameters,
    *,
    repo: RulesRepository,
) -> list[str]:
    errors: list[str] = []
    if parameters.party_level_min > parameters.party_level_max:
        errors.append("party_level_min must be <= party_level_max.")
    bosses = set(build_boss_spawn_names(repo))
    if parameters.boss_type not in bosses:
        errors.append(f"boss_type {parameters.boss_type!r} is not a known boss spawn name.")
    return errors


def build_adventure_prompt(
    parameters: AdventurePromptParameters,
    *,
    repo: RulesRepository,
) -> str:
    errors = validate_prompt_parameters(parameters, repo=repo)
    if errors:
        raise ValueError("; ".join(errors))

    allowlists = load_allowlists_payload(repo)
    example = load_example_manifest()
    room_hint = LENGTH_ROOM_HINTS[parameters.length]
    difficulty_hint = DIFFICULTY_HINTS[parameters.difficulty]

    schema_summary = {
        "schema_version": 1,
        "required_root_fields": [
            "schema_version",
            "id",
            "title",
            "synopsis",
            "source",
            "recommended_levels",
            "default_environment",
            "entrance_room_id",
            "exit_room_id",
            "quest",
            "rooms",
            "ending",
        ],
        "room_fields": ["id", "tile_key", "title", "description", "exits", "triggers"],
        "exit_fields": ["id", "direction", "to", "kind", "status"],
        "trigger_when": ["on_enter", "on_search", "on_treasure"],
        "quest_complete_when_types": [
            "boss_defeated",
            "item_collected",
            "room_reached",
            "peaceful_count",
        ],
        "notes": [
            "Map is an open branching graph; define entrance_room_id and exit_room_id.",
            "Use only allowlisted monster_spawn_names, tile_keys, trap_keys, special_event_keys, and equipment_items.",
            "Do not output HP, AC, attack rolls, dice results, or custom rules.",
            "Foe references use {name, count} only.",
            "Set source.type to ai and copy the parameters object into source.parameters.",
        ],
    }

    parameter_block = {
        "theme": parameters.theme,
        "difficulty": parameters.difficulty,
        "difficulty_guidance": difficulty_hint,
        "length": parameters.length,
        "target_room_count": room_hint,
        "style": parameters.style,
        "environment": parameters.environment,
        "boss_type": parameters.boss_type,
        "party_level_min": parameters.party_level_min,
        "party_level_max": parameters.party_level_max,
    }

    sections = [
        "You are authoring a Four Against Darkness dungeon adventure module as strict JSON.",
        "",
        "OUTPUT RULES (mandatory):",
        "- Return ONLY valid JSON. No markdown fences. No commentary before or after the JSON.",
        "- Use only names and keys from the ALLOWLISTS section.",
        "- Do not invent monster stats, dice rolls, HP, AC, or house rules.",
        "- Write original flavor text for titles, descriptions, and synopsis.",
        "- Build a connected branching graph reachable from entrance_room_id; exit_room_id must be reachable.",
        "- Include a quest with complete_when appropriate to the boss/objective.",
        f"- Target size: {room_hint}. Include the boss ({parameters.boss_type}) in the finale.",
        f"- Recommended hero levels: {parameters.party_level_min}–{parameters.party_level_max}.",
        "",
        "ADVENTURE PARAMETERS:",
        json.dumps(parameter_block, indent=2),
        "",
        "JSON SCHEMA SUMMARY (adventure_manifest v1):",
        json.dumps(schema_summary, indent=2),
        "",
        "ALLOWLISTS (Four Against Darkness engine references):",
        json.dumps(allowlists, indent=2),
        "",
        "EXAMPLE MODULE (structure reference; do not copy verbatim):",
        json.dumps(example, indent=2),
    ]
    return "\n".join(sections)
