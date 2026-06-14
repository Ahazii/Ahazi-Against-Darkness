from __future__ import annotations

from pathlib import Path

from app.engine.combat_summary import summarize_combat_log
from app.engine.consumables import throw_acid_vial, use_mushroom
from app.engine.druid_companion import maybe_summon_on_wilderness_entry, summon_companion
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _party_member(**overrides) -> PartyMemberState:
    base = {
        "character_id": "h1",
        "name": "Hero",
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 2,
        "xp": 0,
        "gold": 0,
        "max_life": 5,
        "current_life": 5,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
        "inventory": [],
        "spells": [],
        "statuses": [],
    }
    base.update(overrides)
    return PartyMemberState.model_validate(base)


def test_summarize_combat_log() -> None:
    summary = summarize_combat_log(
        [
            "Goblin (3) hits Sly Silas for 2 damage.",
            "Sir Benedict hits Goblin (1) for 5 damage.",
            "Goblin (1) is defeated.",
            "Sir Benedict hits Goblin (2) for 2 damage.",
        ],
        party_names=["Sir Benedict", "Sly Silas"],
        enemy_names=["Goblin"],
    )
    assert "Sir Benedict killed Goblin (1) with a hit for 5 damage" in summary
    assert "hit Goblin (2) for 2 damage" in summary
    assert "Sly Silas took 2 damage from Goblin (3)" in summary
    assert "party −" not in summary


def test_summarize_combat_log_counts_takes_damage_wording() -> None:
    summary = summarize_combat_log(
        ["Troll claws Ahazi; Ahazi takes 2 damage from Troll."],
        party_names=["Ahazi"],
        enemy_names=["Troll"],
    )

    assert "Ahazi took 2 damage from Troll" in summary
    assert "No hits this round" not in summary


def test_summarize_combat_log_empty_round_is_unambiguous() -> None:
    assert summarize_combat_log(["Warrior misses.", "Troll misses."]) == (
        "No hits, wounds, or foe defeats this round."
    )


def test_healing_mushroom_restores_life() -> None:
    hero = _party_member(current_life=3, inventory=["Healing mushroom"])
    log, ok = use_mushroom(hero, "Healing mushroom", show_rolls=False)
    assert ok
    assert hero.current_life == 4
    assert any("heals 1 life" in line.lower() for line in log)


def test_acid_vial_damages_foe(monkeypatch) -> None:
    hero = _party_member(level=3, inventory=["Acid vial"])
    troll = EnemyState(
        id="troll",
        name="Troll",
        category="boss",
        level=6,
        life=5,
        max_life=7,
        tags=["boss", "regeneration"],
    )
    monkeypatch.setattr("app.engine.consumables.roll_exploding_for_level", lambda level: (6, [6]))
    log, hit = throw_acid_vial(hero, troll, show_rolls=False)
    assert hit
    assert troll.regen_suppressed
    assert troll.life < 5
    assert any("acid" in line.lower() for line in log)


def test_druid_companion_summons_on_wilderness_with_food() -> None:
    druid = _party_member(
        character_id="d1",
        name="Druid",
        class_id="druid",
        class_name="Druid",
        inventory=["Food ration"],
        companion_kind="bear",
    )
    tile = TileState(
        id="out",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Forest",
        description="Trees",
        terrain="forest",
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[druid],
        map_state=MapState(tiles=[tile], current_tile_id="out"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    log = summon_companion(session, druid, tile=tile)
    assert session.druid_companion_life == 6
    assert session.druid_companion_kind == "bear"
    assert any("Bear joins" in line for line in log)
    assert not any("food ration" in item.lower() for item in druid.inventory)


def test_halfling_luck_search_reroll() -> None:
    eng = engine()
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        searched=True,
    )
    halfling = _party_member(
        character_id="h1",
        name="Hal",
        class_id="halfling",
        class_name="Halfling",
        level=2,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[halfling],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        pending_search_reroll_tile_id="t",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng._use_class_ability(
        session,
        "h1",
        "halfling_luck_search",
        show_rolls=False,
    )
    assert tile.searched is True
    assert session.pending_search_reroll_tile_id == "t"
    assert any("reroll the search" in line.lower() for line in session.log)
