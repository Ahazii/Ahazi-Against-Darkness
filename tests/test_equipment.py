from __future__ import annotations

from pathlib import Path

from app.engine.combat import CombatContext, _defense_bonus
from app.engine.inventory import is_over_encumbered, weapon_carry_slots
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.weapons import infer_default_weapons, select_melee_weapon, select_missile_weapon, weapon_item_slots
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def member(**overrides) -> PartyMemberState:
    base = {
        "character_id": "hero",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 3,
        "xp": 0,
        "gold": 0,
        "current_life": 4,
        "max_life": 4,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "inventory": ["Dagger", "Heavy weapon"],
        "default_melee_weapon": "Dagger",
        "default_missile_weapon": None,
    }
    base.update(overrides)
    return PartyMemberState(**base)


def test_infer_default_weapons() -> None:
    melee, missile = infer_default_weapons(["Bow", "Hand weapon", "Shield"])
    assert missile == "Bow"
    assert melee == "Hand weapon"


def test_default_melee_weapon_is_used() -> None:
    hero = member(default_melee_weapon="Dagger")
    chosen = select_melee_weapon(hero, None)
    assert chosen is not None
    assert chosen.item == "Dagger"


def test_wielded_weapon_overrides_default() -> None:
    hero = member(default_melee_weapon="Dagger")
    chosen = select_melee_weapon(hero, None, wielded="Heavy weapon")
    assert chosen is not None
    assert chosen.item == "Heavy weapon"


def test_default_missile_weapon_is_used() -> None:
    hero = member(inventory=["Bow", "Hand weapon"], default_missile_weapon="Bow")
    chosen = select_missile_weapon(hero)
    assert chosen is not None
    assert chosen.item == "Bow"


def test_two_handed_weapon_counts_as_two_slots() -> None:
    assert weapon_item_slots("Heavy weapon") == 2
    assert weapon_item_slots("Hand weapon") == 1
    assert weapon_carry_slots(["Heavy weapon", "Dagger"]) == 3


def test_over_encumbered_weapon_slots() -> None:
    hero = member(inventory=["Heavy weapon", "Hand weapon", "Dagger"], gold=0)
    assert weapon_carry_slots(hero.inventory) == 4
    assert is_over_encumbered(hero)


def test_over_encumbered_applies_defense_penalty() -> None:
    hero = member(gold=250, inventory=["Shield"])
    enemy = EnemyState(id="e", name="Goblin", category="minions", level=3, life=3, max_life=3)
    modifier, _ = _defense_bonus(hero, enemy, context=CombatContext(), withdraw=False)
    unencumbered = member(gold=10, inventory=["Shield"])
    clean_modifier, _ = _defense_bonus(unencumbered, enemy, context=CombatContext(), withdraw=False)
    assert modifier == clean_modifier - 1


def test_set_default_weapon_in_exploration() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())
    hero = member(inventory=["Dagger", "Hand weapon"], default_melee_weapon="Dagger")
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    engine.advance(
        session,
        "set_default_weapon",
        character_id="hero",
        item_name="Hand weapon",
        weapon_kind="melee",
    )
    assert hero.default_melee_weapon == "Hand weapon"
    assert any("sets default melee" in line for line in session.log)


def test_swap_weapon_runs_foe_phase(monkeypatch) -> None:
    from app.engine import combat

    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda level: (6, [6]))
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())
    hero = member(inventory=["Dagger", "Heavy weapon"], default_melee_weapon="Dagger")
    goblin = EnemyState(id="g", name="Goblin", category="minions", level=3, life=3, max_life=3)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        enemies=[goblin],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        wielded_melee_weapons={"hero": "Dagger"},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    engine.advance(session, "swap_weapon", character_id="hero", item_name="Heavy weapon")
    assert session.wielded_melee_weapons["hero"] == "Heavy weapon"
    assert any("spends the turn drawing" in line for line in session.log)


def test_roster_weapon_defaults_api(monkeypatch) -> None:
    import importlib
    from tempfile import TemporaryDirectory

    from fastapi.testclient import TestClient

    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        warrior = client.post("/api/characters", json={"name": "War", "class_id": "warrior"}).json()
        assert warrior["default_melee_weapon"] == "Hand weapon"

        empty = client.post(f"/api/characters/{warrior['id']}/weapon-defaults", json={})
        assert empty.status_code == 400

        invalid = client.post(
            f"/api/characters/{warrior['id']}/weapon-defaults",
            json={"default_melee_weapon": "Bow"},
        )
        assert invalid.status_code == 400

        ranger = client.post("/api/characters", json={"name": "Ran", "class_id": "ranger"}).json()
        response = client.post(
            f"/api/characters/{ranger['id']}/weapon-defaults",
            json={"default_melee_weapon": "Hand weapon", "default_missile_weapon": "Bow"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["default_melee_weapon"] == "Hand weapon"
        assert body["default_missile_weapon"] == "Bow"
