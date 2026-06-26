from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import ExitState, PartyMemberState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _party_member() -> PartyMemberState:
    return PartyMemberState.model_validate(
        {
            "character_id": "hero-1",
            "name": "Hero",
            "class_id": "warrior",
            "class_name": "Warrior",
            "level": 5,
            "expert_trained": True,
            "max_life": 12,
            "current_life": 12,
            "gold": 200,
            "xp": 0,
            "inventory": ["Hand weapon", "Light armor"],
            "attack_bonus": 0,
            "defense_bonus": 0,
            "save_bonus": 0,
            "marching_order": 1,
        }
    )


def test_forsaken_depths_session_uses_dungeon_catalog() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-1",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    assert session.ruleset == "forsaken_depths"
    assert session.tile_catalog == "forsaken_depths"
    start = session.map_state.tiles[0]
    assert start.tile_key[0] in "123456" and start.tile_key[1] in "123456"
    assert start.tile_catalog == "forsaken_depths"
    assert any("Forsaken Depths start roll" in entry for entry in session.log)


def test_river_walkable_preserves_water_cells() -> None:
    eng = engine()
    repo = eng.rules
    river_def = repo.tiles("forsaken_depths_rivers")["11"]
    rows = eng._normalized_walkable(river_def, river_def.footprint_width, river_def.footprint_height, catalog="forsaken_depths_rivers")
    assert any("2" in row for row in rows)


def test_etr_explore_places_river_tile() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-etr",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    etr_def = eng.rules.tiles("forsaken_depths")["26"]
    origin = TileState(
        id="etr-origin",
        x=0,
        y=0,
        tile_key="26",
        tile_type="room",
        footprint_width=etr_def.footprint_width,
        footprint_height=etr_def.footprint_height,
        walkable=eng._normalized_walkable(etr_def, etr_def.footprint_width, etr_def.footprint_height, catalog="forsaken_depths"),
        cell_shapes=list(etr_def.cell_shapes),
        visible=["1" * etr_def.footprint_width for _ in range(etr_def.footprint_height)],
        title=etr_def.name,
        description="ETR test room",
        content_key="fd_empty",
        tile_catalog="forsaken_depths",
        room_codes=["ETR"],
        exits=[
            ExitState(
                id="etr-north",
                direction="north",
                kind="passage",
                x=2,
                y=0,
                span=1,
            )
        ],
    )
    session.map_state.tiles = [origin]
    session.map_state.current_tile_id = origin.id

    eng.advance(session, "explore", exit_id="etr-north")

    assert session.tile_catalog == "forsaken_depths_rivers"
    assert len(session.map_state.tiles) == 2
    river_tile = next(tile for tile in session.map_state.tiles if tile.id != origin.id)
    assert river_tile.tile_catalog == "forsaken_depths_rivers"
    assert any("underground river" in entry.lower() for entry in session.log)
    assert any("2" in row for row in river_tile.walkable)


def test_setup_includes_forsaken_depths_ruleset_select() -> None:
    index_html = Path("src/app/static/index.html").read_text(encoding="utf-8")
    app_js = Path("src/app/static/app.js").read_text(encoding="utf-8")
    assert 'id="ruleset-select"' in index_html
    assert "forsaken_depths" in index_html
    assert "fd-map-mode" in index_html
    assert "fd-river-type" in index_html
    assert "fd-boat-status" in index_html
    assert "rulesetSelect" in app_js
    assert "fd-travel-mode" in index_html
    assert "fd-citadel" in index_html
    assert "fd-stirs" in index_html
    assert "fdTravelModeDisplay" in app_js
    assert "fdCitadelDisplay" in app_js


def test_map_styles_include_river_water_overlay() -> None:
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")
    assert ".map-square.water" in styles
    assert "env-river" in styles
    assert ".fd-boat-status" in styles


