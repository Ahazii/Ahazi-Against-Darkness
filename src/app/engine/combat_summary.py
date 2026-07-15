"""Readable summaries of combat round log output."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class DamageEvent:
    actor: str
    target: str
    damage: int
    direction: str
    killed: bool = False


_HIT_PATTERNS = (
    re.compile(
        r"(?P<actor>[^.;]+?) hits (?P<target>[^.;]+?) for (?P<damage>\d+) "
        r"(?:subdual )?damage(?: with [^.;]+)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<target>[^.;]+?) takes (?P<damage>\d+) "
        r"(?:extra )?damage from (?P<actor>[^.;]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<target>[^.;]+?) loses (?P<damage>\d+) Life(?: to (?P<actor>[^.;]+))?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<actor>[^.;]+?) (?:wounds|claws|burns|deals|inflicts|slices into) "
        r"(?P<target>[^.;]+?) for (?P<damage>\d+) (?:Life|damage)",
        re.IGNORECASE,
    ),
)
_DEFEAT_PATTERN = re.compile(
    r"(?P<target>[^.;]+?) (?:falls asleep and is|is|are) "
    r"(?:defeated|slain|destroyed|subdued)",
    re.IGNORECASE,
)
_SLAYS_PATTERN = re.compile(
    r"(?P<actor>[^.;]+?) slays (?P<count>\d+) (?P<target>[^.;]+?)(?: with| as|\.|$)",
    re.IGNORECASE,
)


def _clean_name(value: str | None) -> str:
    if not value:
        return "Unknown"
    cleaned = re.sub(r"\s+", " ", value.strip(" .,:;"))
    return cleaned or "Unknown"


def _normalize_name(value: str | None) -> str:
    cleaned = _clean_name(value).lower()
    cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return " ".join(cleaned.split())


def _exact_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", _clean_name(value).lower())


def _matches_name(value: str, names: set[str]) -> bool:
    normalized = _normalize_name(value)
    if not normalized:
        return False
    return normalized in names or any(normalized.startswith(f"{name} ") for name in names)


def _name_set(names: list[str] | tuple[str, ...] | set[str] | None) -> set[str]:
    return {_normalize_name(name) for name in (names or []) if _normalize_name(name)}


def _direction(actor: str, target: str, party_names: set[str], enemy_names: set[str]) -> str:
    actor_is_party = _matches_name(actor, party_names)
    target_is_party = _matches_name(target, party_names)
    actor_is_enemy = _matches_name(actor, enemy_names)
    target_is_enemy = _matches_name(target, enemy_names)
    if actor_is_party or target_is_enemy:
        return "outgoing"
    if target_is_party or actor_is_enemy:
        return "incoming"
    return "generic"


def _extract_damage_events(
    line: str,
    *,
    party_names: set[str],
    enemy_names: set[str],
) -> list[DamageEvent]:
    events: list[DamageEvent] = []
    for pattern in _HIT_PATTERNS:
        for match in pattern.finditer(line):
            actor = _clean_name(match.groupdict().get("actor") or "environment")
            target = _clean_name(match.group("target"))
            damage = int(match.group("damage"))
            if damage <= 0:
                continue
            events.append(
                DamageEvent(
                    actor=actor,
                    target=target,
                    damage=damage,
                    direction=_direction(actor, target, party_names, enemy_names),
                )
            )
    return events


def _extract_slay_events(
    line: str,
    *,
    party_names: set[str],
    enemy_names: set[str],
) -> list[DamageEvent]:
    events: list[DamageEvent] = []
    for match in _SLAYS_PATTERN.finditer(line):
        actor = _clean_name(match.group("actor"))
        if "'s " in actor:
            actor = actor.split("'s ", 1)[0]
        target = _clean_name(match.group("target"))
        count = int(match.group("count"))
        if count <= 0:
            continue
        events.append(
            DamageEvent(
                actor=actor,
                target=target,
                damage=count,
                direction=_direction(actor, target, party_names, enemy_names),
                killed=True,
            )
        )
    return events


def _extract_defeats(line: str) -> list[str]:
    return [_clean_name(match.group("target")) for match in _DEFEAT_PATTERN.finditer(line)]


def _mark_defeats(events: list[DamageEvent], defeated_targets: list[str]) -> list[str]:
    unassigned: list[str] = []
    for target in defeated_targets:
        exact_target = _exact_name(target)
        for event in reversed(events):
            if event.direction == "outgoing" and not event.killed and _exact_name(event.target) == exact_target:
                event.killed = True
                break
        else:
            for event in reversed(events):
                if (
                    event.direction == "outgoing"
                    and not event.killed
                    and _normalize_name(event.target) == _normalize_name(target)
                ):
                    event.killed = True
                    break
            else:
                unassigned.append(target)
    return unassigned


def _join_clauses(clauses: list[str]) -> str:
    if len(clauses) <= 1:
        return clauses[0] if clauses else ""
    return f"{', '.join(clauses[:-1])} and {clauses[-1]}"


def _format_outgoing(events: list[DamageEvent]) -> list[str]:
    sentences: list[str] = []
    actor_order: list[str] = []
    by_actor: dict[str, list[DamageEvent]] = {}
    for event in events:
        if event.actor not in by_actor:
            actor_order.append(event.actor)
            by_actor[event.actor] = []
        by_actor[event.actor].append(event)
    for actor in actor_order:
        clauses = []
        for event in by_actor[actor]:
            if event.killed:
                clauses.append(f"killed {event.target} with a hit for {event.damage} damage")
            else:
                clauses.append(f"hit {event.target} for {event.damage} damage")
        sentences.append(f"{actor} {_join_clauses(clauses)}.")
    return sentences


def _format_incoming(events: list[DamageEvent]) -> list[str]:
    sentences: list[str] = []
    for event in events:
        if event.actor == "environment":
            sentences.append(f"{event.target} took {event.damage} damage.")
        else:
            sentences.append(f"{event.target} took {event.damage} damage from {event.actor}.")
    return sentences


def _format_generic(events: list[DamageEvent]) -> list[str]:
    return [f"{event.actor} hit {event.target} for {event.damage} damage." for event in events]


def summarize_combat_log(
    log_lines: list[str],
    *,
    party_names: list[str] | tuple[str, ...] | set[str] | None = None,
    enemy_names: list[str] | tuple[str, ...] | set[str] | None = None,
) -> str:
    """Build a short narrative round recap from raw combat log lines."""
    if not log_lines:
        return ""
    party_name_set = _name_set(party_names)
    enemy_name_set = _name_set(enemy_names)
    events: list[DamageEvent] = []
    defeated: list[str] = []
    regen_blocked = 0
    for line in log_lines:
        events.extend(_extract_damage_events(line, party_names=party_name_set, enemy_names=enemy_name_set))
        events.extend(_extract_slay_events(line, party_names=party_name_set, enemy_names=enemy_name_set))
        defeated.extend(_extract_defeats(line))
        if "cannot regenerate" in line.lower():
            regen_blocked += 1
    unassigned_defeats = _mark_defeats(events, defeated)
    outgoing = [event for event in events if event.direction == "outgoing"]
    incoming = [event for event in events if event.direction == "incoming"]
    generic = [event for event in events if event.direction == "generic"]
    parts: list[str] = []
    parts.extend(_format_outgoing(outgoing))
    parts.extend(_format_incoming(incoming))
    parts.extend(_format_generic(generic))
    for target in unassigned_defeats:
        parts.append(f"{target} was defeated.")
    if regen_blocked:
        parts.append("Regeneration was blocked.")
    if not parts:
        return "No hits, wounds, or foe defeats this round."
    return " ".join(parts)
