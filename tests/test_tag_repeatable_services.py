from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.dice import AdvancementRollResult
from app.engine.item_containers import add_bag_of_carrying
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.tag_repeatable_services import (
    SHOES_OF_FAST_WALK,
    assigned_hireling_shoes_lock_reason,
    buy_shoes_of_fast_walk,
    finish_repeatable_service,
    repeatable_service_state,
    shoes_of_fast_walk_defense_bonus,
    shoes_of_fast_walk_hireling_defense_bonus,
    teach_leprechaun_illusion_spell,
    train_with_deoldyn,
)
from app.engine.inventory import transfer_item_between
from app.schemas import (
    ActiveQuestState,
    EnemyState,
    HirelingState,
    MapState,
    PartyMemberState,
    SessionState,
    TileState,
)


def _member(
    character_id: str,
    *,
    name: str | None = None,
    class_id: str = "warrior",
    class_name: str | None = None,
    level: int = 3,
    gold: int = 0,
    bank_gold: int = 0,
    spells: list[str] | None = None,
    expert_trained: bool = False,
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name or character_id.title(),
        class_id=class_id,
        class_name=class_name or class_id.replace("_", " ").title(),
        level=level,
        xp=0,
        gold=gold,
        bank_gold=bank_gold,
        current_life=10,
        max_life=10,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=list(spells or []),
        expert_trained=expert_trained,
    )


def _hireling(hireling_id: str = "hireling") -> HirelingState:
    return HirelingState(
        id=hireling_id,
        retainer_type="porter",
        name="Pip",
        life=3,
        max_life=3,
        marching_order=5,
    )


def _session(
    rumor_number: int,
    party: list[PartyMemberState],
    *,
    hirelings: list[HirelingState] | None = None,
) -> SessionState:
    tile = TileState(
        id="scene",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="TAG scene",
        description="TAG repeatable service",
    )
    return SessionState(
        id=f"rumor-{rumor_number}-session",
        party_id="party",
        adventure_id=f"tag-rumor-{rumor_number}",
        adventure_type="imported",
        party=party,
        hirelings=list(hirelings or []),
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        active_quest=ActiveQuestState(
            tile_id=tile.id,
            key="tag_generated_scene",
            description="Resolve the TAG service.",
        ),
        imported_manifest={
            "title": f"TAG Rumor {rumor_number}",
            "source": {
                "parameters": {
                    "tag_reference": {
                        "lead_type": "rumor",
                        "rumor_number": rumor_number,
                    }
                }
            },
        },
        created_at="2026-08-03T00:00:00+00:00",
        updated_at="2026-08-03T00:00:00+00:00",
    )


def _roll(natural: int, *, sides: int = 6, modifier: int = 0) -> AdvancementRollResult:
    return AdvancementRollResult(
        natural=natural,
        total=natural + modifier,
        sides=sides,
        modifier=modifier,
        purpose="level_up",
    )


def _illusion_option(
    *,
    name: str = "Mirror Image",
    native_class_ids: list[str] | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "description": "An illusion creates false copies of the caster.",
        "source_tables": ["illusionist_spells_table"],
        "native_class_ids": list(native_class_ids or ["wizard", "illusionist"]),
        "expert_requirements": {},
    }


def test_shoes_cost_exactly_200gp_bank_first_and_apply_wearer_tier() -> None:
    payer = _member("payer", name="Paymaster", gold=100, bank_gold=150, level=10)
    wearer = _member("wearer", name="Walker", class_id="wizard", gold=0, level=5)
    session = _session(6, [payer, wearer])

    result = buy_shoes_of_fast_walk(
        session,
        payer_character_id=payer.character_id,
        recipient_kind="hero",
        recipient_id=wearer.character_id,
    )

    assert payer.bank_gold == 0
    assert payer.gold == 50
    assert wearer.inventory == [SHOES_OF_FAST_WALK]
    transaction = result["state"]["transactions"][0]
    assert transaction["cost_gp"] == 200
    assert transaction["payment"] == [
        {"name": "Paymaster", "bank_gold": 150, "carried_gold": 50}
    ]
    assert shoes_of_fast_walk_defense_bonus(wearer, session, escaping_melee=False) == 0
    assert shoes_of_fast_walk_defense_bonus(wearer, session, escaping_melee=True) == 2


