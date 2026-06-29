from __future__ import annotations

from pathlib import Path

from app.db import now_utc
from app.engine import tag_campaign
from app.engine.tag_campaign import (
    build_tag_adventure_manifest,
    check_item_availability,
    create_magic_locker,
    default_campaign,
    follow_treasure_map,
    look_for_clues,
    purchase_tag_service,
    roll_gambling_house,
    roll_hidden_treasure_trove_risk,
    roll_aspergillum_break_chance,
    roll_flammable_oil_throw,
    roll_horn_wandering_attraction,
    roll_moneylender_follow_chance,
    roll_treasure_map_price,
    run_streetwise_action,
    cast_tag_guild_spell,
    consume_tag_guild_marker,
    convert_character_gold_to_tag_bank,
    resolve_tag_branch_action,
    resolve_tag_finance_action,
    resolve_tag_route_action,
    resolve_tag_scene_action,
    resolve_tag_xp_action,
    settlement_size_from_roll,
    settlement_service_rows,
    store_tag_treasure,
    summon_magic_locker,
    travel_to_new_settlement,
    use_tag_trinket,
    update_troupe,
    withdraw_tag_stored_gold,
)
from app.engine.adventure_manifest import validate_adventure_manifest
from app.engine.equipment_shop import buy_equipment
from app.rules.repository import RulesRepository
from app.schemas import Character


