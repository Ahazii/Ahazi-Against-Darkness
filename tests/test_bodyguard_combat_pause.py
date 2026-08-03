from __future__ import annotations

from pathlib import Path

from app.engine import combat
from app.engine.combat import CombatContext, CombatRound, resolve_combat_round
from app.engine.hirelings import resolve_bodyguard_intercept
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import (
    ActiveQuestState,
    CombatBodyguardPauseState,
    EnemyState,
    ExitState,
    HirelingState,
    MapState,
    PartyMemberState,
    SessionState,
    TileState,
)


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
    assert session.combat_bodyguard_pause.phases


def test_bodyguard_resume_after_intercept_completes_round() -> None:
    session = _session_with_bodyguard()
    session.map_state.tiles[0].enemies = [
        EnemyState(
            id="e1",
            name="Ogre",
            category="boss",
            level=4,
            life=4,
            max_life=4,
        )
    ]
    session.combat_round = 0
    context = CombatContext(session=session, combat_round=1)
    paused = resolve_combat_round(
        session.party,
        session.map_state.tiles[0].enemies,
        show_rolls=False,
        context=context,
        encounter_round=session.combat_round,
        party_surprised=True,
        foes_strike_first=True,
    )
    assert paused.combat_paused
    pause = session.combat_bodyguard_pause
    assert pause is not None
    assert pause.phases

    from app.engine.hirelings import resolve_bodyguard_intercept

    session.log.extend(resolve_bodyguard_intercept(session, choice="intercept", show_rolls=False))
    assert session.pending_bodyguard_intercept is None

    resumed = resolve_combat_round(
        session.party,
        session.map_state.tiles[0].enemies,
        show_rolls=False,
        context=CombatContext(session=session, combat_round=1),
        encounter_round=session.combat_round,
        resume_after_bodyguard=pause,
    )
    assert not resumed.combat_paused


def test_bodyguard_resume_legacy_empty_phases() -> None:
    from app.schemas import CombatBodyguardPauseState

    session = _session_with_bodyguard()
    session.combat_round = 0
    session.pending_bodyguard_intercept = None
    pause = CombatBodyguardPauseState(phase_index=0, phases=[], remaining_attacks=[])
    session.combat_bodyguard_pause = pause
    context = CombatContext(session=session, combat_round=1)
    result = resolve_combat_round(
        session.party,
        session.map_state.tiles[0].enemies,
        show_rolls=False,
        context=context,
        encounter_round=session.combat_round,
        resume_after_bodyguard=pause,
    )
    assert not result.combat_paused


def test_flee_bodyguard_choices_preserve_every_parting_attack_and_hireling_shoes(monkeypatch) -> None:
    session = _session_with_bodyguard()
    session.party[0].level = 6
    session.party[0].inventory = ["Shoes of Fast Walk"]
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="tag_generated_scene",
        description="Blackbird Hill bargain",
        tag_procedure_state={
            "tag_repeatable_service": {
                "shoe_assignments": [
                    {
                        "recipient_kind": "hireling",
                        "recipient_id": "bg",
                        "owner_character_id": "cleric",
                    }
                ]
            }
        },
    )
    monkeypatch.setattr("app.engine.hirelings.roll_exploding_d6", lambda: (6, [6]))
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())

    engine._flee(session, show_rolls=True)

    assert session.mode == "combat"
    assert session.pending_bodyguard_intercept is not None
    assert session.combat_bodyguard_pause is not None
    assert session.combat_bodyguard_pause.escape_kind == "flee"
    assert len(session.combat_bodyguard_pause.remaining_attacks) == 1
    first_escape_context = dict(session.combat_bodyguard_pause.escape_context)
    assert first_escape_context["party_character_ids"] == ["cleric"]
    assert first_escape_context["active_enemy_ids"] == ["e1", "e2"]
    assert not any("Combat ends in retreat" in line for line in session.log)

    # A bodyguard prompt may be saved and reloaded before the player answers.
    session = SessionState.model_validate(session.model_dump(mode="json"))
    session.log.extend(resolve_bodyguard_intercept(session, choice="intercept", show_rolls=True))
    engine._resume_bodyguard_paused_combat(session, show_rolls=True)

    assert session.mode == "combat"
    assert session.pending_bodyguard_intercept is not None
    assert session.combat_bodyguard_pause is not None
    assert session.combat_bodyguard_pause.escape_kind == "flee"
    assert session.combat_bodyguard_pause.escape_context == first_escape_context

    session.log.extend(resolve_bodyguard_intercept(session, choice="intercept", show_rolls=True))
    engine._resume_bodyguard_paused_combat(session, show_rolls=True)

    assert session.mode == "exploration"
    assert session.pending_bodyguard_intercept is None
    assert session.combat_bodyguard_pause is None
    assert sum("steps in front of" in line for line in session.log) == 2
    assert sum("Shoes of Fast Walk" in line and "party Tier (+2)" in line for line in session.log) == 2
    assert sum("Combat ends in retreat" in line for line in session.log) == 1
    assert sum("Flee wandering check" in line for line in session.log) == 1