def test_shoes_reject_ineligible_or_duplicate_hero_without_payment() -> None:
    payer = _member("payer", gold=500)
    barbarian = _member("barbarian", class_id="barbarian")
    session = _session(6, [payer, barbarian])

    with pytest.raises(ValueError, match="magic items"):
        buy_shoes_of_fast_walk(
            session,
            payer_character_id=payer.character_id,
            recipient_kind="hero",
            recipient_id=barbarian.character_id,
        )
    assert payer.gold == 500

    eligible = _member("eligible", class_id="wizard")
    session.party.append(eligible)
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=payer.character_id,
        recipient_kind="hero",
        recipient_id=eligible.character_id,
    )
    after_first = payer.gold
    with pytest.raises(ValueError, match="already"):
        buy_shoes_of_fast_walk(
            session,
            payer_character_id=payer.character_id,
            recipient_kind="hero",
            recipient_id=eligible.character_id,
        )
    assert payer.gold == after_first
    assert eligible.inventory.count(SHOES_OF_FAST_WALK) == 1


def test_hireling_shoes_remain_party_owned_and_use_party_tier_in_defense(monkeypatch) -> None:
    payer = _member("payer", name="Owner", gold=300, level=10)
    junior = _member("junior", level=2)
    hireling = _hireling()
    session = _session(6, [payer, junior], hirelings=[hireling])

    result = buy_shoes_of_fast_walk(
        session,
        payer_character_id=payer.character_id,
        recipient_kind="hireling",
        recipient_id=hireling.id,
    )

    assignment = result["state"]["shoe_assignments"][0]
    assert assignment["recipient_kind"] == "hireling"
    assert assignment["recipient_id"] == hireling.id
    assert assignment["owner_character_id"] == payer.character_id
    assert assignment["party_tier"] == 3
    assert SHOES_OF_FAST_WALK in payer.inventory
    assert hireling.statuses == [f"{SHOES_OF_FAST_WALK} (party-owned; Owner)"]
    assert shoes_of_fast_walk_defense_bonus(payer, session, escaping_melee=True) == 0
    assert shoes_of_fast_walk_hireling_defense_bonus(
        hireling,
        session,
        escaping_melee=False,
    ) == 0
    assert shoes_of_fast_walk_hireling_defense_bonus(
        hireling,
        session,
        escaping_melee=True,
    ) == 3

    from app.engine.hirelings import resolve_hireling_defense

    monkeypatch.setattr("app.engine.hirelings.roll_exploding_d6", lambda: (2, [2]))
    _passed, log = resolve_hireling_defense(
        hireling,
        EnemyState(
            id="foe",
            name="Foe",
            category="minion",
            level=3,
            life=1,
            max_life=1,
        ),
        session=session,
        escaping_melee=True,
    )
    assert any("party Tier (+3)" in line for line in log)
    assert any("2 + 3 = 5" in line for line in log)


def test_party_owned_hireling_pair_does_not_block_owner_pair_and_returns_on_departure() -> None:
    payer = _member("payer", name="Owner", gold=600, level=10)
    hireling = _hireling()
    session = _session(6, [payer], hirelings=[hireling])

    buy_shoes_of_fast_walk(
        session,
        payer_character_id=payer.character_id,
        recipient_kind="hireling",
        recipient_id=hireling.id,
    )
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=payer.character_id,
        recipient_kind="hero",
        recipient_id=payer.character_id,
    )

    assert payer.inventory.count(SHOES_OF_FAST_WALK) == 2
    assert shoes_of_fast_walk_defense_bonus(payer, session, escaping_melee=True) == 3

    owner_with_only_hireling_pair = _member("other", name="Other owner", gold=200, level=5)
    departing = _hireling("departing")
    return_session = _session(6, [owner_with_only_hireling_pair], hirelings=[departing])
    buy_shoes_of_fast_walk(
        return_session,
        payer_character_id=owner_with_only_hireling_pair.character_id,
        recipient_kind="hireling",
        recipient_id=departing.id,
    )
    assert shoes_of_fast_walk_defense_bonus(
        owner_with_only_hireling_pair,
        return_session,
        escaping_melee=True,
    ) == 0
    return_session.hirelings = []
    assert shoes_of_fast_walk_defense_bonus(
        owner_with_only_hireling_pair,
        return_session,
        escaping_melee=True,
    ) == 2


def test_assigned_pair_is_locked_and_magic_ineligible_transfers_never_gain_effect() -> None:
    owner = _member("owner", gold=200, level=5)
    hireling = _hireling()
    session = _session(6, [owner], hirelings=[hireling])
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=owner.character_id,
        recipient_kind="hireling",
        recipient_id=hireling.id,
    )
    assert "cannot be transferred or sold" in assigned_hireling_shoes_lock_reason(
        session,
        owner.character_id,
    )

    barbarian = _member("barbarian", class_id="barbarian")
    moved, reason = transfer_item_between(
        owner,
        barbarian,
        item_name=SHOES_OF_FAST_WALK,
    )
    assert moved is False
    assert "magic items" in reason
    barbarian.inventory.append(SHOES_OF_FAST_WALK)
    assert shoes_of_fast_walk_defense_bonus(barbarian, None, escaping_melee=True) == 0


