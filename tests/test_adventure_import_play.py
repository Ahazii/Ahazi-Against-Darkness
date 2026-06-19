from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.engine.adventure_import import (
    import_adventure_manifest,
    is_user_installed,
    list_installed_adventure_ids,
    remove_installed_adventure,
    seed_bundled_adventures,
)
from app.engine.adventure_session import create_session_from_manifest, repair_imported_map_layout
from app.main import app
from app.rules.repository import RulesRepository
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import PartyMemberState

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules"
EXAMPLE = ROOT / "data" / "adventures" / "examples" / "crypt-of-whispers" / "adventure.json"


@pytest.fixture
def repo() -> RulesRepository:
    return RulesRepository(RULES, RULES / "_override")


@pytest.fixture
def engine(repo: RulesRepository) -> RandomDungeonEngine:
    return RandomDungeonEngine(repo, ROOT / "assets")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _party_member() -> PartyMemberState:
    return PartyMemberState.model_validate({
        "character_id": "hero-1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 2,
        "max_life": 8,
        "current_life": 8,
        "gold": 50,
        "xp": 0,
        "inventory": ["Hand weapon", "Light armor"],
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
    })


def test_import_installs_under_data_adventures(repo: RulesRepository, tmp_path: Path) -> None:
    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    manifest["id"] = "test-crypt-import"
    path, result = import_adventure_manifest(ROOT, data_dir, manifest, rules_repo=repo, overwrite=True)
    assert result.valid, result.errors
    assert path is not None
    assert path == data_dir / "Adventures" / "test-crypt-import" / "adventure.json"
    assert "test-crypt-import" in list_installed_adventure_ids(ROOT, data_dir)


def test_seed_bundled_adventures_copies_shipped_modules(tmp_path: Path) -> None:
    data_dir = tmp_path / "appdata"
    seed_bundled_adventures(ROOT, data_dir)
    assert (data_dir / "Adventures" / "crypt-of-whispers" / "adventure.json").exists()


