from __future__ import annotations

from pathlib import Path

from app.engine.hirelings import (
    hireling_morale_target,
    load_hirelings_catalog,
    offer_bodyguard_intercept,
    resolve_acolyte_blessing,
    resolve_bodyguard_intercept,
)
from app.engine.heroic_skill_effects import resolve_fear_save
from app.engine.madness import madness_points
from app.schemas import (
    EnemyState,
    HirelingState,
    MapState,
    PartyMemberState,
    PendingAcolyteBlessingState,
    SessionState,
    TileState,
)


def _session(*, patron_life: int = 4) -> SessionState:
    cleric = PartyMemberState(
        character_id="cleric",
        name="Cleric",
        class_id="cleric",
        class_name="Cleric",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
    )
    patron = PartyMemberState(
        character_id="patron",
        name="Patron",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=patron_life,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=2,
    )
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="combat",
        party=[cleric, patron],
        hirelings=[
            HirelingState(
                id="bg",
                retainer_type="bodyguard",
                name="Bruno",
                life=3,
                max_life=3,
                marching_order=5,
                assigned_character_id="cleric",
            ),
            HirelingState(
                id="ac",
                retainer_type="acolyte",
                name="Ada",
                life=2,
                max_life=2,
                marching_order=6,
                assigned_character_id="cleric",
            ),
        ],
        professional_buffs={"storyteller_morale": True, "storyteller_patron_id": "patron"},
        map_state=MapState(
            tiles=[
                TileState(
                    id="t",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[
                        EnemyState(
                            id="e1",
                            name="Ogre",
                            category="boss",
                            level=4,
                            life=4,
                            max_life=4,
                        )
                    ],
                )
            ],
            current_tile_id="t",
        ),
        created_at="now",
        updated_at="now",
    )


def test_fear_save_failure_grants_madness_without_explicit_source() -> None:
    session = _session()
    member = session.party[1]
    member.level = 5
    saved, _ = resolve_fear_save(session, member, 99, show_rolls=False, label="terror")
    assert not saved
    assert madness_points(member) == 1


def test_bodyguard_intercept_choice_decline_hits_protectee(monkeypatch) -> None:
    session = _session()
    enemy = session.map_state.tiles[0].enemies[0]
    protectee = session.party[0]
    hireling = session.hirelings[0]
    offer_bodyguard_intercept(session, protectee, hireling, enemy)
    monkeypatch.setattr(
        "app.engine.dice.roll_exploding_for_level",
        lambda member: (10, [6]),
    )
    log = resolve_bodyguard_intercept(session, choice="decline", show_rolls=False)
    assert session.pending_bodyguard_intercept is None
    assert any("without bodyguard help" in line for line in log)


def test_storyteller_bonus_drops_when_patron_falls() -> None:
    session = _session(patron_life=0)
    hireling = session.hirelings[0]
    target = hireling_morale_target(session, hireling, load_hirelings_catalog())
    assert target == 3
    assert not hireling.morale_storyteller_used

    session2 = _session(patron_life=4)
    hireling2 = session2.hirelings[0]
    hireling2.morale_storyteller_used = False
    target_live = hireling_morale_target(session2, hireling2, load_hirelings_catalog())
    assert target_live == 2
    assert hireling2.morale_storyteller_used


def test_acolyte_blessing_skip_leaves_pending_cleared() -> None:
    session = _session()
    session.pending_acolyte_blessing = PendingAcolyteBlessingState(
        cleric_id="cleric",
        hireling_id="ac",
    )
    log = resolve_acolyte_blessing(session, choice="skip", show_rolls=False)
    assert session.pending_acolyte_blessing is None
    assert any("does not call on" in line for line in log)
