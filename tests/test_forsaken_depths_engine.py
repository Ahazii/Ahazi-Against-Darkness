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
    assert "fd-side-sheet" in index_html
    assert "fd-revelation" in index_html
    assert "fd-oblivion-offer" in index_html
    assert "fdTravelModeDisplay" in app_js
    assert "fdCitadelDisplay" in app_js
    assert "fdSideSheetDisplay" in app_js
    assert "appendFdRevelationActions" in app_js
    assert "enterFdSideSheet" in app_js


def test_map_styles_include_river_water_overlay() -> None:
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")
    assert ".map-square.water" in styles
    assert "env-river" in styles
    assert ".fd-boat-status" in styles
    assert "fd-side-sheet-tile" in styles


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


def test_fd_treasure_roll_10_offers_jackpot_choice(monkeypatch) -> None:
    eng = engine()
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.randint", lambda a, b: 10)
    outcome = eng.table_roller.roll_fd_treasure(show_rolls=True, silk_already_found=False)
    assert outcome.choice_key == "fd_double_or_jackpot"


def test_fd_jackpot_double_roll(monkeypatch) -> None:
    eng = engine()
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.randint", lambda a, b: 4)
    outcome = eng.table_roller.resolve_fd_treasure_choice(
        "fd_double_or_jackpot",
        "double_roll",
        show_rolls=False,
    )
    assert outcome.choice_key is None
    assert outcome.gold > 0


def test_fd_jackpot_quad_sets_wandering_on_claim(monkeypatch) -> None:
    eng = engine()
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.randint", lambda a, b: 4)
    outcome = eng.table_roller.resolve_fd_treasure_choice(
        "fd_double_or_jackpot",
        "quad_roll_wanderers",
        show_rolls=False,
    )
    assert outcome.jackpot_wandering_on_claim
    assert outcome.choice_key is None


def test_fd_jackpot_wandering_on_claim(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-jackpot-claim",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.fd_jackpot_wandering_on_claim = True
    tile.treasure_gold = 50
    tile.treasure_summary = "Jackpot loot"
    session.map_state.current_tile_id = tile.id
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 5)
    monkeypatch.setattr(
        eng,
        "_spawn_wandering_monsters",
        lambda *args, **kwargs: session.log.append("Wandering spawned"),
    )
    eng._claim_treasure(session)
    assert not tile.fd_jackpot_wandering_on_claim
    assert any("Wandering spawned" in line for line in session.log)


