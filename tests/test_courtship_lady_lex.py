"""Tests for Lady of Lament quest and Lex full shop."""

from __future__ import annotations

from app.engine.courtship_book_of_secrets import (
    apply_lady_lament_truelove,
    lex_shop_catalog,
    resolve_courtship_book_choice,
)
from app.engine.courtship_demesne import update_courtship_on_combat_end
from app.engine.courtship_lex import (
    apply_lex_opposition_curses,
    apply_lex_soul_tax_if_needed,
    register_lex_opponents,
    start_lex_cambion_combat,
    track_lex_combat_natural,
)
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


def test_lex_soul_tax_roll_one_curses_opponents(monkeypatch) -> None:
    eng = engine()
    buyer = _party_member()
    buyer.name = "Buyer"
    opponent = _party_member()
    opponent.character_id = "hero-2"
    opponent.name = "Foe"
    opponent.marching_order = 2
    session = eng.create_session(
        "lex-curse",
        "party-1",
        [buyer, opponent],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    buyer = session.party[0]
    opponent = session.party[1]
    item = "Magic Shovel"
    from app.engine.courtship_lex import record_lex_grant

    record_lex_grant(session, buyer, item)
    register_lex_opponents(session, [opponent.character_id])
    monkeypatch.setattr("app.engine.courtship_lex.roll_d6", lambda: 1)
    assert not apply_lex_soul_tax_if_needed(session, buyer, item, engine=eng, show_rolls=False)
    assert buyer.current_life == 0
    assert opponent.current_life == 0
    assert opponent.character_id in session.permanently_lost_character_ids


def test_lex_double_natural_six_curses_hero() -> None:
    session = engine().create_session(
        "lex-double-six",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    session.courtship_lex_combat_active = True
    track_lex_combat_natural(session, member, attack_natural=6, show_rolls=False)
    track_lex_combat_natural(session, member, defense_natural=6, show_rolls=False)
    assert member.current_life == 0
    assert member.character_id in session.permanently_lost_character_ids


def test_attack_lex_registers_opponents_and_spawns(monkeypatch) -> None:
    eng = engine()
    session = eng.create_courtship_demesne_session("lex-attack", "party-1", [_party_member()])
    session.courtship_pending_choice = "lex_cambion"
    with monkeypatch.context() as patch:
        patch.setattr(
            "app.engine.courtship_demesne._spawn_courtship",
            lambda *args, **kwargs: session.log.append("spawned"),
        )
        assert start_lex_cambion_combat(eng, session, show_rolls=False)
    assert session.courtship_lex_combat_active
    assert session.party[0].character_id in session.courtship_lex_opponents
    assert session.courtship_pending_choice is None


def test_lex_sleep_on_hit_skips_next_attack() -> None:
    from app.engine.courtship_combat import COURTSHIP_SKIP_ATTACK, apply_courtship_on_foe_hit

    session = engine().create_courtship_demesne_session("lex-sleep", "party-1", [_party_member()])
    member = session.party[0]
    lex = EnemyState(
        id="lex1",
        name="Lex the Cambion",
        category="weird",
        level=10,
        life=10,
        max_life=10,
        attacks=2,
        tags=["courtship:Lex the Cambion", "courtship_lex_sleep"],
    )
    apply_courtship_on_foe_hit(lex, member, session.party, session=session, show_rolls=False)
    assert COURTSHIP_SKIP_ATTACK in member.statuses


def test_lex_combat_start_fear_save_applies_attack_penalty(monkeypatch) -> None:
    from app.engine.courtship_book_of_secrets import apply_book_of_secrets_combat_entry
    from app.engine.courtship_combat import COURTSHIP_ATTACK_PENALTY

    session = engine().create_courtship_demesne_session("lex-fear", "party-1", [_party_member()])
    member = session.party[0]
    with monkeypatch.context() as patch:
        patch.setattr(
            "app.engine.courtship_demesne._fd_style_save",
            lambda *args, **kwargs: (True, ["fail"]),
        )
        apply_book_of_secrets_combat_entry(session, session.party, [], 7, show_rolls=False)
    assert COURTSHIP_ATTACK_PENALTY in member.statuses


def test_lex_soul_tax_roll_one_returns_to_meadows(monkeypatch) -> None:
    eng = engine()
    buyer = _party_member()
    session = eng.create_courtship_demesne_session("lex-meadows", "party-1", [buyer])
    item = "Magic Shovel"
    from app.engine.courtship_lex import record_lex_grant

    record_lex_grant(session, buyer, item)
    with monkeypatch.context() as patch:
        patch.setattr("app.engine.courtship_lex.roll_d6", lambda: 1)
        patch.setattr(
            "app.engine.courtship_demesne._return_to_meadows_and_roll",
            lambda *args, **kwargs: session.log.append("meadows-reroll") or True,
        )
        assert not apply_lex_soul_tax_if_needed(session, buyer, item, engine=eng, show_rolls=False)
    assert any("meadows-reroll" in line for line in session.log)
