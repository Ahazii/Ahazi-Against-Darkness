"""Blossoms spell scroll casting (TCOTFD p.27)."""

from __future__ import annotations

from unittest.mock import patch

from app.engine.courtship_apothecary import (
    apply_libidinal_virile_conjunction,
    virile_might_breeding_save_bonus,
    virile_might_giving_bonus,
)
from app.engine.courtship_blossoms_spells import (
    cast_blossoms_spell,
    flower_portal_destinations,
    is_blossoms_scroll_item,
    is_blossoms_spell,
    resolve_flower_portal,
    try_cast_blossoms_scroll,
)
from app.engine.courtship_demesne import resolve_courtship_libidinal_reroll
from tests.test_forsaken_depths_engine import _party_member, engine


def test_blossoms_scroll_item_detection() -> None:
    assert is_blossoms_spell("Bountiful Harvest")
    assert is_blossoms_spell("Ætheric Conversion")
    assert is_blossoms_scroll_item("Scroll of Flower Portal")
    assert not is_blossoms_scroll_item("Scroll of Fireball")


def test_fools_gold_scroll_brew() -> None:
    eng = engine()
    member = _party_member()
    member.inventory.extend(
        ["Mineral ingredient"] * 5 + ["Common ingredient (Herbs)"] * 3 + ["Scroll of Fools' Gold"]
    )
    session = eng.create_courtship_demesne_session("fools-gold", "party-1", [member])
    tile = eng._current_tile(session)
    with patch("app.engine.courtship_blossoms_spells.roll_exploding_for_level", return_value=(8, [6])):
        assert try_cast_blossoms_scroll(
            eng,
            session,
            member,
            "Fools' Gold",
            "Scroll of Fools' Gold",
            show_rolls=False,
        )
    assert "Fools' Gold" in member.inventory
    assert "Scroll of Fools' Gold" not in member.inventory


def test_flower_portal_scroll_requires_soul_cube_and_region() -> None:
    eng = engine()
    member = _party_member()
    member.inventory.append("Scroll of Flower Portal")
    session = eng.create_courtship_demesne_session("portal", "party-1", [member])
    session.courtship_demesne_region = "meadows"
    tile = eng._current_tile(session)
    assert not cast_blossoms_spell(
        eng,
        session,
        member,
        "Flower Portal",
        tile,
        show_rolls=False,
        from_scroll=True,
    )
    session.courtship_demesne_region = "seaside"
    member.inventory.append("soul cube")
    with patch("app.engine.courtship_demesne.leave_courtship_demesne", return_value=True):
        assert cast_blossoms_spell(
            eng,
            session,
            member,
            "Flower Portal",
            tile,
            show_rolls=False,
            from_scroll=True,
        )


def test_libidinal_enhancement_during_wooing() -> None:
    eng = engine()
    member = _party_member()
    session = eng.create_courtship_demesne_session("libidinal", "party-1", [member])
    session.courtship_woo_active = True
    session.courtship_woo_speaker_id = member.character_id
    tile = eng._current_tile(session)
    assert cast_blossoms_spell(
        eng,
        session,
        member,
        "Libidinal Enhancement",
        tile,
        target_character_id=member.character_id,
        show_rolls=False,
        from_scroll=True,
    )
    assert session.courtship_libidinal_reroll_available
    member.current_life = 5
    with patch("app.engine.courtship_demesne.resolve_courtship_woo_giving", return_value=True):
        assert resolve_courtship_libidinal_reroll(eng, session, show_rolls=False)
    assert member.current_life == 4
    assert not session.courtship_libidinal_reroll_available


def test_flower_portal_enter_from_water_tile() -> None:
    eng = engine()
    member = _party_member()
    member.inventory.extend(["Scroll of Flower Portal", "soul cube"])
    session = eng.create_session(
        "fp-enter",
        "party-1",
        [member],
        ruleset="ee",
        courtship_enabled=True,
    )
    tile = eng._current_tile(session)
    assert tile is not None
    tile.terrain = "lake"
    with patch("app.engine.courtship_blossoms_spells.roll_exploding_for_level", return_value=(6, [6])):
        assert resolve_flower_portal(
            eng,
            session,
            member,
            tile,
            destination="enter_demesne",
            show_rolls=False,
            from_scroll=True,
        )
    assert session.courtship_demesne_active
    assert session.courtship_entry_source == "flower_portal"
    assert session.courtship_demesne_region == "seaside"


def test_flower_portal_netherworld_consumes_discounted_cubes() -> None:
    eng = engine()
    member = _party_member()
    member.class_id = "wizard"
    member.class_name = "Wizard"
    member.level = 3
    member.inventory.extend(["soul cube"] * 3)
    session = eng.create_session(
        "fp-nether",
        "party-1",
        [member],
        ruleset="ee",
        courtship_enabled=True,
    )
    tile = eng._current_tile(session)
    assert tile is not None
    tile.terrain = "river"
    with patch("app.engine.courtship_blossoms_spells.roll_exploding_for_level", return_value=(8, [5, 3])), patch.object(
        eng, "_open_secret_passage_destination", return_value=True
    ):
        assert resolve_flower_portal(
            eng,
            session,
            member,
            tile,
            destination="netherworld",
            show_rolls=False,
            from_scroll=True,
        )
    assert sum(1 for item in member.inventory if "soul cube" in item.lower()) == 2


def test_flower_portal_demesne_offers_leave_and_netherworld() -> None:
    eng = engine()
    session = eng.create_courtship_demesne_session("fp-opts", "party-1", [_party_member()])
    session.courtship_demesne_region = "riverside"
    tile = eng._current_tile(session)
    opts = flower_portal_destinations(session, tile)
    assert "leave_demesne" in opts
    assert "netherworld" in opts


def test_virile_might_giving_bonus_and_libidinal_conjunction() -> None:
    member = _party_member()
    assert virile_might_giving_bonus(member) == 0
    assert virile_might_breeding_save_bonus(member) == 0
    member.inventory.append("Pills of virile might")
    assert virile_might_giving_bonus(member) == 2
    assert virile_might_breeding_save_bonus(member) == 1
    eng = engine()
    session = eng.create_courtship_demesne_session("virile", "party-1", [member])
    with patch("app.engine.dice.roll_exploding_for_level", return_value=(2, [2])), patch(
        "app.engine.dice.roll_d6", return_value=4
    ):
        apply_libidinal_virile_conjunction(session, member, show_rolls=False)
    assert member.current_life == 8
