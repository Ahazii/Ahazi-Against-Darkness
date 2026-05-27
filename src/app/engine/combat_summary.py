"""One-line summaries of combat round log output."""

from __future__ import annotations

import re


def summarize_combat_log(log_lines: list[str]) -> str:
    """Build a short round recap from raw combat log lines."""
    if not log_lines:
        return ""
    hits = 0
    slain = 0
    party_wounds = 0
    regen_blocked = 0
    for line in log_lines:
        lower = line.lower()
        if " hits " in lower and " for " in lower and " damage" in lower:
            hits += 1
        elif " is defeated" in lower or " is slain" in lower or " is destroyed" in lower:
            slain += 1
        elif " loses " in lower and " life" in lower:
            match = re.search(r"loses (\d+) life", lower)
            if match:
                party_wounds += int(match.group(1))
        elif "cannot regenerate" in lower:
            regen_blocked += 1
    parts: list[str] = []
    if hits:
        parts.append(f"{hits} hit{'s' if hits != 1 else ''}")
    if slain:
        parts.append(f"{slain} foe{'s' if slain != 1 else ''} down")
    if party_wounds:
        parts.append(f"party −{party_wounds} Life")
    if regen_blocked:
        parts.append("regen blocked")
    if not parts:
        return "No hits this round."
    return "; ".join(parts)
