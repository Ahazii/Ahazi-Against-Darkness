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
from app.engine.adventure_manifest import validate_adventure_manifest
from app.engine.adventure_session import create_session_from_manifest, repair_imported_map_layout
from app.engine.tag_campaign import (
    apply_latest_tag_route_to_adventure,
    build_tag_adventure_manifest,
    default_campaign,
    resolve_tag_route_action,
)
from app.engine.random_dungeon import OPPOSITE, RandomDungeonEngine
from app.rules.repository import RulesRepository
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


def test_tag_generated_adventure_installs_under_adventure_section(repo: RulesRepository, tmp_path: Path) -> None:
    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    campaign = default_campaign()
    manifest, entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="2")

    path, result = import_adventure_manifest(ROOT, data_dir, manifest, rules_repo=repo, overwrite=True)

    assert result.valid, result.errors
    assert path is not None
    assert manifest["id"] in list_installed_adventure_ids(ROOT, data_dir)
    assert manifest["id"] in campaign.tag_generated_adventure_ids
    assert "Adventure section" in entry.result_text


def test_tag_generated_adventure_opening_log_is_player_facing(
    engine: RandomDungeonEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="2")

    session = create_session_from_manifest(
        engine,
        "tag-clean-opening",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )

    joined = "\n".join(session.log)
    assert "Adventure begins: The Adventures Guild Rumor 2: Medusa in the Hunter's Cabin." in joined
    assert "Objective: Survive or talk down the assassins, then resolve the medusa Xasartha." in joined
    assert "Entered Medusa in the Hunter's Cabin:" in joined or "Entered Lead Trail:" in joined
    assert "Generated from The Adventures Guild campaign downtime" not in joined
    assert "Imported adventure:" not in joined
    assert "Campaign mode:" not in joined
    assert "Fiendish Foes enabled" not in joined
    assert "Adventures Guild guidance" not in joined
    assert "Adventures Guild actions here" not in joined
    assert "Guild Contact:" not in joined
    assert "Guild Contact says" not in joined


def test_tag_route_marker_rewrites_latest_generated_adventure(repo: RulesRepository, tmp_path: Path) -> None:
    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="2")
    path, result = import_adventure_manifest(ROOT, data_dir, manifest, rules_repo=repo, overwrite=True)
    assert result.valid, result.errors
    assert path is not None

    resolve_tag_route_action(campaign, route_action="parley_success", reference="Scene 10 parley")
    rewrite = apply_latest_tag_route_to_adventure(data_dir, campaign)

    updated = json.loads(path.read_text(encoding="utf-8"))
    reference = updated["source"]["parameters"]["tag_reference"]
    complication = next(room for room in updated["rooms"] if room["id"] == "tag-complication")
    assert "complication proxy combat suppressed" in rewrite
    assert reference["route_markers"][-1]["action"] == "parley_success"
    assert not any("encounter" in trigger for trigger in complication["triggers"])


def test_tag_clue_gate_inserts_follow_up_scene(repo: RulesRepository, tmp_path: Path) -> None:
    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="8")
    path, result = import_adventure_manifest(ROOT, data_dir, manifest, rules_repo=repo, overwrite=True)
    assert result.valid, result.errors
    assert path is not None

    resolve_tag_route_action(campaign, route_action="clue_gate_unlocked", reference="Scene 16 cult hideout", clue_cost=0)
    rewrite = apply_latest_tag_route_to_adventure(data_dir, campaign)

    updated = json.loads(path.read_text(encoding="utf-8"))
    validation = validate_adventure_manifest(updated, rules_repo=repo)
    assert validation.valid, validation.errors
    room_ids = {room["id"] for room in updated["rooms"]}
    complication = next(room for room in updated["rooms"] if room["id"] == "tag-complication")
    reference = updated["source"]["parameters"]["tag_reference"]
    assert "follow-up scene inserted" in rewrite
    assert "tag-unlocked-scene" in room_ids
    assert any(exit_def["to"] == "tag-unlocked-scene" and exit_def["status"] == "open" for exit_def in complication["exits"])
    assert reference["latest_route_rewrite"] == "follow-up scene inserted and route opened"
    assert reference["route_rewrites"][-1]["action"] == "clue_gate_unlocked"


