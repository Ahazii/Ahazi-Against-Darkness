"""Forsaken Depths magic item tables (FD p.49–50)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState
from .dice import roll_d10, roll_d3, roll_d6, roll_formula

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine


def fd_party_tier(hcl: int) -> int:
    return max(1, (hcl + 2) // 3)


def fd_magic_item_table_key(hcl: int) -> str:
    """Heroic table for lower tiers; Legendary from Tier 4+ (FD p.49–50)."""
    return "fd_legendary_magic_item_table" if fd_party_tier(hcl) >= 4 else "fd_heroic_magic_item_table"


def roll_fd_magic_item(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    hcl: int | None = None,
    show_rolls: bool = True,
) -> tuple[str, list[str]]:
    if hcl is None:
        hcl = engine._highest_character_level(session.party)
    table_key = fd_magic_item_table_key(hcl)
    roll = roll_d10() if table_key == "fd_legendary_magic_item_table" else roll_d6()
    row = engine.table_roller.lookup(table_key, roll)
    if row is None:
        return "Magic item", []
    name = str(row.get("name") or row.get("result") or "Magic item")
    item = _materialize_fd_magic_item(row, hcl=hcl)
    log: list[str] = []
    if show_rolls:
        log.append(f"FD magic item roll: {table_key} = {roll} → {name} (FD p.49–50).")
    return item, log


def _materialize_fd_magic_item(row: dict, *, hcl: int) -> str:
    key = row.get("key", "")
    name = str(row.get("name") or row.get("result") or "Magic item")
    if key == "humming_crystals":
        count = roll_d3()
        return f"{count} Humming Crystal{'s' if count != 1 else ''}"
    if key == "legendary_weapon":
        weapon_roll = roll_d6()
        kinds = {
            1: "Legendary bow or sling",
            2: "Legendary bow or sling",
            3: "Legendary light weapon",
            4: "Legendary hand weapon",
            5: "Legendary hand weapon",
            6: "Legendary two-handed weapon",
        }
        return kinds.get(weapon_roll, name)
    if key == "legendary_armor":
        kind = "Legendary light armor" if roll_d6() <= 4 else "Legendary heavy armor"
        return kind
    return name


def grant_fd_magic_item_to_party(
    engine: RandomDungeonEngine,
    session: SessionState,
    member: PartyMemberState,
    item: str,
    *,
    show_rolls: bool = True,
) -> None:
    engine._grant_treasure_item(session, member, item, show_rolls=show_rolls)
