from __future__ import annotations

from pathlib import Path

from app.engine.combat import CombatRound
from app.engine.camp import prepare_camp_outside
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import ExitState, MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def test_prepare_camp_outside_applies_shared_entrance_and_recovery_state() -> None:
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Alive",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=1,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(tiles=[entrance], current_tile_id="elsewhere"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        current_tile_entry_exit_id="old-exit",
        summary=["old summary"],
    )
    calls: list[str] = []

    healed = prepare_camp_outside(
        session,
        entrance,
        refresh_connections=lambda _session, _entrance: calls.append("refresh"),
        initialize_entrance=lambda _entrance: calls.append("initialize") or True,
        reset_resources=lambda _session: calls.append("reset"),
    )

    assert calls == ["refresh", "initialize", "reset"]
    assert session.map_state.current_tile_id == entrance.id
    assert session.current_tile_entry_exit_id is None
    assert session.camped_outside is True
    assert session.summary == []
    assert healed == ["Alive"]
    assert session.party[0].current_life == 3


def test_dungeon_exit_with_fallen_retreats() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        exits=[
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            )
        ],
    )
    deep = TileState(
        id="deep",
        x=0,
        y=1,
        tile_key="11",
        tile_type="room",
        title="Deep",
        description="Deep",
        fallen_character_ids=["h2"],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Alive",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=1,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            ),
            PartyMemberState(
                character_id="h2",
                name="Fallen",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=0,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Magic sword"],
            ),
        ],
        map_state=MapState(tiles=[entrance, deep], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        expended_spells={"h1": ["Sleep"]},
        healing_prayer_uses={"h1": 1},
    )
    eng.advance(session, "explore", exit_id="out")
    assert session.mode == "exploration"
    assert session.camped_outside is True
    assert session.map_state.current_tile_id == "ent"
    assert session.party[0].current_life == session.party[0].max_life
    assert session.expended_spells == {}
    assert session.healing_prayer_uses == {}
    assert len(session.map_state.tiles) == 2


def test_dungeon_exit_without_fallen_completes() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        exits=[
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            )
        ],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Alive",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            ),
        ],
        map_state=MapState(tiles=[entrance], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "explore", exit_id="out")
    assert session.mode == "complete"
    assert session.camped_outside is False


def test_dungeon_exit_blocks_completion_with_pending_classical_xp() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        exits=[
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            )
        ],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Alive",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            ),
        ],
        map_state=MapState(tiles=[entrance], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        xp_rolls_pending=1,
        xp_system="classical",
    )
    eng.advance(session, "explore", exit_id="out", dungeon_exit_intent="complete")
    assert session.mode == "exploration"
    assert session.camped_outside is False
    assert session.xp_rolls_pending == 1
    assert any("XP roll" in entry and "before completing" in entry for entry in session.log)