def test_tag_skip_scene_removes_optional_side_room(repo: RulesRepository, tmp_path: Path) -> None:
    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    campaign = default_campaign()
    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="2")
    path, result = import_adventure_manifest(ROOT, data_dir, manifest, rules_repo=repo, overwrite=True)
    assert result.valid, result.errors
    assert path is not None

    resolve_tag_route_action(campaign, route_action="skip_scene", reference="Optional clue scene")
    rewrite = apply_latest_tag_route_to_adventure(data_dir, campaign)

    updated = json.loads(path.read_text(encoding="utf-8"))
    validation = validate_adventure_manifest(updated, rules_repo=repo)
    assert validation.valid, validation.errors
    room_ids = {room["id"] for room in updated["rooms"]}
    entry = next(room for room in updated["rooms"] if room["id"] == "tag-lead-entry")
    assert "optional side scene removed" in rewrite
    assert "tag-side-clue" not in room_ids
    assert not any(exit_def["to"] == "tag-side-clue" for exit_def in entry["exits"])


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


def _imported_walkable_overlap(session) -> dict[tuple[int, int], list[str]]:
    ownership: dict[tuple[int, int], list[str]] = {}
    for tile in session.map_state.tiles:
        for y in range(tile.footprint_height):
            for x in range(tile.footprint_width):
                if tile.walkable[y][x] == "0":
                    continue
                ownership.setdefault((tile.x + x, tile.y + y), []).append(tile.title)
    return {key: titles for key, titles in ownership.items() if len(titles) > 1}


def test_imported_crypt_has_no_walkable_overlap(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-crypt-overlap",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    overlaps = _imported_walkable_overlap(session)
    assert not overlaps, overlaps


def test_imported_castle_exits_match_tile_artwork(engine: RandomDungeonEngine) -> None:
    manifest_path = Path(r"\\TOWER\appdata\ahazi-against-darkness\Adventures\castle\adventure.json")
    if not manifest_path.exists():
        pytest.skip("castle adventure not installed locally")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "session-castle-layout",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id="castle",
    )
    tile_defs = engine.rules.tiles()
    for tile in session.map_state.tiles:
        tile_def = tile_defs.get(tile.tile_key)
        if tile_def is None:
            continue
        native = {(exit_def.x, exit_def.y) for exit_def in tile_def.exits}
        for exit_state in tile.exits:
            if exit_state.dungeon_exit and exit_state.destination_tile_id is None:
                continue
            assert (exit_state.x, exit_state.y) in native, (
                f"{tile.title} {exit_state.direction} exit drifted off tile artwork "
                f"at ({exit_state.x},{exit_state.y}); native portals={sorted(native)}"
            )

    tile_by_id = {tile.id: tile for tile in session.map_state.tiles}
    misaligned: list[str] = []
    for tile in session.map_state.tiles:
        for exit_state in tile.exits:
            if not exit_state.destination_tile_id:
                continue
            other = tile_by_id.get(exit_state.destination_tile_id)
            if other is None:
                continue
            reciprocal = OPPOSITE.get(exit_state.direction)
            rec = next(
                (
                    item
                    for item in other.exits
                    if item.direction == reciprocal and item.destination_tile_id == tile.id
                ),
                None,
            )
            if rec is None:
                continue
            _, outside_a = engine._exit_edge(tile, exit_state)
            inside_b, _ = engine._exit_edge(other, rec)
            distance = abs(outside_a[0] - inside_b[0]) + abs(outside_a[1] - inside_b[1])
            if distance > 1:
                misaligned.append(
                    f"{tile.title} {exit_state.direction} -> {other.title} (offset {distance})"
                )
    assert not misaligned, misaligned


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


def test_import_export_roundtrip_preserves_manifest(client: TestClient) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    manifest["id"] = "roundtrip-export"
    manifest["title"] = "Roundtrip Export Test"
    client.post("/api/adventures/import", json={"manifest": manifest, "overwrite": True})
    exported = client.get("/api/adventures/roundtrip-export/export").json()
    assert exported["id"] == "roundtrip-export"
    assert exported["title"] == "Roundtrip Export Test"
    assert len(exported["rooms"]) == len(manifest["rooms"])
    assert exported["entrance_room_id"] == manifest["entrance_room_id"]


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


