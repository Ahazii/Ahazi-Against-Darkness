"""Satyr outdoor seduction and woo (TCOTFD p.11-12)."""

from __future__ import annotations

from unittest.mock import patch

from app.engine.courtship_demesne import resolve_courtship_woo_withholding
from app.engine.courtship_satyr_outdoor import (
    complete_outdoor_satyr_woo,
    group_eligible_for_satyr_woo,
    satyr_pheromone_eligible_female,
    start_outdoor_satyr_woo,
    try_satyr_auto_seduce_on_encounter,
)
from app.schemas import EnemyState
from tests.test_forsaken_depths_engine import _party_member, engine


def _orc_enemy(*, enemy_id: str = "e1", sex_roll: int = 2) -> EnemyState:
    return EnemyState(
        id=enemy_id,
        name="Orc",
        category="minions",
        level=4,
        life=4,
        max_life=4,
    )


def test_medusa_always_female_she_orc_too() -> None:
    session = engine().create_session("sex", "party-1", [_party_member()])
    medusa = EnemyState(id="m1", name="Medusa", category="boss", level=6, life=6, max_life=6)
    she_orc = EnemyState(id="s1", name="She-Orc", category="minions", level=3, life=3, max_life=3)
    assert satyr_pheromone_eligible_female(session, medusa)
    assert satyr_pheromone_eligible_female(session, she_orc)


def test_vampire_uses_sex_roll() -> None:
    session = engine().create_session("vamp", "party-1", [_party_member()])
    vampire = EnemyState(id="v1", name="Vampire", category="boss", level=5, life=5, max_life=5)
    session.satyr_foe_sex_rolls[vampire.id] = 4
    assert not satyr_pheromone_eligible_female(session, vampire)
    session.satyr_foe_sex_rolls[vampire.id] = 2
    assert satyr_pheromone_eligible_female(session, vampire)


def test_group_requires_all_eligible() -> None:
    session = engine().create_session("grp", "party-1", [_party_member()])
    female = _orc_enemy(enemy_id="o1")
    session.satyr_foe_sex_rolls[female.id] = 2
    male = _orc_enemy(enemy_id="o2")
    session.satyr_foe_sex_rolls[male.id] = 5
    assert group_eligible_for_satyr_woo(session, [female])
    assert not group_eligible_for_satyr_woo(session, [female, male])


def test_pheromone_starts_outdoor_woo(monkeypatch) -> None:
    eng = engine()
    satyr = _party_member()
    satyr.class_id = "satyr"
    satyr.level = 4
    session = eng.create_session("seduce", "party-1", [satyr], courtship_enabled=True)
    tile = eng._current_tile(session)
    assert tile is not None
    orc = _orc_enemy()
    session.satyr_foe_sex_rolls[orc.id] = 1
    tile.enemies = [orc]
    monkeypatch.setattr("app.engine.courtship_satyr_outdoor.roll_d6", lambda: 6)
    assert try_satyr_auto_seduce_on_encounter(eng, session, tile, show_rolls=False)
    assert session.courtship_woo_active
    assert session.courtship_woo_outdoor
    assert session.courtship_woo_speaker_id == satyr.character_id


def test_outdoor_withholding_costs_life_not_melancholy(monkeypatch) -> None:
    eng = engine()
    satyr = _party_member()
    satyr.class_id = "satyr"
    session = eng.create_session("wh", "party-1", [satyr])
    tile = eng._current_tile(session)
    assert tile is not None
    orc = _orc_enemy()
    session.satyr_foe_sex_rolls[orc.id] = 1
    tile.enemies = [orc]
    start_outdoor_satyr_woo(eng, session, tile, satyr, [orc], show_rolls=False)
    before_life = satyr.current_life
    monkeypatch.setattr(
        "app.engine.class_abilities.roll_exploding_for_level",
        lambda _m: (1, [1]),
    )
    resolve_courtship_woo_withholding(eng, session, show_rolls=False)
    assert satyr.current_life == before_life - 1
    assert session.courtship_melancholy.get(satyr.character_id, 0) == 0


def test_outdoor_woo_success_grants_treasure(monkeypatch) -> None:
    eng = engine()
    satyr = _party_member()
    satyr.class_id = "satyr"
    session = eng.create_session("treasure", "party-1", [satyr])
    tile = eng._current_tile(session)
    assert tile is not None
    orc = _orc_enemy()
    tile.enemies = [orc]
    session.courtship_woo_outdoor = True
    session.courtship_woo_template = "Orc"
    with patch.object(eng, "_award_treasure") as award:
        log = complete_outdoor_satyr_woo(eng, session, tile, satyr, show_rolls=False)
    award.assert_called_once()
    assert not tile.enemies
    assert "Orc" in session.satyr_peaceful_foe_names
    assert any("treasure" in line.lower() for line in log)
