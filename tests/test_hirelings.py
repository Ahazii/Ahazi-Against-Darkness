from __future__ import annotations

from unittest.mock import patch

from app.engine.hirelings import (
    apply_hireling_damage,
    can_hire_retainers,
    check_hireling_morale_after_casualty,
    clear_hirelings_on_dungeon_exit,
    dismiss_hireling,
    hire_retainer,
    pay_hireling_treasure_share,
    retainer_gear_violation,
    return_porter_cargo,
    use_hireling_ability,
    use_professional_service,
)
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _member(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="h1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        xp=0,
        gold=100,
        bank_gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        expert_trained=True,
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def _session(**kwargs) -> SessionState:
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
    )
    defaults = dict(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        party=[_member()],
        map_state=MapState(tiles=[tile], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        camped_outside=True,
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def test_can_hire_requires_expert_and_camp() -> None:
    session = _session(camped_outside=False)
    ok, reason = can_hire_retainers(session)
    assert not ok
    assert "camped" in reason.lower()

    session = _session(party=[_member(expert_trained=False)])
    ok, reason = can_hire_retainers(session)
    assert not ok
    assert "expert" in reason.lower()


def test_hire_and_dismiss_lantern_bearer() -> None:
    session = _session()
    log = hire_retainer(session, "lantern_bearer")
    assert any("Hired" in line for line in log)
    assert len(session.hirelings) == 1
    assert session.hirelings[0].marching_order == 2
    assert session.party[0].gold == 96

    dismiss_log = dismiss_hireling(session, session.hirelings[0].id)
    assert any("dismiss" in line.lower() for line in dismiss_log)
    assert session.hirelings == []


def test_treasure_share_costs_double_fee() -> None:
    session = _session(party=[_member(gold=0, bank_gold=20)])
    hire_retainer(session, "lantern_bearer")
    hireling = session.hirelings[0]
    log = pay_hireling_treasure_share(session, hireling.id)
    assert any("treasure share" in line.lower() for line in log)
    assert hireling.treasure_share_paid
    assert session.party[0].bank_gold == 8


def test_morale_check_after_casualty() -> None:
    session = _session()
    hire_retainer(session, "lantern_bearer")
    with patch("app.engine.hirelings.roll_d6", return_value=1):
        log = check_hireling_morale_after_casualty(session, reason="a party casualty", show_rolls=False)
    assert any("flees" in line.lower() for line in log)
    assert not any(item.life > 0 for item in session.hirelings)


def test_minstrel_song_heals_madness() -> None:
    member = _member()
    member.madness = 1
    member.statuses = ["Madness 1"]
    session = _session(party=[member])
    hire_retainer(session, "minstrel")
    session.camped_outside = False
    log = use_hireling_ability(session, session.hirelings[0].id, "minstrel_song")
    assert any("sings" in line.lower() for line in log)
    assert member.madness == 0


def test_surgeon_heals_two_life() -> None:
    member = _member(current_life=2, max_life=6)
    session = _session(party=[member])
    hire_retainer(session, "surgeon")
    session.camped_outside = False
    use_hireling_ability(session, session.hirelings[0].id, "surgeon_heal")
    assert member.current_life == 4


def test_poison_expert_professional_applies_coating_at_purchase() -> None:
    rogue = _member(
        character_id="r1",
        name="Sneak",
        class_id="rogue",
        class_name="Rogue",
        level=5,
        gold=50,
        inventory=["Scimitar"],
    )
    session = _session(party=[rogue])
    log = use_professional_service(
        session,
        "poison_expert",
        character_id=rogue.character_id,
        item_name="Scimitar",
    )
    assert any("Poison Expert" in line for line in log)
    assert any("(poisoned)" in item for item in rogue.inventory)
    assert not session.professional_buffs.get("poison_expert_pending")


def test_silversmith_professional_applies_coating_at_purchase() -> None:
    warrior = _member(
        character_id="w1",
        name="Blade",
        class_id="warrior",
        class_name="Warrior",
        gold=50,
        inventory=["Hand weapon"],
    )
    session = _session(party=[warrior])
    log = use_professional_service(
        session,
        "silversmith",
        character_id=warrior.character_id,
        item_name="Hand weapon",
    )
    assert any("Silversmith" in line for line in log)
    assert any("(silvered)" in item for item in warrior.inventory)
    assert not session.professional_buffs.get("silversmith_pending")


def test_sage_clue_discount() -> None:
    from app.engine.hirelings import sage_clue_discount

    session = _session(professional_buffs={"sage_clue_double": True})
    assert sage_clue_discount(session, 3) == 2
    assert "sage_clue_double" not in session.professional_buffs


def test_lantern_dropped_on_death() -> None:
    session = _session()
    hire_retainer(session, "lantern_bearer")
    hireling = session.hirelings[0]
    assert hireling.lantern_lit
    log: list[str] = []
    apply_hireling_damage(hireling, 2, log)
    assert not hireling.lantern_lit
    assert any("lantern" in line.lower() for line in log)

    session = _session(party=[_member(gold=200)])
    for _ in range(3):
        log = use_professional_service(session, "storyteller")
        assert log
    blocked = use_professional_service(session, "storyteller")
    assert any("already used" in line.lower() for line in blocked)


def test_fortune_d8_reroll_consumed_on_roll() -> None:
    from unittest.mock import patch

    from app.engine.dice import roll_exploding_for_level

    member = _member(expert_trained=True)
    session = _session(party=[member], professional_buffs={"fortune_reroll_h1": 5})
    log: list[str] = []
    with patch("app.engine.dice.roll_die", return_value=1):
        _total, rolls = roll_exploding_for_level(member, session=session, log=log)
    assert rolls[0] == 5
    assert "fortune_reroll_h1" not in session.professional_buffs
    assert any("Fortune-Teller" in line for line in log)


def test_tailor_reaction_adjust_changes_bribe_outcome() -> None:
    from app.engine.hirelings import apply_tailor_to_reaction_roll
    from app.engine.reactions import ReactionSource

    class FakeRoller:
        def roll_reaction(self, table: str, roll: int) -> dict:
            if roll >= 4:
                return {"key": "bribe", "roll": str(roll)}
            return {"key": "fight", "roll": str(roll)}

    session = _session(professional_buffs={"tailor_reaction": True})
    source = ReactionSource("default_reaction_table", None, "test")
    roll, log = apply_tailor_to_reaction_roll(
        session,
        3,
        source=source,
        living_enemies=[],
        table_roller=FakeRoller(),
    )
    assert roll == 4
    assert "tailor_reaction" not in session.professional_buffs
    assert any("Tailor" in line for line in log)


def test_spear_carrier_shield_ready_counts_as_carried() -> None:
    from app.engine.expert_skill_effects import member_carries_shield

    member = _member(inventory=["Large Shield"], marching_order=4)
    session = _session(party=[member], mode="exploration")
    hire_retainer(
        session,
        "spear_carrier",
        assigned_character_id=member.character_id,
        marching_order=5,
    )
    hireling = session.hirelings[0]
    session.camped_outside = False
    use_hireling_ability(session, hireling.id, "spear_hand_gear", item_name="Large Shield")
    assert "Large Shield" not in member.inventory
    assert hireling.carried_gear == "Large Shield"
    session.mode = "combat"
    assert member_carries_shield(member, session) is False
    session.spear_shield_readied = [member.character_id]
    assert member_carries_shield(member, session) is True


def test_bodyguard_requires_assignment_at_hire() -> None:
    session = _session()
    blocked = hire_retainer(session, "bodyguard")
    assert any("assigned" in line.lower() for line in blocked)
    assert session.hirelings == []


def test_bodyguard_invalid_adjacency_does_not_charge_gold() -> None:
    rear = _member(character_id="h4", name="Rear", marching_order=4)
    session = _session(party=[_member(marching_order=1), _member(character_id="h2", marching_order=2), _member(character_id="h3", marching_order=3), rear])
    starting_gold = session.party[0].gold
    blocked = hire_retainer(session, "bodyguard", assigned_character_id="h1", marching_order=5)
    assert any("adjacent" in line.lower() for line in blocked)
    assert session.hirelings == []
    assert session.party[0].gold == starting_gold


def test_bodyguard_hires_on_slot_five_for_rear_guard() -> None:
    rear = _member(character_id="h4", name="Rear", marching_order=4)
    session = _session(party=[_member(marching_order=1), _member(character_id="h2", marching_order=2), _member(character_id="h3", marching_order=3), rear])
    log = hire_retainer(session, "bodyguard", assigned_character_id="h4", marching_order=5)
    assert any("Hired" in line for line in log)
    assert session.hirelings[0].marching_order == 5
    assert session.hirelings[0].assigned_character_id == "h4"


def test_bodyguard_can_insert_into_front_or_middle_marching_order() -> None:
    h1 = _member(character_id="h1", name="Front", marching_order=1)
    h2 = _member(character_id="h2", name="Middle", marching_order=2, gold=0)
    h3 = _member(character_id="h3", marching_order=3, gold=0)
    h4 = _member(character_id="h4", marching_order=4, gold=0)
    session = _session(party=[h1, h2, h3, h4])

    log = hire_retainer(session, "bodyguard", assigned_character_id="h2", marching_order=3)

    assert any("Hired" in line for line in log)
    assert session.hirelings[0].marching_order == 3
    assert h1.marching_order == 1
    assert h2.marching_order == 2
    assert h3.marching_order == 4
    assert h4.marching_order == 5
    assert session.hirelings[0].assigned_character_id == "h2"


def test_acolyte_can_insert_before_front_cleric() -> None:
    cleric = _member(character_id="c1", class_id="cleric", class_name="Cleric", marching_order=1)
    h2 = _member(character_id="h2", marching_order=2, gold=0)
    h3 = _member(character_id="h3", marching_order=3, gold=0)
    h4 = _member(character_id="h4", marching_order=4, gold=0)
    session = _session(party=[cleric, h2, h3, h4])

    log = hire_retainer(session, "acolyte", assigned_character_id="c1", marching_order=1)

    assert any("Hired" in line for line in log)
    assert session.hirelings[0].marching_order == 1
    assert cleric.marching_order == 2
    assert session.hirelings[0].assigned_character_id == "c1"


def test_acolyte_defaults_in_front_of_assigned_cleric() -> None:
    cleric = _member(character_id="c1", class_id="cleric", class_name="Cleric", marching_order=1)
    h2 = _member(character_id="h2", marching_order=2, gold=0)
    h3 = _member(character_id="h3", marching_order=3, gold=0)
    h4 = _member(character_id="h4", marching_order=4, gold=0)
    session = _session(party=[cleric, h2, h3, h4])

    log = hire_retainer(session, "acolyte", assigned_character_id="c1")

    assert any("Hired" in line for line in log)
    assert session.hirelings[0].marching_order == 1
    assert cleric.marching_order == 2


def test_bodyguard_defaults_in_front_of_assigned_protectee() -> None:
    front = _member(character_id="h1", name="Front", marching_order=1, gold=0)
    guarded = _member(character_id="h2", name="Guarded", marching_order=2, gold=100)
    h3 = _member(character_id="h3", marching_order=3, gold=0)
    h4 = _member(character_id="h4", marching_order=4, gold=0)
    session = _session(party=[front, guarded, h3, h4])

    log = hire_retainer(session, "bodyguard", assigned_character_id="h2")

    assert any("Hired" in line for line in log)
    assert session.hirelings[0].marching_order == 2
    assert guarded.marching_order == 3
    assert front.marching_order == 1


def test_can_hire_two_retainers_on_slots_five_and_six() -> None:
    rear = _member(character_id="h4", name="Rear", marching_order=4, gold=0)
    session = _session(
        party=[
            _member(gold=200, marching_order=1),
            _member(character_id="h2", marching_order=2, gold=0),
            _member(character_id="h3", marching_order=3, gold=0),
            rear,
        ],
    )
    hire_retainer(session, "bodyguard", assigned_character_id="h4", marching_order=5)
    log = hire_retainer(session, "lantern_bearer", marching_order=6)
    assert any("Hired" in line for line in log)
    assert len(session.hirelings) == 2
    assert {item.marching_order for item in session.hirelings} == {5, 6}


def test_set_hireling_marching_order_rolls_back_invalid_assignment() -> None:
    from app.engine.hirelings import set_hireling_marching_order

    rear = _member(character_id="h4", name="Rear", marching_order=4)
    session = _session(
        party=[_member(marching_order=1), _member(character_id="h2", marching_order=2), _member(character_id="h3", marching_order=3), rear],
        mode="exploration",
    )
    hire_retainer(session, "bodyguard", assigned_character_id="h4", marching_order=5)
    hireling = session.hirelings[0]
    blocked = set_hireling_marching_order(session, hireling.id, 6)
    assert any("adjacent" in line.lower() for line in blocked)
    assert hireling.marching_order == 5


def test_set_party_member_marching_order_uses_shared_retainer_order() -> None:
    from app.engine.hirelings import set_party_member_marching_order

    h1 = _member(character_id="h1", name="Front", marching_order=1)
    h2 = _member(character_id="h2", name="Guarded", marching_order=2, gold=0)
    h3 = _member(character_id="h3", marching_order=3, gold=0)
    h4 = _member(character_id="h4", marching_order=4, gold=0)
    session = _session(party=[h1, h2, h3, h4], mode="exploration")
    hire_retainer(session, "bodyguard", assigned_character_id="h2", marching_order=3)
    hireling = session.hirelings[0]

    blocked = set_party_member_marching_order(session, "h2", 5)

    assert any("adjacent" in line.lower() for line in blocked)
    assert h2.marching_order == 2
    assert hireling.marching_order == 3

    moved = set_party_member_marching_order(session, "h1", 6)

    assert any("moves" in line.lower() for line in moved)
    assert h1.marching_order == 6
    assert h2.marching_order == 1
    assert hireling.marching_order == 2


def test_two_acolytes_use_distinct_open_marching_slots() -> None:
    cleric = _member(character_id="c1", class_id="cleric", class_name="Cleric", marching_order=4)
    session = _session(party=[cleric])
    hire_retainer(session, "acolyte", assigned_character_id="c1")
    first = session.hirelings[0].marching_order
    hire_retainer(session, "acolyte", assigned_character_id="c1", name="Acolyte 2")
    assert len(session.hirelings) == 2
    orders = sorted(item.marching_order for item in session.hirelings)
    assert orders[0] != orders[1]
    assert first in {4, 5, 3}


def test_repair_shared_marching_orders_moves_duplicate_hirelings() -> None:
    from app.engine.hirelings import repair_shared_marching_orders

    cleric = _member(character_id="c1", class_id="cleric", class_name="Cleric", marching_order=4)
    session = _session(party=[cleric])
    hire_retainer(session, "acolyte", assigned_character_id="c1", name="Acolyte A")
    hire_retainer(session, "acolyte", assigned_character_id="c1", name="Acolyte B")
    session.hirelings[1].marching_order = session.hirelings[0].marching_order
    assert repair_shared_marching_orders(session) is True
    orders = [item.marching_order for item in session.hirelings]
    assert len(set(orders)) == 2


def test_acolyte_only_preserves_for_assigned_cleric() -> None:
    from app.engine.hirelings import try_acolyte_preserve_blessing, _adjacent_marching_orders

    cleric = _member(character_id="c1", class_id="cleric", class_name="Cleric", marching_order=4)
    session = _session(party=[cleric], mode="combat")
    hire_retainer(session, "acolyte", assigned_character_id="c1")
    hireling = session.hirelings[0]
    assert hireling.marching_order == 5
    assert cleric.marching_order == 4
    assert _adjacent_marching_orders(hireling.marching_order, cleric.marching_order)
    session.camped_outside = False
    with patch("app.engine.hirelings.roll_d6", return_value=6):
        preserved, log = try_acolyte_preserve_blessing(session, cleric, show_rolls=False)
    assert preserved
    assert any("preserves" in line.lower() for line in log)

    session2 = _session(party=[cleric], mode="combat")
    hire_retainer(session2, "acolyte", assigned_character_id="c1")
    session2.hirelings[0].assigned_character_id = None
    session2.hirelings[0].marching_order = 5
    session2.camped_outside = False
    preserved2, log2 = try_acolyte_preserve_blessing(session2, cleric, show_rolls=False)
    assert not preserved2
    assert log2 == []


def test_silversmith_coating_uses_silvered_suffix() -> None:
    from app.engine.hirelings import apply_silversmith_coating
    from app.engine.weapon_finishes import is_weapon_item_silvered

    member = _member(inventory=["Scimitar"])
    session = _session(party=[member], professional_buffs={"silversmith_pending": True})
    apply_silversmith_coating(session, item_name="Scimitar", character_id=member.character_id)
    assert any(is_weapon_item_silvered(item) for item in member.inventory)


def test_porter_cargo_returned_on_dungeon_exit() -> None:
    session = _session()
    hire_retainer(session, "porter")
    hireling = session.hirelings[0]
    hireling.cargo_gp = 50
    hireling.cargo_items = ["Large Shield"]
    session.camped_outside = False
    session.log = []
    clear_hirelings_on_dungeon_exit(session)
    assert session.party[0].gold == 96 + 50
    assert "Large Shield" in session.party[0].inventory
    assert session.hirelings == []
    assert any("returns 50gp" in line for line in session.log)


def test_retainer_death_triggers_morale_for_survivors() -> None:
    session = _session()
    hire_retainer(session, "lantern_bearer")
    hire_retainer(session, "minstrel")
    victim = session.hirelings[0]
    log: list[str] = []
    with patch("app.engine.hirelings.roll_d6", return_value=1):
        apply_hireling_damage(victim, 2, log, session=session, show_rolls=False)
    assert victim.life == 0
    assert any("flees" in line.lower() for line in log)
    assert len([item for item in session.hirelings if item.life > 0]) == 0


def test_retainer_loadout_rejects_heavy_armor_for_surgeon() -> None:
    assert retainer_gear_violation("surgeon", "Heavy Armor") is not None
    assert retainer_gear_violation("surgeon", "Dagger") is None


def test_equip_retainer_weapon_from_hero_inventory() -> None:
    member = _member(inventory=["Dagger"])
    session = _session(party=[member])
    hire_retainer(session, "surgeon")
    session.camped_outside = False
    hireling = session.hirelings[0]
    log = use_hireling_ability(
        session,
        hireling.id,
        "equip_retainer_weapon",
        character_id=member.character_id,
        item_name="Dagger",
    )
    assert any("equips" in line.lower() for line in log)
    assert hireling.equipped_weapon == "Dagger"
    assert "Dagger" not in member.inventory


def test_spear_carrier_requires_slashing_sidearm_to_attack() -> None:
    from app.engine.hirelings import apply_hireling_combat_round

    member = _member(character_id="w1", marching_order=4)
    session = _session(party=[member], mode="combat")
    hire_retainer(session, "spear_carrier", assigned_character_id="w1")
    hireling = session.hirelings[0]
    hireling.marching_order = 5
    session.camped_outside = False
    enemy = EnemyState(id="e1", name="Goblin", category="minion", level=2, life=2, max_life=2)
    log = apply_hireling_combat_round(session, [enemy], show_rolls=False)
    assert any("slashing hand weapon" in line.lower() for line in log)
    hireling.equipped_weapon = "Short Sword"
    log2 = apply_hireling_combat_round(session, [enemy], show_rolls=False)
    assert not any("slashing hand weapon" in line.lower() for line in log2)
