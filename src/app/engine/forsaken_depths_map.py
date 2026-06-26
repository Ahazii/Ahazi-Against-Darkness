"""Forsaken Depths live-session map helpers (catalog selection, ETR transition)."""

from __future__ import annotations

from ..schemas import SessionState, TileState
from .dice import roll_tile_key
from .tile_catalogs import TileCatalogId

RULESET_EE = "ee"
RULESET_FD = "forsaken_depths"


def normalize_ruleset(value: str | None) -> str:
    return RULESET_FD if value == RULESET_FD else RULESET_EE


def is_fd_ruleset(session: SessionState) -> bool:
    return normalize_ruleset(getattr(session, "ruleset", RULESET_EE)) == RULESET_FD


def session_tile_catalog(session: SessionState) -> TileCatalogId:
    catalog = getattr(session, "tile_catalog", RULESET_EE)
    if catalog in ("forsaken_depths", "forsaken_depths_rivers"):
        return catalog  # type: ignore[return-value]
    return "ee"


def starting_tile_catalog(ruleset: str) -> TileCatalogId:
    return "forsaken_depths" if normalize_ruleset(ruleset) == RULESET_FD else "ee"


def roll_fd_dungeon_start_key() -> str:
    return roll_tile_key()


def tile_has_room_code(tile: TileState, code: str) -> bool:
    return code in (tile.room_codes or [])


def should_enter_river_from_etr(
    session: SessionState,
    tile: TileState,
    *,
    generating_new_tile: bool,
) -> bool:
    if not generating_new_tile:
        return False
    if not is_fd_ruleset(session):
        return False
    if session_tile_catalog(session) == "forsaken_depths_rivers":
        return False
    return tile_has_room_code(tile, "ETR")


def map_mode_label(session: SessionState) -> str:
    if not is_fd_ruleset(session):
        return ""
    if session_tile_catalog(session) == "forsaken_depths_rivers":
        return "Underground river"
    return "Forsaken Depths dungeon"


def catalog_label(catalog: str) -> str:
    if catalog == "forsaken_depths_rivers":
        return "Forsaken Depths river"
    if catalog == "forsaken_depths":
        return "Forsaken Depths dungeon"
    return "Expanded Edition"


def fd_river_type_label(river_type: str | None) -> str:
    labels = {
        "oblivion": "River of Oblivion",
        "tears": "River of Tears",
        "death": "River of Death",
        "flame": "River of Flame",
        "conjuration": "River of Conjuration",
        "serpent": "Serpent River",
    }
    return labels.get(river_type or "", "Unknown river")
