"""Tests for the Capture reaction mechanic and clue-based hideout rescue."""
from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.secrets import secret_by_id
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, ExitState, MapState, PartyMemberState, SessionState, TileState


def _rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def _engine() -> RandomDungeonEngine:
    root = Path(__file__).resolve().parents[1]
    return RandomDungeonEngine(_rules(), root / "assets")


def _member(cid: str, name: str, order: int, *, level: int = 3, life: int = 5, gold: int = 20) -> PartyMemberState:
    return PartyMemberState(
        character_id=cid,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=level,
        xp=0,
        gold=gold,
        current_life=life,
        max_life=life,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=order,
    )


def _session(
    *,
    party: list[PartyMemberState],
    current: str = "t1",
    tiles: list[TileState] | None = None,
    mode: str = "exploration",
) -> SessionState:
    tile_list = tiles or [
        TileState(id="t1", x=0, y=0, tile_key="11", tile_type="room", title="Hall", description="A hall"),
    ]
    return SessionState(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        mode=mode,
        party=party,
        map_state=MapState(tiles=tile_list, current_tile_id=current),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _enemy(eid: str, name: str, level: int = 2, life: int = 3) -> EnemyState:
    return EnemyState(
        id=eid,
        name=name,
        category="minion",
        level=level,
        life=life,
        max_life=life,
        attacks=1,
    )


# ---------------------------------------------------------------------------
# 1. "someone_imprisoned" secret definition
# ---------------------------------------------------------------------------


def test_someone_imprisoned_secret_exists() -> None:
    secret = secret_by_id("someone_imprisoned")
    assert secret is not None
    assert secret.implementation == "wired"
    assert "imprisoned" in secret.label.lower() or "imprisoned" in secret.summary.lower()


# ---------------------------------------------------------------------------
# 2. Capture reaction sets capture_mode and capture_foe_name
# ---------------------------------------------------------------------------


def test_capture_reaction_sets_capture_mode() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1)
    goblin = _enemy("g1", "Goblins", level=2, life=2)
    tile = TileState(
        id="t1", x=0, y=0, tile_key="11", tile_type="room",
        title="Room", description="D", enemies=[goblin],
    )
    session = _session(party=[hero], tiles=[tile], mode="combat")
    session.reaction_pending = True
    # Inject capture row directly via build_reaction_outcome path
    from app.engine.reactions import ReactionOutcome

    outcome = ReactionOutcome(
        key="capture",
        result="The minions try to take captives!",
        foes_first=True,
        ends_combat=False,
    )
    # Call the private handler via the action dispatch
    from unittest.mock import patch

    with patch("app.engine.random_dungeon.build_reaction_outcome", return_value=outcome):
        engine.advance(session, "check_reaction", show_rolls=False)

    assert session.capture_mode is True
    assert session.capture_foe_name == "Goblins"
    assert session.foes_strike_first is True
    assert any("captive" in entry.lower() for entry in session.log)


# ---------------------------------------------------------------------------
# 3. Hero knocked to 0 Life in capture mode → captured, not fallen
# ---------------------------------------------------------------------------


def test_hero_knocked_out_in_capture_mode_becomes_captive() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1, life=1)
    hero.inventory = ["Hand weapon", "Shield", "Rope"]
    hero.default_melee_weapon = "Hand weapon"
    goblin = _enemy("g1", "Goblins", level=2, life=3)
    tile = TileState(
        id="t1", x=0, y=0, tile_key="11", tile_type="room",
        title="Room", description="D", enemies=[goblin],
    )
    session = _session(party=[hero], tiles=[tile], mode="combat")
    session.capture_mode = True
    session.capture_foe_name = "Goblins"
    session.capture_origin_tile_id = "t1"

    # Directly exercise _resolve_captures
    session.party[0].current_life = 0
    session.map_state.tiles[0].enemies = [goblin]
    fallen = engine._resolve_captures(session, session.map_state.tiles[0], ["h1"])

    assert "h1" in session.captured_character_ids, "hero should be marked captured"
    assert "h1" not in fallen, "captured hero should not appear in fallen list"
    assert hero.inventory == []
    assert hero.default_melee_weapon is None
    assert session.captured_stripped_equipment["h1"].inventory == ["Hand weapon", "Shield", "Rope"]
    assert any("captive" in entry.lower() or "knock" in entry.lower() for entry in session.log)
    assert any("equipment" in entry.lower() for entry in session.log)


# ---------------------------------------------------------------------------
# 4. find_captive_hideout: needs 3 clues, generates hideout tile and exit
# ---------------------------------------------------------------------------


def test_find_captive_hideout_requires_3_clues() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1)
    session = _session(party=[hero])
    session.captured_character_ids = ["captive1"]
    session.capture_foe_name = "Goblins"
    session.clues_found = 1
    session.party[0].clues = 1

    engine._find_captive_hideout(session, "h1", show_rolls=False)

    assert session.capture_hideout_tile_id is None, "no hideout without 3 Clues"
    assert any("clue" in entry.lower() or "need" in entry.lower() for entry in session.log)


