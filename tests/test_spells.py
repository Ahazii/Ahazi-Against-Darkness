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


def druid(*, spell_list: list[str] | None = None) -> PartyMemberState:
    member = wizard(spell_list=spell_list or ["Water Jet"])
    member.character_id = "druid"
    member.name = "Oak"
    member.class_id = "druid"
    member.class_name = "Druid"
    member.level = 3
    return member


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
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
    caster = wizard()
    enemies = goblin_group()
    outcome = spells.resolve_spell_cast("Fireball", caster, [caster], enemies, show_rolls=False)
    slain = sum(1 for enemy in outcome.enemies if enemy.life <= 0)
    assert slain >= 1
    assert outcome.spell_consumed is True


def test_fireball_major_foe_level_drop_happens_once(monkeypatch) -> None:
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    caster = wizard()
    boss = EnemyState(id="boss", name="Ogre", category="boss", level=5, life=4, max_life=6)

    first = spells.resolve_spell_cast("Fireball", caster, [caster], [boss], show_rolls=False)
    assert first.enemies[0].life == 3
    assert first.enemies[0].level == 4
    assert first.enemies[0].level_drop_applied is True

    second = spells.resolve_spell_cast("Fireball", caster, [caster], [boss], show_rolls=False)
    assert second.enemies[0].life == 2
    assert second.enemies[0].level == 4


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


def test_holy_symbol_of_healing_adds_two_life(monkeypatch) -> None:
    caster = wizard(spell_list=["Healing prayer"])
    caster.class_id = "cleric"
    caster.class_name = "Cleric"
    caster.inventory = ["Holy symbol of healing (+2 Life from Healing prayer)"]
    ally = wizard(spell_list=[])
    ally.character_id = "ally"
    ally.name = "Ally"
    ally.current_life = 1
    ally.max_life = 8
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (2, [2]))

    outcome = spells.resolve_spell_cast(
        "Healing prayer",
        caster,
        [caster, ally],
        [],
        target_character_id="ally",
        show_rolls=True,
    )

    assert outcome.party[1].current_life == 8
    assert any("Holy symbol of healing adds +2 Life" in entry for entry in outcome.log)
    assert any("+ 2 holy symbol" in entry for entry in outcome.log)


def test_summon_beast_log_keeps_pdf_flavor_text() -> None:
    caster = druid(spell_list=["Summon Beast"])
    outcome = spells.resolve_spell_cast("Summon Beast", caster, [caster], goblin_group(1), show_rolls=False)

    assert outcome.spell_consumed is True
    assert outcome.summon_beast is True
    assert any("large animal (boar, large cat, bear)" in entry for entry in outcome.log)


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
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    engine.advance(session, "cast_spell", character_id="wiz", spell_name="Sleep")
    assert any("Sleep" in entry for entry in session.log)
    assert "Sleep" in session.party[0].spells
    assert "Sleep" in session.expended_spells.get("wiz", [])


def test_sleep_immunity_names_undead_target() -> None:
    caster = wizard(spell_list=["Sleep"])
    wraith = EnemyState(
        id="wraith",
        name="Wraith",
        category="weird",
        level=4,
        life=3,
        max_life=3,
        tags=["undead", "spirit"],
    )

    outcome = spells.resolve_spell_cast("Sleep", caster, [caster], [wraith], show_rolls=False)

    assert outcome.enemies[0].life == 3
    assert any(
        "Effect: Sleep has no effect on Wraith "
        "(immune by Level 11+ or undead/dragon/artificial/construct/elemental/spirit trait)."
        in line
        for line in outcome.log
    )


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


def test_blessing_clears_session_curse() -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    cleric = PartyMemberState(
        character_id="cleric",
        name="Cleric",
        class_id="cleric",
        class_name="Cleric",
        level=2,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Blessing"],
    )
    cursed = wizard()
    cursed.character_id = "cursed"
    cursed.name = "Cursed Hero"
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[cleric, cursed],
        cursed_character_id="cursed",
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
    engine.advance(
        session,
        "cast_spell",
        character_id="cleric",
        spell_name="Blessing",
        target_character_id="cursed",
    )
    assert session.cursed_character_id is None
    assert any("Blessing removes curses" in entry for entry in session.log)