def test_assigned_hireling_pair_cannot_be_bagged_and_bonus_requires_loose_owner_pair() -> None:
    owner = _member("owner", gold=200, level=5)
    hireling = _hireling()
    session = _session(6, [owner], hirelings=[hireling])
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=owner.character_id,
        recipient_kind="hireling",
        recipient_id=hireling.id,
    )
    bag = add_bag_of_carrying(owner)
    owner.inventory.append("Torch")
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())

    engine._move_bag_item(
        session,
        owner.character_id,
        item_container_id=bag.id,
        item_name=SHOES_OF_FAST_WALK,
        take_out=False,
    )

    assert SHOES_OF_FAST_WALK in owner.inventory
    assert SHOES_OF_FAST_WALK not in bag.contents
    assert "cannot be transferred or sold" in session.log[-1]
    assert shoes_of_fast_walk_hireling_defense_bonus(
        hireling,
        session,
        escaping_melee=True,
    ) == 2

    engine._move_bag_item(
        session,
        owner.character_id,
        item_container_id=bag.id,
        item_name="Torch",
        take_out=False,
    )
    assert "Torch" in bag.contents

    # Defensive validation also fails safe if another loss path removes the
    # reserved pair without consulting the deliberate-disposition guard.
    owner.inventory.remove(SHOES_OF_FAST_WALK)
    assert shoes_of_fast_walk_hireling_defense_bonus(
        hireling,
        session,
        escaping_melee=True,
    ) == 0


def test_extra_unassigned_pair_may_be_bagged_without_disabling_hireling_pair() -> None:
    owner = _member("owner", gold=400, level=5)
    hireling = _hireling()
    session = _session(6, [owner], hirelings=[hireling])
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=owner.character_id,
        recipient_kind="hireling",
        recipient_id=hireling.id,
    )
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=owner.character_id,
        recipient_kind="hero",
        recipient_id=owner.character_id,
    )
    bag = add_bag_of_carrying(owner)
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())

    engine._move_bag_item(
        session,
        owner.character_id,
        item_container_id=bag.id,
        item_name=SHOES_OF_FAST_WALK,
        take_out=False,
    )

    assert owner.inventory.count(SHOES_OF_FAST_WALK) == 1
    assert bag.contents.count(SHOES_OF_FAST_WALK) == 1
    assert shoes_of_fast_walk_hireling_defense_bonus(
        hireling,
        session,
        escaping_melee=True,
    ) == 2


def test_kukla_compartment_reserves_assigned_pair_but_accepts_an_extra_pair() -> None:
    owner = _member("owner", class_id="kukla", gold=400, level=5)
    hireling = _hireling()
    session = _session(6, [owner], hirelings=[hireling])
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=owner.character_id,
        recipient_kind="hireling",
        recipient_id=hireling.id,
    )
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())

    engine._use_class_ability(
        session,
        owner.character_id,
        "kukla_compartment_stash",
        item_name=SHOES_OF_FAST_WALK,
    )

    assert owner.inventory.count(SHOES_OF_FAST_WALK) == 1
    assert SHOES_OF_FAST_WALK not in owner.kukla_compartment_items
    assert "put out of reach in storage" in session.log[-1]

    buy_shoes_of_fast_walk(
        session,
        payer_character_id=owner.character_id,
        recipient_kind="hero",
        recipient_id=owner.character_id,
    )
    engine._use_class_ability(
        session,
        owner.character_id,
        "kukla_compartment_stash",
        item_name=SHOES_OF_FAST_WALK,
    )

    assert owner.inventory.count(SHOES_OF_FAST_WALK) == 1
    assert owner.kukla_compartment_items.count(SHOES_OF_FAST_WALK) == 1
    assert shoes_of_fast_walk_hireling_defense_bonus(
        hireling,
        session,
        escaping_melee=True,
    ) == 2


def test_unassigned_owner_pair_remains_transferable_while_another_pair_is_on_a_hireling() -> None:
    owner = _member("owner", gold=400, level=5)
    hireling = _hireling()
    session = _session(6, [owner], hirelings=[hireling])
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=owner.character_id,
        recipient_kind="hireling",
        recipient_id=hireling.id,
    )
    buy_shoes_of_fast_walk(
        session,
        payer_character_id=owner.character_id,
        recipient_kind="hero",
        recipient_id=owner.character_id,
    )

    assert owner.inventory.count(SHOES_OF_FAST_WALK) == 2
    assert assigned_hireling_shoes_lock_reason(session, owner.character_id) == ""


