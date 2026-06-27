"""TRUELOVE fidelity, vault betrayal, and Lady doubles (TCOTFD Demesne polish)."""

from __future__ import annotations

from app.engine.courtship_book_of_secrets import apply_lady_lament_truelove, resolve_courtship_book_choice
from app.engine.courtship_combat import apply_courtship_combat_start, courtship_lady_flee_before_combat
from app.engine.courtship_demesne import (
    _add_keyword,
    _maybe_apply_truelove_infidelity,
    apply_courtship_encounter,
)
from app.schemas import EnemyState, TileState
from tests.test_forsaken_depths_engine import _party_member, engine


def test_truelove_infidelity_strips_keywords() -> None:
    session = engine().create_session(
        "infidelity",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    _add_keyword(session, "KEEPSAKE")
    _add_keyword(session, "TRUELOVE")
    session.courtship_truelove_character_id = member.character_id

    assert _maybe_apply_truelove_infidelity(
        session, member, "Matron of Summer", "boss", show_rolls=False
    )
    assert "TRUELOVE" not in session.courtship_keywords
    assert "KEEPSAKE" not in session.courtship_keywords
    assert session.courtship_truelove_character_id is None
    assert session.courtship_lady_heart_broken


def test_truelove_wooing_lady_again_is_faithful() -> None:
    session = engine().create_session(
        "faithful",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    _add_keyword(session, "TRUELOVE")
    session.courtship_truelove_character_id = member.character_id

    assert not _maybe_apply_truelove_infidelity(
        session, member, "Lady of Lament", "boss", show_rolls=False
    )
    assert "TRUELOVE" in session.courtship_keywords


def test_plant_wooing_does_not_break_truelove() -> None:
    session = engine().create_session(
        "plant-woo",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    _add_keyword(session, "TRUELOVE")
    session.courtship_truelove_character_id = member.character_id

    assert not _maybe_apply_truelove_infidelity(
        session, member, "Death Orchid", "weird", show_rolls=False
    )
    assert "TRUELOVE" in session.courtship_keywords


def test_vault_acerbic_applies_pandora_and_broken_heart() -> None:
    eng = engine()
    session = eng.create_session(
        "vault-betrayal",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    session.courtship_demesne_region = "palace"
    tile = TileState(
        id="palace-tile",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Palace",
        description="Palace",
    )
    session.map_state.tiles = [tile]
    session.courtship_return_tile_id = tile.id
    member = session.party[0]
    apply_lady_lament_truelove(session, member, show_rolls=False)
    session.courtship_pending_choice = "queens_vault"

    assert resolve_courtship_book_choice(eng, session, "acerbic", show_rolls=False)
    assert "PANDORA" in session.courtship_keywords
    assert session.courtship_lady_heart_broken
    assert session.courtship_truelove_character_id is None


def test_lady_spawns_illusion_doubles() -> None:
    eng = engine()
    session = eng.create_session(
        "lady-doubles",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    tile = TileState(
        id="woods-tile",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Woods",
        description="Woods",
    )
    session.map_state.tiles = [tile]
    session.courtship_return_tile_id = tile.id
    row = {"effect": "lady_of_lament", "name": "Lady of Lament"}

    apply_courtship_encounter(eng, session, row, show_rolls=False)

    assert session.courtship_lady_doubles_active
    illusions = [enemy for enemy in tile.enemies if "illusion" in enemy.name.lower()]
    assert len(illusions) == 2
    assert any(enemy.name == "Lady of Lament" for enemy in tile.enemies)


def test_lady_flees_combat_leaving_doubles() -> None:
    session = engine().create_session(
        "lady-flee",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    lady = EnemyState(
        id="lady",
        name="Lady of Lament",
        level=6,
        life=8,
        max_life=8,
        category="boss",
        tags=["courtship:Lady of Lament"],
    )
    double = EnemyState(
        id="dbl",
        name="Lady of Lament (illusion)",
        level=6,
        life=1,
        max_life=1,
        category="minions",
        tags=["courtship:Lady of Lament (illusion)"],
    )
    enemies = [lady, double, double]
    log = courtship_lady_flee_before_combat(session, enemies, show_rolls=True)
    assert lady.life == 0
    assert any("flees" in entry.lower() for entry in log)
    assert all(enemy.life > 0 for enemy in enemies if "illusion" in enemy.name.lower())
