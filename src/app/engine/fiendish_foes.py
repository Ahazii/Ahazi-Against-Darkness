"""Fiendish Foes optional tables (EE PDF p.180 / book p.179).

PDF: when 2+ heroes are L3+, roll d6 when resolving monster tables that have
fiendish versions — 1-3 standard, 4-6 fiendish. Traps, events, and features
use the current environment tables. Only fiendish-tagged foes use Fiendish
Foes treasure tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .dice import roll_d6

if TYPE_CHECKING:
    from ..schemas import PartyMemberState, SessionState

FIENDISH_FOE_CATEGORIES = frozenset({"vermin", "minions", "weird", "boss"})


def normalize_fiendish_foes_enabled(value: bool | str | None = None, *, legacy_mode: str | None = None) -> bool:
    """Default enabled. Legacy ``fiendish_foes_mode``: off=False, always/mixed=True."""
    if isinstance(value, bool):
        return value
    if legacy_mode is not None:
        return legacy_mode in {"always", "mixed"}
    if value in {False, "false", "0", "off"}:
        return False
    if value in {True, "true", "1", "on"}:
        return True
    return True


def migrate_legacy_fiendish_foes_mode(mode: str | None) -> bool:
    return normalize_fiendish_foes_enabled(legacy_mode=mode)


def count_level3_plus_heroes(party: list[PartyMemberState]) -> int:
    return sum(1 for member in party if (member.level or 1) >= 3)


def party_fiendish_foes_eligible(party: list[PartyMemberState]) -> bool:
    """EE p.180: apply mixed fiendish rolls when 2+ heroes are L3+."""
    return count_level3_plus_heroes(party) >= 2


def resolve_use_fiendish_foes_table(
    enabled: bool,
    *,
    eligible: bool = True,
    roll_fn=None,
) -> tuple[bool, int | None]:
    if not enabled or not eligible:
        return False, None
    roller = roll_d6 if roll_fn is None else roll_fn
    roll = roller()
    return roll >= 4, roll


def resolve_monster_table_key(
    monsters: dict,
    session: SessionState,
    category: str,
    *,
    use_fiendish: bool,
) -> str:
    if use_fiendish and category in FIENDISH_FOE_CATEGORIES:
        fiendish_key = f"fiendish_foes_{category}"
        if fiendish_key in monsters:
            return fiendish_key
    table_key = category
    if session.environment != "dungeon":
        env_key = f"{session.environment}_{category}"
        if env_key in monsters:
            table_key = env_key
    return table_key


def template_never_wandering(template: dict) -> bool:
    """True when this monster must not appear as a wandering monster."""
    if template.get("never_wandering"):
        return True
    tags = {str(tag).lower() for tag in template.get("tags", [])}
    if "dragon" in tags:
        return True
    for rule in template.get("special_rules", []):
        rule_type = str(rule.get("type", "")).lower()
        if rule_type in {"no_wandering_monster", "no_wandering"}:
            return True
    return False


def fiendish_foes_session_label(enabled: bool, *, eligible: bool) -> str:
    if not enabled:
        return "Fiendish Foes disabled — standard monster tables only"
    if not eligible:
        return (
            "Fiendish Foes enabled — standard tables until 2+ heroes reach L3 "
            "(EE p.180)"
        )
    return "Fiendish Foes enabled — d6 1-3 standard, 4-6 fiendish per monster table (EE p.180)"
