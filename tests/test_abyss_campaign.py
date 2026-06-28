from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, PartyMemberState, TileDefinition


def _engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _hero(**overrides) -> PartyMemberState:
    data = {
        "character_id": "h1",
        "name": "Abyss Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 5,
        "xp": 0,
        "gold": 0,
        "bank_gold": 0,
        "clues": 0,
        "current_life": 10,
        "max_life": 10,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
        "inventory": ["Hand weapon"],
    }
    data.update(overrides)
    return PartyMemberState(**data)


def test_rebellion_plot_contributes_gold_and_resolves_war(monkeypatch) -> None:
    eng = _engine()
    hero = _hero(gold=3000)
    session = eng.create_session("s", "p", [hero], ruleset_profile_id="abyss")
    monkeypatch.setattr("app.engine.abyss_campaign.roll_d3", lambda: 1)
    monkeypatch.setattr("app.engine.abyss_campaign.roll_exploding_for_level", lambda member, **kwargs: (6, [6]))
    monkeypatch.setattr("app.engine.abyss_campaign.roll_d6", lambda: 3)

    eng.advance(session, "start_abyss_campaign_plot", abyss_plot_choice="rebellion")
    eng.advance(session, "abyss_plot_contribute_gold")
    eng.advance(session, "abyss_plot_resolve_finale")

    assert session.abyss_campaign_plot is not None
    assert session.abyss_campaign_plot.completed is True
    assert hero.gold == 300
    assert session.xp_rolls_pending >= 2
    assert any("rebellion succeeds" in line.lower() for line in session.log)


def test_entity_plot_takes_artifact_piece_from_magic_treasure(monkeypatch) -> None:
    eng = _engine()
    hero = _hero()
    session = eng.create_session("s", "p", [hero], ruleset_profile_id="abyss")
    tile = session.map_state.tiles[0]
    tile.treasure_items = ["Ring of Three Wishes (1 wish)"]
    tile.treasure_summary = "Abyss magic treasure"
    monkeypatch.setattr("app.engine.abyss_campaign.roll_die", lambda sides: 1)
    monkeypatch.setattr("app.engine.abyss_campaign.roll_d6", lambda: 2)

    eng.advance(session, "start_abyss_campaign_plot", abyss_plot_choice="entity")
    for _ in range(3):
        tile.treasure_items = ["Ring of Three Wishes (1 wish)"]
        tile.treasure_summary = "Abyss magic treasure"
        tile.treasure_claimed = False
        eng.advance(session, "abyss_plot_take_artifact_piece")

    assert session.abyss_campaign_plot is not None
    assert session.abyss_campaign_plot.completed is True
    assert hero.madness == 1
    assert hero.gold == 200


def test_invasion_plot_spends_clues_and_destroy_artifact_can_lose_holder(monkeypatch) -> None:
    eng = _engine()
    hero = _hero(level=1, clues=9, madness=0)
    session = eng.create_session("s", "p", [hero], ruleset_profile_id="abyss")
    monkeypatch.setattr("app.engine.abyss_campaign.roll_d6", lambda: 1)

    eng.advance(session, "start_abyss_campaign_plot", abyss_plot_choice="invasion", character_id="h1")
    eng.advance(session, "abyss_plot_spend_clues")
    session.abyss_campaign_plot.finale_pending = "destroy_artifact"
    eng.advance(session, "abyss_plot_resolve_finale")

    assert session.abyss_campaign_plot.completed is True
    assert hero.current_life == 0
    assert "h1" in session.permanently_lost_character_ids


def test_vampire_sire_hunt_spends_discounted_clue_and_spawns_sire(monkeypatch) -> None:
    eng = _engine()
    hero = _hero(clues=1, learned_expert_skills=["vampire_hunter"])
    session = eng.create_session("s", "p", [hero], ruleset_profile_id="abyss")
    session.abyss_vampire_sire = EnemyState(
        id="v1",
        name="Major Vampire",
        category="boss",
        level=10,
        life=6,
        max_life=11,
        tags=["abyss", "vampire", "undead"],
    )
    monkeypatch.setattr("app.engine.abyss_campaign.roll_d6", lambda: 3)

    eng.advance(session, "hunt_vampire_sire")

    tile = session.map_state.tiles[0]
    assert hero.clues == 0
    assert session.mode == "combat"
    assert any(enemy.name == "Major Vampire" for enemy in tile.enemies)


def test_large_abyss_room_roll_12_routes_to_dragon_lair(monkeypatch) -> None:
    eng = _engine()
    session = eng.create_session("s", "p", [_hero()], ruleset_profile_id="abyss")
    large_room = TileDefinition(
        key="56",
        name="Large Room",
        tile_type="room",
        footprint_width=7,
        footprint_height=7,
        walkable=["1111111", "1111111", "1111111", "1111111"],
        cell_shapes=["FFFFFFF"],
        exits=[],
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 12)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    content = eng._roll_content(session, "room", 5, tile_def=large_room)

    assert content["key"] == "abyss_dragon"
    assert content["enemies"]
    assert "dragon" in content["enemies"][0].name.lower() or "dragon" in content["enemies"][0].tags
