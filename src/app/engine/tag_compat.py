from __future__ import annotations

from copy import deepcopy
import json
import os
import re
from pathlib import Path
from typing import Any

from .tag_scene_lifecycle import (
    TAG_GENERATED_CLOSEOUT_ACTION_LABEL,
    TAG_GENERATED_CLOSEOUT_LOG_MESSAGE,
    TAG_GENERATED_CLOSEOUT_REMINDER,
)


TREASURE_MAP_PROCEDURE_NOTES: dict[int, dict[str, str]] = {
    1: {
        "title": "Underground caves",
        "procedure": "Underground caves procedure: use Claim Treasure for ordinary room treasure. Separately, run Underground caves room target once to roll/log the d6+3 room target. The app then counts rooms, makes the target room the Treasure Map final Boss room, dead-ends unopened exits there, and completes the objective after that Boss is defeated.",
        "final": "Underground caves closeout: after the target-room Boss is defeated, review double maximum treasure handling, XP, Guild share, banking, or storage before claiming the Treasure Map quest reward.",
    },
    2: {
        "title": "Forgotten temple",
        "procedure": "Forgotten temple procedure: use Claim Treasure for ordinary room treasure. Separately, use Adventures Guild Actions to record idol value, leader scroll chance, cultist treasure, XP, and how the heavy idol is carried or stored when those steps become relevant.",
        "final": "Forgotten temple closeout: confirm idol value, leader scroll chance, cultist treasure, XP, Guild share, banking, and storage.",
    },
    3: {
        "title": "Hostile humanoid camp",
        "procedure": "Hostile humanoid camp procedure: choose report, stealth theft, or fight before reward and XP handling. Use Adventures Guild Actions to record that approach; Claim Treasure only handles ordinary room hoards.",
        "final": "Hostile camp closeout: confirm report reward or theft/fight consequences, loot, reinforcements, XP, Guild share, banking, and storage.",
    },
    4: {
        "title": "Underground structure",
        "procedure": "Underground structure procedure: track generated treasure as deferred state and move it to the final Boss before closeout. Use Claim Treasure only when the destination procedure allows ordinary room treasure.",
        "final": "Underground structure closeout: move deferred treasure to the final Boss, then confirm XP, Guild share, banking, and storage.",
    },
    5: {
        "title": "Boss-only underground structure",
        "procedure": "Boss-only underground structure procedure: convert all monster results to Boss encounters, defer treasure to the final Boss, and enforce final reward minimums. Use Claim Treasure only when the destination procedure allows ordinary room treasure.",
        "final": "Boss-only structure closeout: confirm Boss-only conversion, deferred treasure, final reward minimums, XP, Guild share, banking, and storage.",
    },
    6: {
        "title": "Lich sepulchral chamber",
        "procedure": "Lich chamber procedure: resolve entry death magic, lich Life, defenders, lich treasure, and any map/scroll follow-up before closeout. Claim Treasure only handles ordinary room hoards.",
        "final": "Lich chamber closeout: confirm death-magic Life loss, lich Life, defenders, treasure, XP, Guild share, banking, storage, and any map/scroll follow-up.",
    },
}


_LEGACY_MAP_NOTE_RE = re.compile(
    r"^TAG (?P<final>final\s+)?note:\s*Apply The Map Leads To(?:\s+(?P<roll>[1-6]))?\s+"
    r"(?:reward/procedure text|reward text)\s+for\s+(?P<title>.*?);.*$",
    re.IGNORECASE,
)

_LEGACY_GENERATED_CORE_CLOSEOUT_SENTENCE = (
    "Choose Return to town and finish to close this Adventures Guild lead."
)


def treasure_map_note_for(roll: int | None, *, final: bool = False) -> str:
    note = TREASURE_MAP_PROCEDURE_NOTES.get(roll or 0)
    if not note:
        return (
            "TAG guidance: Treasure Map destination procedure is separate from ordinary room treasure. "
            "If the room says hidden treasure was found, use Claim Treasure. Use Adventures Guild Actions only to record the printed Map Leads To procedure, reward accounting, XP, Guild share, banking, and storage."
        )
    body = note["final"] if final else note["procedure"]
    prefix = "TAG final guidance" if final else "TAG guidance"
    return f"{prefix}: {body}"


def normalize_tag_closeout_text(value: str) -> str:
    text = str(value or "")
    return text.replace(
        _LEGACY_GENERATED_CORE_CLOSEOUT_SENTENCE,
        f"Choose {TAG_GENERATED_CLOSEOUT_ACTION_LABEL} to close this Adventures Guild lead.",
    )


def normalize_tag_log_line(line: str) -> str:
    text = normalize_tag_closeout_text(str(line or ""))
    if text.strip() == "When you are ready, choose Continue to finish the adventure.":
        return TAG_GENERATED_CLOSEOUT_LOG_MESSAGE
    if text.strip() == "Read the resolved Adventures Guild scene, then choose Continue to finish the adventure.":
        return TAG_GENERATED_CLOSEOUT_REMINDER
    if "star-shaped object" in text.lower() and re.search(
        r"\bFollowing the Treasure Map Table\b",
        text,
        flags=re.IGNORECASE,
    ):
        return _trim_bofto_scene19_text(text)
    match = _LEGACY_MAP_NOTE_RE.match(text.strip())
    if not match:
        return text
    roll_text = match.group("roll")
    roll = int(roll_text) if roll_text else None
    return treasure_map_note_for(roll, final=bool(match.group("final")))


def normalize_tag_log_lines(lines: list[str]) -> bool:
    changed = False
    for index, line in enumerate(list(lines)):
        normalized = normalize_tag_log_line(line)
        if normalized != line:
            lines[index] = normalized
            changed = True
    return changed


def _generic_tag_prompt(title: str, body: str, *, action_type: str, action_value: str, reference: str) -> dict[str, Any]:
    return {
        "title": title,
        "body": body,
        "checklist": [
            "Confirm the printed TAG scene/result before changing state.",
            "Use the generated Adventures Guild Director for the current phase, then record only the branch, route, reward, or XP that actually happened.",
        ],
        "actions": [
            {
                "label": title,
                "tooltip": "Use this repaired prompt action only when the printed scene/player decision matches it. Confirm exact values from the PDF/player decision.",
                "action_type": action_type,
                "action_value": action_value,
                "reference": reference,
                "amount": 0,
            },
        ],
    }


def _local_tag_narrative_override(lead_type: str, detail: str) -> dict[str, Any]:
    data_dir = Path(os.getenv("DATA_DIR", ".data"))
    if not data_dir.is_absolute():
        data_dir = (Path(__file__).resolve().parents[3] / data_dir).resolve()
    path = data_dir / "tag_scene_narrative_overrides.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    tag = data.get("tag")
    if not isinstance(tag, dict):
        return {}
    family = tag.get(lead_type)
    if not isinstance(family, dict):
        return {}
    for key in {str(detail), str(detail).strip(), str(detail).strip().lower()}:
        value = family.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _apply_local_tag_narrative_override(manifest: dict[str, Any], tag_reference: dict[str, Any]) -> bool:
    lead_type = str(tag_reference.get("lead_type") or "").strip()
    detail = str(tag_reference.get("lead_detail") or "").strip()
    if not lead_type or not detail:
        return False
    override = _local_tag_narrative_override(lead_type, detail)
    if not override:
        return False
    changed = False
    changed_fields: list[str] = []

    module_title = str(override.get("module_title") or "").strip()
    if module_title and manifest.get("title") != module_title:
        manifest["title"] = module_title
        changed = True
        changed_fields.append("module title")
    objective = str(override.get("objective") or "").strip()
    quest = manifest.get("quest")
    if objective and isinstance(quest, dict) and quest.get("objective_text") != objective:
        quest["objective_text"] = objective
        changed = True
        changed_fields.append("quest objective")

    rooms_override = override.get("rooms")
    if isinstance(rooms_override, dict):
        rooms_by_id = {
            str(room.get("id")): room
            for room in manifest.get("rooms") or []
            if isinstance(room, dict) and room.get("id")
        }
        prompts = tag_reference.setdefault("room_prompts", {})
        if not isinstance(prompts, dict):
            prompts = {}
            tag_reference["room_prompts"] = prompts
        for room_id, room_override in rooms_override.items():
            if not isinstance(room_override, dict):
                continue
            title = str(room_override.get("title") or "").strip()
            description = str(room_override.get("description") or "").strip()
            log = str(room_override.get("log") or room_override.get("on_enter_log") or "").strip()
            room = rooms_by_id.get(str(room_id))
            if isinstance(room, dict):
                if title and room.get("title") != title:
                    room["title"] = title
                    changed = True
                    changed_fields.append(f"{room_id} title")
                if description and room.get("description") != description:
                    room["description"] = description
                    changed = True
                    changed_fields.append(f"{room_id} description")
                for trigger in room.get("triggers") or []:
                    if isinstance(trigger, dict) and log and trigger.get("log") != log:
                        trigger["log"] = log
                        changed = True
                        changed_fields.append(f"{room_id} log")
            prompt = prompts.get(room_id)
            if isinstance(prompt, dict):
                if title and prompt.get("title") != title:
                    prompt["title"] = title
                    changed = True
                    changed_fields.append(f"{room_id} prompt title")
                if description and prompt.get("body") != description:
                    prompt["body"] = description
                    changed = True
                    changed_fields.append(f"{room_id} prompt body")

        lead_entry = rooms_override.get("tag-lead-entry")
        entry_description = (
            str(lead_entry.get("description") or "").strip()
            if isinstance(lead_entry, dict)
            else ""
        )
        if entry_description:
            for npc in manifest.get("npcs") or []:
                if not isinstance(npc, dict) or npc.get("room_id") != "tag-lead-entry":
                    continue
                if npc.get("description") != entry_description:
                    npc["description"] = entry_description
                    changed = True
                    changed_fields.append("Guild Contact description")
                if objective and npc.get("dialogue") != objective:
                    npc["dialogue"] = objective
                    changed = True
                    changed_fields.append("Guild Contact dialogue")

    scene_graph = override.get("scene_graph")
    if isinstance(scene_graph, dict) and tag_reference.get("scene_graph") != scene_graph:
        tag_reference["scene_graph"] = scene_graph
        changed = True
        changed_fields.append("scene branches")
    if changed:
        tag_reference["local_narrative_override_applied"] = True
        existing = tag_reference.get("local_narrative_override_changed_fields")
        merged = list(existing) if isinstance(existing, list) else []
        for field in changed_fields:
            if field not in merged:
                merged.append(field)
        tag_reference["local_narrative_override_changed_fields"] = merged
    return changed