def test_fd_treasure_roll_uses_fd_table(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-treasure",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    monkeypatch.setattr("app.engine.dungeon_table_roller.random.randint", lambda a, b: 4)
    outcome = eng.table_roller.roll_fd_treasure(show_rolls=True, silk_already_found=False)
    assert "Gem worth" in outcome.summary
    assert outcome.gold > 0


def test_fd_stirs_spawns_river_encounter(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-stirs",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_stirs_in_darkness_remaining = 2
    tile = TileState(
        id="empty-room",
        x=0,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Empty",
        description="Quiet",
        content_key="searchable",
        enemies=[],
    )
    rolls = iter([2, 1, 1])
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_d6", lambda: next(rolls, 1))
    monkeypatch.setattr("app.engine.random_dungeon.roll_formula", lambda formula: 3)
    from app.engine.forsaken_depths_content import maybe_fd_stirs_on_tile_enter

    maybe_fd_stirs_on_tile_enter(eng, session, tile, hcl=3, show_rolls=True)
    assert session.fd_stirs_in_darkness_remaining == 1
    assert any(enemy.name == "River Trolls" for enemy in tile.enemies)


def test_fd_oblivion_forgets_spell_on_natural_1() -> None:
    from app.engine.forsaken_depths_river import apply_fd_oblivion_spell_forget_from_cast

    eng = engine()
    session = eng.create_session(
        "fd-oblivion",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_river_type = "oblivion"
    member = session.party[0]
    member.spells = ["Fireball", "Blessing"]
    apply_fd_oblivion_spell_forget_from_cast(
        session,
        member,
        "Fireball",
        ["Fireball (connect): Hero rolls 1 + 5 = 6 vs L3."],
        show_rolls=True,
    )
    assert "Fireball" not in member.spells
    assert "Fireball" in session.fd_forgotten_spells[member.character_id]
    assert any("River of Oblivion" in entry for entry in session.log)


def test_fd_wandering_table_roll(monkeypatch) -> None:
    eng = engine()
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 5)
    outcome = eng.table_roller.roll_fd_wandering_monsters()
    assert outcome.enemy_category == "weird"
    assert outcome.roll == 5


def test_fd_boat_blocks_water_exit_on_foot() -> None:
    from app.engine.forsaken_depths_river import fd_validate_river_exit_travel

    eng = engine()
    session = eng.create_session(
        "fd-boat-foot",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_travel_mode = "foot"
    tile = TileState(
        id="river-stretch",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River stretch",
        description="Water channel north",
        tile_catalog="forsaken_depths_rivers",
        footprint_width=3,
        footprint_height=3,
        walkable=["022", "121", "121"],
        exits=[ExitState(direction="north", kind="passage", x=1, y=0, span=1, offset=1)],
    )
    allowed = fd_validate_river_exit_travel(eng, session, tile, tile.exits[0], show_rolls=True)
    assert allowed is False
    assert any("on foot" in line.lower() for line in session.log)


def test_fd_boat_allows_water_exit_and_disembarks_on_bank() -> None:
    from app.engine.forsaken_depths_river import fd_exit_travel_kind, fd_validate_river_exit_travel

    eng = engine()
    session = eng.create_session(
        "fd-boat-move",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_travel_mode = "boat"
    tile = TileState(
        id="river-stretch",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River stretch",
        description="Channel and bank",
        tile_catalog="forsaken_depths_rivers",
        footprint_width=3,
        footprint_height=3,
        walkable=["022", "121", "121"],
        exits=[
            ExitState(direction="north", kind="passage", x=1, y=0, span=1, offset=1),
            ExitState(direction="east", kind="passage", x=2, y=1, span=1, offset=2),
        ],
    )
    water_exit, bank_exit = tile.exits
    assert fd_exit_travel_kind(eng, tile, water_exit) == "water"
    assert fd_exit_travel_kind(eng, tile, bank_exit) == "bank"
    assert fd_validate_river_exit_travel(eng, session, tile, water_exit, show_rolls=True) is True
    assert session.fd_travel_mode == "boat"
    assert fd_validate_river_exit_travel(eng, session, tile, bank_exit, show_rolls=True) is True
    assert session.fd_travel_mode == "foot"
    assert any("disembarks" in line.lower() for line in session.log)


def test_fd_stirs_only_counts_tile_once(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-stirs-once",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_stirs_in_darkness_remaining = 2
    tile = TileState(
        id="empty-room",
        x=0,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Empty",
        description="Quiet",
        content_key="searchable",
        enemies=[],
    )
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_d6", lambda: 4)
    from app.engine.forsaken_depths_content import maybe_fd_stirs_on_tile_enter

    maybe_fd_stirs_on_tile_enter(eng, session, tile, hcl=3, show_rolls=True)
    maybe_fd_stirs_on_tile_enter(eng, session, tile, hcl=3, show_rolls=True)
    assert session.fd_stirs_in_darkness_remaining == 1
    assert tile.id in session.fd_stirs_processed_tile_ids


def test_fd_treasure_choice_gold_or_masterwork() -> None:
    eng = engine()
    outcome = eng.table_roller.resolve_fd_treasure_choice(
        "fd_gold_or_masterwork",
        "gold",
        staged_gold=120,
    )
    assert outcome.gold == 120
    outcome = eng.table_roller.resolve_fd_treasure_choice(
        "fd_gold_or_masterwork",
        "masterwork",
        staged_gold=120,
    )
    assert "Masterwork weapon" in outcome.items[0]


def test_fd_treasure_choice_clues_grants_two() -> None:
    eng = engine()
    outcome = eng.table_roller.resolve_fd_treasure_choice("fd_clues_or_magic", "clues")
    assert outcome.clues_granted == 2


def test_fd_oblivion_redeem_madness_once() -> None:
    from app.engine.forsaken_depths_river import redeem_fd_oblivion_madness
    from app.engine.madness import apply_madness_gain

    eng = engine()
    session = eng.create_session(
        "fd-redemption",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_river_type = "oblivion"
    session.fd_oblivion_madness_redemption_pending = True
    member = session.party[0]
    apply_madness_gain(session, member, source="test", show_rolls=False)
    assert redeem_fd_oblivion_madness(session, member, show_rolls=True)
    assert session.fd_oblivion_madness_redemption_used
    assert not session.fd_oblivion_madness_redemption_pending
    assert not redeem_fd_oblivion_madness(session, member, show_rolls=False)


def test_fd_oblivion_puzzle_natural_one_forgets_spell(monkeypatch) -> None:
    from app.engine.forsaken_depths_river import apply_fd_oblivion_forget_on_natural_one

    eng = engine()
    session = eng.create_session(
        "fd-puzzle",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_river_type = "oblivion"
    member = session.party[0]
    member.spells = ["Blessing", "Fireball"]
    apply_fd_oblivion_forget_on_natural_one(
        session,
        member,
        natural=1,
        show_rolls=True,
        source="puzzle Save",
    )
    assert len(member.spells) == 1
    assert len(session.fd_forgotten_spells[member.character_id]) == 1


def _fd_ru_entry_tile(eng: RandomDungeonEngine) -> TileState:
    return TileState(
        id="ru-origin",
        x=0,
        y=0,
        tile_key="24",
        tile_type="room",
        footprint_width=5,
        footprint_height=5,
        title="River ruins",
        description="Ru test room",
        content_key="fd_empty",
        tile_catalog="forsaken_depths_rivers",
        room_codes=["Ru"],
        exits=[
            ExitState(
                id="ru-east",
                direction="east",
                kind="passage",
                x=4,
                y=2,
                span=1,
            )
        ],
    )


def test_fd_side_sheet_entry_available() -> None:
    from app.engine.forsaken_depths_side_sheet import fd_side_sheet_entry_available

    eng = engine()
    session = eng.create_session(
        "fd-side-entry",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    ru_tile = _fd_ru_entry_tile(eng)
    available, kind = fd_side_sheet_entry_available(session, ru_tile)
    assert available
    assert kind == "ruins"
    ru_tile.fd_side_sheet_entry_used = True
    available, kind = fd_side_sheet_entry_available(session, ru_tile)
    assert not available


def test_fd_enter_ruins_side_sheet(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-side-enter",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    origin = _fd_ru_entry_tile(eng)
    session.map_state.tiles = [origin]
    session.map_state.current_tile_id = origin.id
    session.mode = "exploration"
    monkeypatch.setattr("app.engine.forsaken_depths_side_sheet.roll_d6", lambda: 4)

    eng.advance(session, "enter_fd_side_sheet")

    assert session.fd_side_sheet_active
    assert session.fd_side_sheet_kind == "ruins"
    assert session.fd_side_sheet_rooms_total == 6
    assert origin.fd_side_sheet_entry_used
    side_tiles = [tile for tile in session.map_state.tiles if tile.fd_side_sheet]
    assert len(side_tiles) == 1
    assert session.map_state.current_tile_id == side_tiles[0].id


def test_fd_exit_side_sheet_returns_to_origin() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-side-exit",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    origin = _fd_ru_entry_tile(eng)
    side = TileState(
        id="ru-side-1",
        x=5,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Ruins room",
        description="Side sheet room",
        content_key="fd_side_sheet",
        tile_catalog="forsaken_depths",
        fd_side_sheet=True,
    )
    session.map_state.tiles = [origin, side]
    session.map_state.current_tile_id = side.id
    session.mode = "exploration"
    session.fd_side_sheet_active = True
    session.fd_side_sheet_kind = "ruins"
    session.fd_side_sheet_origin_tile_id = origin.id
    session.fd_side_sheet_rooms_total = 3
    session.fd_side_sheet_rooms_entered = 1

    eng.advance(session, "exit_fd_side_sheet")

    assert not session.fd_side_sheet_active
    assert session.map_state.current_tile_id == origin.id


def test_fd_side_sheet_room_budget_blocks_explore() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-side-budget",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    side = TileState(
        id="side-full",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        footprint_width=5,
        footprint_height=5,
        walkable=["11111", "11111", "11111", "11111", "11111"],
        visible=["11111", "11111", "11111", "11111", "11111"],
        title="Last ruins room",
        description="Side sheet room",
        content_key="fd_side_sheet",
        tile_catalog="forsaken_depths",
        fd_side_sheet=True,
        exits=[
            ExitState(
                id="side-north",
                direction="north",
                kind="passage",
                x=2,
                y=0,
                span=1,
            )
        ],
    )
    session.map_state.tiles = [side]
    session.map_state.current_tile_id = side.id
    session.mode = "exploration"
    session.fd_side_sheet_active = True
    session.fd_side_sheet_kind = "ruins"
    session.fd_side_sheet_rooms_total = 2
    session.fd_side_sheet_rooms_entered = 2

    eng.advance(session, "explore", exit_id="side-north")

    assert len(session.map_state.tiles) == 1
    assert any("room budget is exhausted" in entry.lower() for entry in session.log)


def test_fd_spend_hallucination_revelation() -> None:
    from app.engine.forsaken_depths_content import spend_fd_hallucination_revelation

    eng = engine()
    session = eng.create_session(
        "fd-revelation",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_hallucination_revelation_available = True
    assert spend_fd_hallucination_revelation(session, "auto_save", show_rolls=True)
    assert not session.fd_hallucination_revelation_available
    assert any("Revelation spent" in entry for entry in session.log)
