from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.engine.class_combat import armor_defense_bonus, defense_modifier, save_modifier
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.weapons import weapon_attack_modifier, weapon_profile
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _hero(**overrides) -> PartyMemberState:
    data = {
        "character_id": "h1",
        "name": "Abyss Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 3,
        "xp": 0,
        "gold": 0,
        "current_life": 6,
        "max_life": 8,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
        "inventory": ["Hand weapon"],
    }
    data.update(overrides)
    return PartyMemberState(**data)


def _session(member: PartyMemberState, enemies: list[EnemyState] | None = None, *, mode: str = "exploration") -> SessionState:
    now = datetime.now(timezone.utc).isoformat()
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="A room.",
        enemies=enemies or [],
    )
    return SessionState(
        id="s1",
        party_id="p1",
        adventure_id="random",
        adventure_type="random",
        mode=mode,
        party=[member],
        map_state=MapState(width=20, height=20, tiles=[tile], current_tile_id="t1"),
        created_at=now,
        updated_at=now,
    )


def test_abyss_passive_defense_and_save_items() -> None:
    undead = EnemyState(id="u1", name="Crypt Undead", category="boss", level=5, life=4, max_life=4, tags=["undead"])
    vampire = EnemyState(id="v1", name="Vampire", category="boss", level=6, life=4, max_life=4, tags=["undead"])
    hero = _hero(inventory=["Amulet of Protection versus Undead", "Cross against Vampires", "Light armor"])

    assert defense_modifier(hero, undead) == 1
    assert defense_modifier(hero, vampire) == 3
    assert save_modifier(hero, save_label="undead gaze", enemies=[undead]) == 1


def test_abyss_magic_armor_suppresses_mundane_armor_slots() -> None:
    hero = _hero(inventory=["Heavy armor", "Shield", "Elfin Chain Mail", "Magic Shield", "Ring of Defense"])

    assert armor_defense_bonus(hero) == 5


def test_abyss_weapons_parse_and_apply_bonus() -> None:
    werewolf = EnemyState(id="w1", name="Werewolf", category="boss", level=5, life=4, max_life=4, tags=["lycanthrope"])
    hero = _hero(inventory=["Silver Weapon", "Baton of Righteousness", "Blessed Stakes"])

    silver = weapon_profile("Silver Weapon")
    baton = weapon_profile("Baton of Righteousness")
    stake = weapon_profile("Blessed Stakes")

    assert silver is not None and silver.slashing
    assert baton is not None and baton.crushing
    assert stake is not None and stake.light
    assert weapon_attack_modifier(silver, werewolf, member=hero) == 1


def test_use_elven_bread_heals_once_per_game() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    hero = _hero(class_id="elf", class_name="Elf", current_life=3, inventory=["Elven Bread", "Elven Bread"])
    session = _session(hero)

    engine.advance(session, "use_abyss_item", character_id="h1", item_name="Elven Bread")
    engine.advance(session, "use_abyss_item", character_id="h1", item_name="Elven Bread")

    assert hero.current_life == 6
    assert hero.inventory == ["Elven Bread"]
    assert any("already benefited" in line for line in session.log)


def test_philter_fire_breath_wounds_major_foe() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    foe = EnemyState(id="f1", name="Abyss Weird", category="weird", level=5, life=4, max_life=4)
    hero = _hero(inventory=["Philter of Fire Breathing"])
    session = _session(hero, [foe], mode="combat")

    engine.advance(session, "use_abyss_item", character_id="h1", item_name="Philter of Fire Breathing")
    engine.advance(session, "use_abyss_item", character_id="h1", treasure_outcome_choice="fire_breath", foe_id="f1")

    assert foe.life == 2
    assert "Abyss Fire Breathing" not in hero.statuses
    assert any("breathes fire" in line for line in session.log)


def test_parchment_of_banishing_consumes_item_and_damages_undead() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    foe = EnemyState(id="u1", name="Undead Horror", category="boss", level=6, life=3, max_life=3, tags=["undead"])
    hero = _hero(class_id="cleric", class_name="Cleric", inventory=["Parchment of Banishing"])
    session = _session(hero, [foe], mode="combat")

    engine.advance(session, "use_abyss_item", character_id="h1", item_name="Parchment of Banishing", foe_id="u1")

    assert foe.life == 1
    assert "Parchment of Banishing" not in hero.inventory


def test_ring_wish_heals_and_decrements_wishes() -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    hero = _hero(current_life=2, madness=2, inventory=["Ring of Three Wishes (2 wishes)"])
    session = _session(hero)

    engine.advance(
        session,
        "use_abyss_item",
        character_id="h1",
        item_name="Ring of Three Wishes (2 wishes)",
        treasure_outcome_choice="heal",
    )

    assert hero.current_life == hero.max_life
    assert hero.madness == 0
    assert hero.inventory == ["Ring of Three Wishes (1 wish)"]


def test_medallion_of_snake_charming_can_end_combat_peacefully(monkeypatch) -> None:
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    foe = EnemyState(id="s1", name="Snake Minions", category="minions", level=5, life=3, max_life=3, tags=["snake"])
    hero = _hero(level=4, inventory=["Medallion of Snake Charming"])
    session = _session(hero, [foe], mode="combat")
    monkeypatch.setattr("app.engine.random_dungeon.roll_die", lambda sides: 4)

    engine.advance(session, "use_abyss_item", character_id="h1", item_name="Medallion of Snake Charming", foe_id="s1")

    assert foe.life == 0
    assert session.mode == "exploration"
    assert any("friendly" in line for line in session.log)