def tag_reference_from_manifest(manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        return {}
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    parameters = source.get("parameters") if isinstance(source.get("parameters"), dict) else {}
    tag_reference = parameters.get("tag_reference") if isinstance(parameters, dict) else None
    return tag_reference if isinstance(tag_reference, dict) else {}


def is_generated_tag_manifest(manifest: dict[str, Any] | None) -> bool:
    return bool(tag_reference_from_manifest(manifest))


_TAG_REPEATABLE_SERVICE_STATE_KEY = "tag_repeatable_service"
_TAG_REPEATABLE_SERVICE_MIGRATION_KEY = "tag_repeatable_service_legacy_migration"
_LEGACY_SERVICE_PROXY_NAMES_KEY = "legacy_service_proxy_foe_names"
_LEGACY_EPIC_REWARD_PREFIX = "Quest complete! Epic reward:"
_LEGACY_SERVICE_REPAIR_LOG = (
    "Legacy TAG service repair: the old proxy-combat completion was reopened so the printed "
    "service choices can be resolved."
)
_LEGACY_REWARD_PRESERVED_LOG = (
    "Legacy TAG service repair: the Epic Reward already granted by the obsolete proxy Quest was "
    "preserved and marked claimed; finish the printed service choices before closing this Rumour."
)


def _tag_repeatable_service_kind(manifest: dict[str, Any]) -> str:
    reference = tag_reference_from_manifest(manifest)
    try:
        rumor_number = int(reference.get("rumor_number") or 0)
    except (TypeError, ValueError):
        rumor_number = 0
    if rumor_number == 6:
        return "leprechaun"
    if rumor_number == 11:
        return "deoldyn"
    haystack = " ".join(
        str(value or "")
        for value in (
            manifest.get("title"),
            reference.get("title"),
            reference.get("lead_detail"),
            reference.get("scene"),
        )
    ).casefold()
    if "leprechaun" in haystack or "blackbird hill" in haystack:
        return "leprechaun"
    if "deoldyn" in haystack or "archery training" in haystack:
        return "deoldyn"
    return ""


def _foe_names(value: Any) -> list[str]:
    if isinstance(value, str):
        clean = value.strip()
        return [clean] if clean else []
    if isinstance(value, dict):
        name = str(value.get("name") or value.get("foe") or "").strip()
        return [name] if name else []
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        names.extend(_foe_names(item))
    return names


def _capture_legacy_service_proxy_names(
    manifest: dict[str, Any],
    tag_reference: dict[str, Any],
) -> bool:
    """Persist exact proxy names before a service upgrade removes their encounter."""
    names = _foe_names(tag_reference.get(_LEGACY_SERVICE_PROXY_NAMES_KEY))
    names.extend(_foe_names(tag_reference.get("final_foe_proxy")))
    names.extend(_foe_names(tag_reference.get("final_foes")))
    quest = manifest.get("quest")
    complete_when = quest.get("complete_when") if isinstance(quest, dict) else None
    if isinstance(complete_when, dict):
        names.extend(_foe_names(complete_when.get("boss_name")))
        target_room = str(complete_when.get("room_id") or "tag-final-scene")
    else:
        target_room = "tag-final-scene"
    for room in manifest.get("rooms") or []:
        if not isinstance(room, dict) or str(room.get("id") or "") != target_room:
            continue
        for trigger in room.get("triggers") or []:
            encounter = trigger.get("encounter") if isinstance(trigger, dict) else None
            if isinstance(encounter, dict):
                names.extend(_foe_names(encounter.get("foes")))
    unique = sorted(
        {name.strip() for name in names if name.strip()},
        key=str.casefold,
    )
    existing = tag_reference.get(_LEGACY_SERVICE_PROXY_NAMES_KEY)
    if not unique or existing == unique:
        return False
    tag_reference[_LEGACY_SERVICE_PROXY_NAMES_KEY] = unique
    return True


def _manifest_room(manifest: dict[str, Any], room_id: str) -> dict[str, Any]:
    return next(
        (
            room
            for room in manifest.get("rooms") or []
            if isinstance(room, dict) and str(room.get("id") or "") == room_id
        ),
        {},
    )


def _session_imported_room_tiles(session: Any, room_id: str) -> list[Any]:
    manifest = getattr(session, "imported_manifest", None)
    entrance_room_id = (
        str(manifest.get("entrance_room_id") or "")
        if isinstance(manifest, dict)
        else ""
    )
    result: list[Any] = []
    for tile in list(getattr(getattr(session, "map_state", None), "tiles", []) or []):
        content_key = str(getattr(tile, "content_key", "") or "")
        if content_key == f"imported:{room_id}" or (
            content_key == "entrance" and entrance_room_id == room_id
        ):
            result.append(tile)
    return result


def _quest_giver_tile_id(session: Any, manifest: dict[str, Any]) -> str:
    quest = manifest.get("quest") if isinstance(manifest.get("quest"), dict) else {}
    giver_room_id = str(
        quest.get("giver_room_id")
        or manifest.get("entrance_room_id")
        or ""
    )
    giver_tiles = _session_imported_room_tiles(session, giver_room_id) if giver_room_id else []
    if giver_tiles:
        return str(getattr(giver_tiles[0], "id", "") or "")
    entrance_tile_id = str(getattr(session, "entrance_tile_id", "") or "")
    if entrance_tile_id:
        return entrance_tile_id
    return str(getattr(getattr(session, "map_state", None), "current_tile_id", "") or "")


def _cached_service_procedure_state(session: Any, kind: str) -> dict[str, Any]:
    cached = getattr(session, "tag_repeatable_service_state", None)
    if not isinstance(cached, dict) or str(cached.get("kind") or kind) != kind:
        return {}
    persisted_keys = {
        "kind",
        "phase",
        "resolved",
        "transactions",
        "shoe_assignments",
        "illusion_lesson",
        "training_results",
        "trained_character_ids",
        "training_batch_resolved",
        "result_text",
        "updated_at",
    }
    state = {
        key: deepcopy(value)
        for key, value in cached.items()
        if key in persisted_keys
    }
    return {_TAG_REPEATABLE_SERVICE_STATE_KEY: state} if state else {}


def _normalize_legacy_service_quest(
    session: Any,
    manifest: dict[str, Any],
    *,
    kind: str,
    preserve_claimed_reward: bool,
) -> bool:
    quest = getattr(session, "active_quest", None)
    legacy_key = str(getattr(quest, "key", "") or "")
    should_normalize = legacy_key in {"imported_room", "imported_boss"}
    should_reconstruct = quest is None and preserve_claimed_reward
    if not should_normalize and not should_reconstruct:
        return False

    from ..schemas import ActiveQuestState

    manifest_quest = manifest.get("quest") if isinstance(manifest.get("quest"), dict) else {}
    description = str(
        manifest_quest.get("objective_text")
        or getattr(quest, "description", "")
        or "Resolve the Adventures Guild scene."
    )
    if quest is None:
        tile_id = _quest_giver_tile_id(session, manifest)
        procedure_state = _cached_service_procedure_state(session, kind)
        quest_id = None
        generated_lead_state: dict[str, Any] = {}
        procedure_signoff = False
        generated_lead_signoff = False
        reward_claimed = preserve_claimed_reward
    else:
        tile_id = str(getattr(quest, "tile_id", "") or _quest_giver_tile_id(session, manifest))
        procedure_state = deepcopy(dict(getattr(quest, "tag_procedure_state", {}) or {}))
        quest_id = str(getattr(quest, "quest_id", "") or "") or None
        generated_lead_state = deepcopy(
            dict(getattr(quest, "tag_generated_lead_state", {}) or {})
        )
        procedure_signoff = bool(getattr(quest, "tag_procedure_signoff", False))
        generated_lead_signoff = bool(
            getattr(quest, "tag_generated_lead_signoff", False)
        )
        reward_claimed = bool(getattr(quest, "reward_claimed", False)) or preserve_claimed_reward
    service_state = procedure_state.get(_TAG_REPEATABLE_SERVICE_STATE_KEY)
    resolved = bool(
        isinstance(service_state, dict)
        and str(service_state.get("phase") or "") == "resolved"
    )
    replacement_data: dict[str, Any] = {
        "tile_id": tile_id,
        "key": "tag_generated_scene",
        "description": description,
        "completed": resolved,
        "reward_claimed": reward_claimed,
        "tag_procedure_state": procedure_state,
        "tag_procedure_signoff": procedure_signoff,
        "tag_generated_lead_state": generated_lead_state,
        "tag_generated_lead_signoff": generated_lead_signoff,
    }
    if quest_id:
        replacement_data["quest_id"] = quest_id
    session.active_quest = ActiveQuestState(**replacement_data)
    return True


def _legacy_epic_reward_line(session: Any) -> str:
    for line in reversed(list(getattr(session, "log", []) or [])):
        text = str(line or "")
        if text.startswith(_LEGACY_EPIC_REWARD_PREFIX):
            return text
    return ""


def _legacy_service_has_completion_evidence(
    session: Any,
    *,
    service_state: dict[str, Any],
    known_proxy_names: list[str],
) -> bool:
    """Require persisted completion provenance before attributing durable gear or skills."""
    if str(service_state.get("phase") or "") == "resolved":
        return True
    if bool(getattr(session, "tag_generated_completion_pending", False)):
        return True
    known = {name.strip().casefold() for name in known_proxy_names if name.strip()}
    for line in list(getattr(session, "log", []) or []):
        text = str(line or "").strip()
        folded = text.casefold()
        if text.startswith(_LEGACY_EPIC_REWARD_PREFIX):
            return True
        if any(
            folded.startswith(f"quest complete: {name} has been ")
            for name in known
        ):
            return True
    return False


def _legacy_service_state(session: Any) -> dict[str, Any]:
    quest = getattr(session, "active_quest", None)
    if quest is None:
        return {}
    procedure = dict(getattr(quest, "tag_procedure_state", {}) or {})
    state = procedure.get(_TAG_REPEATABLE_SERVICE_STATE_KEY)
    return deepcopy(state) if isinstance(state, dict) else {}


def _set_legacy_service_state(session: Any, state: dict[str, Any]) -> None:
    quest = getattr(session, "active_quest", None)
    if quest is None:
        return
    procedure = deepcopy(dict(getattr(quest, "tag_procedure_state", {}) or {}))
    procedure[_TAG_REPEATABLE_SERVICE_STATE_KEY] = deepcopy(state)
    quest.tag_procedure_state = procedure


def _legacy_service_migration_marker(session: Any) -> dict[str, Any]:
    quest = getattr(session, "active_quest", None)
    if quest is None:
        return {}
    procedure = dict(getattr(quest, "tag_procedure_state", {}) or {})
    marker = procedure.get(_TAG_REPEATABLE_SERVICE_MIGRATION_KEY)
    return deepcopy(marker) if isinstance(marker, dict) else {}


def _set_legacy_service_migration_marker(
    session: Any,
    marker: dict[str, Any],
) -> bool:
    quest = getattr(session, "active_quest", None)
    if quest is None:
        return False
    procedure = deepcopy(dict(getattr(quest, "tag_procedure_state", {}) or {}))
    if procedure.get(_TAG_REPEATABLE_SERVICE_MIGRATION_KEY) == marker:
        return False
    procedure[_TAG_REPEATABLE_SERVICE_MIGRATION_KEY] = deepcopy(marker)
    quest.tag_procedure_state = procedure
    return True


def _migrate_legacy_leprechaun_evidence(
    session: Any,
    *,
    allow_inventory_fallback: bool,
) -> bool:
    marker = _legacy_service_migration_marker(session)
    if marker.get("evidence_checked"):
        return False
    state = _legacy_service_state(session)
    state.setdefault("kind", "leprechaun")
    state.setdefault("phase", "open")
    state.setdefault("transactions", [])
    logs = [str(line or "") for line in list(getattr(session, "log", []) or [])]
    assignments = [
        deepcopy(item)
        for item in state.get("shoe_assignments") or []
        if isinstance(item, dict)
    ]
    migrated_pairs = 0
    if not assignments:
        for member in list(getattr(session, "party", []) or []):
            name = str(getattr(member, "name", "") or "").strip()
            if not name:
                continue
            pattern = re.compile(
                rf"{re.escape(name)}\s+buys\s+(?P<count>\d+)\s+pair\(s\)\s+of\s+"
                r"Shoes of Fast Walk\s+for\s+(?P<cost>\d+)\s+gp",
                flags=re.IGNORECASE,
            )
            for line in logs:
                for match in pattern.finditer(line):
                    count = max(0, int(match.group("count")))
                    cost = max(0, int(match.group("cost")))
                    for pair_index in range(1, count + 1):
                        assignments.append(
                            {
                                "recipient_kind": "hero",
                                "recipient_id": str(getattr(member, "character_id", "") or ""),
                                "recipient_name": name,
                                "owner_character_id": str(
                                    getattr(member, "character_id", "") or ""
                                ),
                                "owner_name": name,
                                "payer_character_id": str(
                                    getattr(member, "character_id", "") or ""
                                ),
                                "payer_name": name,
                                "legacy_pair_index": pair_index,
                                "legacy_migrated": True,
                            }
                        )
                    state["transactions"].append(
                        {
                            "type": "shoes",
                            "cost_gp": cost,
                            "pair_count": count,
                            "payer_character_id": str(
                                getattr(member, "character_id", "") or ""
                            ),
                            "payer_name": name,
                            "legacy_migrated": True,
                        }
                    )
                    migrated_pairs += count
        if not assignments and allow_inventory_fallback:
            for member in list(getattr(session, "party", []) or []):
                member_id = str(getattr(member, "character_id", "") or "")
                member_name = str(getattr(member, "name", "") or "")
                owned = sum(
                    1
                    for item in list(getattr(member, "inventory", []) or [])
                    if str(item or "").strip().casefold()
                    == "Shoes of Fast Walk".casefold()
                )
                for pair_index in range(1, owned + 1):
                    assignments.append(
                        {
                            "recipient_kind": "hero",
                            "recipient_id": member_id,
                            "recipient_name": member_name,
                            "owner_character_id": member_id,
                            "owner_name": member_name,
                            "payer_character_id": member_id,
                            "payer_name": member_name,
                            "legacy_pair_index": pair_index,
                            "legacy_inventory_only": True,
                            "legacy_migrated": True,
                        }
                    )
                if owned:
                    state["transactions"].append(
                        {
                            "type": "shoes",
                            "cost_gp": 200 * owned,
                            "pair_count": owned,
                            "payer_character_id": member_id,
                            "payer_name": member_name,
                            "legacy_inventory_only": True,
                            "legacy_cost_reconstructed": True,
                            "legacy_migrated": True,
                        }
                    )
                    migrated_pairs += owned
        if assignments:
            state["shoe_assignments"] = assignments

    lesson = state.get("illusion_lesson")
    migrated_lesson = False
    if not (isinstance(lesson, dict) and lesson.get("spell_name")):
        lesson_candidates: list[tuple[Any, str, str]] = []
        status_prefix = "TAG leprechaun illusion spell pending:"
        for member in list(getattr(session, "party", []) or []):
            for status in list(getattr(member, "statuses", []) or []):
                text = str(status or "").strip()
                if text.casefold().startswith(status_prefix.casefold()):
                    note = text.split(":", 1)[1].strip()
                    lesson_candidates.append((member, note, text))
        if lesson_candidates:
            member, note, status_text = lesson_candidates[0]
            clean_spell = re.sub(
                r"^Scene\s*2\s+illusion\s+spell\s*[-:]?\s*",
                "",
                note,
                flags=re.IGNORECASE,
            ).strip()
            spell_name = clean_spell or note or "Legacy illusion lesson"
            learner_name = str(getattr(member, "name", "") or "")
            price_text = ""
            lesson_pattern = re.compile(
                rf"{re.escape(learner_name)}\s+learns\s+or\s+records\s+.*?\s+from\s+the\s+"
                r"leprechauns\s+for\s+(?P<price>[^.]+)",
                flags=re.IGNORECASE,
            )
            for line in logs:
                match = lesson_pattern.search(line)
                if match:
                    price_text = match.group("price").strip()
                    break
            free = "free" in price_text.casefold() or "free" in note.casefold()
            member_id = str(getattr(member, "character_id", "") or "")
            state["illusion_lesson"] = {
                "spell_name": spell_name,
                "learner_character_id": member_id,
                "learner_name": learner_name,
                "payer_character_id": member_id,
                "payer_name": learner_name,
                "cost_gp": 0 if free else 100,
                "free_after_three_pairs": free,
                "legacy_pending": True,
                "legacy_status_marker": status_text,
                "legacy_migrated": True,
            }
            state["transactions"].append(
                {
                    "type": "illusion_lesson",
                    **deepcopy(state["illusion_lesson"]),
                }
            )
            migrated_lesson = True

    marker.update(
        {
            "version": 1,
            "kind": "leprechaun",
            "evidence_checked": True,
            "migrated_shoe_pairs": migrated_pairs,
            "migrated_illusion_lesson": migrated_lesson,
        }
    )
    _set_legacy_service_state(session, state)
    _set_legacy_service_migration_marker(session, marker)
    return True


def _migrate_legacy_deoldyn_evidence(
    session: Any,
    *,
    allow_durable_fallback: bool,
) -> bool:
    marker = _legacy_service_migration_marker(session)
    if marker.get("evidence_checked"):
        return False
    state = _legacy_service_state(session)
    state.setdefault("kind", "deoldyn")
    state.setdefault("phase", "open")
    state.setdefault("transactions", [])
    existing_results = [
        deepcopy(item)
        for item in state.get("training_results") or []
        if isinstance(item, dict)
    ]
    results: list[dict[str, Any]] = []
    if not existing_results and not state.get("training_batch_resolved"):
        for member in list(getattr(session, "party", []) or []):
            name = str(getattr(member, "name", "") or "").strip()
            if not name:
                continue
            pattern = re.compile(
                rf"{re.escape(name)}\s+pays\s+(?P<cost>\d+)\s+gp\s+to\s+Deoldyn\s+"
                r"(?P<result>and succeeds|but fails)\s+at\s+the\s+Scene\s*3\s+training\s+"
                r"XP\s+roll\s*\((?P<roll>[^)]*)\);\s*"
                r"(?P<skill>Deadly Accuracy|Dead Shot)\s+"
                r"(?P<tail>learned|is not learned)",
                flags=re.IGNORECASE,
            )
            for line in list(getattr(session, "log", []) or []):
                for match in pattern.finditer(str(line or "")):
                    success = match.group("result").casefold() == "and succeeds"
                    skill_name = match.group("skill")
                    outcome = (
                        "deadly_accuracy"
                        if skill_name.casefold() == "deadly accuracy"
                        else "dead_shot"
                    )
                    result = {
                        "character_id": str(getattr(member, "character_id", "") or ""),
                        "name": name,
                        "outcome": outcome,
                        "outcome_name": skill_name,
                        "cost_gp": max(0, int(match.group("cost"))),
                        "roll": {"legacy_text": match.group("roll").strip()},
                        "success": success,
                        "new_spell": "",
                        "payment": [],
                        "legacy_migrated": True,
                    }
                    results.append(result)
                    state["transactions"].append(
                        {"type": "deoldyn_training", **deepcopy(result)}
                    )
        if not results and allow_durable_fallback:
            durable_skills = {
                "deadly_accuracy": "Deadly Accuracy",
                "dead_shot": "Dead Shot",
            }
            for member in list(getattr(session, "party", []) or []):
                targets = dict(getattr(member, "expert_skill_targets", {}) or {})
                for outcome, outcome_name in durable_skills.items():
                    if str(targets.get(outcome) or "") != "tag_deoldyn":
                        continue
                    result = {
                        "character_id": str(
                            getattr(member, "character_id", "") or ""
                        ),
                        "name": str(getattr(member, "name", "") or ""),
                        "outcome": outcome,
                        "outcome_name": outcome_name,
                        "cost_gp": 60 * max(
                            1,
                            int(getattr(member, "level", 1) or 1),
                        ),
                        "roll": {"legacy_text": "durable Deoldyn skill marker"},
                        "success": True,
                        "new_spell": "",
                        "payment": [],
                        "legacy_durable_marker": True,
                        "legacy_cost_reconstructed": True,
                        "legacy_migrated": True,
                    }
                    results.append(result)
                    state["transactions"].append(
                        {"type": "deoldyn_training", **deepcopy(result)}
                    )
    if results:
        state["training_results"] = results
        state["trained_character_ids"] = sorted(
            {str(item.get("character_id") or "") for item in results if item.get("character_id")}
        )
        state["training_batch_resolved"] = True
    marker.update(
        {
            "version": 1,
            "kind": "deoldyn",
            "evidence_checked": True,
            "migrated_training_attempts": len(results),
        }
    )
    _set_legacy_service_state(session, state)
    _set_legacy_service_migration_marker(session, marker)
    return True


def _clear_stale_legacy_proxy_combat_state(session: Any) -> None:
    session.mode = "exploration"
    session.combat_round = 0
    session.reaction_pending = False
    session.reaction_checked = False
    session.reaction_nudge_pending = False
    session.reaction_pre_adjust_roll = None
    session.reaction_key = None
    session.reaction_bribe_gold = 0
    session.reaction_bribe_weapons = 0
    session.reaction_bribe_gold_per_foe = 0
    session.reaction_bribe_weapons_per_foe = 0
    session.reaction_bribe_foe_count = 0
    session.reaction_trade_stock = []
    session.reaction_trade_active = False
    session.reaction_no_fools_gold = False
    session.reaction_sleep_attack_bonus = 0
    session.foes_strike_first = False
    session.party_surprised = False
    session.party_attacked_immediately = False
    session.foe_flee_strike_pending = False


def _sync_and_clean_legacy_service_final_tile(
    session: Any,
    manifest: dict[str, Any],
    *,
    room_id: str,
    known_proxy_names: list[str],
) -> bool:
    changed = False
    room = _manifest_room(manifest, room_id)
    title = str(room.get("title") or "").strip()
    description = str(room.get("description") or "").strip()
    known = {name.strip().casefold() for name in known_proxy_names if name.strip()}
    current_tile_id = str(
        getattr(getattr(session, "map_state", None), "current_tile_id", "") or ""
    )
    for tile in _session_imported_room_tiles(session, room_id):
        if title and getattr(tile, "title", "") != title:
            tile.title = title
            changed = True
        if description and getattr(tile, "description", "") != description:
            tile.description = description
            changed = True
        enemies = list(getattr(tile, "enemies", []) or [])
        if not enemies or not known:
            continue
        live_names = {
            str(getattr(enemy, "name", "") or "").strip().casefold()
            for enemy in enemies
            if str(getattr(enemy, "name", "") or "").strip()
        }
        marker = _legacy_service_migration_marker(session)
        marker.update({"version": 1, "known_proxy_foes": sorted(known)})
        if live_names and live_names.issubset(known):
            tile.enemies = []
            tile.initial_enemy_count = 0
            if str(getattr(tile, "id", "") or "") == current_tile_id:
                session.pending_bodyguard_intercept = None
                session.combat_bodyguard_pause = None
                _clear_stale_legacy_proxy_combat_state(session)
            marker["proxy_cleanup"] = "cleared_exact_known_proxy"
            marker.pop("preserved_unknown_foes", None)
            if _LEGACY_SERVICE_REPAIR_LOG not in list(getattr(session, "log", []) or []):
                session.log.append(_LEGACY_SERVICE_REPAIR_LOG)
            changed = True
        else:
            unknown = sorted(live_names - known)
            marker["proxy_cleanup"] = "preserved_unknown_or_mixed_foes"
            marker["preserved_unknown_foes"] = unknown
        changed = _set_legacy_service_migration_marker(session, marker) or changed
    return changed


def _clear_unresolved_service_closeout(session: Any) -> bool:
    if not bool(getattr(session, "tag_generated_completion_pending", False)):
        return False
    stale_body = str(getattr(session, "tag_generated_completion_body", "") or "")
    session.tag_generated_completion_pending = False
    session.tag_generated_completion_title = ""
    session.tag_generated_completion_body = ""
    if stale_body:
        session.log = [
            line
            for line in list(getattr(session, "log", []) or [])
            if str(line) != stale_body
        ]
    return True


def _remove_legacy_service_completion_markers(
    session: Any,
    known_proxy_names: list[str],
) -> bool:
    known = {name.strip().casefold() for name in known_proxy_names if name.strip()}

    def stale(line: Any) -> bool:
        text = str(line or "").strip()
        folded = text.casefold()
        if text == "Quest complete: objective location reached.":
            return True
        if text.startswith("Quest objective complete. Return to "):
            return True
        if folded.startswith(
            "quest complete: the imported boss has been defeated; objective repaired"
        ):
            return True
        return any(
            folded.startswith(f"quest complete: {name} has been ")
            for name in known
        )

    old_log = list(getattr(session, "log", []) or [])
    repaired_log = [line for line in old_log if not stale(line)]
    changed = repaired_log != old_log
    if changed:
        session.log = repaired_log
    fired_triggers = list(getattr(session, "imported_fired_triggers", []) or [])
    if "quest:return_hint" in fired_triggers:
        session.imported_fired_triggers = [
            key for key in fired_triggers if key != "quest:return_hint"
        ]
        changed = True
    return changed


def _ensure_resolved_service_closeout(
    session: Any,
    *,
    kind: str,
    service_state: dict[str, Any],
) -> bool:
    """Keep an already resolved migrated service at its Continue closeout."""
    quest = getattr(session, "active_quest", None)
    if quest is None:
        return False
    changed = False
    result_text = str(service_state.get("result_text") or "").strip()
    if not result_text:
        result_text = (
            "The party has finished the Blackbird Hill bargain."
            if kind == "leprechaun"
            else "The party has finished Deoldyn's archery training visit."
        )
    title = (
        "Blackbird Hill bargain resolved"
        if kind == "leprechaun"
        else "Deoldyn's archery training resolved"
    )
    if not bool(getattr(quest, "completed", False)):
        quest.completed = True
        changed = True
    lead_state = deepcopy(dict(getattr(quest, "tag_generated_lead_state", {}) or {}))
    expected_state = deepcopy(lead_state)
    expected_state["scene_resolved"] = True
    expected_state["route_recorded"] = True
    expected_state["completion_pending"] = True
    expected_state.setdefault("result_narrative", result_text)
    closeout = expected_state.get("closeout")
    if not isinstance(closeout, dict):
        closeout = {}
    closeout.setdefault("completed", False)
    closeout.setdefault("result", result_text)
    closeout.setdefault("warnings", [])
    expected_state["closeout"] = closeout
    expected_state["next_action"] = TAG_GENERATED_CLOSEOUT_REMINDER
    if lead_state != expected_state:
        quest.tag_generated_lead_state = expected_state
        changed = True
    if not bool(getattr(session, "tag_generated_completion_pending", False)):
        session.tag_generated_completion_pending = True
        changed = True
    if not str(getattr(session, "tag_generated_completion_title", "") or "").strip():
        session.tag_generated_completion_title = title
        changed = True
    if not str(getattr(session, "tag_generated_completion_body", "") or "").strip():
        session.tag_generated_completion_body = result_text
        changed = True
    log = list(getattr(session, "log", []) or [])
    if result_text not in log:
        session.log.append(result_text)
        changed = True
    if TAG_GENERATED_CLOSEOUT_LOG_MESSAGE not in list(getattr(session, "log", []) or []):
        session.log.append(TAG_GENERATED_CLOSEOUT_LOG_MESSAGE)
        changed = True
    return changed


def _repair_repeatable_service_legacy_state(
    session: Any,
    manifest: dict[str, Any],
    complete_when: dict[str, Any],
) -> bool:
    kind = _tag_repeatable_service_kind(manifest)
    if kind not in {"leprechaun", "deoldyn"}:
        return False
    old_quest = getattr(session, "active_quest", None)
    old_key = str(getattr(old_quest, "key", "") or "")
    reward_line = _legacy_epic_reward_line(session) if old_quest is None else ""
    reference = tag_reference_from_manifest(manifest)
    known_proxy_names = _foe_names(reference.get(_LEGACY_SERVICE_PROXY_NAMES_KEY))
    boss_target = str(getattr(old_quest, "boss_target_name", "") or "").strip()
    if old_key == "imported_boss" and boss_target:
        known_proxy_names.append(boss_target)
        merged = sorted(set(known_proxy_names), key=str.casefold)
        if reference.get(_LEGACY_SERVICE_PROXY_NAMES_KEY) != merged:
            reference[_LEGACY_SERVICE_PROXY_NAMES_KEY] = merged
    changed = _normalize_legacy_service_quest(
        session,
        manifest,
        kind=kind,
        preserve_claimed_reward=bool(reward_line),
    )
    quest = getattr(session, "active_quest", None)
    if quest is None:
        return changed

    legacy_context = old_key in {"imported_room", "imported_boss"} or bool(reward_line)
    completion_evidence = _legacy_service_has_completion_evidence(
        session,
        service_state=_legacy_service_state(session),
        known_proxy_names=known_proxy_names,
    )
    legacy_evidence = False
    if kind == "leprechaun":
        legacy_evidence = any(
            "pair(s) of Shoes of Fast Walk" in str(line)
            for line in list(getattr(session, "log", []) or [])
        ) or any(
            str(status).casefold().startswith(
                "tag leprechaun illusion spell pending:"
            )
            for member in list(getattr(session, "party", []) or [])
            for status in list(getattr(member, "statuses", []) or [])
        )
        if not legacy_evidence and completion_evidence:
            legacy_evidence = any(
                str(item or "").strip().casefold()
                == "Shoes of Fast Walk".casefold()
                for member in list(getattr(session, "party", []) or [])
                for item in list(getattr(member, "inventory", []) or [])
            )
    else:
        legacy_evidence = any(
            "pays" in str(line)
            and "to Deoldyn" in str(line)
            and "training XP roll" in str(line)
            for line in list(getattr(session, "log", []) or [])
        )
        if not legacy_evidence and completion_evidence:
            legacy_evidence = any(
                str(source or "") == "tag_deoldyn"
                for member in list(getattr(session, "party", []) or [])
                for skill, source in dict(
                    getattr(member, "expert_skill_targets", {}) or {}
                ).items()
                if str(skill or "") in {"deadly_accuracy", "dead_shot"}
            )
    if legacy_evidence:
        if kind == "leprechaun":
            changed = _migrate_legacy_leprechaun_evidence(
                session,
                allow_inventory_fallback=completion_evidence,
            ) or changed
        else:
            changed = _migrate_legacy_deoldyn_evidence(
                session,
                allow_durable_fallback=completion_evidence,
            ) or changed

    room_id = str(complete_when.get("room_id") or "tag-final-scene")
    changed = _sync_and_clean_legacy_service_final_tile(
        session,
        manifest,
        room_id=room_id,
        known_proxy_names=known_proxy_names,
    ) or changed
    service_state = _legacy_service_state(session)
    resolved = str(service_state.get("phase") or "") == "resolved"
    if bool(getattr(quest, "completed", False)) != resolved:
        quest.completed = resolved
        changed = True
    if not resolved:
        changed = _clear_unresolved_service_closeout(session) or changed
        if old_key in {"imported_room", "imported_boss"}:
            changed = _remove_legacy_service_completion_markers(
                session,
                known_proxy_names,
            ) or changed
    elif legacy_context or bool(_legacy_service_migration_marker(session)):
        changed = _ensure_resolved_service_closeout(
            session,
            kind=kind,
            service_state=service_state,
        ) or changed
    if reward_line:
        marker = _legacy_service_migration_marker(session)
        marker.update(
            {
                "version": 1,
                "kind": kind,
                "reward_preserved": True,
                "preserved_reward_log": reward_line,
            }
        )
        changed = _set_legacy_service_migration_marker(session, marker) or changed
        if _LEGACY_REWARD_PRESERVED_LOG not in list(getattr(session, "log", []) or []):
            session.log.append(_LEGACY_REWARD_PRESERVED_LOG)
            changed = True
    return changed


def repair_generated_tag_core_quest_completion(session: Any) -> bool:
    """Restore the closeout pause after a normal Quest resolves a generated TAG lead."""
    if (
        getattr(session, "mode", "") == "complete"
        or getattr(session, "active_quest", None) is not None
        or getattr(session, "tag_generated_completion_pending", False)
        or not is_generated_tag_manifest(getattr(session, "imported_manifest", None))
    ):
        return False
    log = list(getattr(session, "log", []) or [])
    if not any(str(line).startswith("Quest complete! Epic reward:") for line in log):
        return False
    manifest = getattr(session, "imported_manifest", None) or {}
    lead_title = str(manifest.get("title") or "Adventures Guild lead").strip()
    title = f"{lead_title} resolved"
    body = (
        "The Quest is complete and the Quest-giver accepts the result. "
        "The encounter remains peaceful and does not restart; combat treasure is not awarded. "
        "The Epic Reward shown in Narrative is the Quest reward. "
        f"Choose {TAG_GENERATED_CLOSEOUT_ACTION_LABEL} to close this Adventures Guild lead."
    )
    session.tag_generated_completion_pending = True
    session.tag_generated_completion_title = title
    session.tag_generated_completion_body = body
    if body not in log:
        session.log.append(body)
    return True


def _current_imported_room_id(session: Any) -> str:
    map_state = getattr(session, "map_state", None)
    current_tile_id = getattr(map_state, "current_tile_id", None)
    tiles = list(getattr(map_state, "tiles", []) or [])
    tile = next((item for item in tiles if getattr(item, "id", None) == current_tile_id), None)
    content_key = str(getattr(tile, "content_key", "") or "")
    if content_key.startswith("imported:"):
        return content_key.removeprefix("imported:")
    if content_key == "entrance":
        manifest = getattr(session, "imported_manifest", None)
        if isinstance(manifest, dict):
            return str(manifest.get("entrance_room_id") or "")
    return ""


def repair_required_tag_scene_lifecycle(session: Any) -> bool:
    """Upgrade an arrival-completed required TAG scene and start its entry action."""
    manifest = getattr(session, "imported_manifest", None)
    if not isinstance(manifest, dict) or getattr(session, "mode", "") == "complete":
        return False
    manifest_quest = manifest.get("quest")
    complete_when = manifest_quest.get("complete_when") if isinstance(manifest_quest, dict) else None
    if not isinstance(complete_when, dict) or complete_when.get("type") != "tag_scene_resolved":
        return False
    changed = False
    if getattr(session, "imported_quest_complete_when", None) != complete_when:
        session.imported_quest_complete_when = dict(complete_when)
        changed = True
    original_quest = getattr(session, "active_quest", None)
    arrival_completed = (
        getattr(original_quest, "key", "") == "imported_room"
        and bool(getattr(original_quest, "completed", False))
    )
    changed = _repair_repeatable_service_legacy_state(
        session,
        manifest,
        complete_when,
    ) or changed
    quest = getattr(session, "active_quest", None)
    if quest is None:
        return changed
    if getattr(quest, "key", "") == "imported_room":
        quest.key = "tag_generated_scene"
        changed = True
    target_room = str(complete_when.get("room_id") or "")
    from .tag_scene_lifecycle import (
        auto_start_tag_room_actions,
        required_tag_room_actions_are_terminal,
    )

    procedure_terminal = bool(
        target_room and required_tag_room_actions_are_terminal(session, target_room)
    )
    if (
        arrival_completed
        and not getattr(session, "tag_generated_completion_pending", False)
        and not procedure_terminal
    ):
        quest.completed = False
        false_completion_prefixes = (
            "Quest complete: objective location reached.",
            "Quest objective complete. Return to ",
        )
        repaired_log = [
            line
            for line in list(getattr(session, "log", []) or [])
            if not any(str(line).startswith(prefix) for prefix in false_completion_prefixes)
        ]
        if repaired_log != list(getattr(session, "log", []) or []):
            session.log = repaired_log
        fired_triggers = list(getattr(session, "imported_fired_triggers", []) or [])
        if "quest:return_hint" in fired_triggers:
            session.imported_fired_triggers = [
                key for key in fired_triggers if key != "quest:return_hint"
            ]
        changed = True
    if target_room and _current_imported_room_id(session) == target_room:
        changed = auto_start_tag_room_actions(session, target_room) or changed
    return changed


def _diagnostic_action_label(action: Any) -> str:
    if not isinstance(action, dict):
        return ""
    label = str(action.get("label") or "").strip()
    value = str(action.get("action_value") or action.get("value") or "").strip()
    action_type = str(action.get("action_type") or "").strip()
    return label or value or action_type


def generated_tag_manifest_diagnostics(
    manifest: dict[str, Any] | None,
    *,
    current_room_id: str = "",
    active_quest_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return player-facing health checks for generated Adventures Guild modules."""
    tag_reference = tag_reference_from_manifest(manifest)
    if not tag_reference:
        return {"is_generated": False, "warnings": [], "errors": [], "manual_fallback_needed": False}

    rooms = manifest.get("rooms") if isinstance(manifest, dict) else []
    room_ids = {
        str(room.get("id"))
        for room in rooms or []
        if isinstance(room, dict) and room.get("id")
    }
    prompts = tag_reference.get("room_prompts")
    prompts = prompts if isinstance(prompts, dict) else {}
    scene_graph = tag_reference.get("scene_graph")
    scene_graph = scene_graph if isinstance(scene_graph, dict) else {}
    scenes = scene_graph.get("scenes")
    scenes = scenes if isinstance(scenes, dict) else {}
    warnings: list[str] = []
    errors: list[str] = []
    suggested_fixes: list[str] = []

    expected_prompt_ids = [room_id for room_id in room_ids if room_id.startswith("tag-")]
    missing_prompts = sorted(room_id for room_id in expected_prompt_ids if room_id not in prompts)
    if missing_prompts:
        errors.append(f"Missing room prompt metadata for: {', '.join(missing_prompts[:6])}.")
        suggested_fixes.append("Refresh narrative, then regenerate the module if prompts are still missing.")

    current_prompt = prompts.get(current_room_id) if current_room_id else None
    if current_room_id and current_room_id.startswith("tag-") and not isinstance(current_prompt, dict):
        errors.append(f"Current room {current_room_id} has no prompt/action metadata.")
        suggested_fixes.append("Use Refresh narrative. If it remains missing, report this module with Copy Narrative Report.")

    stale_markers = ("Repaired prompt metadata", "older generated Adventures Guild module")
    stale_prompts = [
        room_id
        for room_id, prompt in prompts.items()
        if isinstance(prompt, dict)
        and any(marker in str(prompt.get("body") or "") for marker in stale_markers)
    ]
    if stale_prompts:
        warnings.append(f"Generic repaired wording still present in: {', '.join(stale_prompts[:6])}.")
        suggested_fixes.append("Refresh narrative from the local PDF extraction file.")

    dialog_actions: list[str] = []
    prompt_action_count = 0
    for room_id, prompt in prompts.items():
        if not isinstance(prompt, dict):
            continue
        actions = prompt.get("actions")
        if not isinstance(actions, list):
            warnings.append(f"{room_id} has no visible action list.")
            continue
        prompt_action_count += len([action for action in actions if isinstance(action, dict)])
        for action in actions:
            if not isinstance(action, dict):
                continue
            label = _diagnostic_action_label(action)
            if action.get("action_type") == "dialog" or "Actions" in label:
                dialog_actions.append(f"{room_id}: {label or 'manual dialog'}")

    missing_scene_targets: list[str] = []
    for scene_key, scene in scenes.items():
        if not isinstance(scene, dict):
            continue
        for branch in scene.get("branches") or []:
            if not isinstance(branch, dict):
                continue
            target = str(branch.get("target_scene") or "").strip()
            if target and target not in scenes:
                missing_scene_targets.append(f"{scene_key}->{target}")
    if missing_scene_targets:
        errors.append(f"Scene branch target missing from local extraction: {', '.join(missing_scene_targets[:6])}.")
        suggested_fixes.append("Re-extract the rules PDF or edit tag_scene_narrative_overrides.json to include the target scene.")

    manual_fallback_needed = bool(errors or dialog_actions)
    current_actions = []
    if isinstance(current_prompt, dict):
        current_actions = [
            _diagnostic_action_label(action)
            for action in current_prompt.get("actions") or []
            if _diagnostic_action_label(action)
        ]

    quest_state = active_quest_state if isinstance(active_quest_state, dict) else {}
    return {
        "is_generated": True,
        "title": str((manifest or {}).get("title") or tag_reference.get("title") or "Generated Adventures Guild lead"),
        "lead_type": str(tag_reference.get("lead_type") or ""),
        "lead_detail": str(tag_reference.get("lead_detail") or ""),
        "current_room_id": current_room_id,
        "current_prompt_found": isinstance(current_prompt, dict),
        "current_actions": current_actions,
        "prompt_count": len(prompts),
        "prompt_action_count": prompt_action_count,
        "room_count": len(room_ids),
        "scene_count": len(scenes),
        "scene_branch_count": sum(
            len(scene.get("branches") or [])
            for scene in scenes.values()
            if isinstance(scene, dict)
        ),
        "local_narrative_active": bool(tag_reference.get("local_narrative_override_applied")),
        "refresh_summary": list(tag_reference.get("local_narrative_override_changed_fields") or [])[:12],
        "quest_next_action": str(quest_state.get("next_action") or ""),
        "warnings": warnings,
        "errors": errors,
        "manual_fallback_needed": manual_fallback_needed,
        "manual_fallback_reasons": dialog_actions[:8],
        "suggested_fixes": suggested_fixes,
    }


def _leprechaun_scene_actions() -> list[dict[str, Any]]:
    return [
        {
            "label": "Buy Shoes of Fast Walk",
            "tooltip": "Buy up to one pair per eligible wearer or recipient for 200 gp each. Heroes must be able to use magic items; hirelings are eligible, but animal companions are not.",
            "action_type": "branch",
            "action_value": "leprechaun_shoes",
            "reference": "Scene 2 Shoes of Fast Walk",
            "amount": 1,
        },
        {
            "label": "Learn illusion spell",
            "tooltip": "One eligible character learns one illusion spell automatically for 100 gp, or free if the party bought at least three pairs of magical shoes.",
            "action_type": "branch",
            "action_value": "leprechaun_illusion_spell",
            "reference": "Scene 2 illusion spell - choose spell",
            "amount": 100,
        },
        {
            "label": "Done — leave Blackbird Hill",
            "tooltip": "TAG pp.25-26, Scene 2: choose this only after resolving every desired optional shoe purchase and the single optional illusion lesson. Leaving Blackbird Hill resolves the bargain and ends this Rumour.",
            "action_type": "branch",
            "action_value": "tag_repeatable_service_done",
            "reference": "TAG pp.25-26 Scene 2 Blackbird Hill bargain complete",
            "amount": 0,
            "required_for_completion": True,
        },
    ]


def _upgrade_leprechaun_vendor_manifest(manifest: dict[str, Any], tag_reference: dict[str, Any]) -> None:
    haystack = " ".join(
        str(value or "")
        for value in (
            manifest.get("title"),
            manifest.get("synopsis"),
            tag_reference.get("title"),
            tag_reference.get("lead_detail"),
            tag_reference.get("rewards"),
            (manifest.get("quest") or {}).get("objective_text") if isinstance(manifest.get("quest"), dict) else "",
        )
    ).lower()
    if "leprechaun" not in haystack and "blackbird hill" not in haystack:
        return

    _capture_legacy_service_proxy_names(manifest, tag_reference)
    tag_reference["title"] = tag_reference.get("title") or "Leprechauns at Blackbird Hill"
    tag_reference["scene"] = tag_reference.get("scene") or "Scene 2"
    tag_reference["pdf_pages"] = tag_reference.get("pdf_pages") or "TAG pp.23, 25-26"
    tag_reference["finale_mode"] = "vendor"
    tag_reference["finale_instruction"] = (
        "Choose who buys magical shoes and which single eligible character learns one illusion spell. "
        "The app derives a free lesson automatically after three successful pair purchases."
    )
    tag_reference["rewards"] = (
        "Buy Shoes of Fast Walk for 200 gp per pair, up to one pair per eligible wearer or recipient. "
        "One eligible character may learn one illusion spell for 100 gp, or free if at least three pairs of shoes were bought."
    )
    tag_reference["final_foe_proxy"] = ""
    tag_reference["final_foe_count"] = 0
    tag_reference["final_foes"] = []
    rules = tag_reference.get("rules")
    if not isinstance(rules, list):
        rules = []
    vendor_rule = "Scene 2 is a bargain/vendor scene; no proxy combat is required unless the table deliberately turns the encounter hostile."
    if vendor_rule not in rules:
        rules.append(vendor_rule)
    tag_reference["rules"] = rules

    quest = manifest.get("quest")
    if isinstance(quest, dict):
        quest["complete_when"] = {"type": "tag_scene_resolved", "room_id": "tag-final-scene"}

    prompts = tag_reference.get("room_prompts")
    if not isinstance(prompts, dict):
        prompts = {}
        tag_reference["room_prompts"] = prompts
    prompts["tag-complication"] = {
        "title": "Complication route",
        "body": (
            "Tiny footprints loop around the stones in impossible circles. A laugh skips from one side of the hill to the other, "
            "always just behind the party. No purchase or spell choice is due in this room; continue to the bargain scene when ready."
        ),
        "checklist": [
            "Do not claim an Epic Reward here.",
            "Continue to the bargain scene unless the table deliberately turns the encounter hostile.",
        ],
        "actions": [
            {
                "label": "Proceed to bargain",
                "tooltip": "Mark that the party keeps following the leprechaun trail toward the Scene 2 bargain.",
                "action_type": "route",
                "action_value": "parley_success",
                "reference": "Scene 2 leprechaun bargain route",
                "amount": 0,
            }
        ],
    }
    prompts["tag-final-scene"] = {
        "title": "Bargain choices",
        "body": (
            "The leprechauns finally stop running the party in circles. They are ready to bargain, not to be looted like a monster room. "
            "Choose the purchase or lesson the party wants, pick the receiving character, and confirm payment before leaving."
        ),
        "checklist": [
            "Buy Shoes of Fast Walk only if a character pays 200 gp per pair.",
            "One eligible character may learn one illusion spell for 100 gp, or free if at least three shoe pairs were bought.",
            "Do not roll or claim a core Epic Reward for this generated Adventures Guild scene.",
        ],
        "actions": _leprechaun_scene_actions(),
    }
    tag_reference["prompt_repair_note"] = (
        "Legacy leprechaun generated module upgraded to the Scene 2 vendor finale. "
        "The old proxy Goblins objective and Epic Reward path are not part of this scene."
    )

    for room in manifest.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        if room.get("id") == "tag-complication":
            room["description"] = str(prompts["tag-complication"]["body"])
        if room.get("id") == "tag-final-scene":
            room["title"] = "Blackbird Hill Bargain"
            room["description"] = "The leprechaun rumor is real. Under the old oak at Blackbird Hill, the little folk are ready to bargain: shoes for gold, or one illusion lesson for a magically inclined hero."
            for trigger in room.get("triggers") or []:
                if isinstance(trigger, dict):
                    trigger.pop("encounter", None)
                    if isinstance(trigger.get("log"), str):
                        trigger["log"] = "The leprechaun bargain is ready: buy Shoes of Fast Walk or choose one illusion lesson before leaving Blackbird Hill."


def _upgrade_deoldyn_service_manifest(
    manifest: dict[str, Any],
    tag_reference: dict[str, Any],
) -> bool:
    """Normalize legacy Rumour 11 modules to the repeatable Scene 3 service."""
    try:
        rumor_number = int(tag_reference.get("rumor_number") or 0)
    except (TypeError, ValueError):
        rumor_number = 0
    title = str(tag_reference.get("title") or manifest.get("title") or "")
    if (
        str(tag_reference.get("lead_type") or "").strip().lower() != "rumor"
        or (rumor_number != 11 and "deoldyn" not in title.casefold())
    ):
        return False

    from .tag_campaign import TAG_RUMOR_PROFILES

    _capture_legacy_service_proxy_names(manifest, tag_reference)
    profile = TAG_RUMOR_PROFILES[11]
    expected_actions = [
        deepcopy(action)
        for action in profile.get("final_prompt_actions") or []
        if isinstance(action, dict)
    ]
    changed = False
    expected_reference_fields = {
        "title": profile["title"],
        "scene": profile["scene"],
        "pdf_pages": profile["pdf_pages"],
        "lead_structure": profile["lead_structure"],
        "finale_mode": profile["finale_mode"],
        "finale_instruction": profile["finale_instruction"],
        "rewards": profile["rewards"],
        "module_profile": deepcopy(profile["module_profile"]),
        "rules": deepcopy(profile["rules"]),
        "final_foe_proxy": "",
        "final_foe_count": 0,
        "final_foes": [],
        "scene_graph_terminal_actions": deepcopy(expected_actions),
    }
    for key, expected in expected_reference_fields.items():
        if tag_reference.get(key) != expected:
            tag_reference[key] = expected
            changed = True

    quest = manifest.get("quest")
    if isinstance(quest, dict):
        expected_objective = str(profile["objective"])
        if quest.get("objective_text") != expected_objective:
            quest["objective_text"] = expected_objective
            changed = True
        expected_completion = {"type": "tag_scene_resolved", "room_id": "tag-final-scene"}
        if quest.get("complete_when") != expected_completion:
            quest["complete_when"] = expected_completion
            changed = True

    prompts = tag_reference.get("room_prompts")
    if not isinstance(prompts, dict):
        prompts = {}
        tag_reference["room_prompts"] = prompts
        changed = True
    expected_prompt = {
        "title": "Service choices",
        "body": (
            f"{profile['final_description']} {profile['finale_instruction']} "
            "Training payments remain spent even when an XP roll fails."
        ),
        "checklist": [
            "Select every bow-capable character who will train; each character may train once between adventures.",
            "Commit every payment of 60 gp × current Level before making any training XP roll.",
            "After all payments are committed, make each selected trainee's XP roll automatically; a base Elf may instead choose normal level advancement.",
            "After the simultaneous batch is rolled, add no later trainee; choose Done when the visit is finished.",
        ],
        "actions": deepcopy(expected_actions),
    }
    if prompts.get("tag-final-scene") != expected_prompt:
        prompts["tag-final-scene"] = expected_prompt
        changed = True

    for room in manifest.get("rooms") or []:
        if not isinstance(room, dict) or room.get("id") != "tag-final-scene":
            continue
        expected_title = str(profile["final_title"])
        expected_description = str(profile["final_description"])
        if room.get("title") != expected_title:
            room["title"] = expected_title
            changed = True
        if room.get("description") != expected_description:
            room["description"] = expected_description
            changed = True
        for trigger in room.get("triggers") or []:
            if not isinstance(trigger, dict):
                continue
            if "encounter" in trigger:
                trigger.pop("encounter", None)
                changed = True
            expected_log = (
                "Deoldyn's Scene 3 training service is ready: select all trainees and choices, "
                "commit every payment, then resolve the automatic XP rolls before choosing Done."
            )
            if isinstance(trigger.get("log"), str) and trigger.get("log") != expected_log:
                trigger["log"] = expected_log
                changed = True

    upgrade_note = (
        "TAG pp.24, 26 Rumour 11 upgraded to Deoldyn's persisted Scene 3 batch-training service; "
        "all payments precede automatic XP rolls and Done explicitly resolves the scene."
    )
    if tag_reference.get("deoldyn_scene3_rules_upgrade") != upgrade_note:
        tag_reference["deoldyn_scene3_rules_upgrade"] = upgrade_note
        changed = True
    return changed


def _trim_bofto_scene19_text(value: str) -> str:
    trimmed = re.split(
        r"\bFollowing the Treasure Map Table\b",
        str(value or ""),
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    return re.sub(
        r"\s+The Star-Slayer From Beyond\s*$",
        "",
        trimmed,
        flags=re.IGNORECASE,
    ).strip()


def _bofto_scene19_prompt(body: str) -> dict[str, Any]:
    return {
        "title": "Scene 19",
        "body": _trim_bofto_scene19_text(body),
        "checklist": [
            "Choose the character who succeeded at the Scene 14 theft.",
            "The app assigns the cursed object, rolls the L8 Will Save with printed modifiers, and closes the module.",
            "The curse persists until the carrier explicitly lets Invisible Gremlins take the object.",
        ],
        "actions": [
            {
                "label": "Choose carrier and resolve Scene 19",
                "tooltip": (
                    "Choose the successful thief. The app assigns the cursed object, rolls the TAG p.30 "
                    "L8 Will Save, applies Spellcaster/Cleric +L and the Halfling reroll, then closes this "
                    "module. The curse persists after either result."
                ),
                "action_type": "branch",
                "action_value": "star_object_will_save",
                "reference": "Scene 19 star-shaped object pickup and Will Save",
                "amount": 0,
            }
        ],
    }


def _upgrade_bofto_manifest(manifest: dict[str, Any], tag_reference: dict[str, Any]) -> bool:
    lead_type = str(tag_reference.get("lead_type") or "").strip().lower()
    lead_detail = str(tag_reference.get("lead_detail") or "").strip()
    title = str(tag_reference.get("title") or manifest.get("title") or "")
    try:
        rumor_number = int(tag_reference.get("rumor_number") or 0)
    except (TypeError, ValueError):
        rumor_number = 0
    is_bofto = lead_type == "rumor" and (
        rumor_number == 1
        or lead_detail == "1"
        or "bofto" in lead_detail.lower()
        or "bofto" in title.lower()
    )
    if not is_bofto:
        return False

    changed = False
    scene_graph = tag_reference.get("scene_graph")
    scenes = scene_graph.get("scenes") if isinstance(scene_graph, dict) else None
    scene19_body = ""
    if isinstance(scenes, dict):
        for scene_key, node in scenes.items():
            if not isinstance(node, dict) or str(scene_key).strip().lower() != "scene 19":
                continue
            original = str(node.get("description") or "")
            trimmed = _trim_bofto_scene19_text(original)
            scene19_body = trimmed
            if trimmed != original:
                node["description"] = trimmed
                changed = True

    prompts = tag_reference.get("room_prompts")
    if not isinstance(prompts, dict):
        prompts = {}
        tag_reference["room_prompts"] = prompts
        changed = True
    legacy_values = {"bofto_scene_choice", "star_slayer_check", "star_object_will_save"}
    for prompt_key, prompt in list(prompts.items()):
        if not isinstance(prompt, dict):
            continue
        original_body = str(prompt.get("body") or "")
        trimmed_body = _trim_bofto_scene19_text(original_body)
        if trimmed_body != original_body:
            prompt["body"] = trimmed_body
            changed = True
        prompt_title = str(prompt.get("title") or "").strip().lower()
        is_scene19 = prompt_title == "scene 19" or str(prompt_key).strip().lower() == "tag-scene-19"
        if str(prompt_key).strip().lower() == "tag-unlocked-scene" and (
            "star-shaped object writhes" in trimmed_body.lower()
            or "character who picked it up" in trimmed_body.lower()
        ):
            is_scene19 = True
        if is_scene19:
            replacement = _bofto_scene19_prompt(trimmed_body or scene19_body)
            if prompt != replacement:
                prompts[prompt_key] = replacement
                changed = True
            continue
        actions = prompt.get("actions")
        if isinstance(actions, list):
            filtered = [
                action
                for action in actions
                if not (
                    isinstance(action, dict)
                    and str(action.get("action_value") or "") in legacy_values
                )
            ]
            if filtered != actions:
                prompt["actions"] = filtered
                changed = True

    for room in manifest.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        original = str(room.get("description") or "")
        trimmed = _trim_bofto_scene19_text(original)
        if trimmed != original:
            room["description"] = trimmed
            changed = True
        for trigger in room.get("triggers") or []:
            if not isinstance(trigger, dict) or not isinstance(trigger.get("log"), str):
                continue
            original_log = trigger["log"]
            trimmed_log = _trim_bofto_scene19_text(original_log)
            if trimmed_log != original_log:
                trigger["log"] = trimmed_log
                changed = True

    if tag_reference.get("scene_graph_terminal_actions"):
        tag_reference["scene_graph_terminal_actions"] = []
        changed = True
    if changed:
        tag_reference["bofto_scene19_rules_upgrade"] = "TAG pp.30-31 automatic curse flow"
    return changed


def _repaired_room_prompts(tag_reference: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    title = str(tag_reference.get("title") or manifest.get("title") or "Generated Adventures Guild lead")
    lead_type = str(tag_reference.get("lead_type") or "generated Adventures Guild lead").replace("_", " ")
    playbook = (
        "Repaired prompt metadata: this older generated Adventures Guild module did not carry room prompts, so the app rebuilt generic phase guidance. "
        "Use it as workflow help only; printed scene text, rewards, room counts, and exact outcomes still come from the PDF/player decision."
    )
    return {
        "tag-lead-entry": _generic_tag_prompt(
            "Record lead choice",
            f"{playbook} Entry phase for {lead_type}: establish why the party follows {title}, then decide whether any optional side lead is worth pursuing.",
            action_type="branch",
            action_value="social_choice",
            reference=f"{title}: repaired lead entry",
        ),
        "tag-side-clue": _generic_tag_prompt(
            "Claim printed reward",
            f"{playbook} Side lead phase: record only the clue, reward, XP, or skipped-scene decision that actually applies.",
            action_type="branch",
            action_value="claim_reward",
            reference=f"{title}: repaired side lead",
        ),
        "tag-complication": _generic_tag_prompt(
            "Record route branch",
            f"{playbook} Complication phase: resolve the parley, hostile turn, Clue gate, blocked path, or special procedure before treating the finale as normal exploration.",
            action_type="route",
            action_value="final_route",
            reference=f"{title}: repaired complication",
        ),
        "tag-final-scene": _generic_tag_prompt(
            "Final route",
            f"{playbook} Finale phase: record final route, reward, XP, capture/bounty/treasure handling, then close out Guild, banking, storage, and guidance.",
            action_type="route",
            action_value="final_route",
            reference=f"{title}: repaired finale",
        ),
        "tag-unlocked-scene": _generic_tag_prompt(
            "Mark unlocked scene",
            f"{playbook} Unlocked scene phase: this room exists because of an earlier choice. Record arrival, route, reward, and XP before returning to the main lead.",
            action_type="route",
            action_value="unlock_scene",
            reference=f"{title}: repaired unlocked scene",
        ),
    }


def _medusa_prompt_action(
    label: str,
    tooltip: str,
    *,
    action_value: str,
    reference: str,
) -> dict[str, Any]:
    return {
        "label": label,
        "tooltip": tooltip,
        "action_type": "branch",
        "action_value": action_value,
        "reference": reference,
        "amount": 0,
    }


def _upgrade_medusa_manifest(manifest: dict[str, Any], tag_reference: dict[str, Any]) -> bool:
    try:
        rumor_number = int(tag_reference.get("rumor_number") or 0)
    except (TypeError, ValueError):
        rumor_number = 0
    title = str(tag_reference.get("title") or manifest.get("title") or "")
    if (
        str(tag_reference.get("lead_type") or "").lower() != "rumor"
        or (rumor_number != 2 and "medusa" not in title.lower())
    ):
        return False

    prompts = tag_reference.get("room_prompts")
    if not isinstance(prompts, dict):
        return False
    rooms_by_id = {
        str(room.get("id")): room
        for room in manifest.get("rooms") or []
        if isinstance(room, dict) and room.get("id")
    }
    changed = False
    for room_id, prompt in list(prompts.items()):
        if not isinstance(prompt, dict):
            continue
        body = str(prompt.get("body") or "")
        lower = body.lower()
        replacement: dict[str, Any] | None = None
        room_title = ""
        if "as you come closer to the hunter" in lower and "assassins" in lower:
            room_title = "Approach to the Hunter's Cabin"
            replacement = {
                "title": room_title,
                "body": body,
                "checklist": [
                    "Roll the one printed group Stealth Save using the living party member with the worst modifier.",
                    "On failure, choose whether to convince the assassin agents or fight them.",
                    "After a successful approach or a victory over the agents, choose whether to approach the cabin or return to town.",
                ],
                "actions": [
                    _medusa_prompt_action(
                        "Approach the cabin",
                        "Run TAG Scene 10's group Stealth Save vs L6. The app persists the result and handles any d3+2 assassin ambush.",
                        action_value="medusa_group_stealth",
                        reference="TAG p.28, Scene 10 cabin approach",
                    )
                ],
            }
        elif "you reach the hunter" in lower and "xasartha" in lower:
            room_title = "Xasartha's Cabin"
            replacement = {
                "title": room_title,
                "body": body,
                "checklist": [
                    "Choose whether the party approaches quietly or calls out from outside.",
                    "For a quiet approach, choose the character making the printed L6 Stealth Save.",
                    "The app rolls Xasartha's reaction when the party calls out; do not choose the reaction result.",
                ],
                "actions": [
                    _medusa_prompt_action(
                        "Approach the cabin",
                        "Choose one living character to make Scene 1's L6 Stealth Save before Xasartha's encounter.",
                        action_value="medusa_stealth_approach",
                        reference="TAG p.25, Scene 1 quiet cabin approach",
                    ),
                    _medusa_prompt_action(
                        "Shout out to the Medusa",
                        "Call to Xasartha from outside and let the app roll her printed reaction table.",
                        action_value="medusa_reaction",
                        reference="TAG p.25, Scene 1 Xasartha reaction",
                    ),
                ],
            }
        elif "pendant is magical" in lower and "luck point" in lower:
            room_title = "Xasartha's Emerald Pendant"
            replacement = {
                "title": room_title,
                "body": body,
                "checklist": [
                    "Assign the magical pendant only to the character who tried it on.",
                    "Its Luck allowance recharges at the beginning of each adventure.",
                ],
                "actions": [],
            }
        if replacement is None:
            continue
        if prompt != replacement:
            prompts[room_id] = replacement
            changed = True
        room = rooms_by_id.get(str(room_id))
        if isinstance(room, dict) and room_title and room.get("title") != room_title:
            room["title"] = room_title
            changed = True
    if changed:
        tag_reference["medusa_scene_prompt_upgrade"] = "TAG pp.25-28 typed Scene 10 and Scene 1 choices"
    return changed


def _upgrade_rumor_entry_manifest(tag_reference: dict[str, Any]) -> bool:
    if str(tag_reference.get("lead_type") or "").strip().lower() != "rumor":
        return False
    prompts = tag_reference.get("room_prompts")
    if not isinstance(prompts, dict):
        return False
    changed = False
    entry_prompt = prompts.get("tag-lead-entry")
    if not isinstance(entry_prompt, dict):
        entry_prompt = {
            "title": "Lead entry choices",
            "body": "",
            "checklist": [],
            "actions": [],
        }
        prompts["tag-lead-entry"] = entry_prompt
        changed = True
    from .tag_campaign import tag_rumor_entry_prompt_actions, tag_rumor_entry_scene_key

    entry_scene = tag_rumor_entry_scene_key(tag_reference)
    if entry_scene and tag_reference.get("entry_scene") != entry_scene:
        tag_reference["entry_scene"] = entry_scene
        changed = True
    base_reference = str(tag_reference.get("title") or "Adventures Guild Rumor")
    actions = tag_rumor_entry_prompt_actions(tag_reference, base_reference=base_reference)
    if actions and entry_prompt.get("actions") != actions:
        entry_prompt["actions"] = actions
        changed = True
    if changed:
        tag_reference["rumor_entry_prompt_upgrade"] = "TAG pp.22-24 shared investigate-or-return decision"
    return changed


def _upgrade_daroc_manifest(manifest: dict[str, Any], tag_reference: dict[str, Any]) -> bool:
    """Normalize legacy Rumor 9 metadata to the typed repeat-search lifecycle."""
    try:
        rumor_number = int(tag_reference.get("rumor_number") or 0)
    except (TypeError, ValueError):
        rumor_number = 0
    title = str(tag_reference.get("title") or manifest.get("title") or "")
    if (
        str(tag_reference.get("lead_type") or "").strip().lower() != "rumor"
        or (rumor_number != 9 and "daroc" not in title.casefold())
    ):
        return False

    from .tag_campaign import TAG_RUMOR_PROFILES
    from .tag_daroc import normalize_daroc_scene5_reward_narrative

    profile = TAG_RUMOR_PROFILES[9]
    changed = False
    for key in ("pdf_pages", "finale_instruction", "rewards"):
        expected = profile.get(key)
        if expected is not None and tag_reference.get(key) != expected:
            tag_reference[key] = expected
            changed = True
    prompts = tag_reference.get("room_prompts")
    if isinstance(prompts, dict):
        final_prompt = prompts.get("tag-final-scene")
        if not isinstance(final_prompt, dict):
            final_prompt = {
                "title": "Scene procedure",
                "body": str(profile.get("finale_instruction") or ""),
                "checklist": [],
                "actions": [],
            }
            prompts["tag-final-scene"] = final_prompt
            changed = True
        expected_actions = [
            dict(action)
            for action in profile.get("final_prompt_actions") or []
            if isinstance(action, dict)
        ]
        if final_prompt.get("actions") != expected_actions:
            final_prompt["actions"] = expected_actions
            changed = True
        expected_body = str(profile.get("finale_instruction") or "")
        if expected_body and final_prompt.get("body") != expected_body:
            final_prompt["body"] = expected_body
            changed = True
    expected_terminal = [
        dict(action)
        for action in profile.get("final_prompt_actions") or []
        if isinstance(action, dict)
    ]
    if tag_reference.get("scene_graph_terminal_actions") and tag_reference.get("scene_graph_terminal_actions") != expected_terminal:
        tag_reference["scene_graph_terminal_actions"] = expected_terminal
        changed = True
    if normalize_daroc_scene5_reward_narrative(manifest):
        changed = True
    if changed:
        tag_reference["daroc_scene5_rules_upgrade"] = (
            "TAG pp.20, 24, 26 selected-character Streetwise search, retained progress, "
            "non-permanent Give up, and player-confirmed 200 gp reward"
        )
    return changed


def _upgrade_required_tag_scene_lifecycle(
    manifest: dict[str, Any],
    tag_reference: dict[str, Any],
) -> bool:
    """Backfill declarative lifecycle metadata for verified required TAG scenes."""
    from .tag_scene_lifecycle import tag_action_lifecycle

    changed = False
    prompts = tag_reference.get("room_prompts")
    final_requires_resolution = False
    if isinstance(prompts, dict):
        for prompt_id, prompt in prompts.items():
            if not isinstance(prompt, dict):
                continue
            actions = prompt.get("actions")
            for action in actions if isinstance(actions, list) else []:
                if not isinstance(action, dict):
                    continue
                lifecycle = tag_action_lifecycle(str(action.get("action_value") or ""))
                if lifecycle is None:
                    continue
                if lifecycle.auto_start and action.get("auto_start") is not True:
                    action["auto_start"] = True
                    changed = True
                if lifecycle.required_for_completion and action.get("required_for_completion") is not True:
                    action["required_for_completion"] = True
                    changed = True
                if prompt_id == "tag-final-scene" and lifecycle.required_for_completion:
                    final_requires_resolution = True
    if final_requires_resolution:
        expected_completion = {"type": "tag_scene_resolved", "room_id": "tag-final-scene"}
        quest = manifest.get("quest")
        if isinstance(quest, dict) and quest.get("complete_when") != expected_completion:
            quest["complete_when"] = expected_completion
            changed = True
        if tag_reference.get("completion_policy") != "scene_resolved_after_required_action":
            tag_reference["completion_policy"] = "scene_resolved_after_required_action"
            changed = True
    return changed


def upgrade_tag_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    parameters = manifest.get("source", {}).get("parameters", {})
    tag_reference = parameters.get("tag_reference") if isinstance(parameters, dict) else None
    map_roll = 0
    if isinstance(tag_reference, dict):
        _upgrade_leprechaun_vendor_manifest(manifest, tag_reference)
        try:
            map_roll = int(tag_reference.get("treasure_map_destination") or tag_reference.get("map_roll") or 0)
        except (TypeError, ValueError):
            map_roll = 0
        is_treasure_map = str(tag_reference.get("lead_type") or "") == "treasure_map" or bool(map_roll)
        rewards = str(tag_reference.get("rewards") or "")
        if "Apply The Map Leads To" in rewards:
            tag_reference["rewards"] = treasure_map_note_for(map_roll).removeprefix("TAG guidance: ")
            is_treasure_map = True
        if is_treasure_map:
            tag_reference.setdefault("side_reward_note", treasure_map_note_for(map_roll).removeprefix("TAG guidance: "))
            tag_reference.setdefault("final_reward_note", treasure_map_note_for(map_roll, final=True).removeprefix("TAG final guidance: "))
        prompts = tag_reference.get("room_prompts")
        if not isinstance(prompts, dict) or not prompts:
            tag_reference["room_prompts"] = _repaired_room_prompts(tag_reference, manifest)
            tag_reference["prompt_repair_note"] = (
                "Generic generated Adventures Guild room prompts were rebuilt for this older module. "
                "Use them as app workflow guidance only; exact printed text and rewards remain with the PDF/player."
            )
            prompts = tag_reference["room_prompts"]
        _upgrade_deoldyn_service_manifest(manifest, tag_reference)
        _apply_local_tag_narrative_override(manifest, tag_reference)
        _upgrade_rumor_entry_manifest(tag_reference)
        _upgrade_daroc_manifest(manifest, tag_reference)
        _upgrade_bofto_manifest(manifest, tag_reference)
        _upgrade_medusa_manifest(manifest, tag_reference)
        _upgrade_required_tag_scene_lifecycle(manifest, tag_reference)
        if is_treasure_map:
            if isinstance(prompts, dict):
                for prompt in prompts.values():
                    if not isinstance(prompt, dict):
                        continue
                    actions = prompt.get("actions")
                    if isinstance(actions, list):
                        prompt["actions"] = [
                            action
                            for action in actions
                            if not (isinstance(action, dict) and action.get("action_value") == "treasure_map_follow")
                        ]

    for room in manifest.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        for trigger in room.get("triggers") or []:
            if not isinstance(trigger, dict):
                continue
            log_line = trigger.get("log")
            if isinstance(log_line, str):
                trigger["log"] = normalize_tag_log_line(log_line)
    ending = manifest.get("ending")
    if isinstance(ending, dict):
        for key in ("victory_text", "defeat_text"):
            value = ending.get(key)
            if isinstance(value, str):
                ending[key] = normalize_tag_log_line(value)
    return manifest
