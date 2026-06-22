from __future__ import annotations

from app.engine.class_abilities import (
    bulwark_magical_healing_blocked,
    caster_has_free_spell_slot,
    gnome_gadget_free_prisoner,
    mushroom_hyphae_communion,
    paladin_heal,
    paladin_summon_steed,
    spend_caster_spell_slot,
)
from app.schemas import PartyMemberState, SessionState


def _session(**overrides) -> SessionState:
    base = {
        "id": "s",
        "party_id": "p",
        "adventure_id": "random",
        "adventure_type": "random",
        "mode": "exploration",
        "party": [],
        "map_state": {"width": 10, "height": 10, "tiles": [], "current_tile_id": "t"},
        "log": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return SessionState.model_validate(base)


def _bulwark(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="b",
        name="Wall",
        class_id="bulwark",
        class_name="Bulwark",
        level=4,
        xp=0,
        gold=0,
        current_life=6,
        max_life=8,
        attack_bonus=0,
        defense_bonus=1,
        save_bonus=0,
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def _cleric(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="c",
        name="Cleric",
        class_id="cleric",
        class_name="Cleric",
        level=3,
        xp=0,
        gold=0,
        current_life=3,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def test_bulwark_blocks_magical_healing_while_others_wounded() -> None:
    bulwark = _bulwark(current_life=6)
    ally = _cleric(current_life=2, max_life=5)
    session = _session(party=[bulwark, ally])
    assert bulwark_magical_healing_blocked(session, bulwark) is not None


def test_bulwark_allows_magical_healing_at_one_life() -> None:
    bulwark = _bulwark(current_life=1)
    ally = _cleric(current_life=2, max_life=5)
    session = _session(party=[bulwark, ally])
    assert bulwark_magical_healing_blocked(session, bulwark) is None


def test_paladin_heal_respects_bulwark_limit() -> None:
    paladin = PartyMemberState(
        character_id="p",
        name="Grace",
        class_id="paladin",
        class_name="Paladin",
        level=3,
        xp=0,
        gold=0,
        current_life=6,
        max_life=6,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
    )
    bulwark = _bulwark(current_life=6)
    ally = _cleric(current_life=2, max_life=5)
    session = _session(party=[paladin, bulwark, ally])
    log = paladin_heal(session, paladin, bulwark)
    assert any("Limited Healing" in line for line in log)


def test_paladin_summon_steed_sets_active_flag() -> None:
    paladin = PartyMemberState(
        character_id="p",
        name="Grace",
        class_id="paladin",
        class_name="Paladin",
        level=3,
        xp=0,
        gold=0,
        current_life=6,
        max_life=6,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
    )
    session = _session(party=[paladin])
    log = paladin_summon_steed(session, paladin)
    assert session.paladin_steed_active_id == "p"
    assert any("steed" in line.lower() for line in log)


def test_hyphae_clue_choice() -> None:
    monk = PartyMemberState(
        character_id="m",
        name="Spore",
        class_id="mushroom_monk",
        class_name="Mushroom Monk",
        level=5,
        xp=0,
        gold=0,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=1,
        save_bonus=0,
    )
    session = _session(party=[monk])
    log, follow_up = mushroom_hyphae_communion(session, monk, environment="wilderness", choice="clue")
    assert follow_up is None
    assert session.clues_found == 1
    assert monk.clues == 1
    assert "m" in session.hyphae_used


def test_hyphae_secret_door_returns_follow_up() -> None:
    monk = PartyMemberState(
        character_id="m",
        name="Spore",
        class_id="mushroom_monk",
        class_name="Mushroom Monk",
        level=5,
        xp=0,
        gold=0,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=1,
        save_bonus=0,
    )
    session = _session(party=[monk])
    _, follow_up = mushroom_hyphae_communion(session, monk, environment="fungal_grottoes", choice="secret_door")
    assert follow_up == "secret_door"


def test_illusionist_spell_slot_spend(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.class_abilities.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    illusionist = PartyMemberState(
        character_id="i",
        name="Glam",
        class_id="illusionist",
        class_name="Illusionist",
        level=3,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Distracting Lights"],
    )
    session = _session(party=[illusionist])
    assert caster_has_free_spell_slot(session, illusionist)
    assert spend_caster_spell_slot(session, illusionist, label="Illusionary knife throw")
    assert len(session.expended_spells["i"]) == 1


def test_gnome_gadget_free_prisoner_success(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.class_abilities.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    gnome = PartyMemberState(
        character_id="g",
        name="Giz",
        class_id="gnome",
        class_name="Gnome",
        level=4,
        xp=0,
        gold=0,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    ally = PartyMemberState(
        character_id="a",
        name="Prisoner",
        class_id="warrior",
        class_name="Warrior",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=6,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
        statuses=["Restrained"],
    )
    session = _session(party=[gnome, ally])
    log = gnome_gadget_free_prisoner(session, gnome, ally, show_rolls=False)
    assert any("frees" in line.lower() for line in log)
    assert "Restrained" not in ally.statuses
