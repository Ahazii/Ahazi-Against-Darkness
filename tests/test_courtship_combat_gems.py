"""Courtship combat specials, Lex shop, and EE gem materialization."""

from __future__ import annotations

from app.engine.courtship_book_of_secrets import apply_matron_wooing_effects
from app.engine.courtship_book_of_secrets import resolve_courtship_book_choice
from app.engine.courtship_combat import courtship_crushing_attack_penalty
from app.engine.courtship_demesne import (
    _courtship_woo_foe_level,
    resolve_courtship_woo_giving,
    resolve_courtship_woo_withholding,
)
from app.engine.gem_items import materialize_treasure_gem_items
from app.schemas import EnemyState
from tests.test_forsaken_depths_engine import _party_member, engine


def test_materialize_treasure_gem_items() -> None:
    log: list[str] = []
    items = materialize_treasure_gem_items(["Jewelry (2d6x20gp)"], log)
    assert len(items) == 1
    assert items[0].startswith("Gem (")
    assert items[0].endswith("gp)")


def test_lex_cambion_grants_blossoms_item(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "courtship-lex",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    session.courtship_return_tile_id = session.map_state.tiles[0].id
    session.courtship_pending_choice = "lex_cambion"
    member = session.party[0]
    member.gold = 500
    assert resolve_courtship_book_choice(eng, session, "buy", show_rolls=False)
    assert session.courtship_pending_choice == "lex_cambion_pick"
    assert resolve_courtship_book_choice(eng, session, "blossoms_magic_1", show_rolls=False)
    assert "Magic Shovel" in member.inventory
    assert member.gold == 200


def test_mistress_quest_requires_three_rare_ingredients() -> None:
    eng = engine()
    session = eng.create_session(
        "courtship-mistress",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    session.courtship_return_tile_id = session.map_state.tiles[0].id
    session.courtship_pending_choice = "mistress_quest_ingredients"
    session.party[0].inventory = ["Rare ingredient (Blooded roses)"]
    assert not resolve_courtship_book_choice(eng, session, "deliver", show_rolls=False)
    session.party[0].inventory.extend(
        ["Rare ingredient (Death orchid petals)", "Rare ingredient (Flayed fay skin)"]
    )
    assert resolve_courtship_book_choice(eng, session, "deliver", show_rolls=False)
    assert len(session.party[0].inventory) == 0


def test_courtship_crushing_penalty_vs_flytrap() -> None:
    enemy = EnemyState(
        id="f1",
        name="Venus Flytrap",
        category="minions",
        level=4,
        life=1,
        max_life=1,
        attacks=1,
        tags=["courtship_plant_crushing_penalty"],
    )
    assert courtship_crushing_attack_penalty(enemy, crushing=True) == -1
    assert courtship_crushing_attack_penalty(enemy, crushing=False) == 0


def test_matron_wooing_permanent_life_first_visit_only() -> None:
    session = engine().create_session(
        "matron-pleasures",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    before_max = member.max_life
    apply_matron_wooing_effects(session, session.party, show_rolls=False)
    assert member.max_life == before_max + 1
    assert member.character_id in session.courtship_matron_pleasures_applied
    apply_matron_wooing_effects(session, session.party, show_rolls=False)
    assert member.max_life == before_max + 1


def test_matron_passionate_stance_lowers_foe_level() -> None:
    session = engine().create_session(
        "matron-passionate",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.party[0].level = 4
    session.courtship_woo_active = True
    session.courtship_woo_template = "Matron of Summer"
    session.courtship_woo_passionate_stance = True
    assert _courtship_woo_foe_level(session, 4) == 3


def test_matron_woo_success_returns_to_meadows(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "matron-meadows",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    tile = session.map_state.tiles[0]
    session.courtship_demesne_active = True
    session.courtship_demesne_region = "woods"
    session.courtship_return_tile_id = tile.id
    session.courtship_woo_active = True
    session.courtship_woo_template = "Matron of Summer"
    session.courtship_woo_speaker_id = session.party[0].character_id
    session.courtship_woo_successes = 2
    tile.enemies.append(
        EnemyState(id="m-1", name="Matron of Summer", level=8, life=1, max_life=1, category="boss")
    )
    monkeypatch.setattr(
        "app.engine.class_abilities.resolve_social_save",
        lambda *args, **kwargs: (True, ["ok"]),
    )
    monkeypatch.setattr("app.engine.courtship_demesne.roll_d3", lambda: 2)
    monkeypatch.setattr(
        "app.engine.courtship_book_of_secrets.apply_book_of_secrets_entry",
        lambda *args, **kwargs: ["Matron pleased (test)."],
    )
    meadows_rolled: list[str] = []

    def _fake_roll(*args, **kwargs) -> bool:
        meadows_rolled.append(session.courtship_demesne_region or "")
        return True

    monkeypatch.setattr("app.engine.courtship_demesne.roll_courtship_encounter", _fake_roll)
    assert resolve_courtship_woo_giving(eng, session, show_rolls=False)
    assert session.courtship_demesne_region == "meadows"
    assert meadows_rolled == ["meadows"]
    assert not session.courtship_woo_active


def test_matron_woo_withholding_skips_melancholy(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "matron-melancholy",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    session.courtship_return_tile_id = session.map_state.tiles[0].id
    session.courtship_woo_active = True
    session.courtship_woo_template = "Matron of Summer"
    session.courtship_woo_speaker_id = session.party[0].character_id
    member = session.party[0]
    session.courtship_melancholy[member.character_id] = 3
    monkeypatch.setattr(
        "app.engine.class_abilities.resolve_social_save",
        lambda *args, **kwargs: (False, ["fail"]),
    )
    monkeypatch.setattr("app.engine.courtship_demesne.roll_d6", lambda: 2)
    resolve_courtship_woo_withholding(eng, session, show_rolls=False)
    assert session.courtship_melancholy[member.character_id] == 3