def _character(**overrides) -> Character:
    timestamp = now_utc()
    data = {
        "id": "hero-1",
        "name": "Sly Silas",
        "class_id": "rogue",
        "class_name": "Rogue",
        "level": 3,
        "gold": 20,
        "clues": 0,
        "max_life": 4,
        "current_life": 4,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    data.update(overrides)
    return Character(**data)


def test_tag_settlement_size_table() -> None:
    assert [settlement_size_from_roll(roll) for roll in range(1, 7)] == [-2, -1, 0, 1, 2, 3]


def test_tag_availability_success_surcharge_and_unavailable(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_size = 0

    rolls = iter([6, 5, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    success = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)
    surcharge = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)
    unavailable = check_item_availability(campaign, item_name="Guild item", difficulty=6, base_price_gp=10)

    assert success.outcome == "available"
    assert success.final_price_gp == 10
    assert surcharge.outcome == "surcharge"
    assert surcharge.final_price_gp == 12
    assert unavailable.outcome == "unavailable"
    assert unavailable.final_price_gp is None


def test_tag_look_for_clues_spends_bribe_and_uses_rogue_level(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character()
    rolls = iter([4, 3])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = look_for_clues(campaign, hero)

    assert hero.gold == 16
    assert hero.clues == 1
    assert entry.roll == 3
    assert entry.modifier == 3
    assert entry.total == 6


def test_tag_look_for_clues_natural_one_loses_existing_clue(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(clues=1)
    rolls = iter([2, 1])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = look_for_clues(campaign, hero)

    assert hero.gold == 18
    assert hero.clues == 0
    assert "lost 1 Clue" in entry.result_text


def test_tag_simple_travel_rolls_days_and_new_size(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_name = "Varian"
    rolls = iter([5, 2, 3, 4])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = travel_to_new_settlement(campaign, destination_name="Diram")

    assert entry.from_settlement == "Varian"
    assert entry.to_settlement == "Diram"
    assert entry.days == 6
    assert entry.new_settlement_size == 2
    assert campaign.settlement_name == "Diram"
    assert campaign.settlement_size == 2
    assert campaign.days_passed == 6


def test_tag_hex_travel_logs_road_tithe_and_encounter_checks(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.settlement_name = "Varian"
    rolls = iter([6, 1, 3, 3, 4, 6, 6, 6])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = travel_to_new_settlement(campaign, destination_name="Diram", use_hex_map=True, pay_road_tithe=True)

    assert entry.new_settlement_size == 3
    assert entry.direction_roll == 1
    assert entry.distance_hexes == 8
    assert entry.road_roll == 18
    assert entry.road_exists is True
    assert entry.road_tithe_paid_gp == 3
    assert entry.encounter_checks == 3
    assert campaign.days_passed == 8


def test_tag_service_rows_gate_by_settlement_size_and_mark_availability() -> None:
    campaign = default_campaign()
    campaign.settlement_size = -1
    rows = {row["key"]: row for row in settlement_service_rows(campaign)}

    assert list(rows)[:28] == [
        "bank_account",
        "bank_inheritance",
        "magic_locker",
        "platinum_exchange",
        "hidden_treasure_trove",
        "resurrection_blessing_tags",
        "gems_jewelry_conversion",
        "bag_of_carrying",
        "ten_foot_pole",
        "lantern_hook",
        "very_nutritious_food",
        "poison_resistance_training",
        "martial_arts_training",
        "gambling_house",
        "treasure_maps",
        "moneylenders",
        "good_boots",
        "flammable_oil",
        "horn",
        "wineskin",
        "flail_axe",
        "aspergillum",
        "availability_rolls",
        "streetwise_rules",
        "adventurers_guild_jobs",
        "trinkets",
        "guild_spells",
        "tag_special_foes",
    ]
    assert rows["bank_account"]["status"] == "available"
    assert rows["magic_locker"]["status"] == "unavailable"
    assert rows["platinum_exchange"]["status"] == "church_only"
    assert rows["bag_of_carrying"]["availability_difficulty"] == 6
    assert rows["very_nutritious_food"]["availability_difficulty"] == 4
    assert rows["moneylenders"]["credit_limit_gp"] == 1800
    assert rows["horn"]["action"] == "horn_attract"
    assert rows["aspergillum"]["action"] == "aspergillum_break"
    assert "Adventure module" in rows["adventurers_guild_jobs"]["automation"]
    assert "Power Cookie" in rows["trinkets"]["summary"]
    assert "Wizard's Luck" in rows["guild_spells"]["summary"]
    assert "white gargoyles" in rows["tag_special_foes"]["summary"]

    campaign.settlement_size = 3
    rows = {row["key"]: row for row in settlement_service_rows(campaign)}
    assert rows["magic_locker"]["status"] == "available"
    assert rows["platinum_exchange"]["status"] == "available"


def test_tag_hidden_treasure_trove_risk_roll(monkeypatch) -> None:
    campaign = default_campaign()
    rolls = iter([1, 2, 2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = roll_hidden_treasure_trove_risk(campaign)

    assert entry.action == "hidden_treasure_trove_risk"
    assert entry.total == 5
    assert "discovered and stolen" in entry.result_text


def test_tag_treasure_map_price_uses_exploding_sixes(monkeypatch) -> None:
    campaign = default_campaign()
    rolls = iter([6, 2, 1, 3, 4, 5])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    entry = roll_treasure_map_price(campaign)

    assert entry.cost_gp == 21
    assert "6+2+1+3+4+5 = 21 gp" in entry.result_text


def test_tag_moneylender_follow_chance(monkeypatch) -> None:
    campaign = default_campaign()
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)

    entry = roll_moneylender_follow_chance(campaign, debt_gp=310)

    assert entry.total == 4
    assert "4-in-6 chance" in entry.result_text
    assert "enforcers follow" in entry.result_text


def test_tag_horn_oil_and_aspergillum_rolls(monkeypatch) -> None:
    campaign = default_campaign()
    rolls = iter([2, 1, 2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))

    horn = roll_horn_wandering_attraction(campaign)
    oil = roll_flammable_oil_throw(campaign)
    aspergillum = roll_aspergillum_break_chance(campaign)

    assert "wandering monsters are attracted" in horn.result_text
    assert "sprays a friend" in oil.result_text
    assert "breaks" in aspergillum.result_text


def test_tag_troupe_storage_purchase_and_locker(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(gold=1000)

    update_troupe(
        campaign,
        troupe_name="Varian Guild",
        member_character_ids=["hero-1", "hero-2", "hero-1"],
        active_character_ids=["hero-1", "hero-2", "hero-1"],
        guild_member=True,
        guild_coffers_gp=5000,
    )
    assert campaign.tag_troupe_name == "Varian Guild"
    assert campaign.tag_troupe_member_character_ids == ["hero-1", "hero-2"]
    assert campaign.tag_troupe_active_character_ids == ["hero-1", "hero-2"]
    assert campaign.tag_guild_member is True

    stored = store_tag_treasure(campaign, hero, storage="bank", gold_gp=100, item_name="Ruby", quantity=2)
    assert hero.gold == 890
    assert campaign.tag_storage_gold_gp == 100
    assert campaign.tag_stored_items[0].item_name == "Ruby"
    assert "10 gp bank fee" in stored.result_text

    withdrawn = withdraw_tag_stored_gold(campaign, hero, gold_gp=40)
    assert hero.gold == 930
    assert campaign.tag_storage_gold_gp == 60
    assert "withdraws 40 gp" in withdrawn.result_text

    purchase = purchase_tag_service(campaign, hero, service_key="blessing_tag", quantity=2)
    assert hero.gold == 770
    assert hero.inventory.count("TAG Blessing tag") == 2
    assert "Blessing tag" in purchase.result_text

    campaign.settlement_size = 0
    locker = create_magic_locker(campaign, hero, contents="Silver sword", kind="item")
    assert hero.gold == 720
    assert campaign.tag_magic_lockers[0].contents == "Silver sword"
    assert "magic locker" in locker.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 2)
    summon = summon_magic_locker(campaign, locker_id=campaign.tag_magic_lockers[0].id)
    assert campaign.tag_magic_lockers[0].mishap_locked is True
    assert "mishap" in summon.result_text


def test_tag_troupe_active_party_is_limited_to_troupe_members() -> None:
    campaign = default_campaign()

    update_troupe(
        campaign,
        guild_member=True,
        guild_coffers_gp=0,
        member_character_ids=["hero-1", "hero-2"],
        active_character_ids=["hero-2", "hero-3", "hero-1"],
    )

    assert campaign.tag_guild_coffers_gp == 5000
    assert campaign.tag_troupe_member_character_ids == ["hero-1", "hero-2"]
    assert campaign.tag_troupe_active_character_ids == ["hero-2", "hero-1"]


def test_tag_bank_migration_can_include_legacy_bank_with_optional_fee() -> None:
    campaign = default_campaign()
    hero = _character(gold=120)

    entry = convert_character_gold_to_tag_bank(
        campaign,
        hero,
        include_legacy_bank=True,
        legacy_bank_gold=80,
        apply_deposit_fee=True,
        note="migration",
    )

    assert hero.gold == 0
    assert campaign.tag_bank_accounts[0].gold_gp == 180
    assert campaign.tag_bank_accounts[0].notes == "migration"
    assert "20 gp TAG deposit fee" in entry.result_text


def test_tag_streetwise_gambling_and_treasure_map(monkeypatch) -> None:
    campaign = default_campaign()
    campaign.tag_guild_member = True
    hero = _character(gold=100, current_life=4)

    rolls = iter([5, 5, 6])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    monkeypatch.setattr(tag_campaign, "roll_d10", lambda: 7)
    monkeypatch.setattr(tag_campaign, "roll_d12", lambda: 6)

    rumor = run_streetwise_action(campaign, hero, action="listen_rumors")
    assert "hears rumor" in rumor.result_text

    gamble = roll_gambling_house(campaign, hero, stake_gp=10)
    assert gamble.total == 8
    assert "wins +10%" in gamble.result_text

    map_entry = follow_treasure_map(campaign, use_guild_cartographer=True)
    assert map_entry.total == 6
    assert "The Map Leads To 6" in map_entry.result_text


def test_tag_adventure_manifest_generation_validates() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()
    for lead_type in ("rumor", "treasure_map", "thematic_dungeon", "guild_job"):
        manifest, entry = build_tag_adventure_manifest(campaign, lead_type=lead_type, detail="1")
        result = validate_adventure_manifest(manifest, rules_repo=repo)
        assert result.valid, result.errors
        assert manifest["id"] in campaign.tag_generated_adventure_ids
        assert manifest["source"]["parameters"]["lead_type"] == lead_type
        assert "Adventure section" in entry.result_text


def test_tag_rumor_manifest_carries_pdf_rule_profile() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    manifest, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="2")
    result = validate_adventure_manifest(manifest, rules_repo=repo)

    assert result.valid, result.errors
    reference = manifest["source"]["parameters"]["tag_reference"]
    assert manifest["title"] == "TAG Rumor 2: Medusa in the Hunter's Cabin"
    assert reference["scene"] == "Scene 10 leading to Scene 1"
    assert reference["pdf_pages"] == "TAG pp.22, 25-26"
    assert reference["final_foe_proxy"] == "Medusa"
    assert "Pendant worth 260 gp" in reference["rewards"]
    final_room = next(room for room in manifest["rooms"] if room["id"] == "tag-final-scene")
    assert final_room["triggers"][0]["encounter"]["foes"] == [{"name": "Medusa", "count": 1}]


def test_tag_thematic_and_guild_job_manifests_use_profiles(monkeypatch) -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    dragon, _entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail="3")
    dragon_result = validate_adventure_manifest(dragon, rules_repo=repo)
    assert dragon_result.valid, dragon_result.errors
    dragon_ref = dragon["source"]["parameters"]["tag_reference"]
    assert dragon["title"] == "TAG Thematic Dungeon: Dragon's Lair"
    assert dragon_ref["pdf_pages"] == "TAG pp.39-40"
    assert dragon_ref["final_foe_proxy"] == "Young Dragon"
    assert any("Four-room target" in rule for rule in dragon_ref["rules"])

    rolls = iter([2])
    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: next(rolls))
    job, _entry = build_tag_adventure_manifest(campaign, lead_type="guild_job", detail="1")
    job_result = validate_adventure_manifest(job, rules_repo=repo)
    assert job_result.valid, job_result.errors
    job_ref = job["source"]["parameters"]["tag_reference"]
    assert job["title"] == "TAG Guild Job 1: Gorungar the Mighty"
    assert job_ref["pdf_pages"] == "TAG p.55"
    assert job_ref["final_foe_proxy"] == "Gorungar the Mighty"
    assert "50 gp for his head" in job_ref["rewards"]
    final_room = next(room for room in job["rooms"] if room["id"] == "tag-final-scene")
    assert final_room["triggers"][0]["encounter"]["foes"] == [
        {"name": "Gorungar the Mighty", "count": 1},
        {"name": "Gorungar's Goblin Archers", "count": 8},
    ]


def test_tag_special_foes_are_allowlisted_and_used_in_generated_adventures() -> None:
    repo = RulesRepository(Path("data/rules"), Path("data/rules/_override"))
    campaign = default_campaign()

    rumor, _entry = build_tag_adventure_manifest(campaign, lead_type="rumor", detail="10")
    assert validate_adventure_manifest(rumor, rules_repo=repo).valid
    rumor_ref = rumor["source"]["parameters"]["tag_reference"]
    assert rumor_ref["final_foes"] == [{"name": "White Gargoyles", "count": 8}]

    theme, _entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail="6")
    assert validate_adventure_manifest(theme, rules_repo=repo).valid
    theme_ref = theme["source"]["parameters"]["tag_reference"]
    assert theme_ref["final_foes"] == [
        {"name": "Bandit Chieftain", "count": 1},
        {"name": "TAG Bandits", "count": 6},
    ]


def test_tag_branch_trinket_guild_spell_and_finance_actions(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(
        gold=10,
        clues=5,
        current_life=1,
        inventory=["Potion of Healing", "Scroll of Wizard's Luck"],
        spells=["Look Tough"],
        statuses=["Poisoned"],
    )

    branch = resolve_tag_branch_action(
        campaign,
        hero,
        branch_action="spend_clues",
        reference="Scene 16 clue spend",
        clue_cost=2,
    )
    assert hero.clues == 3
    assert "spends 2 Clue" in branch.result_text

    trinket = use_tag_trinket(campaign, hero, trinket_key="potion_of_healing")
    assert hero.current_life == hero.max_life
    assert "Poisoned" not in hero.statuses
    assert "Potion of Healing" not in hero.inventory
    assert "uses Potion of Healing" in trinket.result_text

    spell = cast_tag_guild_spell(campaign, hero, spell_key="wizards_luck")
    assert "Scroll of Wizard's Luck" not in hero.inventory
    assert "TAG Wizard's Luck pending" in hero.statuses
    assert "scroll consumed" in spell.result_text

    hero.current_life = 1
    hero.inventory.append("Scroll of Speedy Recovery")
    recovery_spell = cast_tag_guild_spell(campaign, hero, spell_key="speedy_recovery")
    assert hero.current_life == hero.max_life
    assert "TAG Speedy Recovery pending" in hero.statuses
    assert "scroll consumed" in recovery_spell.result_text

    clear_marker = consume_tag_guild_marker(campaign, hero, marker_key="speedy_recovery")
    assert "TAG Speedy Recovery pending" not in hero.statuses
    assert "clears TAG Guild marker" in clear_marker.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 1)
    risk = resolve_tag_finance_action(campaign, hero, finance_action="robbery_risk")
    assert risk.total == 3
    assert "robbery or theft occurs" in risk.result_text

    recovery = resolve_tag_finance_action(campaign, hero, finance_action="robbery_recovery")
    assert "spends 3 Clues" in recovery.result_text

    campaign.tag_guild_coffers_gp = 1000
    upkeep = resolve_tag_finance_action(campaign, finance_action="guild_upkeep")
    assert campaign.tag_guild_coffers_gp == 900
    assert "100 gp paid" in upkeep.result_text


def test_tag_route_and_xp_actions_persist_structured_signoff_state() -> None:
    campaign = default_campaign()
    hero = _character(clues=3, xp=2, statuses=[])

    route = resolve_tag_route_action(
        campaign,
        hero,
        route_action="clue_gate_unlocked",
        reference="Scene 16 cult hideout",
        clue_cost=2,
    )
    assert hero.clues == 1
    assert campaign.tag_adventure_routes[-1].route_action == "clue_gate_unlocked"
    assert campaign.tag_adventure_routes[-1].resolved is True
    assert "route is unlocked" in route.result_text

    blocked = resolve_tag_route_action(
        campaign,
        hero,
        route_action="clue_gate_blocked",
        reference="Dragon lair reveal",
        clue_cost=2,
    )
    assert campaign.tag_adventure_routes[-1].resolved is False
    assert "Route remains blocked" in blocked.result_text

    xp = resolve_tag_xp_action(campaign, hero, xp_action="award_scene_xp", reference="Daroc's cat", xp=1)
    assert hero.xp == 3
    assert campaign.tag_xp_markers[-1].applied is True
    assert "gains 1 XP" in xp.result_text

    training = resolve_tag_xp_action(campaign, hero, xp_action="mark_training_xp_roll", reference="Deoldyn", xp=0)
    assert "TAG Deoldyn archery XP roll pending" in hero.statuses
    assert campaign.tag_xp_markers[-1].xp_action == "mark_training_xp_roll"
    assert "Training XP roll marker" in training.result_text


def test_tag_scene_rewards_and_bank_ledgers(monkeypatch) -> None:
    campaign = default_campaign()
    hero = _character(gold=500, clues=3, level=2, inventory=[], statuses=[])

    bounty = resolve_tag_scene_action(campaign, hero, scene_action="gargoyle_bounty", amount=3)
    assert hero.gold == 545
    assert "45 gp" in bounty.result_text

    agaratha = resolve_tag_scene_action(campaign, hero, scene_action="agaratha")
    assert "Agaratha" in hero.inventory
    assert "TAG Agaratha Luck-on-major-kill" in hero.statuses
    assert "Luck-on-major-kill" in agaratha.result_text

    monkeypatch.setattr(tag_campaign, "roll_d6", lambda: 4)
    reveal = resolve_tag_scene_action(campaign, hero, scene_action="dragon_type_reveal")
    assert hero.clues == 1
    assert "Dragon's Lair" in reveal.result_text

    deposit = resolve_tag_finance_action(campaign, hero, finance_action="bank_deposit", amount_gp=100, note="Sister Joyce")
    assert hero.gold == 435
    assert campaign.tag_bank_accounts[0].gold_gp == 100
    assert campaign.tag_bank_accounts[0].notes == "Sister Joyce"
    assert "10 gp fee" in deposit.result_text

    inheritance = resolve_tag_finance_action(campaign, hero, finance_action="inheritance", note="Sister Joyce")
    assert campaign.tag_bank_accounts[0].heir_name == "Sister Joyce"
    assert "20% inheritance tax" in inheritance.result_text

    heir = _character(id="heir-1", name="Sister Joyce", gold=0)
    transfer = resolve_tag_finance_action(campaign, heir, finance_action="inheritance_transfer")
    assert heir.gold == 80
    assert campaign.tag_bank_accounts[0].gold_gp == 0
    assert "20 gp inheritance tax" in transfer.result_text


def test_tag_guild_ledger_deposit_and_martial_training_are_free() -> None:
    campaign = default_campaign()
    campaign.tag_guild_member = True
    hero = _character(gold=125, statuses=[])

    deposit = resolve_tag_finance_action(campaign, hero, finance_action="bank_deposit", amount_gp=100, note="Guild ledger")
    assert hero.gold == 25
    assert campaign.tag_bank_accounts[0].gold_gp == 100
    assert "for free under the TAG Guild ledger rule" in deposit.result_text

    training = purchase_tag_service(campaign, hero, service_key="martial_arts_training")
    assert hero.gold == 25
    assert "TAG martial arts training" in hero.statuses
    assert "train for free" in training.result_text


def test_tag_guild_mundane_equipment_discount() -> None:
    catalog = RulesRepository(Path("data/rules"), Path("data/rules/_override")).equipment_shop()
    hero = _character(class_id="warrior", class_name="Warrior", gold=10)

    ok, message = buy_equipment(hero, catalog, item_key="shield", tag_guild_discount=True)

    assert ok, message
    assert hero.gold == 5
    assert "TAG Guild mundane equipment discount" in message
