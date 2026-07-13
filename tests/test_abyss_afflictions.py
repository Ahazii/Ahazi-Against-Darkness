from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.engine.abyss_afflictions import (
    DARK_PLAGUE_STATUS,
    LYCANTHROPY_IMMUNITY_STATUS,
    LYCANTHROPY_STATUS,
    VAMPIRE_RISE_PENDING_STATUS,
    resolve_lycanthropy_exposures,
    tick_dark_plague_on_room_entry,
)
from app.engine.monster_template_effects import apply_member_level_loss
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.spells import resolve_spell_cast
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _hero(**overrides) -> PartyMemberState:
    data = {
        "character_id": "h1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 3,
        "xp": 0,
        "gold": 0,
        "bank_gold": 0,
        "current_life": 7,
        "max_life": 7,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
        "inventory": ["Hand weapon"],
        "statuses": [],
    }
    data.update(overrides)
    return PartyMemberState(**data)


def _tile(**overrides) -> TileState:
    data = {
        "id": "t1",
        "x": 0,
        "y": 0,
        "tile_key": "11",
        "tile_type": "room",
        "title": "Room",
        "description": "A room.",
    }
    data.update(overrides)
    return TileState(**data)


def _session(party: list[PartyMemberState], tile: TileState | None = None, **overrides) -> SessionState:
    now = datetime.now(timezone.utc).isoformat()
    tile = tile or _tile()
    data = {
        "id": "s1",
        "party_id": "p1",
        "adventure_id": "random",
        "adventure_type": "random",
        "mode": "exploration",
        "party": party,
        "map_state": MapState(width=20, height=20, tiles=[tile], current_tile_id=tile.id),
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SessionState(**data)


def test_dark_plague_ticks_and_spreads_room_by_room(monkeypatch) -> None:
    infected = _hero(character_id="h1", name="Carrier", current_life=5, statuses=[DARK_PLAGUE_STATUS])
    exposed = _hero(character_id="h2", name="Companion")
    tile = _tile(title="North Room")
    session = _session([infected, exposed], tile)
    rolls = iter([1])
    saves = iter([(4, [4])])
    monkeypatch.setattr("app.engine.abyss_afflictions.roll_die", lambda sides: next(rolls))
    monkeypatch.setattr("app.engine.abyss_afflictions.roll_exploding_for_level", lambda member, **kwargs: next(saves))

    log = tick_dark_plague_on_room_entry(session, tile, show_rolls=True)

    assert infected.current_life == 4
    assert DARK_PLAGUE_STATUS in exposed.statuses
    assert any("Dark Plague spread" in line for line in log)


def test_dark_plague_save_does_not_grant_an_unprinted_immunity(monkeypatch) -> None:
    infected = _hero(character_id="h1", name="Carrier", statuses=[DARK_PLAGUE_STATUS])
    exposed = _hero(character_id="h2", name="Companion")
    tile = _tile()
    session = _session([infected, exposed], tile)
    monkeypatch.setattr("app.engine.abyss_afflictions.roll_die", lambda sides: 2)
    monkeypatch.setattr("app.engine.abyss_afflictions.roll_exploding_for_level", lambda member, **kwargs: (10, [10]))

    tick_dark_plague_on_room_entry(session, tile, show_rolls=False)

    assert DARK_PLAGUE_STATUS not in exposed.statuses
    assert all("dark plague immunity" not in status.lower() for status in exposed.statuses)


def test_blessing_uses_abyss_dark_plague_cure_roll(monkeypatch) -> None:
    caster = _hero(character_id="c", name="Cleric", class_id="cleric", class_name="Cleric", level=3)
    target = _hero(character_id="t", name="Target", statuses=[DARK_PLAGUE_STATUS])
    monkeypatch.setattr("app.engine.abyss_afflictions.roll_exploding_for_level", lambda member, **kwargs: (7, [7]))

    outcome = resolve_spell_cast(
        "Blessing",
        caster,
        [caster, target],
        [],
        target_character_id="t",
        show_rolls=True,
        session=_session([caster, target]),
    )

    assert DARK_PLAGUE_STATUS not in target.statuses
    assert all("dark plague immunity" not in status.lower() for status in target.statuses)
    assert any("Dark Plague Blessing" in line for line in outcome.log)


def test_failed_dark_plague_blessing_is_wasted(monkeypatch) -> None:
    caster = _hero(character_id="c", name="Cleric", class_id="cleric", class_name="Cleric", level=2)
    target = _hero(character_id="t", name="Target", statuses=[DARK_PLAGUE_STATUS, "Cursed"])
    monkeypatch.setattr("app.engine.abyss_afflictions.roll_exploding_for_level", lambda member, **kwargs: (2, [2]))

    outcome = resolve_spell_cast(
        "Blessing",
        caster,
        [caster, target],
        [],
        target_character_id="t",
        show_rolls=True,
        session=_session([caster, target]),
    )

    assert DARK_PLAGUE_STATUS in target.statuses
    assert "Cursed" in target.statuses
    assert any("fails to cure" in line for line in outcome.log)


def test_elven_bread_cures_dark_plague_without_granting_immunity() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    hero = _hero(inventory=["Elven Bread"], statuses=[DARK_PLAGUE_STATUS])
    session = _session([hero])

    engine.advance(session, "use_abyss_item", character_id="h1", item_name="Elven Bread")

    assert DARK_PLAGUE_STATUS not in hero.statuses
    assert all("dark plague immunity" not in status.lower() for status in hero.statuses)


def test_lycanthropy_exposure_resolves_and_drops_silver_and_lantern(monkeypatch) -> None:
    hero = _hero(
        statuses=["Lycanthropy exposure"],
        inventory=["Silver Weapon", "Lantern", "Rope"],
    )
    tile = _tile()
    session = _session([hero], tile)
    monkeypatch.setattr("app.engine.abyss_afflictions.roll_exploding_for_level", lambda member, **kwargs: (1, [1]))

    log = resolve_lycanthropy_exposures(session, tile, show_rolls=True)

    assert LYCANTHROPY_STATUS in hero.statuses
    assert "Silver Weapon" not in hero.inventory
    assert "Lantern" not in hero.inventory
    assert tile.treasure_items == ["Silver Weapon", "Lantern"]
    assert any("contracts Lycanthropy" in line for line in log)


def test_monastery_treatment_spends_gold_cures_and_can_grant_immunity(monkeypatch) -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    hero = _hero(statuses=[LYCANTHROPY_STATUS], gold=150, bank_gold=300)
    session = _session([hero], camped_outside=True)
    monkeypatch.setattr("app.engine.abyss_afflictions.roll_exploding_for_level", lambda member, **kwargs: (8, [6, 2]))

    engine.advance(session, "treat_lycanthropy", character_id="h1")

    assert hero.gold == 50
    assert hero.bank_gold == 0
    assert LYCANTHROPY_STATUS not in hero.statuses
    assert LYCANTHROPY_IMMUNITY_STATUS in hero.statuses


def test_vampire_level_drain_death_blocks_resurrection() -> None:
    hero = _hero(level=1, current_life=1, max_life=5)
    session = _session([hero], camped_outside=True, fallen_outside_character_ids=["h1"])

    log = apply_member_level_loss(hero, source="Minor Vampire's level drain")
    RandomDungeonEngine(rules=None, asset_dir=Path()).advance(
        session,
        "attempt_resurrection",
        target_character_id="h1",
    )

    assert VAMPIRE_RISE_PENDING_STATUS in hero.statuses
    assert hero.current_life == 0
    assert any("will rise as a vampire" in line for line in log)
    assert any("cannot be resurrected until the sire vampire is destroyed" in line for line in session.log)
