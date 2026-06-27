"""PANDORA hostility, Lex soul tax, and Courtship combat wiring (TCOTFD)."""

from __future__ import annotations

from unittest.mock import patch

from app.engine.combat import apply_enemy_damage, resolve_flee
from app.engine.courtship_combat import (
    COURTSHIP_ENTANGLED,
    courtship_clear_entangle_on_escape,
    necrogaunt_rescue_blocks_melee,
)
from app.engine.courtship_lex import (
    apply_lex_soul_tax_if_needed,
    is_lex_granted_item,
    record_lex_grant,
)
from app.engine.courtship_pandora import (
    has_pandora,
    pandora_blocks_wooing,
    pandora_forces_fight_to_death,
    prepare_pandora_fight,
)
from app.schemas import EnemyState
from tests.test_forsaken_depths_engine import _party_member, engine


def test_pandora_blocks_wooing_except_lady() -> None:
    session = engine().create_session(
        "pandora",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_keywords.append("PANDORA")
    assert has_pandora(session)
    assert pandora_forces_fight_to_death(session, "Matron of Summer")
    assert not pandora_forces_fight_to_death(session, "Lady of Lament")
    assert pandora_blocks_wooing(session, "Death Orchid")
    assert not pandora_blocks_wooing(session, "Lady of Lament")


def test_prepare_pandora_tags_only_hostile_foes() -> None:
    session = engine().create_session(
        "pandora-tags",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_keywords.append("PANDORA")
    matron = EnemyState(
        id="m1",
        name="Matron of Summer",
        category="boss",
        level=4,
        life=10,
        max_life=10,
        tags=["courtship:Matron of Summer"],
    )
    lady = EnemyState(
        id="l1",
        name="Lady of Lament",
        category="boss",
        level=4,
        life=10,
        max_life=10,
        tags=["courtship:Lady of Lament"],
    )
    prepare_pandora_fight(session, [matron, lady])
    assert session.reaction_key == "fight_to_death"
    assert "fight_to_death" in matron.tags
    assert "fight_to_death" not in lady.tags


def test_lex_soul_tax_only_on_first_use() -> None:
    session = engine().create_session(
        "lex-tax",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    item = "Potion of Healing"
    record_lex_grant(session, member, item)
    assert is_lex_granted_item(session, member, item)

    with patch("app.engine.courtship_lex.roll_d6", return_value=3):
        assert apply_lex_soul_tax_if_needed(session, member, item, show_rolls=False)
    assert apply_lex_soul_tax_if_needed(session, member, item, show_rolls=False)

    session.courtship_lex_soul_taxed.clear()
    with patch("app.engine.courtship_lex.roll_d6", return_value=1):
        assert not apply_lex_soul_tax_if_needed(session, member, item, show_rolls=False)
    assert member.current_life == 0


def test_necrogaunt_rescue_blocks_melee_only() -> None:
    session = engine().create_session(
        "necro-rescue",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_necrogaunt_rescue_active = True
    assert necrogaunt_rescue_blocks_melee(session, missile=False, from_spell=False)
    assert not necrogaunt_rescue_blocks_melee(session, missile=True, from_spell=False)
    assert not necrogaunt_rescue_blocks_melee(session, missile=False, from_spell=True)


def test_entangle_cleared_on_escape() -> None:
    session = engine().create_session(
        "entangle",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    member = session.party[0]
    member.statuses.append(COURTSHIP_ENTANGLED)
    log = courtship_clear_entangle_on_escape(session, session.party)
    assert COURTSHIP_ENTANGLED not in member.statuses
    assert log


def test_spell_damage_triggers_roper_backlash() -> None:
    session = engine().create_session(
        "roper-spell",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    member = session.party[0]
    member.statuses.append(COURTSHIP_ENTANGLED)
    member.current_life = 5
    roper = EnemyState(
        id="r1",
        name="Stone Roper",
        category="weird",
        level=4,
        life=8,
        max_life=8,
        tags=["courtship:Stone Roper"],
    )
    log: list[str] = []
    apply_enemy_damage(
        roper,
        1,
        courtship_spell_session=session,
        courtship_spell_party=session.party,
        courtship_spell_log=log,
    )
    assert member.current_life == 4
    assert any("backlash" in line for line in log)


def test_flee_clears_stone_roper_entangle() -> None:
    session = engine().create_session(
        "flee-entangle",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    member = session.party[0]
    member.statuses.append(COURTSHIP_ENTANGLED)
    from app.engine.combat import CombatContext

    result = resolve_flee(
        session.party,
        [],
        show_rolls=False,
        context=CombatContext(session=session),
        skip_parting_attacks=True,
    )
    assert result.fled
    assert COURTSHIP_ENTANGLED not in member.statuses
    assert any("tendrils release" in line for line in result.log)


def test_colleen_per_round_skip_attack() -> None:
    from app.engine.courtship_combat import (
        COURTSHIP_SKIP_ATTACK,
        apply_courtship_per_turn,
        consume_courtship_skip_attack,
    )

    session = engine().create_session(
        "colleen",
        "party-1",
        [_party_member()],
        ruleset="forsaken_depths",
        courtship_enabled=True,
    )
    session.courtship_demesne_active = True
    member = session.party[0]
    colleen = EnemyState(
        id="c1",
        name="Colleen of Lilies",
        category="minions",
        level=4,
        life=5,
        max_life=5,
        attacks=1,
        tags=["courtship:Colleen of Lilies"],
    )
    from unittest.mock import patch

    with patch("app.engine.courtship_combat._mesmerize_save", return_value=(False, [])):
        log = apply_courtship_per_turn(
            session,
            session.party,
            [colleen],
            show_rolls=False,
        )
    assert COURTSHIP_SKIP_ATTACK in member.statuses
    assert any("skip" in line.lower() for line in log)
    assert consume_courtship_skip_attack(member)
    assert COURTSHIP_SKIP_ATTACK not in member.statuses
