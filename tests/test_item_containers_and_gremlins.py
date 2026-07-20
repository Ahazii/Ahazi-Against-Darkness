from __future__ import annotations

from pathlib import Path

from app.engine.combat import CombatContext, _foe_hit_damage
from app.engine.gremlin_events import (
    apply_gremlin_repellant,
    begin_invisible_gremlins,
    move_gremlin_item_protection,
    offer_gremlin_temple_tag,
    offer_gremlin_temporary_weapon,
    resolve_pending_gremlin_theft,
    reveal_invisible_gremlins,
)
from app.engine.inventory import transfer_inventory_item
from app.engine.item_containers import (
    put_item_in_bag,
    remove_inventory_item_with_contents,
    take_item_from_bag,
)
from app.engine.monster_template_effects import apply_on_hit_effects
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.tag_temporary_weapon_enchantment import (
    pending_temporary_weapon_loss_choice,
    resolve_temporary_weapon_loss_choice,
)
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, ItemContainerState, PartyMemberState, PendingGremlinEventState, SessionState, TileState


def _member(character_id: str, name: str, **overrides) -> PartyMemberState:
    data = {
        "character_id": character_id,
        "name": name,
        "class_id": "warrior",
        "class_name": "Warrior",
        "level": 3,
        "xp": 0,
        "gold": 0,
        "current_life": 6,
        "max_life": 6,
        "attack_bonus": 0,
        "defense_bonus": 0,
        "save_bonus": 0,
        "marching_order": 1,
    }
    data.update(overrides)
    return PartyMemberState(**data)


def _session(party: list[PartyMemberState]) -> SessionState:
    return SessionState(
        id="gremlin-session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=party,
        map_state={"current_tile_id": "room", "tiles": []},
        created_at="2026-07-20T00:00:00Z",
        updated_at="2026-07-20T00:00:00Z",
    )


def test_legacy_multiple_bags_gain_stable_containers_without_duplication() -> None:
    member = _member(
        "hero",
        "Hero",
        inventory=["Bag of Carrying", "Sword", "Bag of Carrying"],
    )

    assert [bag.id for bag in member.item_containers] == ["hero-bag-1", "hero-bag-2"]

    reloaded = PartyMemberState.model_validate(member.model_dump())
    copied_with_models = _member(
        "hero-copy",
        "Hero Copy",
        inventory=list(member.inventory),
        item_containers=[bag.model_copy(deep=True) for bag in member.item_containers],
    )

    assert [bag.id for bag in reloaded.item_containers] == ["hero-bag-1", "hero-bag-2"]
    assert len(copied_with_models.item_containers) == 2


def test_specific_bag_contents_move_with_that_bag_and_barbarian_rejects_it() -> None:
    first = ItemContainerState(id="bag-one")
    second = ItemContainerState(id="bag-two")
    source = _member(
        "source",
        "Source",
        inventory=["Bag of Carrying", "Bag of Carrying", "Sword", "Potion of Healing"],
        item_containers=[first, second],
    )
    receiver = _member("receiver", "Receiver", marching_order=2)
    barbarian = _member(
        "barbarian",
        "Barbarian",
        class_id="barbarian",
        class_name="Barbarian",
        marching_order=3,
    )

    assert put_item_in_bag(source, container_id="bag-one", item_name="Sword")[0] is True
    assert put_item_in_bag(source, container_id="bag-two", item_name="Potion of Healing")[0] is True

    moved, _message = transfer_inventory_item(
        [source, receiver, barbarian],
        from_character_id="source",
        to_character_id="receiver",
        item_name="Bag of Carrying",
        item_container_id="bag-two",
    )
    refused, refused_message = transfer_inventory_item(
        [source, receiver, barbarian],
        from_character_id="source",
        to_character_id="barbarian",
        item_name="Bag of Carrying",
        item_container_id="bag-one",
    )

    assert moved is True
    assert [bag.id for bag in source.item_containers] == ["bag-one"]
    assert source.item_containers[0].contents == ["Sword"]
    assert [bag.id for bag in receiver.item_containers] == ["bag-two"]
    assert receiver.item_containers[0].contents == ["Potion of Healing"]
    assert refused is False
    assert "cannot use magic items" in refused_message

    taken, _message = take_item_from_bag(
        receiver,
        container_id="bag-two",
        item_name="Potion of Healing",
    )
    assert taken is True
    assert receiver.item_containers[0].contents == []
    assert "Potion of Healing" in receiver.inventory


