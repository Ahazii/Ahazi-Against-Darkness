from __future__ import annotations

from pathlib import Path

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
    eng.advance(session, "accept_quest")
    assert session.active_quest is not None
    assert session.active_quest.key == "bring_gold"
    assert session.active_quest.gold_required == 100


def test_use_potion_heals_to_full() -> None:
    eng = engine()
    session = base_session()
    session.party[0].current_life = 1
    eng.advance(session, "use_potion", character_id="h")
    assert session.party[0].current_life == 3
    assert "h" in session.potion_used_character_ids
    assert "Potion of Healing" not in session.party[0].inventory


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
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_d6", lambda: (6, [6]))
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
    assert any("final_boss" in enemy.tags for enemy in tile.enemies)
    assert tile.final_boss_treasure is True
    assert session.final_boss_designated is True


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
