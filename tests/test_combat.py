from __future__ import annotations

from pathlib import Path

from app.engine import combat
from app.engine.class_combat import armor_defense_bonus
from app.engine.combat import CombatContext, CombatRound, assign_enemy_attacks, can_melee_attack, resolve_combat_round, resolve_flee
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def member(*, class_id: str = "wizard", attack_bonus: int = 0) -> PartyMemberState:
    return PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id=class_id,
        class_name=class_id.title(),
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=attack_bonus,
        defense_bonus=0,
        save_bonus=0,
    )


def enemy() -> EnemyState:
    return EnemyState(
        id="rat",
        name="Rat",
        category="vermin",
        level=3,
        life=1,
        max_life=1,
        attacks=1,
    )


def test_combat_round_can_trace_rolls_and_math(monkeypatch) -> None:
    outcomes = iter([(2, [2]), (1, [1])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: next(outcomes))

    result = resolve_combat_round([member()], [enemy()], show_rolls=True, explain_math=True)

    assert any("Attack roll: Hero vs Rat:" in entry for entry in result.log)
    assert any("unarmed -2" in entry for entry in result.log)
    assert any("Attack math: need total >= enemy level 3 to hit." in entry for entry in result.log)
    assert any("Defense roll: Hero vs Rat: 1 + 0 = 1." in entry for entry in result.log)
    assert any("Defense math: need total > enemy level 3 to avoid damage." in entry for entry in result.log)
    assert result.party[0].current_life == 2


def test_enchanted_weapon_rolls_two_attack_dice_keep_best(monkeypatch) -> None:
    hero = member(class_id="warrior")
    hero.inventory = ["Sword"]
    hero.statuses = ["Enchanted weapon"]
    target = enemy()
    target.level = 4
    rolls = iter([(1, [1]), (4, [4])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: next(rolls))

    result = resolve_combat_round([hero], [target], show_rolls=True, encounter_round=1)

    assert any("Enchanted weapon rolls two attack dice; keeps 4 over 1" in entry for entry in result.log)
    assert any("Attack roll: Hero vs Rat: 4" in entry for entry in result.log)


def test_shield_of_warning_counts_when_normal_shields_are_blocked() -> None:
    hero = member(class_id="warrior")
    hero.inventory = ["Shield of Warning"]

    assert armor_defense_bonus(hero, include_shield=False) == 0
    assert armor_defense_bonus(hero, include_shield=False, warning_shield_override=True) == 1


def test_cleric_undead_full_level_attack_is_logged(monkeypatch) -> None:
    hero = member(class_id="cleric")
    hero.level = 4
    skeleton = EnemyState(
        id="skel",
        name="Skeleton",
        category="minions",
        level=4,
        life=1,
        max_life=1,
        attacks=1,
        tags=["undead"],
    )
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (2, [2]))

    result = resolve_combat_round([hero], [skeleton], show_rolls=False, encounter_round=1)

    assert result.enemies[0].life <= 0
    assert any("Effect: Hero uses full Level Attack vs undead Skeleton." in line for line in result.log)


def test_crushing_weapon_bonus_vs_undead_is_logged(monkeypatch) -> None:
    hero = member(class_id="warrior")
    hero.inventory = ["Mace", "Lantern"]
    skeleton = EnemyState(
        id="skel",
        name="Skeleton",
        category="minions",
        level=3,
        life=1,
        max_life=1,
        attacks=1,
        tags=["undead"],
    )
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    result = resolve_combat_round([hero], [skeleton], show_rolls=False, encounter_round=1)

    assert result.enemies[0].life <= 0
    assert any("Effect: Mace gains +1 Attack vs skeleton/undead Skeleton." in line for line in result.log)


def test_blessed_temple_bonus_applies_and_ends_after_undead_slain(monkeypatch) -> None:
    hero = member(class_id="warrior")
    hero.inventory = ["Mace", "Lantern"]
    skeleton = EnemyState(
        id="skel",
        name="Skeleton",
        category="minions",
        level=4,
        life=1,
        max_life=1,
        attacks=1,
        tags=["undead"],
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
        blessed_undead_bonus_character_id="hero",
    )
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    result = resolve_combat_round(
        [hero],
        [skeleton],
        show_rolls=False,
        encounter_round=1,
        context=CombatContext(session=session),
    )

    assert result.enemies[0].life <= 0
    assert session.blessed_undead_bonus_character_id is None
    assert any("Effect: Blessed Temple bonus gives Hero +1 Attack vs Skeleton." in line for line in result.log)
    assert any("Effect: Blessed Temple bonus ends after an undead or demon foe is slain." in line for line in result.log)


def test_terrifying_secret_forces_next_eligible_morale_failure(monkeypatch) -> None:
    hero = member(attack_bonus=-10)
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
        terrifying_secret_pending_character_id="hero",
    )
    foes = [
        EnemyState(id=f"g{i}", name="Goblin", category="minions", level=9, life=1, max_life=1)
        for i in range(4)
    ]
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    result = resolve_combat_round(
        [hero],
        foes,
        show_rolls=True,
        initial_minor_count=8,
        context=CombatContext(session=session),
    )

    assert result.morale_failed is True
    assert session.terrifying_secret_pending_character_id is None
    assert all(foe.life == 0 for foe in foes)
    assert any("Terrifying Secret" in line for line in result.log)


