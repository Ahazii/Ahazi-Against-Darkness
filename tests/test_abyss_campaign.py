from __future__ import annotations

from pathlib import Path

from app.db import Store, init_db
from app.engine.clues import spend_living_party_clues
from app.engine.tag_campaign import apply_abyss_campaign_to_session, load_campaign, sync_abyss_campaign_from_session
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


def test_spend_living_party_clues_uses_marching_order_and_excludes_fallen_heroes() -> None:
    eng = _engine()
    first = _hero(character_id="first", name="First", clues=1, marching_order=1)
    second = _hero(character_id="second", name="Second", clues=3, marching_order=2)
    fallen = _hero(character_id="fallen", name="Fallen", clues=9, current_life=0, marching_order=3)
    session = eng.create_session("s", "p", [first, second, fallen], ruleset_profile_id="abyss")
    session.clues_found = 4

    paid, log = spend_living_party_clues(session, 3)

    assert paid is True
    assert (first.clues, second.clues, fallen.clues, session.clues_found) == (0, 1, 9, 1)
    assert log == ["First spends 1 Clue(s).", "Second spends 2 Clue(s)."]


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


def test_rebellion_plot_pauses_between_multiple_battles(monkeypatch) -> None:
    eng = _engine()
    hero = _hero(gold=3000)
    session = eng.create_session("s", "p", [hero], ruleset_profile_id="abyss")
    monkeypatch.setattr("app.engine.abyss_campaign.roll_d3", lambda: 2)
    monkeypatch.setattr("app.engine.abyss_campaign.roll_exploding_for_level", lambda member, **kwargs: (6, [6]))
    monkeypatch.setattr("app.engine.abyss_campaign.roll_d6", lambda: 3)

    eng.advance(session, "start_abyss_campaign_plot", abyss_plot_choice="rebellion")
    eng.advance(session, "abyss_plot_contribute_gold")
    eng.advance(session, "abyss_plot_resolve_finale")

    assert session.abyss_campaign_plot is not None
    assert session.abyss_campaign_plot.completed is False
    assert session.abyss_campaign_plot.rebellion_battles_resolved == 1
    assert any("pauses between battles" in line.lower() for line in session.log)

    eng.advance(session, "abyss_plot_resolve_finale")

    assert session.abyss_campaign_plot.completed is True


def test_entity_plot_takes_one_artifact_piece_per_adventure_and_persists(monkeypatch, tmp_path) -> None:
    eng = _engine()
    store = Store(tmp_path / "game.db")
    init_db(store.db_path)
    hero = _hero()
    monkeypatch.setattr("app.engine.abyss_campaign.roll_die", lambda sides: 1)
    monkeypatch.setattr("app.engine.abyss_campaign.roll_d6", lambda: 2)

    session1 = eng.create_session("s1", "p", [hero], ruleset_profile_id="abyss")
    tile = session1.map_state.tiles[0]
    tile.treasure_items = ["Ring of Three Wishes (1 wish)"]
    tile.treasure_summary = "Abyss magic treasure"

    eng.advance(session1, "start_abyss_campaign_plot", abyss_plot_choice="entity")
    eng.advance(session1, "abyss_plot_take_artifact_piece")
    tile.treasure_items = ["Ring of Three Wishes (1 wish)"]
    tile.treasure_summary = "Abyss magic treasure"
    tile.treasure_claimed = False
    eng.advance(session1, "abyss_plot_take_artifact_piece")

    assert session1.abyss_campaign_plot is not None
    assert session1.abyss_campaign_plot.progress == 1
    assert any("only one artefact piece" in line.lower() for line in session1.log)

    sync_abyss_campaign_from_session(store, session1)
    campaign = load_campaign(store)
    assert campaign.abyss_campaign_plot is not None
    assert campaign.abyss_campaign_plot.progress == 1

    session2 = eng.create_session("s2", "p", [_hero()], ruleset_profile_id="abyss")
    apply_abyss_campaign_to_session(store, session2)
    assert session2.abyss_campaign_plot is not None
    assert session2.abyss_campaign_plot.progress == 1
    assert session2.abyss_campaign_plot.entity_piece_claimed_this_adventure is False
    tile = session2.map_state.tiles[0]
    tile.treasure_items = ["Ring of Three Wishes (1 wish)"]
    tile.treasure_summary = "Abyss magic treasure"
    eng.advance(session2, "abyss_plot_take_artifact_piece")
    sync_abyss_campaign_from_session(store, session2)

    session3 = eng.create_session("s3", "p", [_hero()], ruleset_profile_id="abyss")
    apply_abyss_campaign_to_session(store, session3)
    tile = session3.map_state.tiles[0]
    if tile:
        tile.treasure_items = ["Ring of Three Wishes (1 wish)"]
        tile.treasure_summary = "Abyss magic treasure"
        tile.treasure_claimed = False
    eng.advance(session3, "abyss_plot_take_artifact_piece")
    sync_abyss_campaign_from_session(store, session3)

    assert session3.abyss_campaign_plot is not None
    assert session3.abyss_campaign_plot.completed is True
    campaign = load_campaign(store)
    assert campaign.abyss_campaign_plot is None
    assert [plot.key for plot in campaign.abyss_campaign_completed_plots] == ["entity"]


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


def test_vampire_sire_persists_to_next_abyss_session(tmp_path) -> None:
    eng = _engine()
    store = Store(tmp_path / "game.db")
    init_db(store.db_path)
    session = eng.create_session("s1", "p", [_hero()], ruleset_profile_id="abyss")
    session.abyss_vampire_sire = EnemyState(
        id="v1",
        name="Major Vampire",
        category="boss",
        level=10,
        life=6,
        max_life=11,
        tags=["abyss", "vampire", "undead"],
    )

    sync_abyss_campaign_from_session(store, session)
    next_session = eng.create_session("s2", "p", [_hero()], ruleset_profile_id="abyss")
    apply_abyss_campaign_to_session(store, next_session)

    assert next_session.abyss_vampire_sire is not None
    assert next_session.abyss_vampire_sire.name == "Major Vampire"


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