def test_create_session_from_manifest(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-1",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    assert session.adventure_type == "imported"
    assert len(session.map_state.tiles) == 5
    assert session.active_quest is not None
    assert session.imported_exit_tile_id is not None
    assert session.map_state.current_tile_id in {tile.id for tile in session.map_state.tiles}


def test_imported_crypt_entrance_and_exit_exits(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-1",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    entrance = next(tile for tile in session.map_state.tiles if tile.content_key == "entrance")
    assert any(exit_state.dungeon_exit for exit_state in entrance.exits)
    assert any(exit_state.direction == "north" for exit_state in entrance.exits)
    assert any(exit_state.direction == "east" for exit_state in entrance.exits)
    north = next(exit_state for exit_state in entrance.exits if exit_state.direction == "north")
    east = next(exit_state for exit_state in entrance.exits if exit_state.direction == "east")
    assert north.destination_tile_id != east.destination_tile_id

    exit_tile = next(tile for tile in session.map_state.tiles if tile.title == "Stairs to Daylight")
    leave_exits = [exit_state for exit_state in exit_tile.exits if exit_state.dungeon_exit]
    assert len(leave_exits) == 1
    assert leave_exits[0].destination_tile_id is None


def test_import_json_parse_strips_markdown_fences() -> None:
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")
    assert 'raw.replace(/^```(?:json)?\\s*/i, "")' in app_js
    assert "JSON parse failed" in app_js


def test_imported_layout_aligns_exit_portals(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-1",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    chapel = next(tile for tile in session.map_state.tiles if tile.title == "Ruined Chapel")
    hall = next(tile for tile in session.map_state.tiles if tile.title == "Ossuary Hall")
    north = next(exit_state for exit_state in chapel.exits if exit_state.direction == "north")
    south = next(exit_state for exit_state in hall.exits if exit_state.direction == "south")
    _, chapel_out = engine._exit_edge(chapel, north)
    hall_in, _ = engine._exit_edge(hall, south)
    assert chapel_out == hall_in

    for tile in session.map_state.tiles:
        width, height = engine._rotated_size(tile.footprint_width, tile.footprint_height, tile.rotation)
        rows = tile.walkable
        for exit_state in tile.exits:
            if exit_state.dungeon_exit and exit_state.destination_tile_id is None:
                continue
            assert rows[exit_state.y][exit_state.x] != "0", (
                f"{tile.title} exit {exit_state.direction} at ({exit_state.x},{exit_state.y}) is not walkable"
            )


def test_imported_mausaleum_layout_has_no_walkable_overlap(engine: RandomDungeonEngine) -> None:
    manifest_path = Path(r"\\TOWER\appdata\ahazi-against-darkness\Adventures\mausaleum\adventure.json")
    if not manifest_path.exists():
        pytest.skip("mausaleum adventure not installed locally")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-mausaleum",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    ownership: dict[tuple[int, int], list[str]] = {}
    for tile in session.map_state.tiles:
        for y in range(tile.footprint_height):
            for x in range(tile.footprint_width):
                if tile.walkable[y][x] == "0":
                    continue
                ownership.setdefault((tile.x + x, tile.y + y), []).append(tile.title)
    overlaps = {key: titles for key, titles in ownership.items() if len(titles) > 1}
    assert not overlaps, overlaps
    hall = next(tile for tile in session.map_state.tiles if tile.title == "Gallery of Names")
    hub = next(tile for tile in session.map_state.tiles if tile.title == "Crossroads Crypt")
    assert hub.y < hall.y
    south = next(exit_state for exit_state in hub.exits if exit_state.direction == "south")
    assert hub.walkable[south.y][south.x] != "0"
    assert south.destination_tile_id is not None


def test_repair_imported_map_layout_fixes_overlapping_tiles(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-1",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    for tile in session.map_state.tiles:
        tile.x += 5
    session.imported_manifest = manifest
    assert repair_imported_map_layout(engine, session)
    ownership: dict[tuple[int, int], int] = {}
    for tile in session.map_state.tiles:
        for y in range(tile.footprint_height):
            for x in range(tile.footprint_width):
                if tile.walkable[y][x] == "0":
                    continue
                key = (tile.x + x, tile.y + y)
                ownership[key] = ownership.get(key, 0) + 1
    assert max(ownership.values(), default=0) <= 1


def test_imported_ossuary_hall_has_north_exit(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-1",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    hall = next(tile for tile in session.map_state.tiles if tile.title == "Ossuary Hall")
    north = next((exit_state for exit_state in hall.exits if exit_state.direction == "north"), None)
    assert north is not None
    assert north.destination_tile_id is not None


def test_list_adventures_includes_crypt(client: TestClient) -> None:
    adventures = client.get("/api/adventures").json()
    crypt = next((item for item in adventures if item["id"] == "crypt-of-whispers"), None)
    assert crypt is not None
    assert crypt["playable"] is True


def test_validate_and_import_api(client: TestClient) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    manifest["id"] = "api-import-test"
    validation = client.post("/api/adventures/validate", json={"manifest": manifest}).json()
    assert validation["valid"] is True
    imported = client.post("/api/adventures/import", json={"manifest": manifest, "overwrite": True}).json()
    assert imported["adventure_id"] == "api-import-test"
    adventures = client.get("/api/adventures").json()
    assert any(item["id"] == "api-import-test" and item["playable"] for item in adventures)
    entry = next(item for item in adventures if item["id"] == "api-import-test")
    assert entry["removable"] is True


def test_remove_installed_adventure(repo: RulesRepository, tmp_path: Path) -> None:
    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    manifest["id"] = "remove-me-test"
    path, result = import_adventure_manifest(ROOT, data_dir, manifest, rules_repo=repo, overwrite=True)
    assert result.valid and path is not None
    assert is_user_installed(data_dir, "remove-me-test")

    remove_result = remove_installed_adventure(ROOT, data_dir, "remove-me-test")
    assert remove_result.removed
    assert not is_user_installed(data_dir, "remove-me-test")
    assert "remove-me-test" not in list_installed_adventure_ids(ROOT, data_dir)

    missing = remove_installed_adventure(ROOT, data_dir, "remove-me-test")
    assert not missing.removed
    assert missing.error


def test_remove_adventure_api(client: TestClient) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    manifest["id"] = "api-import-test"
    client.post("/api/adventures/import", json={"manifest": manifest, "overwrite": True})
    response = client.delete("/api/adventures/api-import-test")
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] is True
    assert body["adventure_id"] == "api-import-test"
    adventures = client.get("/api/adventures").json()
    installed = next((item for item in adventures if item["id"] == "api-import-test"), None)
    if installed is not None:
        assert installed["removable"] is False


def test_npc_dialogue_logged_on_entrance(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "npc-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    assert any("Brother Cade" in line for line in session.log)
    assert any("Wraith took them all" in line for line in session.log)


def test_export_adventure_api(client: TestClient) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    client.post("/api/adventures/import", json={"manifest": manifest, "overwrite": True})
    response = client.get("/api/adventures/crypt-of-whispers/export")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "crypt-of-whispers"
    assert len(body["rooms"]) == 5


def test_imported_combat_does_not_roll_procedural_treasure(engine: RandomDungeonEngine) -> None:
    manifest = {
        "schema_version": 1,
        "id": "treasure-test",
        "title": "Treasure Test",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
        "entrance_room_id": "a",
        "exit_room_id": "a",
        "quest": {
            "key": "slay_all",
            "objective_text": "Test",
            "complete_when": {"type": "room_reached", "room_id": "a"},
        },
        "rooms": [
            {
                "id": "a",
                "tile_key": "02",
                "title": "A",
                "description": "A",
                "exits": [],
                "triggers": [
                    {
                        "when": "on_enter",
                        "once": True,
                        "encounter": {"foes": [{"name": "Goblins", "count": 1}]},
                    },
                    {
                        "when": "on_search",
                        "once": True,
                        "treasure": {"gold": 10, "items": ["Lantern"]},
                    },
                ],
            }
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    session = create_session_from_manifest(
        engine,
        "treasure-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id="treasure-test",
    )
    tile = next(t for t in session.map_state.tiles if t.title == "A")
    tile.enemies.clear()
    tile.resolved = True
    engine._award_treasure(session, tile, show_rolls=True)
    assert tile.treasure_gold == 0
    assert not tile.treasure_items

    from app.engine.adventure_runtime import fire_imported_triggers

    tile.searched = False
    fire_imported_triggers(engine, session, tile, "on_search", show_rolls=False)
    assert tile.treasure_gold == 10
    assert tile.treasure_items == ["Lantern"]
    assert tile.treasure_claimed is False


def test_repair_stuck_imported_treasure_after_search(engine: RandomDungeonEngine) -> None:
    from app.engine.adventure_session import repair_stuck_imported_treasure

    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "repair-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    tile = session.map_state.tiles[0]
    tile.treasure_claimed = True
    tile.treasure_gold = 10
    tile.treasure_items = ["Lantern"]
    assert repair_stuck_imported_treasure(session)
    assert tile.treasure_claimed is False


def test_look_action_logs_room(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "look-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    engine.advance(session, "look", show_rolls=False)
    assert any("Ruined Chapel" in line for line in session.log)
    assert any("Collapsed pews" in line for line in session.log)


def test_room_recap_after_combat(engine: RandomDungeonEngine) -> None:
    from app.schemas import EnemyState

    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "recap-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    tile = next(t for t in session.map_state.tiles if t.title == "Ruined Chapel")
    session.map_state.current_tile_id = tile.id
    engine._log_room_recap_after_combat(session, tile)
    assert any("── Ruined Chapel ──" in line for line in session.log)
    assert any("Collapsed pews" in line for line in session.log)