def test_random_engine_marks_fallen_hero_on_current_tile(monkeypatch) -> None:
    hero = member()
    hero.current_life = 1
    foe = enemy()
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[foe],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    outcomes = iter([(2, [2]), (1, [1])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: next(outcomes))

    RandomDungeonEngine(rules=None, asset_dir=Path())._combat_round(session)

    tile = session.map_state.tiles[0]
    assert hero.character_id in tile.fallen_character_ids
    assert any("falls" in entry for entry in session.log)


def test_random_engine_records_defeated_enemies_on_current_tile(monkeypatch) -> None:
    hero = member(class_id="warrior")
    foe = enemy()
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[foe],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    RandomDungeonEngine(rules=None, asset_dir=Path())._combat_round(session)

    tile = session.map_state.tiles[0]
    assert [enemy.id for enemy in tile.defeated_enemies] == ["rat"]
    assert tile.enemies == []
    assert session.mode == "exploration"


def test_combat_round_respects_attack_targets(monkeypatch) -> None:
    rat = enemy()
    goblin = EnemyState(
        id="goblin",
        name="Goblin",
        category="minions",
        level=4,
        life=2,
        max_life=2,
        attacks=1,
    )
    hero = member(class_id="warrior")
    hero.inventory = ["Short Sword"]
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    result = resolve_combat_round(
        [hero],
        [rat, goblin],
        show_rolls=False,
        attack_targets={"hero": "goblin"},
        encounter_round=1,
    )

    assert rat.life == 1
    assert goblin.life == 1
    assert not result.combat_over


def test_random_engine_combat_round_accepts_attack_targets(monkeypatch) -> None:
    rat = enemy()
    goblin = EnemyState(
        id="goblin",
        name="Goblin",
        category="minions",
        level=4,
        life=2,
        max_life=2,
        attacks=1,
    )
    hero = member(class_id="warrior")
    hero.inventory = ["Short Sword"]
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        combat_round=1,
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[rat, goblin],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    RandomDungeonEngine(rules=None, asset_dir=Path())._combat_round(
        session,
        attack_targets={"hero": "goblin"},
    )

    assert rat.life == 1
    assert goblin.life == 1


def test_combat_empty_treasure_roll_does_not_offer_claim(monkeypatch) -> None:
    hero = member(class_id="warrior")
    foe = enemy()
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[foe],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 1)

    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    engine._combat_round(session, show_rolls=True)

    assert "Treasure is available to claim." not in session.log
    assert "No treasure found." in session.log
    tile = session.map_state.tiles[0]
    assert tile.treasure_gold == 0
    assert tile.treasure_items == []

    engine._claim_treasure(session)
    assert "There is no unclaimed treasure here." not in session.log
    assert "No treasure found." in session.log


def test_combat_treasure_roll_can_be_claimed(monkeypatch) -> None:
    hero = member(class_id="warrior")
    foe = enemy()
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=[foe],
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    rolls = iter([2, 4])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: next(rolls))

    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    engine._combat_round(session, show_rolls=True)

    assert "Treasure is available to claim." in session.log
    tile = session.map_state.tiles[0]
    assert tile.treasure_gold > 0
    expected_gold = hero.gold + tile.treasure_gold

    engine._claim_treasure(session)
    assert tile.treasure_claimed is True
    assert hero.gold == expected_gold
    assert tile.treasure_gold == 0
    assert any("Treasure claimed:" in entry for entry in session.log)


