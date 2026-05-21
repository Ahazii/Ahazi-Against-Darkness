from __future__ import annotations

from pathlib import Path

from app.engine import spells
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.scrolls import find_scroll_item, is_scroll_item, scroll_spell_name
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, ExitState, MapState, PartyMemberState, SessionState, TileState


def wizard(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="wiz",
        name="Marius",
        class_id="wizard",
        class_name="Wizard",
        level=3,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Escape", "Fireball"],
        inventory=["Scroll of Sleep"],
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def session_with_tile(*, mode: str = "exploration", enemies: list[EnemyState] | None = None) -> SessionState:
    entrance = TileState(
        id="entrance",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        objects=["Entrance"],
    )
    room = TileState(
        id="room",
        x=1,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        enemies=enemies or [],
    )
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode=mode,
        party=[wizard()],
        map_state=MapState(tiles=[entrance, room], current_tile_id="room"),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def test_escape_teleports_to_entrance() -> None:
    outcome = spells.resolve_spell_cast("Escape", wizard(), [wizard()], [], show_rolls=False)
    assert outcome.teleport_to_entrance is True
    assert outcome.combat_over is True


def test_scroll_item_parsing() -> None:
    assert is_scroll_item("Scroll of Fireball")
    assert scroll_spell_name("Scroll of Fireball") == "Fireball"
    assert scroll_spell_name("Bark: Disperse Vermin") == "Disperse Vermin"


def test_burn_scroll_casts_without_expending_slot(monkeypatch) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    member = wizard(spells=[], inventory=["Scroll of Sleep"])
    foe = EnemyState(id="g", name="Goblin", category="minions", level=3, life=1, max_life=1)
    session = session_with_tile(mode="combat", enemies=[foe])
    session.party = [member]
    monkeypatch.setattr(spells, "roll_exploding_d6", lambda: (6, [6]))
    engine.advance(session, "burn_scroll", character_id="wiz", spell_name="Sleep")
    assert "Scroll of Sleep" not in member.inventory
    assert "Sleep" not in session.expended_spells.get("wiz", [])


def test_sealed_door_spellcast_opens(monkeypatch) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = session_with_tile()
    tile = session.map_state.tiles[1]
    tile.exits = [
        ExitState(
            id="door-n",
            direction="north",
            kind="door",
            door_type="sealed",
            door_level=4,
            door_open=False,
        )
    ]
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_d6", lambda: (5, [5]))
    engine.advance(session, "spellcast_door", exit_id="door-n", character_id="wiz")
    assert tile.exits[0].door_open is True


def test_sealed_door_rejects_non_spellcaster() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = session_with_tile()
    session.party = [
        PartyMemberState(
            character_id="war",
            name="Warrior",
            class_id="warrior",
            class_name="Warrior",
            level=3,
            xp=0,
            gold=0,
            current_life=5,
            max_life=5,
            attack_bonus=0,
            defense_bonus=0,
            save_bonus=0,
        )
    ]
    tile = session.map_state.tiles[1]
    tile.exits = [
        ExitState(
            id="door-n",
            direction="north",
            kind="door",
            door_type="sealed",
            door_level=4,
            door_open=False,
        )
    ]
    engine.advance(session, "spellcast_door", exit_id="door-n", character_id="war")
    assert tile.exits[0].door_open is False
    assert any("spellcaster" in entry.lower() for entry in session.log)


def test_druid_disperse_vermin(monkeypatch) -> None:
    monkeypatch.setattr(spells, "roll_exploding_d6", lambda: (4, [4]))
    druid = wizard(
        character_id="d",
        name="Druid",
        class_id="druid",
        class_name="Druid",
        spells=["Disperse Vermin"],
    )
    vermin = EnemyState(id="r", name="Rat", category="vermin", level=2, life=1, max_life=1)
    outcome = spells.resolve_spell_cast("Disperse Vermin", druid, [druid], [vermin], show_rolls=False)
    assert vermin.life == 0
    assert outcome.combat_over is True
