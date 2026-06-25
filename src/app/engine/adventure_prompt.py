from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schemas import AdventurePromptParameters
from .adventure_allowlists import (
    build_adventure_allowlists,
    build_boss_spawn_names,
    foe_names_for_validation,
)
from .adventure_tile_catalog import tile_catalog_for_prompt
from ..rules.repository import RulesRepository

LENGTH_ROOM_HINTS = {
    "short": "6–8 rooms",
    "medium": "10–14 rooms",
    "long": "16–20 rooms",
}

LENGTH_ROOM_BOUNDS = {
    "short": (6, 8),
    "medium": (10, 14),
    "long": (16, 20),
}

DIFFICULTY_HINTS = {
    "easy": "lighter encounters, fewer foes per room, lower-level threats",
    "standard": "balanced threat for the recommended party level",
    "hard": "denser encounters, tougher foe mixes, occasional trap pressure",
}

# Names LLMs often invent that fail validation — steer them to real allowlist entries.
COMMON_MISTAKES = [
    {
        "wrong": "Inventing a new dungeon layout instead of filling the SKELETON TO FILL",
        "fix": "Keep every skeleton room id, tile_key, and exit (direction, to, kind, status). Only replace TODO prose and add triggers.",
    },
    {
        "wrong": 'recommended_levels as {"min": 2, "max": 4}',
        "fix": "Use a two-element integer array: recommended_levels: [2, 4].",
    },
    {
        "wrong": "ending as a plain string",
        "fix": 'Use an object: ending: { "victory_text": "...", "defeat_text": "..." }.',
    },
    {
        "wrong": "Omitting quest.objective_text",
        "fix": "Replace the skeleton TODO with a short objective string; quest.objective_text is required.",
    },
    {
        "wrong": "exit kind 'door' when the tile native portal is 'passage' (or vice versa)",
        "fix": "Copy exit kind from TILE CATALOG native_exit_ports for that tile_key and direction — do not guess.",
    },
    {
        "wrong": "Invented boss names (Fallen Prior, Lich King, …)",
        "fix": "Pick boss_name and finale foes from monster_spawn_names and boss_spawn_names exactly.",
    },
    {
        "wrong": '"Skeletons", "Zombies", "Ghosts", "Cultists" alone when not on the allowlist',
        "fix": 'Use exact spawn names from foe_spawn_names (e.g. "Skeletons", "Goblins", "Wraith").',
    },
    {
        "wrong": "Rooms without tile_key",
        "fix": 'Every room needs tile_key from tile_keys (e.g. "11", "22", "33").',
    },
    {
        "wrong": 'Exits with only direction and to (missing id, kind, status)',
        "fix": 'Every exit needs id, direction, to, kind ("door"|"passage"), status ("open"|"closed").',
    },
    {
        "wrong": "Missing source object",
        "fix": 'Include source: { "type": "ai", "parameters": { …copy adventure parameters… } }.',
    },
    {
        "wrong": "Markdown code fences (```json) inside or around the JSON",
        "fix": "Return one raw JSON object only — no backticks, no commentary.",
    },
    {
        "wrong": 'special_event keys like "quest_giver" or custom text fields on events',
        "fix": 'Use special_event_keys only (e.g. "ghost", "healer"). Put NPC dialogue in npcs[].',
    },
    {
        "wrong": 'Trap keys like "curse", "spike_trap", "gas_trap"',
        "fix": "Use trap_keys only (e.g. poison_gas, trapdoor, dart, hidden_pit).",
    },
    {
        "wrong": 'Treasure items like "Silver holy symbol", "Magic sword"',
        "fix": "Use equipment_items only (e.g. Talisman, Amulet, Potion of Healing, Scroll tube).",
    },
    {
        "wrong": "Copying tile_key chains from the example (11→12→22→33…)",
        "fix": "Use the SKELETON tile_key assignments or pick from TILE CATALOG native_exit_ports.",
    },
    {
        "wrong": "Describing a vast hall while using a 1-exit corridor tile",
        "fix": "Read shape_summary, walkable_map (# = floor), and native_exit_ports; prose must match the tile art.",
    },
    {
        "wrong": "Declaring north exit on a tile whose only portal is south-center",
        "fix": "Only use directions from native_exit_ports; mention portal position (e.g. north-west door) in description.",
    },
    {
        "wrong": "Using dungeon tiles 11–66 for entrance_room_id",
        "fix": "entrance_room_id and exit_room_id should use tile_role entrance_surface (tiles 01–06).",
    },
    {
        "wrong": "Names from an old/cached allowlist that differ from your game rules",
        "fix": "Copy foe/trap/item strings only from ALLOWLISTS in the current prompt (built from live rules).",
    },
    {
        "wrong": "Room B linked from A but B has exits: []",
        "fix": "Every link needs reciprocal exits: if chapel north→hall, hall must south→chapel (id, kind, status on both).",
    },
    {
        "wrong": "Putting all treasure on on_treasure or only on combat",
        "fix": "Hidden loot: on_search with treasure{}. Claim reactions: on_treasure with log/encounter. on_enter spawns foes.",
    },
    {
        "wrong": "Statue/puzzle hooks only in room description",
        "fix": "Use room.special_event { key } from special_event_keys, or triggers with when: on_feature after resolution.",
    },
    {
        "wrong": "boss_type in parameters does not match quest.complete_when.boss_name",
        "fix": "The boss in the finale encounter and quest.complete_when.boss_name must be the same foe_spawn_names entry.",
    },
]