def test_fd_room_content_spawns_vermin(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-spawn",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 5)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 3)
    monkeypatch.setattr("app.engine.random_dungeon.roll_formula", lambda formula: 4)
    content = eng._roll_content(session, "room", hcl=3)
    assert content["key"] == "fd_vermin"
    assert len(content["enemies"]) == 4
    assert content["enemies"][0].name == "Spore Spiders"
    assert content["enemies"][0].category == "vermin"


def test_fd_boss_content_spawns_named_boss(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-boss",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 8)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    content = eng._roll_content(session, "room", hcl=4)
    assert content["key"] == "fd_boss"
    assert len(content["enemies"]) == 1
    assert content["enemies"][0].name == "Deep Hobgoblin Champion"
    assert content["enemies"][0].category == "boss"


def test_fd_river_ambush_spawns_on_tile(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-ambush",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "death"
    tile = TileState(
        id="river-1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River stretch",
        description="Test river stretch",
        tile_catalog="forsaken_depths_rivers",
        enemies=[],
    )
    rolls = iter([1, 3, 1])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls))
    monkeypatch.setattr("app.engine.random_dungeon.roll_formula", lambda formula: 5)
    eng._fd_on_river_stretch_entered(session, tile, show_rolls=True)
    assert any(enemy.name == "River Trolls" for enemy in tile.enemies)
    assert any("River ambush" in entry for entry in session.log)


def test_fd_monster_tables_loaded() -> None:
    eng = engine()
    monsters = eng.rules.monsters()
    assert len(monsters["fd_vermin"]) == 6
    assert len(monsters["fd_minions"]) == 9
    assert len(monsters["fd_boss"]) == 7
    assert len(monsters["fd_weird"]) == 13
    assert len(monsters["fd_horde"]) == 6


def test_fd_river_type_rolled_on_etr_transition(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-river-type",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    etr_def = eng.rules.tiles("forsaken_depths")["26"]
    origin = TileState(
        id="etr-origin",
        x=0,
        y=0,
        tile_key="26",
        tile_type="room",
        footprint_width=etr_def.footprint_width,
        footprint_height=etr_def.footprint_height,
        walkable=eng._normalized_walkable(etr_def, etr_def.footprint_width, etr_def.footprint_height, catalog="forsaken_depths"),
        cell_shapes=list(etr_def.cell_shapes),
        visible=["1" * etr_def.footprint_width for _ in range(etr_def.footprint_height)],
        title=etr_def.name,
        description="ETR test room",
        content_key="fd_empty",
        tile_catalog="forsaken_depths",
        room_codes=["ETR"],
        exits=[
            ExitState(
                id="etr-north",
                direction="north",
                kind="passage",
                x=2,
                y=0,
                span=1,
            )
        ],
    )
    session.map_state.tiles = [origin]
    session.map_state.current_tile_id = origin.id

    eng.advance(session, "explore", exit_id="etr-north")

    assert session.fd_river_type == "tears"
    assert any("River of Tears" in entry for entry in session.log)


def test_fd_river_hazard_damaged_boat(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-hazard",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "death"
    tile = TileState(
        id="river-1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River stretch",
        description="Test river stretch",
        tile_catalog="forsaken_depths_rivers",
    )
    rolls = iter([1, 2])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls))
    eng._fd_on_river_stretch_entered(session, tile, show_rolls=True)
    assert session.fd_boat_status == "damaged"
    assert session.fd_travel_mode == "boat"
    assert any("slightly damaged" in entry.lower() for entry in session.log)


def test_fd_boat_destroyed_sets_foot_travel() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-foot",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_boat_status = "damaged"
    eng._fd_apply_damaged_boat(session)
    assert session.fd_boat_status == "destroyed"
    assert session.fd_travel_mode == "foot"


def test_fd_tears_river_blocks_rest() -> None:
    from app.engine.rest import rest_eligibility

    eng = engine()
    session = eng.create_session(
        "fd-tears",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "tears"
    tile = TileState(
        id="room-1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River room",
        description="test",
        tile_catalog="forsaken_depths_rivers",
        searched=True,
        resolved=True,
        exits=[],
    )
    ok, reason = rest_eligibility(session, tile)
    assert not ok
    assert "Tears" in reason


def test_fd_narrow_corridor_weapon_rules() -> None:
    from app.engine.forsaken_depths_river import fd_narrow_corridor_weapon_adjustment
    from app.engine.weapons import WeaponProfile

    spear = WeaponProfile(item="Spear", kind="melee", slashing=True)
    adj, block = fd_narrow_corridor_weapon_adjustment(spear, missile=False)
    assert block is not None
    dagger = WeaponProfile(item="Dagger", kind="melee", light=True, slashing=True)
    adj, block = fd_narrow_corridor_weapon_adjustment(dagger, missile=False)
    assert block is None
    assert adj == 2


def test_fd_death_river_combat_adjustments() -> None:
    from app.engine.forsaken_depths_river import fd_death_river_combat_adjustments

    eng = engine()
    session = eng.create_session(
        "fd-death",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "death"
    assert fd_death_river_combat_adjustments(session) == (1, -1)


def test_fd_river_hazard_runs_when_traveling_on_foot(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-foot-hazard",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "oblivion"
    session.fd_travel_mode = "foot"
    session.fd_boat_status = "destroyed"
    tile = TileState(
        id="river-foot",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River stretch",
        description="Test",
        tile_catalog="forsaken_depths_rivers",
    )
    rolls = iter([1, 4])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls, 4))
    monkeypatch.setattr("app.engine.forsaken_depths_river.roll_exploding_for_level", lambda *args, **kwargs: (10, [10]))
    eng._fd_on_river_stretch_entered(session, tile, show_rolls=True)
    assert any("Ghosts of the River" in entry or "River hazard" in entry for entry in session.log)


def test_fd_trap_seeded_on_content(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-trap",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 2)
    trap = eng.table_roller.roll_fd_trap(3, show_rolls=True, explain_math=False)
    assert trap.trap_key == "fd_oblivion_trapdoor"
    assert trap.trap_level == 6
    tile = TileState(
        id="trap-room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Trap room",
        description="Trap test",
        content_key="fd_trap",
        objects=["Trap"],
    )
    eng._seed_tile_features(tile, hcl=3, show_rolls=True, session=session)
    assert tile.trap_key == "fd_oblivion_trapdoor"
    assert tile.trap_level == 6


def test_fd_event_content_uses_d10(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-event",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 11)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d10", lambda: 2)
    content = eng._roll_content(session, "room", hcl=3)
    assert content["key"] == "fd_event"
    assert content["special_event_key"] == "winds_of_despair"
    assert "Winds of Despair" in content["description"]


def test_fd_weird_splits_citadel_table(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-weird-citadel",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    rolls = iter([9, 5, 1])
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: next(rolls, 9))
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls, 5))
    content = eng._roll_content(session, "room", hcl=4)
    assert content["key"] == "fd_weird"
    assert content["enemies"][0].name == "Chaos Mothbeast Queen"
    assert "Citadel Weird" in content["description"]


def test_fd_hallucination_applies_on_prepare(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-hallucination",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="hall-room",
        x=0,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Gloomy room",
        description="Hallucination test",
        content_key="fd_hallucination",
    )
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_d6", lambda: 4)
    eng._prepare_tile_features(session, tile, show_rolls=True, explain_math=False)
    assert tile.resolved
    assert any("Horrors from Beyond" in entry for entry in session.log)


def test_fd_citadel_roll_on_etc(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-citadel",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="etc-tile",
        x=0,
        y=0,
        tile_key="23",
        tile_type="corridor",
        title="Citadel entrance",
        description="ETC",
        tile_catalog="forsaken_depths_rivers",
        room_codes=["ETC"],
    )
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_d6", lambda: 3)
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_formula", lambda formula: 4)
    from app.engine.forsaken_depths_river import apply_room_codes_on_stretch_entry

    apply_room_codes_on_stretch_entry(eng, session, tile, show_rolls=True)
    assert session.fd_citadel_type == "citadel_of_traps"
    assert session.fd_citadel_room_count == 14
