from __future__ import annotations

from pathlib import Path

from app.engine import random_dungeon
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


def test_forsaken_depths_start_tile_gets_dungeon_exit(monkeypatch) -> None:
    eng = engine()
    monkeypatch.setattr(random_dungeon, "roll_fd_dungeon_start_key", lambda: "16")

    session = eng.create_session(
        "fd-start-exit",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )

    start = session.map_state.tiles[0]
    dungeon_exits = [exit_state for exit_state in start.exits if exit_state.dungeon_exit]
    assert start.tile_catalog == "forsaken_depths"
    assert len(dungeon_exits) == 1
    assert dungeon_exits[0].status == "open"
    assert any("entered through the" in entry for entry in session.log)


def test_forsaken_depths_normalize_repairs_missing_start_exit(monkeypatch) -> None:
    eng = engine()
    monkeypatch.setattr(random_dungeon, "roll_fd_dungeon_start_key", lambda: "16")
    session = eng.create_session(
        "fd-start-repair",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    start = session.map_state.tiles[0]
    start.exits = [exit_state for exit_state in start.exits if not exit_state.dungeon_exit]

    repaired, changed = eng.normalize_session(session)

    assert repaired is session
    assert changed is True
    assert any(exit_state.dungeon_exit for exit_state in start.exits)
    assert next(exit_state for exit_state in start.exits if exit_state.dungeon_exit).status == "open"


def test_forsaken_depths_beast_cage_resolve_logs_feedback() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-beast-cage",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "fd_trap"
    tile.trap_key = "fd_beast_cage"
    tile.trap_level = 10
    tile.trap_resolved = False
    before = len(session.log)

    eng.advance(session, "resolve_trap")

    new_log = session.log[before:]
    assert any("Beast Cage" in entry for entry in new_log)
    assert any("Trap cleared" in entry or "attacks with surprise" in entry for entry in new_log)
    assert tile.trap_resolved is True


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
    assert "fd-surrounded-by-foes" in index_html
    assert "fd-fingers-worms" in index_html
    assert "fd-no-danger-here" in index_html
    assert "fd-oblivion-offer" in index_html
    assert "fd-magic-mr" in index_html
    assert "fdTravelModeDisplay" in app_js
    assert "fdCitadelDisplay" in app_js
    assert "fdSideSheetDisplay" in app_js
    assert "fdCitadelModifierTooltip" in app_js
    assert "appendFdCitadelSideSheetActions" in app_js
    assert "appendCourtshipDemesneActions" in app_js
    assert "courtship_roll_encounter" in app_js
    assert "courtship_book_choice" in app_js
    assert "courtship_damsel_penalty" in app_js
    assert "courtshipDamselPenaltyLife" in app_js
    assert "furnaceGemItems" in app_js
    assert "courtship_book_of_secrets_table" in app_js
    assert "resolve_fd_cyclopean_idol" in app_js
    assert "appendFdQuestActions" in app_js
    assert "fd_quest_spend_clue_enemy" in app_js
    assert "recover_fd_lost_page" in app_js
    assert "appendFdRevelationActions" in app_js
    assert "fdSurroundedByFoesDisplay" in app_js
    assert "Surrounded by Foes hallucination" in app_js
    assert "fdFingersWormsDisplay" in app_js
    assert "fdNoDangerHereDisplay" in app_js
    assert "My Fingers are Worms (FD p.55)" in app_js
    assert "There is No Danger Here (FD p.55)" in app_js
    assert "enterFdSideSheet" in app_js
    assert "fdPrisonersEscape" in app_js


def test_map_styles_include_river_water_overlay() -> None:
    styles = Path("src/app/static/styles.css").read_text(encoding="utf-8")
    assert ".map-square.water" in styles
    assert "env-river" in styles
    assert ".fd-boat-status" in styles
    assert ".fd-surrounded-by-foes" in styles
    assert ".fd-fingers-worms" in styles
    assert ".fd-no-danger-here" in styles
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
    hordes = {row["name"]: row for row in monsters["fd_horde"]}
    assert hordes["Horde of Deep Trolls"]["attacks"] == 1
    assert "regeneration" in hordes["Horde of Deep Trolls"]["tags"]
    assert hordes["Horde of Lizardmen of the Deep"]["attacks"] == 2
    assert "fd_horde_lizardman_poison" in hordes["Horde of Lizardmen of the Deep"]["tags"]
    assert hordes["Horde of Goblins of the Deep"]["attacks"] == 1
    assert "half_life_level_drop:2" in hordes["Horde of Goblins of the Deep"]["tags"]


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
    from app.engine.forsaken_depths_content import apply_fd_hallucination

    apply_fd_hallucination(eng, session, tile, hcl=5, show_rolls=True)
    assert tile.resolved
    assert any("Horrors from Beyond" in entry for entry in session.log)
    assert session.party[0].madness == 2


def test_fd_horrors_from_beyond_applies_tier_madness(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-horrors-tier",
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
    from app.engine.forsaken_depths_content import apply_fd_hallucination

    apply_fd_hallucination(eng, session, tile, hcl=7, show_rolls=True)

    assert session.party[0].madness == 3


def test_fd_fingers_are_worms_blocks_items_and_clears() -> None:
    eng = engine()
    member = _party_member()
    member.inventory.append("Potion of Healing")
    session = eng.create_session(
        "fd-worms",
        "party-1",
        [member],
        ruleset="forsaken_depths",
    )
    from app.engine.forsaken_depths_content import FD_FINGERS_ARE_WORMS_STATUS

    session.party[0].statuses.append(FD_FINGERS_ARE_WORMS_STATUS)
    eng.advance(session, "use_potion", character_id="hero-1", item_name="Potion of Healing")

    assert "Potion of Healing" in session.party[0].inventory
    assert any("cannot use weapons or held items" in entry for entry in session.log)

    from app.engine.forsaken_depths_content import clear_fd_fingers_are_worms_at_encounter_end

    session.log.extend(clear_fd_fingers_are_worms_at_encounter_end(session))
    assert FD_FINGERS_ARE_WORMS_STATUS not in session.party[0].statuses
    assert any("ends with the encounter" in entry for entry in session.log)


def test_fd_hallucinations_clear_on_damage_and_blessing() -> None:
    member = _party_member()
    session = engine().create_session(
        "fd-hallucination-clear",
        "party-1",
        [member],
        ruleset="forsaken_depths",
    )
    from app.engine.forsaken_depths_content import (
        FD_FINGERS_ARE_WORMS_STATUS,
        FD_NO_DANGER_HERE_STATUS,
    )
    from app.engine.party_life import apply_party_life_loss
    from app.engine.spells import _cast_blessing

    session.party[0].statuses.extend([FD_FINGERS_ARE_WORMS_STATUS, FD_NO_DANGER_HERE_STATUS])
    applied = apply_party_life_loss(session, session.party[0], 1, log=session.log)
    assert applied == 1
    assert FD_FINGERS_ARE_WORMS_STATUS not in session.party[0].statuses
    assert FD_NO_DANGER_HERE_STATUS not in session.party[0].statuses
    assert any("stops ignoring danger" in entry for entry in session.log)

    session.party[0].statuses.extend([FD_FINGERS_ARE_WORMS_STATUS, FD_NO_DANGER_HERE_STATUS])
    _cast_blessing(
        session.party[0],
        session.party,
        [],
        session.party[0].character_id,
        session.log,
        session=session,
    )
    assert FD_FINGERS_ARE_WORMS_STATUS not in session.party[0].statuses
    assert FD_NO_DANGER_HERE_STATUS not in session.party[0].statuses
    assert any("Blessing clears My Fingers are Worms" in entry for entry in session.log)


def test_fd_no_danger_here_auto_fails_trap_save() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-no-danger-save",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    from app.engine.forsaken_depths_content import FD_NO_DANGER_HERE_STATUS

    session.party[0].statuses.append(FD_NO_DANGER_HERE_STATUS)
    failed, log = eng.table_roller._trap_save_check(
        session.party[0],
        99,
        "L99 trap",
        poison=False,
        show_rolls=True,
        explain_math=True,
        trap_key="hidden_pit",
        session=session,
    )

    assert failed
    assert any("automatically fails" in entry for entry in log)


def test_fd_surrounded_by_foes_tracks_combat_rounds(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-surrounded",
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
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_d6", lambda: 1)
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_formula", lambda formula: 2)

    from app.engine.forsaken_depths_content import apply_fd_hallucination

    apply_fd_hallucination(eng, session, tile, hcl=5, show_rolls=True)

    assert session.fd_surrounded_by_foes_character_id == "hero-1"
    assert session.fd_surrounded_by_foes_turns_remaining == 2
    assert any("allies are foes" in entry for entry in session.log)

    from app.engine.forsaken_depths_content import tick_fd_surrounded_by_foes

    tick_fd_surrounded_by_foes(session, show_rolls=True)
    assert session.fd_surrounded_by_foes_turns_remaining == 1
    tick_fd_surrounded_by_foes(session, show_rolls=True)
    assert session.fd_surrounded_by_foes_turns_remaining == 0
    assert session.fd_surrounded_by_foes_character_id is None
    assert any("shakes off Surrounded by Foes" in entry for entry in session.log)


def test_fd_foe_hallucination_mirror_no_defense_auto_hit(monkeypatch) -> None:
    from app.engine.combat import CombatContext, _resolve_pc_attack
    from app.engine.forsaken_depths_content import (
        FD_FOE_NO_DEFENSE_TAG,
        apply_fd_foe_hallucination,
    )

    eng = engine()
    session = eng.create_session(
        "fd-foe-hallucination",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    enemy = EnemyState(
        id="foe-1",
        name="Hallucinating Foe",
        category="boss",
        level=20,
        life=3,
        max_life=3,
        attacks=1,
        tags=["forsaken_depths"],
    )
    tile = session.map_state.tiles[0]
    tile.enemies = [enemy]
    log = apply_fd_foe_hallucination(eng, session, tile, enemy, forced_roll=2)
    assert FD_FOE_NO_DEFENSE_TAG in enemy.tags
    assert any("stops attacking and defending" in entry for entry in log)

    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
    combat_log: list[str] = []
    _resolve_pc_attack(
        session.party[0],
        enemy,
        show_rolls=True,
        explain_math=True,
        party_attack_bonus=0,
        subdual=False,
        missile=False,
        living_enemies=[enemy],
        log=combat_log,
        context=CombatContext(session=session),
    )

    assert enemy.life < enemy.max_life
    assert FD_FOE_NO_DEFENSE_TAG not in enemy.tags
    assert any("hits automatically" in entry for entry in combat_log)
    assert any("foe hallucination ends" in entry for entry in combat_log)


def test_fd_foe_hallucination_revelation_fails_next_attack() -> None:
    from app.engine.combat import CombatContext, _resolve_pc_attack
    from app.engine.forsaken_depths_content import FD_FOE_NEXT_ATTACK_FAILS_TAG, apply_fd_foe_hallucination

    eng = engine()
    session = eng.create_session(
        "fd-foe-revelation",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    enemy = EnemyState(
        id="foe-1",
        name="Revealed Foe",
        category="boss",
        level=5,
        life=3,
        max_life=3,
        attacks=1,
        tags=["forsaken_depths"],
    )
    tile = session.map_state.tiles[0]
    tile.enemies = [enemy]
    apply_fd_foe_hallucination(eng, session, tile, enemy, forced_roll=5)
    assert FD_FOE_NEXT_ATTACK_FAILS_TAG in enemy.tags
    assert enemy.level == 4

    combat_log: list[str] = []
    _resolve_pc_attack(
        session.party[0],
        enemy,
        show_rolls=True,
        explain_math=False,
        party_attack_bonus=99,
        subdual=False,
        missile=False,
        living_enemies=[enemy],
        log=combat_log,
        context=CombatContext(session=session),
    )

    assert enemy.life == enemy.max_life
    assert FD_FOE_NEXT_ATTACK_FAILS_TAG not in enemy.tags
    assert any("fails automatically" in entry for entry in combat_log)


def test_fd_foe_hallucination_party_controlled_attacks_other_foe(monkeypatch) -> None:
    from app.engine.forsaken_depths_content import (
        FD_FOE_PARTY_CONTROLLED_TAG,
        apply_fd_foe_hallucination,
        apply_fd_party_controlled_foes,
    )

    eng = engine()
    session = eng.create_session(
        "fd-foe-party-controlled",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    controlled = EnemyState(
        id="foe-1",
        name="Confused Foe",
        category="boss",
        level=5,
        life=3,
        max_life=3,
        attacks=1,
        tags=["forsaken_depths"],
    )
    target = EnemyState(
        id="foe-2",
        name="Other Foe",
        category="boss",
        level=2,
        life=3,
        max_life=3,
        attacks=1,
        tags=["forsaken_depths"],
    )
    tile = session.map_state.tiles[0]
    tile.enemies = [controlled, target]
    apply_fd_foe_hallucination(eng, session, tile, controlled, forced_roll=1)
    assert FD_FOE_PARTY_CONTROLLED_TAG in controlled.tags
    monkeypatch.setattr("app.engine.dice.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    log = apply_fd_party_controlled_foes(tile.enemies, show_rolls=True)

    assert target.life == 2
    assert any("attacks Other Foe for the party" in entry for entry in log)


def test_fd_goblin_horde_half_life_level_drop_is_two() -> None:
    from app.engine.subdual import apply_major_foe_level_drop

    enemy = EnemyState(
        id="goblin-horde",
        name="Horde of Goblins of the Deep",
        category="boss",
        level=6,
        life=2,
        max_life=5,
        attacks=1,
        tags=["horde", "forsaken_depths", "half_life_level_drop:2"],
    )

    assert apply_major_foe_level_drop(enemy) is True
    assert enemy.level == 4


def test_fd_goblin_horde_opening_javelins_target_highest_life(monkeypatch) -> None:
    from app.engine.forsaken_depths_hordes import (
        FD_HORDE_VOLLEY_USED_TAG,
        apply_fd_horde_opening_volleys,
    )

    eng = engine()
    hero = _party_member()
    scout = PartyMemberState.model_validate(
        {
            **hero.model_dump(),
            "character_id": "hero-2",
            "name": "Scout",
            "current_life": 6,
            "max_life": 8,
            "marching_order": 2,
        }
    )
    session = eng.create_session(
        "fd-goblin-volley",
        "party-1",
        [hero, scout],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    enemy = EnemyState(
        id="goblin-horde",
        name="Horde of Goblins of the Deep",
        category="boss",
        level=20,
        life=4,
        max_life=4,
        attacks=1,
        tags=["horde", "goblin", "forsaken_depths", "fd_horde_goblin_javelins"],
    )
    tile.enemies = [enemy]
    monkeypatch.setattr("app.engine.forsaken_depths_hordes.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    log = apply_fd_horde_opening_volleys(session, tile, show_rolls=True)

    assert FD_HORDE_VOLLEY_USED_TAG in enemy.tags
    assert session.party[0].current_life == 10
    assert session.party[1].current_life == 5
    assert sum(1 for entry in log if entry.startswith("Volley Defense:")) == 3
    assert any("throws javelins before melee" in entry for entry in log)


def test_fd_horde_salvage_marks_room_after_defeat() -> None:
    from app.engine.forsaken_depths_hordes import (
        FD_HORDE_WEAPON_SALVAGE_OBJECT,
        add_fd_horde_weapon_salvage,
    )

    tile = TileState(
        id="horde-room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Horde room",
        description="Defeated horde",
    )
    defeated = [
        EnemyState(
            id="troll-horde",
            name="Horde of Deep Trolls",
            category="boss",
            level=6,
            life=0,
            max_life=7,
            attacks=1,
            tags=["horde", "forsaken_depths"],
        )
    ]

    log = add_fd_horde_weapon_salvage(tile, defeated)

    assert FD_HORDE_WEAPON_SALVAGE_OBJECT in tile.objects
    assert any("Light weapon" in entry and "hand weapon" in entry for entry in log)


def test_fd_lizardman_horde_poison_is_cumulative_and_affects_attack(monkeypatch) -> None:
    from app.engine.class_combat import attack_modifier
    from app.engine.forsaken_depths_hordes import (
        FD_LIZARDMAN_HORDE_POISON_STATUS,
        apply_lizardman_horde_poison_after_party_turn,
    )

    eng = engine()
    hero = _party_member()
    hero.current_life = 8
    session = eng.create_session(
        "fd-lizardman-poison",
        "party-1",
        [hero],
        ruleset="forsaken_depths",
    )
    session.party[0].current_life = 8
    enemy = EnemyState(
        id="lizard-horde",
        name="Horde of Lizardmen of the Deep",
        category="boss",
        level=7,
        life=5,
        max_life=5,
        attacks=2,
        tags=["horde", "lizardman", "forsaken_depths", "fd_horde_lizardman_poison"],
    )
    monkeypatch.setattr("app.engine.forsaken_depths_hordes.random.choice", lambda choices: choices[0])
    monkeypatch.setattr("app.engine.forsaken_depths_hordes.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    first = apply_lizardman_horde_poison_after_party_turn(session, [enemy], show_rolls=True)
    second = apply_lizardman_horde_poison_after_party_turn(session, [enemy], show_rolls=True)

    assert session.party[0].statuses.count(FD_LIZARDMAN_HORDE_POISON_STATUS) == 2
    assert attack_modifier(session.party[0], enemy) == session.party[0].level - 2
    assert any("now -1" in entry for entry in first)
    assert any("now -2" in entry for entry in second)


def test_fd_lizardman_horde_poison_clears_with_blessing() -> None:
    from app.engine.forsaken_depths_hordes import FD_LIZARDMAN_HORDE_POISON_STATUS
    from app.engine.spells import _cast_blessing

    eng = engine()
    member = _party_member()
    member.spells = ["Blessing"]
    member.statuses.extend([FD_LIZARDMAN_HORDE_POISON_STATUS, FD_LIZARDMAN_HORDE_POISON_STATUS])
    session = eng.create_session(
        "fd-lizardman-blessing",
        "party-1",
        [member],
        ruleset="forsaken_depths",
    )
    log: list[str] = []

    _cast_blessing(
        session.party[0],
        session.party,
        [],
        session.party[0].character_id,
        log,
        session=session,
        show_rolls=True,
    )

    assert FD_LIZARDMAN_HORDE_POISON_STATUS not in session.party[0].statuses
    assert any("Lizardman Horde poison Attack penalty" in entry for entry in log)


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
    assert outcome.items
    assert any("Gem" in item for item in outcome.items)


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
    assert outcome.items
    assert any("Gem" in item for item in outcome.items)


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


def test_fd_ruins_complex_machinery_success_grants_clue(monkeypatch) -> None:
    from app.engine.forsaken_depths_ruins import setup_ruins_complex_machinery

    eng = engine()
    session = eng.create_session(
        "fd-ruins-machinery-success",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    session.mode = "exploration"
    setup_ruins_complex_machinery(session, tile, show_rolls=False)
    monkeypatch.setattr("app.engine.forsaken_depths_ruins.roll_exploding_for_level", lambda *args, **kwargs: (20, [20]))

    eng.advance(session, "resolve_fd_ruins_machinery", character_id="hero-1")

    assert tile.fd_ruins_machinery_resolved
    assert session.clues_found == 1
    assert session.party[0].clues == 1
    assert any("gains 1 Clue" in entry for entry in session.log)


def test_fd_ruins_complex_machinery_failure_deals_tier_damage_and_locks_attempt(monkeypatch) -> None:
    from app.engine.experience import tier_for_level
    from app.engine.forsaken_depths_ruins import setup_ruins_complex_machinery

    eng = engine()
    session = eng.create_session(
        "fd-ruins-machinery-fail",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    session.mode = "exploration"
    setup_ruins_complex_machinery(session, tile, show_rolls=False)
    monkeypatch.setattr("app.engine.forsaken_depths_ruins.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
    before = session.party[0].current_life

    eng.advance(session, "resolve_fd_ruins_machinery", character_id="hero-1")
    eng.advance(session, "resolve_fd_ruins_machinery", character_id="hero-1")

    assert not tile.fd_ruins_machinery_resolved
    assert session.party[0].current_life == before - tier_for_level(session.party[0].level)
    assert tile.fd_ruins_machinery_attempted_character_ids == ["hero-1"]
    assert any("already tried" in entry for entry in session.log)


def test_fd_ruins_psychic_residue_failure_choices(monkeypatch) -> None:
    from app.engine.forsaken_depths_ruins import resolve_ruins_psychic_residue

    caster = _party_member()
    caster.character_id = "hero-2"
    caster.name = "Wizard"
    caster.class_id = "wizard"
    caster.class_name = "Wizard"
    caster.spells = ["Sleep", "Fireball"]
    eng = engine()
    session = eng.create_session(
        "fd-ruins-psychic",
        "party-1",
        [_party_member(), caster],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    session.mode = "exploration"
    monkeypatch.setattr("app.engine.forsaken_depths_ruins.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    resolve_ruins_psychic_residue(eng, session, tile, hcl=5, show_rolls=False)
    eng.advance(
        session,
        "resolve_fd_ruins_psychic_choice",
        character_id="hero-1",
        fd_ruins_psychic_choice="damage",
    )
    eng.advance(
        session,
        "resolve_fd_ruins_psychic_choice",
        character_id="hero-2",
        fd_ruins_psychic_choice="spell_slots",
    )

    assert "hero-1" not in session.fd_ruins_psychic_pending
    assert "hero-2" not in session.fd_ruins_psychic_pending
    assert session.party[0].current_life == 9
    assert session.party[1].spells == []
    assert any("loses spell slot" in entry for entry in session.log)


def test_fd_ruins_psychic_residue_success_grants_future_bonus(monkeypatch) -> None:
    from app.engine.forsaken_depths_ruins import FD_RUINS_PSYCHIC_IMMUNITY_STATUS, resolve_ruins_psychic_residue

    eng = engine()
    session = eng.create_session(
        "fd-ruins-psychic-success",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    session.mode = "exploration"
    monkeypatch.setattr("app.engine.forsaken_depths_ruins.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    resolve_ruins_psychic_residue(eng, session, tile, hcl=5, show_rolls=False)
    assert FD_RUINS_PSYCHIC_IMMUNITY_STATUS in session.party[0].statuses
    assert not session.fd_ruins_psychic_pending


def test_fd_winds_of_despair_waits_for_player_choices() -> None:
    from app.engine.forsaken_depths_content import apply_fd_event

    eng = engine()
    session = eng.create_session(
        "fd-winds-choice",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.special_event_key = "winds_of_despair"

    apply_fd_event(eng, session, tile, hcl=5, show_rolls=False)
    assert session.fd_winds_of_despair_pending == {"hero-1": tile.id}

    eng.advance(session, "resolve_fd_winds_choice", character_id="hero-1", fd_winds_choice="life")

    assert session.fd_winds_of_despair_pending == {}
    assert session.party[0].current_life == 10


def test_fd_disintegration_blast_player_can_sacrifice_magic_item(monkeypatch) -> None:
    eng = engine()
    hero = _party_member()
    hero.inventory.append("Legendary Ring")
    session = eng.create_session(
        "fd-disintegration-choice",
        "party-1",
        [hero],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.trap_key = "fd_disintegration_blast"
    tile.trap_level = 99
    monkeypatch.setattr("app.engine.forsaken_depths_traps.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))
    before = session.party[0].current_life

    eng.advance(session, "resolve_trap")
    assert session.fd_disintegration_pending["character_id"] == "hero-1"
    assert not tile.trap_resolved

    eng.advance(
        session,
        "resolve_fd_disintegration_choice",
        fd_disintegration_choice="sacrifice_item",
        item_name="Legendary Ring",
    )

    assert session.fd_disintegration_pending == {}
    assert tile.trap_resolved
    assert "Legendary Ring" not in session.party[0].inventory
    assert session.party[0].current_life < before


def test_fd_magic_resistant_liquid_blocks_spell_cast(monkeypatch) -> None:
    eng = engine()
    hero = _party_member()
    hero.class_id = "wizard"
    hero.class_name = "Wizard"
    hero.spells = ["Fireball"]
    session = eng.create_session(
        "fd-magic-liquid",
        "party-1",
        [hero],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.trap_key = "fd_magic_resistant_liquid"
    tile.trap_level = 99
    monkeypatch.setattr("app.engine.forsaken_depths_traps.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    eng.advance(session, "resolve_trap")
    eng.advance(session, "cast_spell", character_id="hero-1", spell_name="Fireball")

    assert any(status.startswith("FD Magic Resistant Liquid") for status in session.party[0].statuses)
    assert any("magic resistant liquid" in entry for entry in session.log)


def test_fd_soulbinding_trap_prompts_consequence_when_away(monkeypatch) -> None:
    from app.engine.forsaken_depths_traps import check_fd_soulbinding_on_area_enter

    eng = engine()
    hero = _party_member()
    rear = _party_member()
    rear.character_id = "hero-2"
    rear.name = "Rear"
    rear.marching_order = 2
    session = eng.create_session(
        "fd-soulbinding-choice",
        "party-1",
        [hero, rear],
        ruleset="forsaken_depths",
    )
    origin = session.map_state.tiles[0]
    origin.trap_key = "fd_soulbinding_trap"
    origin.trap_level = 99
    monkeypatch.setattr("app.engine.forsaken_depths_traps.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    eng.advance(session, "resolve_trap")
    assert any(status.startswith("FD Soulbound:") for status in session.party[1].statuses)

    away = TileState(id="away", x=1, y=0, tile_key="11", tile_type="room", title="Away", description="Away")
    check_fd_soulbinding_on_area_enter(session, away, show_rolls=False)
    assert session.fd_soulbinding_pending == {"hero-2": "away"}

    eng.advance(session, "resolve_fd_soulbinding_choice", character_id="hero-2", fd_soulbinding_choice="madness")
    assert session.fd_soulbinding_pending == {}
    assert session.party[1].madness == 1


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


def test_fd_legendary_destroy_invincible_fiend(monkeypatch) -> None:
    from app.engine.forsaken_depths_legendary_spells import try_resolve_fd_legendary_spell
    from app.engine.spells import normalize_spell_name

    caster = _party_member()
    caster.class_id = "wizard"
    caster.spells = ["Destroy Invincible Fiend"]
    foe = EnemyState(
        id="fiend-1",
        name="Invincible Horror",
        level=8,
        life=20,
        max_life=20,
        category="weird",
        party_attacks_received=12,
    )
    monkeypatch.setattr(
        "app.engine.forsaken_depths_legendary_spells.resolve_spell_effect",
        lambda *args, **kwargs: (True, ["hit"], 10, []),
    )
    log: list[str] = []
    outcome = try_resolve_fd_legendary_spell(
        normalize_spell_name("Destroy Invincible Fiend"),
        "Destroy Invincible Fiend",
        caster,
        [caster],
        [foe],
        log,
        target_foe_id="fiend-1",
        show_rolls=False,
    )
    assert outcome is not None
    assert foe.life == 0
    assert outcome.combat_over is True


def test_fd_legendary_illusionary_distraction(monkeypatch) -> None:
    from app.engine.forsaken_depths_legendary_spells import try_resolve_fd_legendary_spell
    from app.engine.spells import normalize_spell_name

    eng = engine()
    session = eng.create_session("fd-illus", "party-1", [_party_member()], ruleset="forsaken_depths")
    caster = session.party[0]
    caster.class_id = "illusionist"
    foe = EnemyState(id="f-1", name="Minion", level=3, life=1, max_life=1, category="minions")
    monkeypatch.setattr(
        "app.engine.forsaken_depths_legendary_spells.resolve_spell_effect",
        lambda *args, **kwargs: (True, ["hit"], 8, []),
    )
    outcome = try_resolve_fd_legendary_spell(
        normalize_spell_name("Illusionary Distractions"),
        "Illusionary Distractions",
        caster,
        [caster],
        [foe],
        [],
        spell_target_mode="combat",
        session=session,
        show_rolls=False,
    )
    assert outcome is not None
    assert session.fd_illusionary_distraction_active is True
    assert "illusionary_distracted" in foe.tags


def test_courtship_woo_giving_three_successes_clears_foes(monkeypatch) -> None:
    from app.engine.courtship_demesne import resolve_courtship_woo_giving

    eng = engine()
    session = eng.create_session(
        "courtship-woo",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    tile = session.map_state.tiles[0]
    session.courtship_demesne_active = True
    session.courtship_return_tile_id = tile.id
    session.courtship_woo_active = True
    session.courtship_woo_template = "Lorelei"
    session.courtship_woo_speaker_id = session.party[0].character_id
    tile.enemies.append(
        EnemyState(id="d-1", name="Lorelei", level=3, life=1, max_life=1, category="minions")
    )
    session.courtship_woo_successes = 2
    monkeypatch.setattr(
        "app.engine.class_abilities.resolve_social_save",
        lambda *args, **kwargs: (True, ["ok"]),
    )
    monkeypatch.setattr("app.engine.courtship_demesne.roll_d3", lambda: 2)
    assert resolve_courtship_woo_giving(eng, session, show_rolls=False)
    assert not tile.enemies
    assert not session.courtship_woo_active


def test_courtship_seduce_reaction_peaceful(monkeypatch) -> None:
    from app.engine.courtship_demesne import resolve_courtship_seduce_reaction

    eng = engine()
    session = eng.create_session(
        "courtship-seduce",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    tile = session.map_state.tiles[0]
    session.courtship_demesne_active = True
    session.courtship_return_tile_id = tile.id
    session.courtship_pending_choice = "seduce_or_fight"
    session.courtship_pending_choice_label = "Giggling Gingers"
    tile.enemies.append(
        EnemyState(id="g-1", name="Giggling Gingers", level=3, life=1, max_life=1, category="minions")
    )
    monkeypatch.setattr("app.engine.courtship_demesne.roll_d6", lambda: 3)
    monkeypatch.setattr(
        "app.engine.class_abilities.resolve_social_save",
        lambda *args, **kwargs: (True, ["seduced"]),
    )
    monkeypatch.setattr("app.engine.courtship_demesne.roll_d3", lambda: 1)
    assert resolve_courtship_seduce_reaction(eng, session, None, show_rolls=False)
    assert not tile.enemies


def test_gem_item_value_parsed_from_name() -> None:
    from app.engine.gem_items import format_gem_item, gem_item_value_gp, party_gem_items

    assert gem_item_value_gp("Gem (250gp)") == 250
    assert gem_item_value_gp("Gem") == 0
    assert gem_item_value_gp("Iron sword") == 0
    assert format_gem_item(200) == "Gem (200gp)"


def test_courtship_damsel_penalty_choice(monkeypatch) -> None:
    from app.engine.courtship_demesne import resolve_courtship_damsel_penalty, resolve_courtship_woo_withholding

    eng = engine()
    session = eng.create_session(
        "courtship-damsel",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    session.courtship_return_tile_id = session.map_state.tiles[0].id
    session.courtship_woo_active = True
    session.courtship_woo_template = "Damsel of Teeming Roses"
    session.courtship_woo_speaker_id = session.party[0].character_id
    session.courtship_damsel_penalty_pending = True
    assert resolve_courtship_damsel_penalty(session, "madness", show_rolls=False)
    assert session.courtship_damsel_penalty_mode == "madness"
    monkeypatch.setattr(
        "app.engine.class_abilities.resolve_social_save",
        lambda *args, **kwargs: (False, ["fail"]),
    )
    resolve_courtship_woo_withholding(eng, session, show_rolls=False)
    assert session.courtship_damsel_penalty_mode is None


def test_disturbing_altar_book_choice(monkeypatch) -> None:
    from app.engine.courtship_demesne import resolve_courtship_book_choice

    eng = engine()
    session = eng.create_session(
        "courtship-altar",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    session.courtship_return_tile_id = session.map_state.tiles[0].id
    session.courtship_pending_choice = "disturbing_altar"
    monkeypatch.setattr("app.engine.courtship_book_of_secrets.roll_d3", lambda: 2)
    assert resolve_courtship_book_choice(eng, session, "clues", show_rolls=False)
    assert session.courtship_pending_choice is None


def test_furnace_rejects_gem_below_200gp(monkeypatch) -> None:
    from app.engine.forsaken_depths_legendary_spells import _cast_furnace_of_the_amulet

    caster = _party_member()
    caster.inventory = ["Gem (150gp)"]
    foe = EnemyState(id="f1", name="Weird", category="weird", level=5, life=1, max_life=5, attacks=1)
    monkeypatch.setattr(
        "app.engine.forsaken_depths_legendary_spells.resolve_spell_effect",
        lambda *args, **kwargs: (True, ["hit"], 0, []),
    )
    log: list[str] = []
    outcome = _cast_furnace_of_the_amulet(
        caster,
        [caster],
        [foe],
        log,
        target_foe_id=foe.id,
        session=None,
        show_rolls=False,
        gem_item_name="Gem (150gp)",
    )
    assert any("200" in line for line in outcome.log)


def test_fd_defeated_foe_treasure_stages_choice(monkeypatch) -> None:
    from app.engine.dungeon_table_roller import TreasureOutcome

    eng = engine()
    session = eng.create_session(
        "fd-slay-treasure",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "fd_minions"
    tile.resolved = True
    tile.defeated_enemies = [
        EnemyState(
            id="h1",
            name="Deep Hobgoblins",
            category="minions",
            level=8,
            life=0,
            max_life=1,
            attacks=1,
        )
    ]
    monkeypatch.setattr(
        eng.table_roller,
        "roll_fd_treasure_batch_with_bonuses",
        lambda bonuses, **kwargs: TreasureOutcome(
            "Gold or masterwork weapon?",
            0,
            [],
            [],
            choice_key="fd_gold_or_masterwork",
        ),
    )
    eng._award_treasure(session, tile, show_rolls=True)
    assert tile.pending_treasure_choice == "fd_gold_or_masterwork"
    assert "no treasure rolls" not in " ".join(session.log).lower()


def test_fd_defeated_foe_treasure_skips_without_template_rolls() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-slay-mod",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "fd_minions"
    tile.resolved = True
    tile.defeated_enemies = [
        EnemyState(
            id="t1",
            name="Deep Trolls",
            category="minions",
            level=6,
            life=0,
            max_life=1,
            attacks=1,
        )
    ]
    eng._award_treasure(session, tile, show_rolls=False)
    assert tile.treasure_gold == 0
    assert any("no treasure rolls" in entry.lower() for entry in session.log)


def test_fd_vermin_without_treasure_rolls_skips_loot() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-no-loot",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "fd_vermin"
    tile.resolved = True
    tile.defeated_enemies = [
        EnemyState(
            id="r1",
            name="Rockslugs",
            category="vermin",
            level=5,
            life=0,
            max_life=1,
            attacks=1,
        )
    ]
    eng._award_treasure(session, tile, show_rolls=True)
    assert tile.treasure_gold == 0
    assert not tile.pending_treasure_choice
    assert any("no treasure rolls" in entry.lower() for entry in session.log)


def _fd_etc_entry_tile(eng: RandomDungeonEngine) -> TileState:
    return TileState(
        id="etc-origin",
        x=0,
        y=0,
        tile_key="23",
        tile_type="corridor",
        footprint_width=5,
        footprint_height=5,
        title="Citadel entrance",
        description="ETC test room",
        content_key="fd_empty",
        tile_catalog="forsaken_depths",
        room_codes=["ETC"],
        exits=[
            ExitState(
                id="etc-east",
                direction="east",
                kind="passage",
                x=4,
                y=2,
                span=1,
            )
        ],
    )


def test_fd_enter_citadel_side_sheet_pregenerates_rooms(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-citadel-pregen",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    origin = _fd_etc_entry_tile(eng)
    session.map_state.tiles = [origin]
    session.map_state.current_tile_id = origin.id
    session.mode = "exploration"
    session.fd_citadel_type = "ghost_citadel"
    session.fd_citadel_room_count = 4
    session.fd_citadel_entry_tile_id = origin.id
    monkeypatch.setattr("app.engine.forsaken_depths_side_sheet.roll_d6", lambda: 3)

    eng.advance(session, "enter_fd_side_sheet")

    side_tiles = [tile for tile in session.map_state.tiles if tile.fd_side_sheet]
    assert session.fd_side_sheet_active
    assert session.fd_side_sheet_kind == "citadel"
    assert len(side_tiles) == 4
    assert session.map_state.current_tile_id == side_tiles[0].id
    assert any("Citadel side sheet" in entry for entry in session.log)


def test_fd_dungeon_etc_rolls_citadel_on_enter(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-dungeon-etc",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = _fd_etc_entry_tile(eng)
    session.map_state.tiles = [tile]
    session.map_state.current_tile_id = tile.id
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_d6", lambda: 2)
    monkeypatch.setattr("app.engine.forsaken_depths_content.roll_formula", lambda formula: 5)
    from app.engine.forsaken_depths_river import apply_fd_dungeon_room_codes_on_enter

    apply_fd_dungeon_room_codes_on_enter(eng, session, tile, show_rolls=True)
    assert session.fd_citadel_type == "crowded_citadel"
    assert session.fd_citadel_entry_tile_id == tile.id


def test_fd_end_clears_river_type() -> None:
    from app.engine.forsaken_depths_river import apply_room_codes_on_stretch_entry

    eng = engine()
    session = eng.create_session(
        "fd-end",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "death"
    session.fd_travel_mode = "boat"
    session.fd_flame_stretch_count = 2
    tile = TileState(
        id="end-stretch",
        x=0,
        y=0,
        tile_key="16",
        tile_type="room",
        title="River end",
        description="END",
        tile_catalog="forsaken_depths_rivers",
        room_codes=["END"],
    )
    apply_room_codes_on_stretch_entry(eng, session, tile, show_rolls=True)
    assert session.fd_river_type is None
    assert session.fd_travel_mode == "foot"
    assert session.fd_flame_stretch_count == 0


def test_fd_special_feature_hazard_adds_bridge(monkeypatch) -> None:
    from app.engine.forsaken_depths_river import apply_special_feature_hazard

    session = engine().create_session(
        "fd-spec-bridge",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    tile = TileState(
        id="spec",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Stretch",
        description="Test",
        tile_catalog="forsaken_depths_rivers",
        room_codes=[],
    )
    monkeypatch.setattr("app.engine.forsaken_depths_river.roll_d6", lambda: 1)
    apply_special_feature_hazard(session, tile, show_rolls=True)
    assert "B" in tile.room_codes


def test_fd_river_stretch_hazard_runs_once(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-hazard-once",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "death"
    tile = TileState(
        id="river-once",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River stretch",
        description="Test",
        tile_catalog="forsaken_depths_rivers",
    )
    rolls = iter([1, 2])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls, 2))
    eng._fd_on_river_stretch_entered(session, tile, show_rolls=True)
    hazard_logs = [entry for entry in session.log if "River hazard" in entry]
    assert len(hazard_logs) == 1
    session.log.clear()
    eng._fd_on_river_stretch_entered(session, tile, show_rolls=True)
    assert not any("River hazard" in entry for entry in session.log)


def test_fd_damaged_boat_hazard_skipped_on_foot(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-dmg-foot",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "death"
    session.fd_travel_mode = "foot"
    session.fd_boat_status = "destroyed"
    tile = TileState(
        id="river-foot-dmg",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River stretch",
        description="Test",
        tile_catalog="forsaken_depths_rivers",
    )
    rolls = iter([1, 2])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls, 2))
    eng._fd_on_river_stretch_entered(session, tile, show_rolls=True)
    assert session.fd_boat_status == "destroyed"
    assert any("no effect while traveling on foot" in entry.lower() for entry in session.log)


def test_fd_boatman_charges_fee(monkeypatch) -> None:
    from app.engine.forsaken_depths_river import fd_acquire_boat_at_etr

    eng = engine()
    session = eng.create_session(
        "fd-boatman",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    hero = session.party[0]
    hero.gold = 100
    etr = TileState(
        id="etr",
        x=0,
        y=0,
        tile_key="26",
        tile_type="room",
        title="ETR",
        description="River exit",
        tile_catalog="forsaken_depths",
    )
    monkeypatch.setattr("app.engine.forsaken_depths_river.roll_d6", lambda: 3)
    fd_acquire_boat_at_etr(session, etr, show_rolls=True)
    assert session.fd_travel_mode == "boat"
    assert hero.gold == 80
    assert any("pays the" in entry.lower() for entry in session.log)


def test_fd_serpent_spawns_higher_level_boss(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "fd-serpent",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "serpent"
    row = {
        "name": "Horde of Deep Trolls",
        "enemy_category": "horde",
        "count": "1",
    }
    monkeypatch.setattr(eng, "_resolve_monster_table_key", lambda *args, **kwargs: "fd_horde")
    spawned = eng._fd_spawn_from_table_row(session, row, hcl=5)
    assert spawned
    assert spawned[0].level == 7


def test_fd_conjuration_consult_grants_clue_and_madness() -> None:
    from app.engine.forsaken_depths_river import consult_fd_conjuration_spirits

    eng = engine()
    session = eng.create_session(
        "fd-conj",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "conjuration"
    tile = session.map_state.tiles[0]
    tile.tile_catalog = "forsaken_depths_rivers"
    session.map_state.current_tile_id = tile.id
    session.mode = "exploration"
    hero = session.party[0]
    before_clues = session.clues_found
    assert consult_fd_conjuration_spirits(eng, session, hero.character_id, show_rolls=True)
    assert session.clues_found == before_clues + 1
    assert hero.madness >= 1
    assert tile.id in session.fd_conjuration_consulted_tile_ids


def test_fd_tears_death_spreads_madness() -> None:
    from app.engine.forsaken_depths_river import apply_fd_tears_death_madness_spread

    session = engine().create_session(
        "fd-tears-death",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "tears"
    survivor = session.party[0]
    fallen = PartyMemberState.model_validate(
        {
            **survivor.model_dump(),
            "character_id": "fallen-1",
            "name": "Fallen",
            "current_life": 0,
        }
    )
    session.party.append(fallen)
    apply_fd_tears_death_madness_spread(session, [fallen.character_id], show_rolls=True)
    assert survivor.madness >= 1


def test_fd_fireproof_boat_survives_flame_river(monkeypatch) -> None:
    from app.engine.forsaken_depths_river import apply_flame_river_entry

    eng = engine()
    session = eng.create_session(
        "fd-fireproof",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_river_type = "flame"
    session.fd_travel_mode = "boat"
    session.fd_boat_status = "ok"
    session.fd_boat_fireproof = True
    monkeypatch.setattr("app.engine.forsaken_depths_river.roll_d6", lambda: 6)
    apply_flame_river_entry(session, hcl=5, show_rolls=True)
    assert session.fd_boat_status == "ok"
    assert session.fd_travel_mode == "boat"


def test_fd_waste_of_time_skips_next_hazard(monkeypatch) -> None:
    from app.engine.forsaken_depths_river import fd_on_waste_of_time_hazard

    eng = engine()
    session = eng.create_session(
        "fd-waste",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_river_type = "death"
    tile = TileState(
        id="waste-skip",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="River stretch",
        description="Test",
        tile_catalog="forsaken_depths_rivers",
    )
    fd_on_waste_of_time_hazard(session, show_rolls=True)
    assert session.fd_waste_of_time_skip_hazard_stretches == 2
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    eng._fd_on_river_stretch_entered(session, tile, show_rolls=True)
    assert session.fd_waste_of_time_skip_hazard_stretches == 1
    assert not any("River hazard:" in entry for entry in session.log)


def test_fd_disembark_at_bridge() -> None:
    from app.engine.forsaken_depths_river import fd_disembark_at_bridge

    session = engine().create_session(
        "fd-bridge",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.tile_catalog = "forsaken_depths_rivers"
    session.fd_travel_mode = "boat"
    tile = TileState(
        id="bridge",
        x=0,
        y=0,
        tile_key="15",
        tile_type="room",
        title="Bridge stretch",
        description="Test",
        tile_catalog="forsaken_depths_rivers",
        room_codes=["B"],
    )
    assert fd_disembark_at_bridge(session, tile, show_rolls=True)
    assert session.fd_travel_mode == "foot"


def test_fd_ghost_citadel_prefers_oversized_tiles() -> None:
    eng = engine()
    session = eng.create_session(
        "fd-ghost-tiles",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
    )
    session.fd_side_sheet_active = True
    session.fd_side_sheet_kind = "citadel"
    session.fd_citadel_type = "ghost_citadel"
    keys = eng._generated_placement_attempt_keys(session)
    tiles = eng._tiles_for_session(session)
    first_area = tiles[keys[0]].footprint_width * tiles[keys[0]].footprint_height
    assert first_area >= 40
