from __future__ import annotations

from app.engine.heroic_skill_effects import (
    bank_training_focus,
    consume_training_focus_bonus,
    deep_wound_extra_damage,
    heroic_attack_bonus,
    heroic_defense_bonus,
    rotate_aggressive_stance_penalty,
    training_focus_bonus_amount,
    weapon_matches_accuracy,
)
from app.engine.weapons import inventory_weapons
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _session(**kwargs) -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=kwargs.pop("party", []),
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        **kwargs,
    )


def _warrior(*skills: str) -> PartyMemberState:
    return PartyMemberState(
        character_id="w",
        name="Veteran",
        class_id="warrior",
        class_name="Warrior",
        level=10,
        xp=0,
        gold=0,
        current_life=8,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        learned_heroic_skills=list(skills),
    )


def test_heroic_accuracy_matches_weapon_type() -> None:
    member = _warrior("heroic_accuracy")
    member.expert_skill_targets = {"heroic_accuracy": "hand weapon"}
    member.inventory = ["Hand weapon"]
    weapon = inventory_weapons(member)[0]
    assert weapon_matches_accuracy(member, weapon, missile=False) is True
    assert heroic_attack_bonus(member, missile=False, living_foe_count=1, weapon=weapon) == 1


def test_legendary_battle_training_with_two_foes() -> None:
    member = _warrior("battle_training")
    member.learned_legendary_skills = ["legendary_battle_training"]
    bonus = heroic_attack_bonus(member, missile=False, living_foe_count=2)
    assert bonus == 2


def test_aggressive_and_defensive_stance_defense() -> None:
    member = _warrior("heroic_dodge", "defensive_stance")
    session = _session(party=[member], aggressive_stance_penalty=["w"])
    bonus = heroic_defense_bonus(
        member,
        single_attacker=True,
        defensive_stance=True,
        aggressive_stance_penalty=True,
    )
    assert bonus == 1


def test_deep_wound_vs_major_foe() -> None:
    member = _warrior("deep_wound")
    boss = EnemyState(id="b1", name="Ogre", category="boss", level=6, life=10, max_life=10)
    extra, log = deep_wound_extra_damage(member, boss)
    assert extra == 1
    assert log


def test_training_focus_banks_and_consumes() -> None:
    member = _warrior("training_focus")
    session = _session(party=[member])
    assert training_focus_bonus_amount(member) == 1
    assert bank_training_focus(session, member)
    assert session.training_focus_bonus["w"] == 1
    assert consume_training_focus_bonus(session, "w") == 1
    assert consume_training_focus_bonus(session, "w") == 0


def test_rotate_aggressive_stance_penalty() -> None:
    session = _session()
    rotate_aggressive_stance_penalty(session, {"a", "b"})
    assert set(session.aggressive_stance_penalty) == {"a", "b"}
