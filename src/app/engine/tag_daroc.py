"""Typed TAG Scene 5 procedure for Daroc's lost familiar."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


TAG_TOWN_STREETWISE_CLUE = "TAG Town Streetwise Clue"
DAROC_FAMILIAR_REWARD_GP = 200
_CAT_LIKE_CLASS_PATTERN = re.compile(r"\b(cat-like|catlike|catfolk|cat folk|feline|felid)\b", re.IGNORECASE)
_CAT_COMPANION_PATTERN = re.compile(
    r"\b(cat|wildcat|panther|tiger|giant cat|giant feline)\b",
    re.IGNORECASE,
)


class DarocPartyMember(Protocol):
    character_id: str
    name: str
    class_id: str
    class_name: str
    current_life: int
    gold: int
    clues: int
    statuses: list[str]
    abilities: list[str]
    class_traits: list[str]
    companion_kind: str | None


@dataclass(frozen=True)
class DarocFamiliarResult:
    success: bool
    required_clues: int
    available_clues: int
    discount_reason: str
    recipient_id: str | None
    result_text: str


def town_streetwise_clue_count(member: DarocPartyMember) -> int:
    marked = sum(1 for status in member.statuses if status == TAG_TOWN_STREETWISE_CLUE)
    return min(max(0, int(member.clues)), marked)


def record_town_streetwise_clue(member: DarocPartyMember) -> None:
    member.statuses.append(TAG_TOWN_STREETWISE_CLUE)


def normalize_town_streetwise_clues(member: DarocPartyMember) -> None:
    allowed = max(0, int(member.clues))
    retained = 0
    statuses: list[str] = []
    for status in member.statuses:
        if status != TAG_TOWN_STREETWISE_CLUE:
            statuses.append(status)
            continue
        if retained < allowed:
            statuses.append(status)
            retained += 1
    member.statuses = statuses


def _member_discount_reason(member: DarocPartyMember) -> str:
    class_text = f"{member.class_id} {member.class_name}".lower().replace("_", " ")
    if re.search(r"\bbeastmaster\b", class_text):
        return f"{member.name} is a Beastmaster"
    if re.search(r"\bdruid\b", class_text):
        return f"{member.name} is a Druid"
    metadata = " ".join(
        [
            class_text,
            *(str(value) for value in member.class_traits),
            *(str(value) for value in member.abilities),
        ]
    )
    if _CAT_LIKE_CLASS_PATTERN.search(metadata):
        return f"{member.name} is cat-like"
    if _CAT_COMPANION_PATTERN.search(str(member.companion_kind or "")):
        return f"{member.name} has a cat animal companion"
    return ""


def daroc_discount_reason(
    party: list[DarocPartyMember],
    *,
    active_companion_kind: str | None = None,
    active_companion_life: int = 0,
) -> str:
    for member in party:
        if member.current_life <= 0:
            continue
        reason = _member_discount_reason(member)
        if reason:
            return reason
    if active_companion_life > 0 and _CAT_COMPANION_PATTERN.search(str(active_companion_kind or "")):
        companion = str(active_companion_kind or "cat").strip().title()
        return f"the party has an active {companion} animal companion"
    return ""


def daroc_familiar_view(
    party: list[DarocPartyMember],
    *,
    active_companion_kind: str | None = None,
    active_companion_life: int = 0,
    resolved: bool = False,
) -> dict[str, object]:
    living = [member for member in party if member.current_life > 0]
    reason = daroc_discount_reason(
        living,
        active_companion_kind=active_companion_kind,
        active_companion_life=active_companion_life,
    )
    required = 1 if reason else 2
    holders = [
        {
            "character_id": member.character_id,
            "name": member.name,
            "clues": town_streetwise_clue_count(member),
        }
        for member in living
        if town_streetwise_clue_count(member)
    ]
    return {
        "required_clues": required,
        "available_clues": sum(int(holder["clues"]) for holder in holders),
        "discount_reason": reason,
        "holders": holders,
        "reward_gp": DAROC_FAMILIAR_REWARD_GP,
        "resolved": resolved,
    }


def resolve_daroc_familiar(
    party: list[DarocPartyMember],
    *,
    recipient_id: str,
    active_companion_kind: str | None = None,
    active_companion_life: int = 0,
) -> DarocFamiliarResult:
    living = [member for member in party if member.current_life > 0]
    recipient = next((member for member in living if member.character_id == recipient_id), None)
    view = daroc_familiar_view(
        living,
        active_companion_kind=active_companion_kind,
        active_companion_life=active_companion_life,
    )
    required = int(view["required_clues"])
    available = int(view["available_clues"])
    reason = str(view["discount_reason"])
    if recipient is None:
        return DarocFamiliarResult(
            success=False,
            required_clues=required,
            available_clues=available,
            discount_reason=reason,
            recipient_id=None,
            result_text=f"Choose a living party member to receive Daroc's {DAROC_FAMILIAR_REWARD_GP} gp reward.",
        )
    if available < required:
        reduction = f" The cost is reduced because {reason}." if reason else ""
        return DarocFamiliarResult(
            success=False,
            required_clues=required,
            available_clues=available,
            discount_reason=reason,
            recipient_id=recipient.character_id,
            result_text=(
                f"Daroc's cat is still missing: the party has {available} of {required} required town "
                f"Streetwise Clue(s). Clues from previous adventures do not count.{reduction}"
            ),
        )

    remaining = required
    spent: list[str] = []
    for member in living:
        if remaining <= 0:
            break
        count = min(remaining, town_streetwise_clue_count(member))
        if count <= 0:
            continue
        member.clues -= count
        for _ in range(count):
            member.statuses.remove(TAG_TOWN_STREETWISE_CLUE)
        remaining -= count
        spent.append(f"{member.name} {count}")

    recipient.gold += DAROC_FAMILIAR_REWARD_GP
    reduction = f" The cost was reduced to 1 because {reason}." if reason else ""
    return DarocFamiliarResult(
        success=True,
        required_clues=required,
        available_clues=available,
        discount_reason=reason,
        recipient_id=recipient.character_id,
        result_text=(
            f"The party spends {required} town Streetwise Clue(s) ({', '.join(spent)}) and finds Daroc's "
            f"lost cat.{reduction} {recipient.name} receives {DAROC_FAMILIAR_REWARD_GP} gp, and the party gains 1 pending XP roll."
        ),
    )
