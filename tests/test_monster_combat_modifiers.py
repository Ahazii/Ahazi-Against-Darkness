from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.engine.combat import CombatContext, _resolve_attacks, _resolve_pc_attack
from app.engine.monster_combat_modifiers import (
    apply_end_of_combat_poison,
    armor_neutralizes_crushing_bonus,
    blademaster_riposte_applies,
    foe_frenzy_attack_bonus,
    orc_looter_spell_morale_check,
    pc_attack_modifier_from_template,
    resolve_on_hit_poison_timing,
    withdraw_blocked_by_webs,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.weapons import WeaponProfile
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, PartyMemberState, SessionState, TileState

ROOT = Path(__file__).resolve().parents[1]


def _hero(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        max_life=6,
        current_life=6,
        marching_order=1,
        inventory=["Arrows"],
        statuses=[],
        spells=[],
        learned_expert_skills=[],
        gold=0,
        clues=0,
        xp=0,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _session(party: list[PartyMemberState]) -> SessionState:
    return SessionState(
        id="s1",
        party_id="p1",
        adventure_id="random",
        adventure_type="random",
        party=party,
        map_state={"current_tile_id": "t1", "tiles": []},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _engine() -> RandomDungeonEngine:
    return RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )


def test_armored_skeleton_neutralizes_crushing_and_arrow_penalty() -> None:
    engine = _engine()
    skeleton = EnemyState(
        id="sk1",
        name="Armored Skeletons",
        category="vermin",
        level=8,
        life=1,
        max_life=1,
        tags=["undead"],
    )
    template = engine._monster_template_for_enemy(skeleton)
    assert template is not None
    assert armor_neutralizes_crushing_bonus(template)
    mace = WeaponProfile(item="Mace", kind="melee", crushing=True)
    bow = WeaponProfile(item="Longbow", kind="missile")
    crush_adj, _ = pc_attack_modifier_from_template(mace, skeleton, template, member=_hero())
    arrow_adj, _ = pc_attack_modifier_from_template(bow, skeleton, template, member=_hero())
    assert crush_adj == -1
    assert arrow_adj == -1


def test_fiendish_spider_crushing_vulnerability() -> None:
    engine = _engine()
    spider = EnemyState(id="sp1", name="Fiendish Spiders", category="vermin", level=5, life=1, max_life=1)
    template = engine._monster_template_for_enemy(spider)
    mace = WeaponProfile(item="Mace", kind="melee", crushing=True)
    adj, notes = pc_attack_modifier_from_template(mace, spider, template, member=_hero())
    assert adj == 1
    assert notes


def test_gnoll_frenzy_vs_wounded_pc() -> None:
    engine = _engine()
    gnoll = EnemyState(id="g1", name="Gnolls", category="minions", level=8, life=1, max_life=1)
    wounded = _hero(current_life=3)
    healthy = _hero(character_id="hero-2", name="Healthy", current_life=6)
    lookup = engine._monster_template_for_enemy
    assert foe_frenzy_attack_bonus(gnoll, wounded, lookup_template=lookup) == 1
    assert foe_frenzy_attack_bonus(gnoll, healthy, lookup_template=lookup) == 0


def test_blademaster_riposte_on_melee_natural_one() -> None:
    engine = _engine()
    hero = _hero()
    blademaster = EnemyState(
        id="b1",
        name="Hobgoblin Blademasters",
        category="minions",
        level=8,
        life=1,
        max_life=1,
    )
    context = CombatContext(session=_session([hero]), lookup_monster_template=engine._monster_template_for_enemy)
    assert blademaster_riposte_applies(
        blademaster,
        missile=False,
        first_die=1,
        lookup_template=engine._monster_template_for_enemy,
    )
    log: list[str] = []
    with patch("app.engine.combat.roll_exploding_for_level", return_value=(1, [1])):
        _resolve_pc_attack(
            hero,
            blademaster,
            show_rolls=False,
            explain_math=False,
            party_attack_bonus=0,
            subdual=False,
            missile=False,
            living_enemies=[blademaster],
            log=log,
            context=context,
        )
    assert any("riposte" in line.lower() for line in log)


def test_spider_poison_deferred_to_end_of_combat() -> None:
    hero = _hero()
    session = _session([hero])
    spider = EnemyState(
        id="sp1",
        name="Fiendish Spiders",
        category="vermin",
        level=5,
        life=1,
        max_life=1,
        on_hit_effects=[
            {
                "type": "poison",
                "timing": "end_of_combat",
                "save_level": 5,
                "damage": 1,
            }
        ],
    )
    context = CombatContext(session=session)
    deferred = resolve_on_hit_poison_timing(
        spider.on_hit_effects[0],
        spider,
        hero,
        context=context,
        show_rolls=False,
        explain_math=False,
        session=session,
    )
    assert deferred
    assert session.pending_end_of_combat_poison
    log: list[str] = []
    with patch("app.engine.monster_combat_modifiers.poison_save_succeeds", return_value=(False, [])):
        apply_end_of_combat_poison(session, [hero], log, show_rolls=False)
    assert hero.current_life == 5
    assert not session.pending_end_of_combat_poison


def test_withdraw_blocked_until_fireball_burns_webs() -> None:
    spiders = [
        EnemyState(id="sp1", name="Fiendish Spiders", category="vermin", level=5, life=1, max_life=1),
    ]
    assert withdraw_blocked_by_webs(spiders, webs_burned=False)
    assert not withdraw_blocked_by_webs(spiders, webs_burned=True)


def test_orc_looter_spell_morale_flee() -> None:
    hero = _hero()
    session = _session([hero])
    before = [
        EnemyState(id=f"o{i}", name="Orc Looters", category="minions", level=7, life=1, max_life=1)
        for i in range(4)
    ]
    after = [enemy.model_copy(deep=True) for enemy in before]
    after[0].life = 0
    after[1].life = 0
    log: list[str] = []
    with patch("app.engine.monster_combat_modifiers.roll_d6", return_value=2):
        fled = orc_looter_spell_morale_check(
            before,
            after,
            initial_orc_count=4,
            session=session,
            party=[hero],
            log=log,
            show_rolls=False,
        )
    assert fled
    assert all(enemy.life == 0 for enemy in after)


def test_frenzy_increases_foe_attack_level() -> None:
    engine = _engine()
    hero = _hero(current_life=3)
    gnoll = EnemyState(id="g1", name="Gnolls", category="minions", level=8, life=1, max_life=1)
    context = CombatContext(session=_session([hero]), lookup_monster_template=engine._monster_template_for_enemy)
    log, _paused = _resolve_attacks(
        [(gnoll, hero)],
        party=[hero],
        show_rolls=True,
        explain_math=False,
        context=context,
    )
    assert any("frenzy" in line.lower() for line in log)
