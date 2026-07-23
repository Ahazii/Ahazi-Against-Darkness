from __future__ import annotations

from pathlib import Path

from app.db import Store, init_db
from app.engine.combat import CombatRound
from app.engine.courtship_book_of_secrets import apply_curse_of_tamas_zeya
from app.engine.equipment_shop import sell_item
from app.engine.experience import award_encounter_xp
from app.engine.gremlin_events import apply_gremlin_repellant, resolve_invisible_gremlins
from app.engine.inventory import transfer_inventory_item
from app.engine.monster_template_effects import apply_star_slayer_sight_effects
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.spells import _cast_blessing
from app.engine.star_object_curse import (
    STAR_OBJECT_ITEM,
    STAR_OBJECT_STATUS,
    STAR_SLAYER_NAME,
    assign_recovered_star_object,
    apply_star_object_campaign_to_session,
    give_star_object,
    maybe_find_star_object_in_treasure,
    maybe_replace_major_foes,
    reconcile_star_object_carrier,
    removable_inventory_items,
    resolve_scene19_pickup,
    spawn_star_slayer,
    star_object_carrier,
    star_slayer_final_treasure_source,
    sync_star_object_campaign_from_session,
)
from app.engine.tag_campaign import STAR_OBJECT_EFFECT_KEY, campaign_effect, default_campaign, load_campaign, store_tag_treasure
from app.rules.repository import RulesRepository
from app.schemas import (
    Character,
    EnemyState,
    ExitState,
    MapState,
    PartyMemberState,
    PendingGremlinEventState,
    SessionState,
    TileState,
)


def _hero(
    character_id: str,
    name: str,
    *,
    class_id: str = "warrior",
    level: int = 4,
    marching_order: int = 1,
    inventory: list[str] | None = None,
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name,
        class_id=class_id,
        class_name=class_id.title(),
        level=level,
        xp=0,
        gold=20,
        current_life=8,
        max_life=8,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=marching_order,
        inventory=list(inventory or []),
    )


def _tile(tile_id: str = "room", *, x: int = 0) -> TileState:
    return TileState(
        id=tile_id,
        x=x,
        y=0,
        tile_key="11",
        tile_type="room",
        title=tile_id.title(),
        description=tile_id.title(),
    )


def _session(party: list[PartyMemberState], tiles: list[TileState] | None = None) -> SessionState:
    map_tiles = tiles or [_tile()]
    return SessionState(
        id="star-session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=party,
        map_state=MapState(tiles=map_tiles, current_tile_id=map_tiles[-1].id),
        created_at="2026-07-20T00:00:00Z",
        updated_at="2026-07-20T00:00:00Z",
    )


def _engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _monsters() -> dict:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override").monsters()


def _character(inventory: list[str]) -> Character:
    return Character(
        id="hero-1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=4,
        xp=0,
        gold=20,
        max_life=8,
        current_life=8,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=inventory,
        created_at="2026-07-20T00:00:00Z",
        updated_at="2026-07-20T00:00:00Z",
    )


def test_scene19_assigns_curse_and_applies_spellcaster_level() -> None:
    wizard = _hero("wizard", "Wizard", class_id="wizard", level=3)
    session = _session([wizard])

    result = resolve_scene19_pickup(session, wizard, roll_save=lambda _member: (5, [5]))

    assert result.passed is True
    assert result.modifier == 3
    assert result.total == 8
    assert wizard.inventory == [STAR_OBJECT_ITEM]
    assert STAR_OBJECT_STATUS in wizard.statuses
    assert wizard.madness == 0
    assert session.tag_star_object_curse_active is True


