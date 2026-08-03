from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


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


def normalize_tag_log_line(line: str) -> str:
    text = str(line or "")
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
        "Choose Return to town and finish to close this Adventures Guild lead."
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
    quest = getattr(session, "active_quest", None)
    if quest is None:
        return False
    changed = False
    if getattr(session, "imported_quest_complete_when", None) != complete_when:
        session.imported_quest_complete_when = dict(complete_when)
        changed = True
    arrival_completed = getattr(quest, "key", "") == "imported_room" and bool(getattr(quest, "completed", False))
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
            "tooltip": "Buy up to one pair per character for 200 gp each. Only characters who can use magic items, and hirelings, may use them; animal companions may not.",
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

    tag_reference["title"] = tag_reference.get("title") or "Leprechauns at Blackbird Hill"
    tag_reference["scene"] = tag_reference.get("scene") or "Scene 2"
    tag_reference["pdf_pages"] = tag_reference.get("pdf_pages") or "TAG pp.23, 25"
    tag_reference["finale_mode"] = "vendor"
    tag_reference["finale_instruction"] = (
        "Choose who buys magical shoes, whether the party buys enough pairs to make spell teaching free, "
        "and which single eligible character learns an illusion spell."
    )
    tag_reference["rewards"] = (
        "Buy Shoes of Fast Walk for 200 gp per pair, up to one pair per character. "
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
        quest["complete_when"] = {"type": "room_reached", "room_id": "tag-final-scene"}

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
        _apply_local_tag_narrative_override(manifest, tag_reference)
        _upgrade_rumor_entry_manifest(tag_reference)
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