def test_illusion_lesson_validates_learner_before_charging_and_is_once_only() -> None:
    payer = _member("payer", gold=50, bank_gold=100)
    rogue = _member("rogue", class_id="rogue")
    wizard = _member("wizard", class_id="wizard")
    session = _session(6, [payer, rogue, wizard])
    options = [_illusion_option()]

    with pytest.raises(ValueError, match="cannot normally add"):
        teach_leprechaun_illusion_spell(
            session,
            payer_character_id=payer.character_id,
            learner_character_id=rogue.character_id,
            spell_name="Mirror Image",
            spell_options=options,
        )
    assert (payer.gold, payer.bank_gold) == (50, 100)

    result = teach_leprechaun_illusion_spell(
        session,
        payer_character_id=payer.character_id,
        learner_character_id=wizard.character_id,
        spell_name="Mirror Image",
        spell_options=options,
    )
    assert result["state"]["illusion_lesson"]["cost_gp"] == 100
    assert (payer.gold, payer.bank_gold) == (50, 0)
    assert wizard.spells == ["Mirror Image"]

    with pytest.raises(ValueError, match="only one illusion spell"):
        teach_leprechaun_illusion_spell(
            session,
            payer_character_id=payer.character_id,
            learner_character_id=wizard.character_id,
            spell_name="Mirror Image",
            spell_options=options,
        )
    assert wizard.spells == ["Mirror Image"]


def test_illusion_lesson_becomes_free_only_from_three_recorded_shoe_purchases() -> None:
    payer = _member("payer", gold=700, level=10)
    recipient_one = _member("one", class_id="wizard")
    recipient_two = _member("two", class_id="cleric")
    learner = _member("learner", class_id="illusionist")
    hireling = _hireling()
    session = _session(
        6,
        [payer, recipient_one, recipient_two, learner],
        hirelings=[hireling],
    )

    for recipient_kind, recipient_id in (
        ("hero", recipient_one.character_id),
        ("hero", recipient_two.character_id),
        ("hireling", hireling.id),
    ):
        buy_shoes_of_fast_walk(
            session,
            payer_character_id=payer.character_id,
            recipient_kind=recipient_kind,
            recipient_id=recipient_id,
        )
    assert payer.gold == 100

    result = teach_leprechaun_illusion_spell(
        session,
        payer_character_id=payer.character_id,
        learner_character_id=learner.character_id,
        spell_name="Mirror Image",
        spell_options=[_illusion_option(native_class_ids=["illusionist"])],
    )

    assert payer.gold == 100
    assert result["state"]["illusion_lesson"]["cost_gp"] == 0
    assert result["state"]["illusion_lesson"]["free_after_three_pairs"] is True


def test_deoldyn_validates_entire_batch_before_taking_any_payment() -> None:
    archer = _member("archer", gold=200, level=2)
    non_archer = _member("rogue", class_id="rogue", gold=200, level=2)
    session = _session(11, [archer, non_archer])

    with pytest.raises(ValueError, match="may not use"):
        train_with_deoldyn(
            session,
            trainings=[
                {"character_id": archer.character_id, "outcome": "deadly_accuracy"},
                {"character_id": non_archer.character_id, "outcome": "dead_shot"},
            ],
            roller=lambda _member: _roll(6),
        )

    assert archer.gold == 200
    assert non_archer.gold == 200
    assert repeatable_service_state(session) == {}


def test_deoldyn_takes_all_payments_before_rolling_and_marks_skill_sources() -> None:
    warrior = _member("warrior", gold=100, bank_gold=100, level=2)
    ranger = _member("ranger", class_id="ranger", gold=100, bank_gold=100, level=3)
    session = _session(11, [warrior, ranger])
    calls: list[str] = []

    def roller(member: PartyMemberState) -> AdvancementRollResult:
        assert (warrior.gold, warrior.bank_gold) == (80, 0)
        assert (ranger.gold, ranger.bank_gold) == (20, 0)
        calls.append(member.character_id)
        return _roll(6)

    result = train_with_deoldyn(
        session,
        trainings=[
            {"character_id": warrior.character_id, "outcome": "deadly_accuracy"},
            {"character_id": ranger.character_id, "outcome": "dead_shot"},
        ],
        roller=roller,
    )

    assert calls == [warrior.character_id, ranger.character_id]
    assert [item["cost_gp"] for item in result["results"]] == [120, 180]
    assert warrior.learned_expert_skills == ["deadly_accuracy"]
    assert warrior.abilities == ["Deadly Accuracy"]
    assert warrior.expert_skill_targets["deadly_accuracy"] == "tag_deoldyn"
    assert ranger.learned_expert_skills == ["dead_shot"]
    assert ranger.abilities == ["Dead Shot"]
    assert ranger.expert_skill_targets["dead_shot"] == "tag_deoldyn"

    late_trainee = _member("late", gold=500, level=2)
    session.party.append(late_trainee)
    with pytest.raises(ValueError, match="simultaneous training batch has already"):
        train_with_deoldyn(
            session,
            trainings=[{"character_id": late_trainee.character_id, "outcome": "dead_shot"}],
            roller=lambda _member: _roll(6),
        )
    assert late_trainee.gold == 500


