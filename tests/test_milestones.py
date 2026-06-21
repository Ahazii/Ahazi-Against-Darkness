from __future__ import annotations

from app.engine.milestones import (
    assign_milestone,
    bind_scroll_librarian,
    craft_gem_collector_jewelry,
    create_panoplia,
    milestone_attack_bonus,
    milestone_spellcasting_bonus,
    pay_thrice_blessed_sacrifice,
    record_defeated_foes,
    record_lightning_damage,
    record_sleep_levels,
    thrice_blessed_save_active,
    use_panoplia_favor,
)
from app.schemas import EnemyState, MilestonesProgress, PartyMemberState


def _member(
    *,
    class_id: str = "warrior",
    milestones: MilestonesProgress | None = None,
    inventory: list[str] | None = None,
    gold: int = 500,
    level: int = 5,
) -> PartyMemberState:
    return PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id=class_id,
        class_name=class_id.title(),
        level=level,
        xp=0,
        gold=gold,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=list(inventory or []),
        milestones=milestones or MilestonesProgress(),
    )


def _goblin(level: int = 1) -> EnemyState:
    return EnemyState(
        id=f"g{level}",
        name="Goblin",
        category="minions",
        level=level,
        life=0,
        max_life=1,
        tags=["goblin"],
    )


def test_goblinslayer_progresses_and_completes() -> None:
    member = _member(milestones=MilestonesProgress(active_id="goblinslayer"))
    logs = record_defeated_foes([member], [_goblin(35), _goblin(35)])
    assert member.milestones.levels_goblins == 70
    assert "goblinslayer" in member.milestones.completed_ids
    assert member.milestones.active_id is None
    assert any("Milestone complete" in line for line in logs)


def test_goblinslayer_attack_bonus_after_completion() -> None:
    member = _member(milestones=MilestonesProgress(completed_ids=["goblinslayer"]))
    assert milestone_attack_bonus(member, _goblin()) == 1


def test_thundermaster_requires_exploding_lightning() -> None:
    caster = _member(class_id="wizard", milestones=MilestonesProgress(active_id="thundermaster"))
    record_lightning_damage(caster, 20, exploded=False)
    assert caster.milestones.active_id == "thundermaster"
    record_lightning_damage(caster, 0, exploded=True)
    assert "thundermaster" in caster.milestones.completed_ids


def test_slumbermaster_tracks_sleep_levels() -> None:
    caster = _member(class_id="wizard", milestones=MilestonesProgress(active_id="slumbermaster"))
    record_sleep_levels(caster, 100)
    assert "slumbermaster" in caster.milestones.completed_ids
    assert milestone_spellcasting_bonus(caster, "sleep") == 1


def test_scroll_librarian_bind_grants_spell_slot() -> None:
    scrolls = ["Scroll of Blessing"] * 20
    member = _member(
        class_id="wizard",
        milestones=MilestonesProgress(active_id="scroll_librarian", scrolls_collected=20),
        inventory=scrolls,
    )
    logs = bind_scroll_librarian(member, "Blessing")
    assert "scroll_librarian" in member.milestones.completed_ids
    assert "Blessing" in member.spells
    assert "Blessing" in member.milestones.extra_spell_slots
    assert any("binds" in line for line in logs)


def test_gem_collector_crafts_jewelry_at_one_fifty_percent() -> None:
    gems = [f"Ruby gem ({index}) (50gp)" for index in range(10)]
    member = _member(
        milestones=MilestonesProgress(active_id="gem_collector", gems_50gp=10),
        inventory=gems,
    )
    craft_gem_collector_jewelry(member)
    assert "gem_collector" in member.milestones.completed_ids
    assert any("Jewelry (milestone, 750gp)" in item for item in member.inventory)


def test_panoplia_and_favor_flow() -> None:
    member = _member(
        milestones=MilestonesProgress(active_id="panoplia", panoplia_ready_inventory=True),
        inventory=["Magic weapon +1", "Magic shield +1", "Magic armor +1"],
        gold=200,
    )
    create_panoplia(member)
    assert member.gold == 100
    assert member.milestones.panoplia_favor_available
    use_panoplia_favor(member, "gold")
    assert member.gold == 400
    assert member.milestones.panoplia_favor_used


def test_thrice_blessed_sacrifice_unlocks_save_bonus() -> None:
    member = _member(
        level=4,
        gold=100,
        milestones=MilestonesProgress(thrice_blessed_unlocked=True),
    )
    assert not thrice_blessed_save_active(member)
    pay_thrice_blessed_sacrifice(member)
    assert member.gold == 60
    assert thrice_blessed_save_active(member)


def test_assign_milestone_rejects_completed() -> None:
    member = _member(milestones=MilestonesProgress(completed_ids=["goblinslayer"]))
    logs = assign_milestone(member, "goblinslayer")
    assert any("already completed" in line for line in logs)