ROOM_TEMPLATE = {
    "id": "room-slug",
    "tile_key": "22",
    "title": "Room Title",
    "description": "Flavor text.",
    "exits": [
        {
            "id": "room-slug-north",
            "direction": "north",
            "to": "other-room-slug",
            "kind": "passage",
            "status": "open",
        }
    ],
    "triggers": [
        {
            "when": "on_enter",
            "once": True,
            "encounter": {"foes": [{"name": "Goblins", "count": 4}]},
        }
    ],
}

NPC_TEMPLATE = {
    "id": "npc-slug",
    "name": "NPC Name",
    "room_id": "room-slug",
    "description": "What the party sees.",
    "dialogue": "What they say (flavor only; no mechanics).",
}


def _packaged_adventures_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "adventures"


def load_allowlists_payload(
    repo: RulesRepository,
    *,
    environment: str = "dungeon",
) -> dict[str, Any]:
    """Always build from live rules so prompt and validator stay in sync."""
    return build_adventure_allowlists(repo, environment=environment)


def load_example_manifest() -> dict[str, Any]:
    path = _packaged_adventures_dir() / "examples" / "crypt-of-whispers" / "adventure.json"
    return json.loads(path.read_text(encoding="utf-8"))


def adventure_prompt_defaults(repo: RulesRepository) -> dict[str, Any]:
    bosses = build_boss_spawn_names(repo)
    foe_names = foe_names_for_validation(build_adventure_allowlists(repo))
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
    foe_names = foe_names_for_validation(build_adventure_allowlists(repo))
    if parameters.boss_type not in bosses:
        errors.append(f"boss_type {parameters.boss_type!r} is not a known boss spawn name.")
    elif parameters.boss_type not in foe_names:
        errors.append(
            f"boss_type {parameters.boss_type!r} is not spawnable in encounters (missing from foe_spawn_names)."
        )
    return errors


def _critical_rules_first(
    parameters: AdventurePromptParameters,
    skeleton: dict[str, Any],
    *,
    boss_name: str,
    min_rooms: int,
    max_rooms: int,
    room_hint: str,
) -> list[str]:
    """Top-of-prompt block for rules LLMs most often violate."""
    sk_id = skeleton["id"]
    entrance = skeleton["entrance_room_id"]
    exit_id = skeleton["exit_room_id"]
    room_ids = ", ".join(room["id"] for room in skeleton["rooms"])
    levels = f"[{parameters.party_level_min}, {parameters.party_level_max}]"
    return [
        "CRITICAL — READ FIRST (violations below cause import failure):",
        "- Return ONLY one raw JSON object. No markdown ``` fences. No commentary.",
        f"- Fill the SKELETON TO FILL at the end of this prompt — do NOT invent a new map, room ids, or tile_keys.",
        f"- Keep id {sk_id!r}, entrance_room_id {entrance!r}, exit_room_id {exit_id!r}.",
        f"- Keep these room ids exactly: {room_ids}.",
        "- Keep every skeleton exit (id, direction, to, kind, status) and tile_key — only replace TODO text and add triggers.",
        f"- recommended_levels must be exactly {levels} (two integers in an array), NOT {{\"min\": …, \"max\": …}}.",
        '- ending must be { "victory_text": "…", "defeat_text": "…" } — NOT a single string.',
        "- quest.objective_text is required — replace the skeleton TODO string.",
        f'- Boss: use "{boss_name}" in quest.complete_when.boss_name and in the boss room on_enter encounter (count 1).',
        "- exit.kind must match TILE CATALOG native_exit_ports for that tile_key and direction (door vs passage).",
        f"- {exit_id!r} must use an entrance_surface tile_key (01–06), not a dungeon interior tile (11–66).",
        f"- Room count stays {min_rooms}–{max_rooms} ({room_hint}) — the skeleton room list is final.",
        "",
    ]


