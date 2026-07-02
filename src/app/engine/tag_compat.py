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
                "label": "Open Adventures Guild Actions",
                "tooltip": "Open the full Adventures Guild Actions dialog without changing any values.",
                "action_type": "dialog",
            },
            {
                "label": title,
                "tooltip": "Prefill Adventures Guild Actions from repaired generic prompt metadata. Confirm exact values from the PDF/player decision.",
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
