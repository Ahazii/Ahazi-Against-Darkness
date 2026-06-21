from __future__ import annotations

from app.engine.class_abilities import apply_nourishing_meal, luck_points_remaining, spend_luck_point
from app.engine.equipment_effects import AMULET_LUCK_STATUS, has_ten_foot_pole_in_inventories
from app.engine.equipment_shop import buy_equipment, sell_item
from app.engine.hunger import (
    HUNGER_WARN_HOURS,
    HUNGRY_STATUS,
    feed_member_hunger,
    feed_hungry_heroes,
    tick_party_hunger,
)
from app.engine.reactions import consume_fools_gold
from app.schemas import Character, PartyMemberState, SessionState


def _member(**kwargs) -> PartyMemberState:
    base = dict(
        character_id="h1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=1,
        defense_bonus=0,
        save_bonus=0,
        inventory=[],
    )
    base.update(kwargs)
    return PartyMemberState(**base)


def test_hunger_becomes_hungry_after_24_hours() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member()],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        created_at="t",
        updated_at="t",
    )
    logs: list[str] = []
    for _ in range(24):
        tick_party_hunger(session, session.party, log=logs)
    assert HUNGRY_STATUS in session.party[0].statuses
    assert any("24 hours" in line for line in logs)


def test_hunger_warns_at_20_hours() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member()],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        created_at="t",
        updated_at="t",
    )
    logs: list[str] = []
    for _ in range(HUNGER_WARN_HOURS):
        tick_party_hunger(session, session.party, log=logs)
    assert HUNGRY_STATUS not in session.party[0].statuses
    assert any("Hungry soon" in line for line in logs)


def test_feed_hungry_heroes_batch() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            _member(character_id="h1", name="A", statuses=[HUNGRY_STATUS], inventory=["Food ration"]),
            _member(character_id="h2", name="B", statuses=[HUNGRY_STATUS]),
        ],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        created_at="t",
        updated_at="t",
    )
    logs = feed_hungry_heroes(session, session.party)
    assert HUNGRY_STATUS not in session.party[0].statuses
    assert HUNGRY_STATUS in session.party[1].statuses
    assert any("Ran out" in line for line in logs)


def test_feeding_clears_hunger() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member(statuses=[HUNGRY_STATUS])],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        hunger_rounds={"h1": 30},
        created_at="t",
        updated_at="t",
    )
    feed_member_hunger(session, session.party[0])
    assert HUNGRY_STATUS not in session.party[0].statuses
    assert session.hunger_rounds["h1"] == 0


def test_amulet_luck_stacks_with_halfling() -> None:
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member(class_id="halfling", class_name="Halfling", statuses=[AMULET_LUCK_STATUS])],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        created_at="t",
        updated_at="t",
    )
    assert luck_points_remaining(session, session.party[0]) >= 2


def test_fools_gold_consumed() -> None:
    party = [_member(inventory=["Fools' Gold"])]
    ok, message = consume_fools_gold(party)
    assert ok
    assert "Fools' Gold" not in party[0].inventory


def test_no_fools_gold_blocks_bribe_shortcut() -> None:
    from pathlib import Path

    from app.engine.random_dungeon import RandomDungeonEngine
    from app.rules.repository import RulesRepository
    from app.schemas import EnemyState

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        reaction_key="bribe",
        reaction_bribe_gold=5,
        reaction_bribe_gold_per_foe=5,
        reaction_bribe_foe_count=1,
        reaction_no_fools_gold=True,
        party=[_member(inventory=["Fools' Gold"])],
        map_state={
            "tiles": [
                {
                    "id": "tile",
                    "x": 0,
                    "y": 0,
                    "tile_key": "11",
                    "tile_type": "room",
                    "title": "Room",
                    "description": "Room",
                    "enemies": [
                        EnemyState(
                            id="foe",
                            name="Iron Eater",
                            category="weird",
                            level=4,
                            life=3,
                            max_life=3,
                        ).model_dump()
                    ],
                    "initial_enemy_count": 1,
                }
            ],
            "current_tile_id": "tile",
        },
        created_at="t",
        updated_at="t",
    )
    engine.advance(session, "pay_bribe_fools_gold")
    assert session.mode == "combat"
    assert "Fools' Gold" in session.party[0].inventory
    assert any("cannot be fooled" in line for line in session.log)


def test_fools_gold_satisfies_gold_bribe() -> None:
    from pathlib import Path

    from app.engine.random_dungeon import RandomDungeonEngine
    from app.rules.repository import RulesRepository
    from app.schemas import EnemyState, MapState, TileState

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path(__file__).resolve().parents[1] / "assets")
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        reaction_key="bribe",
        reaction_bribe_gold=5,
        reaction_bribe_gold_per_foe=5,
        reaction_bribe_foe_count=1,
        reaction_no_fools_gold=False,
        party=[_member(inventory=["Fools' Gold"])],
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
                    enemies=[
                        EnemyState(
                            id="foe",
                            name="Goblin",
                            category="minions",
                            level=3,
                            life=1,
                            max_life=1,
                        )
                    ],
                    initial_enemy_count=1,
                )
            ],
            current_tile_id="tile",
        ),
        created_at="t",
        updated_at="t",
    )
    engine.advance(session, "pay_bribe_fools_gold")
    assert session.mode == "exploration"
    assert "Fools' Gold" not in session.party[0].inventory


def test_one_pole_per_party() -> None:
    assert has_ten_foot_pole_in_inventories([["10' pole"], []]) is True
    assert has_ten_foot_pole_in_inventories([["Bow"], ["Hand weapon"]]) is False


def test_amulet_luck_save_reroll_for_non_halfling() -> None:
    from app.engine.class_abilities import reroll_failed_save_with_luck

    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[_member(class_id="warrior", class_name="Warrior", statuses=[AMULET_LUCK_STATUS], inventory=["Amulet"])],
        map_state={"width": 1, "height": 1, "tiles": [], "current_tile_id": "t"},
        pending_save_reroll={"character_id": "h1", "level": 3, "modifier": 0},
        created_at="t",
        updated_at="t",
    )
    log, succeeded = reroll_failed_save_with_luck(session, session.party[0], show_rolls=True)
    assert any("Save reroll" in line for line in log)
    assert AMULET_LUCK_STATUS not in session.party[0].statuses