def test_scene19_failure_gains_madness_and_halfling_rerolls() -> None:
    warrior = _hero("warrior", "Warrior")
    failed_session = _session([warrior])
    failed = resolve_scene19_pickup(failed_session, warrior, roll_save=lambda _member: (2, [2]))
    assert failed.passed is False
    assert warrior.madness == 1

    halfling = _hero("halfling", "Halfling", class_id="halfling", level=2)
    reroll_session = _session([halfling])
    rolls = iter([(2, [2]), (8, [6, 2])])
    rerolled = resolve_scene19_pickup(reroll_session, halfling, roll_save=lambda _member: next(rolls))
    assert rerolled.passed is True
    assert rerolled.rolls == [6, 2]
    assert halfling.madness == 0
    assert any("Halfling reroll" in line for line in rerolled.log)


def test_blessing_cannot_remove_star_object_curse() -> None:
    cleric = _hero("cleric", "Cleric", class_id="cleric")
    session = _session([cleric])
    give_star_object(session, cleric)
    log: list[str] = []

    _cast_blessing(cleric, [cleric], [], cleric.character_id, log, session=session, show_rolls=False)

    assert STAR_OBJECT_ITEM in cleric.inventory
    assert STAR_OBJECT_STATUS in cleric.statuses
    assert session.tag_star_object_curse_active is True


def test_star_object_transfer_sale_storage_and_random_loss_are_blocked() -> None:
    carrier = _hero("carrier", "Carrier", inventory=[STAR_OBJECT_ITEM, "Sword"])
    ally = _hero("ally", "Ally", marching_order=2)
    ok, message = transfer_inventory_item(
        [carrier, ally],
        from_character_id=carrier.character_id,
        to_character_id=ally.character_id,
        item_name=STAR_OBJECT_ITEM,
    )
    assert ok is False
    assert "cannot be transferred" in message

    character = _character([STAR_OBJECT_ITEM])
    sold, message, payout = sell_item(character, {}, item_name=STAR_OBJECT_ITEM)
    assert sold is False
    assert payout == 0
    assert "cannot be sold" in message

    campaign = default_campaign()
    stored = store_tag_treasure(campaign, character, item_name=STAR_OBJECT_ITEM)
    assert campaign.tag_stored_items == []
    assert "cannot be stored" in stored.result_text
    assert removable_inventory_items(carrier.inventory) == ["Sword"]


def test_invisible_gremlins_require_choice_and_release_bypasses_protection() -> None:
    carrier = _hero("carrier", "Carrier", inventory=["Gremlin Repellant"])
    session = _session([carrier])
    give_star_object(session, carrier)

    prompt = resolve_invisible_gremlins(session, session.party)
    assert session.tag_star_object_gremlin_choice_pending is True
    assert any("Let them take it" in line for line in prompt)

    released = resolve_invisible_gremlins(session, session.party, star_object_choice="release")
    assert star_object_carrier(session) is None
    assert session.tag_star_object_curse_active is False
    assert session.tag_star_object_curse_cleared is True
    assert "Gremlin Repellant" in carrier.inventory
    assert any("protection is bypassed" in line for line in released)


def test_keeping_star_object_uses_normal_gremlin_protection() -> None:
    carrier = _hero("carrier", "Carrier", inventory=["Gremlin Repellant", "Magic Sword"])
    session = _session([carrier])
    session.camped_outside = True
    applied = apply_gremlin_repellant(
        session,
        repellant_owner=carrier,
        target=carrier,
        item_name="Magic Sword",
    )
    session.camped_outside = False
    give_star_object(session, carrier)

    log = resolve_invisible_gremlins(session, session.party, star_object_choice="keep")

    assert star_object_carrier(session) is carrier
    assert "Gremlin Repellant" not in carrier.inventory
    assert "Magic Sword" in carrier.inventory
    assert any("protected" in line.lower() for line in applied)
    assert any("normal Gremlin event continues" in line for line in log)


def test_keep_star_object_action_immediately_resolves_ordinary_theft() -> None:
    carrier = _hero("carrier", "Carrier", inventory=["Magic Sword"])
    session = _session([carrier])
    give_star_object(session, carrier)
    session.pending_gremlin_event = PendingGremlinEventState(
        tile_id="room",
        theft_count=1,
        major_tally_counted=True,
    )
    session.tag_star_object_gremlin_choice_pending = True

    _engine().advance(
        session,
        "resolve_star_object_gremlins",
        star_object_choice="keep",
    )

    assert session.pending_gremlin_event is None
    assert session.tag_star_object_gremlin_choice_pending is False
    assert "Magic Sword" not in carrier.inventory
    assert star_object_carrier(session) is carrier
    assert any("steal up to 1 item" in line for line in session.log)


