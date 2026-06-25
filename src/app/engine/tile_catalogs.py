from __future__ import annotations

from typing import Literal

TileCatalogId = Literal["ee", "forsaken_depths", "forsaken_depths_rivers"]

EE_STARTING_KEYS = {f"0{index}" for index in range(1, 7)}
EE_GENERATED_KEYS = {f"{tens}{ones}" for tens in range(1, 7) for ones in range(1, 7)}
EE_TILE_KEYS = EE_STARTING_KEYS | EE_GENERATED_KEYS

FD_TILE_KEYS = {f"{tens}{ones}" for tens in range(1, 7) for ones in range(1, 7)}

TILE_CATALOG_FILES: dict[TileCatalogId, str] = {
    "ee": "tiles.json",
    "forsaken_depths": "forsaken_depths_tiles.json",
    "forsaken_depths_rivers": "forsaken_depths_rivers_tiles.json",
}

TILE_CATALOG_KEYS: dict[TileCatalogId, frozenset[str]] = {
    "ee": frozenset(EE_TILE_KEYS),
    "forsaken_depths": frozenset(FD_TILE_KEYS),
    "forsaken_depths_rivers": frozenset(FD_TILE_KEYS),
}

# Forsaken Depths p.32 (dungeon tiles) and p.37–40 (river stretches).
ROOM_CODE_DESCRIPTIONS: dict[str, str] = {
    "NC": (
        "Narrow corridor (FD p.32): party travels single file; two-handed weapons attack at -1 "
        "and ignore their +1 two-handed bonus; spears and pikes may not be used; light slashing "
        "weapons attack at +1 and ignore the light-weapon -1; ranged weapons only from marching "
        "order position 1 (or position 4 on a rear attack)."
    ),
    "ETC": (
        "Entrance to Citadel (FD p.32; River Hazard p.30): passage to a separate Citadel dungeon "
        "on another sheet; Citadels use their own content tables and are suggested for Legendary "
        "Tier characters. ETC may appear on dungeon or river tiles."
    ),
    "ETR": (
        "Exit To River (FD p.32–28): exit to an underground river on a separate river map; "
        "4-in-6 chance of finding a boat; boatman services if no violent encounter in the room."
    ),
    "END": (
        "River end (FD p.37): the river can no longer be navigated and goes underground; "
        "a later river stretch may be found but its type is rolled again."
    ),
    "Ru": (
        "Ruin (FD p.39–40): ruined building along the river; optional d6+2 room side dungeon "
        "using Forsaken Ruins content on a separate sheet."
    ),
    "Ca": (
        "Cairn (FD p.40–41): Precursor stone mound harnessing river magic; printed as the letter "
        "C on river tile art — mark room code Ca in the editor. Spellcasters may tap cairn energy "
        "per the rulebook."
    ),
    "B": (
        "Bridge (FD p.40): boat moves near a bridge; 2-in-6 chance a River Encounter Table "
        "foe guards the bridge; party may disembark and continue on foot."
    ),
}

DUNGEON_ROOM_CODES = ("NC", "ETC", "ETR")
RIVER_ROOM_CODES = ("ETC", "END", "Ru", "Ca", "B")

WALKABLE_BLOCKED = "0"
WALKABLE_FLOOR = "1"
WALKABLE_WATER = "2"
VALID_WALKABLE_CODES = frozenset({WALKABLE_BLOCKED, WALKABLE_FLOOR, WALKABLE_WATER})


def normalize_catalog_id(catalog: str | None) -> TileCatalogId:
    normalized = (catalog or "ee").strip().lower()
    if normalized not in TILE_CATALOG_FILES:
        raise ValueError(f"Unknown tile catalog {catalog!r}.")
    return normalized  # type: ignore[return-value]


def room_codes_for_catalog(catalog: TileCatalogId) -> tuple[str, ...]:
    if catalog == "forsaken_depths_rivers":
        return RIVER_ROOM_CODES
    if catalog == "forsaken_depths":
        return DUNGEON_ROOM_CODES
    return ()


def room_codes_table_rows() -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for code in DUNGEON_ROOM_CODES:
        rows.append(
            {
                "catalog": "forsaken_depths",
                "code": code,
                "result": ROOM_CODE_DESCRIPTIONS[code],
                "source_page": 32,
            }
        )
    river_pages = {"ETC": 30, "END": 37, "Ru": 39, "Ca": 40, "B": 40}
    for code in RIVER_ROOM_CODES:
        rows.append(
            {
                "catalog": "forsaken_depths_rivers",
                "code": code,
                "result": ROOM_CODE_DESCRIPTIONS[code],
                "source_page": river_pages[code],
            }
        )
    return rows
