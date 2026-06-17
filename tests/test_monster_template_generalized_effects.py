from __future__ import annotations

import json
from pathlib import Path

from app.engine.combat import CombatContext
from app.engine.monster_template_effects import (
    apply_encounter_start_effects,
    apply_on_hit_effects,
    template_encounter_start_effects,
    template_on_hit_effects,
)
from app.schemas import EnemyState, PartyMemberState, SessionState


def _hero(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=4,
        max_life=6,
        current_life=6,
        marching_order=1,
        inventory=["Hand weapon"],
        statuses=[],
        spells=[],
        learned_expert_skills=[],
        gold=0,
        clues=0,
        xp=0,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _session(party: list[PartyMemberState]) -> SessionState:
    return SessionState(
        id="sess-1",
        party_id="party-1",
        adventure_id="adv-1",
        adventure_type="random",
        party=party,
        map_state={"current_tile_id": "tile-1", "tiles": []},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _template(table_key: str, monster_name: str) -> dict:
    monsters_path = Path(__file__).resolve().parents[1] / "data" / "rules" / "monsters.json"
    table = json.loads(monsters_path.read_text(encoding="utf-8"))[table_key]
    return next(item for item in table if item["name"] == monster_name)


def test_charge_encounter_start_sets_round_one_level_bonus() -> None:
    hero = _hero()
    session = _session([hero])
    template = _template("fiendish_foes_vermin", "Goatmen")
    goat = EnemyState(
        id="goat-1",
        name="Goatmen",
        category="vermin",
        level=5,
        life=1,
        max_life=1,
        encounter_start_effects=template_encounter_start_effects(template),
    )
    log = apply_encounter_start_effects([goat], [hero], session, show_rolls=False)
    assert "charge_level_bonus:2" in goat.tags
    assert any("charges" in line.lower() for line in log)


def test_shapeshift_encounter_start_marks_mimicked_target(monkeypatch) -> None:
    hero = _hero()
    session = _session([hero])
    template = _template("fiendish_foes_weird", "Doppelganger")
    doppel = EnemyState(
        id="doppel-1",
        name="Doppelganger",
        category="weird",
        level=6,
        life=5,
        max_life=5,
        encounter_start_effects=template_encounter_start_effects(template),
    )
    monkeypatch.setattr("app.engine.monster_template_effects.roll_d6", lambda: 1)
    log = apply_encounter_start_effects([doppel], [hero], session, show_rolls=False)
    assert any(tag.startswith("Doppelganger mimics:") for tag in doppel.tags)
    assert any("shapeshifts" in line.lower() for line in log)


def test_disease_on_hit_queues_end_of_encounter_loss(monkeypatch) -> None:
    hero = _hero()
    session = _session([hero])
    template = _template("fungal_grottoes_minions", "Moldspawn")
    moldspawn = EnemyState(
        id="mold-1",
        name="Moldspawn",
        category="minion",
        level=6,
        life=1,
        max_life=1,
        on_hit_effects=template_on_hit_effects(template),
    )
    monkeypatch.setattr("app.engine.monster_template_effects.roll_exploding_for_level", lambda level: (1, [1]))
    log = apply_on_hit_effects(moldspawn, hero, context=CombatContext(session=session), show_rolls=False)
    assert any(status.lower().startswith("disease pending:") for status in hero.statuses)
    assert any("pending" in line.lower() and "disease" in line.lower() for line in log)


def test_magic_attack_penalty_and_slime_disease_apply_statuses(monkeypatch) -> None:
    hero = _hero()
    session = _session([hero])
    hag_template = _template("fungal_grottoes_boss", "Fungus Hag")
    slime_template = _template("fiendish_foes_weird", "Green Slime")
    hag = EnemyState(
        id="hag-1",
        name="Fungus Hag",
        category="boss",
        level=7,
        life=6,
        max_life=6,
        on_hit_effects=template_on_hit_effects(hag_template),
    )
    slime = EnemyState(
        id="slime-1",
        name="Green Slime",
        category="weird",
        level=7,
        life=8,
        max_life=8,
        on_hit_effects=template_on_hit_effects(slime_template),
    )
    monkeypatch.setattr("app.engine.monster_template_effects.roll_exploding_for_level", lambda level: (1, [1]))
    apply_on_hit_effects(hag, hero, context=CombatContext(session=session), show_rolls=False)
    apply_on_hit_effects(slime, hero, context=CombatContext(session=session), show_rolls=False)
    lowered = {status.lower() for status in hero.statuses}
    assert "attack penalty (magic) -1" in lowered
    assert "slime disease" in lowered
