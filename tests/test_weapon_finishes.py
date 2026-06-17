from __future__ import annotations

from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.equipment_effects import silver_gild_attack_bonus
from app.engine.equipment_shop import buy_equipment, sell_quote
from app.engine.class_combat import armor_defense_bonus
from app.engine.magic_armor import mundane_armor_defense_bonus
from app.engine.weapon_finishes import (
    apply_weapon_finish,
    apply_weapon_service_to_character,
    build_fiendish_treasure_weapon,
    format_leafsteel_armor,
    is_weapon_item_gilded,
    is_weapon_item_silvered,
    roll_two_in_six,
    tick_leafsteel_after_adventure,
    weapon_finish_resale_bonus,
)
from app.rules.repository import RulesRepository
from app.schemas import Character, EnemyState, PartyMemberState
from pathlib import Path


def _member(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        max_life=5,
        current_life=5,
        marching_order=1,
        inventory=[],
        statuses=[],
        spells=[],
        learned_expert_skills=[],
        gold=20,
        clues=0,
        xp=0,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _character(**overrides) -> Character:
    base = dict(
        id="char-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        max_life=5,
        current_life=5,
        gold=200,
        inventory=["Hand weapon"],
        statuses=[],
        spells=[],
        abilities=[],
        class_traits=[],
        secrets=[],
        madness=0,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
        clues=0,
        xp=0,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    base.update(overrides)
    return Character(**base)


def _roller() -> DungeonTableRoller:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())


def test_apply_weapon_finishes_and_resale_bonus():
    silvered = apply_weapon_finish("Hand weapon", "silvered")
    assert is_weapon_item_silvered(silvered)
    assert weapon_finish_resale_bonus(silvered) == 20
    gilded = apply_weapon_finish("Two-handed weapon", "gilded")
    assert is_weapon_item_gilded(gilded)
    assert weapon_finish_resale_bonus(gilded) == 50


def test_shop_silvering_tags_specific_weapon():
    character = _character(inventory=["Hand weapon", "Bow"])
    catalog = {"items": [{"key": "silvering_light", "name": "Silvering (light/hand/quiver)", "price_gp": 20, "category": "service"}]}
    ok, message = buy_equipment(character, catalog, item_key="silvering_light", target_weapon="Hand weapon")
    assert ok, message
    assert any(is_weapon_item_silvered(item) for item in character.inventory)
    assert not any(is_weapon_item_silvered(item) for item in character.inventory if "bow" in item.lower())


def test_shop_gilding_tags_specific_weapon():
    character = _character(inventory=["Sling"])
    catalog = {"items": [{"key": "gilding", "name": "Gilding", "price_gp": 50, "category": "service"}]}
    ok, message = buy_equipment(character, catalog, item_key="gilding", target_weapon="Sling")
    assert ok, message
    assert character.inventory == ["Sling (gilded)"]


def test_silver_gild_bonus_uses_wielded_weapon_only():
    member = _member(inventory=["Hand weapon (silvered)", "Bow"])
    werewolf = EnemyState(id="f1", name="Werewolf", category="weird", life=3, max_life=3, level=4, tags=["were"])
    with_silver = silver_gild_attack_bonus(member, werewolf, weapon_item="Hand weapon (silvered)")
    without_silver = silver_gild_attack_bonus(member, werewolf, weapon_item="Bow")
    assert with_silver == 1
    assert without_silver == 0


def test_fiendish_treasure_row_three_choice_flow():
    roller = _roller()
    outcome = roller.resolve_environment_treasure_choice("fiendish_scroll_or_weapon", "weapon")
    assert outcome.choice_key == "fiendish_weapon_pick"
    weapon_outcome = roller.resolve_environment_treasure_choice(
        "fiendish_weapon_pick",
        "hand_weapon",
        environment="dungeon",
    )
    assert weapon_outcome.items
    assert "Hand weapon" in weapon_outcome.items[0]
    assert any("Silvered weapon chance" in line for line in weapon_outcome.log)


def test_fiendish_weapon_build_silvered():
    weapon, _ = build_fiendish_treasure_weapon("bow", silvered=True)
    assert weapon == "Bow (silvered)"


def test_fungal_leafsteel_choice_and_decay():
    roller = _roller()
    outcome = roller.resolve_environment_treasure_choice("fungal_gem_or_leafsteel", "leafsteel")
    assert outcome.items == [format_leafsteel_armor(3)]
    member = _member(inventory=[format_leafsteel_armor(3)])
    assert mundane_armor_defense_bonus(member) == 2
    assert armor_defense_bonus(member) == 2
    logs = tick_leafsteel_after_adventure(member)
    assert any("2 adventure" in line for line in logs)
    assert member.inventory == [format_leafsteel_armor(2)]


def test_roll_two_in_six():
    success, value, log = roll_two_in_six(roll_fn=lambda: 2)
    assert success is True
    assert value == 2
    assert log