def test_dungeon_exit_return_intent_camps_and_heals_without_completing() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        exits=[
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            )
        ],
    )
    deep = TileState(
        id="deep",
        x=0,
        y=1,
        tile_key="11",
        tile_type="room",
        title="Deep",
        description="Deep",
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Wounded",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=1,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                statuses=["Continual Light"],
            ),
        ],
        map_state=MapState(tiles=[entrance, deep], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        alchemist_potion_bought=["h1"],
        alchemist_poison_bought=["h1"],
        potion_used_character_ids=["h1"],
        bandage_used_character_ids=["h1"],
        expended_spells={"h1": ["Sleep"]},
        healing_prayer_uses={"h1": 2},
        rest_used=True,
        rest_available=True,
        rest_block_reason="Already rested.",
        rage_uses_spent={"h1": 1},
        luck_points_spent={"h1": 1},
        panache_points={"h1": 2},
        paladin_prayer_spent={"h1": 1},
        nourishing_meal_used=True,
        pending_save_reroll={"character_id": "h1", "target": 4},
        acrobat_tricks_spent={"h1": 1},
        gnome_gadgets_spent={"h1": 2},
        mushroom_spore_uses={"h1": 1},
        foe_level_penalties={"e1": 1},
        assassin_hidden_id="h1",
        assassin_mark_enemy_id="e1",
        gnome_smokescreen_ready=True,
        skip_parting_flee=True,
        acrobat_skip_attack={"h1": True},
        gladiator_counter_pending={"h1": {"enemy_id": "e1", "damage": 1}},
        gladiator_counter_used=["h1"],
        evasion_character_ids=["h1"],
        expert_encounter_spent={"h1": ["double_shot"]},
        expert_protective_incense_target="h1",
        phasing_panther_escape_used=["h1"],
        pending_treasure_reroll_tile_id="deep",
        pending_search_reroll_tile_id="deep",
        divine_smite_used=["h1"],
        army_of_dolls_deployed=["h1"],
        sacrifice_shield_used=["h1"],
        hyphae_used=["h1"],
        kukla_doll_active=["h1"],
        graceful_save_reroll_id="h1",
        hyphae_search_bonus_id="h1",
        paladin_steed_active_id="h1",
        continual_light_owner_id="h1",
        heroes_rest_used=True,
        heroic_courage_used=["h1"],
        legendary_courage_used=["h1"],
        training_focus_bonus={"h1": 1},
        aggressive_stance_penalty=["h1"],
        heroic_carnage_bonus={"h1": 2},
        heros_banquet_used=True,
        song_of_elidra_used=True,
        mass_blessing_used=True,
        mass_blessing_active_round=3,
        protected_by_fate_used=["h1"],
        yogic_preservation_used=["h1"],
        restore_mental_capacity_used=True,
        copy_grimoire_used=["h1"],
        ward_of_protection_targets={"h1": "h1"},
        druid_companion_life=1,
        druid_companion_max_life=4,
    )

    eng.advance(session, "explore", exit_id="out", dungeon_exit_intent="return")

    assert session.mode == "exploration"
    assert session.camped_outside is True
    assert session.map_state.current_tile_id == "ent"
    assert session.party[0].current_life == session.party[0].max_life
    assert len(session.map_state.tiles) == 2
    assert session.alchemist_potion_bought == []
    assert session.alchemist_poison_bought == []
    assert session.potion_used_character_ids == []
    assert session.bandage_used_character_ids == []
    assert session.expended_spells == {}
    assert session.healing_prayer_uses == {}
    assert session.rest_used is False
    assert session.rest_available is False
    assert session.rest_block_reason == ""
    assert session.rage_uses_spent == {}
    assert session.luck_points_spent == {}
    assert session.panache_points == {}
    assert session.paladin_prayer_spent == {}
    assert session.nourishing_meal_used is False
    assert session.pending_save_reroll is None
    assert session.acrobat_tricks_spent == {}
    assert session.gnome_gadgets_spent == {}
    assert session.mushroom_spore_uses == {}
    assert session.foe_level_penalties == {}
    assert session.assassin_hidden_id is None
    assert session.assassin_mark_enemy_id is None
    assert session.gnome_smokescreen_ready is False
    assert session.skip_parting_flee is False
    assert session.acrobat_skip_attack == {}
    assert session.gladiator_counter_pending == {}
    assert session.gladiator_counter_used == []
    assert session.evasion_character_ids == []
    assert session.expert_encounter_spent == {}
    assert session.expert_protective_incense_target is None
    assert session.phasing_panther_escape_used == ["h1"]
    assert session.pending_treasure_reroll_tile_id is None
    assert session.pending_search_reroll_tile_id is None
    assert session.divine_smite_used == []
    assert session.army_of_dolls_deployed == []
    assert session.sacrifice_shield_used == []
    assert session.hyphae_used == []
    assert session.kukla_doll_active == []
    assert session.graceful_save_reroll_id is None
    assert session.hyphae_search_bonus_id is None
    assert session.paladin_steed_active_id is None
    assert session.continual_light_owner_id is None
    assert "Continual Light" not in session.party[0].statuses
    assert session.heroes_rest_used is False
    assert session.heroic_courage_used == []
    assert session.legendary_courage_used == []
    assert session.training_focus_bonus == {}
    assert session.aggressive_stance_penalty == []
    assert session.heroic_carnage_bonus == {}
    assert session.heros_banquet_used is False
    assert session.song_of_elidra_used is False
    assert session.mass_blessing_used is False
    assert session.mass_blessing_active_round == -1
    assert session.protected_by_fate_used == []
    assert session.yogic_preservation_used == []
    assert session.restore_mental_capacity_used is False
    assert session.copy_grimoire_used == []
    assert session.ward_of_protection_targets == {}
    assert session.druid_companion_life == session.druid_companion_max_life
    assert any("remain ready for return" in entry for entry in session.log)
    assert any("resources refresh" in entry for entry in session.log)


