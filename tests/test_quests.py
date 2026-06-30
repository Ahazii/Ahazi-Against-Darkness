from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.engine.adventure_allowlists import major_foe_table_keys
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import ActiveQuestState, EnemyState, MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def base_session(**kwargs) -> SessionState:
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        lady_in_white_available=True,
    )
    defaults = dict(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=200,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
                inventory=["Potion of Healing"],
            )
        ],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def test_refuse_quest_blocks_lady() -> None:
    eng = engine()
    session = base_session()
    eng.advance(session, "refuse_quest")
    assert session.lady_in_white_refused is True
    assert session.map_state.tiles[0].lady_in_white_available is False


def test_accept_quest_sets_active_quest(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    session.party[0].gold = 0
    monkeypatch.setattr(
        "app.engine.random_dungeon.roll_d6",
        lambda: 2,
    )
    monkeypatch.setattr(
        "app.engine.class_abilities.roll_exploding_for_level",
        lambda _level: (6, [6]),
    )
    eng.advance(session, "accept_quest")
    assert session.active_quest is not None
    assert session.active_quest.key == "bring_gold"
    assert session.active_quest.gold_required == 100


def test_active_quest_can_persist_tag_treasure_map_procedure_state() -> None:
    quest = ActiveQuestState(
        tile_id="t",
        key="tag_treasure_map",
        description="Follow the purchased TAG treasure map to the underground caves.",
    )
    quest.tag_treasure_map_destination = 1
    quest.tag_procedure_signoff = True
    quest.tag_generated_lead_signoff = True
    quest.tag_generated_lead_state["entry_seen"] = True
    quest.tag_generated_lead_state["route_recorded"] = True
    quest.tag_generated_lead_state["closeout_warnings"] = ["1 pending TAG XP marker still needs review."]
    quest.tag_generated_lead_state["closeout"] = {
        "completed": True,
        "result": "Reviewed",
        "warnings": ["1 pending TAG XP marker still needs review."],
    }
    quest.tag_procedure_state["map_cave_room_count"] = {
        "completed": True,
        "total": 6,
        "result": "Map cave complex room count: dungeon ends after 6 rooms.",
    }
    quest.tag_procedure_state["next_action"] = "Explore until the room target is reached."

    restored = ActiveQuestState.model_validate(quest.model_dump())
    assert restored.tag_treasure_map_destination == 1
    assert restored.tag_procedure_signoff is True
    assert restored.tag_generated_lead_signoff is True
    assert restored.tag_generated_lead_state["entry_seen"] is True
    assert restored.tag_generated_lead_state["route_recorded"] is True
    assert restored.tag_generated_lead_state["closeout"]["completed"] is True
    assert "pending TAG XP" in restored.tag_generated_lead_state["closeout"]["warnings"][0]
    assert restored.tag_procedure_state["map_cave_room_count"]["completed"] is True
    assert restored.tag_procedure_state["map_cave_room_count"]["total"] == 6
    assert "room target" in restored.tag_procedure_state["next_action"]


def test_kerrak_dar_reward_spends_one_clue_for_hoard(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    hero = session.party[0]
    hero.gold = 0
    hero.clues = 1
    session.clues_found = 1
    session.active_quest = ActiveQuestState(tile_id="t", key="peaceful_way", description="Peace", completed=True)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)

    eng.advance(session, "claim_quest_reward", show_rolls=False)
    assert "Kerrak Dar Hoard" in hero.statuses

    eng.advance(session, "claim_kerrak_dar_hoard")
    assert hero.clues == 0
    assert session.clues_found == 0
    assert hero.gold == 200
    assert session.map_state.tiles[0].treasure_gold == 300
    assert "Kerrak Dar Hoard" not in hero.statuses
    assert any("Kerrak Dar's hoard found" in entry for entry in session.log)


def test_enchanted_weapon_reward_marks_adventure_status(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(tile_id="t", key="peaceful_way", description="Peace", completed=True)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 3)

    eng.advance(session, "claim_quest_reward", show_rolls=False)
    assert session.active_quest is None
    assert "Enchanted weapon" in session.party[0].statuses
    assert any("weapon is enchanted until adventure end" in entry for entry in session.log)


def test_arrow_of_slaying_deals_three_damage_to_major_foe() -> None:
    eng = engine()
    boss = EnemyState(id="b", name="Ogre", category="boss", level=5, life=4, max_life=6)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
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
                inventory=["Bow", "Arrow of Slaying (target: Ogre)"],
                default_missile_weapon="Bow",
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R", enemies=[boss])],
            current_tile_id="t",
        ),
    )

    eng.advance(session, "use_arrow_of_slaying", character_id="h", attack_targets={"h": "b"}, show_rolls=False)

    assert boss.life == 1
    assert boss.level == 4
    assert session.party[0].inventory == ["Bow"]
    assert any("3 automatic damage" in entry for entry in session.log)


