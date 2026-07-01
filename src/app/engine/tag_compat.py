from __future__ import annotations

import re
from typing import Any


TREASURE_MAP_PROCEDURE_NOTES: dict[int, dict[str, str]] = {
    1: {
        "title": "Underground caves",
        "procedure": "Underground caves procedure: use Claim Treasure for ordinary room treasure. Separately, run Underground caves room target once to roll/log the d6+3 room target. The app then counts rooms, makes the target room the Treasure Map final Boss room, dead-ends unopened exits there, and completes the objective after that Boss is defeated.",
        "final": "Underground caves closeout: after the target-room Boss is defeated, review double maximum treasure handling, XP, Guild share, banking, or storage before claiming the Treasure Map quest reward.",
    },
    2: {
        "title": "Forgotten temple",
        "procedure": "Forgotten temple procedure: use Claim Treasure for ordinary room treasure. Separately, use TAG Actions to record idol value, leader scroll chance, cultist treasure, XP, and how the heavy idol is carried or stored when those steps become relevant.",
        "final": "Forgotten temple closeout: confirm idol value, leader scroll chance, cultist treasure, XP, Guild share, banking, and storage.",
    },
    3: {
        "title": "Hostile humanoid camp",
        "procedure": "Hostile humanoid camp procedure: choose report, stealth theft, or fight before reward and XP handling. Use TAG Actions to record that approach; Claim Treasure only handles ordinary room hoards.",
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
            "If the room says hidden treasure was found, use Claim Treasure. Use TAG Actions only to record the printed Map Leads To procedure, reward accounting, XP, Guild share, banking, and storage."
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
            "Use the generated TAG Director for the current phase, then record only the branch, route, reward, or XP that actually happened.",
        ],
        "actions": [
            {
                "label": "Open TAG Actions",
                "tooltip": "Open the full TAG Actions dialog without changing any values.",
                "action_type": "dialog",
            },
            {
                "label": title,
                "tooltip": "Prefill TAG Actions from repaired generic prompt metadata. Confirm exact values from the PDF/player decision.",
                "action_type": action_type,
                "action_value": action_value,
                "reference": reference,
                "amount": 0,
            },
        ],
    }


def _repaired_room_prompts(tag_reference: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    title = str(tag_reference.get("title") or manifest.get("title") or "Generated TAG lead")
    lead_type = str(tag_reference.get("lead_type") or "generated TAG lead").replace("_", " ")
    playbook = (
        "Repaired prompt metadata: this older generated TAG module did not carry room prompts, so the app rebuilt generic phase guidance. "
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
        try:
            map_roll = int(tag_reference.get("treasure_map_destination") or tag_reference.get("map_roll") or 0)
        except (TypeError, ValueError):
            map_roll = 0
        rewards = str(tag_reference.get("rewards") or "")
        if "Apply The Map Leads To" in rewards:
            tag_reference["rewards"] = treasure_map_note_for(map_roll).removeprefix("TAG guidance: ")
        tag_reference.setdefault("side_reward_note", treasure_map_note_for(map_roll).removeprefix("TAG guidance: "))
        tag_reference.setdefault("final_reward_note", treasure_map_note_for(map_roll, final=True).removeprefix("TAG final guidance: "))
        prompts = tag_reference.get("room_prompts")
        if not isinstance(prompts, dict) or not prompts:
            tag_reference["room_prompts"] = _repaired_room_prompts(tag_reference, manifest)
            tag_reference["prompt_repair_note"] = (
                "Generic generated TAG room prompts were rebuilt for this older module. "
                "Use them as app workflow guidance only; exact printed text and rewards remain with the PDF/player."
            )
            prompts = tag_reference["room_prompts"]
        if str(tag_reference.get("lead_type") or "") == "treasure_map" or map_roll:
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