def test_star_object_campaign_effect_is_scoped_to_assigned_campaign(tmp_path) -> None:
    store = Store(tmp_path / "game.db")
    init_db(store.db_path)
    carrier = _hero("carrier", "Carrier")
    source = _session([carrier])
    source.campaign_id = "campaign-a"
    give_star_object(source, carrier)

    sync_star_object_campaign_from_session(store, source)

    campaign = load_campaign(store)
    effect = campaign_effect(campaign, campaign_id="campaign-a", key=STAR_OBJECT_EFFECT_KEY)
    assert effect is not None
    assert effect.status == "active"
    assert effect.carrier_character_id == "carrier"
    assert campaign_effect(campaign, campaign_id="campaign-b", key=STAR_OBJECT_EFFECT_KEY) is None

    resumed = _session([_hero("carrier", "Carrier")])
    resumed.campaign_id = "campaign-a"
    unrelated = _session([_hero("other", "Other")])
    unrelated.campaign_id = "campaign-b"

    apply_star_object_campaign_to_session(store, resumed)
    apply_star_object_campaign_to_session(store, unrelated)
    sync_star_object_campaign_from_session(store, unrelated)

    assert star_object_carrier(resumed) is resumed.party[0]
    assert star_object_carrier(unrelated) is None
    campaign = load_campaign(store)
    assert campaign_effect(campaign, campaign_id="campaign-a", key=STAR_OBJECT_EFFECT_KEY).status == "active"
    assert campaign_effect(campaign, campaign_id="campaign-b", key=STAR_OBJECT_EFFECT_KEY) is None


def test_death_transfers_curse_and_total_party_loss_queues_recovery() -> None:
    first = _hero("first", "First")
    second = _hero("second", "Second", marching_order=2)
    session = _session([first, second])
    give_star_object(session, first)

    first.current_life = 0
    assert reconcile_star_object_carrier(session) is True
    assert star_object_carrier(session) is second

    second.current_life = 0
    assert reconcile_star_object_carrier(session) is True
    assert star_object_carrier(session) is None
    assert session.tag_star_object_recovery_pending is True

    future = _session([_hero("future", "Future")])
    future.tag_star_object_recovery_pending = True
    treasure_tile = future.map_state.tiles[0]
    assert maybe_find_star_object_in_treasure(future, treasure_tile, roll_fn=lambda: 1) is True
    assert future.tag_star_object_assignment_pending is True
    assert maybe_find_star_object_in_treasure(future, treasure_tile, roll_fn=lambda: 1) is False

    assigned = assign_recovered_star_object(future, "future")
    assert star_object_carrier(future) is future.party[0]
    assert future.tag_star_object_recovery_pending is False
    assert any("curse is operative again" in line for line in assigned)


def test_permanent_character_loss_transfers_star_object_before_removal() -> None:
    doomed = _hero("doomed", "Doomed")
    survivor = _hero("survivor", "Survivor", marching_order=2)
    session = _session([doomed, survivor])
    give_star_object(session, doomed)

    apply_curse_of_tamas_zeya(session, doomed, show_rolls=False)

    assert [member.character_id for member in session.party] == ["survivor"]
    assert star_object_carrier(session) is survivor


def test_captured_gear_does_not_confiscate_or_duplicate_star_object() -> None:
    carrier = _hero("carrier", "Carrier", inventory=["Sword"])
    session = _session([carrier])
    give_star_object(session, carrier)

    stripped = _engine()._strip_captive(session, carrier)

    assert stripped["equipment_count"] == 1
    assert carrier.inventory == [STAR_OBJECT_ITEM]
    assert session.captured_stripped_equipment[carrier.character_id].inventory == ["Sword"]


