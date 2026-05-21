from __future__ import annotations

from pathlib import Path

from app.engine.equipment_shop import sell_quote
from app.engine.inventory import distribute_items_among
from app.engine.magic_weapons import (
    is_magic_weapon,
    magic_weapon_resale_gp,
    resolve_treasure_item_list,
    roll_magic_weapon_name,
)
from app.engine.weapons import (
    select_melee_weapon,
    set_weapon_default,
    weapon_attack_modifier,
)
from app.rules.repository import RulesRepository
from app.schemas import PartyMemberState


def warrior(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="war",
        name="Warrior",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        inventory=[],
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def test_roll_magic_weapon_types() -> None:
    name, roll = roll_magic_weapon_name(roll=4)
    assert roll == 4
    assert name == "Magic Sword (Hand weapon, +1 Attack)"


def test_resolve_treasure_placeholder() -> None:
    resolved, log = resolve_treasure_item_list(["Magic Weapon (+1 Attack)"], roll_fn=lambda: 3)
    assert resolved == ["Magic Mace (Hand weapon, +1 Attack)"]
    assert any("d6 = 3" in line for line in log)


def test_magic_weapon_adds_attack_bonus() -> None:
    member = warrior(inventory=["Magic Sword (Hand weapon, +1 Attack)"])
    weapon = select_melee_weapon(member)
    assert weapon is not None
    assert weapon_attack_modifier(weapon) == 1


def test_barbarian_cannot_set_magic_weapon_default() -> None:
    barbarian = warrior(
        character_id="barb",
        name="Barbarian",
        class_id="barbarian",
        class_name="Barbarian",
        inventory=["Magic Sword (Hand weapon, +1 Attack)"],
    )
    ok, message = set_weapon_default(barbarian, item_name="Magic Sword (Hand weapon, +1 Attack)", weapon_kind="melee")
    assert not ok
    assert "magic" in message.lower()


def test_distribute_skips_barbarian_for_magic_weapon() -> None:
    barbarian = warrior(
        character_id="barb",
        name="Barbarian",
        class_id="barbarian",
        class_name="Barbarian",
        marching_order=1,
    )
    cleric = warrior(
        character_id="cleric",
        name="Cleric",
        class_id="cleric",
        class_name="Cleric",
        marching_order=2,
    )
    uncarried, placed = distribute_items_among(
        [barbarian, cleric],
        ["Magic Sword (Hand weapon, +1 Attack)"],
    )
    assert not uncarried
    assert placed == ["Magic Sword (Hand weapon, +1 Attack)"]
    assert "Magic Sword (Hand weapon, +1 Attack)" in cleric.inventory
    assert "Magic Sword (Hand weapon, +1 Attack)" not in barbarian.inventory


def test_magic_weapon_resale_value() -> None:
    assert magic_weapon_resale_gp("Magic Sword (Hand weapon, +1 Attack)") == 112
    assert is_magic_weapon("Magic Sword (Hand weapon, +1 Attack)")


def test_magic_weapon_sell_quote() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    catalog = RulesRepository(packaged, packaged / "_override").equipment_shop()
    member = warrior(inventory=["Magic Bow (Bow, +1 Attack)"])
    quote = sell_quote(member, catalog, item_name="Magic Bow (Bow, +1 Attack)")
    assert quote["quote_gp"] == 130
