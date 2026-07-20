from __future__ import annotations

from pathlib import Path

from app.engine.class_combat import armor_defense_bonus
from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.gremlin_events import apply_gremlin_repellant, resolve_invisible_gremlins
from app.rules.repository import RulesRepository
from app.engine.magic_armor import is_magic_armor, magic_armor_defense_bonus, resolve_magic_armor_placeholder
from app.engine.magic_weapons import resolve_treasure_item_list
from app.engine.special_items import (
    consume_prayer_bead,
    equip_glittering_crystal,
    format_prayer_bead_necklace,
    member_has_light_source,
    resolve_special_treasure_items,
)
from app.schemas import EnemyState, PartyMemberState, SessionState


def _member(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        max_life=5,
        current_life=3,
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


def test_magic_armor_defense_bonus_stacks_with_mundane():
    member = _member(inventory=["Heavy armor", "Magic Shield (+1 Defense)"])
    assert magic_armor_defense_bonus(member) == 1
    assert armor_defense_bonus(member) == 3


def test_resolve_fiendish_magic_armor_placeholder():
    name, rolled = resolve_magic_armor_placeholder("Magic Armor (+1 or +2 Defense)", roll_fn=lambda: 6)
    assert rolled == 6
    assert is_magic_armor(name)
    assert "+2 Defense" in name or "+1 Defense" in name


def test_resolve_treasure_magic_armor_and_prayer_beads():
    items, log = resolve_treasure_item_list(["Magic Armor (+1 or +2 Defense)"], roll_fn=lambda: 4)
    assert items and is_magic_armor(items[0])
    assert any("Fiendish magic armor" in line for line in log)

    resolved, bead_log = resolve_special_treasure_items(["Necklace with d6 Prayer Beads"], roll_fn=lambda: 4)
    assert resolved == [format_prayer_bead_necklace(4)]
    assert any("Prayer beads" in line for line in bead_log)


def test_prayer_bead_only_when_opted_in():
    cleric = _member(class_id="cleric", inventory=["Necklace with 2 prayer beads"])
    used, _saved, log = consume_prayer_bead(cleric)
    assert used is True
    assert log
    assert prayer_bead_count(cleric) == 1


def test_prayer_bead_necklace_helper():
    cleric = _member(class_id="cleric", inventory=["Necklace with 3 prayer beads"])
    from app.engine.special_items import member_has_prayer_bead_necklace

    assert member_has_prayer_bead_necklace(cleric)


def test_glittering_crystal_counts_as_light_source():
    member = _member(statuses=[])
    assert member_has_light_source(member) is False
    equip_glittering_crystal(member)
    assert member_has_light_source(member) is True


def test_fiendish_foes_treasure_table_rolls():
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    roller = DungeonTableRoller(RulesRepository(packaged, packaged / "_override").dungeon_tables())
    outcome = roller.roll_fiendish_foes_treasure(treasure_bonus=0)
    assert outcome.log
    assert "Fiendish Foes treasure roll" in outcome.log[0]


def test_gremlin_repellant_blocks_steal():
    member = _member(inventory=["Gremlin repellant", "Magic Sword (+1 Attack)"])
    session = _session([member])
    session.camped_outside = True
    applied = apply_gremlin_repellant(
        session,
        repellant_owner=member,
        target=member,
        item_name="Magic Sword (+1 Attack)",
    )
    session.camped_outside = False
    log = resolve_invisible_gremlins(session, [member])
    assert any("protected" in line.lower() for line in applied)
    assert not any("gremlin repellant" in item.lower() for item in member.inventory)
    assert "Magic Sword (+1 Attack)" in member.inventory
    assert not any("Magic Sword" in line for line in log)


def test_gremlins_steal_magic_first():
    member = _member(inventory=["Dagger", "Magic Sword (+1 Attack)"], gold=0)
    session = _session([member])
    log = resolve_invisible_gremlins(session, [member], roll_fn=lambda: 6)
    assert any("Magic Sword" in line for line in log)
    assert not any("magic sword" in item.lower() for item in member.inventory)


def test_scroll_tube_protects_first_three_scrolls():
    member = _member(
        inventory=[
            "Scroll tube",
            "Scroll of Fireball",
            "Scroll of Sleep",
            "Scroll of Blessing",
            "Scroll of Escape",
            "Dagger",
        ],
        gold=0,
    )
    session = _session([member])
    log = resolve_invisible_gremlins(session, [member], roll_fn=lambda: 6)
    assert any("Scroll of Escape" in line for line in log)
    assert "Scroll of Escape" not in member.inventory
    assert "Scroll of Fireball" in member.inventory
    assert "Scroll of Sleep" in member.inventory
    assert "Scroll of Blessing" in member.inventory


def prayer_bead_count(member: PartyMemberState) -> int:
    from app.engine.special_items import prayer_bead_count as count

    necklace = next((item for item in member.inventory if "prayer bead" in item.lower()), "")
    return count(necklace) if necklace else 0
