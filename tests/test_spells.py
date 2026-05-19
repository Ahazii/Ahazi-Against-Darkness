from __future__ import annotations

from pathlib import Path

from app.engine import combat, spells
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def wizard(*, spell_list: list[str] | None = None) -> PartyMemberState:
    return PartyMemberState(
        character_id="wiz",
        name="Marius",
        class_id="wizard",
        class_name="Wizard",
        level=4,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=spell_list or ["Fireball", "Sleep", "Protection"],
    )


def goblin_group(count: int = 5) -> list[EnemyState]:
    return [
        EnemyState(
            id=f"g{i}",
            name="Goblin",
            category="minions",
            level=3,
            life=1,
            max_life=1,
        )
        for i in range(count)
    ]


def test_fireball_slays_multiple_minions(monkeypatch) -> None:
    monkeypatch.setattr(spells, "roll_exploding_d6", lambda: (4, [4]))
    caster = wizard()
    enemies = goblin_group()
    outcome = spells.resolve_spell_cast("Fireball", caster, [caster], enemies, show_rolls=False)
    slain = sum(1 for enemy in outcome.enemies if enemy.life <= 0)
    assert slain >= 1
    assert outcome.spell_consumed is True


def test_protection_adds_status() -> None:
    caster = wizard(spell_list=["Protection"])
    ally = wizard(spell_list=[])
    ally.character_id = "ally"
    ally.name = "Ally"
    outcome = spells.resolve_spell_cast(
        "Protection",
        caster,
        [caster, ally],
        goblin_group(1),
        target_character_id="ally",
        show_rolls=False,
    )
    assert "Protection" in outcome.party[1].statuses


def test_cast_spell_in_session(monkeypatch) -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")

    caster = wizard(spell_list=["Sleep"])
    foe = EnemyState(id="ogre", name="Ogre", category="boss", level=4, life=6, max_life=6)
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[caster],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[foe],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    monkeypatch.setattr(spells, "roll_exploding_d6", lambda: (6, [6]))
    engine.advance(session, "cast_spell", character_id="wiz", spell_name="Sleep")
    assert any("Sleep" in entry for entry in session.log)
    assert "Sleep" in session.party[0].spells
    assert "Sleep" in session.expended_spells.get("wiz", [])


def test_healing_prayer_allows_three_uses() -> None:
    cleric = PartyMemberState(
        character_id="c",
        name="Cleric",
        class_id="cleric",
        class_name="Cleric",
        level=2,
        xp=0,
        gold=0,
        current_life=2,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Healing prayer"],
    )
    ally = PartyMemberState(
        character_id="a",
        name="Ally",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=1,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[cleric, ally],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    for _ in range(3):
        assert spells.can_cast_spell(
            cleric,
            "Healing prayer",
            expended_spells=session.expended_spells.get("cleric", []),
            healing_prayer_uses=session.healing_prayer_uses.get("cleric", 0),
        )
        expended, uses, _ = spells.mark_spell_expended(
            "Healing prayer",
            expended_spells=list(session.expended_spells.get("cleric", [])),
            healing_prayer_uses=session.healing_prayer_uses.get("cleric", 0),
        )
        session.expended_spells["cleric"] = expended
        session.healing_prayer_uses["cleric"] = uses
    assert "Healing prayer" in cleric.spells
    assert not spells.can_cast_spell(
        cleric,
        "Healing prayer",
        expended_spells=session.expended_spells.get("cleric", []),
        healing_prayer_uses=session.healing_prayer_uses.get("cleric", 0),
    )


def test_protection_bonus_applies_to_defense() -> None:
    member = wizard()
    member.statuses = ["Protection"]
    enemy = EnemyState(id="1", name="Goblin", category="minions", level=3, life=1, max_life=1)
    modifier, _ = combat._defense_bonus(member, enemy, context=combat.CombatContext())
    assert modifier >= 1