def test_generic_item_loss_removes_only_the_selected_bag_and_its_contents() -> None:
    first = ItemContainerState(id="bag-one", contents=["Sword"])
    second = ItemContainerState(id="bag-two", contents=["Potion of Healing"])
    member = _member(
        "hero",
        "Hero",
        inventory=["Bag of Carrying", "Torch", "Bag of Carrying"],
        item_containers=[first, second],
    )

    removed, contents = remove_inventory_item_with_contents(member, inventory_index=2)

    assert removed == "Bag of Carrying"
    assert contents == ["Potion of Healing"]
    assert member.inventory == ["Bag of Carrying", "Torch"]
    assert [bag.id for bag in member.item_containers] == ["bag-one"]
    assert member.item_containers[0].contents == ["Sword"]


def test_stolen_bag_loses_its_contents_with_the_container() -> None:
    bag = ItemContainerState(id="loaded-bag", contents=["Scroll of Fireball", "Sword"])
    member = _member(
        "hero",
        "Hero",
        inventory=["Bag of Carrying"],
        item_containers=[bag],
    )
    session = _session([member])
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=1)

    log = resolve_pending_gremlin_theft(session, session.party)

    assert member.inventory == []
    assert member.item_containers == []
    assert any("everything inside" in line and "Scroll of Fireball" in line for line in log)


def test_protected_bag_survives_and_prevents_all_equipment_clue() -> None:
    bag = ItemContainerState(id="protected-bag", contents=["Magic Ring"])
    member = _member(
        "hero",
        "Hero",
        inventory=["Gremlin Repellant", "Bag of Carrying", "Dagger"],
        item_containers=[bag],
    )
    session = _session([member])
    session.camped_outside = True

    applied = apply_gremlin_repellant(
        session,
        repellant_owner=member,
        target=member,
        item_container_id="protected-bag",
    )
    session.camped_outside = False
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=2)
    log = resolve_pending_gremlin_theft(session, session.party)

    assert any("protected" in line.lower() for line in applied)
    assert member.inventory == ["Bag of Carrying"]
    assert member.item_containers[0].contents == ["Magic Ring"]
    assert session.clues_found == 0
    assert not any("thank-you" in line for line in log)


def test_item_level_repellant_moves_with_the_selected_bag() -> None:
    bag = ItemContainerState(id="protected-bag", contents=["Magic Ring"])
    source = _member(
        "source",
        "Source",
        inventory=["Gremlin Repellant", "Bag of Carrying"],
        item_containers=[bag],
    )
    receiver = _member("receiver", "Receiver", marching_order=2)
    session = _session([source, receiver])
    session.camped_outside = True
    apply_gremlin_repellant(
        session,
        repellant_owner=source,
        target=source,
        item_container_id="protected-bag",
    )

    moved, _message = transfer_inventory_item(
        session.party,
        from_character_id="source",
        to_character_id="receiver",
        item_name="Bag of Carrying",
        item_container_id="protected-bag",
    )
    protection_moved = move_gremlin_item_protection(
        session,
        from_character_id="source",
        to_character_id="receiver",
        item_name="Bag of Carrying",
        item_container_id="protected-bag",
    )

    assert moved is True
    assert protection_moved is True
    assert session.gremlin_protected_items[0].character_id == "receiver"


def test_temple_tag_is_only_taken_when_player_volunteers_it() -> None:
    member = _member(
        "hero",
        "Hero",
        inventory=["TAG Resurrection tag", "Dagger"],
    )
    session = _session([member])
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=2)

    offered = offer_gremlin_temple_tag(
        session,
        character_id="hero",
        item_name="TAG Resurrection tag",
    )
    resolved = resolve_pending_gremlin_theft(session, session.party)

    assert any("voluntarily" in line for line in offered)
    assert "TAG Resurrection tag" not in member.inventory
    assert "Dagger" not in member.inventory
    assert any("Dagger" in line for line in resolved)


def test_dead_kukla_secret_compartment_items_and_gold_are_exposed() -> None:
    kukla = _member(
        "kukla",
        "Kukla",
        class_id="kukla",
        class_name="Kukla",
        current_life=0,
        kukla_compartment_items=["Magic Ring"],
        kukla_compartment_gold=20,
    )
    survivor = _member("hero", "Hero", marching_order=2)
    session = _session([kukla, survivor])
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=3)

    log = resolve_pending_gremlin_theft(session, session.party)

    assert kukla.kukla_compartment_items == []
    assert kukla.kukla_compartment_gold == 0
    assert any("secret compartment loses Magic Ring" in line for line in log)
    assert sum("secret compartment loses 10gp" in line for line in log) == 2


