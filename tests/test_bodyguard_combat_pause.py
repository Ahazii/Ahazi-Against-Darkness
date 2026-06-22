from __future__ import annotations

from app.engine.combat import CombatContext, resolve_combat_round
from app.schemas import EnemyState, HirelingState, MapState, PartyMemberState, SessionState, TileState


def _session_with_bodyguard() -> SessionState:
    cleric = PartyMemberState(
        character_id="cleric",
        name="Cleric",
        class_id="cleric",
        class_name="Cleric",
        level=3,
        xp=0,
        gold=100,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=4,
    )
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="combat",
        party=[cleric],
        hirelings=[
            HirelingState(
                id="bg",
                retainer_type="bodyguard",
                name="Bruno",
                life=3,
                max_life=3,
                marching_order=5,
                assigned_character_id="cleric",
            )
        ],
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
                        ),
                        EnemyState(
                            id="e2",
                            name="Troll",
                            category="boss",
                            level=4,
                            life=4,
                            max_life=4,
                        ),
                    ],
                )
            ],
            current_tile_id="t",
        ),
        created_at="now",
        updated_at="now",
    )


def test_bodyguard_offer_pauses_combat_round() -> None:
    session = _session_with_bodyguard()
    session.combat_round = 0
    context = CombatContext(session=session, combat_round=1)
    result = resolve_combat_round(
        session.party,
        session.map_state.tiles[0].enemies,
        show_rolls=False,
        context=context,
        encounter_round=session.combat_round,
        party_surprised=True,
        foes_strike_first=True,
    )
    assert result.combat_paused
    assert session.pending_bodyguard_intercept is not None
    assert session.combat_bodyguard_pause is not None
    assert session.combat_bodyguard_pause.remaining_attacks


def test_final_boss_check_logged_in_summary_mode(monkeypatch) -> None:
    from app.engine.experience import mark_final_boss_candidate

    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 2)
    enemies = [
        EnemyState(id="b", name="Ogre", category="boss", level=5, life=5, max_life=5),
    ]
    log, boss = mark_final_boss_candidate(
        enemies,
        major_foes_encountered=2,
        show_rolls=False,
    )
    assert boss is None
    assert any("Final Boss check" in line for line in log)
    assert any("No Final Boss designation" in line for line in log)
