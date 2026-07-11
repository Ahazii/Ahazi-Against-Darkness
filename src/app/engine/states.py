from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .state_catalog import ResolvedStateCatalog, resolve_state_catalog
from .supplements import LOCKED_CORE_SUPPLEMENT_ID, known_supplement_ids


STATE_REGISTRY_VERSION = 1

LEGACY_STATE_FIELDS: list[dict[str, str]] = [
    {
        "field": "Character.statuses",
        "status": "legacy_compatibility",
        "replacement": "state_instances",
        "notes": "Roster-level status strings remain in saved characters until state instances are introduced.",
    },
    {
        "field": "PartyMemberState.statuses",
        "status": "legacy_compatibility",
        "replacement": "state_instances",
        "notes": "Session party status strings remain the active combat/exploration representation for now.",
    },
    {
        "field": "Character.madness",
        "status": "legacy_compatibility",
        "replacement": "state_instances",
        "notes": "Madness is a numeric counter today; the registry treats it as a counter state.",
    },
    {
        "field": "PartyMemberState.madness",
        "status": "legacy_compatibility",
        "replacement": "state_instances",
        "notes": "Session madness counters remain unchanged until save migration is explicit.",
    },
    {
        "field": "SessionState.pending_*",
        "status": "legacy_compatibility",
        "replacement": "state_instances + procedures",
        "notes": "Pending choice objects are state-like procedure pauses, but they are not migrated in this slice.",
    },
]

