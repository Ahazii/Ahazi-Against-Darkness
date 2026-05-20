from __future__ import annotations

from app.engine.class_combat import attack_modifier, defense_modifier, is_hated_by_foes, save_modifier
from app.schemas import EnemyState, PartyMemberState


def member(*, class_id: str, level: int = 3, name: str = "Hero") -> PartyMemberState:
    return PartyMemberState(
        character_id=class_id,
        name=name,
        class_id=class_id,
        class_name=class_id.title(),
        level=level,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )


def test_cleric_full_attack_vs_undead() -> None:
    cleric = member(class_id="cleric", level=4)
    skeleton = EnemyState(id="1", name="Skeleton", category="minions", level=3, life=1, max_life=1, tags=["undead"])
    assert attack_modifier(cleric, skeleton) == 4


def test_rogue_full_attack_vs_weak_minion() -> None:
    rogue = member(class_id="rogue", level=3)
    rat = EnemyState(id="1", name="Rat", category="vermin", level=1, life=1, max_life=1)
    assert attack_modifier(rogue, rat) == 3


def test_dwarf_hatred_vs_goblin() -> None:
    dwarf = member(class_id="dwarf", level=2)
    goblin = EnemyState(id="1", name="Goblin", category="minions", level=3, life=1, max_life=1)
    assert attack_modifier(dwarf, goblin) == 3


def test_elf_hatred_vs_orc() -> None:
    elf = member(class_id="elf", level=2)
    orc = EnemyState(id="1", name="Orc", category="minions", level=4, life=1, max_life=1)
    assert attack_modifier(elf, orc) == 3


def test_rogue_trap_save_uses_level() -> None:
    rogue = member(class_id="rogue", level=4)
    assert save_modifier(rogue, trap=True) == 4


def test_halfling_defense_vs_giant() -> None:
    halfling = member(class_id="halfling", level=3)
    ogre = EnemyState(id="1", name="Ogre", category="boss", level=5, life=6, max_life=6)
    assert defense_modifier(halfling, ogre) == 3


def test_cleric_hated_by_undead_foes() -> None:
    cleric = member(class_id="cleric")
    undead = EnemyState(id="1", name="Wraith", category="weird", level=4, life=3, max_life=3, tags=["undead"])
    assert is_hated_by_foes(cleric, [undead]) is True
