from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.engine.combat import CombatContext, resolve_combat_round
from app.engine.monster_combat_hooks import (
    apply_free_slaves_choice,
    apply_mantlebeast_ambush_drop,
    apply_mantlebeast_spot_on_entry,
    apply_per_turn_monster_effects,
    member_cannot_attack,
    on_enemy_killed_by_pc,
    treasure_roll_count_from_defeated,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, PartyMemberState, SessionState, TileState

ROOT = Path(__file__).resolve().parents[1]


def _hero(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        max_life=6,
        current_life=6,
        marching_order=1,
        inventory=[],
        statuses=[],
        spells=[],
        learned_expert_skills=[],
        gold=0,
        clues=0,
        xp=0,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _session(party: list[PartyMemberState]) -> SessionState:
    return SessionState(
        id="s1",
        party_id="p1",
        adventure_id="random",
        adventure_type="random",
        party=party,
        map_state={"current_tile_id": "t1", "tiles": []},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_treasure_roll_count_groups_by_foe_name() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    defeated = [
        EnemyState(id="1", name="Gnolls", category="minions", level=5, life=0, max_life=1),
        EnemyState(id="2", name="Gnolls", category="minions", level=5, life=0, max_life=1),
        EnemyState(id="3", name="Gnolls", category="minions", level=5, life=0, max_life=1),
    ]
    log: list[str] = []
    count = treasure_roll_count_from_defeated(
        defeated,
        lookup_template=engine._monster_template_for_enemy,
        log=log,
    )
    assert count == 1


def test_treasure_roll_count_sums_major_template_rolls() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    defeated = [
        EnemyState(id="1", name="Fiendish Chaos Lord", category="boss", level=8, life=0, max_life=7),
    ]
    count = treasure_roll_count_from_defeated(
        defeated,
        lookup_template=engine._monster_template_for_enemy,
        log=[],
    )
    assert count == 3


def test_treasure_roll_count_zero_when_template_missing_treasure_rolls() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    defeated = [
        EnemyState(id="1", name="Giant Toads", category="vermin", level=5, life=0, max_life=1),
    ]
    count = treasure_roll_count_from_defeated(
        defeated,
        lookup_template=engine._monster_template_for_enemy,
        log=[],
    )
    assert count == 0


def test_treasure_roll_count_uses_alias_for_legacy_dragon_stub() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    defeated = [
        EnemyState(id="1", name="Dragon", category="boss", level=10, life=0, max_life=8),
    ]
    count = treasure_roll_count_from_defeated(
        defeated,
        lookup_template=engine._monster_template_for_enemy,
        log=[],
    )
    assert count == 3


def test_monster_template_prefers_richest_row_across_tables() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    enemy = EnemyState(id="1", name="Wraith", category="weird", level=9, life=0, max_life=3)
    template = engine._monster_template_for_enemy(enemy)
    assert template is not None
    assert template.get("treasure_rolls") == 2


def test_treasure_roll_count_defaults_for_unknown_major_without_template() -> None:
    defeated = [
        EnemyState(id="1", name="Mystery Boss", category="boss", level=8, life=0, max_life=6),
    ]
    count = treasure_roll_count_from_defeated(
        defeated,
        lookup_template=lambda _enemy: None,
        log=[],
    )
    assert count == 2


def test_mantlebeast_spot_on_entry_allows_turn_back() -> None:
    hero = _hero(class_id="rogue")
    session = _session([hero])
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="1",
        tile_type="room",
        title="Room",
        description="",
        enemies=[
            EnemyState(id="m1", name="Lurking Mantlebeast", category="weird", level=8, life=5, max_life=5)
        ],
    )
    with patch("app.engine.monster_combat_hooks.chance_roll_succeeds", return_value=(True, 1, 4, 6)):
        spotted = apply_mantlebeast_spot_on_entry(session, tile, [hero], show_rolls=False)
    assert spotted
    assert tile.mantlebeast_spotted
    assert any("Turn Back" in line or "turn back" in line.lower() for line in session.log)


def test_turn_back_from_mantlebeast_retreats_to_previous_tile() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    hero = _hero()
    session = _session([hero])
    previous = TileState(
        id="prev",
        x=0,
        y=0,
        tile_key="1",
        tile_type="room",
        title="Previous Room",
        description="",
        exits=[
            {
                "id": "exit-prev",
                "direction": "east",
                "kind": "passage",
                "destination_tile_id": "beast",
                "status": "open",
            }
        ],
    )
    beast_room = TileState(
        id="beast",
        x=1,
        y=0,
        tile_key="2",
        tile_type="room",
        title="Beast Room",
        description="",
        mantlebeast_spotted=True,
        enemies=[
            EnemyState(id="m1", name="Lurking Mantlebeast", category="weird", level=8, life=5, max_life=5)
        ],
        exits=[
            {
                "id": "exit-beast",
                "direction": "west",
                "kind": "passage",
                "destination_tile_id": "prev",
                "status": "open",
            }
        ],
    )
    session.map_state.tiles = [previous, beast_room]
    session.map_state.current_tile_id = "beast"
    session.current_tile_entry_exit_id = "exit-beast"
    engine._turn_back_from_mantlebeast(session, show_rolls=False)
    assert session.map_state.current_tile_id == "prev"
    assert any("Turn Back:" in line for line in session.log)


def test_mantlebeast_ambush_drop_pins_failed_saves() -> None:
    hero = _hero()
    session = _session([hero])
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="1",
        tile_type="room",
        title="Room",
        description="",
        enemies=[
            EnemyState(id="m1", name="Lurking Mantlebeast", category="weird", level=8, life=5, max_life=5)
        ],
    )
    with patch("app.engine.monster_combat_hooks.roll_exploding_for_level", return_value=(1, [1])):
        log = apply_mantlebeast_ambush_drop(session, tile, [hero], show_rolls=False)
    assert tile.mantlebeast_ambush_resolved
    assert member_cannot_attack(hero)
    assert any("pinned" in line.lower() for line in log)


def test_confusion_save_blocks_attack() -> None:
    hero = _hero(character_id="hero-2", name="Ally")
    mimic = _hero()
    doppel = EnemyState(
        id="d1",
        name="Doppelganger",
        category="weird",
        level=7,
        life=5,
        max_life=5,
        tags=[f"Doppelganger mimics: {mimic.character_id}"],
        per_turn_effects=[{"type": "confusion_save", "save_level": 4, "save_type": "confusion"}],
    )
    context = CombatContext(session=_session([mimic, hero]))
    with patch("app.engine.monster_combat_hooks.monster_effect_save", return_value=(False, [])):
        log = apply_per_turn_monster_effects([doppel], [mimic, hero], context=context, show_rolls=False)
    assert member_cannot_attack(hero)
    assert not member_cannot_attack(mimic)
    assert any("confused" in line.lower() for line in log)


def test_possessed_dwarf_revives_on_d6_3_plus() -> None:
    dwarf = EnemyState(id="p1", name="Possessed Dwarves", category="minions", level=8, life=0, max_life=1)
    hero = _hero()
    template = {"special_rules": [{"type": "hard_to_kill", "revival_threshold": 3}]}
    context = CombatContext(session=_session([hero]))
    with patch("app.engine.monster_combat_hooks.roll_d6", return_value=4):
        log = on_enemy_killed_by_pc(dwarf, hero, context=context, show_rolls=False, template=template)
    assert dwarf.life == 1
    assert any("rises again" in line.lower() for line in log)


def test_free_slaves_grants_clue_and_clears_pending() -> None:
    engine = RandomDungeonEngine(
        rules=RulesRepository(ROOT / "data" / "rules", ROOT / "data" / "rules" / "_override"),
        asset_dir=Path(),
    )
    hero = _hero(clues=0)
    session = _session([hero])
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="1",
        tile_type="room",
        title="Room",
        description="",
    )
    session.map_state.tiles = [tile]
    session.pending_free_slaves_tile_id = tile.id
    with patch.object(engine, "_spawn_wandering_monsters") as wandering:
        apply_free_slaves_choice(engine, session, accept=True, show_rolls=False)
    wandering.assert_called_once()
    assert session.pending_free_slaves_tile_id is None
    assert hero.clues == 1


def test_skeletal_demon_spawns_skeletons_after_pc_damage() -> None:
    hero = _hero()
    demon = EnemyState(
        id="sd1",
        name="Skeletal Demon",
        category="boss",
        level=9,
        life=8,
        max_life=8,
        per_turn_effects=[{"type": "summon_reinforcements", "trigger": "pc_takes_damage"}],
    )
    goblin = EnemyState(id="g1", name="Gnolls", category="minions", level=5, life=1, max_life=1)
    context = CombatContext(session=_session([hero]))
    with patch("app.engine.combat.assign_enemy_attacks", return_value=[(goblin, hero)]):
        with patch("app.engine.combat.roll_exploding_for_level", return_value=(1, [1])):
            with patch("app.engine.combat.defense_succeeds", return_value=False):
                resolve_combat_round(
                    [hero],
                    [demon, goblin],
                    show_rolls=False,
                    context=context,
                    encounter_round=0,
                    party_attacked_immediately=True,
                )
    assert context.pending_skeleton_spawns >= 1