STATE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "dark-plague",
        "name": "Dark Plague",
        "family": "disease",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 37, "topic": "Dark Plague"},
        "legacy_mappings": {"statuses": ["Dark Plague"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Dark Plague", "hover": "Abyss disease state. Current rules are implemented through the existing affliction helpers."},
    },
    {
        "id": "dark-plague-immunity",
        "name": "Dark Plague Immunity",
        "family": "disease",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 61, "topic": "Elven Bread / Dark Plague cure"},
        "legacy_mappings": {"statuses": ["Dark Plague immunity"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Dark Plague immunity", "hover": "Adventure-long immunity applied by existing Abyss cure logic."},
    },
    {
        "id": "lycanthropy-exposure",
        "name": "Lycanthropy Exposure",
        "family": "disease",
        "scope": "character",
        "value_type": "pending_choice",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 39, "topic": "Lycanthropy"},
        "legacy_mappings": {"statuses": ["Lycanthropy exposure"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Lycanthropy exposure", "hover": "Queued Abyss infection save after a werewolf wound."},
    },
    {
        "id": "lycanthropy",
        "name": "Lycanthropy",
        "family": "disease",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 39, "topic": "Lycanthropy"},
        "legacy_mappings": {"statuses": ["Lycanthropy"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Lycanthropy", "hover": "Persistent Abyss affliction with monastery treatment in the current app."},
    },
    {
        "id": "vampire-rise-pending",
        "name": "Vampire-Rise Pending",
        "family": "death_and_resurrection",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 0, "topic": "Vampire sire / resurrection block"},
        "legacy_mappings": {"statuses": ["Vampire-rise pending"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Vampire-rise pending", "hover": "Abyss resurrection block tied to a tracked vampire sire."},
    },
    {
        "id": "madness",
        "name": "Madness",
        "family": "madness_and_fear",
        "scope": "character",
        "value_type": "counter",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 0, "topic": "Madness"},
        "legacy_mappings": {"fields": ["Character.madness", "PartyMemberState.madness"], "status_prefixes": ["Madness "]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Madness", "hover": "Numeric mental strain counter currently stored on characters and session party members."},
    },
    {
        "id": "paranoid",
        "name": "Paranoid",
        "family": "madness_and_fear",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 0, "topic": "Madness side effect"},
        "legacy_mappings": {"statuses": ["Paranoid"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Paranoid", "hover": "Derived from Madness in the current app; blocks equipment exchange while active."},
    },
    {
        "id": "hungry",
        "name": "Hungry",
        "family": "survival",
        "scope": "character",
        "value_type": "timer",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Food and hunger"},
        "legacy_mappings": {"statuses": ["Hungry"], "fields": ["SessionState.hunger_rounds"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Hungry", "hover": "Food timer status. Current app uses hunger_rounds plus a Hungry status string."},
    },
    {
        "id": "protection",
        "name": "Protection",
        "family": "blessings_and_buffs",
        "scope": "character",
        "value_type": "modifier",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 146, "topic": "Protection spell"},
        "legacy_mappings": {"statuses": ["Protection"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Protection", "hover": "Defensive spell buff tracked as a status string during the adventure."},
    },
    {
        "id": "cursed",
        "name": "Cursed",
        "family": "core_conditions",
        "scope": "character",
        "value_type": "modifier",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Cursed Altar"},
        "legacy_mappings": {"statuses": ["Cursed"], "fields": ["SessionState.cursed_character_id"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Cursed", "hover": "Defense penalty condition currently removable by Blessing and other printed exits."},
    },
    {
        "id": "blessed-temple-bonus",
        "name": "Blessed Temple Bonus",
        "family": "blessings_and_buffs",
        "scope": "character",
        "value_type": "modifier",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Blessed Temple/Shrine"},
        "legacy_mappings": {"fields": ["SessionState.blessed_undead_bonus_character_id"], "status_text": ["Blessed Temple/Shrine"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Blessed Temple bonus", "hover": "Attack bonus against undead or demons until the printed ending condition is met."},
    },
    {
        "id": "trapped-in-pit",
        "name": "Trapped in Pit",
        "family": "location_states",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Hidden pit trap"},
        "legacy_mappings": {"statuses": ["Trapped in pit"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Trapped in pit", "hover": "Hidden pit trap status cleared by climb-out help or rope in the current app."},
    },
    {
        "id": "petrified",
        "name": "Petrified",
        "family": "core_conditions",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Petrification"},
        "legacy_mappings": {"statuses": ["Petrified"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Petrified", "hover": "Turned-to-stone condition currently tracked as a status string."},
    },
    {
        "id": "asleep",
        "name": "Asleep",
        "family": "core_conditions",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Sleep"},
        "legacy_mappings": {"statuses": ["Asleep"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Asleep", "hover": "Sleep condition currently tracked as a status string."},
    },
    {
        "id": "paralyzed",
        "name": "Paralyzed",
        "family": "core_conditions",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 55, "topic": "Ghoul paralysis"},
        "legacy_mappings": {"statuses": ["Paralyzed", "Paralyzed (Blessing cures)"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Paralyzed", "hover": "Paralysis condition from ghoul-like effects and Courtship variants."},
    },
    {
        "id": "poisoned-lingering",
        "name": "Poisoned",
        "family": "core_conditions",
        "scope": "character",
        "value_type": "timer",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Poison"},
        "legacy_mappings": {"statuses": ["Poisoned"], "status_prefixes": ["Poisoned L"]},
        "implemented": True,
        "review_status": "needs_pdf_page",
        "ui": {"label": "Poisoned", "hover": "Lingering poison state from foe attacks; save/cure timing remains in existing combat helpers."},
    },
    {
        "id": "envenomed-weapon",
        "name": "Envenomed Weapon",
        "family": "equipment_states",
        "scope": "equipment",
        "value_type": "flag",
        "source": {"supplement_id": "four-against-the-abyss", "source_pdf": "Four-Against-the-Abyss.pdf", "page": 32, "topic": "Poison Expert / blade poison"},
        "legacy_mappings": {"statuses": ["Envenomed weapon (melee)", "Envenomed weapon (missile)"], "item_suffixes": ["(poisoned)"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Envenomed weapon", "hover": "Weapon poison state represented by status strings or poisoned inventory suffixes."},
    },
    {
        "id": "fd-psychic-residue-save",
        "name": "Psychic Residue Save Bonus",
        "family": "madness_and_fear",
        "scope": "character",
        "value_type": "modifier",
        "source": {"supplement_id": "forsaken-depths", "source_pdf": "Four_Against_the_Forsaken_Depths.pdf", "page": 56, "topic": "Psychic Residue"},
        "legacy_mappings": {"statuses": ["FD Psychic Residue +3 Save"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Psychic Residue +3 Save", "hover": "Forsaken Depths save bonus marker after resisting Psychic Residue."},
    },
    {
        "id": "fd-my-fingers-are-worms",
        "name": "My Fingers Are Worms",
        "family": "madness_and_fear",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": "forsaken-depths", "source_pdf": "Four_Against_the_Forsaken_Depths.pdf", "page": 55, "topic": "Hallucinations"},
        "legacy_mappings": {"statuses": ["FD My Fingers are Worms"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "My Fingers are Worms", "hover": "Forsaken Depths hallucination state currently applied through FD room content."},
    },
    {
        "id": "fd-no-danger-here",
        "name": "There Is No Danger Here",
        "family": "madness_and_fear",
        "scope": "character",
        "value_type": "flag",
        "source": {"supplement_id": "forsaken-depths", "source_pdf": "Four_Against_the_Forsaken_Depths.pdf", "page": 55, "topic": "Hallucinations"},
        "legacy_mappings": {"statuses": ["FD No Danger Here"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "No Danger Here", "hover": "Forsaken Depths hallucination state currently applied through FD room content."},
    },
    {
        "id": "fd-lizardman-horde-poison",
        "name": "Lizardman Horde Poison",
        "family": "combat_modifiers",
        "scope": "character",
        "value_type": "modifier",
        "source": {"supplement_id": "forsaken-depths", "source_pdf": "Four_Against_the_Forsaken_Depths.pdf", "page": 42, "topic": "Lizardman Hordes"},
        "legacy_mappings": {"statuses": ["FD Lizardman Horde poison -1 Attack"]},
        "implemented": True,
        "review_status": "source_backed",
        "ui": {"label": "Lizardman Horde poison", "hover": "Cumulative FD attack penalty marker from Lizardman Horde poison."},
    },
]


def state_registry() -> list[dict[str, Any]]:
    return deepcopy(STATE_DEFINITIONS)


def resolve_state_registry(active_supplement_ids: list[str] | tuple[str, ...]) -> ResolvedStateCatalog:
    """Resolve state definitions for a locked supplement snapshot.

    The returned catalogue is metadata-only for now. Existing mechanics still
    use their legacy status/counter helpers until each rule family is migrated
    with source-backed parity tests.
    """
    return resolve_state_catalog(
        STATE_DEFINITIONS,
        active_supplement_ids,
        default_provider_id=LOCKED_CORE_SUPPLEMENT_ID,
    )


def registry_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item or "").strip()]
    if isinstance(value, dict):
        values: list[str] = []
        for item in value.values():
            values.extend(registry_text_list(item))
        return values
    text = str(value).strip()
    return [text] if text else []


def normalize_legacy_state_label(label: str) -> tuple[str, str]:
    raw = str(label or "").strip().lower()
    base = re.sub(r"\s*\([^)]*\)\s*", " ", raw)
    base = re.sub(r"[^a-z0-9+ -]", " ", base)
    base = " ".join(base.split())
    return raw, base


def state_definition_for_status(label: str, states: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    raw, base = normalize_legacy_state_label(label)
    if not raw:
        return None
    registry = states if states is not None else STATE_DEFINITIONS
    for definition in registry:
        mappings = definition.get("legacy_mappings") if isinstance(definition.get("legacy_mappings"), dict) else {}
        exact = [item.lower() for item in registry_text_list(mappings.get("statuses"))]
        if any(item == raw or item == base for item in exact):
            return deepcopy(definition)
        status_text = [item.lower() for item in registry_text_list(mappings.get("status_text"))]
        if any(item in raw or item in base for item in status_text):
            return deepcopy(definition)
        prefixes = [item.lower() for item in registry_text_list(mappings.get("status_prefixes"))]
        if any(raw.startswith(item) or base.startswith(item) for item in prefixes):
            return deepcopy(definition)
        suffixes = [item.lower() for item in registry_text_list(mappings.get("item_suffixes"))]
        if any(item in raw for item in suffixes):
            return deepcopy(definition)
    return None


def state_definitions_for_statuses(labels: list[str], states: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    matches: dict[str, dict[str, Any]] = {}
    registry = states if states is not None else STATE_DEFINITIONS
    for label in labels:
        definition = state_definition_for_status(label, registry)
        if definition and definition.get("id"):
            matches[str(definition["id"])] = definition
    return list(matches.values())


def state_registry_diagnostics(states: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    registry = states if states is not None else STATE_DEFINITIONS
    diagnostics: list[dict[str, str]] = []
    seen: set[str] = set()
    supplements = known_supplement_ids()
    for index, state in enumerate(registry):
        state_id = str(state.get("id") or "").strip()
        path = state_id or f"state[{index}]"
        if not state_id:
            diagnostics.append({"severity": "error", "path": path, "message": "State record is missing id."})
            continue
        if state_id in seen:
            diagnostics.append({"severity": "warning", "path": state_id, "message": f"Duplicate state id {state_id!r}."})
        seen.add(state_id)
        source = state.get("source") if isinstance(state.get("source"), dict) else {}
        supplement_id = str(source.get("supplement_id") or "").strip()
        if supplement_id and supplement_id not in supplements:
            diagnostics.append({"severity": "warning", "path": state_id, "message": f"State {state_id!r} references unknown supplement {supplement_id!r}."})
        if state.get("review_status") == "source_backed" and int(source.get("page") or 0) <= 0:
            diagnostics.append({"severity": "warning", "path": state_id, "message": f"State {state_id!r} is source_backed but has no positive source page."})
        if not state.get("legacy_mappings"):
            diagnostics.append({"severity": "info", "path": state_id, "message": f"State {state_id!r} has no legacy mapping yet."})
    return diagnostics


def state_payload() -> dict[str, Any]:
    states = state_registry()
    return {
        "schema_version": STATE_REGISTRY_VERSION,
        "read_only": True,
        "states": states,
        "diagnostics": state_registry_diagnostics(states),
        "legacy_fields": deepcopy(LEGACY_STATE_FIELDS),
        "families": sorted({state["family"] for state in states}),
        "scopes": sorted({state["scope"] for state in states}),
    }