def test_temporary_weapon_enchantment_is_kept_unless_player_offers_it() -> None:
    marker = "TAG Temporary Weapon Enchantment: Sword is magical, no Attack bonus"
    member = _member(
        "hero",
        "Hero",
        inventory=["Sword", "Magic Ring"],
        statuses=[marker],
    )
    session = _session([member])
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=1)

    ordinary = resolve_pending_gremlin_theft(session, session.party)

    assert "Sword" in member.inventory
    assert "Magic Ring" not in member.inventory
    assert marker in member.statuses
    assert any("Magic Ring" in line for line in ordinary)

    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=1)
    offered = offer_gremlin_temporary_weapon(
        session,
        character_id="hero",
        item_name="Sword",
    )

    assert "Sword" not in member.inventory
    assert marker not in member.statuses
    assert session.pending_gremlin_event is None
    assert any("chooses to let" in line and "TAG p.65" in line for line in offered)


def test_one_temporary_enchantment_protects_only_one_identically_named_weapon() -> None:
    marker = "TAG Temporary Weapon Enchantment: Sword is magical, no Attack bonus"
    member = _member(
        "hero",
        "Hero",
        inventory=["Sword", "Sword"],
        statuses=[marker],
    )
    session = _session([member])
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=1)

    resolve_pending_gremlin_theft(session, session.party)

    assert member.inventory == ["Sword"]
    assert marker in member.statuses


def test_disbelief_reveals_printed_gremlin_group_profile() -> None:
    session = _session([_member("hero", "Hero")])
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=7)

    enemies, log = reveal_invisible_gremlins(session, roll_fn=lambda: 4)

    assert len(enemies) == 5
    assert session.pending_gremlin_event is None
    assert all(enemy.level == 3 and enemy.life == 1 and enemy.attacks == 1 for enemy in enemies)
    assert all("damage_per_hit:0" in enemy.tags for enemy in enemies)
    assert all("morale_modifier:-1" in enemy.tags for enemy in enemies)
    assert all(enemy.on_hit_effects == [{"type": "steal_item", "source": "Invisible Gremlins"}] for enemy in enemies)
    assert any("one Treasure roll" in line for line in log)


def test_pending_gremlin_event_counts_once_toward_major_foes() -> None:
    session = _session([_member("hero", "Hero")])

    first = begin_invisible_gremlins(session, session.party, tile_id="room", roll_fn=lambda: 2)
    second = begin_invisible_gremlins(session, session.party, tile_id="room", roll_fn=lambda: 6)

    assert session.major_foes_encountered == 1
    assert session.pending_gremlin_event is not None
    assert session.pending_gremlin_event.theft_count == 5
    assert session.pending_gremlin_event.major_tally_counted is True
    assert any("cannot be the Final Boss" in line for line in first)
    assert not any("Major Foe tally" in line for line in second)


def test_revealed_gremlin_hit_steals_instead_of_causing_life_loss() -> None:
    member = _member("hero", "Hero", inventory=["Magic Sword"], current_life=6)
    session = _session([member])
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=7)
    enemies, _log = reveal_invisible_gremlins(session, roll_fn=lambda: 1)
    enemy = enemies[0]

    effect_log = apply_on_hit_effects(
        enemy,
        member,
        context=CombatContext(session=session),
        show_rolls=False,
    )

    assert _foe_hit_damage(enemy, CombatContext(session=session)) == 0
    assert member.current_life == 6
    assert "Magic Sword" not in member.inventory
    assert any("loses Magic Sword" in line for line in effect_log)


def test_revealed_gremlin_respects_persisted_temporary_weapon_choice() -> None:
    marker = "TAG Temporary Weapon Enchantment: Sword is magical, no Attack bonus"
    member = _member(
        "hero",
        "Hero",
        inventory=["Sword", "Magic Ring"],
        statuses=[marker],
    )
    session = _session([member])
    session.mode = "combat"
    enemy = EnemyState(
        id="gremlin",
        name="Revealed Invisible Gremlin",
        category="minions",
        level=3,
        life=1,
        max_life=1,
        attacks=1,
        on_hit_effects=[{"type": "steal_item", "source": "Invisible Gremlins"}],
    )
    session.map_state.tiles = [
        TileState(
            id="room",
            x=0,
            y=0,
            tile_key="11",
            tile_type="room",
            title="Room",
            description="Room",
            enemies=[enemy],
        )
    ]

    pending = pending_temporary_weapon_loss_choice(session)
    assert pending is not None and pending.loss_kind == "stolen"
    resolve_temporary_weapon_loss_choice(session, "keep")
    reloaded = SessionState.model_validate(session.model_dump())

    effect_log = apply_on_hit_effects(
        enemy,
        reloaded.party[0],
        context=CombatContext(session=reloaded),
        show_rolls=False,
    )

    assert "Sword" in reloaded.party[0].inventory
    assert "Magic Ring" not in reloaded.party[0].inventory
    assert marker in reloaded.party[0].statuses
    assert any("Magic Ring" in line for line in effect_log)


