from __future__ import annotations

import json
from pathlib import Path

from app.engine.class_combat import save_modifier
from app.engine.expert_skill_effects import (
    arcane_tanner_hides_from_defeated,
    can_use_phasing_panther_escape,
)
from app.engine.equipment_shop import sell_quote
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.secrets import (
    is_chaos_fanatic,
    secret_defense_bonus,
    secret_save_bonus,
)
from app.rules.repository import RulesRepository
from app.schemas import Character, EnemyState, MapState, PartyMemberState, SessionState, TileState


def _engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")


def _catalog() -> dict:
    path = Path(__file__).resolve().parents[1] / "data" / "rules" / "equipment_shop.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _member(**overrides) -> PartyMemberState:
    base = {
        "character_id": "h",
        "name": "Hero",
        "class_id": "wizard",
        "class_name": "Wizard",
        "level": 6,
        "xp": 0,
        "max_life": 6,
        "current_life": 6,
        "gold": 0,
        "inventory": [],
        "marching_order": 1,
        "save_bonus": 0,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "spells": [],
        "statuses": [],
        "secrets": [],
    }
    base.update(overrides)
    return PartyMemberState(**base)


def _tile(**overrides) -> TileState:
    base = {
        "id": "t1",
        "x": 0,
        "y": 0,
        "tile_key": "11",
        "tile_type": "room",
        "title": "Room",
        "description": "A room.",
        "content_key": "encounter",
        "enemies": [],
        "exits": [],
    }
    base.update(overrides)
    return TileState(**base)


def _session(member: PartyMemberState, tile: TileState, *, mode: str = "exploration") -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode=mode,
        party=[member],
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_dragon_hide_drops_from_slain_dragon() -> None:
    dragon = EnemyState(id="d1", name="Young Dragon", category="boss", level=5, life=0, max_life=5, tags=["dragon"])
    items, log = arcane_tanner_hides_from_defeated([dragon], roll_fn=lambda: 6)
    assert items == ["Dragon Hide"]
    assert any("Dragon Hide" in line for line in log)


def test_panther_hide_can_drop_from_weird_monster() -> None:
    weird = EnemyState(id="w1", name="Doppelganger", category="weird", level=4, life=0, max_life=4, tags=[])
    items, _ = arcane_tanner_hides_from_defeated([weird], roll_fn=lambda: 1)
    assert items == ["Panther Hide"]


def test_arcane_tanner_default_roll_d6_callable() -> None:
    weird = EnemyState(
        id="w1",
        name="Green Slime",
        category="weird",
        level=7,
        life=0,
        max_life=7,
        tags=["final_boss"],
    )
    arcane_tanner_hides_from_defeated([weird])


def test_panther_hide_default_roll_fn_does_not_require_sides() -> None:
    weird = EnemyState(id="w1", name="Green Slime", category="weird", level=7, life=0, max_life=7, tags=[])
    items, log = arcane_tanner_hides_from_defeated([weird], roll_fn=lambda: 2)
    assert items == ["Panther Hide"]
    assert any("Panther Hide" in line for line in log)
    items, _ = arcane_tanner_hides_from_defeated([weird], roll_fn=lambda: 3)
    assert items == []


def test_garment_resale_is_one_fifty_gp() -> None:
    catalog = _catalog()
    hero = Character(
        id="c1",
        name="Hero",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        max_life=1,
        current_life=1,
        inventory=["Phasing Panther Garment", "Dragon-Skin Garment"],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert sell_quote(hero, catalog, item_name="Phasing Panther Garment")["quote_gp"] == 150
    assert sell_quote(hero, catalog, item_name="Dragon-Skin Garment")["quote_gp"] == 150


def test_phasing_garment_escape_once_per_adventure() -> None:
    wizard = _member(inventory=["Phasing Panther Garment"])
    session = _session(wizard, _tile())
    assert can_use_phasing_panther_escape(wizard, session) is True
    session.expert_encounter_spent = {"h": ["phasing_panther_escape"]}
    assert can_use_phasing_panther_escape(wizard, session) is False
    barbarian = _member(class_id="barbarian", inventory=["Phasing Panther Garment"])
    assert can_use_phasing_panther_escape(barbarian, session) is False


def test_dragon_garment_save_bonus_vs_breath() -> None:
    member = _member(inventory=["Dragon-Skin Garment"])
    assert save_modifier(member, save_label="fire breath") > save_modifier(member)


def test_chaos_fanatics_secret_grants_defense_vs_goatmen() -> None:
    goatmen = EnemyState(id="g1", name="Goatmen", category="vermin", level=3, life=3, max_life=3, tags=["chaos"])
    assert is_chaos_fanatic(goatmen) is True
    member = _member(secrets=["chaos_fanatics"])
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="combat",
        party=[member],
        map_state=MapState(tiles=[_tile()], current_tile_id="t1"),
        secret_chaos_fanatics_active=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert secret_defense_bonus(member, goatmen, session) == 1


def test_yummy_meal_secret_save_bonus() -> None:
    member = _member(class_id="halfling")
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        party=[member],
        map_state=MapState(tiles=[_tile()], current_tile_id="t1"),
        secret_yummy_meal_active=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert secret_save_bonus(member, session, save_label="fear") == 1
    assert secret_save_bonus(member, session, save_label="disease") == 1


def test_corridor_leads_rerolls_room_content(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 12)
    hero = _member(secrets=["corridor_leads"])
    tile = _tile(content_key="encounter", enemies=[], resolved=False)
    session = _session(hero, tile)
    eng = _engine()
    eng.advance(session, "use_secret", character_id="h", secret_id="corridor_leads")
    assert "corridor_leads" not in hero.secrets
    assert "rerolls the room content table" in " ".join(session.log).lower()


def test_yummy_meal_requires_halfling_user() -> None:
    hero = _member(class_id="wizard", secrets=["yummy_meal"])
    session = _session(hero, _tile())
    eng = _engine()
    eng.advance(session, "use_secret", character_id="h", secret_id="yummy_meal")
    assert "Only a halfling" in session.log[-1]
    assert session.secret_yummy_meal_active is False


def test_yummy_meal_halfling_activates_bonus() -> None:
    hero = _member(class_id="halfling", secrets=["yummy_meal"])
    session = _session(hero, _tile())
    eng = _engine()
    eng.advance(session, "use_secret", character_id="h", secret_id="yummy_meal")
    assert session.secret_yummy_meal_active is True
    assert "Madness" in session.log[-1]