def test_claimed_tile_treasure_does_not_block_later_encounter_treasure(monkeypatch) -> None:
    hero = member(class_id="warrior")
    foe = EnemyState(id="wander", name="Troll", category="boss", level=5, life=0, max_life=7, attacks=1)
    tile = TileState(
        id="tile",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        content_key="minions",
        resolved=True,
        treasure_summary="Found 11gp.",
        treasure_claimed=True,
        enemies=[foe],
        defeated_enemies=[],
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="tile"),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    rolls = iter([2, 4])
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: next(rolls))

    engine = RandomDungeonEngine(rules=None, asset_dir=Path())
    engine._apply_combat_result(
        session,
        tile,
        CombatRound(party=session.party, enemies=[foe], log=["Troll is defeated."], combat_over=True),
        show_rolls=True,
        active_enemy_ids={"wander"},
    )

    assert "Treasure roll (dungeon): d6 = 2 - 1 + 0 = 1." in session.log
    assert "Treasure is available to claim." in session.log
    assert tile.treasure_claimed is False
    assert tile.treasure_gold > 0
    assert tile.treasure_summary != "Found 11gp."


def test_claim_treasure_logs_item_recipients_and_capped_gold() -> None:
    capped = member(class_id="halfling")
    capped.character_id = "capped"
    capped.name = "AhaziHalfling"
    capped.marching_order = 1
    capped.gold = 200
    carrier = member(class_id="warrior")
    carrier.character_id = "carrier"
    carrier.name = "Ahazidin"
    carrier.marching_order = 2
    carrier.gold = 0
    tile = TileState(
        id="treasure-room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Treasure Room",
        description="Room",
        treasure_gold=50,
        treasure_items=["Jewel"],
        treasure_summary="50gp, Jewel",
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[capped, carrier],
        map_state=MapState(tiles=[tile], current_tile_id="treasure-room"),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())

    engine._claim_treasure(session)

    assert capped.gold == 200
    assert carrier.gold == 50
    assert any("AhaziHalfling +0gp" in entry and "cap" in entry for entry in session.log)
    assert any("Items assigned: AhaziHalfling receives Jewel" in entry for entry in session.log)


def test_final_boss_treasure_remaining_is_not_tripled_again() -> None:
    party = []
    for index in range(4):
        hero = member(class_id="warrior")
        hero.character_id = f"hero-{index}"
        hero.name = f"Hero {index + 1}"
        hero.marching_order = index + 1
        hero.gold = 150
        party.append(hero)
    tile = TileState(
        id="boss-room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Boss Room",
        description="Boss Room",
        treasure_gold=330,
        treasure_summary="Final Boss treasure: 330gp",
        final_boss_treasure=True,
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=party,
        map_state=MapState(tiles=[tile], current_tile_id="boss-room"),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())

    engine._claim_treasure(session)
    assert sum(hero.gold for hero in party) == 800
    assert tile.treasure_gold == 130
    for hero in party:
        hero.gold = 0

    engine._claim_treasure(session)

    assert sum(hero.gold for hero in party) == 130
    assert tile.treasure_gold == 0
    assert tile.treasure_claimed is True


def test_final_boss_treasure_claim_caps_legacy_inflated_remaining() -> None:
    party = []
    for index in range(4):
        hero = member(class_id="warrior")
        hero.character_id = f"hero-{index}"
        hero.name = f"Hero {index + 1}"
        hero.marching_order = index + 1
        hero.gold = 0
        party.append(hero)
    tile = TileState(
        id="boss-room",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Boss Room",
        description="Boss Room",
        treasure_gold=1930,
        treasure_summary="Final Boss treasure: 330gp",
        final_boss_treasure=True,
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=party,
        map_state=MapState(tiles=[tile], current_tile_id="boss-room"),
        created_at="2026-05-18T00:00:00+00:00",
        updated_at="2026-05-18T00:00:00+00:00",
    )
    engine = RandomDungeonEngine(rules=None, asset_dir=Path())

    engine._claim_treasure(session)

    assert sum(hero.gold for hero in party) == 330
    assert tile.treasure_gold == 0
    assert tile.treasure_claimed is True
    assert any("corrected from 1930gp to 330gp" in entry for entry in session.log)


