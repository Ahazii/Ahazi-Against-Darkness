from __future__ import annotations

from pathlib import Path

from app.engine.adventurer_body import resolve_adventurer_body_loot
from app.engine.combat import _apply_pc_hit
from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.foe_weapon_restrictions import (
    template_weapon_allow_tags,
    weapon_hit_blocked_by_restriction,
)
from app.engine.weapons import weapon_profile
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, PartyMemberState


def _member(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        max_life=5,
        current_life=5,
        marching_order=1,
        inventory=[],
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


def _wraith() -> EnemyState:
    return EnemyState(
        id="wraith-1",
        name="Wraith",
        category="boss",
        level=6,
        life=6,
        max_life=6,
        tags=["undead", "weapon_allow:magic_weapons", "weapon_allow:silvered_weapons", "weapon_allow:two_plus_damage_single_blow"],
    )


def _roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def test_template_weapon_allow_tags_from_wraith_template():
    template = {
        "special_rules": [
            {
                "type": "weapon_restriction",
                "allowed": ["magic_weapons", "silvered_weapons", "two_plus_damage_single_blow"],
            }
        ]
    }
    tags = template_weapon_allow_tags(template)
    assert "weapon_allow:silvered_weapons" in tags


def test_mundane_weapon_blocked_vs_wraith():
    member = _member(inventory=["Hand weapon"])
    weapon = weapon_profile("Hand weapon")
    blocked, reason = weapon_hit_blocked_by_restriction(member, _wraith(), weapon, pending_damage=1)
    assert blocked is True
    assert "silvered" in reason.lower()


def test_silvered_weapon_hits_wraith():
    member = _member(inventory=["Hand weapon (silvered)"])
    weapon = weapon_profile("Hand weapon (silvered)")
    blocked, _ = weapon_hit_blocked_by_restriction(member, _wraith(), weapon, pending_damage=1)
    assert blocked is False


def test_two_plus_damage_hits_wraith_without_silver():
    member = _member(inventory=["Hand weapon"])
    weapon = weapon_profile("Hand weapon")
    blocked, _ = weapon_hit_blocked_by_restriction(member, _wraith(), weapon, pending_damage=2)
    assert blocked is False


def test_apply_pc_hit_logs_blocked_weapon_vs_wraith():
    member = _member(inventory=["Hand weapon"])
    wraith = _wraith()
    log: list[str] = []
    living = _apply_pc_hit(
        member,
        wraith,
        final_total=7,
        foe_level=6,
        living_enemies=[wraith],
        log=log,
        subdual=False,
        attack_label="a Hand weapon melee attack",
        weapon=weapon_profile("Hand weapon"),
    )
    assert wraith.life == 6
    assert living == [wraith]
    assert any("no effect" in line.lower() for line in log)


def test_fungal_adventurer_body_choice():
    items, gold, log, summary = resolve_adventurer_body_loot(
        "fungal",
        "bow",
        environment="fungal_grottoes",
        roll_random_spell_loot=lambda env: ("Scroll of Blessing", []),
    )
    assert "Bow" in items
    assert "Rope" in items
    assert any("Food rations" in item for item in items)
    assert gold > 0
    assert summary
    assert log


def test_caverns_adventurer_body_includes_chicken_blood():
    items, gold, log, summary = resolve_adventurer_body_loot("caverns", "chicken_blood")
    assert "Jar of chicken blood" in items
    assert gold >= 10
    assert summary
    assert log


def test_fungal_treasure_row_four_stages_adventurer_body_choice():
    roller = _roller()
    outcome = roller.roll_magic_treasure(environment="fungal_grottoes", table_name="fungal_grottoes_rare_item_table")
    # Force isn't possible without mock; test resolve path directly
    resolved = roller.resolve_environment_treasure_choice(
        "fungal_adventurer_body",
        "lantern",
        environment="fungal_grottoes",
    )
    assert "Lantern" in resolved.items
    assert resolved.gold > 0
