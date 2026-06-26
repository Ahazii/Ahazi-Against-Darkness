from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, ExitState, PartyMemberState, TileState


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
    assert "fd-magic-mr" in index_html
    assert "fdTravelModeDisplay" in app_js
    assert "fdCitadelDisplay" in app_js
    assert "fdSideSheetDisplay" in app_js
    assert "fdCitadelModifierTooltip" in app_js
    assert "appendFdCitadelSideSheetActions" in app_js
    assert "appendCourtshipDemesneActions" in app_js
    assert "courtship_roll_encounter" in app_js
    assert "resolve_fd_cyclopean_idol" in app_js
    assert "appendFdQuestActions" in app_js
    assert "fd_quest_spend_clue_enemy" in app_js
    assert "recover_fd_lost_page" in app_js
    assert "appendFdRevelationActions" in app_js
    assert "enterFdSideSheet" in app_js
    assert "fdPrisonersEscape" in app_js


def test_map_styles_include_river_water_overlay() -> None:
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")
    assert ".map-square.water" in styles
    assert "env-river" in styles
    assert ".fd-boat-status" in styles
    assert "fd-side-sheet-tile" in styles
    assert ".fd-magic-mr" in styles


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
    assert len(monsters["fd_weird"]) == 14
    assert len(monsters["courtship_demons"]) >= 20
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
    from app.engine.forsaken_depths_revelation import spend_fd_hallucination_revelation

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
    assert session.fd_revelation_auto_save
    assert any("Revelation spent" in entry for entry in session.log)


