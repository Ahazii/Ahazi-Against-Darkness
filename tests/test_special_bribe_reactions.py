from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.equipment_shop import jewelry_bribe_counted_gp
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.reactions import is_bribe_reaction
from app.rules.repository import RulesRepository
from app.schemas import DetachedGroupState, EnemyState, ExitState, MapState, PartyMemberState, SessionState, TileState

ALL_SPECIAL_BRIBE_KEYS = frozenset(
    {
        "bribe_magic_item",
        "bribe_food",
        "bribe_food_per_foe",
        "bribe_gold_or_food",
        "bribe_ration_gold_or_mushroom",
        "bribe_food_or_gem",
        "bribe_gem",
        "bribe_scrolls_or_potions",
        "bribe_gem_or_two_handed_weapon",
        "bribe_treasure_or_magic_item",
    }
)


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def _engine() -> RandomDungeonEngine:
    return RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")


def _hero(**overrides) -> PartyMemberState:
    base = dict(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon"],
    )
    base.update(overrides)
    return PartyMemberState(**base)


def _pending_special_bribe_session(
    reaction_key: str,
    *,
    party: list[PartyMemberState],
    foe_count: int = 1,
    enemy_name: str = "Foes",
) -> SessionState:
    enemies = [
        EnemyState(
            id=f"foe-{index}",
            name=enemy_name,
            category="minions",
            level=4,
            life=1,
            max_life=1,
        )
        for index in range(foe_count)
    ]
    return SessionState(
        id="special-bribe",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        reaction_pending=True,
        reaction_key=reaction_key,
        reaction_bribe_foe_count=foe_count,
        party=party,
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
                    enemies=enemies,
                    initial_enemy_count=len(enemies),
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def _two_dwarf_party(**inventory_gold) -> list[PartyMemberState]:
    return [
        _hero(
            character_id="d1",
            name="D1",
            class_id="dwarf",
            class_name="Dwarf",
            gold=inventory_gold.get("gold", 200),
            inventory=inventory_gold.get("inventory", ["Hand weapon"]),
        ),
        _hero(
            character_id="d2",
            name="D2",
            class_id="dwarf",
            class_name="Dwarf",
            gold=inventory_gold.get("gold", 200),
            inventory=inventory_gold.get("inventory", ["Hand weapon"]),
        ),
    ]


def _scout_special_bribe_session(
    *,
    scout_inventory: list[str],
    enemy_name: str,
    scout_gold: int = 0,
) -> SessionState:
    remote = _hero(character_id="remote", name="Remote", marching_order=1)
    scout = _hero(
        character_id="scout",
        name="Scout",
        class_id="rogue",
        class_name="Rogue",
        gold=scout_gold,
        inventory=scout_inventory,
        marching_order=2,
    )
    main = TileState(
        id="main",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Main Room",
        description="Main",
        exits=[ExitState(id="to-scout", direction="east", kind="door", status="open", destination_tile_id="scout-room")],
    )
    scout_room = TileState(
        id="scout-room",
        x=1,
        y=0,
        tile_key="12",
        tile_type="room",
        title="Scout Room",
        description="Scout",
        enemies=[EnemyState(id="foe", name=enemy_name, category="minions", level=4, life=1, max_life=1)],
        initial_enemy_count=1,
        exits=[ExitState(id="to-main", direction="west", kind="door", status="open", destination_tile_id="main")],
    )
    return SessionState(
        id="scout-special-bribe",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[remote, scout],
        detached_groups=[DetachedGroupState(tile_id="scout-room", character_ids=["scout"], reason="scout")],
        scout_encounter_origin_tile_ids={"scout-room": "main"},
        map_state=MapState(tiles=[main, scout_room], current_tile_id="main"),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


@pytest.mark.parametrize(
    ("reaction_key", "party", "foe_count", "advance_extra", "log_fragment"),
    [
        pytest.param(
            "bribe_magic_item",
            [_hero(inventory=["Magic Sword (+1 Attack)"])],
            1,
            {"character_id": "hero", "item_name": "Magic Sword (+1 Attack)"},
            "gives Magic Sword",
            id="bribe_magic_item",
        ),
        pytest.param(
            "bribe_food",
            [_hero(inventory=["Food ration"] * 4)],
            1,
            {},
            "gives 4 Food ration",
            id="bribe_food",
        ),
        pytest.param(
            "bribe_food_per_foe",
            [_hero(inventory=["Food ration"])],
            1,
            {},
            "gives 1 Food ration",
            id="bribe_food_per_foe",
        ),
        pytest.param(
            "bribe_gold_or_food",
            [_hero(inventory=["Food ration"] * 5)],
            1,
            {"reaction_bribe_mode": "food"},
            "gives 5 Food ration",
            id="bribe_gold_or_food-food",
        ),
        pytest.param(
            "bribe_gold_or_food",
            [_hero(gold=15, inventory=[])],
            1,
            {"reaction_bribe_mode": "gold"},
            "pays 15gp",
            id="bribe_gold_or_food-gold",
        ),
        pytest.param(
            "bribe_ration_gold_or_mushroom",
            [_hero(inventory=["Food ration", "Food ration"])],
            2,
            {"reaction_bribe_mode": "food"},
            "gives 2 Food ration",
            id="bribe_ration_gold_or_mushroom-food",
        ),
        pytest.param(
            "bribe_ration_gold_or_mushroom",
            [_hero(inventory=["Puffball mushroom", "Puffball mushroom"])],
            2,
            {"reaction_bribe_mode": "mushroom", "item_name": "Puffball mushroom"},
            "gives Puffball mushroom",
            id="bribe_ration_gold_or_mushroom-mushroom",
        ),
        pytest.param(
            "bribe_ration_gold_or_mushroom",
            [_hero(gold=10, inventory=[])],
            2,
            {"reaction_bribe_mode": "gold"},
            "pays 10gp",
            id="bribe_ration_gold_or_mushroom-gold",
        ),
        pytest.param(
            "bribe_food_or_gem",
            [_hero(inventory=["Food ration", "Food ration"])],
            2,
            {"reaction_bribe_mode": "food"},
            "gives 2 Food ration",
            id="bribe_food_or_gem-food",
        ),
        pytest.param(
            "bribe_food_or_gem",
            [_hero(inventory=["Small gemstone (25gp)"])],
            2,
            {"character_id": "hero", "item_name": "Small gemstone (25gp)"},
            "gives Small gemstone",
            id="bribe_food_or_gem-gem",
        ),
        pytest.param(
            "bribe_gem",
            [_hero(inventory=["Small gemstone (25gp)"])],
            1,
            {"character_id": "hero", "item_name": "Small gemstone (25gp)"},
            "gives Small gemstone",
            id="bribe_gem",
        ),
        pytest.param(
            "bribe_scrolls_or_potions",
            [_hero(inventory=["Scroll of Blessing", "Healing potion"])],
            1,
            {"character_id": "hero", "item_name": "Scroll of Blessing"},
            "gives Scroll of Blessing",
            id="bribe_scrolls_or_potions",
        ),
        pytest.param(
            "bribe_gem_or_two_handed_weapon",
            [_hero(inventory=["Heavy weapon"])],
            1,
            {"character_id": "hero", "item_name": "Heavy weapon"},
            "gives Heavy weapon",
            id="bribe_gem_or_two_handed_weapon-weapon",
        ),
        pytest.param(
            "bribe_gem_or_two_handed_weapon",
            [_hero(inventory=["Small gemstone (25gp)"])],
            1,
            {"character_id": "hero", "item_name": "Small gemstone (25gp)"},
            "gives Small gemstone",
            id="bribe_gem_or_two_handed_weapon-gem",
        ),
        pytest.param(
            "bribe_treasure_or_magic_item",
            [_hero(inventory=["Magic Sword (+1 Attack)"])],
            1,
            {"character_id": "hero", "item_name": "Magic Sword (+1 Attack)"},
            "gives Magic Sword",
            id="bribe_treasure_or_magic_item-magic",
        ),
        pytest.param(
            "bribe_treasure_or_magic_item",
            [_hero(gold=120, inventory=[])],
            1,
            {"reaction_bribe_mode": "all_gold"},
            "gives the dragon all carried gold",
            id="bribe_treasure_or_magic_item-gold",
        ),
    ],
)
def test_special_bribe_success_table(
    reaction_key: str,
    party: list[PartyMemberState],
    foe_count: int,
    advance_extra: dict,
    log_fragment: str,
) -> None:
    engine = _engine()
    session = _pending_special_bribe_session(reaction_key, party=party, foe_count=foe_count)
    before_gold = sum(member.gold for member in party)
    before_items = [list(member.inventory) for member in party]

    engine.advance(session, "reaction_choice", reaction_choice="accept", **advance_extra)

    assert session.mode == "exploration"
    assert session.map_state.tiles[0].enemies == []
    assert any(log_fragment in entry for entry in session.log)
    assert sum(member.gold for member in party) < before_gold or any(
        member.inventory != before_items[index] for index, member in enumerate(party)
    )


def test_special_bribe_success_table_covers_all_keys() -> None:
    covered = {
        "bribe_magic_item",
        "bribe_food",
        "bribe_food_per_foe",
        "bribe_gold_or_food",
        "bribe_ration_gold_or_mushroom",
        "bribe_food_or_gem",
        "bribe_gem",
        "bribe_scrolls_or_potions",
        "bribe_gem_or_two_handed_weapon",
        "bribe_treasure_or_magic_item",
    }
    assert covered == ALL_SPECIAL_BRIBE_KEYS


@pytest.mark.parametrize(
    ("reaction_key", "party", "foe_count", "advance_extra", "log_fragment"),
    [
        pytest.param("bribe_magic_item", [_hero(inventory=[])], 1, {}, "magic item", id="bribe_magic_item"),
        pytest.param("bribe_food", [_hero(inventory=[])], 1, {}, "Food ration", id="bribe_food"),
        pytest.param("bribe_food_per_foe", [_hero(inventory=[])], 2, {}, "Food ration", id="bribe_food_per_foe"),
        pytest.param(
            "bribe_gold_or_food",
            [_hero(gold=0, inventory=[])],
            1,
            {"reaction_bribe_mode": "gold"},
            "15gp",
            id="bribe_gold_or_food",
        ),
        pytest.param(
            "bribe_ration_gold_or_mushroom",
            [_hero(gold=0, inventory=[])],
            2,
            {"reaction_bribe_mode": "gold"},
            "10gp",
            id="bribe_ration_gold_or_mushroom",
        ),
        pytest.param(
            "bribe_food_or_gem",
            [_hero(inventory=[])],
            2,
            {"reaction_bribe_mode": "food"},
            "gem or 2 Food",
            id="bribe_food_or_gem",
        ),
        pytest.param("bribe_gem", [_hero(inventory=[])], 1, {}, "gem", id="bribe_gem"),
        pytest.param(
            "bribe_scrolls_or_potions",
            [_hero(inventory=[])],
            1,
            {},
            "scroll or potion",
            id="bribe_scrolls_or_potions",
        ),
        pytest.param(
            "bribe_gem_or_two_handed_weapon",
            [_hero(inventory=[])],
            1,
            {},
            "gem or heavy",
            id="bribe_gem_or_two_handed_weapon",
        ),
        pytest.param(
            "bribe_treasure_or_magic_item",
            [_hero(gold=50, inventory=[])],
            1,
            {"reaction_bribe_mode": "all_gold"},
            "100gp",
            id="bribe_treasure_or_magic_item",
        ),
    ],
)
def test_special_bribe_failure_table(
    reaction_key: str,
    party: list[PartyMemberState],
    foe_count: int,
    advance_extra: dict,
    log_fragment: str,
) -> None:
    engine = _engine()
    session = _pending_special_bribe_session(reaction_key, party=party, foe_count=foe_count)
    before_gold = [member.gold for member in party]
    before_inventory = [list(member.inventory) for member in party]

    engine.advance(session, "reaction_choice", reaction_choice="accept", **advance_extra)

    assert session.mode == "combat"
    assert session.map_state.tiles[0].enemies
    assert [member.gold for member in party] == before_gold
    assert [list(member.inventory) for member in party] == before_inventory
    assert any(log_fragment.lower() in entry.lower() for entry in session.log)


@pytest.mark.parametrize("reaction_key", sorted(ALL_SPECIAL_BRIBE_KEYS))
def test_dwarf_miser_blocks_special_bribes(reaction_key: str) -> None:
    engine = _engine()
    party = _two_dwarf_party(
        inventory=["Food ration"] * 6
        + ["Small gemstone (25gp)", "Magic Sword (+1 Attack)", "Scroll of Blessing", "Healing potion", "Heavy weapon"],
        gold=200,
    )
    session = _pending_special_bribe_session(reaction_key, party=party, foe_count=2)
    engine.advance(
        session,
        "reaction_choice",
        reaction_choice="accept",
        reaction_bribe_mode="all_gold",
        character_id="d1",
        item_name=party[0].inventory[0],
    )
    assert session.mode == "combat"
    assert any("Miser" in entry for entry in session.log)


def test_gem_bribe_logs_counted_value_for_dwarf(monkeypatch) -> None:
    catalog = packaged_rules().equipment_shop()

    def _counted(item_name: str, class_id: str, _catalog: dict) -> int | None:
        if "gemstone" in item_name.lower():
            value = 25
            if class_id.lower() == "dwarf":
                value = int(value * 1.2)
            return value
        return jewelry_bribe_counted_gp(item_name, class_id, _catalog)

    monkeypatch.setattr("app.engine.random_dungeon.jewelry_bribe_counted_gp", _counted)
    engine = _engine()
    party = [_hero(class_id="dwarf", class_name="Dwarf", inventory=["Small gemstone (25gp)"])]
    session = _pending_special_bribe_session("bribe_gem", party=party)

    engine.advance(
        session,
        "reaction_choice",
        reaction_choice="accept",
        character_id="hero",
        item_name="Small gemstone (25gp)",
    )

    assert session.mode == "exploration"
    assert any("Counted gem value for bribe: 30gp" in entry for entry in session.log)


@pytest.mark.parametrize(
    ("enemy_name", "roll", "scout_inventory", "log_fragment"),
    [
        pytest.param("Moldspawn", 2, ["Food ration"], "gives 1 Food ration", id="scout-bribe_food_per_foe"),
        pytest.param(
            "Wraith",
            1,
            ["Magic Sword (+1 Attack)"],
            "surrenders a magic item",
            id="scout-bribe_magic_item",
        ),
        pytest.param("Cavemen", 2, ["Small gemstone (25gp)"], "gives Small gemstone", id="scout-bribe_food_or_gem"),
    ],
)
def test_scout_special_bribe_table(
    monkeypatch,
    enemy_name: str,
    roll: int,
    scout_inventory: list[str],
    log_fragment: str,
) -> None:
    engine = _engine()
    session = _scout_special_bribe_session(scout_inventory=scout_inventory, enemy_name=enemy_name)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: roll)

    engine.advance(session, "scout_reaction", detached_tile_id="scout-room")

    scout_room = next(tile for tile in session.map_state.tiles if tile.id == "scout-room")
    assert scout_room.enemies == []
    assert scout_room.resolved is True
    assert any(log_fragment in entry for entry in session.log)


def test_all_special_bribe_keys_are_recognized() -> None:
    for key in ALL_SPECIAL_BRIBE_KEYS:
        assert is_bribe_reaction(key)
