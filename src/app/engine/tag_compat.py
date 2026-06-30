from __future__ import annotations

import re
from typing import Any


TREASURE_MAP_PROCEDURE_NOTES: dict[int, dict[str, str]] = {
    1: {
        "title": "Underground caves",
        "procedure": "Underground caves procedure: use Claim Treasure for ordinary room treasure. Separately, open TAG Actions > Branch > Underground caves room target to roll/log the d6+3 room target. Track that count, skip entrance-room content, dead-end unopened exits after the target count, then sign off the final Boss with +2 Life and double maximum treasure.",
        "final": "Underground caves closeout: confirm the room target was reached, unopened exits were dead-ended, the final Boss used +2 Life, and double maximum treasure was handled before XP, Guild share, banking, or storage.",
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
        if str(tag_reference.get("lead_type") or "") == "treasure_map" or map_roll:
            prompts = tag_reference.get("room_prompts")
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
