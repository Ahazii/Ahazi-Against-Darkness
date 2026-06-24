from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.engine.tile_catalogs import DUNGEON_ROOM_CODES, RIVER_ROOM_CODES, ROOM_CODE_DESCRIPTIONS, room_codes_table_rows
from app.engine.tile_validation import validate_tile_definition
from app.main import app
from app.rules.repository import RulesRepository

ROOT = Path(__file__).resolve().parents[1]


client = TestClient(app)


def test_forsaken_depths_tile_catalog_loads_from_packaged_json() -> None:
    repo = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override")
    dungeon = repo.tiles("forsaken_depths")
    rivers = repo.tiles("forsaken_depths_rivers")
    assert len(dungeon) == 36
    assert len(rivers) == 35
    sample = dungeon["11"]
    assert sample.catalog == "forsaken_depths"
    assert sample.image == "forsaken_depths/Forsaken Depths Tile 11.gif"
    river_sample = rivers["11"]
    assert river_sample.catalog == "forsaken_depths_rivers"
    assert river_sample.terrain == "river"


def test_forsaken_depths_tiles_api_and_room_code_reference() -> None:
    response = client.get("/api/rules/tiles", params={"catalog": "forsaken_depths"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 36
    assert payload[0]["catalog"] == "forsaken_depths"

    codes = client.get("/api/rules/tiles/room-codes", params={"catalog": "forsaken_depths"}).json()
    assert [row["code"] for row in codes["codes"]] == list(DUNGEON_ROOM_CODES)
    assert all(row["description"] for row in codes["codes"])

    river_codes = client.get("/api/rules/tiles/room-codes", params={"catalog": "forsaken_depths_rivers"}).json()
    assert [row["code"] for row in river_codes["codes"]] == list(RIVER_ROOM_CODES)


def test_forsaken_depths_room_codes_table_rows() -> None:
    rows = room_codes_table_rows()
    assert len(rows) == len(DUNGEON_ROOM_CODES) + len(RIVER_ROOM_CODES)
    ca_row = next(row for row in rows if row["code"] == "Ca")
    assert "C on river tile art" in str(ca_row["result"])


    repo = RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override")
    rivers = repo.tiles("forsaken_depths_rivers")
    tile = rivers["11"].model_copy(deep=True)
    tile.walkable = ["222222222", "211111112", "222222222"]
    tile.room_codes = ["END"]
    issues = validate_tile_definition(tile, catalog="forsaken_depths_rivers")
    assert not any("invalid walkable" in issue for issue in issues)


def test_room_code_descriptions_match_pdf_topics() -> None:
    assert "Narrow corridor" in ROOM_CODE_DESCRIPTIONS["NC"]
    assert "Citadel" in ROOM_CODE_DESCRIPTIONS["ETC"]
    assert "underground" in ROOM_CODE_DESCRIPTIONS["END"].lower()
