from __future__ import annotations

from pathlib import Path

from datetime import datetime, timezone

from app.engine.magic_items import (
    consume_magic_item_charge,
    find_magic_item,
    parse_charged_magic_item,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def test_parse_wand_of_sleep() -> None:
    parsed = parse_charged_magic_item("Wand of Sleep (3 charges)")
    assert parsed is not None
    assert parsed.spell_name == "Sleep"
    assert parsed.charges == 3


def test_parse_fireball_staff() -> None:
    parsed = parse_charged_magic_item("Fireball Staff (2 charges)")
    assert parsed is not None
    assert parsed.spell_name == "Fireball"
    assert parsed.charges == 2


def test_consume_magic_item_charge() -> None:
    updated = consume_magic_item_charge("Wand of Sleep (3 charges)")
    assert updated == "Wand of Sleep (2 charges)"
    spent = consume_magic_item_charge("Wand of Sleep (1 charge)")
    assert spent is None


def test_use_magic_item_in_combat() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    foe = EnemyState(id="f1", name="Goblin", category="minions", level=2, life=3, max_life=3)
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="A room.",
        enemies=[foe],
    )
    wizard = PartyMemberState(
        character_id="w1",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=3,
        xp=0,
        gold=0,
        current_life=8,
        max_life=8,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        inventory=["Fireball Staff (2 charges)"],
        spells=["Protection"],
    )
    now = datetime.now(timezone.utc).isoformat()
    session = SessionState(
        id="s1",
        party_id="p1",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[wizard],
        map_state=MapState(width=20, height=20, tiles=[tile], current_tile_id="t1"),
        created_at=now,
        updated_at=now,
    )
    engine.advance(
        session,
        "use_magic_item",
        character_id="w1",
        spell_name="Fireball",
        item_name="Fireball Staff (2 charges)",
        foe_id="f1",
        spell_target_mode="single",
    )
    assert find_magic_item(wizard.inventory, "Fireball") == "Fireball Staff (1 charge)"
    assert any("Fireball" in line for line in session.log)
    assert any("from magic item" in line for line in session.log)