def test_deoldyn_failed_roll_keeps_the_full_payment() -> None:
    warrior = _member("warrior", gold=100, bank_gold=100, level=3)
    session = _session(11, [warrior])

    result = train_with_deoldyn(
        session,
        trainings=[{"character_id": warrior.character_id, "outcome": "dead_shot"}],
        roller=lambda _member: _roll(1),
    )

    assert result["results"][0]["success"] is False
    assert (warrior.gold, warrior.bank_gold) == (20, 0)
    assert "dead_shot" not in warrior.learned_expert_skills
    assert repeatable_service_state(session)["trained_character_ids"] == [warrior.character_id]


@pytest.mark.parametrize("class_id", ["warrior", "wood_elf", "fire_elf"])
def test_deoldyn_level_up_is_limited_to_a_normal_elf(class_id: str) -> None:
    member = _member("candidate", class_id=class_id, gold=500, level=3)
    session = _session(11, [member])

    with pytest.raises(ValueError, match="Only a normal Elf"):
        train_with_deoldyn(
            session,
            trainings=[
                {
                    "character_id": member.character_id,
                    "outcome": "level_up",
                    "new_spell": "Fireball",
                }
            ],
            roller=lambda _member: _roll(6),
        )
    assert member.gold == 500
    assert member.level == 3


def test_deoldyn_elf_level_up_checks_repeat_tier_gate_and_spell_before_payment() -> None:
    repeated = _member("repeated", class_id="elf", gold=500, level=3)
    repeated_session = _session(11, [repeated])
    repeated_session.last_leveled_character_id = repeated.character_id
    with pytest.raises(ValueError, match="cannot level twice"):
        train_with_deoldyn(
            repeated_session,
            trainings=[{"character_id": repeated.character_id, "outcome": "level_up", "new_spell": "Fireball"}],
        )
    assert repeated.gold == 500

    untrained = _member("untrained", class_id="elf", gold=500, level=5)
    untrained_session = _session(11, [untrained])
    with pytest.raises(ValueError, match="needs Expert training"):
        train_with_deoldyn(
            untrained_session,
            trainings=[{"character_id": untrained.character_id, "outcome": "level_up", "new_spell": "Fireball"}],
        )
    assert untrained.gold == 500

    invalid_spell = _member("invalid", class_id="elf", gold=500, level=3)
    invalid_session = _session(11, [invalid_spell])
    with pytest.raises(ValueError, match="Choose the spell"):
        train_with_deoldyn(
            invalid_session,
            trainings=[{"character_id": invalid_spell.character_id, "outcome": "level_up", "new_spell": "Not a spell"}],
        )
    assert invalid_spell.gold == 500


def test_deoldyn_normal_elf_may_pay_roll_and_level_with_a_valid_spell() -> None:
    elf = _member("elf", class_id="elf", gold=300, level=3)
    session = _session(11, [elf])

    result = train_with_deoldyn(
        session,
        trainings=[
            {
                "character_id": elf.character_id,
                "outcome": "level_up",
                "new_spell": "Fireball",
            }
        ],
        roller=lambda _member: _roll(6),
    )

    assert result["results"][0]["success"] is True
    assert elf.level == 4
    assert elf.gold == 120
    assert elf.spells == ["Fireball"]
    assert session.last_leveled_character_id == elf.character_id


@pytest.mark.parametrize("rumor_number", [6, 11])
def test_zero_transaction_done_is_allowed_and_idempotent(rumor_number: int) -> None:
    session = _session(rumor_number, [_member("hero")])

    first = finish_repeatable_service(session)
    log_after_first = list(session.log)
    second = finish_repeatable_service(session)

    assert first["phase"] == "resolved"
    assert first["resolved"] is True
    assert first["transactions"] == []
    assert second == first
    assert session.log == log_after_first
