from __future__ import annotations

from app.engine import spells
from app.schemas import PartyMemberState


def test_expended_spell_stays_on_prepared_list() -> None:
    wizard = PartyMemberState(
        character_id="w",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=2,
        xp=0,
        gold=0,
        current_life=3,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Sleep", "Fireball"],
    )
    expended, uses, log = spells.mark_spell_expended(
        "Sleep",
        expended_spells=[],
        healing_prayer_uses=0,
    )
    assert wizard.spells == ["Sleep", "Fireball"]
    assert "Sleep" in expended
    assert not spells.can_cast_spell(wizard, "Sleep", expended_spells=expended, healing_prayer_uses=uses)
    assert spells.can_cast_spell(wizard, "Fireball", expended_spells=expended, healing_prayer_uses=uses)
    assert any("expended until this adventure ends" in line for line in log)