def test_withdraw_bodyguard_pause_delays_door_move_and_wandering_until_resolved(monkeypatch) -> None:
    session = _session_with_bodyguard()
    session.map_state.tiles[0].enemies = [session.map_state.tiles[0].enemies[0]]
    destination = TileState(
        id="previous",
        x=1,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Previous Room",
        description="Previous Room",
    )
    outward = ExitState(
        id="withdraw-door",
        direction="east",
        kind="door",
        status="open",
        destination_tile_id=destination.id,
        door_open=True,
    )
    reciprocal = ExitState(
        id="return-door",
        direction="west",
        kind="door",
        status="open",
        destination_tile_id="t",
        door_open=True,
    )
    session.map_state.tiles[0].exits = [outward]
    destination.exits = [reciprocal]
    session.map_state.tiles.append(destination)
    monkeypatch.setattr("app.engine.hirelings.roll_exploding_d6", lambda: (6, [6]))
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())

    engine._withdraw(session, outward.id, show_rolls=True)

    assert session.mode == "combat"
    assert session.map_state.current_tile_id == "t"
    assert outward.door_open is True
    assert reciprocal.door_open is True
    assert not any("Withdraw wandering check" in line for line in session.log)

    session.log.extend(resolve_bodyguard_intercept(session, choice="intercept", show_rolls=True))
    engine._resume_bodyguard_paused_combat(session, show_rolls=True)

    assert session.mode == "exploration"
    assert session.map_state.current_tile_id == destination.id
    assert outward.door_open is False
    assert reciprocal.door_open is False
    assert session.combat_bodyguard_pause is None
    assert sum("Withdraw wandering check" in line for line in session.log) == 1
    assert sum("withdraws to Previous Room" in line for line in session.log) == 1


def test_declined_withdraw_intercept_keeps_escape_defense_modifiers(monkeypatch) -> None:
    session = _session_with_bodyguard()
    hero = session.party[0]
    hero.level = 6
    hero.gold = 0
    hero.inventory = ["Shoes of Fast Walk"]
    hero.learned_expert_skills = ["quick_footed"]
    session.map_state.tiles[0].enemies = [session.map_state.tiles[0].enemies[0]]
    session.map_state.tiles[0].enemies[0].level = 1
    session.map_state.tiles[0].enemies[0].category = "minions"
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (2, [2]))
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    context = engine._combat_context(session, session.map_state.tiles[0])
    from app.engine.combat import resolve_withdraw

    paused = resolve_withdraw(
        session.party,
        session.map_state.tiles[0].enemies,
        show_rolls=True,
        context=context,
    )
    assert paused.combat_paused
    assert session.pending_bodyguard_intercept is not None
    assert session.pending_bodyguard_intercept.escaping_melee is True
    assert session.pending_bodyguard_intercept.withdrawing is True

    enemy = session.map_state.tiles[0].enemies[0]
    ordinary_context = combat.combat_context_for_session(session)
    ordinary_modifier, _ = combat._defense_bonus(
        hero,
        enemy,
        context=ordinary_context,
    )
    escape_context = combat.combat_context_for_session(session)
    escape_context.withdrawing = True
    escape_modifier, _ = combat._defense_bonus(
        hero,
        enemy,
        context=escape_context,
        withdraw=True,
    )
    # TAG p.41 Shoes of Fast Walk add Tier (+2 here); Quick Footed adds +1;
    # the ordinary withdrawal rule adds +1.
    assert escape_modifier - ordinary_modifier == 4

    life_before = hero.current_life
    decline_log = resolve_bodyguard_intercept(session, choice="decline", show_rolls=True)

    assert hero.current_life == life_before
    assert any(
        f"Defense roll: Cleric vs Ogre: 2 + {escape_modifier} = {2 + escape_modifier}"
        in line
        for line in decline_log
    )


def test_bodyguard_resume_counts_boss_defeated_before_pause(monkeypatch) -> None:
    session = _session_with_bodyguard()
    boss = EnemyState(
        id="boss",
        name="Bandit Chieftain",
        category="boss",
        level=6,
        life=0,
        max_life=6,
    )
    guard = EnemyState(
        id="guard",
        name="TAG Bandits",
        category="minion",
        level=4,
        life=1,
        max_life=1,
    )
    tile = session.map_state.tiles[0]
    tile.content_key = "imported:tag-final-scene"
    tile.enemies = [boss, guard]
    session.adventure_type = "imported"
    session.imported_manifest = {"rooms": [{"id": "tag-final-scene", "title": "Bandit Chieftain's Den"}]}
    session.imported_quest_complete_when = {
        "type": "boss_defeated",
        "boss_name": "Bandit Chieftain",
        "room_id": "tag-final-scene",
    }
    session.active_quest = ActiveQuestState(
        tile_id=tile.id,
        key="imported_boss",
        description="Clear the hideout and decide whether to capture the chieftain alive.",
        boss_slay_pending=True,
        boss_target_name="Bandit Chieftain",
    )
    session.combat_bodyguard_pause = CombatBodyguardPauseState(
        phase_index=0,
        phases=["foe_melee"],
        remaining_attacks=[],
    )

    def fake_resolve(*args, **kwargs):
        guard.life = 0
        return CombatRound(party=session.party, enemies=[boss, guard], log=["Resume fake."], combat_over=True)

    monkeypatch.setattr("app.engine.random_dungeon.resolve_combat_round", fake_resolve)
    RandomDungeonEngine(rules=None, asset_dir=Path())._resume_bodyguard_paused_combat(session, show_rolls=False)

    assert session.active_quest is not None
    assert session.active_quest.completed
    assert any("Bandit Chieftain has been destroyed" in line for line in session.log)


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