def test_healing_prayer_targets_ally() -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    cleric = PartyMemberState(
        character_id="cleric",
        name="Cleric",
        class_id="cleric",
        class_name="Cleric",
        level=2,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Healing prayer"],
    )
    ally = wizard()
    ally.character_id = "ally"
    ally.name = "Ally"
    ally.current_life = 2
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
    engine.advance(
        session,
        "cast_spell",
        character_id="cleric",
        spell_name="Healing prayer",
        target_character_id="ally",
    )
    assert session.party[1].current_life > 2
    assert any("Ally" in entry and "Life" in entry for entry in session.log)


def test_fireball_requires_aim_when_mixed() -> None:
    caster = wizard(spell_list=["Fireball"])
    enemies = goblin_group(2) + [
        EnemyState(id="ogre", name="Ogre", category="boss", level=4, life=6, max_life=6),
    ]
    outcome = spells.resolve_spell_cast("Fireball", caster, [caster], enemies, show_rolls=False)
    assert any("cannot hit both groups" in entry.lower() for entry in outcome.log)
    assert outcome.spell_consumed is False


def test_fireball_single_leaves_minions(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
    caster = wizard(spell_list=["Fireball"])
    enemies = goblin_group(3) + [
        EnemyState(id="ogre", name="Ogre", category="boss", level=4, life=6, max_life=6),
    ]
    outcome = spells.resolve_spell_cast(
        "Fireball",
        caster,
        [caster],
        enemies,
        show_rolls=False,
        target_foe_id="ogre",
        spell_target_mode="single",
    )
    ogre = next(enemy for enemy in outcome.enemies if enemy.id == "ogre")
    goblins_alive = sum(1 for enemy in outcome.enemies if enemy.id.startswith("g") and enemy.life > 0)
    assert ogre.life == 5
    assert goblins_alive == 3
    assert any("aimed at ogre" in entry.lower() for entry in outcome.log)


def test_fireball_minions_slay_multiple(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
    caster = wizard(spell_list=["Fireball"])
    enemies = goblin_group(5)
    outcome = spells.resolve_spell_cast(
        "Fireball",
        caster,
        [caster],
        enemies,
        show_rolls=False,
        spell_target_mode="minions",
    )
    slain = sum(1 for enemy in outcome.enemies if enemy.life <= 0)
    assert slain >= 2
    assert any("aimed at minions" in entry.lower() for entry in outcome.log)


def test_fireball_mummy_plus_two(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (3, [3]))
    caster = wizard(spell_list=["Fireball"])
    mummy = EnemyState(id="m", name="Mummy", category="boss", level=8, life=6, max_life=6)
    outcome = spells.resolve_spell_cast("Fireball", caster, [caster], [mummy], show_rolls=True)
    assert mummy.life == 5
    assert any("Fireball gains +2 vs Mummy" in line for line in outcome.log)


def test_fireball_non_mummy_same_roll_misses(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (3, [3]))
    caster = wizard(spell_list=["Fireball"])
    ogre = EnemyState(id="o", name="Ogre", category="boss", level=8, life=6, max_life=6)
    outcome = spells.resolve_spell_cast("Fireball", caster, [caster], [ogre], show_rolls=False)
    assert ogre.life == 6
    assert any("misses" in line.lower() for line in outcome.log)


def test_lightning_targets_chosen_foe(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    caster = wizard(spell_list=["Lightning"])
    enemies = [
        EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1),
        EnemyState(id="ogre", name="Ogre", category="boss", level=4, life=6, max_life=6),
    ]
    outcome = spells.resolve_spell_cast(
        "Lightning",
        caster,
        [caster],
        enemies,
        show_rolls=False,
        target_foe_id="ogre",
    )
    ogre = next(enemy for enemy in outcome.enemies if enemy.id == "ogre")
    goblin = next(enemy for enemy in outcome.enemies if enemy.id == "g1")
    assert ogre.life == 4
    assert goblin.life == 1


def test_fireball_on_iron_door_without_foes() -> None:
    caster = wizard(spell_list=["Fireball"])
    outcome = spells.resolve_spell_cast(
        "Fireball",
        caster,
        [caster],
        [],
        show_rolls=False,
        door_type="iron",
    )
    assert outcome.destroy_door is True
    assert outcome.spell_consumed is True
    assert any("destroys the iron door" in line.lower() for line in outcome.log)
    assert not any("no targets" in line.lower() for line in outcome.log)


def test_lightning_on_iron_door_without_foes() -> None:
    caster = wizard(spell_list=["Lightning"])
    outcome = spells.resolve_spell_cast(
        "Lightning",
        caster,
        [caster],
        [],
        show_rolls=False,
        door_type="iron",
    )
    assert outcome.destroy_door is True
    assert outcome.spell_consumed is True
    assert any("destroys the iron door" in line.lower() for line in outcome.log)
    assert not any("no targets" in line.lower() for line in outcome.log)


def test_water_jet_requires_explicit_effect_choice() -> None:
    caster = druid()
    foe = EnemyState(id="ogre", name="Ogre", category="boss", level=4, life=6, max_life=6)

    outcome = spells.resolve_spell_cast("Water Jet", caster, [caster], [foe], show_rolls=False)

    assert outcome.spell_consumed is False
    assert foe.life == 6
    assert any("Choose Water Jet effect" in line for line in outcome.log)


def test_water_jet_fire_effect_rolls_against_target_level_and_deals_two(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
    caster = druid()
    fire = EnemyState(id="f", name="Fire Elemental", category="weird", level=6, life=5, max_life=5, tags=["fire"])

    outcome = spells.resolve_spell_cast(
        "Water Jet",
        caster,
        [caster],
        [fire],
        spell_target_mode="fire",
        target_foe_id="f",
        show_rolls=True,
    )

    assert fire.life == 3
    assert outcome.spell_consumed is True
    assert any("Water Jet (connect): Oak rolls 4 + 3 = 7 vs L6." in line for line in outcome.log)
    assert any("Water Jet inflicts 2 damage" in line for line in outcome.log)


def test_water_jet_disperses_two_vermin_after_hit(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
    caster = druid()
    vermin = [
        EnemyState(id=f"r{i}", name="Rat", category="vermin", level=2, life=1, max_life=1)
        for i in range(3)
    ]

    outcome = spells.resolve_spell_cast(
        "Water Jet",
        caster,
        [caster],
        vermin,
        spell_target_mode="vermin",
        target_foe_id="r0",
        show_rolls=False,
    )

    assert sum(1 for foe in outcome.enemies if foe.life <= 0) == 2
    assert any("Water Jet disperses 2 vermin" in line for line in outcome.log)


def test_water_jet_knocks_out_one_minion_even_above_one_life(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
    caster = druid()
    minion = EnemyState(id="m", name="Elite Guard", category="minions", level=3, life=2, max_life=2)

    outcome = spells.resolve_spell_cast(
        "Water Jet",
        caster,
        [caster],
        [minion],
        spell_target_mode="minion",
        target_foe_id="m",
        show_rolls=False,
    )

    assert minion.life == 0
    assert outcome.combat_over is True
    assert any("Water Jet knocks out Elite Guard" in line for line in outcome.log)


def test_water_jet_distracts_major_foe_for_clean_flee(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))
    caster = druid()
    ogre = EnemyState(id="o", name="Ogre", category="boss", level=4, life=6, max_life=6)

    outcome = spells.resolve_spell_cast(
        "Water Jet",
        caster,
        [caster],
        [ogre],
        spell_target_mode="distract",
        target_foe_id="o",
        show_rolls=False,
    )

    assert ogre.life == 6
    assert outcome.flee_bonus is True
    assert any("can flee from this combat without being attacked" in line for line in outcome.log)


def test_water_jet_distract_sets_session_clean_flee(monkeypatch) -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    caster = druid()
    ogre = EnemyState(id="o", name="Ogre", category="boss", level=4, life=6, max_life=6)
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
                    enemies=[ogre],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (4, [4]))

    engine.advance(
        session,
        "cast_spell",
        character_id="druid",
        spell_name="Water Jet",
        spell_target_mode="distract",
        foe_id="o",
        show_rolls=False,
    )

    assert session.skip_parting_flee is True