def build_adventure_prompt(
    parameters: AdventurePromptParameters,
    *,
    repo: RulesRepository,
) -> str:
    errors = validate_prompt_parameters(parameters, repo=repo)
    if errors:
        raise ValueError("; ".join(errors))

    allowlists = load_allowlists_payload(repo, environment=parameters.environment)
    env_pack = allowlists.get("for_environment") or {}
    tile_catalog = tile_catalog_for_prompt(repo)
    from .adventure_skeleton import generate_adventure_skeleton

    skeleton = generate_adventure_skeleton(parameters, repo=repo)
    skeleton_notes = skeleton.pop("_skeleton_notes", [])
    example = load_example_manifest()
    room_hint = LENGTH_ROOM_HINTS[parameters.length]
    min_rooms, max_rooms = LENGTH_ROOM_BOUNDS[parameters.length]
    difficulty_hint = DIFFICULTY_HINTS[parameters.difficulty]
    boss_name = parameters.boss_type

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
        "optional_root_fields": ["npcs"],
        "room_required_fields": ["id", "tile_key", "title", "description", "exits"],
        "exit_required_fields": ["id", "direction", "to", "kind", "status"],
        "exit_direction_values": list(allowlists["exit_directions"]),
        "exit_kind_values": list(allowlists["exit_kinds"]),
        "exit_status_values": list(allowlists["exit_statuses"]),
        "trigger_when": list(allowlists["trigger_when"]),
        "quest_complete_when_types": list(allowlists["quest_complete_when_types"]),
        "room_template": ROOM_TEMPLATE,
        "npc_template": NPC_TEMPLATE,
        "notes": [
            "Map is an open branching graph; define entrance_room_id and exit_room_id.",
            "Every room MUST include tile_key from TILE CATALOG; every exit direction must appear in native_exit_ports.",
            "Write room descriptions using shape_summary and walkable_map so prose matches map geometry.",
            "Every exit MUST include id, direction, to, kind, and status.",
            "exit.direction must be one of the eight values in exit_directions.",
            "Use only allowlisted foe_spawn_names, tile_keys, trap_keys, special_event_keys, and equipment_items.",
            f'quest.complete_when.boss_name must exactly match foe_spawn_names (use "{boss_name}" for this adventure).',
            f'Finale encounter must include {{ "name": "{boss_name}", "count": 1 }} in the boss room on_enter trigger.',
            "Put NPC dialogue in npcs[]; special_event objects only accept { key } from special_event_keys.",
            "Do not output HP, AC, attack rolls, dice results, or custom rules.",
            "Foe references use {name, count} only.",
            "recommended_levels is [min, max] with two integers (e.g. [2, 4]).",
            "ending is { victory_text, defeat_text } — both strings required.",
            "quest.objective_text is required (replace skeleton TODO).",
            "exit.kind must match native_exit_ports kind for that tile_key and direction.",
            'Set source.type to "ai" and copy the parameters object into source.parameters.',
        ],
    }

    parameter_block = {
        "theme": parameters.theme,
        "difficulty": parameters.difficulty,
        "difficulty_guidance": difficulty_hint,
        "length": parameters.length,
        "min_rooms": min_rooms,
        "max_rooms": max_rooms,
        "target_room_count": room_hint,
        "style": parameters.style,
        "environment": parameters.environment,
        "boss_type": boss_name,
        "party_level_min": parameters.party_level_min,
        "party_level_max": parameters.party_level_max,
    }

    checklist = [
        f"Single JSON object; no markdown ``` fences anywhere in the response.",
        f"Include source.type ai and source.parameters (copy ADVENTURE PARAMETERS).",
        f"{min_rooms}–{max_rooms} rooms — use the SKELETON graph (do not change room ids, tile_key, or exit wiring).",
        "Keep skeleton id, entrance_room_id, exit_room_id, and every room id exactly as given.",
        "recommended_levels: [party_level_min, party_level_max] — not an object with min/max keys.",
        "ending must be { victory_text, defeat_text } — not a single string.",
        "quest.objective_text: replace the TODO string; do not omit.",
        "Fill every TODO in the skeleton with original prose; remove skeleton metadata keys starting with _.",
        "Each exit has id, direction (one of the eight compass directions), to, kind, status.",
        f'quest.complete_when.boss_name is exactly "{boss_name}" (from foe_spawn_names / boss_spawn_names).',
        f'Boss room on_enter encounter includes {{ "name": "{boss_name}", "count": 1 }}.',
        "All foe names, trap keys, event keys, and treasure items match ALLOWLISTS exactly.",
        "Graph connected from entrance_room_id; exit_room_id reachable.",
        "Reciprocal exits: if A north→B, then B south→A (same kind/status pattern).",
        "Rooms with incoming links must not use exits: [] — declare the return passage/door.",
        "Hidden treasure on on_search; on_treasure for claim-time log/ambush (not both for the same loot).",
        "Room special_event uses { key } from special_event_keys; on_feature triggers fire when it resolves.",
        "Optional npcs[] for quest givers; set quest.giver_room_id to the NPC's room.",
    ]

    sections = [
        "You are authoring a Four Against Darkness dungeon adventure module as strict JSON.",
        "The output will be pasted into a game validator — invalid JSON or invented names are rejected.",
        "",
        *_critical_rules_first(
            parameters,
            skeleton,
            boss_name=boss_name,
            min_rooms=min_rooms,
            max_rooms=max_rooms,
            room_hint=room_hint,
        ),
        "OUTPUT RULES (mandatory — violations cause import failure):",
        "- Return ONLY one valid JSON object. No markdown fences. No ```json blocks. No commentary.",
        "- Do not wrap individual rooms in code blocks. The entire response must be parseable JSON.parse().",
        "- Copy exact strings from ALLOWLISTS for foe_spawn_names, trap_keys, special_event_keys, equipment_items, tile_keys.",
        "- exit.direction must match one of the eight values in ALLOWLISTS.exit_directions.",
        "- Never invent monster, trap, item, or event names — not even if they sound thematic.",
        "- Do not invent custom stats, dice, HP, AC, or house rules.",
        "- Fill the SKELETON TO FILL below — keep structure; replace TODO text; add allowlisted encounters/treasure.",
        "- Every exit direction must exist on that room's tile_key (see TILE CATALOG native_exit_ports).",
        "- Room descriptions must match shape_summary / walkable_map; mention portal positions (north-center, etc.).",
        "- Build a connected branching graph from entrance_room_id; exit_room_id must be reachable.",
        f"- Room count: {min_rooms}–{max_rooms} rooms ({room_hint}).",
        f'- Boss for this adventure: "{boss_name}" — use this exact string in quest.complete_when.boss_name and the finale encounter.',
        f"- Recommended hero levels: {parameters.party_level_min}–{parameters.party_level_max}.",
        "",
        "AUTHORING CHECKLIST (verify before responding):",
        *[f"- {item}" for item in checklist],
        "",
        "COMMON MISTAKES (do not do these):",
        *[f'- WRONG: {item["wrong"]} → FIX: {item["fix"]}' for item in COMMON_MISTAKES],
        "",
        "ADVENTURE PARAMETERS:",
        json.dumps(parameter_block, indent=2),
        "",
        "JSON SCHEMA SUMMARY (adventure_manifest v1):",
        json.dumps(schema_summary, indent=2),
        "",
        "ALLOWLISTS (built from your game's live rules — only these strings validate on import):",
        json.dumps(allowlists, indent=2),
        "",
        f"PREFERRED FOES/TRAPS/EVENTS FOR environment={parameters.environment!r} (subset of allowlists):",
        json.dumps(env_pack, indent=2),
        "",
        "TILE CATALOG (map art + geometry — exit directions must match):",
        json.dumps(tile_catalog, indent=2),
        "",
        "SKELETON TO FILL (mandatory structure — do not change ids, tile_key, exits, or graph):",
        json.dumps(skeleton, indent=2),
        "",
        "SKELETON NOTES:",
        *[f"- {note}" for note in skeleton_notes],
        "",
        "EXAMPLE MODULE (tone reference only — do not copy tile_key chains or room layout):",
        json.dumps(example, indent=2),
    ]
    return "\n".join(sections)