def test_find_captive_hideout_spends_clues_and_creates_tile() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1)
    goblin = _enemy("g1", "Goblins", level=2, life=2)
    tile = TileState(
        id="t1", x=0, y=0, tile_key="11", tile_type="room",
        title="Hall", description="D",
        enemies=[goblin],
        defeated_enemies=[goblin],
    )
    session = _session(party=[hero], tiles=[tile])
    session.captured_character_ids = ["captive1"]
    session.capture_foe_name = "Goblins"
    session.clues_found = 3
    session.party[0].clues = 3

    tiles_before = len(session.map_state.tiles)
    engine._find_captive_hideout(session, "h1", show_rolls=False)

    assert session.capture_hideout_tile_id is not None, "hideout tile ID must be set"
    assert len(session.map_state.tiles) == tiles_before + 1, "a new hideout tile must be added"
    hideout = next(t for t in session.map_state.tiles if t.id == session.capture_hideout_tile_id)
    assert hideout.title == "Captive Hideout"
    assert len(hideout.enemies) >= 2, "hideout must have guards"
    assert session.clues_found == 0, "3 Clues should have been spent"
    # Origin tile should have an exit pointing to the hideout
    origin = session.map_state.tiles[0]
    assert any(e.destination_tile_id == hideout.id for e in origin.exits), "origin must have exit to hideout"
    assert any("hideout" in entry.lower() for entry in session.log)


# ---------------------------------------------------------------------------
# 5. pay_captive_ransom: frees captives when at hideout with enough gold
# ---------------------------------------------------------------------------


def test_pay_captive_ransom_frees_captives_and_deducts_gold() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1, gold=200)
    captive = _member("c1", "Brynn", 2, life=0, gold=0)
    captive.current_life = 0
    hideout_tile = TileState(
        id="hideout", x=5, y=0, tile_key="11", tile_type="room",
        title="Captive Hideout", description="Cave",
    )
    origin_tile = TileState(id="t1", x=0, y=0, tile_key="11", tile_type="room", title="Hall", description="D")
    session = _session(party=[hero, captive], tiles=[origin_tile, hideout_tile], current="hideout")
    session.captured_character_ids = ["c1"]
    session.captured_stripped_equipment["c1"] = {
        "inventory": ["Hand weapon", "Lantern"],
        "default_melee_weapon": "Hand weapon",
    }
    session.capture_foe_name = "Goblins"
    session.capture_hideout_tile_id = "hideout"

    from unittest.mock import patch

    with patch("app.engine.random_dungeon.roll_d3", return_value=2):
        engine._pay_captive_ransom(session, show_rolls=False)

    assert session.captured_character_ids == [], "captives should be freed"
    assert captive.current_life == 2, "captive restored to d3 Life"
    assert captive.inventory == ["Hand weapon", "Lantern"]
    assert captive.default_melee_weapon == "Hand weapon"
    assert session.captured_stripped_equipment == {}
    assert hero.gold < 200, "ransom gold deducted from party"
    assert session.capture_hideout_tile_id is None, "hideout state cleared"


def test_clearing_hideout_restores_stripped_equipment() -> None:
    engine = _engine()
    captive = _member("c1", "Brynn", 1, life=0, gold=0)
    hideout_tile = TileState(
        id="hideout", x=5, y=0, tile_key="11", tile_type="room",
        title="Captive Hideout", description="Cave",
    )
    session = _session(party=[captive], tiles=[hideout_tile], current="hideout")
    session.captured_character_ids = ["c1"]
    session.captured_stripped_equipment["c1"] = {
        "inventory": ["Bow", "Bandage"],
        "default_missile_weapon": "Bow",
    }

    from unittest.mock import patch

    with patch("app.engine.random_dungeon.roll_d3", return_value=3):
        engine._rescue_captives(session, hideout_tile, show_rolls=True)

    assert session.captured_character_ids == []
    assert session.captured_stripped_equipment == {}
    assert captive.current_life == 3
    assert captive.inventory == ["Bow", "Bandage"]
    assert captive.default_missile_weapon == "Bow"


def test_pay_captive_ransom_fails_if_not_at_hideout() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1, gold=200)
    captive = _member("c1", "Brynn", 2, life=0)
    captive.current_life = 0
    session = _session(party=[hero, captive])
    session.captured_character_ids = ["c1"]
    session.capture_hideout_tile_id = "hideout"

    engine._pay_captive_ransom(session, show_rolls=False)

    assert any("must be at" in entry.lower() or "hideout" in entry.lower() for entry in session.log)
    assert session.captured_character_ids == ["c1"], "captives not freed when not at hideout"


# ---------------------------------------------------------------------------
# 6. Frontend JS regression: renderCapturePanel functions present in app.js
# ---------------------------------------------------------------------------


def test_capture_ui_functions_present_in_app_js() -> None:
    app_js = Path(__file__).resolve().parents[1] / "src" / "app" / "static" / "app.js"
    js = app_js.read_text(encoding="utf-8")
    assert "renderCapturePanel" in js, "renderCapturePanel function must exist"
    assert "isCapturedHero" in js, "isCapturedHero helper must exist"
    assert "find_captive_hideout" in js, "find_captive_hideout action must be dispatched in JS"
    assert "pay_captive_ransom" in js, "pay_captive_ransom action must be dispatched in JS"
    assert "party-sheet-captured" in js, "captured CSS class must be applied"


# ---------------------------------------------------------------------------
# 7. Minion reaction table contains capture key
# ---------------------------------------------------------------------------


def test_minion_reaction_table_has_capture() -> None:
    import json

    tables_path = Path(__file__).resolve().parents[1] / "data" / "rules" / "dungeon_tables.json"
    tables = json.loads(tables_path.read_text(encoding="utf-8"))
    minion_table = tables.get("minion_reaction_table", [])
    keys = {row["key"] for row in minion_table}
    assert "capture" in keys, "capture must be a possible minion reaction"
