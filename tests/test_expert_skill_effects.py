from __future__ import annotations

from pathlib import Path

from app.engine import combat
from app.engine.combat import CombatContext, _defense_bonus
from app.engine.expert_skill_effects import (
    adjust_incoming_damage,
    adjust_search_roll,
    effective_barbarian_rage_uses,
    expert_attack_bonus,
    expert_morale_modifier,
    has_skill,
    unarmed_attack_penalty,
)
from app.engine.foe_weapon_restrictions import weapon_hit_blocked_by_restriction
from app.engine.expert_skills import apply_expert_skill_learn
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.combat import resolve_combat_round
from app.engine.weapons import weapon_profile
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _member(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=6,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def _session() -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _orc() -> EnemyState:
    return EnemyState(
        id="e1",
        name="Orc",
        category="minions",
        level=3,
        life=3,
        max_life=3,
        tags=["orc"],
    )


def _skeleton() -> EnemyState:
    return EnemyState(
        id="skel",
        name="Skeleton",
        category="minions",
        level=3,
        life=3,
        max_life=3,
        tags=["undead"],
    )


def _engine() -> RandomDungeonEngine:
    return RandomDungeonEngine(rules=None, asset_dir=Path())


def test_brawler_reduces_unarmed_penalty() -> None:
    warrior = _member(learned_expert_skills=["brawler"])
    assert unarmed_attack_penalty(warrior) == -1


def test_berserk_fury_adds_rage_use() -> None:
    barbarian = _member(class_id="barbarian", class_name="Barbarian", learned_expert_skills=["berserk_fury"])
    assert effective_barbarian_rage_uses(6, barbarian) == 5


def test_berserk_fury_table_explains_abyss_text_and_ee_interpretation() -> None:
    from app.engine.expert_skill_effects import expert_skill_implementation_rows

    row = next(
        item
        for item in expert_skill_implementation_rows(
            {"skills": [{"id": "berserk_fury", "name": "Berserk Fury", "source_page": 15}]}
        )
        if item["skill"] == "Berserk Fury"
    )
    assert "twice per adventure" in row["mechanic"]
    assert "+1 extra melee Rage use" in row["mechanic"]
    assert "never to ranged attacks" in row["mechanic"]


def test_impervious_and_orcslayer_bonuses() -> None:
    session = _session()
    warrior = _member(
        learned_expert_skills=["orcslayer"],
        default_missile_weapon="Long Bow",
    )
    elf = _member(
        class_id="elf",
        class_name="Elf",
        learned_expert_skills=["deadly_accuracy"],
        default_missile_weapon="Long Bow",
    )
    assert expert_attack_bonus(warrior, _orc(), session) == 1
    assert expert_attack_bonus(elf, _orc(), session, missile=True) == 1


def test_impervious_defense_bonus() -> None:
    session = _session()
    warrior = _member(
        learned_expert_skills=["impervious:goblin"],
        expert_skill_targets={"impervious": "goblin"},
    )
    goblin = EnemyState(
        id="g1",
        name="Goblin",
        category="minions",
        level=2,
        life=1,
        max_life=1,
        tags=["goblin"],
    )
    context = CombatContext(session=session)
    bonus, _ = _defense_bonus(warrior, goblin, context=context)
    plain, _ = _defense_bonus(_member(), goblin, context=context)
    assert bonus == plain + 1


def test_withstand_pain_once_per_encounter() -> None:
    session = _session()
    warrior = _member(learned_expert_skills=["withstand_pain"])
    damage, notes = adjust_incoming_damage(session, warrior, 1)
    assert damage == 0
    assert notes
    damage, notes = adjust_incoming_damage(session, warrior, 1)
    assert damage == 1
    assert not notes


def test_protective_incense_is_spent_once_but_bonus_applies_to_target() -> None:
    session = _session()
    cleric = _member(
        character_id="c",
        class_id="cleric",
        class_name="Cleric",
        learned_expert_skills=["protective_incense"],
    )
    ally = _member(character_id="a", name="Ally")
    skeleton = _skeleton()
    session.party = [cleric, ally]
    engine = _engine()
    context = engine._combat_context(
        session,
        session.map_state.tiles[0],
        combat_abilities={"c": "protective_incense"},
        combat_log=session.log,
        protective_incense_targets={"c": "a"},
    )

    assert "protective_incense" in session.expert_encounter_spent["c"]
    bonus, _ = _defense_bonus(ally, skeleton, context=context)
    plain, _ = _defense_bonus(_member(character_id="p"), skeleton, context=context)
    assert bonus == plain + 1

    engine._combat_context(
        session,
        session.map_state.tiles[0],
        combat_abilities={"c": "protective_incense"},
        combat_log=session.log,
        protective_incense_targets={"c": "c"},
    )
    assert session.expert_protective_incense_target == "a"
    assert any("already used Protective Incense" in line for line in session.log)


def test_vampire_hunter_bypasses_vampire_weapon_restriction() -> None:
    vampire = EnemyState(
        id="v1",
        name="Vampire",
        category="boss",
        level=5,
        life=3,
        max_life=3,
        tags=["vampire", "weapon_allow:magic_weapons"],
    )
    mundane_sword = weapon_profile("Sword")
    hunter = _member(learned_expert_skills=["vampire_hunter"], inventory=["Sword"])
    plain = _member(inventory=["Sword"])

    blocked, reason = weapon_hit_blocked_by_restriction(plain, vampire, mundane_sword, pending_damage=1)
    assert blocked is True
    assert reason
    blocked, reason = weapon_hit_blocked_by_restriction(hunter, vampire, mundane_sword, pending_damage=1)
    assert blocked is False
    assert reason == ""


def test_terrifying_savagery_requires_barbarian_minion_kill() -> None:
    session = _session()
    barbarian = _member(
        character_id="b",
        class_id="barbarian",
        class_name="Barbarian",
        learned_expert_skills=["terrifying_savagery"],
    )
    warrior = _member(character_id="w", learned_expert_skills=["terrifying_savagery"])

    assert expert_morale_modifier(session, [barbarian], eligible_character_ids={"w"}) == 0
    assert expert_morale_modifier(session, [warrior], eligible_character_ids={"w"}) == 0
    assert expert_morale_modifier(session, [barbarian], eligible_character_ids={"b"}) == -1
    assert expert_morale_modifier(session, [barbarian], eligible_character_ids={"b"}) == 0


def test_dead_shot_requires_declaration_and_spends_on_failed_missile(monkeypatch) -> None:
    archer = _member(
        level=1,
        learned_expert_skills=["dead_shot"],
        inventory=["Bow", "Lantern"],
        default_missile_weapon="Bow",
    )
    skeleton = EnemyState(
        id="skel",
        name="Skeleton",
        category="minions",
        level=6,
        life=1,
        max_life=1,
        tags=["undead"],
    )
    session = _session()
    session.party = [archer]
    rolls = iter([(1, [1]), (6, [6])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: next(rolls, (1, [1])))

    undeclared = resolve_combat_round(
        [archer],
        [skeleton.model_copy(deep=True)],
        show_rolls=True,
        context=CombatContext(session=session),
        party_attacked_immediately=True,
        encounter_round=0,
    )

    assert "dead_shot" not in session.expert_encounter_spent.get("h", [])
    assert not any("uses Dead Shot" in line for line in undeclared.log)

    archer = _member(
        level=1,
        learned_expert_skills=["dead_shot"],
        inventory=["Bow", "Lantern"],
        default_missile_weapon="Bow",
    )
    session = _session()
    session.party = [archer]
    rolls = iter([(1, [1]), (6, [6])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: next(rolls, (1, [1])))
    declared = resolve_combat_round(
        [archer],
        [skeleton.model_copy(deep=True)],
        show_rolls=True,
        context=CombatContext(session=session, dead_shot_attackers={"h"}),
        party_attacked_immediately=True,
        encounter_round=0,
    )

    assert "dead_shot" in session.expert_encounter_spent["h"]
    assert any("uses Dead Shot to reroll" in line for line in declared.log)
    assert any("Dead Shot reroll" in line for line in declared.log)


def test_learn_impervious_requires_target() -> None:
    packaged = __import__("pathlib").Path(__file__).resolve().parents[1] / "data" / "rules"
    from app.rules.repository import RulesRepository

    catalog = RulesRepository(packaged, packaged / "_override").expert_skills()
    warrior = _member(level=6, expert_trained=True)
    blocked = apply_expert_skill_learn(warrior, "impervious", catalog)
    assert "monster type" in blocked[0].lower()
    ok = apply_expert_skill_learn(warrior, "impervious", catalog, target="goblin")
    assert "learns" in ok[0].lower()
    assert has_skill(warrior, "impervious")
    assert warrior.expert_skill_targets["impervious"] == "goblin"


def test_search_roll_intuition() -> None:
    party = [_member(learned_expert_skills=["intuition"])]
    adjusted, notes = adjust_search_roll(party, 4, choice=None)
    assert adjusted == 5
    assert notes


def test_search_roll_detective_on_initial_search() -> None:
    party = [_member(learned_expert_skills=["detective"])]
    adjusted, notes = adjust_search_roll(party, 4, choice=None)
    assert adjusted == 5
    assert any("Detective" in note for note in notes)


def test_search_roll_stone_mastery_on_initial_search() -> None:
    party = [_member(learned_expert_skills=["stone_mastery"])]
    adjusted, notes = adjust_search_roll(party, 4, choice=None)
    assert adjusted == 5
    assert any("Stone Mastery" in note for note in notes)


def test_expert_implementation_table_api() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    payload = client.get("/api/rules/tables").json()
    rows = payload["expert_skill_implementation_table"]
    assert rows
    assert all(row["status"] == "wired" for row in rows)
    assert len(rows) >= 40


def test_super_logic_puzzle_bonus() -> None:
    from app.engine.expert_skill_effects import expert_puzzle_bonus

    party = [_member(learned_expert_skills=["super_logic"])]
    assert expert_puzzle_bonus(party) == 1
    assert expert_puzzle_bonus([_member()]) == 0


def test_prepare_adventure_expert_items() -> None:
    from app.engine.expert_skill_effects import prepare_adventure_expert_items

    cleric = _member(
        class_id="cleric",
        class_name="Cleric",
        gold=50,
        learned_expert_skills=["create_holy_water"],
    )
    log: list[str] = []
    prepare_adventure_expert_items([cleric], log)
    assert "Holy Water" in cleric.inventory
    assert cleric.gold == 40
    assert log


def test_turn_undead_logs_success_and_completes_combat(monkeypatch) -> None:
    cleric = _member(class_id="cleric", class_name="Cleric", learned_expert_skills=["turn_undead"])
    skeleton = _skeleton()
    session = _session()
    session.mode = "combat"
    session.party = [cleric]
    session.map_state.tiles[0].enemies = [skeleton]
    rolls = iter([6, 3])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls))

    _engine().advance(session, "use_class_ability", character_id="h", class_ability="turn_undead")

    assert skeleton.life == 0
    assert session.mode == "exploration"
    assert "turn_undead" in session.expert_encounter_spent["h"]
    assert any("Hero invokes Turn Undead against 1 undead foe." in line for line in session.log)
    assert any("Turn Undead succeeds against Skeleton; it loses 3 Life and is destroyed." in line for line in session.log)


def test_turn_undead_logs_failure_and_spent_use(monkeypatch) -> None:
    cleric = _member(class_id="cleric", class_name="Cleric", level=1, learned_expert_skills=["turn_undead"])
    skeleton = _skeleton()
    session = _session()
    session.mode = "combat"
    session.party = [cleric]
    session.map_state.tiles[0].enemies = [skeleton]
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    _engine().advance(session, "use_class_ability", character_id="h", class_ability="turn_undead")
    _engine().advance(session, "use_class_ability", character_id="h", class_ability="turn_undead")

    assert skeleton.life == 3
    assert any("Turn Undead fails against Skeleton." in line for line in session.log)
    assert any("Hero has already used Turn Undead this encounter." in line for line in session.log)


def test_turn_undead_requires_undead_targets() -> None:
    cleric = _member(class_id="cleric", class_name="Cleric", learned_expert_skills=["turn_undead"])
    session = _session()
    session.mode = "combat"
    session.party = [cleric]
    session.map_state.tiles[0].enemies = [_orc()]

    _engine().advance(session, "use_class_ability", character_id="h", class_ability="turn_undead")

    assert session.expert_encounter_spent == {}
    assert any("Turn Undead has no eligible undead foes in this encounter." in line for line in session.log)


def test_lesser_necromancy_strips_class_abilities_spells_and_skills(monkeypatch) -> None:
    necromancer = _member(
        character_id="n",
        name="Necromancer",
        class_id="wizard",
        class_name="Wizard",
        learned_expert_skills=["lesser_necromancy"],
    )
    fallen = _member(
        character_id="f",
        name="Fallen",
        class_id="elf",
        class_name="Elf",
        current_life=0,
        max_life=8,
        spells=["Sleep"],
        abilities=["Spellcasting"],
        learned_expert_skills=["dead_shot"],
        learned_heroic_skills=["master_strike"],
        learned_legendary_skills=["legendary_courage"],
        expert_skill_targets={"sworn_enemy": "vampire"},
        statuses=["Fallen"],
    )
    session = _session()
    session.party = [necromancer, fallen]
    session.map_state.tiles[0].fallen_character_ids = ["f"]
    monkeypatch.setattr("app.engine.random_dungeon.roll_die", lambda sides: 8)

    _engine().advance(
        session,
        "use_class_ability",
        character_id="n",
        class_ability="lesser_necromancy",
        target_character_id="f",
    )

    assert fallen.current_life == 4
    assert fallen.abilities == []
    assert fallen.spells == []
    assert fallen.learned_expert_skills == []
    assert fallen.learned_heroic_skills == []
    assert fallen.learned_legendary_skills == []
    assert fallen.expert_skill_targets == {}
    assert "Undead" in fallen.statuses
    assert "f" not in session.map_state.tiles[0].fallen_character_ids