def test_return_from_camp_reenters_from_entrance_tile() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        footprint_width=2,
        footprint_height=1,
        exits=[
            ExitState(
                id="into",
                direction="east",
                kind="passage",
                x=1,
                y=0,
                status="open",
                destination_tile_id="deep",
            ),
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            ),
        ],
    )
    deep = TileState(
        id="deep",
        x=2,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Deep",
        description="Deep",
        exits=[
            ExitState(
                id="back",
                direction="west",
                kind="passage",
                status="open",
                destination_tile_id="ent",
            )
        ],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Ready",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            ),
        ],
        map_state=MapState(tiles=[entrance, deep], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        camped_outside=True,
    )

    assert session.map_state.current_tile_id == "ent"
    eng.advance(session, "return_to_dungeon")
    assert session.camped_outside is False
    assert session.map_state.current_tile_id == "ent"
    assert any("enters the dungeon at the entrance" in entry for entry in session.log)


def test_camped_party_cannot_move_deeper_before_returning() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        footprint_width=2,
        footprint_height=1,
        exits=[
            ExitState(
                id="into",
                direction="east",
                kind="passage",
                x=1,
                y=0,
                status="open",
                destination_tile_id="deep",
            )
        ],
    )
    deep = TileState(
        id="deep",
        x=2,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Deep",
        description="Deep",
        exits=[
            ExitState(
                id="back",
                direction="west",
                kind="passage",
                status="open",
                destination_tile_id="ent",
            )
        ],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[entrance, deep], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        camped_outside=True,
    )

    eng.advance(session, "explore", exit_id="into")

    assert session.camped_outside is True
    assert session.map_state.current_tile_id == "ent"
    assert any("Return to the dungeon before moving deeper" in entry for entry in session.log)


def test_camped_saved_session_normalizes_to_entrance_tile() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
    )
    deep = TileState(
        id="deep",
        x=2,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Deep",
        description="Deep",
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[],
        map_state=MapState(tiles=[entrance, deep], current_tile_id="deep"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        camped_outside=True,
    )

    normalized, changed = eng.normalize_session(session)
    assert changed is True
    assert normalized.map_state.current_tile_id == "ent"


def test_dungeon_exit_with_fallen_outside_keeps_recovery_camp() -> None:
    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        exits=[
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            )
        ],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Alive",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            ),
            PartyMemberState(
                character_id="h2",
                name="Fallen",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=0,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                statuses=["Fallen"],
            ),
        ],
        fallen_outside_character_ids=["h2"],
        map_state=MapState(tiles=[entrance], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "explore", exit_id="out")
    assert session.mode == "exploration"
    assert session.camped_outside is True
    assert session.map_state.current_tile_id == "ent"
    assert any("awaiting recovery" in entry.lower() for entry in session.log)
    assert not any("leaves the dungeon" in entry.lower() for entry in session.log)


def test_combat_result_preserves_carried_body_member() -> None:
    eng = engine()
    tile = TileState(
        id="room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
    )
    alive = PartyMemberState(
        character_id="h1",
        name="Alive",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    fallen = PartyMemberState(
        character_id="h2",
        name="Fallen",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=0,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="combat",
        party=[alive, fallen],
        body_carrier_id="h1",
        carried_body_id="h2",
        map_state=MapState(tiles=[tile], current_tile_id="room"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    result = CombatRound(party=[alive.model_copy(deep=True)], enemies=[], log=[], combat_over=True)
    eng._apply_combat_result(session, tile, result, show_rolls=False)
    assert {member.character_id for member in session.party} == {"h1", "h2"}
    assert session.carried_body_id == "h2"
    assert session.body_carrier_id == "h1"


def test_dungeon_exit_is_blocked_by_living_foes_at_entrance() -> None:
    from app.schemas import EnemyState

    eng = engine()
    entrance = TileState(
        id="ent",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
        alchemist_available=True,
        exits=[
            ExitState(
                id="out",
                direction="south",
                kind="passage",
                dungeon_exit=True,
                status="open",
            )
        ],
        enemies=[
            EnemyState(
                id="e1",
                name="Rat",
                category="vermin",
                level=1,
                life=1,
                max_life=1,
            )
        ],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        party=[
            PartyMemberState(
                character_id="h1",
                name="Alive",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            ),
        ],
        map_state=MapState(tiles=[entrance], current_tile_id="ent"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "explore", exit_id="out")
    assert session.mode == "exploration"
    assert session.map_state.current_tile_id == "ent"
    assert any("living foes block every exit" in entry.lower() for entry in session.log)
