from __future__ import annotations

from pathlib import Path

from app.engine.class_abilities import (
    kukla_doll_round_attacks,
    resolve_social_save,
)
from app.engine.combat import CombatContext
from app.engine.expert_skill_effects import adjust_search_roll
from app.engine.heroic_skill_effects import (
    apply_heroes_rest_bonus,
    resolve_fear_save,
    try_sacrifice_shield,
)
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _session(**kwargs) -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=kwargs.pop("party", []),
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        **kwargs,
    )


def test_hyphae_search_bonus_consumed() -> None:
    monk = PartyMemberState(
        character_id="m",
        name="Spore",
        class_id="mushroom_monk",
        class_name="Mushroom Monk",
        level=6,
        xp=0,
        gold=0,
        current_life=8,
        max_life=8,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = _session(party=[monk], hyphae_search_bonus_id="m")
    adjusted, notes = adjust_search_roll([monk], 3, choice=None, session=session)
    assert adjusted == 4
    assert session.hyphae_search_bonus_id is None
    assert notes


def test_sacrifice_shield_negates_hit_and_forfeits_shield() -> None:
    bulwark = PartyMemberState(
        character_id="b",
        name="Wall",
        class_id="bulwark",
        class_name="Bulwark",
        level=6,
        xp=0,
        gold=0,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=1,
        save_bonus=0,
        learned_expert_skills=["sacrifice_shield"],
        inventory=["Hand weapon", "Shield"],
    )
    session = _session(party=[bulwark])
    context = CombatContext(
        sacrifice_shield_users={"b"},
        session=session,
    )
    enemy = EnemyState(id="g1", name="Goblin", category="minions", level=4, life=4, max_life=4)
    log: list[str] = []
    assert try_sacrifice_shield(context, bulwark, log)
    assert bulwark.current_life == 10
    assert "Shield" not in bulwark.inventory
    assert session.forfeited_shields["b"] == "Shield"
    assert any("Sacrifice Shield" in entry for entry in log)


def test_kukla_doll_attack_can_damage_foe() -> None:
    kukla = PartyMemberState(
        character_id="k",
        name="Dolly",
        class_id="kukla",
        class_name="Kukla",
        level=6,
        xp=0,
        gold=0,
        current_life=6,
        max_life=6,
        attack_bonus=0,
        defense_bonus=1,
        save_bonus=0,
    )
    session = _session(party=[kukla], kukla_doll_active=["k"])
    target = EnemyState(id="r1", name="Rat", category="vermin", level=1, life=2, max_life=2)

    class FixedRoll:
        def __init__(self, values: list[int]):
            self.values = values

        def __call__(self, _level: int):
            if self.values:
                value = self.values.pop(0)
                return value, [value]
            return 6, [6]

    import app.engine.class_abilities as abilities

    original = abilities.roll_exploding_for_level
    abilities.roll_exploding_for_level = FixedRoll([6])  # type: ignore[method-assign]
    try:
        log = kukla_doll_round_attacks(session, kukla, target, show_rolls=False)
    finally:
        abilities.roll_exploding_for_level = original

    assert target.life == 1
    assert any("fighting doll hits" in entry for entry in log)


def test_heroes_rest_bonus_once_per_adventure() -> None:
    hero = PartyMemberState(
        character_id="h",
        name="Veteran",
        class_id="warrior",
        class_name="Warrior",
        level=10,
        xp=0,
        gold=0,
        current_life=9,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        learned_heroic_skills=["heros_rest"],
    )
    session = _session(party=[hero])
    log = apply_heroes_rest_bonus(session, party=[hero])
    assert hero.current_life == 10
    assert session.heroes_rest_used
    assert log
    assert not apply_heroes_rest_bonus(session, party=[hero])


def test_graceful_move_rerolls_failed_social_save() -> None:
    acrobat = PartyMemberState(
        character_id="a",
        name="Flip",
        class_id="acrobat",
        class_name="Acrobat",
        level=5,
        xp=0,
        gold=0,
        current_life=7,
        max_life=7,
        attack_bonus=0,
        defense_bonus=1,
        save_bonus=0,
    )
    session = _session(party=[acrobat], graceful_save_reroll_id="a")

    class SeqRoll:
        def __init__(self, values: list[int]):
            self.values = values

        def __call__(self, _level: int):
            value = self.values.pop(0)
            return value, [value]

    import app.engine.class_abilities as abilities

    original = abilities.roll_exploding_for_level
    abilities.roll_exploding_for_level = SeqRoll([1, 6])  # type: ignore[method-assign]
    try:
        ok, log = resolve_social_save(session, acrobat, 4, show_rolls=False, label="social")
    finally:
        abilities.roll_exploding_for_level = original

    assert ok
    assert session.graceful_save_reroll_id is None
    assert any("Graceful Move" in entry for entry in log)


def test_fear_save_uses_heroic_courage_ignore_once() -> None:
    warrior = PartyMemberState(
        character_id="w",
        name="Brave",
        class_id="warrior",
        class_name="Warrior",
        level=6,
        xp=0,
        gold=0,
        current_life=8,
        max_life=8,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        learned_heroic_skills=["heroic_courage"],
    )
    session = _session(party=[warrior])

    class FailRoll:
        def __call__(self, _level: int):
            return 1, [1]

    import app.engine.heroic_skill_effects as heroic

    original = heroic.roll_exploding_for_level
    heroic.roll_exploding_for_level = FailRoll()  # type: ignore[method-assign]
    try:
        saved, log = resolve_fear_save(session, warrior, 4, show_rolls=False)
    finally:
        heroic.roll_exploding_for_level = original

    assert saved
    assert "w" in session.heroic_courage_used
    assert any("Heroic Courage" in entry for entry in log)
