"""Line-by-line Secrets player-text and constraint compliance tests."""
from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def _engine() -> RandomDungeonEngine:
    root = Path(__file__).resolve().parents[1]
    return RandomDungeonEngine(_rules(), root / "assets")


def _member(
    cid: str,
    name: str,
    order: int,
    *,
    level: int = 3,
    life: int = 6,
    clues: int = 0,
    class_id: str = "warrior",
    class_name: str = "Warrior",
) -> PartyMemberState:
    return PartyMemberState(
        character_id=cid,
        name=name,
        class_id=class_id,
        class_name=class_name,
        level=level,
        xp=0,
        gold=200,
        clues=clues,
        current_life=life,
        max_life=life,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
        marching_order=order,
    )


def _session(*, party: list[PartyMemberState], tile: TileState, mode: str = "exploration") -> SessionState:
    return SessionState(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        mode=mode,
        party=party,
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _contains(log: list[str], needle: str) -> bool:
    n = needle.lower()
    return any(n in line.lower() for line in log)


def test_hidden_treasure_secret_uses_required_text() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1, clues=3)
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Hall",
        description="A room",
        content_key="empty",
    )
    session = _session(party=[hero], tile=tile)
    session.clues_found = 3

    engine.advance(
        session,
        "reveal_secret_with_clues",
        character_id="h1",
        secret_id="hidden_treasure_location",
        show_rolls=False,
    )

    assert _contains(
        session.log,
        "Here a hidden treasure can be revealed by speaking a secret password.",
    )
    assert _contains(session.log, "A niche opens in a wall")


def test_magic_item_location_secret_uses_required_text() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1)
    hero.secrets = ["magic_item_location"]
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Hall",
        description="A room",
        content_key="empty",
    )
    session = _session(party=[hero], tile=tile, mode="exploration")

    engine.advance(
        session,
        "use_secret",
        character_id="h1",
        secret_id="magic_item_location",
        show_rolls=False,
    )

    assert _contains(session.log, "You recognize this location as a hidden magic item cache.")
    assert _contains(session.log, "It can be revealed by speaking the correct password")


def test_scroll_location_secret_uses_required_text() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1)
    hero.secrets = ["scroll_location"]
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Hall",
        description="A room",
        content_key="empty",
    )
    session = _session(party=[hero], tile=tile, mode="exploration")

    engine.advance(
        session,
        "use_secret",
        character_id="h1",
        secret_id="scroll_location",
        item_name="scroll",
        show_rolls=False,
    )

    assert _contains(session.log, "Hidden in a niche, you find a scroll, piece of bark or prism")


def test_someone_imprisoned_blocked_without_adjacent_space() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1, clues=3)
    origin = TileState(id="t1", x=0, y=0, tile_key="11", tile_type="room", title="Hall", description="A room")
    east_block = TileState(id="e1", x=2, y=0, tile_key="11", tile_type="room", title="East", description="A room")
    south_block = TileState(id="s1", x=0, y=2, tile_key="11", tile_type="room", title="South", description="A room")
    session = SessionState(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        mode="exploration",
        party=[hero],
        map_state=MapState(tiles=[origin, east_block, south_block], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    session.clues_found = 3
    session.captured_character_ids = ["c1"]
    session.capture_foe_name = "Goblins"

    engine.advance(
        session,
        "reveal_secret_with_clues",
        character_id="h1",
        secret_id="someone_imprisoned",
        show_rolls=False,
    )

    assert session.capture_hideout_tile_id is None
    assert _contains(session.log, "needs free map space around the current tile to place a hideout")


def test_major_foe_hints_include_weakness_and_deal() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1, class_id="wizard", class_name="Wizard")
    hero.secrets = ["weakness_of_a_foe", "deal_with_a_foe"]
    boss = EnemyState(
        id="b1",
        name="Chaos Champion",
        category="boss",
        level=4,
        life=8,
        max_life=8,
        attacks=1,
        tags=[],
    )
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Boss Room",
        description="A threat",
        enemies=[boss],
        initial_enemy_count=1,
    )
    session = _session(party=[hero], tile=tile, mode="combat")

    hints = engine._secret_timing_hints(session, tile)

    assert any("has weakness of a foe" in hint.lower() for hint in hints)
    assert any("has deal with a foe" in hint.lower() for hint in hints)
