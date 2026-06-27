"""FD quest scroll rewards — player-chosen spell scrolls (FD p.54 Dark Pits)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState
from .forsaken_depths_heroic_spells import heroic_spell_names
from .spells import normalize_spell_name

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


def _spell_names_from_table_rows(rows: list[dict], field: str = "spell") -> list[str]:
    names: list[str] = []
    for row in rows:
        name = str(row.get(field) or row.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def fd_legendary_spell_names(engine: RandomDungeonEngine) -> list[str]:
    rows = engine.table_roller.tables.get("fd_legendary_spell_table") or []
    return _spell_names_from_table_rows(rows, field="name")


def fd_spell_reward_catalog(engine: RandomDungeonEngine) -> dict[str, list[str]]:
    """Spells eligible for Dark Pits (and similar) scroll rewards by tier."""
    tables = engine.table_roller.tables
    basic = _spell_names_from_table_rows(tables.get("basic_spells_table") or [])
    expert: list[str] = []
    for row in engine.rules.expert_skills().get("expert_spells") or []:
        name = str(row.get("name") or "").strip()
        if name and name not in expert:
            expert.append(name)
    basic_norm = {normalize_spell_name(spell) for spell in basic}
    expert_norm = {normalize_spell_name(spell) for spell in expert}
    legendary = fd_legendary_spell_names(engine)
    legendary_norm = {normalize_spell_name(spell) for spell in legendary}
    heroic: list[str] = []
    for spell in heroic_spell_names():
        key = normalize_spell_name(spell)
        if key in basic_norm or key in expert_norm or key in legendary_norm:
            continue
        if spell not in heroic:
            heroic.append(spell)
    return {
        "basic": basic,
        "expert": expert,
        "heroic": heroic,
        "legendary": legendary,
    }


def resolve_fd_spell_scroll_item(engine: RandomDungeonEngine, spell_name: str) -> str | None:
    if not spell_name or not str(spell_name).strip():
        return None
    normalized = normalize_spell_name(spell_name)
    tables = engine.table_roller.tables
    for row in tables.get("illusionist_spells_table") or []:
        spell = str(row.get("spell", "")).strip()
        if spell and normalize_spell_name(spell) == normalized:
            return f"Prism of {spell}"
    for row in tables.get("druid_spells_table") or []:
        spell = str(row.get("spell", "")).strip()
        if spell and normalize_spell_name(spell) == normalized:
            return f"Bark of {spell}"
    return f"Scroll of {str(spell_name).strip()}"


def validate_fd_reward_spell(engine: RandomDungeonEngine, spell_name: str) -> bool:
    catalog = fd_spell_reward_catalog(engine)
    target = normalize_spell_name(spell_name)
    for tier_spells in catalog.values():
        if any(normalize_spell_name(spell) == target for spell in tier_spells):
            return True
    return False


def grant_fd_spell_scroll(
    engine: RandomDungeonEngine,
    session: SessionState,
    member: PartyMemberState,
    spell_name: str,
    *,
    show_rolls: bool = True,
) -> bool:
    if not validate_fd_reward_spell(engine, spell_name):
        session.log.append(f"{spell_name} is not on the Basic, Expert, Heroic, or Legendary spell lists.")
        return False
    item = resolve_fd_spell_scroll_item(engine, spell_name)
    if item is None:
        return False
    from .inventory import can_add_item

    ok, message = can_add_item(member, item)
    if not ok:
        session.log.append(message)
        return False
    member.inventory.append(item)
    if show_rolls:
        session.log.append(f"{member.name} receives {item} (FD p.54).")
    return True