def test_revealed_gremlin_can_take_temporary_weapon_when_player_allows_it() -> None:
    marker = "TAG Temporary Weapon Enchantment: Sword is magical, no Attack bonus"
    member = _member(
        "hero",
        "Hero",
        inventory=["Sword", "Scroll of Blessing"],
        statuses=[marker],
    )
    session = _session([member])
    session.mode = "combat"
    enemy = EnemyState(
        id="gremlin",
        name="Revealed Invisible Gremlin",
        category="minions",
        level=3,
        life=1,
        max_life=1,
        attacks=1,
        on_hit_effects=[{"type": "steal_item", "source": "Invisible Gremlins"}],
    )
    session.map_state.tiles = [
        TileState(
            id="room",
            x=0,
            y=0,
            tile_key="11",
            tile_type="room",
            title="Room",
            description="Room",
            enemies=[enemy],
        )
    ]
    resolve_temporary_weapon_loss_choice(session, "allow")

    apply_on_hit_effects(
        enemy,
        member,
        context=CombatContext(session=session),
        show_rolls=False,
    )

    assert "Sword" not in member.inventory
    assert "Scroll of Blessing" in member.inventory
    assert marker not in member.statuses


def test_iron_eater_respects_temporary_weapon_choice_and_gold_fallback(monkeypatch) -> None:
    marker = "TAG Temporary Weapon Enchantment: Sword is magical, no Attack bonus"
    member = _member("hero", "Hero", inventory=["Sword"], statuses=[marker], gold=20)
    session = _session([member])
    session.mode = "combat"
    enemy = EnemyState(
        id="iron-eater",
        name="Iron Eater",
        category="weird",
        level=5,
        life=4,
        max_life=4,
        attacks=3,
        on_hit_effects=[
            {
                "type": "destroy_metal_items",
                "priority_order": ["armor", "shield", "main_weapon", "3d6gp"],
            }
        ],
    )
    session.map_state.tiles = [
        TileState(
            id="room",
            x=0,
            y=0,
            tile_key="11",
            tile_type="room",
            title="Room",
            description="Room",
            enemies=[enemy],
        )
    ]
    pending = pending_temporary_weapon_loss_choice(session)
    assert pending is not None and pending.loss_kind == "destroyed"
    resolve_temporary_weapon_loss_choice(session, "keep")

    kept_log = apply_on_hit_effects(
        enemy,
        member,
        context=CombatContext(session=session),
        show_rolls=False,
    )

    assert "Sword" in member.inventory
    assert any("may not destroy it" in line for line in kept_log)

    member.inventory.clear()
    monkeypatch.setattr("app.engine.monster_template_effects.roll_d6", lambda: 2)
    gold_log = apply_on_hit_effects(
        enemy,
        member,
        context=CombatContext(session=session),
        show_rolls=False,
    )

    assert member.gold == 14
    assert any("destroys Hero's 6gp" in line for line in gold_log)


def test_casting_disbelief_during_pending_event_starts_revealed_combat() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())
    caster = _member(
        "illusionist",
        "Illusionist",
        class_id="illusionist",
        class_name="Illusionist",
        spells=["Disbelief"],
    )
    session = _session([caster])
    session.map_state.tiles = [
        TileState(
            id="room",
            x=0,
            y=0,
            tile_key="11",
            tile_type="room",
            title="Room",
            description="Room",
        )
    ]
    session.pending_gremlin_event = PendingGremlinEventState(tile_id="room", theft_count=7)

    engine.advance(
        session,
        "cast_spell",
        character_id="illusionist",
        spell_name="Disbelief",
    )

    assert session.mode == "combat"
    assert session.pending_gremlin_event is None
    assert 2 <= len(session.map_state.tiles[0].enemies) <= 7
    assert "Disbelief" in session.expended_spells["illusionist"]
    assert any("reveals" in line and "Invisible Gremlin" in line for line in session.log)