def test_arrow_of_slaying_requires_major_foe() -> None:
    eng = engine()
    goblin = EnemyState(id="g", name="Goblin", category="minions", level=3, life=1, max_life=1)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
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
                inventory=["Bow", "Arrow of Slaying (target: Ogre)"],
                default_missile_weapon="Bow",
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R", enemies=[goblin])],
            current_tile_id="t",
        ),
    )

    eng.advance(session, "use_arrow_of_slaying", character_id="h", attack_targets={"h": "g"}, show_rolls=False)

    assert goblin.life == 1
    assert "Arrow of Slaying (target: Ogre)" in session.party[0].inventory
    assert any("must target a living Major Foe" in entry for entry in session.log)


def test_arrow_of_slaying_requires_bow_and_designed_target() -> None:
    eng = engine()
    boss = EnemyState(id="b", name="Ogre", category="boss", level=5, life=4, max_life=6)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
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
                inventory=["Arrow of Slaying (target: Ogre)"],
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R", enemies=[boss])],
            current_tile_id="t",
        ),
    )

    eng.advance(session, "use_arrow_of_slaying", character_id="h", attack_targets={"h": "b"}, show_rolls=False)
    assert boss.life == 4
    assert any("only by a PC with a bow" in entry for entry in session.log)


def test_arrow_of_slaying_rejects_wrong_designed_target() -> None:
    eng = engine()
    boss = EnemyState(id="b", name="Troll", category="boss", level=5, life=4, max_life=6)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
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
                inventory=["Bow", "Arrow of Slaying (target: Ogre)"],
                default_missile_weapon="Bow",
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R", enemies=[boss])],
            current_tile_id="t",
        ),
    )

    eng.advance(session, "use_arrow_of_slaying", character_id="h", attack_targets={"h": "b"}, show_rolls=False)
    assert boss.life == 4
    assert "Arrow of Slaying (target: Ogre)" in session.party[0].inventory
    assert any("was made for Ogre" in entry for entry in session.log)


def test_arrow_of_slaying_reward_rolls_target(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(tile_id="t", key="peaceful_way", description="Peace", completed=True)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 5)
    monkeypatch.setattr(eng, "_roll_epic_major_foe_target_name", lambda _session: "Manticore")

    eng.advance(session, "claim_quest_reward", show_rolls=False)

    assert "Arrow of Slaying (target: Manticore)" in session.party[0].inventory
    assert any("Arrow of Slaying target rolled: Manticore" in entry for entry in session.log)


def test_major_foe_table_keys_include_all_environments_and_fiendish() -> None:
    monsters = engine().rules.monsters()
    keys = major_foe_table_keys(monsters)
    assert set(keys) == {
        "weird",
        "boss",
        "caverns_weird",
        "caverns_boss",
        "fungal_grottoes_weird",
        "fungal_grottoes_boss",
        "fiendish_foes_weird",
        "fiendish_foes_boss",
        "tag_weird",
        "tag_boss",
        "fd_weird",
        "fd_boss",
        "fd_horde",
    }


def test_arrow_of_slaying_picks_table_then_foe_pdf_p163() -> None:
    eng = engine()
    session = base_session()
    fiendish_boss = next(
        row for row in eng.rules.monsters()["fiendish_foes_boss"] if row["name"] == "Young Red Dragon"
    )
    with patch("app.engine.random_dungeon.random.choice", side_effect=["fiendish_foes_boss", fiendish_boss]):
        target = eng._roll_epic_major_foe_target_name(session)
    assert target == "Young Red Dragon"
    assert any("Major Foe table" in line and "fiendish_foes_boss" in line for line in session.log)


def test_use_potion_heals_to_full() -> None:
    eng = engine()
    session = base_session()
    session.party[0].current_life = 1
    eng.advance(session, "use_potion", character_id="h")
    assert session.party[0].current_life == 3
    assert "h" in session.potion_used_character_ids
    assert "Potion of Healing" not in session.party[0].inventory


def test_use_potion_only_consumes_one_of_many() -> None:
    eng = engine()
    session = base_session()
    session.party[0].current_life = 1
    session.party[0].inventory = ["Potion of Healing", "Potion of Healing", "Potion of Healing"]
    eng.advance(session, "use_potion", character_id="h", item_name="Potion of Healing")
    assert session.party[0].current_life == 3
    assert session.party[0].inventory.count("Potion of Healing") == 2
    assert "h" in session.potion_used_character_ids


