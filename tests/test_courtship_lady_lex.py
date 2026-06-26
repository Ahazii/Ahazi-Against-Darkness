"""Tests for Lady of Lament quest and Lex full shop."""

from __future__ import annotations

from app.engine.courtship_book_of_secrets import (
    apply_lady_lament_truelove,
    lex_shop_catalog,
    resolve_courtship_book_choice,
)
from app.engine.courtship_demesne import update_courtship_on_combat_end
from app.schemas import EnemyState
from tests.test_forsaken_depths_engine import _party_member, engine


def test_lex_shop_catalog_has_eighteen_items() -> None:
    catalog = lex_shop_catalog()
    assert len(catalog) == 18
    assert any(row["item"] == "Magic Shovel" for row in catalog)
    assert any(row["item"] == "Wand of Sleep (3 charges)" for row in catalog)


def test_lex_cambion_three_picks(monkeypatch) -> None:
    eng = engine()
    session = eng.create_session(
        "courtship-lex-3",
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
    assert session.courtship_lex_picks_remaining == 3
    picks = ["blossoms_magic_1", "blossoms_scroll_2", "4ad_magic_3"]
    for key in picks:
        assert resolve_courtship_book_choice(eng, session, key, show_rolls=False)
    assert session.courtship_pending_choice is None
    assert session.courtship_lex_picks_remaining == 0
    assert member.gold == 200
    assert "Magic Shovel" in member.inventory
    assert "Scroll of Bountiful Harvest" in member.inventory
    assert "Fools' Gold" in member.inventory


def test_lady_lament_truelove_blocks_satyr() -> None:
    session = engine().create_session(
        "lady-truelove",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    member.class_id = "satyr"
    log = apply_lady_lament_truelove(session, member, show_rolls=False)
    assert "satyr" in " ".join(log).lower()
    assert "TRUELOVE" not in session.courtship_keywords


def test_lady_lament_truelove_grants_keyword() -> None:
    session = engine().create_session(
        "lady-truelove-ok",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    apply_lady_lament_truelove(session, member, show_rolls=False)
    assert "TRUELOVE" in session.courtship_keywords
    assert session.courtship_truelove_character_id == member.character_id


def test_lady_combat_grants_head_for_matron_quest() -> None:
    eng = engine()
    session = eng.create_session(
        "lady-head",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    session.courtship_matron_head_quest_active = True
    defeated = [
        EnemyState(
            id="l1",
            name="Lady of Lament",
            category="boss",
            level=8,
            life=0,
            max_life=8,
            attacks=1,
        )
    ]
    update_courtship_on_combat_end(eng, session, defeated, show_rolls=False)
    assert any("Lady of Lament's head" in item for item in session.party[0].inventory)
    assert session.courtship_demesne_region == "woods"
