from __future__ import annotations

from app.engine import combat
from app.engine.combat import CombatContext, resolve_combat_round
from app.engine.weapons import (
    select_melee_weapon,
    select_missile_weapon,
    weapon_attack_modifier,
)
from app.schemas import EnemyState, PartyMemberState


def member(*, inventory: list[str] | None = None, marching_order: int = 1) -> PartyMemberState:
    return PartyMemberState(
        character_id="hero",
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
        marching_order=marching_order,
        inventory=inventory or [],
    )


def skeleton() -> EnemyState:
    return EnemyState(
        id="skel",
        name="Skeleton",
        category="minions",
        level=3,
        life=1,
        max_life=1,
        tags=["undead"],
    )


def goblin() -> EnemyState:
    return EnemyState(
        id="gob",
        name="Goblin",
        category="minions",
        level=3,
        life=3,
        max_life=3,
    )


def test_weapon_modifiers() -> None:
    heavy = select_melee_weapon(member(inventory=["Heavy weapon"]))
    light = select_melee_weapon(member(inventory=["Dagger"]))
    assert heavy is not None and weapon_attack_modifier(heavy, goblin()) == 1
    assert light is not None and weapon_attack_modifier(light, goblin()) == -1
    mace = select_melee_weapon(member(inventory=["Mace"]))
    assert mace is not None and weapon_attack_modifier(mace, skeleton()) == 1
    assert weapon_attack_modifier(None, goblin()) == -2


def test_opening_missile_volley_when_attacking_immediately(monkeypatch) -> None:
    rolls = iter([(6, [6]), (2, [2]), (3, [3])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: next(rolls, (3, [3])))
    ranger = member(inventory=["Bow", "Hand weapon"], marching_order=2)
    ranger.class_id = "ranger"
    tough = EnemyState(id="boss", name="Ogre", category="boss", level=8, life=6, max_life=6)
    result = resolve_combat_round(
        [ranger],
        [tough],
        show_rolls=True,
        party_attacked_immediately=True,
        encounter_round=0,
        missile_used=set(),
    )
    assert any("Opening missile volley" in line for line in result.log)
    missile_idx = next(i for i, line in enumerate(result.log) if "Opening missile" in line)
    defense_idx = next((i for i, line in enumerate(result.log) if "Defense roll" in line), None)
    if defense_idx is not None:
        assert missile_idx < defense_idx
    assert "hero" in (result.missile_used or set())


def test_no_opening_volley_after_reactions_first(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    ranger = member(inventory=["Bow", "Hand weapon"], marching_order=2)
    result = resolve_combat_round(
        [ranger],
        [goblin()],
        show_rolls=True,
        party_attacked_immediately=False,
        foes_strike_first=False,
        encounter_round=0,
        missile_used=set(),
    )
    assert all("Opening missile volley" not in line for line in result.log)


def test_room_missile_only_on_first_round(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    ranger = member(inventory=["Bow"], marching_order=1)
    missile_used = {"hero"}
    result = resolve_combat_round(
        [ranger],
        [goblin()],
        show_rolls=False,
        encounter_round=1,
        missile_used=missile_used,
    )
    assert all("Missile roll" not in line for line in result.log)
    assert any("melee" in line.lower() for line in result.log)


def test_corridor_rear_rank_missile(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    archer = member(inventory=["Bow"], marching_order=4)
    context = CombatContext(tile_type="corridor")
    result = resolve_combat_round(
        [archer],
        [goblin()],
        show_rolls=True,
        context=context,
        encounter_round=2,
        missile_used=set(),
    )
    assert any("Missile roll" in line for line in result.log)
    assert select_missile_weapon(archer) is not None


def test_corridor_front_rank_cannot_missile(monkeypatch) -> None:
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    front = member(inventory=["Bow", "Hand weapon"], marching_order=1)
    context = CombatContext(tile_type="corridor")
    result = resolve_combat_round(
        [front],
        [goblin()],
        show_rolls=False,
        context=context,
        encounter_round=0,
        missile_used=set(),
    )
    assert all("Missile roll" not in line for line in result.log)