def test_use_potion_of_sleep_in_combat(monkeypatch) -> None:
    eng = engine()
    foe = EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)
    session = base_session(
        mode="combat",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
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
                inventory=["Potion of Sleep"],
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
                    title="R",
                    description="R",
                    enemies=[foe],
                )
            ],
            current_tile_id="t",
        ),
    )
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    monkeypatch.setattr("app.engine.spells.roll_d6", lambda: 6)
    eng.advance(session, "use_potion", character_id="h", item_name="Potion of Sleep")
    assert session.mode == "exploration"
    assert "Potion of Sleep" not in session.party[0].inventory
    assert any("quaffs" in entry for entry in session.log)


def test_barbarian_cannot_drink_potion() -> None:
    eng = engine()
    session = base_session()
    session.party[0].class_id = "barbarian"
    session.party[0].class_name = "Barbarian"
    session.party[0].current_life = 1
    eng.advance(session, "use_potion", character_id="h")
    assert session.party[0].current_life == 1
    assert "Potion of Healing" in session.party[0].inventory
    assert "h" not in session.potion_used_character_ids
    assert any("cannot use potions" in entry for entry in session.log)


def test_stale_combat_clears_when_no_foes() -> None:
    eng = engine()
    session = base_session(mode="combat", reaction_pending=True)
    eng.advance(session, "rest")
    assert session.mode == "exploration"
    assert any("No active foes remain" in entry for entry in session.log)


def test_final_boss_grants_extra_xp(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    boss = EnemyState(
        id="b",
        name="Dragon",
        category="boss",
        level=6,
        life=0,
        max_life=8,
        tags=["final_boss"],
    )
    eng._award_encounter_xp(session, [boss], show_rolls=False)
    assert session.xp_rolls_pending == 2
    assert session.final_boss_defeated is True


def test_mark_final_boss_on_high_roll(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(id="b", name="Ogre", category="boss", level=5, life=5, max_life=5),
    ]
    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 6)
    eng._begin_combat(session, "Fight!", show_rolls=False)
    assert any("Final Boss check" in line for line in session.log)
    assert any("final_boss" in enemy.tags for enemy in tile.enemies)
    assert tile.final_boss_treasure is True
    assert session.final_boss_designated is True


def test_final_boss_no_treasure_foe_gets_minimum_bounty() -> None:
    eng = engine()
    session = base_session(mode="exploration")
    tile = session.map_state.tiles[0]
    tile.resolved = True
    tile.final_boss_treasure = True
    tile.defeated_enemies = [
        EnemyState(
            id="s1",
            name="Green Slime",
            category="weird",
            level=7,
            life=0,
            max_life=8,
            tags=["final_boss", "weird"],
        ),
    ]
    eng._award_treasure(session, tile, show_rolls=True)
    assert tile.treasure_gold == 100
    assert tile.treasure_claimed is False
    assert any("Final Boss bounty" in line for line in session.log)


def test_wandering_major_cannot_become_final_boss(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 6)
    monkeypatch.setattr(
        eng,
        "_roll_wandering_enemies",
        lambda _session, _category, _hcl: [
            EnemyState(id="b", name="Ogre", category="boss", level=5, life=5, max_life=5),
        ],
    )
    eng._spawn_wandering_monsters(session, tile, show_rolls=True)
    assert session.major_foes_encountered == 1
    assert not any("final_boss" in enemy.tags for enemy in tile.enemies)
    assert not tile.final_boss_treasure
    assert not session.final_boss_designated
    assert not any("Final Boss check" in line for line in session.log)
    assert tile.enemies[0].life == 5
    assert tile.enemies[0].attacks == 1


def test_second_major_foe_skips_final_boss_check(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(id="b1", name="Dragon", category="boss", level=5, life=5, max_life=5),
    ]
    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 6)
    eng._begin_combat(session, "First major!", show_rolls=False)
    assert session.final_boss_designated is True

    tile.enemies = [
        EnemyState(id="b2", name="Iron Eater", category="weird", level=4, life=4, max_life=4),
    ]
    log_before = len(session.log)
    eng._begin_combat(session, "Second major!", show_rolls=True)
    new_log = session.log[log_before:]
    assert not any("Final Boss check" in line for line in new_log)
    assert not any("final_boss" in enemy.tags for enemy in tile.enemies)
    assert tile.enemies[0].name == "Iron Eater"


def test_peaceful_quest_progress() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="peaceful_way",
        description="Peace",
        peaceful_required=3,
    )
    eng._record_peaceful_quest_progress(session)
    assert session.active_quest.peaceful_count == 1


def test_peaceful_quest_completion_logs_summary_milestone() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="peaceful_way",
        description="Peace",
        peaceful_required=1,
    )
    eng._record_peaceful_quest_progress(session)
    assert session.active_quest.completed is True
    assert any("Quest objective complete: peaceful encounters finished" in entry for entry in session.log)