def test_star_slayer_replacement_uses_hcl_stats_and_keeps_final_treasure_source() -> None:
    hero = _hero("hero", "Hero", level=4)
    session = _session([hero])
    give_star_object(session, hero)
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(
            id="boss",
            name="Ancient Dragon",
            category="boss",
            level=8,
            life=10,
            max_life=10,
            tags=["final_boss"],
        )
    ]

    changed = maybe_replace_major_foes(session, tile, _monsters(), roll_fn=lambda: 2, show_rolls=False)

    assert changed is True
    slayer = tile.enemies[0]
    assert slayer.name == STAR_SLAYER_NAME
    assert slayer.level == 10
    assert slayer.life == slayer.max_life == 9
    assert slayer.attacks == 4
    assert {"star_slayer", "no_morale", "damage_per_hit:tier", "final_boss"} <= set(slayer.tags)
    assert star_slayer_final_treasure_source(slayer) == "Ancient Dragon"


def test_star_slayer_sight_applies_damage_madness_and_no_flee_once(monkeypatch) -> None:
    failed = _hero("failed", "Failed")
    passed = _hero("passed", "Passed", marching_order=2)
    session = _session([failed, passed])
    slayer = spawn_star_slayer(session, _monsters())
    rolls = iter([(1, [1]), (6, [6])])
    monkeypatch.setattr(
        "app.engine.monster_template_effects.roll_exploding_for_level",
        lambda *_args, **_kwargs: next(rolls),
    )

    log = apply_star_slayer_sight_effects([slayer], session.party, session, show_rolls=False)

    assert failed.current_life == 6
    assert failed.madness == 1
    assert failed.character_id in session.star_slayer_no_flee_character_ids
    assert passed.current_life == 8
    assert passed.madness == 0
    assert passed.character_id not in session.star_slayer_no_flee_character_ids
    assert apply_star_slayer_sight_effects([slayer], session.party, session, show_rolls=False) == []
    assert any("cannot flee" in line for line in log)


def test_star_slayer_split_flee_leaves_failed_saver_in_combat(monkeypatch) -> None:
    previous = _tile("previous", x=0)
    combat_tile = _tile("combat", x=1)
    combat_tile.exits = [
        ExitState(
            id="back",
            direction="west",
            kind="passage",
            status="open",
            destination_tile_id=previous.id,
        )
    ]
    failed = _hero("failed", "Failed")
    passed = _hero("passed", "Passed", marching_order=2)
    session = _session([failed, passed], [previous, combat_tile])
    session.mode = "combat"
    session.current_tile_entry_exit_id = "back"
    session.star_slayer_no_flee_character_ids = [failed.character_id]
    combat_tile.enemies = [spawn_star_slayer(session, _monsters())]
    monkeypatch.setattr(
        "app.engine.random_dungeon.resolve_flee",
        lambda party, enemies, **_kwargs: CombatRound(
            party=list(party),
            enemies=enemies,
            log=["The eligible heroes flee."],
            combat_over=True,
            fled=True,
        ),
    )

    _engine()._flee(session, show_rolls=False)

    assert session.mode == "combat"
    assert any(
        group.tile_id == previous.id and group.character_ids == [passed.character_id]
        for group in session.detached_groups
    )
    assert all(failed.character_id not in group.character_ids for group in session.detached_groups)
    assert any("combat continues" in line for line in session.log)


def test_star_slayer_awards_exactly_two_xp_rolls_even_as_final_boss() -> None:
    session = _session([_hero("hero", "Hero")])
    defeated = spawn_star_slayer(
        session,
        _monsters(),
        final_boss=True,
        final_treasure_source="Ancient Dragon",
    )
    defeated.life = 0

    award_encounter_xp(session, [defeated], show_rolls=False)

    assert session.xp_rolls_pending == 2
    assert session.final_boss_defeated is True
    assert any("exactly two XP rolls" in line for line in session.log)
