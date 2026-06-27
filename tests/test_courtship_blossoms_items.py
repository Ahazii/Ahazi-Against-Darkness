"""Blossoms magic items (TCOTFD p.69)."""

from __future__ import annotations

from unittest.mock import patch

from app.engine.courtship_blossoms_items import (
    ENCHANTED_ALEMBIC,
    MAGIC_SHOVEL,
    TALISMAN_OF_IMPOTENCE,
    cast_bountiful_harvest,
    prepare_blossoms_magic_item,
    talisman_blocks_giving,
)
from app.engine.courtship_blossoms_spells import resolve_bountiful_harvest_choice
from app.engine.courtship_combat import apply_courtship_combat_start
from app.engine.courtship_demesne import resolve_courtship_woo_giving
from app.engine.magic_weapons import is_magic_weapon, magic_weapon_attack_bonus
from app.engine.weapons import _parse_weapon_item
from app.schemas import EnemyState
from tests.test_forsaken_depths_engine import _party_member, engine


def test_prepare_alembic_adds_charges() -> None:
    with patch("app.engine.courtship_blossoms_items.roll_d6", return_value=4):
        item = prepare_blossoms_magic_item(ENCHANTED_ALEMBIC)
    assert item == "Enchanted Alembic (4 charges)"


def test_magic_shovel_is_light_magic_weapon() -> None:
    profile = _parse_weapon_item(MAGIC_SHOVEL)
    assert profile is not None
    assert profile.light is True
    assert profile.crushing is True
    assert is_magic_weapon(MAGIC_SHOVEL)
    assert magic_weapon_attack_bonus(MAGIC_SHOVEL) == 1


def test_bountiful_harvest_success_sets_pending_choice() -> None:
    eng = engine()
    member = _party_member()
    member.inventory.append(f"{ENCHANTED_ALEMBIC} (3 charges)")
    session = eng.create_courtship_demesne_session("bountiful", "party-1", [member])
    session.courtship_pending_choice = None
    session.courtship_pending_choice_label = None
    tile = eng._current_tile(session)
    with patch("app.engine.courtship_blossoms_spells.roll_exploding_for_level", return_value=(6, [6])):
        assert cast_bountiful_harvest(eng, session, member, tile, show_rolls=False)
    assert session.courtship_pending_choice == "bountiful_harvest"
    assert session.courtship_pending_choice_label == member.character_id


def test_bountiful_harvest_choice_grants_ingredients() -> None:
    session = engine().create_courtship_demesne_session(
        "bountiful-choice",
        "party-1",
        [_party_member()],
    )
    member = session.party[0]
    session.courtship_pending_choice = "bountiful_harvest"
    session.courtship_pending_choice_label = member.character_id
    with patch("app.engine.courtship_blossoms_spells.roll_d6", return_value=3):
        assert resolve_bountiful_harvest_choice(session, member, "common", show_rolls=False)
    assert sum(1 for item in member.inventory if item == "Common ingredient") == 3
    assert session.courtship_pending_choice is None


def test_talisman_blocks_giving_and_satyr_wounds() -> None:
    satyr = _party_member()
    satyr.class_id = "satyr"
    satyr.inventory.append(TALISMAN_OF_IMPOTENCE)
    assert talisman_blocks_giving(satyr)
    session = engine().create_courtship_demesne_session("talisman", "party-1", [satyr])
    session.courtship_woo_active = True
    session.courtship_woo_template = "Damsel of Teeming Roses"
    session.courtship_woo_speaker_id = satyr.character_id
    assert not resolve_courtship_woo_giving(engine(), session, show_rolls=False)
    assert any("Talisman of Impotence" in line for line in session.log)

    satyr2 = _party_member()
    satyr2.class_id = "satyr"
    satyr2.inventory.append(TALISMAN_OF_IMPOTENCE)
    session2 = engine().create_courtship_demesne_session("satyr-wounds", "party-1", [satyr2])
    with patch("app.engine.courtship_blossoms_items.roll_d6", return_value=4):
        log = apply_courtship_combat_start(session2, session2.party, [], show_rolls=True)
    assert satyr2.current_life == satyr2.max_life - 4
    assert any("Talisman of Impotence" in line for line in log)


def test_satyr_talisman_wounds_on_combat_start() -> None:
    satyr = _party_member()
    satyr.class_id = "satyr"
    satyr.inventory.append(TALISMAN_OF_IMPOTENCE)
    session = engine().create_courtship_demesne_session("satyr-only", "party-1", [satyr])
    foe = EnemyState(id="f1", name="Flower demon", category="minions", level=1, life=1, max_life=1)
    with patch("app.engine.courtship_blossoms_items.roll_d6", return_value=2):
        apply_courtship_combat_start(session, session.party, [foe], show_rolls=False)
    assert satyr.current_life == satyr.max_life - 2
