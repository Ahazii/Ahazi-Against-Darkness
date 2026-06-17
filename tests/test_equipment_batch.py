from __future__ import annotations

from app.engine.consumables import throw_acid_vial, throw_holy_water
from app.engine.equipment_effects import (
    TALISMAN_ARMED_STATUS,
    TALISMAN_SAVE_STATUS,
    arm_talisman_save,
    enforce_single_pole_carrier,
    finalize_talisman_after_save,
)
from app.engine.firearm import firearm_broken, gnome_repair_firearm, misfire_firearm
from app.engine.hunger import eat_food_ration
from app.engine.weapons import _parse_weapon_item, crossbow_needs_reload, mark_crossbow_needs_reload, weapon_attack_modifier
from app.schemas import EnemyState, PartyMemberState, SessionState


def _member(**kwargs) -> PartyMemberState:
    base = dict(
        character_id="h1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
        inventory=[],
    )
    base.update(kwargs)
    return PartyMemberState(**base)


def _enemy(**kwargs) -> EnemyState:
    base = dict(
        id="e1",
        name="Skeleton",
        category="minions",
        level=2,
        life=2,
        max_life=2,
        tags=["undead"],
    )
    base.update(kwargs)
    return EnemyState(**base)


def test_bow_is_two_slot_not_two_handed() -> None:
    profile = _parse_weapon_item("Bow")
    assert profile is not None
    assert profile.two_slot is True
    assert profile.two_handed is False
    assert profile.slashing is True


def test_crossbow_slashing_plus_one() -> None:
    profile = _parse_weapon_item("Crossbow")
    assert profile is not None
    assert profile.slashing is True
    enemy = _enemy()
    mod = weapon_attack_modifier(profile, enemy)
    assert mod == 1


def test_sling_is_crushing() -> None:
    profile = _parse_weapon_item("Sling")
    assert profile is not None
    assert profile.crushing is True


def test_enforce_single_pole_carrier() -> None:
    party = [
        _member(character_id="a", inventory=["10' pole"]),
        _member(character_id="b", name="B", inventory=["10' pole", "Dagger"]),
    ]
    logs = enforce_single_pole_carrier(party)
    assert any("pole" in line.lower() for line in logs)
    assert not any("10' pole" in item for item in party[1].inventory)


def test_holy_water_auto_damage_undead() -> None:
    thrower = _member()
    target = _enemy()
    log, ok = throw_holy_water(thrower, target, show_rolls=False)
    assert ok
    assert target.life == 1
    assert any("1 Life" in line for line in log)


def test_acid_vial_self_splash_on_one(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.consumables.roll_d6", lambda: 1)
    thrower = _member()
    target = _enemy(name="Orc", tags=[])
    log, ok = throw_acid_vial(thrower, target, show_rolls=False)
    assert ok
    assert thrower.current_life == 3
    assert target.life == 2


def test_eat_food_ration() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member(inventory=["Food ration"])],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        hunger_rounds={"h1": 20},
        created_at="t",
        updated_at="t",
    )
    logs = eat_food_ration(session, session.party[0], session.party)
    assert session.hunger_rounds["h1"] == 0
    assert "Food ration" not in session.party[0].inventory
    assert logs


def test_talisman_arm_and_consume() -> None:
    member = _member(statuses=[TALISMAN_SAVE_STATUS], inventory=["Talisman"])
    ok, _ = arm_talisman_save(member)
    assert ok
    assert TALISMAN_ARMED_STATUS in member.statuses
    logs = finalize_talisman_after_save(member)
    assert logs
    assert "Talisman" not in member.inventory


def test_firearm_misfire_and_gnome_repair() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            _member(character_id="g", class_id="gnome", class_name="Gnome", inventory=["Handgun"]),
            _member(character_id="w", name="Shooter", inventory=["Handgun"]),
        ],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        created_at="t",
        updated_at="t",
    )
    shooter = session.party[1]
    session.log.extend(misfire_firearm(session, shooter, "Handgun"))
    assert firearm_broken(session, shooter)
    logs = gnome_repair_firearm(session, session.party[0], shooter)
    assert any("repair" in line.lower() for line in logs)
    assert not firearm_broken(session, shooter)


def test_crossbow_reload_tracking() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member()],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        created_at="t",
        updated_at="t",
    )
    member = session.party[0]
    mark_crossbow_needs_reload(session, member)
    assert crossbow_needs_reload(session, member)