def test_imported_search_treasure_accepts_singular_item_key(engine: RandomDungeonEngine) -> None:
    manifest = {
        "schema_version": 1,
        "id": "singular-item-treasure",
        "title": "Singular Item Treasure",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
        "entrance_room_id": "vault",
        "exit_room_id": "vault",
        "quest": {
            "key": "slay_all",
            "objective_text": "Test",
            "complete_when": {"type": "room_reached", "room_id": "vault"},
        },
        "rooms": [
            {
                "id": "vault",
                "tile_key": "02",
                "title": "Vault",
                "description": "A small vault.",
                "exits": [],
                "triggers": [
                    {
                        "when": "on_search",
                        "once": True,
                        "treasure": {"item": "Bandage"},
                    }
                ],
            }
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    session = create_session_from_manifest(
        engine,
        "singular-item-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id="singular-item-treasure",
    )
    tile = next(t for t in session.map_state.tiles if t.title == "Vault")
    engine.advance(session, "search", show_rolls=False)
    assert tile.treasure_items == ["Bandage"]
    engine.advance(session, "claim_treasure", show_rolls=False)
    assert tile.treasure_claimed
    assert "Bandage" in session.party[0].inventory


def test_on_treasure_trigger_fires_on_claim(engine: RandomDungeonEngine) -> None:
    manifest = {
        "schema_version": 1,
        "id": "treasure-claim-trigger",
        "title": "Treasure Claim Trigger",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
        "entrance_room_id": "vault",
        "exit_room_id": "vault",
        "quest": {
            "key": "slay_all",
            "objective_text": "Test",
            "complete_when": {"type": "room_reached", "room_id": "vault"},
        },
        "rooms": [
            {
                "id": "vault",
                "tile_key": "02",
                "title": "Vault",
                "description": "A small vault.",
                "exits": [],
                "triggers": [
                    {
                        "when": "on_search",
                        "once": True,
                        "treasure": {"gold": 15, "items": []},
                    },
                    {
                        "when": "on_treasure",
                        "once": True,
                        "log": "A hidden sigil flares as the loot is taken.",
                    },
                ],
            }
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    session = create_session_from_manifest(
        engine,
        "on-treasure-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id="treasure-claim-trigger",
    )
    tile = next(t for t in session.map_state.tiles if t.title == "Vault")
    tile.resolved = True
    tile.enemies.clear()
    engine.advance(session, "search", show_rolls=False)
    assert tile.treasure_gold == 15
    engine.advance(session, "claim_treasure", show_rolls=False)
    assert tile.treasure_claimed
    assert any("hidden sigil flares" in line for line in session.log)


def test_on_feature_trigger_fires_when_special_feature_resolves(engine: RandomDungeonEngine) -> None:
    manifest = {
        "schema_version": 1,
        "id": "feature-trigger",
        "title": "Feature Trigger",
        "synopsis": "Test",
        "source": {"type": "ai", "parameters": {}},
        "recommended_levels": [1, 3],
        "default_environment": "dungeon",
        "entrance_room_id": "entry",
        "exit_room_id": "entry",
        "quest": {
            "key": "slay_all",
            "objective_text": "Test",
            "complete_when": {"type": "room_reached", "room_id": "shrine"},
        },
        "rooms": [
            {
                "id": "entry",
                "tile_key": "02",
                "title": "Entry",
                "description": "Entry hall.",
                "exits": [
                    {
                        "id": "entry-north",
                        "direction": "north",
                        "to": "shrine",
                        "kind": "passage",
                        "status": "open",
                    }
                ],
            },
            {
                "id": "shrine",
                "tile_key": "22",
                "title": "Shrine",
                "description": "A cracked statue looms.",
                "special_event": {"key": "statue"},
                "exits": [
                    {
                        "id": "shrine-south",
                        "direction": "south",
                        "to": "entry",
                        "kind": "passage",
                        "status": "open",
                    }
                ],
                "triggers": [
                    {
                        "when": "on_feature",
                        "once": True,
                        "log": "The statue's eyes dim as the party moves on.",
                    }
                ],
            }
        ],
        "ending": {"victory_text": "Win", "defeat_text": "Lose"},
    }
    session = create_session_from_manifest(
        engine,
        "on-feature-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id="feature-trigger",
    )
    tile = next(t for t in session.map_state.tiles if t.title == "Shrine")
    session.map_state.current_tile_id = tile.id
    assert tile.content_key == "imported:shrine"
    assert tile.special_event_key == "statue"
    engine.advance(
        session,
        "resolve_special_feature",
        special_feature_choice="leave_statue",
        show_rolls=False,
    )
    assert tile.resolved
    assert any("statue's eyes dim" in line for line in session.log)


def test_quest_giver_return_and_resolution(engine: RandomDungeonEngine) -> None:
    from app.engine.adventure_runtime import fire_imported_triggers, update_imported_quest_on_combat_end
    from app.schemas import EnemyState

    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "giver-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    throne = next(tile for tile in session.map_state.tiles if tile.title == "Throne of Bones")
    session.map_state.current_tile_id = throne.id
    wraith = EnemyState(
        id="wraith-1",
        name="Wraith",
        category="boss",
        level=5,
        life=0,
        max_life=10,
        attacks=2,
    )
    update_imported_quest_on_combat_end(session, [wraith], throne)
    assert session.active_quest is not None
    assert session.active_quest.completed
    assert any("Return to Brother Cade" in line for line in session.log)

    chapel = next(tile for tile in session.map_state.tiles if tile.title == "Ruined Chapel")
    session.map_state.current_tile_id = chapel.id
    fire_imported_triggers(engine, session, chapel, "on_enter", show_rolls=False)
    assert any('Brother Cade says: "The Wraith took them all' in line for line in session.log)


def test_imported_boss_quest_accepts_subdued_capture(engine: RandomDungeonEngine) -> None:
    from app.engine.adventure_runtime import update_imported_quest_on_combat_end
    from app.schemas import EnemyState

    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "capture-boss-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    throne = next(tile for tile in session.map_state.tiles if tile.title == "Throne of Bones")
    session.map_state.current_tile_id = throne.id
    wraith = EnemyState(
        id="wraith-1",
        name="Wraith",
        category="boss",
        level=5,
        life=0,
        max_life=10,
        attacks=2,
        subdued=True,
    )
    update_imported_quest_on_combat_end(session, [wraith], throne)

    assert session.active_quest is not None
    assert session.active_quest.completed
    assert session.active_quest.captured_boss_name == "Wraith"
    assert any("subdued alive" in line for line in session.log)


def test_imported_boss_quest_repairs_resolved_boss_room(engine: RandomDungeonEngine) -> None:
    from app.engine.adventure_runtime import imported_trigger_key, update_imported_quest_on_enter

    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "repair-boss-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    throne = next(tile for tile in session.map_state.tiles if tile.title == "Throne of Bones")
    throne.resolved = True
    throne.enemies = []
    session.imported_fired_triggers.append(imported_trigger_key("ossuary-throne", "on_enter", 0))
    chapel = next(tile for tile in session.map_state.tiles if tile.title == "Ruined Chapel")

    update_imported_quest_on_enter(session, chapel)

    assert session.active_quest is not None
    assert session.active_quest.completed
    assert any("objective repaired from the resolved boss room" in line for line in session.log)


def test_imported_adventure_can_exit_without_quest_complete(engine: RandomDungeonEngine) -> None:
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    session = create_session_from_manifest(
        engine,
        "early-exit-session",
        "party-1",
        [_party_member()],
        manifest,
        adventure_id=manifest["id"],
    )
    assert session.active_quest is not None
    assert not session.active_quest.completed
    exit_tile = next(tile for tile in session.map_state.tiles if tile.title == "Stairs to Daylight")
    session.map_state.current_tile_id = exit_tile.id
    engine._complete_dungeon(session)
    assert session.mode == "complete"
    assert session.active_quest is not None
    assert not session.active_quest.completed
    assert any("Quest left incomplete" in line for line in session.summary)
    assert any("leaves without completing the quest" in line for line in session.log)
    assert any("crypt claims another party" in line for line in session.log)


def test_build_adventure_export_zip(repo: RulesRepository, tmp_path: Path) -> None:
    import io
    import zipfile

    from app.engine.adventure_import import build_adventure_export_zip, import_adventure_manifest

    data_dir = tmp_path / "appdata"
    manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    path, result = import_adventure_manifest(ROOT, data_dir, manifest, rules_repo=repo, overwrite=True)
    assert result.valid, result.errors
    assert path is not None
    payload = build_adventure_export_zip(ROOT, data_dir, manifest["id"])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        assert "adventure.json" in names
        assert "adventure.meta.json" in names
        manifest_text = archive.read("adventure.json").decode("utf-8")
        assert "Crypt of Whispers" in manifest_text