def test_fd_event_flood_applies_saves(monkeypatch) -> None:
    from app.engine.forsaken_depths_events import apply_fd_event_flood

    eng = engine()
    session = eng.create_session(
        "fd-flood",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    monkeypatch.setattr(
        "app.engine.forsaken_depths_events._fd_save_vs_level",
        lambda *args, **kwargs: (False, ["save log"]),
    )
    apply_fd_event_flood(eng, session, hcl=3, show_rolls=True)
    assert session.fd_flood_bow_penalty_rooms == 12
    assert any("Flood" in entry for entry in session.log)


def test_fd_hidden_treasure_claim(monkeypatch) -> None:
    from app.engine.forsaken_depths_events import claim_fd_hidden_treasure_chamber

    eng = engine()
    session = eng.create_session(
        "fd-chamber",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.fd_hidden_treasure_chamber = True
    tile.resolved = True
    session.map_state.current_tile_id = tile.id
    monkeypatch.setattr(
        "app.engine.forsaken_depths_events.roll_fd_magic_item",
        lambda *args, **kwargs: ("Lucky Boat", ["item roll"]),
    )
    monkeypatch.setattr(
        "app.engine.forsaken_depths_events.grant_fd_magic_item_to_party",
        lambda *args, **kwargs: None,
    )
    assert claim_fd_hidden_treasure_chamber(eng, session, show_rolls=True)
    assert tile.fd_hidden_treasure_claimed


def test_fd_crowded_citadel_doubles_minions(monkeypatch) -> None:
    from app.engine.forsaken_depths_citadel import apply_fd_citadel_room

    eng = engine()
    session = eng.create_session(
        "fd-crowded",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_side_sheet_active = True
    session.fd_side_sheet_kind = "citadel"
    session.fd_citadel_type = "crowded_citadel"
    session.fd_side_sheet_rooms_total = 4
    session.fd_side_sheet_rooms_entered = 1
    tile = TileState(
        id="citadel-room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Citadel room",
        description="Side sheet",
        content_key="fd_side_sheet",
        tile_catalog="forsaken_depths",
        fd_side_sheet=True,
    )
    monkeypatch.setattr("app.engine.forsaken_depths_citadel.roll_d6", lambda: 6)
    monkeypatch.setattr(
        eng,
        "_roll_fd_content",
        lambda session, tile_type, hcl: {
            "key": "fd_minions",
            "description": "Servitors",
            "objects": ["Servitors"],
            "enemies": [
                EnemyState(
                    id="m1",
                    name="Servitor",
                    category="minions",
                    level=3,
                    life=3,
                    max_life=3,
                )
            ],
        },
    )
    apply_fd_citadel_room(eng, session, tile, hcl=5, show_rolls=False)
    assert len(tile.enemies) == 2


def test_fd_prisoners_escape_spends_clues() -> None:
    from app.engine.forsaken_depths_citadel import escape_fd_prisoners_citadel

    eng = engine()
    session = eng.create_session(
        "fd-prisoners",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    origin = _fd_ru_entry_tile(eng)
    origin.room_codes = ["ETC"]
    session.map_state.tiles = [origin]
    session.map_state.current_tile_id = origin.id
    session.fd_side_sheet_active = True
    session.fd_side_sheet_kind = "citadel"
    session.fd_citadel_type = "prisoners_citadel"
    session.fd_side_sheet_origin_tile_id = origin.id
    session.clues_found = 5
    session.party[0].clues = 5
    assert escape_fd_prisoners_citadel(eng, session, show_rolls=False)
    assert session.clues_found == 1
    assert not session.fd_side_sheet_active


def test_fd_citadel_of_dead_blocks_rest_healing() -> None:
    from app.engine.forsaken_depths_citadel import fd_citadel_of_dead_blocks_healing

    eng = engine()
    session = eng.create_session(
        "fd-dead",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_side_sheet_active = True
    session.fd_side_sheet_kind = "citadel"
    session.fd_citadel_type = "citadel_of_dead"
    tile = TileState(
        id="dead-room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Dead citadel room",
        description="Side sheet",
        fd_side_sheet=True,
    )
    assert fd_citadel_of_dead_blocks_healing(session, tile, source="rest")
    assert fd_citadel_of_dead_blocks_healing(session, tile, source="potion")
    assert fd_citadel_of_dead_blocks_healing(session, tile, source="bandage") is None


def test_fd_magic_citadel_mr_suspended() -> None:
    from app.engine.combat_modifiers import enemy_magic_resist_bonus

    eng = engine()
    session = eng.create_session(
        "fd-magic",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_magic_citadel_mr_active = True
    enemy = EnemyState(
        id="e1",
        name="Dragon",
        category="boss",
        level=5,
        life=10,
        max_life=10,
        tags=["dragon", "magic_resist"],
    )
    assert enemy_magic_resist_bonus(enemy, session=session) == 0


def test_fd_ruins_secret_passage_offer(monkeypatch) -> None:
    from app.engine.forsaken_depths_content import apply_ruins_room_content
    from app.engine.forsaken_depths_secret_passage import offer_fd_ruins_secret_passage

    eng = engine()
    session = eng.create_session(
        "fd-sp-offer",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="ruins-sp",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Ruins passage",
        description="Secret passage room",
        content_key="ruins_secret_passage",
    )
    offer_fd_ruins_secret_passage(session, tile, show_rolls=False)
    assert session.fd_secret_passage_tile_id == tile.id
    assert tile.fd_secret_passage_room
    assert "Secret Passage" in tile.objects
    assert not session.fd_secret_passage_unlocked

    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_2d6", lambda: 12)
    apply_ruins_room_content(eng, session, tile, hcl=5, show_rolls=False)
    assert session.fd_secret_passage_tile_id == tile.id


def test_fd_secret_passage_unlock_with_clues() -> None:
    from app.engine.forsaken_depths_secret_passage import offer_fd_ruins_secret_passage

    eng = engine()
    session = eng.create_session(
        "fd-sp-clues",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(id="sp-tile", x=0, y=0, tile_key="11", tile_type="room", title="SP", description="SP")
    session.map_state.tiles = [tile]
    session.map_state.current_tile_id = tile.id
    session.mode = "exploration"
    offer_fd_ruins_secret_passage(session, tile, show_rolls=False)
    session.clues_found = 3

    eng.advance(session, "fd_secret_passage_unlock_clues")

    assert session.fd_secret_passage_unlocked
    assert session.clues_found == 0
    assert any("opens" in entry.lower() for entry in session.log)


def test_fd_secret_passage_trap_progress_unlocks() -> None:
    from app.engine.forsaken_depths_secret_passage import (
        note_fd_secret_passage_trap_cleared,
        offer_fd_ruins_secret_passage,
    )

    eng = engine()
    session = eng.create_session(
        "fd-sp-traps",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="trap-tile",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Trap",
        description="Trap",
    )
    offer_fd_ruins_secret_passage(session, tile, show_rolls=False)
    hcl = eng._highest_character_level(session.party)

    note_fd_secret_passage_trap_cleared(session, trap_level=hcl + 3, hcl=hcl, show_rolls=False)
    assert session.fd_secret_passage_traps_cleared == 1
    assert not session.fd_secret_passage_unlocked

    note_fd_secret_passage_trap_cleared(session, trap_level=hcl + 3, hcl=hcl, show_rolls=False)
    note_fd_secret_passage_trap_cleared(session, trap_level=hcl + 3, hcl=hcl, show_rolls=False)
    assert session.fd_secret_passage_traps_cleared == 3
    assert session.fd_secret_passage_unlocked


def test_fd_secret_passage_low_trap_does_not_count() -> None:
    from app.engine.forsaken_depths_secret_passage import (
        note_fd_secret_passage_trap_cleared,
        offer_fd_ruins_secret_passage,
    )

    eng = engine()
    session = eng.create_session(
        "fd-sp-low-trap",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="low-trap",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Trap",
        description="Trap",
    )
    offer_fd_ruins_secret_passage(session, tile, show_rolls=False)
    hcl = eng._highest_character_level(session.party)
    note_fd_secret_passage_trap_cleared(session, trap_level=hcl + 2, hcl=hcl, show_rolls=False)
    assert session.fd_secret_passage_traps_cleared == 0


def test_fd_secret_passage_weird_defeats_unlock() -> None:
    from app.engine.forsaken_depths_secret_passage import (
        note_fd_secret_passage_weird_defeated,
        offer_fd_ruins_secret_passage,
    )

    eng = engine()
    session = eng.create_session(
        "fd-sp-weird",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(id="weird-tile", x=0, y=0, tile_key="11", tile_type="room", title="Weird", description="Weird")
    offer_fd_ruins_secret_passage(session, tile, show_rolls=False)
    weird = EnemyState(
        id="w1",
        name="Weird Thing",
        category="weird",
        level=5,
        life=0,
        max_life=10,
    )
    note_fd_secret_passage_weird_defeated(session, weird, show_rolls=False)
    assert session.fd_secret_passage_weird_defeated == 1
    note_fd_secret_passage_weird_defeated(session, weird, show_rolls=False)
    assert session.fd_secret_passage_unlocked


def test_fd_secret_passage_abyss_destination(monkeypatch) -> None:
    from app.engine.forsaken_depths_secret_passage import offer_fd_ruins_secret_passage

    eng = engine()
    session = eng.create_session(
        "fd-sp-abyss",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="abyss-origin",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Passage",
        description="Passage",
        footprint_width=5,
        footprint_height=5,
        walkable=["11111"] * 5,
        visible=["11111"] * 5,
    )
    session.map_state.tiles = [tile]
    session.map_state.current_tile_id = tile.id
    session.mode = "exploration"
    offer_fd_ruins_secret_passage(session, tile, show_rolls=False)
    session.fd_secret_passage_unlocked = True
    monkeypatch.setattr(eng, "_open_secret_passage_destination", lambda *args, **kwargs: True)

    eng.advance(
        session,
        "choose_fd_secret_passage_destination",
        fd_secret_passage_destination="abyss",
    )

    assert session.fd_secret_passage_tile_id is None
    assert not session.fd_secret_passage_unlocked
    assert any("Abyss" in entry for entry in session.log)


def test_fd_secret_passage_citadel_sets_entry(monkeypatch) -> None:
    from app.engine.forsaken_depths_secret_passage import offer_fd_ruins_secret_passage

    eng = engine()
    session = eng.create_session(
        "fd-sp-citadel",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(id="citadel-sp", x=0, y=0, tile_key="11", tile_type="room", title="Passage", description="Passage")
    session.map_state.tiles = [tile]
    session.map_state.current_tile_id = tile.id
    session.mode = "exploration"
    offer_fd_ruins_secret_passage(session, tile, show_rolls=False)
    session.fd_secret_passage_unlocked = True
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_fd_citadel", lambda *args, **kwargs: {"key": "ghost_citadel"})

    eng.advance(
        session,
        "choose_fd_secret_passage_destination",
        fd_secret_passage_destination="citadel",
    )

    assert session.fd_citadel_entry_tile_id == tile.id
    assert session.fd_secret_passage_tile_id is None


def test_fd_portal_demesne_enters_courtship(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-demesne",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="portal-tile",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Portal room",
        description="Portal",
        fd_portal_available=True,
    )
    session.map_state.tiles = [tile]
    session.map_state.current_tile_id = tile.id
    session.fd_portal_tile_id = tile.id
    session.mode = "exploration"

    eng.advance(session, "choose_fd_event_portal", fd_portal_destination="demesne")

    assert session.courtship_demesne_active
    assert session.courtship_demesne_region == "seaside"
    assert session.courtship_return_tile_id == tile.id
    assert not tile.fd_portal_available


def test_cyclopean_idol_walking_idol_spawns(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-idol",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="idol-room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Idol chamber",
        description="Chamber",
        fd_cyclopean_idol_available=True,
    )
    session.map_state.tiles = [tile]
    session.map_state.current_tile_id = tile.id
    session.mode = "exploration"
    monkeypatch.setattr("app.engine.forsaken_depths_cyclopean_idol.roll_d6", lambda: 2)

    eng.advance(session, "resolve_fd_cyclopean_idol")

    assert tile.fd_cyclopean_idol_resolved
    assert any(enemy.name == "Walking Idol" for enemy in tile.enemies)
    assert any("Walking Idol" in entry for entry in session.log)


def test_courtship_encounter_clues(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-courtship",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.courtship_demesne_active = True
    session.courtship_demesne_region = "woods"
    session.courtship_return_tile_id = "origin"
    session.mode = "exploration"
    monkeypatch.setattr("app.engine.courtship_demesne.roll_2d6", lambda: 4)

    eng.advance(session, "courtship_roll_encounter")

    assert any("Grisly Findings" in entry or "clue" in entry.lower() for entry in session.log)


def _fd_quest_session(quest_key: str, **quest_kwargs):
    eng = engine()
    session = eng.create_session(
        f"fd-quest-{quest_key}",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    from app.schemas import ActiveQuestState

    quest = ActiveQuestState(tile_id=tile.id, key=quest_key, description="test quest")
    for name, value in quest_kwargs.items():
        setattr(quest, name, value)
    session.active_quest = quest
    session.map_state.current_tile_id = tile.id
    session.mode = "exploration"
    return eng, session, tile, quest


def test_fd_quest_enemy_spawns_after_five_areas(monkeypatch) -> None:
    eng, session, tile, quest = _fd_quest_session("fd_defeat_enemy", fd_quest_areas_until_spawn=1)
    monkeypatch.setattr("app.engine.forsaken_depths_quest.roll_d6", lambda: 1)
    from app.engine.forsaken_depths_quest import tick_fd_quest_on_area_enter

    tick_fd_quest_on_area_enter(eng, session, tile, show_rolls=False)
    assert quest.fd_quest_enemy_spawned
    assert any(e.tags for e in tile.enemies if "fd_quest_enemy" in e.tags)


def test_fd_quest_spend_clue_summons_enemy(monkeypatch) -> None:
    eng, session, tile, quest = _fd_quest_session("fd_defeat_enemy", fd_quest_areas_until_spawn=5)
    session.clues_found = 2
    session.party[0].clues = 2
    monkeypatch.setattr("app.engine.forsaken_depths_quest.roll_d6", lambda: 4)
    from app.engine.forsaken_depths_quest import spend_fd_quest_clue_for_enemy

    assert spend_fd_quest_clue_for_enemy(eng, session, show_rolls=False)
    assert quest.fd_quest_enemy_spawned
    assert session.clues_found == 1


def test_fd_quest_servitor_pending_spawns_on_next_room(monkeypatch) -> None:
    eng, session, tile, quest = _fd_quest_session(
        "fd_servitor",
        fd_quest_servitor_type="Bone Collector",
        fd_quest_servitor_pending_room=True,
    )
    monkeypatch.setattr("app.engine.forsaken_depths_quest.roll_d6", lambda: 1)
    from app.engine.forsaken_depths_quest import fd_quest_on_new_tile_entered

    fd_quest_on_new_tile_entered(eng, session, tile, show_rolls=False)
    assert not quest.fd_quest_servitor_pending_room
    assert any("fd_quest_servitor" in e.tags for e in tile.enemies)


def test_fd_quest_lost_page_counts_scroll(monkeypatch) -> None:
    eng, session, tile, quest = _fd_quest_session("fd_lost_pages", fd_quest_pages_required=4)
    session.party[0].inventory.append("Scroll of Fireball")
    from app.engine.forsaken_depths_quest import recover_fd_lost_page

    assert recover_fd_lost_page(eng, session, "Scroll of Fireball", show_rolls=False)
    assert quest.fd_quest_pages_found == 1
    assert "Scroll of Fireball" not in session.party[0].inventory


def test_fd_quest_three_items_rejects_gear_at_accept() -> None:
    eng, session, tile, quest = _fd_quest_session(
        "fd_three_items",
        fd_quest_items_required=3,
        fd_quest_inventory_snapshot={"hero-1": ["Hand weapon", "Light armor"]},
    )
    session.party[0].inventory.append("Magic wand of sparks")
    from app.engine.forsaken_depths_quest import turn_in_fd_quest_item

    assert turn_in_fd_quest_item(eng, session, "Hand weapon", show_rolls=False) is False
    assert turn_in_fd_quest_item(eng, session, "Magic wand of sparks", show_rolls=False)
    assert quest.fd_quest_items_turned_in == 1


def test_fd_quest_combat_end_tracks_servitor_capture() -> None:
    _, session, _, quest = _fd_quest_session("fd_servitor")
    from app.engine.forsaken_depths_quest import update_fd_quest_on_combat_end
    from app.schemas import EnemyState

    servitor = EnemyState(
        id="srv-1",
        name="Bone Collector",
        category="minions",
        level=3,
        life=0,
        max_life=3,
        attacks=1,
        subdued=True,
        tags=["fd_quest_servitor"],
    )
    update_fd_quest_on_combat_end(session, [servitor], show_rolls=False)
    assert quest.fd_quest_servitor_found


def test_fd_session_courtship_enabled_by_default() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-court",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    assert session.courtship_enabled is True


def test_fd_session_courtship_can_be_disabled() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-no-court",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=False,
    )
    assert session.courtship_enabled is False


def test_fd_portal_demesne_blocked_when_courtship_disabled() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-portal",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=False,
    )
    tile = session.map_state.tiles[0]
    session.fd_portal_tile_id = tile.id
    session.mode = "exploration"
    from app.engine.forsaken_depths_events import choose_fd_event_portal

    assert choose_fd_event_portal(eng, session, "demesne", show_rolls=False) is False


def test_fd_lady_in_black_oracle_kills_on_incomplete_exit() -> None:
    eng, session, _, quest = _fd_quest_session("fd_lost_pages")
    quest.fd_oracle_character_id = session.party[0].character_id
    from app.engine.forsaken_depths_quest import resolve_fd_lady_in_black_oracle_on_exit

    resolve_fd_lady_in_black_oracle_on_exit(session, show_rolls=False)
    assert session.party[0].current_life == 0
    assert session.party[0].character_id in session.permanently_lost_character_ids


def test_fd_oracle_claim_clears_enchantment() -> None:
    eng, session, tile, quest = _fd_quest_session(
        "fd_pilgrimage",
        fd_quest_idol_visits=3,
        fd_quest_idol_visits_required=3,
    )
    quest.fd_oracle_character_id = session.party[0].character_id
    quest.tile_id = tile.id
    session.map_state.current_tile_id = tile.id
    from app.engine.forsaken_depths_quest import claim_fd_quest_reward

    assert claim_fd_quest_reward(
        eng, session, show_rolls=False, quest_id=quest.quest_id, reward_choice="xp_all"
    )
    assert quest.fd_oracle_character_id is None
    assert session.active_quest is None


def test_fd_dual_quests_oracle_only_kills_linked() -> None:
    eng, session, tile, quest_a = _fd_quest_session(
        "fd_pilgrimage",
        fd_quest_idol_visits=3,
        fd_quest_idol_visits_required=3,
    )
    from app.schemas import ActiveQuestState
    from app.engine.forsaken_depths_quest import claim_fd_quest_reward, resolve_fd_lady_in_black_oracle_on_exit

    quest_b = ActiveQuestState(
        tile_id=tile.id,
        key="fd_defeat_enemy",
        description="oracle quest b",
        fd_quest_enemy_defeated=False,
    )
    quest_a.fd_oracle_character_id = session.party[0].character_id
    quest_b.fd_oracle_character_id = session.party[0].character_id
    session.fd_secondary_quest = quest_b
    assert claim_fd_quest_reward(
        eng, session, show_rolls=False, quest_id=quest_a.quest_id, reward_choice="xp_all"
    )
    resolve_fd_lady_in_black_oracle_on_exit(session, show_rolls=False)
    assert session.party[0].current_life == 0


def test_fd_legendary_spell_catalog() -> None:
    eng = engine()
    from app.engine.forsaken_depths_spell_scrolls import fd_spell_reward_catalog

    catalog = fd_spell_reward_catalog(eng)
    assert "Contact Forgotten God" in catalog["legendary"]
    assert "Destroy Invincible Fiend" in catalog["legendary"]


def test_fd_sacrifice_grants_clue_and_quest(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-sacrifice",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    session.mode = "exploration"
    session.map_state.current_tile_id = tile.id
    session.fd_idol_pending_choice = "lady_in_black"
    member = session.party[0]
    member.inventory.append("Heroic magic weapon")
    monkeypatch.setattr("app.engine.forsaken_depths_quest.roll_d6", lambda: 2)
    from app.engine.forsaken_depths_cyclopean_idol import resolve_fd_idol_choice

    assert resolve_fd_idol_choice(
        eng,
        session,
        tile,
        "lady_sacrifice",
        item_name="Heroic magic weapon",
        show_rolls=False,
    )
    assert session.clues_found >= 1
    assert session.active_quest is not None
    assert session.active_quest.fd_oracle_character_id is None


def test_fd_dark_pits_scroll_reward() -> None:
    eng, session, tile, quest = _fd_quest_session(
        "fd_dark_pits",
        fd_quest_dark_pits_cleared=True,
        reward_claimed=False,
    )
    quest.tile_id = tile.id
    session.map_state.current_tile_id = tile.id
    from app.engine.forsaken_depths_quest import claim_fd_quest_reward

    assert claim_fd_quest_reward(eng, session, spell_name="Fireball", show_rolls=False)
    assert any("Scroll of Fireball" in item for item in session.party[0].inventory)


def test_setup_includes_courtship_toggle() -> None:
    index_html = Path("src/app/static/index.html").read_text(encoding="utf-8")
    assert 'id="courtship-enabled"' in index_html