def test_corridor_limits_melee_to_front_rank() -> None:
    front = member(class_id="warrior")
    front.marching_order = 1
    front.character_id = "front"
    front.name = "Front"
    rear = member(class_id="warrior")
    rear.marching_order = 3
    rear.character_id = "rear"
    rear.name = "Rear"
    context = CombatContext(tile_type="corridor")
    assert can_melee_attack(front, context)
    assert not can_melee_attack(rear, context)


def test_corridor_normal_foe_targets_front_rank() -> None:
    front = member(class_id="warrior")
    front.marching_order = 1
    front.name = "Front"
    rear = member(class_id="warrior")
    rear.marching_order = 4
    rear.name = "Rear"
    foe = enemy()
    pairs = assign_enemy_attacks(
        [foe],
        [front, rear],
        context=CombatContext(tile_type="corridor", wandering_ambush=False),
    )
    assert pairs
    assert pairs[0][1].marching_order == 1


def test_foe_display_labels_number_duplicates() -> None:
    from app.engine.combat import foe_display_labels

    foes = [
        EnemyState(id="a", name="Orcs", category="minions", level=3, life=1, max_life=1),
        EnemyState(id="b", name="Orcs", category="minions", level=3, life=1, max_life=1),
    ]
    labels = foe_display_labels(foes)
    assert labels["a"] == "Orcs (1)"
    assert labels["b"] == "Orcs (2)"


def test_wandering_ambush_targets_rear_guard() -> None:
    front = member(class_id="warrior")
    front.marching_order = 1
    rear = member(class_id="warrior")
    rear.marching_order = 4
    rear.name = "Rear"
    foe = enemy()
    pairs = assign_enemy_attacks(
        [foe],
        [front, rear],
        context=CombatContext(tile_type="corridor", wandering_ambush=True),
    )
    assert pairs
    assert pairs[0][1].marching_order == 4


def test_multi_attack_foe_logs_assigned_targets(monkeypatch) -> None:
    first = member(class_id="warrior")
    first.marching_order = 1
    first.character_id = "first"
    first.name = "First"
    second = member(class_id="cleric")
    second.marching_order = 2
    second.character_id = "second"
    second.name = "Second"
    dragon = enemy()
    dragon.name = "Dragon"
    dragon.attacks = 3
    dragon.level = 1
    dragon.life = 5
    dragon.max_life = 5
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    result = resolve_combat_round(
        [first, second],
        [dragon],
        show_rolls=False,
        foe_phase_only=True,
        context=CombatContext(),
    )

    assert "Event: Dragon makes 3 attacks this round: #1 First, #2 Second, #1 First." in result.log


def test_flee_ends_combat_with_survivors(monkeypatch) -> None:
    hero = member(class_id="warrior")
    hero.current_life = 3
    foe = enemy()
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    result = resolve_flee([hero], [foe], show_rolls=False)
    assert result.fled
    assert hero.current_life > 0


def test_poison_foe_applies_lingering_status(monkeypatch) -> None:
    from app.engine import combat_modifiers

    hero = member(class_id="warrior")
    hero.current_life = 3
    snake = enemy()
    snake.name = "Snake"
    snake.tags = ["poison"]
    outcomes = iter([(1, [1]), (1, [1]), (1, [1]), (6, [6])])
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: next(outcomes))
    monkeypatch.setattr(combat_modifiers, "roll_exploding_for_level", lambda *args, **kwargs: next(outcomes))

    first = resolve_combat_round(
        [hero],
        [snake],
        show_rolls=False,
        foes_first=True,
        foe_phase_only=True,
        context=CombatContext(),
    )
    assert hero.current_life == 1
    assert any(status.lower().startswith("poisoned l") for status in hero.statuses)

    second = resolve_combat_round(
        first.party,
        [snake],
        show_rolls=False,
        foes_first=True,
        foe_phase_only=True,
        context=CombatContext(combat_round=2),
    )
    assert any("lingering poison" in entry for entry in second.log)


def test_mirror_image_absorbs_foe_hit(monkeypatch) -> None:
    hero = member(class_id="wizard")
    hero.current_life = 3
    hero.statuses = ["Mirror Image x2"]
    foe = enemy()
    monkeypatch.setattr(combat, "roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    result = resolve_combat_round(
        [hero],
        [foe],
        show_rolls=False,
        foes_first=True,
        foe_phase_only=True,
        context=CombatContext(),
    )

    assert hero.current_life == 3
    assert any("mirror image absorbs" in entry.lower() for entry in result.log)
    assert any(status == "Mirror Image x1" for status in hero.statuses)
