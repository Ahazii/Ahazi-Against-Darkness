"""TCOTFD trained Surgeon / Herbalist / Poison Expert expert skills."""

from __future__ import annotations

from pathlib import Path

from app.engine.courtship_professional_skills import (
    TRAINED_HERBALIST,
    TRAINED_POISON_EXPERT,
    TRAINED_SURGEON,
    member_has_arsenic,
    use_trained_herbalist,
    use_trained_poison_expert,
    use_trained_surgeon_heal,
)
from app.engine.expert_skills import eligible_expert_skills, has_skill
from app.engine.hirelings import professional_save_bonus
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import PartyMemberState


def _engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _member(
    *,
    class_id: str = "wandering_alchemist",
    class_name: str = "Wandering Alchemist",
    level: int = 6,
    character_id: str = "a1",
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name="Test Hero",
        class_id=class_id,
        class_name=class_name,
        level=level,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
        learned_expert_skills=[TRAINED_SURGEON],
    )


def test_eligible_trained_skills_for_alchemist_and_conservationist() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    catalog = RulesRepository(packaged, packaged / "_override").expert_skills()
    alchemist = _member()
    alchemist.learned_expert_skills = []
    conservationist = _member(class_id="conservationist", class_name="Conservationist", character_id="c1")
    conservationist.learned_expert_skills = []

    alchemist_ids = {skill["id"] for skill in eligible_expert_skills(alchemist, catalog)}
    assert TRAINED_SURGEON in alchemist_ids
    assert TRAINED_HERBALIST in alchemist_ids
    assert TRAINED_POISON_EXPERT in alchemist_ids

    cons_ids = {skill["id"] for skill in eligible_expert_skills(conservationist, catalog)}
    assert TRAINED_SURGEON in cons_ids
    assert TRAINED_HERBALIST in cons_ids
    assert TRAINED_POISON_EXPERT not in cons_ids


def test_trained_surgeon_heals_party_once_per_adventure() -> None:
    eng = _engine()
    surgeon = _member()
    ally = _member(character_id="a2", class_id="warrior", class_name="Warrior")
    ally.current_life = 2
    ally.learned_expert_skills = []
    session = eng.create_session("surgeon-heal", "party-1", [surgeon, ally])
    session.mode = "exploration"

    first = use_trained_surgeon_heal(session, surgeon.character_id)
    assert any("stitches wounds" in line for line in first)
    assert ally.current_life == 4

    second = use_trained_surgeon_heal(session, surgeon.character_id)
    assert any("already tended" in line for line in second)


def test_trained_herbalist_applies_save_buff_at_camp() -> None:
    eng = _engine()
    herbalist = _member()
    herbalist.learned_expert_skills = [TRAINED_HERBALIST]
    session = eng.create_session("herbalist", "party-1", [herbalist])
    session.camped_outside = True

    logs = use_trained_herbalist(session, herbalist.character_id)
    assert any("herbal remedies" in line for line in logs)
    assert session.professional_buffs.get("herbalist_saves")
    assert professional_save_bonus(session, poison=True) == 1


def test_trained_poison_expert_requires_arsenic() -> None:
    eng = _engine()
    alchemist = _member()
    alchemist.learned_expert_skills = [TRAINED_POISON_EXPERT]
    rogue = _member(character_id="r1", class_id="rogue", class_name="Rogue")
    rogue.inventory = ["Scimitar"]
    session = eng.create_session("poison", "party-1", [alchemist, rogue])
    session.camped_outside = True

    blocked = use_trained_poison_expert(
        session,
        alchemist.character_id,
        target_character_id=rogue.character_id,
        item_name="Scimitar",
    )
    assert any("arsenic" in line.lower() for line in blocked)

    alchemist.inventory = ["Arsenic (mineral ingredient)"]
    ok = use_trained_poison_expert(
        session,
        alchemist.character_id,
        target_character_id=rogue.character_id,
        item_name="Scimitar",
    )
    assert any("envenoms" in line.lower() or "coats" in line.lower() for line in ok)
    assert not member_has_arsenic(alchemist)
    assert has_skill(alchemist, TRAINED_POISON_EXPERT)
