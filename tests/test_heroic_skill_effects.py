from __future__ import annotations

from app.engine.heroic_skill_effects import (
    apply_heros_banquet_bonus,
    apply_mass_blessing,
    apply_restore_healing,
    apply_song_of_elidra,
    bank_training_focus,
    beast_leadership_reaction_bonus,
    consume_training_focus_bonus,
    deadly_stab_extra_damage,
    deep_wound_extra_damage,
    eldritch_force_extra_damage,
    heroic_attack_bonus,
    heroic_climber_search_bonus,
    heroic_defense_bonus,
    preserve_corpse_resurrection_bonus,
    prodigious_memory_search_bonus,
    rotate_aggressive_stance_penalty,
    trap_damage_after_reduction,
    trap_save_bonus,
    training_focus_bonus_amount,
    try_survive_killing_blow,
    weapon_matches_accuracy,
    ward_defense_bonus,
)
from app.engine.weapons import inventory_weapons
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


def _warrior(*skills: str) -> PartyMemberState:
    return PartyMemberState(
        character_id="w",
        name="Veteran",
        class_id="warrior",
        class_name="Warrior",
        level=10,
        xp=0,
        gold=0,
        current_life=8,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        learned_heroic_skills=list(skills),
    )


def test_heroic_accuracy_matches_weapon_type() -> None:
    member = _warrior("heroic_accuracy")
    member.expert_skill_targets = {"heroic_accuracy": "hand weapon"}
    member.inventory = ["Hand weapon"]
    weapon = inventory_weapons(member)[0]
    assert weapon_matches_accuracy(member, weapon, missile=False) is True
    assert heroic_attack_bonus(member, missile=False, living_foe_count=1, weapon=weapon) == 1


def test_legendary_battle_training_with_two_foes() -> None:
    member = _warrior("battle_training")
    member.learned_legendary_skills = ["legendary_battle_training"]
    bonus = heroic_attack_bonus(member, missile=False, living_foe_count=2)
    assert bonus == 2


def test_aggressive_and_defensive_stance_defense() -> None:
    member = _warrior("heroic_dodge", "defensive_stance")
    session = _session(party=[member], aggressive_stance_penalty=["w"])
    bonus = heroic_defense_bonus(
        member,
        single_attacker=True,
        defensive_stance=True,
        aggressive_stance_penalty=True,
    )
    assert bonus == 1


def test_deep_wound_vs_major_foe() -> None:
    member = _warrior("deep_wound")
    boss = EnemyState(id="b1", name="Ogre", category="boss", level=6, life=10, max_life=10)
    extra, log = deep_wound_extra_damage(member, boss)
    assert extra == 1
    assert log


def test_training_focus_banks_and_consumes() -> None:
    member = _warrior("training_focus")
    session = _session(party=[member])
    assert training_focus_bonus_amount(member) == 1
    assert bank_training_focus(session, member)
    assert session.training_focus_bonus["w"] == 1
    assert consume_training_focus_bonus(session, "w") == 1
    assert consume_training_focus_bonus(session, "w") == 0


def test_rotate_aggressive_stance_penalty() -> None:
    session = _session()
    rotate_aggressive_stance_penalty(session, {"a", "b"})
    assert set(session.aggressive_stance_penalty) == {"a", "b"}


def test_charge_breaker_single_melee_attacker() -> None:
    member = _warrior("charge_breaker", "heroic_dodge")
    bonus = heroic_defense_bonus(member, single_attacker=False, melee_attacks_on_target=1)
    assert bonus == 1


def test_deadly_stab_on_dagger() -> None:
    member = _warrior("deadly_stab")
    member.inventory = ["Dagger"]
    weapon = inventory_weapons(member)[0]
    extra, log = deadly_stab_extra_damage(member, weapon, missile=False)
    assert extra == 1
    assert log


def test_eldritch_force_bonus() -> None:
    member = _warrior("eldritch_force")
    assert eldritch_force_extra_damage(member) == 1


def test_ward_of_protection_defense() -> None:
    cleric = _warrior("ward_of_protection")
    cleric.character_id = "c"
    ally = _warrior()
    ally.character_id = "a"
    session = _session(party=[cleric, ally], ward_of_protection_targets={"a": "c"})
    assert ward_defense_bonus(session, ally) == 1


def test_mass_blessing_once_per_adventure() -> None:
    cleric = _warrior("mass_blessing")
    session = _session(party=[cleric])
    assert apply_mass_blessing(session, cleric, 1)
    assert session.mass_blessing_used is True
    assert apply_mass_blessing(session, cleric, 2) == ["Mass Blessing was already used this adventure."]


def test_restore_healing_once_per_encounter() -> None:
    cleric = _warrior("restore")
    cleric.class_id = "cleric"
    cleric.character_id = "c"
    ally = _warrior()
    ally.character_id = "a"
    ally.current_life = 5
    session = _session(party=[cleric, ally])
    assert apply_restore_healing(session, cleric, ally)
    assert ally.current_life == 6
    assert "already used" in apply_restore_healing(session, cleric, ally)[0]


def test_protected_by_fate_survives() -> None:
    member = _warrior("protected_by_fate")
    session = _session(party=[member])
    member.current_life = 0
    log: list[str] = []
    assert try_survive_killing_blow(session, member, log)
    assert member.current_life == 1


def test_song_of_elidra_once() -> None:
    bard = _warrior("song_of_elidra")
    session = _session(party=[bard])
    bonus, notes = apply_song_of_elidra(session, [bard])
    assert bonus == 1
    assert notes
    assert apply_song_of_elidra(session, [bard]) == (0, [])


def test_beast_leadership_vs_beasts() -> None:
    member = _warrior("beast_leadership")
    beasts = [EnemyState(id="w1", name="Wolf", category="minions", level=3, life=1, max_life=1, tags=["beast"])]
    bonus, notes = beast_leadership_reaction_bonus([member], beasts)
    assert bonus == 1
    assert notes


def test_prodigious_memory_on_revisited_tile() -> None:
    member = _warrior("prodigious_memory")
    session = _session(party=[member], visited_tile_ids=["t2"])
    bonus, notes = prodigious_memory_search_bonus(session, [member], "t2")
    assert bonus == 1
    assert notes


def test_heroic_climber_secret_door() -> None:
    member = _warrior("heroic_climber")
    assert heroic_climber_search_bonus(member, "secret_door") == 1


def test_catfall_reduces_fall_damage() -> None:
    member = _warrior("catfall")
    member.level = 5
    damage, notes = trap_damage_after_reduction(member, "falling_stone", "falling stone", 2)
    assert damage == 0
    assert notes


def test_heroic_swimmer_water_trap_save() -> None:
    member = _warrior("heroic_swimmer")
    member.level = 6
    assert trap_save_bonus(member, "water_pit", "water trap") == 6


def test_heros_banquet_on_rest() -> None:
    member = _warrior("heros_banquet")
    member.current_life = 5
    session = _session(party=[member])
    log = apply_heros_banquet_bonus(session, [member])
    assert member.current_life == 6
    assert log


def test_preserve_corpse_resurrection_bonus() -> None:
    member = _warrior("preserve_corpse")
    assert preserve_corpse_resurrection_bonus([member]) == 1
