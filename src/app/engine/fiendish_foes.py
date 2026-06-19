"""Fiendish Foes optional tables (EE PDF p.180 / book p.179).

PDF: use when 2+ heroes are L3+; works in all dungeon types; replace standard
monster tables entirely or 50% of the time (d6 1-3 standard, 4-6 fiendish).
Only fiendish-tagged foes use the Fiendish Foes treasure tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .dice import roll_d6

if TYPE_CHECKING:
    from ..schemas import PartyMemberState, SessionState

FiendishFoesMode = Literal["off", "always", "mixed"]

FIENDISH_FOE_CATEGORIES = frozenset({"vermin", "minions", "weird", "boss"})


def normalize_fiendish_foes_mode(value: str | None) -> FiendishFoesMode:
    if value in {"always", "mixed"}:
        return value  # type: ignore[return-value]
    return "off"


def count_level3_plus_heroes(party: list[PartyMemberState]) -> int:
    return sum(1 for member in party if (member.level or 1) >= 3)


def party_fiendish_foes_eligible(party: list[PartyMemberState]) -> bool:
    """EE p.180: start using when 2+ heroes are L3+."""
    return count_level3_plus_heroes(party) >= 2


def resolve_use_fiendish_foes_table(
    mode: FiendishFoesMode,
    *,
    roll_fn=None,
) -> tuple[bool, int | None]:
    if mode == "off":
        return False, None
    if mode == "always":
        return True, None
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


def fiendish_foes_mode_label(mode: FiendishFoesMode) -> str:
    if mode == "always":
        return "Fiendish Foes replace standard monster tables (EE p.180)"
    if mode == "mixed":
        return "Fiendish Foes mixed 50% (d6 1-3 standard, 4-6 fiendish; EE p.180)"
    return "Standard monster tables only"