def test_bring_alive_quest_completes_on_subdued_boss() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="bring_alive",
        description="Capture",
        boss_capture_pending=True,
    )
    boss = EnemyState(
        id="b",
        name="Ogre",
        category="boss",
        level=5,
        life=0,
        max_life=6,
        subdued=True,
    )
    eng._update_quest_on_combat_end(session, [boss], show_rolls=False)
    assert session.active_quest.completed is True
    assert session.active_quest.captured_boss_name == "Ogre"
    assert session.active_quest.boss_capture_pending is False
    assert any("Quest objective complete: return to the Quest-giver with the living captive." in entry for entry in session.log)


def test_bring_item_quest_logs_completion_once(monkeypatch) -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="bring_item",
        description="Find item",
        item_name="Moon Key",
    )
    rolls = iter([1])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls))
    defeated = [
        EnemyState(id="w1", name="Manticore", category="weird", level=4, life=0, max_life=4),
        EnemyState(id="w2", name="Troll", category="weird", level=4, life=0, max_life=4),
    ]
    eng._update_quest_on_combat_end(session, defeated, show_rolls=True)
    assert session.active_quest.item_collected is True
    assert sum(1 for entry in session.log if "Quest objective complete: return to the Quest-giver with the item." in entry) == 1


def test_bring_alive_quest_logs_when_boss_is_slain_instead() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="bring_alive",
        description="Capture",
        boss_capture_pending=True,
    )
    boss = EnemyState(
        id="b",
        name="Ogre",
        category="boss",
        level=5,
        life=0,
        max_life=6,
        subdued=False,
    )
    eng._update_quest_on_combat_end(session, [boss], show_rolls=False)
    assert session.active_quest.completed is False
    assert session.active_quest.boss_capture_pending is True
    assert any("was slain, not subdued" in entry for entry in session.log)


def test_bring_head_not_complete_when_boss_subdued() -> None:
    eng = engine()
    session = base_session()
    session.active_quest = ActiveQuestState(
        tile_id="t",
        key="bring_head",
        description="Slay",
        boss_slay_pending=True,
    )
    boss = EnemyState(
        id="b",
        name="Ogre",
        category="boss",
        level=5,
        life=0,
        max_life=6,
        subdued=True,
    )
    eng._update_quest_on_combat_end(session, [boss], show_rolls=False)
    assert session.active_quest.completed is False
    assert session.active_quest.boss_slay_pending is True
    assert any("was subdued, not slain" in entry for entry in session.log)


def test_bring_head_requires_selected_boss_head_and_return_to_giver(monkeypatch) -> None:
    eng = engine()
    giver = TileState(
        id="giver",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Quest Giver",
        description="Quest Giver",
    )
    away = TileState(
        id="away",
        x=1,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Away",
        description="Away",
    )
    session = base_session(
        map_state=MapState(tiles=[giver, away], current_tile_id="away"),
        active_quest=ActiveQuestState(
            tile_id="giver",
            key="bring_head",
            description="Bring me its head!",
            boss_slay_pending=True,
            boss_target_name="Ogre",
        ),
    )

    wrong_boss = EnemyState(id="b1", name="Troll", category="boss", level=5, life=0, max_life=6)
    eng._update_quest_on_combat_end(session, [wrong_boss], show_rolls=False)
    assert session.active_quest.boss_slay_pending is True
    assert session.active_quest.boss_head_acquired is False

    target_boss = EnemyState(id="b2", name="Ogre", category="boss", level=5, life=0, max_life=6)
    eng._update_quest_on_combat_end(session, [target_boss], show_rolls=False)
    assert session.active_quest.boss_slay_pending is False
    assert session.active_quest.boss_head_acquired is True
    assert session.active_quest.completed is False

    eng._claim_quest_reward(session, show_rolls=False)
    assert session.active_quest is not None
    assert any("Return to the Quest-giver's tile with the Boss head." in entry for entry in session.log)

    session.map_state.current_tile_id = "giver"
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    eng._claim_quest_reward(session, show_rolls=False)
    assert session.active_quest is None
    assert any("Quest complete! Epic reward" in entry for entry in session.log)


def test_bring_alive_reward_requires_return_to_giver() -> None:
    eng = engine()
    giver = TileState(
        id="giver",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Quest Giver",
        description="Quest Giver",
    )
    away = TileState(
        id="away",
        x=1,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Away",
        description="Away",
    )
    session = base_session(
        map_state=MapState(tiles=[giver, away], current_tile_id="away"),
        active_quest=ActiveQuestState(
            tile_id="giver",
            key="bring_alive",
            description="I want it alive!",
            boss_capture_pending=False,
            captured_boss_name="Ogre",
            completed=True,
        ),
    )
    eng._claim_quest_reward(session, show_rolls=False)
    assert session.active_quest is not None
    assert any("Return to the Quest-giver's tile with the living captive." in entry for entry in session.log)
